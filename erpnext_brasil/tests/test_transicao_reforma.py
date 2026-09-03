# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/impostos/transicao_reforma.py` e do ano usado na apuração.

O teste que mais importa é `TestAnoDaOperacao`: prova que documento sem ano de
competência passa a usar o ano do **próprio documento**, e não o ano-teste fixo — a
correção do risco silencioso descrito no módulo.
"""

import unittest
from datetime import date

from erpnext_brasil.fiscal.impostos.ibs_cbs import ANO_TESTE
from erpnext_brasil.fiscal.impostos.transicao_reforma import avaliar_transicao
from erpnext_brasil.integracao.mapeamento import _ano_da_operacao


class TestAvaliarTransicao(unittest.TestCase):
	def test_ano_teste_nao_alerta(self):
		situacao = avaliar_transicao(ANO_TESTE)

		self.assertTrue(situacao.aliquotas_embutidas)
		self.assertFalse(situacao.deve_alertar)

	def test_ano_seguinte_alerta(self):
		situacao = avaliar_transicao(ANO_TESTE + 1)

		self.assertFalse(situacao.aliquotas_embutidas)
		self.assertTrue(situacao.deve_alertar)

	def test_mensagem_do_ano_seguinte_explica_o_risco(self):
		situacao = avaliar_transicao(ANO_TESTE + 1)

		self.assertIn("CBS", situacao.mensagem)
		self.assertIn("recolher a menos", situacao.mensagem)

	def test_ano_muito_posterior_tambem_alerta(self):
		self.assertTrue(avaliar_transicao(2033).deve_alertar)

	def test_ano_anterior_alerta_por_motivo_oposto(self):
		"""Antes de 2026 IBS/CBS não existiam — sinal de ano digitado errado."""
		situacao = avaliar_transicao(ANO_TESTE - 1)

		self.assertTrue(situacao.deve_alertar)
		self.assertIn("digitado", situacao.mensagem)


class TestAnoDaOperacao(unittest.TestCase):
	"""A correção do risco silencioso: o padrão passou a ser o ano do documento."""

	def test_ano_informado_tem_prioridade(self):
		documento = {"br_ano_competencia": 2029, "posting_date": date(2027, 5, 10)}

		self.assertEqual(_ano_da_operacao(documento), 2029)

	def test_sem_ano_informado_usa_a_data_do_documento(self):
		"""Antes caía no ano-teste fixo e apuraria 1% num documento de 2027."""
		self.assertEqual(_ano_da_operacao({"posting_date": date(2027, 5, 10)}), 2027)

	def test_aceita_data_como_texto(self):
		"""O Frappe entrega `posting_date` ora como `date`, ora como string ISO."""
		self.assertEqual(_ano_da_operacao({"posting_date": "2028-01-31"}), 2028)

	def test_usa_transaction_date_quando_nao_ha_posting_date(self):
		"""Pedidos usam `transaction_date`, não `posting_date`."""
		self.assertEqual(_ano_da_operacao({"transaction_date": date(2027, 3, 1)}), 2027)

	def test_sem_data_nenhuma_cai_no_padrao(self):
		self.assertEqual(_ano_da_operacao({}), ANO_TESTE)

	def test_documento_de_2026_continua_no_ano_teste(self):
		"""A correção não muda nada no ano corrente — só no futuro."""
		self.assertEqual(_ano_da_operacao({"posting_date": date(ANO_TESTE, 6, 1)}), ANO_TESTE)


class TestIntegracaoComOCalculo(unittest.TestCase):
	def test_documento_futuro_sem_aliquotas_falha_alto(self):
		"""A consequência desejada da correção: em vez de calcular 1% em silêncio, a
		apuração recusa e diz o que falta."""
		from erpnext_brasil.fiscal.impostos.ibs_cbs import aliquotas_do_ano

		with self.assertRaises(ValueError) as contexto:
			aliquotas_do_ano(_ano_da_operacao({"posting_date": date(2027, 1, 15)}))

		self.assertIn("2027", str(contexto.exception))
		self.assertIn("alíquotas vigentes", str(contexto.exception))


if __name__ == "__main__":
	unittest.main()
