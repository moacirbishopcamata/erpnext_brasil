# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Lê os documentos do site e produz o Bloco C do EFD-ICMS/IPI.

Última peça entre os blocos implementados e um arquivo real: `contabil/efd_arquivo.py`
monta o arquivo, `contabil/efd_bloco_c.py` sabe o leiaute, e faltava quem lesse
`Sales Invoice` e `Purchase Invoice` do período e produzisse os registros.

O `C190` é agrupamento, não cópia de linha
--------------------------------------------------
O erro natural é emitir um `C190` por item, que é como o documento está estruturado no
ERPNext. O leiaute pede o contrário: **um registro por combinação distinta de
`CST_ICMS` + `CFOP` + `ALIQ_ICMS`**, com os valores somados. Uma nota com dez itens de
mesma tributação vira **um** `C190`, não dez.

Isso importa porque a validação do `C100` é sobre a soma: `VL_BC_ICMS` do documento tem
de bater com a soma dos analíticos. Emitir um por item bate por acaso; agrupar errado não
bate nunca — e o PVA só diz que a soma divergiu.

Entrada e saída não são o mesmo documento
-------------------------------------------------
`Sales Invoice` é saída (`IND_OPER = 1`), `Purchase Invoice` é entrada (`IND_OPER = 0`), e
a diferença não para aí: na entrada o **emitente é o fornecedor**, então `IND_EMIT` é `1`
(terceiros) e o `COD_PART` aponta para quem emitiu, não para quem recebeu.

O que este módulo **não** faz
-------------------------------------
- **Não inventa `COD_SIT`.** Documento cancelado no ERPNext (`docstatus = 2`) vira
  `COD_SIT = "02"`; o resto é `"00"` (regular). As demais situações do leiaute — denegado,
  extemporâneo, regime especial — dependem de fato que o ERPNext não registra, e supô-las
  seria declarar ao Fisco algo que ninguém disse.
- **Não cobre `C170`.** Para NF-e de emissão própria o guia dispensa (ver
  `docs/sped-fiscal.md`), e é o caso da esmagadora maioria.
- **Não decide o período.** Recebe as datas de quem chama.

