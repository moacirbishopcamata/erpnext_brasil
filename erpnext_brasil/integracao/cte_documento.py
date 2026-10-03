# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Mapeia uma `Sales Invoice` de transporte para a árvore do CT-e.

Fecha o item 2.1 do change `fechar-laco-cte-mdfe`: a camada entre o documento real do ERPNext
e a montagem pura de `fiscal/cte_montagem.py`.

O que este módulo faz — e o que não faz
-----------------------------------------
Só **lê o cadastro e traduz** para `DadosCte`: `Company` → emitente, `Customer` → remetente,
destinatário e tomador, campos `br_*` da fatura → prestação, carga e ICMS. Toda a regra do
leiaute (ordem dos grupos, cálculo do ICMS, o que se recusa) mora em `fiscal/cte_montagem.py`,
onde `tests/test_cte_montagem.py` a trava sem bench. A divisão existe porque este módulo importa
`frappe` e a suíte pura não o alcança — a primeira versão tinha a regra aqui dentro, com `cNF`
fixo, `infCTeNorm` vazio e um `imp` de mentira, e nada podia pegá-los.

O que **se recusa** a inventar
-------------------------------
Cada ausência levanta `DadosInsuficientes` dizendo qual dado falta e **em qual cadastro**:
remetente, destinatário, tomador, CST/alíquota do ICMS, carga, RNTRC, CFOP, municípios. O
tomador não é assumido: quem paga o frete vem de `br_tomador_cte`, e "Outros" usa o cliente da
fatura com cadastro completo.

O número é alocado **aqui, mas só depois** de a montagem de prova validar tudo
(`montar_cte_alocando_numero`): a série vem de `br_serie_cte` e `numero_do_documento` reaproveita
o número de uma reemissão. A data de emissão é o instante da chamada, com o fuso do
sistema — o XSD recusa `dhEmi` sem deslocamento.

