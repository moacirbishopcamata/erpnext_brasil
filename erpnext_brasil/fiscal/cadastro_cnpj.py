# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Consulta de CNPJ — a parte que não depende de rede nem de Frappe.

Por que existe
--------------
Cadastrar cliente, fornecedor e empresa à mão é onde entram a razão social digitada errada, o endereço
incompleto e — o que importa para a nota — o CNPJ **baixado ou inapto** que ninguém conferiu. Este módulo sabe
*montar a pergunta*, *ler a resposta* e *decidir o que cabe no cadastro*. Quem faz a chamada HTTP é
`integracao/consulta_cnpj.py`.

A fonte, e por que não é "a Receita"
-------------------------------------
**Não existe API gratuita oficial da Receita.** A oficial é a do Serpro (OAuth2, certificado e-CNPJ, gratuita só por
30 dias ou 3.000 consultas, depois cobrada); não é o padrão deste módulo. As gratuitas processam os **dados abertos
da Receita, publicados todo mês**: a BrasilAPI e o Minha Receita (MIT, **pode ser hospedado pela própria empresa**, sem
terceiro) respondem o **mesmo esquema** — a BrasilAPI usa a base do Minha Receita — e são os dois modelos de URL
padrão. A consequência que o usuário precisa ver: a **situação cadastral pode estar defasada em até um mês**
(`AVISO_DE_DEFASAGEM`). Consulta de situação em tempo real é do SEFAZ/Receita com certificado, outra frente.

O que a verificação ao vivo ensinou (2026-10-10, com o CNPJ público do Banco do Brasil)
-----------------------------------------------------------------------------------------
- `codigo_municipio` (9701) é o código **da Receita**; o do IBGE, de 7 dígitos, é `codigo_municipio_ibge` (5300108).
  Trocar um pelo outro grava um município errado sem dar erro.
- O CNPJ **alfanumérico** (IN RFB 2.229/2024, em produção desde julho de 2026) é formato válido para os dois: um
  inexistente devolve **404**, não 400. Um dígito inválido devolve **400**. Os dois erros vêm em JSON.
- `numero` vem como `SN` quando não há número.
- O tipo do logradouro vem à parte (`RUA` + `CAPITAO CRUZ`), mas há casos em que ele já consta no nome
  (`QUADRA` + `SAUN QUADRA 5…`); repeti-lo daria "QUADRA SAUN QUADRA 5…".

Privacidade
-----------
- **O quadro de sócios (`qsa`) nunca é lido**: traz nome e CPF mascarado de pessoas físicas, e nada nele serve ao cadastro.
  O mesmo vale para e-mail e telefone do estabelecimento, que podem ser de pessoa física (empresário individual).
- **A razão social do MEI** deixou de levar o CPF em 12/12/2022 (passou a ser os 8 dígitos do CNPJ seguidos do nome, para
  adequar o cadastro à LGPD), mas o registro só é atualizado quando o titular acessa o cadastro: pode haver
  "NOME 12345678909" na base. Um nome que **termina em 11 dígitos** (ou traz um CPF formatado) **não é sugerido** — o
  campo fica em branco e o usuário preenche. O formato novo ("12.345.678 NOME") é o nome oficial e fica como está.

Regra de ouro: sugestão preenche lacuna, nunca corrige
--------------------------------------------------------
`lacunas_da_parte` só propõe campo **vazio**. Cliente costuma ter nome fantasia no cadastro, e trocá-lo pela razão social
apagaria uma escolha. O que a Receita diz da situação (`aviso_de_situacao`) é **aviso**, não bloqueio: a base é mensal.

