# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Consulta de CNPJ para o cadastro de cliente, fornecedor e empresa.

A regra mora em `fiscal/cadastro_cnpj.py` (pura, testada sem rede). Aqui ficam a chamada HTTP, os provedores, o cache,
o limite de uso, a permissão e a criação do endereço.

O que o usuário precisa saber antes de confiar
------------------------------------------------
- **A fonte são os dados abertos da Receita, publicados todo mês.** Quem responde (BrasilAPI e Minha Receita, o mesmo esquema) não
  consulta a Receita em tempo real: a situação cadastral pode estar defasada em até um mês. A tela diz isso.
- **É aviso, não bloqueio.** CNPJ baixado, suspenso ou inapto gera um alerta no formulário; nada impede de salvar.
- **Sem rede o cadastro continua**: provedor fora do ar, limite de uso ou resposta estranha viram "indisponível", sem exceção.

Provedores e fallback
----------------------
`brasil_consulta_cnpj_provedores` em `site_config` é uma lista de modelos de URL com `{cnpj}`; sem ela valem os dois padrão
(BrasilAPI, depois Minha Receita). Cai-se para o próximo só quando o provedor **não responde** (rede, limite, 5xx, resposta
inválida) — um 404 é a resposta, não uma falha, e não é repetido no outro. Quem não admite mandar o CNPJ a terceiros hospeda o
Minha Receita (MIT) e aponta a lista para ele. **Lista configurada e inválida não volta aos padrão**: seria reintroduzir
exatamente os terceiros que o administrador quis evitar; a consulta fica indisponível e o erro é registrado.
`brasil_consulta_cnpj: false` desliga tudo.

Privacidade
-----------
O que sai do servidor é **só o CNPJ**. Em empresário individual e MEI o CNPJ identifica uma pessoa física, razão pela qual o
envio é desligável e hospedável. O quadro de sócios, o e-mail e o telefone nunca são lidos (ver o módulo puro). O `Address` só
nasce por ação explícita do usuário e **só se a parte ainda não tem endereço**.