Estado de verificação: camada Frappe, **não** exercitada contra bench real (lacuna de
`docs/gaps.md`, seção 2). A árvore que ela produz foi validada contra o `cte_v4.00.xsd` oficial
nos cenários de ICMS 00/20/45/90/SN, só sem a assinatura.
"""

from datetime import datetime
from decimal import Decimal

import frappe

from erpnext_brasil.fiscal.codigos_de_erro import (
	DOCUMENTO_CTE_DADO_INVALIDO,
	DOCUMENTO_CTE_DADO_OBRIGATORIO_AUSENTE,
)
from erpnext_brasil.fiscal.cte import CteInvalido, TomadorOutros
from erpnext_brasil.fiscal.cte_montagem import (
	CargaCte,
	DadosCte,
	EmitenteCte,
	IcmsCte,
	ParteCte,
	QuantidadeCarga,
	montar_cte_alocando_numero,
)
from erpnext_brasil.integracao.configuracao_fiscal import agora_da_emissao, serie_padrao
from erpnext_brasil.integracao.nfe_documento import (
	DadosInsuficientes,
	_endereco_vinculado,
	_exigir,
	_grupo_endereco,
	_regime_tributario,
)
from erpnext_brasil.integracao.numeracao_fiscal import numero_do_documento
from erpnext_brasil.setup.campos_documento import (
	MODAL_CTE_POR_ROTULO,
	TIPO_SERVICO_CTE_POR_ROTULO,
	TOMADOR_CTE_POR_ROTULO,
	UNIDADE_CARGA_POR_ROTULO,
)
from erpnext_brasil.setup.custom_fields import INDICADOR_IE_POR_ROTULO

__all__ = ["DadosInsuficientes", "montar_cte_do_documento"]

MODELO_CTE = "57"
CAMPO_NUMERO = "br_numero_cte"


def _traduzir(rotulo, tabela: dict, campo: str, onde: str) -> str:
	texto = _exigir(rotulo, campo, onde)

	if texto not in tabela:
		raise CteInvalido(
			f"{campo} {texto!r} em {onde} não é um dos valores {sorted(tabela)}",
			campo,
			DOCUMENTO_CTE_DADO_INVALIDO,
		)

	return tabela[texto]


def _decimal(valor, campo: str, onde: str) -> Decimal:
	return Decimal(str(_exigir(valor, campo, onde)))


def _emitente(company: str) -> EmitenteCte:
	"""O emitente é a transportadora — a `Company` que emite a fatura de frete."""
	empresa = frappe.get_cached_doc("Company", company)
	onde = f"Company {company}"

	return EmitenteCte(
		cnpj=_exigir(empresa.get("tax_id"), "CNPJ do emitente", onde),
		nome=_exigir(empresa.get("company_name"), "razão social", onde),
		inscricao_estadual=_exigir(empresa.get("br_inscricao_estadual"), "inscrição estadual", onde),
		regime_tributario=_regime_tributario(empresa, company),
		endereco=_grupo_endereco(_endereco_vinculado("Company", company), f"endereço da {onde}"),
	)


def _cliente(nome: str, papel: str) -> tuple[ParteCte, str]:
	"""A parte (remetente/destinatário) e o `indIEToma` dela, caso seja o tomador."""
	parte = frappe.get_cached_doc("Customer", nome)
	onde = f"Customer {nome} ({papel})"
	endereco = _grupo_endereco(_endereco_vinculado("Customer", nome), f"endereço do {onde}")
	indicador = _traduzir(parte.get("br_indicador_ie"), INDICADOR_IE_POR_ROTULO, "indicador de IE", onde)

	return (
		ParteCte(
			documento=_exigir(parte.get("tax_id"), "CNPJ/CPF", onde),
			nome=_exigir(parte.get("customer_name"), "razão social", onde),
			endereco=endereco,
			inscricao_estadual=str(parte.get("br_inscricao_estadual") or ""),
		),
		indicador,
	)


def _tomador(doc, indicador_rem: str, indicador_dest: str):
	"""Papel, cadastro de `toma4` (só em "Outros") e `indIEToma` do tomador escolhido."""
	onde = f"{doc.doctype} {doc.name}"
	papel = _traduzir(doc.get("br_tomador_cte"), TOMADOR_CTE_POR_ROTULO, "tomador do serviço", onde)

	if papel == "0":
		return papel, None, indicador_rem

	if papel == "3":
		return papel, None, indicador_dest

	pagador, indicador = _cliente(_exigir(doc.get("customer"), "cliente", onde), "tomador")
	outros = TomadorOutros(
		nome=pagador.nome,
		cnpj_cpf=pagador.documento,
		inscricao_estadual=pagador.inscricao_estadual,
		endereco=pagador.endereco,
	)

	return papel, outros, indicador


def _carga(doc) -> CargaCte:
	onde = f"{doc.doctype} {doc.name}"
	valor = doc.get("br_valor_carga")

	return CargaCte(
		produto_predominante=_exigir(doc.get("br_produto_predominante"), "produto predominante", onde),
		quantidades=(
			QuantidadeCarga(
				unidade=_traduzir(
					doc.get("br_unidade_carga"), UNIDADE_CARGA_POR_ROTULO, "unidade da carga", onde
				),
				tipo_medida=_exigir(doc.get("br_tipo_medida_carga"), "tipo da medida da carga", onde),
				quantidade=_decimal(doc.get("br_quantidade_carga"), "quantidade da carga", onde),
			),
		),
		valor=Decimal(str(valor)) if valor else None,
	)


def _icms(doc) -> IcmsCte:
	onde = f"{doc.doctype} {doc.name}"
	cst = _exigir(doc.get("br_cst_icms_cte"), "CST do ICMS do CT-e", onde)
	sem_imposto = cst in {"40", "41", "51", "SN"}

	return IcmsCte(
		cst=cst,
		aliquota=Decimal(0)
		if sem_imposto
		else _decimal(doc.get("br_aliquota_icms_cte"), "alíquota do ICMS", onde),
		reducao_base=Decimal(str(doc.get("br_reducao_base_icms_cte") or 0)),
	)


def _municipio(doc, prefixo: str, rotulo: str) -> tuple[str, str, str]:
	onde = f"{doc.doctype} {doc.name}"

	return (
		_exigir(doc.get(f"br_municipio_{prefixo}"), f"município de {rotulo}", onde),
		_exigir(doc.get(f"br_municipio_{prefixo}_nome"), f"nome do município de {rotulo}", onde),
		_exigir(doc.get(f"br_uf_{prefixo}"), f"UF de {rotulo}", onde),
	)


def _montar(doc, ambiente: str, agora: datetime | None) -> tuple[dict, str]:
	"""A árvore `CTe` **não assinada** e a chave de acesso, a partir de uma fatura de transporte.

	A série vem de `br_serie_cte` da `Company` e o número é alocado aqui, **depois** de todo o
	cadastro validar — uma recusa por dado faltante nunca consome número da série. Reemitir uma
	fatura que já tem `br_numero_cte` reaproveita o número. `ambiente` é `"producao"` ou
	`"homologacao"`. Chamar dentro da transação do documento (a alocação não faz `commit`).
	"""
	onde = f"{doc.doctype} {doc.name}"
	remetente, indicador_rem = _cliente(
		_exigir(doc.get("br_remetente_cte"), "remetente da carga", onde), "remetente"
	)
	destinatario, indicador_dest = _cliente(
		_exigir(doc.get("br_destinatario_cte"), "destinatário da carga", onde), "destinatário"
	)
	papel, outros, indicador = _tomador(doc, indicador_rem, indicador_dest)
	company = _exigir(doc.get("company"), "empresa", onde)
	empresa = frappe.get_cached_doc("Company", company)
	serie = _exigir(serie_padrao(company, MODELO_CTE), "série do CT-e (br_serie_cte)", f"Company {company}")

	dados = DadosCte(
		emitente=_emitente(company),
		remetente=remetente,
		destinatario=destinatario,
		tomador_papel=papel,
		tomador_outros=outros,
		indicador_ie_tomador=indicador,
		cfop=_exigir(doc.get("br_cfop_transporte"), "CFOP do CT-e", onde),
		natureza_operacao=_exigir(doc.get("br_natureza_transporte"), "natureza da operação", onde),
		serie=serie,
		emissao=agora or agora_da_emissao(),
		ambiente="1" if ambiente == "producao" else "2",
		modal=_traduzir(doc.get("br_modal_cte"), MODAL_CTE_POR_ROTULO, "modal do CT-e", onde),
		tipo_servico=_traduzir(
			doc.get("br_tipo_servico_cte"), TIPO_SERVICO_CTE_POR_ROTULO, "tipo de serviço", onde
		),
		municipio_inicio=_municipio(doc, "inicio", "início"),
		municipio_fim=_municipio(doc, "fim", "fim"),
		valor_prestacao=_decimal(doc.get("grand_total"), "valor total da prestação", onde),
		icms=_icms(doc),
		carga=_carga(doc),
		rntrc=_exigir(empresa.get("br_rntrc"), "RNTRC", f"Company {company}"),
	)

	return montar_cte_alocando_numero(
		dados, lambda: numero_do_documento(doc, MODELO_CTE, serie, CAMPO_NUMERO)
	)


def montar_cte_do_documento(doc, ambiente: str, agora: datetime | None = None) -> tuple[dict, str]:
	"""A árvore `CTe` **não assinada** e a chave de acesso, a partir de uma fatura de transporte.

	Toda recusa sai como `CteInvalido`, com `codigo` (`fiscal/codigos_de_erro.py`) e `campo`: o
	`DadosInsuficientes` dos leitores de cadastro vira "dado obrigatório ausente" (1206), e a
	montagem pura já levanta o seu com 1206 ou 1207. Quem exibe usa `erro.mensagem_com_codigo`.

	⚠️ Um regime tributário que não tem CRT correspondente também chega aqui como
	`DadosInsuficientes` (leitor compartilhado com a NF-e) e sai como 1206, embora seja, a rigor,
	um valor a corrigir. A mensagem nomeia o problema; separar os dois pede mexer no leitor da NF-e.

	Chamar dentro da transação do documento (a alocação do número não faz `commit`).
	"""
	try:
		return _montar(doc, ambiente, agora)
	except DadosInsuficientes as erro:
		raise CteInvalido(str(erro), "", DOCUMENTO_CTE_DADO_OBRIGATORIO_AUSENTE) from erro
