# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Consulta de CEP e logradouro no ViaCEP, para preencher o `Address`.

A regra mora em `fiscal/endereco_cep.py` (pura, testada sem rede). Aqui fica o que depende do mundo: a
chamada HTTP, o cache, o limite de uso, a permissão e a degradação quando não há rede.

Por que o servidor consulta, e não o navegador
------------------------------------------------
O navegador do usuário poderia falar direto com o ViaCEP, mas aí a decisão do que entra no cadastro, o
cache e o limite de uso ficariam espalhados em cada máquina — e o servidor, que é quem valida e grava,
nunca saberia de onde o dado veio. O JS (`public/js/endereco_cep.js`) só mostra o que esta camada decide.

O que sai do servidor, e o que não sai
---------------------------------------
Só o CEP ou o texto de busca (UF, cidade, logradouro) que o usuário digitou. **Nenhum dado de pessoa**
(nome, CPF, CNPJ) vai ao ViaCEP; um CEP isolado não identifica ninguém. O texto de busca vai a um serviço de
terceiro, e quem não admite isso desliga a consulta com `brasil_consulta_cep: false` em `site_config`.

Um serviço de terceiro gratuito, sem SLA — o desenho assume que ele vai falhar
-------------------------------------------------------------------------------
O ViaCEP não publica SLA nem limite de requisições, e avisa que uso massivo para validar bases pode levar a
bloqueio por tempo indeterminado. Daí:

- consulta **só sob demanda** (o usuário digitou o CEP ou pediu a busca), nunca em lote nem em validação de
  base;
- **cache** (7 dias para CEP achado, 1 dia para inexistente e para busca vazia): CEP quase não muda, e o
  usuário que erra a digitação três vezes não custa três requisições;
- cada resultado de uma busca por logradouro **alimenta o cache por CEP**, de modo que escolher uma linha da
  lista não faz uma segunda chamada;
- **prazo curto** (`ESPERA_S`) e **nenhuma exceção sobe**: sem rede, com erro 5xx ou com resposta estranha, a
  tela recebe `situacao: "indisponivel"` e o usuário preenche à mão, como sempre fez. A consulta ajuda e
  nunca trava o cadastro;
- limite por IP no endpoint (`rate_limit`), para um cliente com defeito não virar o "uso massivo" do aviso.

Devolve `situacao` em vez de levantar erro: CEP inexistente é resultado normal de consulta, e indisponível é
estado esperado de um serviço externo — nenhum dos dois é falha do sistema.

