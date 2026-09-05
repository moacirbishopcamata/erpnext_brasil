# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Costura da produção (Bloco K) — o que dá para travar sem bench.

Teste-âncora: `test_o_saldo_do_k200_vem_do_mesmo_lugar_que_o_h010` — um arquivo em que o
Bloco H e o Bloco K discordam sobre o mesmo estoque é rejeitado, e descobrir qual dos dois
está errado exige refazer as duas contas. Fonte única elimina a classe inteira de erro.
"""

import unittest
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

_FONTE = (RAIZ / "integracao" / "efd_producao.py").read_text(encoding="utf-8")


class TestFonteUnicaDoSaldo(unittest.TestCase):
	def test_o_saldo_do_k200_vem_do_mesmo_lugar_que_o_h010(self):
		"""O teste-âncora: `saldos_na_data` é a única fonte dos dois blocos."""
		self.assertIn("from erpnext_brasil.integracao.efd_inventario import saldos_na_data", _FONTE)

	def test_nao_ha_segunda_consulta_ao_razao(self):
		"""Uma consulta própria aqui produziria um número que pode divergir do Bloco H."""
		self.assertNotIn("tabStock Ledger Entry", _FONTE)


class TestPrecisaoNaFronteira(unittest.TestCase):
	"""O achado do leiaute: saldo tem 3 casas, movimentação tem 6 — no mesmo bloco."""

	def test_o_saldo_usa_tres_casas(self):
		from erpnext_brasil.contabil.efd_bloco_k import DECIMAIS_SALDO, arredondar_quantidade

		self.assertEqual(DECIMAIS_SALDO, 3)
		self.assertEqual(arredondar_quantidade(Decimal("1.23456789"), DECIMAIS_SALDO), Decimal("1.235"))

	def test_a_producao_usa_seis_casas(self):
		from erpnext_brasil.contabil.efd_bloco_k import (
			DECIMAIS_MOVIMENTACAO,
			arredondar_quantidade,
		)

		self.assertEqual(DECIMAIS_MOVIMENTACAO, 6)
		self.assertEqual(
			arredondar_quantidade(Decimal("1.23456789"), DECIMAIS_MOVIMENTACAO), Decimal("1.234568")
		)

	def test_a_conversao_e_explicita_nos_dois_lugares(self):
		"""Converter implicitamente é como o saldo deixa de fechar com a movimentação."""
		self.assertIn("arredondar_quantidade(item.quantidade, DECIMAIS_SALDO)", _FONTE)
		self.assertIn("DECIMAIS_MOVIMENTACAO", _FONTE)


class TestOrdemDeProducao(unittest.TestCase):
	def test_os_tres_campos_da_ordem_vao_juntos_ou_nenhum(self):
		"""`ItemProduzido` recusa metade — o leiaute exige o conjunto."""
		from erpnext_brasil.contabil.efd_bloco_k import ItemProduzido
		from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido

		with self.assertRaises(EfdInvalido):
			ItemProduzido(
				codigo_item="P1",
				quantidade=Decimal("1.000000"),
				codigo_ordem_producao="OP-1",  # sem data de início
			)

	def test_ordem_sem_data_de_inicio_e_ignorada(self):
		"""Melhor apontar por período do que montar meia ordem que o registro recusa."""
		self.assertIn("if not inicio:", _FONTE)

	def test_ordem_em_aberto_deixa_a_data_de_fim_vazia(self):
		"""Em branco é informação: produção em elaboração no fim do período."""
		self.assertIn("if fim else None", _FONTE)


class TestEncerramentoDoBloco(unittest.TestCase):
	def test_o_k990_e_refeito_depois_de_acrescentar_producao(self):
		"""O encerramento conta as linhas do bloco; acrescentar registros depois de
		montá-lo deixaria o número errado — e o PVA só diz que a contagem divergiu."""
		self.assertIn("base[:-1]", _FONTE)
		self.assertIn("montar_k990(len(linhas) + 1)", _FONTE)

	def test_sem_producao_o_bloco_base_e_devolvido_intacto(self):
		"""Refazer o encerramento sem necessidade seria recontar o que já estava certo."""
		self.assertIn("if not producao:", _FONTE)


class TestEscopoDeclarado(unittest.TestCase):
	def test_so_stock_entry_de_manufatura_entra(self):
		"""Ordem planejada e não executada não produziu nada."""
		self.assertIn('"stock_entry_type": TIPO_MANUFATURA', _FONTE)
		self.assertIn('"docstatus": 1', _FONTE)

	def test_o_k220_fica_declarado_como_ausente(self):
		"""`Material Transfer` não distingue reclassificação de mudança de depósito."""
		self.assertIn("Não emite `K220`", _FONTE)

	def test_o_leiaute_padrao_e_o_completo(self):
		"""É o que exige mais, e portanto nunca informa a menos."""
		import inspect

		from erpnext_brasil.contabil.efd_bloco_k import LEIAUTE_COMPLETO, montar_bloco_k

		padrao = inspect.signature(montar_bloco_k).parameters["tipo_de_leiaute"].default

		self.assertEqual(padrao, LEIAUTE_COMPLETO)


if __name__ == "__main__":
	unittest.main()