Estado de verificação: camada Frappe, exercitada por `tests_bench/test_consulta_cnpj.py` com o HTTP trocado por um duplo; a
chamada real foi conferida à mão em 2026-10-10 (ver `fiscal/cadastro_cnpj.py`).
"""

import dataclasses
from urllib.parse import urlsplit

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from erpnext_brasil.fiscal.cadastro_cnpj import (
	CAMPO_NOME_POR_DOCTYPE,
	MODELOS_PADRAO,
	CadastroCnpj,
	CnpjInvalido,
	EnderecoCnpj,
	ModeloInvalido,
	ProvedorIndisponivel,
	RespostaCnpjInvalida,
	aviso_de_situacao,
	campos_do_endereco,
	interpretar_resposta,
	lacunas_da_parte,
	normalizar_cnpj,
	resumo,
	tem_cpf_no_nome,
	url_do_provedor,
)

__all__ = ["consultar_cnpj", "criar_endereco_pelo_cnpj"]

CHAVE_CONFIGURACAO = "brasil_consulta_cnpj"
"""`site_config`: `false` desliga a consulta (rede restrita, ou política de não enviar o CNPJ a terceiros)."""
CHAVE_PROVEDORES = "brasil_consulta_cnpj_provedores"
"""`site_config`: lista de modelos de URL com `{cnpj}`. Sem ela, valem `MODELOS_PADRAO`."""

ESPERA_S = 5
VALIDADE_ACHADO_S = 24 * 3600
"""Um dia: a base é mensal, então uma consulta repetida na mesma tarde não ganha nada indo à rede."""
VALIDADE_AUSENTE_S = 3600
PREFIXO_CACHE = "erpnext_brasil:cnpj:"

ENCONTRADO = "encontrado"
NAO_ENCONTRADO = "nao_encontrado"
INDISPONIVEL = "indisponivel"
INVALIDO = "invalido"


def _http(url: str) -> tuple[int, bytes]:
	"""A requisição de verdade: `(status, corpo)`. **Não segue redirecionamento** (um provedor não deve nos mandar a outro
	lugar) e não levanta por status — quem decide o que cada status significa é a camada pura."""
	import requests

	resposta = requests.get(
		url,
		timeout=ESPERA_S,
		allow_redirects=False,
		headers={"Accept": "application/json", "User-Agent": "erpnext_brasil"},
	)

	return resposta.status_code, resposta.content


def _cache():
	"""O cache do Frappe — função no v15, objeto no v16."""
	cache = frappe.cache

	return cache() if callable(cache) else cache


def _ligada() -> bool:
	return frappe.conf.get(CHAVE_CONFIGURACAO, True) not in (False, 0, "0", "false", "off")


def _resposta(situacao: str, mensagem: str = "", **extra) -> dict:
	return {"situacao": situacao, "mensagem": mensagem, **extra}


def _modelos() -> list[str]:
	"""Os modelos de URL válidos, na ordem. Lista configurada e inválida **não** volta aos padrão (ver a docstring do módulo)."""
	configurados = frappe.conf.get(CHAVE_PROVEDORES)

	if not configurados:
		return list(MODELOS_PADRAO)

	validos = []

	for modelo in configurados if isinstance(configurados, list | tuple) else [configurados]:
		try:
			url_do_provedor(modelo, "00000000000191")  # confere o modelo, não consulta ninguém
			validos.append(modelo)
		except ModeloInvalido as erro:
			frappe.log_error(title="Consulta de CNPJ: provedor inválido", message=str(erro))

	return validos


def _atual(valor, doctype: str) -> dict[str, str]:
	"""Os valores do formulário, filtrados para o campo de nome da parte (vem do navegador)."""
	if isinstance(valor, str):
		try:
			valor = frappe.parse_json(valor) if valor.strip() else {}
		except (ValueError, TypeError):
			return {}

	campo = CAMPO_NOME_POR_DOCTYPE.get(doctype)

	return {campo: str(valor.get(campo) or "")} if campo and isinstance(valor, dict) else {}


def _guardar(cadastro: CadastroCnpj, fonte: str) -> None:
	_cache().set_value(
		PREFIXO_CACHE + cadastro.cnpj,
		{"cadastro": dataclasses.asdict(cadastro), "fonte": fonte},
		expires_in_sec=VALIDADE_ACHADO_S,
	)


def _do_cache(cnpj: str):
	"""`(CadastroCnpj, fonte)`, `False` para "inexistente guardado", ou `None` quando não há nada."""
	guardado = _cache().get_value(PREFIXO_CACHE + cnpj)

	if not isinstance(guardado, dict):
		return None

	if guardado.get("ausente"):
		return False

	try:
		dados = dict(guardado["cadastro"])
		dados["endereco"] = EnderecoCnpj(**dados["endereco"])

		return CadastroCnpj(**dados), guardado.get("fonte", "")
	except (KeyError, TypeError):
		return None  # cache de uma forma antiga: ignora e consulta de novo


def _buscar_cadastro(cnpj: str, buscar):
	"""`(CadastroCnpj, fonte)`, `False` (inexistente) ou `None` (nenhum provedor respondeu)."""
	guardado = _do_cache(cnpj)

	if guardado is not None:
		return guardado

	for modelo in _modelos():
		try:
			status, corpo = buscar(url_do_provedor(modelo, cnpj))
			cadastro = interpretar_resposta(status, corpo)
		except (OSError, ProvedorIndisponivel, RespostaCnpjInvalida):
			continue

		if cadastro is None:
			_cache().set_value(PREFIXO_CACHE + cnpj, {"ausente": True}, expires_in_sec=VALIDADE_AUSENTE_S)

			return False

		fonte = urlsplit(modelo.replace("{cnpj}", "x")).hostname or ""
		_guardar(cadastro, fonte)

		return cadastro, fonte

	return None


def consultar(doctype: str, cnpj, atual=None, buscar=_http) -> dict:
	"""Consulta por CNPJ. `buscar` é a chamada HTTP — injetável para teste, **fora** do endpoint exposto."""
	if not _ligada():
		return _resposta(INDISPONIVEL, _("A consulta de CNPJ está desligada neste site."))

	try:
		digitos = normalizar_cnpj(cnpj)
	except CnpjInvalido as erro:
		return _resposta(INVALIDO, str(erro))

	if not _modelos():
		return _resposta(INDISPONIVEL, _("Nenhum provedor de CNPJ válido está configurado neste site."))

	achado = _buscar_cadastro(digitos, buscar)

	if achado is None:
		return _resposta(
			INDISPONIVEL, _("Consulta de CNPJ indisponível agora. Preencha o cadastro manualmente.")
		)

	if achado is False:
		return _resposta(
			NAO_ENCONTRADO,
			_("CNPJ não encontrado na base da Receita (a base é mensal: um CNPJ novo pode demorar)."),
		)

	cadastro, fonte = achado

	return _resposta(
		ENCONTRADO,
		preencher=lacunas_da_parte(doctype, _atual(atual, doctype), cadastro),
		aviso=aviso_de_situacao(cadastro),
		aviso_nome=_(
			"A razão social traz um CPF (formato antigo de MEI) e não foi sugerida como nome. Preencha à mão."
		)
		if tem_cpf_no_nome(cadastro.razao_social)
		else "",
		ativo=cadastro.ativo,
		resumo=resumo(cadastro),
		pode_criar_endereco=bool(campos_do_endereco(cadastro)),
		fonte=fonte,
	)


def _exigir_permissao(doctype: str) -> None:
	"""Quem consulta é quem poderia gravar o cadastro — e só para os três cadastros que têm CNPJ."""
	if doctype not in CAMPO_NOME_POR_DOCTYPE or not (
		frappe.has_permission(doctype, "create") or frappe.has_permission(doctype, "write")
	):
		raise frappe.PermissionError(_("Sem permissão para cadastrar {0}.").format(doctype))


def criar_endereco(doctype: str, name: str, buscar=_http) -> dict:
	"""Cria o `Address` do estabelecimento — **só** se a parte ainda não tem endereço. Ação explícita do usuário."""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	frappe.has_permission("Address", "create", throw=True)

	if frappe.db.exists(
		"Dynamic Link", {"link_doctype": doctype, "link_name": name, "parenttype": "Address"}
	):
		return _resposta("ja_tem_endereco", _("Este cadastro já tem endereço; nada foi alterado."))

	try:
		digitos = normalizar_cnpj(doc.get("tax_id"))
	except CnpjInvalido as erro:
		return _resposta(INVALIDO, str(erro))

	achado = _buscar_cadastro(digitos, buscar) if _ligada() else None

	if not achado:
		return _resposta(INDISPONIVEL, _("Não foi possível obter o endereço do CNPJ agora."))

	campos = campos_do_endereco(achado[0])

	if not campos:
		return _resposta(NAO_ENCONTRADO, _("A Receita não traz logradouro para este CNPJ."))

	endereco = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": doc.get(CAMPO_NOME_POR_DOCTYPE[doctype]) or name,
			"address_type": "Billing",
			"is_primary_address": 1,
			"links": [{"link_doctype": doctype, "link_name": name}],
			**campos,
		}
	)
	endereco.insert()

	return _resposta(
		"criado",
		_("Endereço criado a partir do CNPJ. Confira o número e o complemento."),
		endereco=endereco.name,
	)


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def consultar_cnpj(doctype: str, cnpj: str, atual: str | dict | None = None) -> dict:
	"""Cadastro do CNPJ: o que cabe preencher (só lacuna), a situação na Receita e um resumo. Nunca levanta por falha do serviço."""
	_exigir_permissao(doctype)

	return consultar(doctype, cnpj, atual)


@frappe.whitelist()
@rate_limit(limit=20, seconds=60)
def criar_endereco_pelo_cnpj(doctype: str, name: str) -> dict:
	"""Cria o endereço do estabelecimento para a parte que ainda não tem nenhum."""
	_exigir_permissao(doctype)

	return criar_endereco(doctype, name)
