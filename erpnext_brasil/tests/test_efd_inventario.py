# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Costura do inventário (Bloco H) — o que dá para travar sem bench.

`integracao/efd_inventario.py` importa `frappe` e consulta o razão de estoque, então a
execução só existe num site real. O que se pode conferir aqui são as **decisões**: de onde
o saldo é lido, o que fica de fora, e a limitação dos dois valores do item.

Teste-âncora: `test_o_saldo_vem_do_razao_e_nao_do_bin` — o `Bin` guarda o saldo de
**hoje**; um inventário de 31/12 gerado em fevereiro declararia o estoque errado, e o
número seria plausível.
"""

import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

_FONTE = (RAIZ / "integracao" / "efd_inventario.py").read_text(encoding="utf-8")

# Só o corpo da consulta, isolado da prosa que a explica.
_SQL = _FONTE[_FONTE.index("SELECT sle.item_code") : _FONTE.index("GROUP BY sle.item_code")]


class TestOrigemDoSaldo(unittest.TestCase):
	def test_o_saldo_vem_do_razao_e_nao_do_bin(self):
		"""O teste-âncora: `Bin` é o saldo corrente, e o inventário é de uma data."""
		self.assertIn("tabStock Ledger Entry", _SQL)
		self.assertNotIn("tabBin", _SQL)

	def test_a_consulta_respeita_a_data(self):
		"""Sem o corte por data, o saldo seria o de hoje com cara de ser o do período."""
		self.assertIn("posting_date <= %(data)s", _SQL)

	def test_lancamento_cancelado_nao_conta(self):
		self.assertIn("is_cancelled = 0", _SQL)

	def test_usa_o_acumulado_e_nao_a_soma_dos_movimentos(self):
		"""`qty_after_transaction` já é o acumulado; somar `actual_qty` daria o mesmo
		número com mais chance de perder um lançamento pelo caminho.

		A checagem é sobre o **SQL**, não sobre o arquivo: a docstring cita `actual_qty`
		justamente para explicar por que não usá-lo, e medir o texto inteiro reprovaria a
		explicação junto com o erro que ela previne.
		"""
		self.assertIn("qty_after_transaction", _SQL)
		self.assertNotIn("actual_qty", _SQL)


class TestOqueFicaDeFora(unittest.TestCase):
	def test_saldo_zero_e_negativo_ficam_de_fora(self):
		"""Zero é desnecessário pelo guia; negativo é inconsistência do sistema, não fato
		a declarar ao Fisco."""
		self.assertIn("quantidade <= ZERO", _FONTE)

	def test_o_motivo_padrao_e_o_final_do_periodo(self):
		"""Os outros cinco motivos dependem de fato que o ERPNext não registra."""
		from erpnext_brasil.contabil.efd_bloco_h import MOTIVO_FINAL_DO_PERIODO, montar_bloco_h

		self.assertEqual(
			montar_bloco_h.__defaults__[-1] if montar_bloco_h.__defaults__ else None,
			MOTIVO_FINAL_DO_PERIODO,
		)

	def test_o_motivo_de_st_continua_recusado(self):
		"""`MOT_INV = 06` exige um H030 por item, que este projeto não monta."""
		from datetime import date
		from decimal import Decimal

		from erpnext_brasil.contabil.efd_bloco_h import (
			MOTIVO_SUBSTITUICAO_TRIBUTARIA,
			ItemInventario,
			montar_bloco_h,
		)
		from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido

		item = ItemInventario(
			codigo_item="P1",
			unidade="UN",
			quantidade=Decimal("1.000"),
			valor_unitario=Decimal("1.000000"),
			valor_item=Decimal("1.00"),
		)

		with self.assertRaises(EfdInvalido):
			montar_bloco_h(date(2026, 12, 31), [item], motivo=MOTIVO_SUBSTITUICAO_TRIBUTARIA)


class TestLimitacaoDosDoisValores(unittest.TestCase):
	"""A limitação mais relevante do módulo — declarada, não escondida."""

	def test_os_dois_valores_do_item_saem_iguais(self):
		"""O ERPNext guarda um custo só; separar as óticas exigiria saber quanto de tributo
		recuperável está embutido, dado que não sobrevive à valoração do estoque."""
		self.assertIn("valor_item_ir=valor.quantize", _FONTE)

	def test_a_limitacao_esta_escrita_no_modulo(self):
		"""Escondê-la numa nota de rodapé seria o silêncio que este projeto evita."""
		self.assertIn("limitação declarada", _FONTE)

	def test_o_leiaute_permite_valores_diferentes(self):
		"""A limitação é nossa, não do leiaute: `H010` aceita os dois valores distintos, e
		há teste provando — é isso que torna a lacuna paga um dia."""
		from decimal import Decimal

		from erpnext_brasil.contabil.efd_bloco_h import ItemInventario, montar_h010

		campos = montar_h010(
			ItemInventario(
				codigo_item="P1",
				unidade="UN",
				quantidade=Decimal("1.000"),
				valor_unitario=Decimal("1000.000000"),
				valor_item=Decimal("1000.00"),
				valor_item_ir=Decimal("820.00"),
			)
		)

		self.assertNotEqual(campos["VL_ITEM"], campos["VL_ITEM_IR"])


if __name__ == "__main__":
	unittest.main()
