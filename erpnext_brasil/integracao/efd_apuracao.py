# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Apura o ICMS do período a partir dos documentos e produz o Bloco E do EFD.

O Bloco E é o único que **não pode ser vazio**: `montar_e001` aceita apenas
`IND_MOV = "0"`, e `E100`/`E110` são sempre obrigatórios (ver `contabil/efd_icms_ipi.py`).
Um arquivo sem ele é recusado, o que torna esta camada mais urgente que as dos blocos
D/H/K — sem ela, nenhum EFD é entregável.

Débito é saída, crédito é entrada — e a direção vem do CFOP
--------------------------------------------------------------------
A não cumulatividade do ICMS (Art. 155, §2º, I da Constituição) compensa o que se deve
pelas saídas com o que se creditou nas entradas. Aqui isso vira uma soma simples, e a
única decisão é **de que lado cada documento entra**.

Essa decisão **não** sai do DocType. Um `Purchase Invoice` normalmente é entrada, mas uma
devolução de venda também é registrada como compra e ainda assim é crédito da mesma
natureza; um `Sales Invoice` de devolução de compra é saída que estorna crédito. O que
diz a direção é o **primeiro dígito do CFOP** — `1`/`2`/`3` entrada, `5`/`6`/`7` saída —
que é como o próprio leiaute organiza a tabela.

Ler o CFOP e não o DocType é o que faz devolução cair no lado certo sem caso especial.

Crédito de entrada não é automático
-------------------------------------------
Nem toda entrada gera crédito: uso e consumo, ativo imobilizado e mercadoria destinada a
saída isenta não creditam, e a regra varia por destinação. Este módulo soma o que os
documentos **declaram** em `br_valor_icms` — se a apuração do documento já respeitou a
recuperabilidade (e ela respeita, via `custo_aquisicao`/`ItemFiscal`), o total está certo;
se alguém preencheu à mão, o total reflete o que foi preenchido.

É deliberado: reinterpretar aqui produziria um número diferente do que o documento exibe,
e divergência entre o que se vê e o que se declara é pior que um número discutível.

O que este módulo **não** faz
-------------------------------------
- **Não gera `E111` (ajustes).** O código do ajuste vem da tabela da UF, que este projeto
  documenta como não modelada (`docs/sped-fiscal.md`). Sem código não há ajuste, e inventar
  um seria declarar ao Fisco uma natureza que ninguém escolheu.
- **Não apura IPI (`E500`+).** Depende de o contribuinte ser industrial ou equiparado, o
  que o `IND_ATIV` do `0000` já declara — mas a apuração em si é outra frente.
- **Não traz saldo credor de período anterior.** Ele existe em `ApuracaoPeriodo` e sai
  zerado aqui: recuperá-lo exige ler o `Arquivo SPED` anterior, e usar zero quando havia
  saldo **aumenta** o imposto a recolher. Erra para mais, que é o lado seguro — mas erra,
  e por isso está declarado.

Estado de verificação: camada Frappe, **não** exercitada contra bench real.
"""

from decimal import Decimal

import frappe

from erpnext_brasil.contabil.apuracao_periodo import ApuracaoPeriodo
from erpnext_brasil.contabil.efd_icms_ipi import montar_e001, montar_e100, montar_e110, montar_e990

__all__ = ["CFOP_DE_ENTRADA", "CFOP_DE_SAIDA", "apuracao_do_periodo", "bloco_e_do_periodo"]

ZERO = Decimal("0.00")

CFOP_DE_ENTRADA = frozenset({"1", "2", "3"})
CFOP_DE_SAIDA = frozenset({"5", "6", "7"})

_DOCTYPES = ("Sales Invoice", "Purchase Invoice")


def _decimal(valor) -> Decimal:
	if valor in (None, ""):
		return ZERO

	return Decimal(str(valor))


def _data_sped(valor) -> str:
	return frappe.utils.getdate(valor).strftime("%d%m%Y")


def apuracao_do_periodo(company: str, data_inicial: str, data_final: str) -> ApuracaoPeriodo:
	"""Soma débitos e créditos de ICMS do período, pela direção do CFOP.

	Documento **cancelado** não entra: ele existe na escrituração do Bloco C com
	`COD_SIT = "02"` para que a numeração feche, mas não gera nem débito nem crédito —
	somá-lo cobraria imposto de operação que não aconteceu.
	"""
	debitos = ZERO
	creditos = ZERO

	for doctype in _DOCTYPES:
		nomes = frappe.get_all(
			doctype,
			filters={
				"company": company,
				"posting_date": ["between", [data_inicial, data_final]],
				"docstatus": 1,
			},
			pluck="name",
		)

		for nome in nomes:
			doc = frappe.get_doc(doctype, nome)

			for linha in doc.get("items", []):
				cfop = str(linha.get("br_cfop_sugerido") or "").strip()
				valor = _decimal(linha.get("br_valor_icms"))

				if not cfop or valor == ZERO:
					continue

				if cfop[0] in CFOP_DE_SAIDA:
					debitos += valor
				elif cfop[0] in CFOP_DE_ENTRADA:
					creditos += valor

	return ApuracaoPeriodo(tributo="ICMS", debitos=debitos, creditos=creditos)


def bloco_e_do_periodo(company: str, data_inicial: str, data_final: str) -> list[dict]:
	"""O Bloco E completo: `E001`, `E100`, `E110` e `E990`.

	Sempre com dados — este bloco não admite ser declarado vazio, e é por isso que
	`montar_e001` não recebe parâmetro nenhum.
	"""
	apuracao = apuracao_do_periodo(company, data_inicial, data_final)

	linhas = [
		montar_e001(),
		montar_e100(_data_sped(data_inicial), _data_sped(data_final)),
		montar_e110(apuracao),
	]

	return [*linhas, montar_e990(len(linhas) + 1)]
