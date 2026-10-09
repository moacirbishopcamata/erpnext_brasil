# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Aplicação das regras fiscais brasileiras aos DocTypes de parte.

Esta é a camada de tradução: as funções puras de `validators` não conhecem o Frappe,
e aqui o resultado delas vira `frappe.throw`. A separação existe para que a regra
fiscal seja testável sem site e sem banco.

A validação roda apenas quando a Company (ou o país do sistema) é o Brasil. Uma
instalação multiempresa com filial no exterior não deve ter o CNPJ exigido de um
fornecedor estrangeiro.
"""

import frappe
from frappe import _

from erpnext_brasil.fiscal.codigos.municipio import (
	ExcecoesInvalidas,
	MunicipioInvalido,
	ler_excecoes,
	validar_municipio,
)
from erpnext_brasil.fiscal.codigos_de_erro import (
	CADASTRO_CODIGO_DE_MUNICIPIO_INVALIDO,
	CADASTRO_CPF_CNPJ_INVALIDO,
	CADASTRO_INSCRICAO_ESTADUAL_INVALIDA,
	CADASTRO_NCM_INVALIDO,
	formatar,
)
from erpnext_brasil.fiscal.inscricao_estadual import validar_inscricao_estadual
from erpnext_brasil.fiscal.ufs import resolver_uf
from erpnext_brasil.fiscal.validators import (
	ValidacaoFiscalError,
	formatar_cnpj,
	formatar_cpf,
	limpar,
	validar_cpf_cnpj,
)


def _pais_e_brasil() -> bool:
	"""Indica se o contexto atual é brasileiro.

	Usa a Company em foco quando houver; do contrário, o país das configurações.
	"""
	empresa = frappe.local.flags.company or frappe.defaults.get_user_default("Company")

	if empresa:
		return frappe.get_cached_value("Company", empresa, "country") == "Brazil"

	return frappe.get_system_settings("country") == "Brazil"


pais_e_brasil = _pais_e_brasil
"""Nome público para outros módulos de integração (ex.: `valoracao_estoque`), sem importar o privado."""


def validar_tax_id(doc, method=None):
	"""Valida o CPF/CNPJ em `tax_id` e o normaliza para o formato com máscara.

	Ligado via `doc_events` para Company, Customer e Supplier. Campo vazio é aceito:
	obrigatoriedade é decisão de configuração do DocType, não desta validação.
	"""
	if not doc.get("tax_id") or not _pais_e_brasil():
		return

	try:
		limpo = validar_cpf_cnpj(doc.tax_id)
	except ValidacaoFiscalError as e:
		frappe.throw(
			formatar(
				CADASTRO_CPF_CNPJ_INVALIDO,
				_("CPF/CNPJ inválido em {0}: {1}").format(doc.doctype, str(e)),
			),
			title=_("Documento fiscal inválido"),
		)
		return

	# Normaliza na gravação para que buscas e comparações não dependam da máscara
	# que o usuário digitou. O valor canônico é sempre o formatado.
	doc.tax_id = formatar_cpf(limpo) if len(limpo) == 11 else formatar_cnpj(limpo)


def uf_da_parte(doc) -> str | None:
	"""Descobre a UF da parte a partir do endereço padrão dela.

	A Inscrição Estadual mora na parte, mas a UF que define o algoritmo mora no
	Address — e `state` no ERPNext é texto livre. Quando a UF não puder ser afirmada,
	devolve None e a validação da IE é dispensada, em vez de arriscar rejeitar um
	cadastro legítimo.

	Função pública (não mais `_uf_da_parte`) desde que `integracao/cfop_sugestao.py`
	passou a precisar da mesma UF para decidir `mesmo_estado` do CFOP — segunda
	chamadora real é o que justifica generalizar, não suposição de uso futuro.
	"""
	from frappe.contacts.doctype.address.address import get_default_address

	if doc.doctype == "Company":
		estado = frappe.db.get_value(
			"Address", {"is_your_company_address": 1, "link_name": doc.name}, "state"
		)
	else:
		endereco = get_default_address(doc.doctype, doc.name) if doc.name else None
		estado = frappe.db.get_value("Address", endereco, "state") if endereco else None

	return resolver_uf(estado)


def validar_ie(doc, method=None):
	"""Valida a Inscrição Estadual quando a UF da parte puder ser determinada."""
	ie = doc.get("br_inscricao_estadual")

	if not ie or not _pais_e_brasil():
		return

	uf = uf_da_parte(doc)

	if not uf:
		return

	try:
		doc.br_inscricao_estadual = validar_inscricao_estadual(ie, uf)
	except ValidacaoFiscalError as e:
		frappe.throw(
			formatar(
				CADASTRO_INSCRICAO_ESTADUAL_INVALIDA,
				_("Inscrição Estadual inválida: {0}").format(str(e)),
			),
			title=_("Documento fiscal inválido"),
		)


CHAVE_EXCECOES_DO_DIGITO = "brasil_municipios_excecao_dv"
"""Códigos de município que o administrador libera da conferência do dígito verificador, em `site_config`.

Existe porque o IBGE já atribuiu 9 códigos fora da regra (`fiscal/codigos/municipio.py`) e pode atribuir
outros: sem esta saída, um município real novo travaria o cadastro até uma nova versão do app.
"""


def _excecoes_do_administrador() -> frozenset[str]:
	"""A lista configurada. Valor inválido cai em "nenhuma exceção" **e fica registrado** — travar toda gravação
	de endereço por um erro de digitação em `site_config` seria pior do que o erro."""
	try:
		return ler_excecoes(frappe.conf.get(CHAVE_EXCECOES_DO_DIGITO))
	except ExcecoesInvalidas as erro:
		frappe.log_error(
			title="Município: configuração inválida", message=f"{CHAVE_EXCECOES_DO_DIGITO}: {erro}"
		)

		return frozenset()


def validar_codigo_municipio(doc, method=None):
	"""Valida o código IBGE do município em Address: formato, UF do endereço e dígito verificador.

	A regra e as exceções estão em `fiscal/codigos/municipio.py`, conferidas contra a lista oficial do IBGE.
	"""
	codigo = doc.get("br_codigo_municipio_ibge")

	if not codigo or not _pais_e_brasil():
		return

	limpo = limpar(codigo)

	try:
		validar_municipio(limpo, doc.get("state"), _excecoes_do_administrador())
	except MunicipioInvalido as erro:
		frappe.throw(
			formatar(CADASTRO_CODIGO_DE_MUNICIPIO_INVALIDO, str(erro)),
			title=_("Documento fiscal inválido"),
		)

	doc.br_codigo_municipio_ibge = limpo


def validar_ncm(doc, method=None):
	"""Valida o NCM do Item (8 dígitos)."""
	ncm = doc.get("br_ncm")

	if not ncm or not _pais_e_brasil():
		return

	limpo = limpar(ncm)

	if not limpo.isdigit() or len(limpo) != 8:
		frappe.throw(
			formatar(
				CADASTRO_NCM_INVALIDO,
				_("NCM deve ter 8 dígitos numéricos, recebido {0}").format(ncm),
			),
			title=_("Documento fiscal inválido"),
		)

	doc.br_ncm = limpo