Estado de verificação: camada Frappe, exercitada por `tests_bench/test_consulta_cep.py` com o HTTP trocado
por um duplo. A chamada real ao ViaCEP foi conferida à mão em 2026-10-10 (ver `fiscal/endereco_cep.py`).
"""

import dataclasses
import hashlib

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from erpnext_brasil.fiscal.endereco_cep import (
	CAMPOS_DO_ENDERECO,
	CepInvalido,
	EnderecoCep,
	RespostaCepInvalida,
	campos_do_endereco,
	divergencias,
	interpretar_busca,
	interpretar_cep,
	lacunas,
	normalizar_cep,
	url_por_cep,
	url_por_logradouro,
)

__all__ = ["buscar_logradouro", "consultar_cep"]

CHAVE_CONFIGURACAO = "brasil_consulta_cep"
"""`site_config`: `false` desliga a consulta (rede restrita, ou política de não enviar texto a terceiros)."""

ESPERA_S = 5
"""Prazo da chamada. Curto de propósito: o usuário está parado esperando o campo, e o fallback é digitar."""

VALIDADE_ACHADO_S = 7 * 24 * 3600
VALIDADE_AUSENTE_S = 24 * 3600
PREFIXO_CACHE = "erpnext_brasil:viacep:"

ENCONTRADO = "encontrado"
NAO_ENCONTRADO = "nao_encontrado"
INDISPONIVEL = "indisponivel"
INVALIDO = "invalido"

ROTULOS = {
	"state": "UF",
	"city": "Município",
	"br_codigo_municipio_ibge": "Código IBGE",
}


def _http(url: str) -> bytes:
	"""A requisição de verdade. A URL vem de `url_por_cep`/`url_por_logradouro`, nunca de texto cru do usuário."""
	import requests

	resposta = requests.get(
		url, timeout=ESPERA_S, headers={"Accept": "application/json", "User-Agent": "erpnext_brasil"}
	)

	if resposta.status_code != 400:
		# O 400 do serviço vem com uma página HTML; deixá-lo seguir faz o parser acusar "resposta inválida",
		# que é o que ele é. Os demais erros (429, 5xx) viram exceção e caem em `indisponivel`.
		resposta.raise_for_status()

	return resposta.content


def _cache():
	"""O cache do Frappe — função no v15, objeto no v16."""
	cache = frappe.cache

	return cache() if callable(cache) else cache


def _ligada() -> bool:
	return frappe.conf.get(CHAVE_CONFIGURACAO, True) not in (False, 0, "0", "false", "off")


def _resposta(situacao: str, mensagem: str = "", **extra) -> dict:
	return {"situacao": situacao, "mensagem": mensagem, **extra}


def _atual(valor) -> dict[str, str]:
	"""Os valores que o formulário tem hoje, filtrados para os campos que a consulta conhece.

	Vem do navegador, então nada além de `CAMPOS_DO_ENDERECO` é lido, e tudo vira texto."""
	if isinstance(valor, str):
		try:
			valor = frappe.parse_json(valor) if valor.strip() else {}
		except (ValueError, TypeError):
			return {}  # texto que não é JSON: ignora o que o formulário mandou, não derruba a consulta

	if not isinstance(valor, dict):
		return {}

	return {campo: str(valor.get(campo) or "") for campo in CAMPOS_DO_ENDERECO}


def _guardar(endereco: EnderecoCep) -> None:
	_cache().set_value(
		PREFIXO_CACHE + endereco.cep.replace("-", ""),
		{"achado": dataclasses.asdict(endereco)},
		expires_in_sec=VALIDADE_ACHADO_S,
	)


def _guardar_ausente(digitos: str) -> None:
	_cache().set_value(PREFIXO_CACHE + digitos, {"ausente": True}, expires_in_sec=VALIDADE_AUSENTE_S)


def _do_cache(digitos: str):
	"""`EnderecoCep` guardado, `False` para "inexistente guardado", ou `None` quando não há nada."""
	guardado = _cache().get_value(PREFIXO_CACHE + digitos)

	if not isinstance(guardado, dict):
		return None

	if guardado.get("ausente"):
		return False

	try:
		return EnderecoCep(**guardado["achado"])
	except (KeyError, TypeError):
		return None  # cache de uma forma antiga: ignora e consulta de novo


def _montar_encontrado(endereco: EnderecoCep, atual: dict) -> dict:
	return _resposta(
		ENCONTRADO,
		endereco=campos_do_endereco(endereco),
		preencher=lacunas(atual, endereco),
		divergencias=[
			{"campo": d.campo, "rotulo": ROTULOS[d.campo], "atual": d.atual, "sugerido": d.sugerido}
			for d in divergencias(atual, endereco)
		],
		fonte="ViaCEP",
	)


def consultar(cep, atual=None, buscar=_http) -> dict:
	"""Consulta por CEP. `buscar` é a chamada HTTP — injetável para teste, **fora** do endpoint exposto."""
	atual = _atual(atual)

	if not _ligada():
		return _resposta(INDISPONIVEL, _("A consulta de CEP está desligada neste site."))

	try:
		digitos = normalizar_cep(cep)
	except CepInvalido as erro:
		return _resposta(INVALIDO, str(erro))

	guardado = _do_cache(digitos)

	if guardado is False:
		return _resposta(NAO_ENCONTRADO, _("CEP não encontrado na base do ViaCEP."))

	if guardado is not None:
		return _montar_encontrado(guardado, atual)

	try:
		endereco = interpretar_cep(buscar(url_por_cep(digitos)))
	except (OSError, RespostaCepInvalida):
		return _resposta(
			INDISPONIVEL, _("Consulta de CEP indisponível agora. Preencha o endereço manualmente.")
		)

	if endereco is None:
		_guardar_ausente(digitos)

		return _resposta(NAO_ENCONTRADO, _("CEP não encontrado na base do ViaCEP."))

	_guardar(endereco)

	return _montar_encontrado(endereco, atual)


def _rotulo(endereco: EnderecoCep) -> str:
	partes = [p for p in (endereco.logradouro, endereco.bairro) if p]

	return " — ".join([", ".join(partes) or endereco.cidade, endereco.cep])


def _chave_da_busca(uf: str, cidade: str, logradouro: str) -> str:
	normal = "|".join(" ".join(str(t or "").split()).casefold() for t in (uf, cidade, logradouro))

	# SHA-1 só como chave de cache (não protege nada), por isso `usedforsecurity=False`.
	resumo = hashlib.sha1(normal.encode("utf-8"), usedforsecurity=False).hexdigest()

	return PREFIXO_CACHE + "busca:" + resumo


def buscar(uf, cidade, logradouro, http=_http) -> dict:
	"""Busca de CEP por logradouro. `http` é a chamada HTTP, injetável para teste."""
	if not _ligada():
		return _resposta(INDISPONIVEL, _("A consulta de CEP está desligada neste site."))

	try:
		url = url_por_logradouro(uf, cidade, logradouro)
	except CepInvalido as erro:
		return _resposta(INVALIDO, str(erro))

	chave = _chave_da_busca(uf, cidade, logradouro)
	guardado = _cache().get_value(chave)

	if isinstance(guardado, dict) and "resultados" in guardado:
		return _resposta(
			ENCONTRADO if guardado["resultados"] else NAO_ENCONTRADO, resultados=guardado["resultados"]
		)

	try:
		achados = interpretar_busca(http(url))
	except (OSError, RespostaCepInvalida):
		return _resposta(
			INDISPONIVEL, _("Busca de endereço indisponível agora. Preencha o endereço manualmente.")
		)

	resultados = []

	for endereco in achados:
		# Cada linha da lista já é um endereço completo: guardá-lo por CEP evita a segunda chamada quando o
		# usuário escolhe uma delas.
		_guardar(endereco)
		resultados.append(
			{"rotulo": _rotulo(endereco), "cep": endereco.cep, "endereco": campos_do_endereco(endereco)}
		)

	_cache().set_value(
		chave,
		{"resultados": resultados},
		expires_in_sec=VALIDADE_ACHADO_S if resultados else VALIDADE_AUSENTE_S,
	)

	if not resultados:
		return _resposta(NAO_ENCONTRADO, _("Nenhum endereço encontrado para essa busca."), resultados=[])

	return _resposta(ENCONTRADO, resultados=resultados, fonte="ViaCEP")


def _exigir_permissao() -> None:
	"""Quem consulta é quem poderia gravar o endereço — não há razão para um usuário sem acesso gastar a cota."""
	if not (frappe.has_permission("Address", "create") or frappe.has_permission("Address", "write")):
		raise frappe.PermissionError(_("Sem permissão para cadastrar endereços."))


@frappe.whitelist()
@rate_limit(limit=120, seconds=60)
def consultar_cep(cep: str, atual: str | dict | None = None) -> dict:
	"""Endereço do CEP, o que cabe preencher (só lacunas) e o que o cadastro contradiz (só aviso).

	`atual` são os valores do formulário; sem eles tudo é lacuna. Nunca levanta por falha do serviço."""
	_exigir_permissao()

	return consultar(cep, atual)


@frappe.whitelist()
@rate_limit(limit=60, seconds=60)
def buscar_logradouro(uf: str, cidade: str, logradouro: str) -> dict:
	"""Até 50 endereços que casam com UF, cidade e logradouro. Nunca levanta por falha do serviço."""
	_exigir_permissao()

	return buscar(uf, cidade, logradouro)
