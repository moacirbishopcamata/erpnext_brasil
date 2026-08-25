# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes dos grupos de IBS/CBS do layout da NF-e.

O teste mais importante aqui é o de `pIBSUF`: a regra UB18-10 da NT 2025.002 exige
exatamente `0.1000` em documentos de 2025 e 2026, e a rejeição 1026 é o que se recebe
quando o valor sai diferente. Um erro de fração para percentual passaria despercebido em
qualquer teste de aritmética e derrubaria toda nota emitida.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.documento.ibs_cbs_xml import (
	grupo_ibscbs_item,
	grupo_totais_ibscbs,
	percentual,
	valor,
)
from erpnext_brasil.fiscal.impostos.ibs_cbs import calcular_ibs_cbs


def d(v: str) -> Decimal:
	return Decimal(v)


class TestFormatacao(unittest.TestCase):
	def test_fracao_vira_percentual_com_quatro_casas(self):
		self.assertEqual(percentual(d("0.001")), "0.1000")
		self.assertEqual(percentual(d("0.009")), "0.9000")
		self.assertEqual(percentual(d("0")), "0.0000")

	def test_percentual_de_aliquota_cheia(self):
		self.assertEqual(percentual(d("0.18")), "18.0000")

	def test_valor_com_duas_casas(self):
		self.assertEqual(valor(d("10")), "10.00")
		self.assertEqual(valor(d("9.5")), "9.50")


class TestGrupoDoItem(unittest.TestCase):
	def setUp(self):
		self.resultado = calcular_ibs_cbs(d("1000.00"), ano=2026)
		self.grupo = grupo_ibscbs_item(self.resultado, cst="000", classificacao_tributaria="000001")

	def test_hierarquia_das_tags(self):
		self.assertIn("IBSCBS", self.grupo)

		ibscbs = self.grupo["IBSCBS"]
		self.assertIn("CST", ibscbs)
		self.assertIn("cClassTrib", ibscbs)
		self.assertIn("gIBSCBS", ibscbs)

		g = ibscbs["gIBSCBS"]
		self.assertEqual(set(g), {"vBC", "gIBSUF", "gIBSMun", "vIBS", "gCBS"})

	def test_regra_ub18_10_a_aliquota_estadual_e_0_1000(self):
		"""Rejeição 1026 quando pIBSUF difere de 0,1% em 2025/2026."""
		self.assertEqual(self.grupo["IBSCBS"]["gIBSCBS"]["gIBSUF"]["pIBSUF"], "0.1000")

	def test_aliquota_da_cbs(self):
		self.assertEqual(self.grupo["IBSCBS"]["gIBSCBS"]["gCBS"]["pCBS"], "0.9000")

	def test_valores_calculados(self):
		g = self.grupo["IBSCBS"]["gIBSCBS"]

		self.assertEqual(g["vBC"], "1000.00")
		self.assertEqual(g["gIBSUF"]["vIBSUF"], "1.00")
		self.assertEqual(g["gIBSMun"]["vIBSMun"], "0.00")
		self.assertEqual(g["vIBS"], "1.00")
		self.assertEqual(g["gCBS"]["vCBS"], "9.00")

	def test_vibs_e_a_soma_das_parcelas(self):
		g = self.grupo["IBSCBS"]["gIBSCBS"]
		soma = Decimal(g["gIBSUF"]["vIBSUF"]) + Decimal(g["gIBSMun"]["vIBSMun"])

		self.assertEqual(Decimal(g["vIBS"]), soma)

	def test_ibs_municipal_aparece_mesmo_zerado(self):
		"""O grupo não é omitido quando a parcela é zero — o layout espera o campo."""
		self.assertIn("gIBSMun", self.grupo["IBSCBS"]["gIBSCBS"])

	def test_cst_e_classificacao_sao_obrigatorios(self):
		for cst, classificacao in (("", "000001"), ("000", ""), ("", "")):
			with self.subTest(cst=cst, classificacao=classificacao):
				with self.assertRaises(ValueError):
					grupo_ibscbs_item(self.resultado, cst=cst, classificacao_tributaria=classificacao)


class TestTotais(unittest.TestCase):
	def test_soma_de_varios_itens(self):
		itens = [
			calcular_ibs_cbs(d("1000.00"), ano=2026),
			calcular_ibs_cbs(d("500.00"), ano=2026),
		]

		totais = grupo_totais_ibscbs(itens)["IBSCBSTot"]

		self.assertEqual(totais["vBCIBSCBS"], "1500.00")
		# Dentro de gIBS os subgrupos repetem os nomes do item; não existe sufixo "Tot".
		self.assertEqual(totais["gIBS"]["gIBSUF"]["vIBSUF"], "1.50")
		self.assertEqual(totais["gIBS"]["gIBSMun"]["vIBSMun"], "0.00")
		self.assertEqual(totais["gIBS"]["vIBS"], "1.50")
		self.assertEqual(totais["gCBS"]["vCBS"], "13.50")

	def test_total_e_soma_dos_itens_arredondados_nao_recalculo(self):
		"""Dois itens de 0,05 somam 0,10; recalcular sobre a base daria outro centavo.

		O validador confere o total contra a soma dos itens, então a soma é que manda.
		"""
		itens = [calcular_ibs_cbs(d("55.00"), ano=2026) for _ in range(3)]

		soma_itens = sum(i.cbs for i in itens)
		totais = grupo_totais_ibscbs(itens)["IBSCBSTot"]

		self.assertEqual(Decimal(totais["gCBS"]["vCBS"]), soma_itens)

	def test_lista_vazia_e_erro(self):
		with self.assertRaises(ValueError):
			grupo_totais_ibscbs([])


if __name__ == "__main__":
	unittest.main()
