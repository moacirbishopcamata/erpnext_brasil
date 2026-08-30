# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes das tabelas de URL de consulta da NFC-e por UF (QR Code e por chave).

RO é o teste mais importante — prioridade de verificação confirmada pelo usuário —
conferido contra uma segunda fonte independente (Cartilha de Orientações NFC-e da
própria SEFIN-RO), não só a tabela de referência.
"""

import unittest

from erpnext_brasil.fiscal.documento.consulta_nfce import (
	URL_CHAVE_POR_UF,
	URL_QRCODE_POR_UF,
	UfDesconhecida,
	url_chave,
	url_qrcode,
)


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


class TestUrlChave(unittest.TestCase):
	"""Fonte: ENCAT, 'URL por UF utilizada para consulta chave' — 22 de 27 UFs
	confirmadas em produção; CE só em homologação; GO/MG/PE/SC ausentes de propósito."""

	def test_23_ufs_tem_ao_menos_um_ambiente_confirmado(self):
		"""23 UFs aparecem na tabela (CE incluída, só com homologação) — 22 delas com
		produção confirmada (ver `test_22_ufs_com_producao`)."""
		self.assertEqual(len(URL_CHAVE_POR_UF), 23)

	def test_22_ufs_com_producao(self):
		com_producao = [uf for uf, ambientes in URL_CHAVE_POR_UF.items() if "producao" in ambientes]

		self.assertEqual(len(com_producao), 22)

	def test_ro_e_o_dominio_base_sem_caminho(self):
		"""Confirmado na própria fonte ENCAT: só o domínio, sem o caminho
		`/consultanfce/consulta.jsp` que a URL do QR Code tem — as duas infraestruturas
		são distintas mesmo para RO, não a mesma URL reaproveitada."""
		self.assertEqual(url_chave("RO"), "http://www.nfce.sefin.ro.gov.br")
		self.assertNotEqual(url_chave("RO"), url_qrcode("RO"))

	def test_ce_so_tem_homologacao(self):
		self.assertNotIn("producao", URL_CHAVE_POR_UF["CE"])
		self.assertIn("homologacao", URL_CHAVE_POR_UF["CE"])

	def test_ce_producao_levanta_not_implemented(self):
		with self.assertRaises(NotImplementedError):
			url_chave("CE", "producao")

	def test_ce_homologacao_funciona(self):
		self.assertTrue(url_chave("CE", "homologacao").startswith("http"))

	def test_go_mg_pe_sc_ausentes_de_proposito(self):
		for uf in ("GO", "MG", "PE", "SC"):
			with self.subTest(uf=uf):
				self.assertNotIn(uf, URL_CHAVE_POR_UF)

				with self.assertRaises(UfDesconhecida):
					url_chave(uf)

	def test_uf_desconhecida_de_verdade(self):
		with self.assertRaises(UfDesconhecida):
			url_chave("XX")

	def test_nao_reaproveita_url_do_qrcode_para_uf_ausente(self):
		"""GO tem URL de QR Code confirmada, mas não de consulta por chave — as duas
		tabelas não se substituem."""
		self.assertIn("GO", URL_QRCODE_POR_UF)
		self.assertNotIn("GO", URL_CHAVE_POR_UF)


if __name__ == "__main__":
	unittest.main()
