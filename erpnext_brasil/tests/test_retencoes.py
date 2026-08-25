# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes das retenções na fonte.

O teste central não é a multiplicação: é a diferença entre os dois tipos de dispensa.
O IRRF dispensa pelo **imposto calculado**; a CSRF dispensa pela **base**. Confundir os
dois é o erro mais comum da área, e há teste específico travando cada um.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.retencoes import (
	ALIQUOTA_CSRF,
	MINIMO_CSRF,
	MINIMO_IRRF,
	calcular_csrf,
	calcular_inss,
	calcular_irrf,
	calcular_iss_retido,
	decompor_csrf,
	total_retido,
)


def d(v: str) -> Decimal:
	return Decimal(v)


class TestIRRF(unittest.TestCase):
	def test_retem_acima_do_minimo(self):
		r = calcular_irrf(d("1000.00"))

		self.assertEqual(r.valor, d("15.00"))
		self.assertFalse(r.dispensada)
		self.assertEqual(r.retido, d("15.00"))

	def test_dispensa_quando_o_imposto_nao_supera_o_minimo(self):
		r = calcular_irrf(d("600.00"))

		self.assertEqual(r.valor, d("9.00"))
		self.assertTrue(r.dispensada)
		self.assertEqual(r.retido, d("0.00"))

	def test_dispensa_e_por_valor_calculado_nao_por_base(self):
		"""Base alta com alíquota baixa pode ficar dispensada — e o inverso não."""
		# Base de 5.000 com alíquota de 0,1% dá 5,00: dispensado, apesar da base grande.
		r = calcular_irrf(d("5000.00"), aliquota=d("0.001"))

		self.assertEqual(r.valor, d("5.00"))
		self.assertTrue(r.dispensada)

	def test_limite_e_inclusivo(self):
		"""Exatamente o mínimo não se retém: a regra é "igual ou inferior"."""
		r = calcular_irrf(MINIMO_IRRF / d("0.015"))

		self.assertEqual(r.valor, d("10.00"))
		self.assertTrue(r.dispensada)

	def test_um_centavo_acima_do_limite_ja_retem(self):
		r = calcular_irrf(d("700.00"))

		self.assertEqual(r.valor, d("10.50"))
		self.assertFalse(r.dispensada)

	def test_motivo_e_registrado(self):
		self.assertIn("mínimo", calcular_irrf(d("100.00")).motivo)
		self.assertEqual(calcular_irrf(d("1000.00")).motivo, "")


class TestCSRF(unittest.TestCase):
	def test_aliquota_somada(self):
		self.assertEqual(ALIQUOTA_CSRF, d("0.0465"))

	def test_retem_acima_do_minimo(self):
		r = calcular_csrf(d("1000.00"))

		self.assertEqual(r.valor, d("46.50"))
		self.assertFalse(r.dispensada)

	def test_dispensa_e_pela_base_nao_pelo_valor(self):
		r = calcular_csrf(d("200.00"))

		self.assertTrue(r.dispensada)
		self.assertEqual(r.retido, d("0.00"))

	def test_limite_inclusivo(self):
		self.assertTrue(calcular_csrf(MINIMO_CSRF).dispensada)
		self.assertFalse(calcular_csrf(MINIMO_CSRF + d("0.01")).dispensada)

	def test_os_dois_minimos_se_correspondem(self):
		"""215,05 x 4,65% = 10,00 — os pisos de IRRF e CSRF são o mesmo valor."""
		self.assertEqual((MINIMO_CSRF * ALIQUOTA_CSRF).quantize(d("0.01")), MINIMO_IRRF)


class TestDecomposicaoCSRF(unittest.TestCase):
	def test_separa_nas_tres_contribuicoes(self):
		partes = decompor_csrf(calcular_csrf(d("1000.00")))

		self.assertEqual(partes["CSLL"], d("10.00"))
		self.assertEqual(partes["PIS"], d("6.50"))
		self.assertEqual(partes["COFINS"], d("30.00"))

	def test_a_soma_das_partes_bate_com_o_total(self):
		"""Invariante: rateio não pode criar nem sumir com centavo."""
		for base in ("1000.00", "333.33", "1234.56", "987.65", "215.06"):
			with self.subTest(base=base):
				retencao = calcular_csrf(d(base))
				partes = decompor_csrf(retencao)

				self.assertEqual(sum(partes.values()), retencao.valor)

	def test_dispensada_decompoe_em_zeros(self):
		partes = decompor_csrf(calcular_csrf(d("100.00")))

		self.assertEqual(set(partes.values()), {d("0.00")})


class TestINSSeISS(unittest.TestCase):
	def test_inss_nao_tem_dispensa_por_valor(self):
		r = calcular_inss(d("100.00"))

		self.assertEqual(r.valor, d("11.00"))
		self.assertFalse(r.dispensada)

	def test_iss_exige_aliquota_explicita(self):
		"""Não há padrão nacional: assumir um valor seria inventar tributo."""
		with self.assertRaises(ValueError) as ctx:
			calcular_iss_retido(d("1000.00"), d("0"))

		self.assertIn("município", str(ctx.exception))

	def test_iss_com_aliquota_informada(self):
		self.assertEqual(calcular_iss_retido(d("1000.00"), d("0.05")).valor, d("50.00"))


class TestTotal(unittest.TestCase):
	def test_soma_apenas_o_que_e_efetivamente_retido(self):
		retencoes = [
			calcular_irrf(d("1000.00")),
			calcular_csrf(d("1000.00")),
			calcular_iss_retido(d("1000.00"), d("0.05")),
		]

		self.assertEqual(total_retido(retencoes), d("111.50"))

	def test_dispensadas_nao_entram_no_total(self):
		retencoes = [calcular_irrf(d("100.00")), calcular_csrf(d("100.00"))]

		self.assertEqual(total_retido(retencoes), d("0.00"))


class TestValidacao(unittest.TestCase):
	def test_base_negativa_e_erro(self):
		with self.assertRaises(ValueError):
			calcular_irrf(d("-1.00"))

	def test_aliquota_como_percentual_e_erro(self):
		with self.assertRaises(ValueError):
			calcular_irrf(d("1000.00"), aliquota=d("1.5"))


if __name__ == "__main__":
	unittest.main()
