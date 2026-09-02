# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/documento/autorizadores_mdfe.py`."""

import unittest

from erpnext_brasil.fiscal.documento.autorizadores_mdfe import endpoint


class TestEndpoint(unittest.TestCase):
	def test_uf_e_ignorada_mesmo_resultado_para_qualquer_uf(self):
		"""Achado real: MDF-e tem um único autorizador nacional -- a UF não muda
		o resultado."""
		self.assertEqual(endpoint("RO", "MDFeRecepcaoSinc"), endpoint("SP", "MDFeRecepcaoSinc"))
		self.assertEqual(endpoint("MG", "MDFeRecepcaoSinc"), endpoint("AC", "MDFeRecepcaoSinc"))

	def test_producao(self):
		url = endpoint("RO", "MDFeRecepcaoSinc")
		self.assertEqual(url, "https://mdfe.svrs.rs.gov.br/ws/MDFeRecepcaoSinc/MDFeRecepcaoSinc.asmx")

	def test_homologacao_diferente_de_producao(self):
		self.assertNotEqual(
			endpoint("RO", "MDFeRecepcaoSinc", ambiente="homologacao"),
			endpoint("RO", "MDFeRecepcaoSinc"),
		)

	def test_ambiente_invalido_levanta_erro(self):
		with self.assertRaises(ValueError):
			endpoint("RO", "MDFeRecepcaoSinc", ambiente="teste")

	def test_servico_inexistente_devolve_none(self):
		self.assertIsNone(endpoint("RO", "ServicoInexistente"))


if __name__ == "__main__":
	unittest.main()
