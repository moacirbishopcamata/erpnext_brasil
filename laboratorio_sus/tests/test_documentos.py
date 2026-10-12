# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

import unittest

from laboratorio_sus.puro.documentos import cns_valido, cpf_valido, somente_digitos


def _cns_com_dv(prefixo11: str) -> str:
	"""Monta um CNS válido por força bruta sobre os 4 últimos dígitos, sem repetir a fórmula testada."""
	for resto in range(10000):
		candidato = prefixo11 + f"{resto:04d}"

		if cns_valido(candidato):
			return candidato

	raise AssertionError("não achou")


class TestCpf(unittest.TestCase):
	def test_cpf_conhecido_valido(self):
		self.assertTrue(cpf_valido("529.982.247-25"))

	def test_dv_errado(self):
		self.assertFalse(cpf_valido("529.982.247-26"))

	def test_repetidos_e_tamanho(self):
		self.assertFalse(cpf_valido("111.111.111-11"))
		self.assertFalse(cpf_valido("1234"))
		self.assertFalse(cpf_valido(""))

	def test_somente_digitos(self):
		self.assertEqual(somente_digitos("12.3-4 x5"), "12345")


class TestCns(unittest.TestCase):
	def test_aceita_o_que_fecha_a_soma_ponderada(self):
		for inicio in ("12345678901", "23456789012", "78901234567", "89012345678", "90123456789"):
			cns = _cns_com_dv(inicio)
			soma = sum(int(d) * p for d, p in zip(cns, range(15, 0, -1), strict=True))
			self.assertEqual(soma % 11, 0, cns)
			self.assertTrue(cns_valido(cns))

	def test_recusa_alteracao_de_um_digito(self):
		cns = _cns_com_dv("12345678901")
		alterado = cns[:5] + ("0" if cns[5] != "0" else "1") + cns[6:]
		self.assertFalse(cns_valido(alterado))

	def test_recusa_prefixo_invalido_e_tamanho(self):
		self.assertFalse(cns_valido("000000000000000"))
		self.assertFalse(cns_valido("123"))
		self.assertFalse(cns_valido("3" + "0" * 14))


if __name__ == "__main__":
	unittest.main()
