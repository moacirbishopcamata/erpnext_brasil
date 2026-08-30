# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_assinatura.py` — estrutura pura do envelope XMLDSig do
eSocial (SHA-256), sem nenhuma biblioteca de criptografia."""

import unittest

from erpnext_brasil.folha.esocial_assinatura import (
	ALGORITMO_ASSINATURA,
	ALGORITMO_C14N,
	ALGORITMO_DIGEST,
	AssinaturaInvalida,
	CertificadoExpirado,
	MaterialAssinatura,
	montar_signature,
	montar_signed_info,
	referencia_do_id,
)


class TestReferenciaDoId(unittest.TestCase):
	def test_acrescenta_o_prefixo(self):
		self.assertEqual(referencia_do_id("ID1234567890"), "#ID1234567890")

	def test_vazio_e_erro(self):
		with self.assertRaises(AssinaturaInvalida):
			referencia_do_id("")

	def test_ja_com_prefixo_e_erro(self):
		with self.assertRaises(AssinaturaInvalida):
			referencia_do_id("#ID1234567890")


class TestMontarSignedInfo(unittest.TestCase):
	def test_usa_os_algoritmos_sha256_nao_sha1(self):
		signed_info = montar_signed_info("ID1", "digestFake==")

		self.assertEqual(
			signed_info["SignedInfo"]["SignatureMethod"]["@Algorithm"], ALGORITMO_ASSINATURA
		)
		self.assertIn("sha256", ALGORITMO_ASSINATURA)
		self.assertIn("sha256", ALGORITMO_DIGEST)
		self.assertNotIn("sha1", ALGORITMO_ASSINATURA)

	def test_canonicalizacao_e_c14n_padrao_nao_exclusive(self):
		signed_info = montar_signed_info("ID1", "digestFake==")

		algoritmo = signed_info["SignedInfo"]["CanonicalizationMethod"]["@Algorithm"]

		self.assertEqual(algoritmo, ALGORITMO_C14N)
		self.assertNotIn("exc-c14n", algoritmo)

	def test_referencia_aponta_para_o_id(self):
		signed_info = montar_signed_info("ID1", "digestFake==")

		self.assertEqual(signed_info["SignedInfo"]["Reference"]["@URI"], "#ID1")

	def test_digest_vazio_e_erro(self):
		with self.assertRaises(AssinaturaInvalida):
			montar_signed_info("ID1", "")


class TestMontarSignature(unittest.TestCase):
	def _material(self, **overrides) -> MaterialAssinatura:
		base = dict(digest="digestFake==", assinatura="assinaturaFake==", certificado="certFake==")
		base.update(overrides)

		return MaterialAssinatura(**base)

	def test_estrutura_completa(self):
		signature = montar_signature("ID1", self._material())

		self.assertIn("SignedInfo", signature["Signature"])
		self.assertEqual(signature["Signature"]["SignatureValue"], "assinaturaFake==")
		self.assertEqual(
			signature["Signature"]["KeyInfo"]["X509Data"]["X509Certificate"], "certFake=="
		)

	def test_assinatura_vazia_e_erro(self):
		with self.assertRaises(AssinaturaInvalida):
			montar_signature("ID1", self._material(assinatura=""))

	def test_certificado_vazio_e_erro(self):
		with self.assertRaises(AssinaturaInvalida):
			montar_signature("ID1", self._material(certificado=""))


class TestCertificadoExpiradoEhSubclasse(unittest.TestCase):
	def test_e_subclasse_de_assinatura_invalida(self):
		self.assertTrue(issubclass(CertificadoExpirado, AssinaturaInvalida))


if __name__ == "__main__":
	unittest.main()
