# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da tabela de URL de consulta do QR Code da NFC-e por UF.

RO é o teste mais importante — prioridade de verificação confirmada pelo usuário —
conferido contra uma segunda fonte independente (Cartilha de Orientações NFC-e da
própria SEFIN-RO), não só a tabela de referência.
"""

import unittest

from erpnext_brasil.fiscal.documento.consulta_nfce import URL_QRCODE_POR_UF, UfDesconhecida, url_qrcode


class TestCobertura(unittest.TestCase):
	def test_as_27_ufs_estao_mapeadas(self):
		self.assertEqual(len(URL_QRCODE_POR_UF), 27)

	def test_todas_tem_producao_e_homologacao(self):
		for uf, ambientes in URL_QRCODE_POR_UF.items():
			with self.subTest(uf=uf):
				self.assertIn("producao", ambientes)
				self.assertIn("homologacao", ambientes)
				self.assertTrue(ambientes["producao"].startswith("http"))
				self.assertTrue(ambientes["homologacao"].startswith("http"))


class TestRondonia(unittest.TestCase):
	"""Confirmado contra a Cartilha de Orientações NFC-e da SEFIN-RO, não só a tabela
	de referência — a mesma URL vale para os dois ambientes."""

	def test_url_de_producao(self):
		self.assertEqual(
			url_qrcode("RO"), "http://www.nfce.sefin.ro.gov.br/consultanfce/consulta.jsp"
		)

	def test_homologacao_igual_a_producao(self):
		self.assertEqual(url_qrcode("RO", "producao"), url_qrcode("RO", "homologacao"))


class TestValidacao(unittest.TestCase):
	def test_uf_desconhecida(self):
		with self.assertRaises(UfDesconhecida):
			url_qrcode("XX")

	def test_uf_minuscula_e_normalizada(self):
		self.assertEqual(url_qrcode("ro"), url_qrcode("RO"))

	def test_ambiente_invalido(self):
		with self.assertRaises(ValueError):
			url_qrcode("RO", "teste")

	def test_producao_e_o_padrao(self):
		self.assertEqual(url_qrcode("SP"), url_qrcode("SP", "producao"))


if __name__ == "__main__":
	unittest.main()