Funções puras: nenhuma dependência do Frappe.
"""

import json
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from erpnext_brasil.fiscal.validators import ValidacaoFiscalError, validar_cnpj

__all__ = [
	"AVISO_DE_DEFASAGEM",
	"CAMPO_NOME_POR_DOCTYPE",
	"MODELOS_PADRAO",
	"SITUACAO_ATIVA",
	"CadastroCnpj",
	"CnpjInvalido",
	"EnderecoCnpj",
	"ModeloInvalido",
	"ProvedorIndisponivel",
	"RespostaCnpjInvalida",
	"aviso_de_situacao",
	"campos_do_endereco",
	"interpretar_resposta",
	"lacunas_da_parte",
	"normalizar_cnpj",
	"razao_social_sugerida",
	"resumo",
	"tem_cpf_no_nome",
	"url_do_provedor",
]

MODELOS_PADRAO = (
	"https://brasilapi.com.br/api/cnpj/v1/{cnpj}",
	"https://minhareceita.org/{cnpj}",
)
"""Os dois provedores verificados ao vivo, com o mesmo esquema. O marcador `{cnpj}` leva os 14 caracteres limpos."""

AVISO_DE_DEFASAGEM = "Dados abertos da Receita Federal, atualizados mensalmente: a situação cadastral pode estar defasada em até um mês."

CHAVE_IBGE_DO_PROVEDOR = "codigo_municipio_ibge"
"""Chave do **JSON do provedor**, não campo de documento (o do documento é `br_codigo_municipio_ibge`). Constante
nomeada para o guarda `test_resquicios_do_renome` não confundir a chave externa com o nome de campo anterior ao `br_`."""

SITUACAO_ATIVA = 2

SITUACOES = {1: "NULA", 2: "ATIVA", 3: "SUSPENSA", 4: "INAPTA", 8: "BAIXADA"}
"""Códigos do layout dos dados abertos (fonte secundária; o `2 = ATIVA` foi confirmado na resposta real)."""

CAMPO_NOME_POR_DOCTYPE = {
	"Customer": "customer_name",
	"Supplier": "supplier_name",
	"Company": "company_name",
}

_CPF_NO_FIM = re.compile(r"(?:^|\s)\d{11}$")
_CPF_FORMATADO = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")


class CnpjInvalido(ValueError):
	"""O CNPJ que não vale a pena perguntar a ninguém — barrado antes de sair."""


class ModeloInvalido(ValueError):
	"""Modelo de URL de provedor mal configurado."""


class RespostaCnpjInvalida(ValueError):
	"""O que voltou não é uma resposta de CNPJ utilizável (página de erro, JSON de outra forma, lixo)."""


class ProvedorIndisponivel(ValueError):
	"""Limite de uso, erro de servidor ou qualquer status que não diga nada sobre o CNPJ."""


@dataclass(frozen=True)
class EnderecoCnpj:
	logradouro: str
	"""Tipo + nome, sem repetir o tipo quando ele já consta no nome."""
	numero: str
	complemento: str
	bairro: str
	cep: str
	"""`70040-912`, o formato que o app já aceita."""
	municipio: str
	uf: str
	codigo_municipio_ibge: str
	"""Os 7 dígitos do IBGE — **não** o `codigo_municipio` da Receita."""


@dataclass(frozen=True)
class CadastroCnpj:
	cnpj: str
	razao_social: str
	nome_fantasia: str
	situacao: int | None
	situacao_descricao: str
	data_situacao: str
	motivo_situacao: str
	cnae_codigo: str
	cnae_descricao: str
	natureza_juridica: str
	porte: str
	optante_simples: bool | None
	mei: bool | None
	matriz: bool | None
	endereco: EnderecoCnpj

	@property
	def ativo(self) -> bool:
		return self.situacao == SITUACAO_ATIVA


def normalizar_cnpj(texto) -> str:
	"""Os 14 caracteres do CNPJ (numérico ou alfanumérico), com os dígitos conferidos — ou `CnpjInvalido`."""
	try:
		return validar_cnpj(texto)
	except ValidacaoFiscalError as erro:
		raise CnpjInvalido(str(erro)) from erro


def url_do_provedor(modelo, cnpj) -> str:
	"""A URL da consulta, a partir do modelo configurado. O modelo tem de ter `{cnpj}` uma vez e ser http(s) sem credencial."""
	texto = str(modelo or "").strip()

	if texto.count("{cnpj}") != 1:
		raise ModeloInvalido(f"O modelo de URL precisa ter {{cnpj}} exatamente uma vez: {modelo!r}")

	partes = urlsplit(texto.replace("{cnpj}", "00000000000000"))

	if partes.scheme not in ("http", "https") or not partes.hostname or "@" in partes.netloc:
		raise ModeloInvalido(f"O modelo de URL deve ser http(s) com servidor e sem usuário/senha: {modelo!r}")

	return texto.replace("{cnpj}", normalizar_cnpj(cnpj))


def _carregar(corpo):
	if isinstance(corpo, bytes | bytearray):
		corpo = bytes(corpo).decode("utf-8", errors="replace")

	if not isinstance(corpo, str):
		return corpo

	try:
		return json.loads(corpo)
	except ValueError as erro:
		raise RespostaCnpjInvalida(
			"A resposta não é JSON — o provedor devolveu uma página de erro?"
		) from erro


def _texto(dados: dict, chave: str) -> str:
	return " ".join(str(dados.get(chave) or "").split())


def _logico(dados: dict, chave: str):
	valor = dados.get(chave)

	if isinstance(valor, bool):
		return valor

	if isinstance(valor, str):
		minusculo = valor.strip().lower()

		if minusculo in ("s", "sim", "true"):
			return True

		if minusculo in ("n", "nao", "não", "false"):
			return False

	return None


def _codigo(valor) -> int | None:
	texto = str(valor if valor is not None else "").strip()

	return int(texto) if texto.isdigit() else None


def _logradouro(tipo: str, nome: str) -> str:
	if not nome:
		return ""

	if tipo and not re.search(rf"\b{re.escape(tipo)}\b", nome, re.IGNORECASE):
		return f"{tipo} {nome}"

	return nome


def _cep(valor) -> str:
	digitos = "".join(ch for ch in str(valor or "") if ch.isdigit())

	if not digitos or len(digitos) > 8:
		return ""

	digitos = digitos.zfill(8)

	return f"{digitos[:5]}-{digitos[5:]}"


def _ibge(valor) -> str:
	texto = str(valor if valor is not None else "").strip()

	return texto if len(texto) == 7 and texto.isdigit() else ""


def _cadastro(dados: dict) -> CadastroCnpj:
	if not isinstance(dados, dict) or not _texto(dados, "razao_social"):
		raise RespostaCnpjInvalida("Resposta sem razão social — não é um cadastro de CNPJ")

	cnpj = "".join(ch for ch in str(dados.get("cnpj") or "") if ch.isalnum()).upper()

	if len(cnpj) != 14:
		raise RespostaCnpjInvalida(f"CNPJ da resposta malformado: {dados.get('cnpj')!r}")

	situacao = _codigo(dados.get("situacao_cadastral"))
	matriz = _codigo(dados.get("identificador_matriz_filial"))

	return CadastroCnpj(
		cnpj=cnpj,
		razao_social=_texto(dados, "razao_social"),
		nome_fantasia=_texto(dados, "nome_fantasia"),
		situacao=situacao,
		situacao_descricao=_texto(dados, "descricao_situacao_cadastral") or SITUACOES.get(situacao, ""),
		data_situacao=_texto(dados, "data_situacao_cadastral"),
		motivo_situacao=_texto(dados, "descricao_motivo_situacao_cadastral"),
		cnae_codigo=_texto(dados, "cnae_fiscal"),
		cnae_descricao=_texto(dados, "cnae_fiscal_descricao"),
		natureza_juridica=_texto(dados, "natureza_juridica"),
		porte=_texto(dados, "porte"),
		optante_simples=_logico(dados, "opcao_pelo_simples"),
		mei=_logico(dados, "opcao_pelo_mei"),
		matriz=None if matriz is None else matriz == 1,
		endereco=EnderecoCnpj(
			logradouro=_logradouro(
				_texto(dados, "descricao_tipo_de_logradouro"), _texto(dados, "logradouro")
			),
			numero=_texto(dados, "numero"),
			complemento=_texto(dados, "complemento"),
			bairro=_texto(dados, "bairro"),
			cep=_cep(dados.get("cep")),
			municipio=_texto(dados, "municipio"),
			uf=_texto(dados, "uf").upper(),
			codigo_municipio_ibge=_ibge(dados.get(CHAVE_IBGE_DO_PROVEDOR)),
		),
	)


def interpretar_resposta(status: int, corpo) -> CadastroCnpj | None:
	"""O cadastro da resposta, ou `None` quando o CNPJ não existe na base (404).

	400 é resposta inválida (o CNPJ já foi conferido antes de sair), e qualquer outro status — limite de uso, erro de
	servidor — é `ProvedorIndisponivel`: não diz nada sobre o CNPJ, e o chamador tenta o próximo provedor."""
	if status == 404:
		return None

	if status == 400:
		raise RespostaCnpjInvalida("O provedor recusou o CNPJ como malformado (HTTP 400)")

	if status != 200:
		raise ProvedorIndisponivel(f"Provedor respondeu HTTP {status}")

	return _cadastro(_carregar(corpo))


def tem_cpf_no_nome(razao_social) -> bool:
	"""Nome que termina em 11 dígitos ou traz um CPF formatado: o formato antigo do MEI, com dado pessoal."""
	texto = " ".join(str(razao_social or "").split())

	return bool(_CPF_NO_FIM.search(texto) or _CPF_FORMATADO.search(texto))


def razao_social_sugerida(cadastro: CadastroCnpj) -> str:
	"""A razão social como a Receita registra, ou vazio quando ela traz dado pessoal (CPF) que não vai ao cadastro."""
	return "" if tem_cpf_no_nome(cadastro.razao_social) else cadastro.razao_social


def _vazio(valor) -> bool:
	return not str(valor or "").strip()


def lacunas_da_parte(doctype: str, atual: dict, cadastro: CadastroCnpj) -> dict[str, str]:
	"""O que cabe preencher no cadastro da parte: só campo **vazio**, nunca o já informado."""
	campo = CAMPO_NOME_POR_DOCTYPE.get(doctype)
	nome = razao_social_sugerida(cadastro)

	if not campo or not nome or not _vazio((atual or {}).get(campo)):
		return {}

	return {campo: nome}


def data_br(data: str) -> str:
	"""`2005-11-03` → `03/11/2005`; o que não for uma data ISO volta como veio."""
	partes = str(data or "").split("-")

	return f"{partes[2]}/{partes[1]}/{partes[0]}" if len(partes) == 3 and all(partes) else str(data or "")


def aviso_de_situacao(cadastro: CadastroCnpj) -> str:
	"""Vazio quando a situação é ATIVA; senão o que a Receita diz, com a data e o motivo."""
	if cadastro.ativo:
		return ""

	if cadastro.situacao is None and not cadastro.situacao_descricao:
		return "Situação cadastral não informada pelo provedor — confira na Receita antes de emitir documento fiscal."

	texto = f"Situação cadastral na Receita: {cadastro.situacao_descricao or cadastro.situacao}"

	if cadastro.data_situacao:
		texto += f" desde {data_br(cadastro.data_situacao)}"

	if cadastro.motivo_situacao and cadastro.motivo_situacao.upper() != "SEM MOTIVO":
		texto += f" (motivo: {cadastro.motivo_situacao})"

	return texto + ". Confira antes de emitir documento fiscal para este CNPJ."


def campos_do_endereco(cadastro: CadastroCnpj) -> dict[str, str]:
	"""O endereço do estabelecimento nos nomes de campo do `Address`, sem o que a resposta não trouxe.

	Sem logradouro não há endereço a criar. Aqui o `complemento` **é** do estabelecimento (diferente do `complemento`
	do ViaCEP, que descreve a faixa do CEP), e por isso entra em `address_line2`."""
	e = cadastro.endereco

	if not e.logradouro:
		return {}

	todos = {
		"address_line1": e.logradouro,
		"address_line2": e.complemento,
		"br_numero_endereco": e.numero,
		"br_bairro": e.bairro,
		"city": e.municipio,
		"state": e.uf,
		"pincode": e.cep,
		"br_codigo_municipio_ibge": e.codigo_municipio_ibge,
	}

	return {**{campo: valor for campo, valor in todos.items() if valor}, "country": "Brazil"}


def _sim_nao(valor, sim: str, nao: str) -> str:
	return "" if valor is None else (sim if valor else nao)


def resumo(cadastro: CadastroCnpj) -> dict:
	"""O que a tela mostra ao usuário. Nada de sócio, e-mail ou telefone."""
	e = cadastro.endereco
	cnae = " — ".join(p for p in (cadastro.cnae_codigo, cadastro.cnae_descricao) if p)
	local = ", ".join(p for p in (e.logradouro, e.numero) if p)
	cidade = "/".join(p for p in (e.municipio, e.uf) if p)

	return {
		"razao_social": cadastro.razao_social,
		"nome_fantasia": cadastro.nome_fantasia,
		"situacao": cadastro.situacao_descricao,
		"data_situacao": data_br(cadastro.data_situacao),
		"ativo": cadastro.ativo,
		"cnae": cnae,
		"natureza_juridica": cadastro.natureza_juridica,
		"porte": cadastro.porte,
		"simples": _sim_nao(cadastro.optante_simples, "Optante", "Não optante"),
		"mei": _sim_nao(cadastro.mei, "MEI", "Não é MEI"),
		"matriz_filial": _sim_nao(cadastro.matriz, "Matriz", "Filial"),
		"endereco": " — ".join(p for p in (local, e.bairro, cidade, e.cep) if p),
		"aviso_de_defasagem": AVISO_DE_DEFASAGEM,
	}