Estado de verificação: camada Frappe, **não** exercitada contra bench real.
"""

from collections import defaultdict
from decimal import Decimal

import frappe

from erpnext_brasil.contabil.efd_bloco_c import (
	EMISSAO_PROPRIA,
	EMISSAO_TERCEIROS,
	MODELO_NFE,
	OPERACAO_ENTRADA,
	OPERACAO_SAIDA,
	DocumentoFiscal,
	RegistroAnalitico,
	montar_c001,
	montar_c100,
	montar_c190,
	montar_c990,
)
from erpnext_brasil.integracao.configuracao_fiscal import serie_padrao

__all__ = ["SITUACAO_CANCELADO", "SITUACAO_REGULAR", "bloco_c_do_periodo"]

ZERO = Decimal("0.00")

SITUACAO_REGULAR = "00"
SITUACAO_CANCELADO = "02"

# `Sales Invoice` é saída e de emissão própria; `Purchase Invoice` é entrada, e quem
# emitiu foi o fornecedor — daí `IND_EMIT` diferente e o participante ser outro campo.
_ORIGENS = {
	"Sales Invoice": (OPERACAO_SAIDA, EMISSAO_PROPRIA, "customer"),
	"Purchase Invoice": (OPERACAO_ENTRADA, EMISSAO_TERCEIROS, "supplier"),
}


def _decimal(valor) -> Decimal:
	if valor in (None, ""):
		return ZERO

	return Decimal(str(valor))


def _data_sped(valor) -> str:
	"""`ddmmaaaa`, o formato que o registro espera como texto já pronto."""
	return frappe.utils.getdate(valor).strftime("%d%m%Y")


def _documento_fiscal(doc, doctype: str, serie: str) -> DocumentoFiscal:
	operacao, emissao, campo_parte = _ORIGENS[doctype]

	return DocumentoFiscal(
		operacao=operacao,
		emissao=emissao,
		codigo_modelo=MODELO_NFE,
		codigo_situacao=SITUACAO_CANCELADO if doc.docstatus == 2 else SITUACAO_REGULAR,
		numero=str(doc.get("br_numero_nfe") or "").strip() or doc.name,
		serie=serie,
		data_emissao=_data_sped(doc.posting_date),
		valor_documento=_decimal(doc.grand_total),
		# `IND_PGTO` e `IND_FRT` não têm padrão que se possa assumir; vêm dos campos que
		# `transporte_pagamento` também usa, e o registro recusa valor fora do domínio.
		indicador_pagamento="1" if doc.get("payment_schedule") else "0",
		indicador_frete=_indicador_frete(doc),
		codigo_participante=doc.get(campo_parte) or "",
		chave_acesso=str(doc.get("br_chave_acesso") or "").strip(),
		valor_mercadorias=_decimal(doc.net_total),
		valor_desconto=_decimal(doc.get("discount_amount")),
		valor_bc_icms=_somar_linhas(doc, "br_base_icms"),
		valor_icms=_somar_linhas(doc, "br_valor_icms"),
		valor_ipi=_somar_linhas(doc, "br_valor_ipi"),
		valor_pis=_somar_linhas(doc, "br_valor_pis"),
		valor_cofins=_somar_linhas(doc, "br_valor_cofins"),
	)


def _indicador_frete(doc) -> str:
	"""`IND_FRT` do `C100` a partir da modalidade escolhida no documento.

	Sem modalidade informada vale `"9"` — **e aqui isso é diferente da NF-e**. No XML,
	`modFrete="9"` é afirmação e o projeto se recusa a assumi-la. Na escrituração o
	documento **já existe**: ou tem transporte declarado, ou não tem, e o `C100` não admite
	o campo vazio. Declarar "sem ocorrência" é a leitura fiel do que o documento diz.
	"""
	from erpnext_brasil.setup.custom_fields import MODALIDADES_FRETE

	return MODALIDADES_FRETE.get((doc.get("br_modalidade_frete") or "").strip(), "9")


def _somar_linhas(doc, campo: str) -> Decimal:
	return sum((_decimal(linha.get(campo)) for linha in doc.get("items", [])), ZERO)


def _cst_de_tres_digitos(linha) -> str:
	"""`CST_ICMS` do `C190`: origem da mercadoria + CST, três dígitos.

	    O usuário preenche os dois em telas diferentes — a origem é atributo do `Item` (não
	    muda de nota para nota), o CST é da linha (a mesma mercadoria pode ser tributada
	    diferente conforme a operação). Juntá-los aqui é o que evita pedir a mesma informação
	    duas vezes, ou pior, guardá-la em dois lugares que divergem.

	Sem CST na linha não há analítico possível — quem chama pula a linha, porque o `C190`
	não admite o campo vazio e inventar um valor seria declarar tributação que ninguém
	escolheu.
	"""
	cst = str(linha.get("br_cst_icms") or "").strip()

	if not cst:
		return ""

	origem = str(linha.get("br_origem_mercadoria") or "0").strip()[:1] or "0"

	return f"{origem}{cst}"


def _analiticos(doc) -> list[RegistroAnalitico]:
	"""Agrupa os itens por `CST_ICMS` + `CFOP` + `ALIQ_ICMS` — ver docstring do módulo."""
	grupos: dict[tuple, dict] = defaultdict(
		lambda: {"operacao": ZERO, "base": ZERO, "icms": ZERO, "ipi": ZERO}
	)

	for linha in doc.get("items", []):
		# `br_cst_icms` guarda dois dígitos (o domínio do Select); o `C190` exige três,
		# com a origem da mercadoria na frente. Concatenar aqui é o que liga os dois
		# campos que o usuário preenche em telas diferentes — item e linha.
		cst = _cst_de_tres_digitos(linha)
		cfop = str(linha.get("br_cfop_sugerido") or "").strip()
		aliquota = _decimal(linha.get("br_aliquota_icms"))

		# Linha sem CFOP ou sem CST não vira analítico: o `C190` não admite os campos
		# vazios, e preenchê-los por conta própria declararia ao Fisco uma tributação que
		# ninguém escolheu. A linha aparece no total do `C100` e falta no analítico — o
		# PVA acusa a divergência, que é o comportamento certo: melhor a recusa explícita
		# do que um arquivo aceito descrevendo outra operação.
		if not cfop or not cst:
			continue

		chave = (cst, cfop, aliquota)
		acumulado = grupos[chave]
		acumulado["operacao"] += _decimal(linha.get("net_amount") or linha.get("amount"))
		acumulado["base"] += _decimal(linha.get("br_base_icms"))
		acumulado["icms"] += _decimal(linha.get("br_valor_icms"))
		acumulado["ipi"] += _decimal(linha.get("br_valor_ipi"))

	return [
		RegistroAnalitico(
			cst_icms=cst,
			cfop=cfop,
			aliquota_icms=aliquota,
			valor_operacao=valores["operacao"],
			valor_bc_icms=valores["base"],
			valor_icms=valores["icms"],
			valor_ipi=valores["ipi"],
		)
		for (cst, cfop, aliquota), valores in sorted(grupos.items(), key=lambda p: p[0][:2])
	]


def bloco_c_do_periodo(company: str, data_inicial: str, data_final: str) -> list[dict]:
	"""O Bloco C inteiro para o período, pronto para `efd_arquivo.montar_arquivo_efd`.

	Inclui documentos **cancelados** (`docstatus = 2`): o leiaute os exige com
	`COD_SIT = "02"`, porque o número foi consumido e a numeração precisa fechar sem
	lacuna. Omiti-los produziria buraco que o Fisco cobra.
	"""
	linhas: list[dict] = []

	# A série é da empresa, não do documento: um mesmo estabelecimento emite toda a NF-e
	# na mesma série, e o número é que anda. Ler uma vez evita uma consulta por documento.
	serie = serie_padrao(company, MODELO_NFE)

	for doctype in _ORIGENS:
		nomes = frappe.get_all(
			doctype,
			filters={
				"company": company,
				"posting_date": ["between", [data_inicial, data_final]],
				"docstatus": ["in", [1, 2]],
			},
			pluck="name",
			order_by="posting_date, name",
		)

		for nome in nomes:
			doc = frappe.get_doc(doctype, nome)
			linhas.append(montar_c100(_documento_fiscal(doc, doctype, serie)))

			# Documento cancelado não tem registro filho — a regra é a mesma do Bloco D.
			if doc.docstatus == 2:
				continue

			linhas.extend(montar_c190(analitico) for analitico in _analiticos(doc))

	if not linhas:
		return [montar_c001(tem_dados=False), montar_c990(2)]

	completo = [montar_c001(tem_dados=True), *linhas]

	return [*completo, montar_c990(len(completo) + 1)]
