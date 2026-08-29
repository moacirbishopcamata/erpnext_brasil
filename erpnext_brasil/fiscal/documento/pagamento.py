# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Grupo `pag` — formas de pagamento.

A regra condicional do `vPag`
------------------------------
O XSD documenta explicitamente: *"Esta tag poderá ser omitida quando tPag=90 (Sem
Pagamento), caso contrário deverá ser preenchida."* É a única forma de pagamento em que
o valor é dispensado — todas as outras exigem `vPag`, mesmo pagamento futuro (`indPag`
a prazo) ou parcial.

`tPag` não tem enumeração fixa no XSD
--------------------------------------
O tipo é só `[0-9]{2}` — os códigos válidos vêm de uma **tabela externa** (o Portal da
NF-e a publica em Documentos > Diversos, "Tabela de Meios de Pagamento", atualizada
independente da versão do leiaute). `FORMAS_PAGAMENTO` aqui é a tabela vigente, mas por
ser tabela externa e não restrição de schema, uma emissão em produção deve confirmá-la
contra a versão publicada antes de assumir que está completa.

Escopo
------
Cobertos: `detPag` (lista), incluindo `card` para pagamento com cartão. Fora: os
sub-campos de bandeira/autorização de `card` além do essencial, e a integração com o
processo de compra (Pix dinâmico, por exemplo) — este módulo só monta o que já foi
decidido fora dele.

Funções puras: nenhuma dependência do Frappe.
"""

from decimal import Decimal

from erpnext_brasil.fiscal.impostos.icms import arredondar

__all__ = ["FORMAS_PAGAMENTO", "SEM_PAGAMENTO", "PagamentoInvalido", "montar_pag"]

# Tabela de Meios de Pagamento — publicada à parte do leiaute, no Portal da NF-e.
FORMAS_PAGAMENTO = {
	"01": "Dinheiro",
	"02": "Cheque",
	"03": "Cartão de Crédito",
	"04": "Cartão de Débito",
	"05": "Crédito Loja",
	"10": "Vale Alimentação",
	"11": "Vale Refeição",
	"12": "Vale Presente",
	"13": "Vale Combustível",
	"15": "Boleto Bancário",
	"16": "Depósito Bancário",
	"17": "Pagamento Instantâneo (PIX)",
	"18": "Transferência bancária, Carteira Digital",
	"19": "Programa de fidelidade, Cashback, Crédito Virtual",
	"90": "Sem pagamento",
	"99": "Outros",
}

SEM_PAGAMENTO = "90"


class PagamentoInvalido(ValueError):
	def __init__(self, mensagem: str, campo: str = ""):
		super().__init__(mensagem)
		self.campo = campo


def _valor(quantia) -> str:
	return str(arredondar(Decimal(str(quantia or 0))))


def _det_pag(
	forma: str,
	valor,
	indicador: str = "",
	descricao: str = "",
	cartao: dict | None = None,
) -> dict:
	if forma not in FORMAS_PAGAMENTO:
		raise PagamentoInvalido(
			f"Forma de pagamento {forma!r} não consta na Tabela de Meios de Pagamento",
			"forma",
		)

	# Regra do próprio XSD: vPag é dispensado só quando tPag=90.
	if forma != SEM_PAGAMENTO and valor is None:
		raise PagamentoInvalido(
			f"vPag é obrigatório para a forma {forma} ({FORMAS_PAGAMENTO[forma]}) — "
			f"só é dispensado para {SEM_PAGAMENTO} (Sem pagamento)",
			"valor",
		)

	if forma == "99" and not descricao:
		raise PagamentoInvalido(
			"Forma de pagamento 99 (Outros) exige a descrição (xPag)", "descricao"
		)

	grupo: dict = {}

	if indicador:
		grupo["indPag"] = indicador

	grupo["tPag"] = forma

	if descricao:
		grupo["xPag"] = descricao

	if valor is not None:
		grupo["vPag"] = _valor(valor)

	# `is not None`, não `if cartao`: um dicionário vazio significa "cartão com os
	# padrões", e `if cartao` o descartaria em silêncio por ser falso em Python.
	if cartao is not None:
		grupo["card"] = {
			"tpIntegra": cartao.get("tipo_integracao", "2"),
			**({"CNPJ": cartao["cnpj"]} if cartao.get("cnpj") else {}),
			**({"tBand": cartao["bandeira"]} if cartao.get("bandeira") else {}),
			**({"cAut": cartao["autorizacao"]} if cartao.get("autorizacao") else {}),
		}

	return grupo


def montar_pag(pagamentos: list[dict], troco=None) -> dict:
	"""Monta o grupo `pag` a partir de uma lista de pagamentos.

	Cada item de `pagamentos` é um dicionário com as chaves de `_det_pag`: `forma`,
	`valor`, e opcionalmente `indicador`, `descricao`, `cartao`.
	"""
	if not pagamentos:
		raise PagamentoInvalido("O grupo pag exige ao menos uma forma de pagamento", "pagamentos")

	grupo: dict = {"detPag": [_det_pag(**p) for p in pagamentos]}

	if troco:
		grupo["vTroco"] = _valor(troco)

	return {"pag": grupo}
