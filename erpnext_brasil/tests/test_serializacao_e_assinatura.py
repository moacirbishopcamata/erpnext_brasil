# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da serialização em XML e da estrutura da assinatura.

Estes testes rodam **sem `lxml` e sem `cryptography`**: a estrutura do envelope XMLDSig e
a conversão para XML são puras, e só a criptografia depende de biblioteca externa. É a
mesma separação que permite verificar o formato da assinatura sem ter certificado.

O teste `test_ordem_e_preservada` guarda algo que parece cosmético e não é: canonicalização
e assinatura dependem da ordem dos elementos, e o XSD da NF-e usa `xs:sequence`. Trocar
dois irmãos de lugar invalida a assinatura sem gerar erro de schema.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.documento.assinatura import (
	ALGORITMO_ASSINATURA,
	ALGORITMO_C14N,
	ALGORITMO_DIGEST,
	ALGORITMO_TRANSFORMACAO,
	Assinador,
	AssinaturaInvalida,
	MaterialAssinatura,
	montar_signature,
	montar_signed_info,
	referencia_do_id,
)
from erpnext_brasil.fiscal.documento.serializacao import Cdata, ErroSerializacao, para_xml

MATERIAL = MaterialAssinatura(
	digest="ZGlnZXN0",
	assinatura="YXNzaW5hdHVyYQ==",
	certificado="Y2VydGlmaWNhZG8=",
)


class TestSerializacao(unittest.TestCase):
	def test_elemento_simples(self):
		self.assertEqual(para_xml({"a": "1"}), "<a>1</a>")

	def test_aninhamento(self):
		self.assertEqual(para_xml({"a": {"b": {"c": "x"}}}), "<a><b><c>x</c></b></a>")

	def test_atributo(self):
		self.assertEqual(para_xml({"a": {"@id": "7", "b": "x"}}), '<a id="7"><b>x</b></a>')

	def test_namespace(self):
		self.assertEqual(para_xml({"a": {"b": "x"}}, namespace="urn:x"), '<a xmlns="urn:x"><b>x</b></a>')

	def test_namespace_nao_sobrescreve_o_declarado(self):
		arvore = {"a": {"@xmlns": "urn:proprio", "b": "x"}}

		self.assertIn('xmlns="urn:proprio"', para_xml(arvore, namespace="urn:outro"))

	def test_lista_vira_irmaos_repetidos(self):
		self.assertEqual(para_xml({"a": {"b": ["1", "2"]}}), "<a><b>1</b><b>2</b></a>")

	def test_none_e_omitido(self):
		"""Tag vazia é rejeição, não omissão."""
		self.assertEqual(para_xml({"a": {"b": "1", "c": None}}), "<a><b>1</b></a>")

	def test_ordem_e_preservada(self):
		"""Canonicalização e assinatura dependem da ordem; o XSD usa xs:sequence."""
		arvore = {"a": {"z": "1", "m": "2", "b": "3"}}

		self.assertEqual(para_xml(arvore), "<a><z>1</z><m>2</m><b>3</b></a>")

	def test_escapa_conteudo(self):
		self.assertEqual(para_xml({"a": "x & <y>"}), "<a>x &amp; &lt;y&gt;</a>")

	def test_escapa_atributo_na_forma_canonica(self):
		"""C14N exige aspas duplas e `&quot;` — não a troca de delimitador."""
		xml = para_xml({"a": {"@id": 'a"b', "b": "1"}})

		self.assertIn('id="a&quot;b"', xml)
		self.assertNotIn("'", xml)

	def test_escapa_caracteres_de_controle_no_atributo(self):
		xml = para_xml({"a": {"@id": "linha\nnova", "b": "1"}})

		self.assertIn("&#xA;", xml)

	def test_decimal_e_serializado_pelo_texto(self):
		self.assertEqual(para_xml({"v": Decimal("1234.50")}), "<v>1234.50</v>")

	def test_float_e_recusado(self):
		"""float traz erro de arredondamento e notação científica."""
		with self.assertRaises(ErroSerializacao) as ctx:
			para_xml({"v": 0.1})

		self.assertIn("Decimal", str(ctx.exception))

	def test_booleano_e_recusado(self):
		"""bool é int em Python: True viraria "1" sem aviso."""
		with self.assertRaises(ErroSerializacao):
			para_xml({"v": True})

	def test_exige_raiz_unica(self):
		for arvore in ({}, {"a": "1", "b": "2"}):
			with self.subTest(arvore=arvore):
				with self.assertRaises(ErroSerializacao):
					para_xml(arvore)

	def test_declaracao_opcional(self):
		self.assertTrue(para_xml({"a": "1"}, declaracao=True).startswith("<?xml"))
		self.assertFalse(para_xml({"a": "1"}).startswith("<?xml"))

	def test_raiz_vazia_e_erro(self):
		with self.assertRaises(ErroSerializacao):
			para_xml({"a": {}})


class TestCdata(unittest.TestCase):
	"""`qrCode` da NFC-e exige o conteúdo como CDATA, não texto XML-escapado — a URL tem
	`&` que, fora de CDATA, teria que virar `&amp;` e mudaria o conteúdo assinado."""

	def test_serializa_como_secao_cdata(self):
		xml = para_xml({"qrCode": Cdata("http://x?p=1&2")})

		self.assertEqual(xml, "<qrCode><![CDATA[http://x?p=1&2]]></qrCode>")

	def test_conteudo_nao_e_escapado(self):
		"""Diferente do texto normal, `&`/`<`/`>` dentro do CDATA passam ao vivo."""
		xml = para_xml({"x": Cdata("<a&b>")})

		self.assertIn("<![CDATA[<a&b>]]>", xml)

	def test_fechamento_de_cdata_no_meio_e_erro(self):
		with self.assertRaises(ErroSerializacao):
			Cdata("algo]]>que fecharia a secao no meio")

	def test_cdata_dentro_de_arvore_maior(self):
		xml = para_xml({"infNFeSupl": {"@versao": "4.00", "qrCode": Cdata("http://x"), "urlChave": "http://y"}})

		self.assertIn("<qrCode><![CDATA[http://x]]></qrCode>", xml)
		self.assertIn("<urlChave>http://y</urlChave>", xml)
		# Ordem preservada: qrCode antes de urlChave, como o XSD exige.
		self.assertLess(xml.index("qrCode"), xml.index("urlChave"))


class TestReferencia(unittest.TestCase):
	def test_prefixa_com_cerquilha(self):
		self.assertEqual(referencia_do_id("NFe3526..."), "#NFe3526...")

	def test_id_com_cerquilha_e_erro(self):
		"""Duplicar o prefixo gera "digest value inválido", que não aponta a causa."""
		with self.assertRaises(AssinaturaInvalida):
			referencia_do_id("#NFe3526")

	def test_id_vazio_e_erro(self):
		for vazio in ("", "   ", None):
			with self.subTest(valor=vazio):
				with self.assertRaises(AssinaturaInvalida):
					referencia_do_id(vazio)


class TestSignedInfo(unittest.TestCase):
	def setUp(self):
		self.bloco = montar_signed_info("NFe123", "ZGlnZXN0")["SignedInfo"]

	def test_algoritmos_do_perfil_da_nfe(self):
		self.assertEqual(self.bloco["CanonicalizationMethod"]["@Algorithm"], ALGORITMO_C14N)
		self.assertEqual(self.bloco["SignatureMethod"]["@Algorithm"], ALGORITMO_ASSINATURA)
		self.assertEqual(self.bloco["Reference"]["DigestMethod"]["@Algorithm"], ALGORITMO_DIGEST)

	def test_duas_transformacoes_na_ordem_do_perfil(self):
		transformacoes = self.bloco["Reference"]["Transforms"]["Transform"]

		self.assertEqual(
			[t["@Algorithm"] for t in transformacoes], [ALGORITMO_TRANSFORMACAO, ALGORITMO_C14N]
		)

	def test_uri_aponta_para_o_id(self):
		self.assertEqual(self.bloco["Reference"]["@URI"], "#NFe123")

	def test_digest_vazio_e_erro(self):
		with self.assertRaises(AssinaturaInvalida):
			montar_signed_info("NFe123", "")

	def test_ordem_dos_elementos(self):
		self.assertEqual(
			list(self.bloco), ["CanonicalizationMethod", "SignatureMethod", "Reference"]
		)


class TestSignature(unittest.TestCase):
	def setUp(self):
		self.bloco = montar_signature("NFe123", MATERIAL)["Signature"]

	def test_namespace_dsig(self):
		self.assertEqual(self.bloco["@xmlns"], "http://www.w3.org/2000/09/xmldsig#")

	def test_partes_obrigatorias_e_ordem(self):
		self.assertEqual(
			[c for c in self.bloco if not c.startswith("@")],
			["SignedInfo", "SignatureValue", "KeyInfo"],
		)

	def test_certificado_embutido(self):
		self.assertEqual(
			self.bloco["KeyInfo"]["X509Data"]["X509Certificate"], MATERIAL.certificado
		)

	def test_assinatura_vazia_e_erro(self):
		with self.assertRaises(AssinaturaInvalida):
			montar_signature("NFe123", MaterialAssinatura(digest="d", assinatura="", certificado="c"))

	def test_certificado_ausente_e_erro(self):
		with self.assertRaises(AssinaturaInvalida) as ctx:
			montar_signature("NFe123", MaterialAssinatura(digest="d", assinatura="a", certificado=""))

		self.assertIn("validar quem assinou", str(ctx.exception))

	def test_serializa_para_xml(self):
		xml = para_xml(montar_signature("NFe123", MATERIAL))

		self.assertTrue(xml.startswith("<Signature "))
		self.assertIn('URI="#NFe123"', xml)
		self.assertIn("<DigestValue>ZGlnZXN0</DigestValue>", xml)
		self.assertIn(ALGORITMO_ASSINATURA, xml)


class AssinadorFalso:
	"""Duplo que satisfaz a porta sem precisar de certificado."""

	def __init__(self):
		self.chamadas = []

	def assinar(self, xml: bytes, id_elemento: str) -> MaterialAssinatura:
		self.chamadas.append((xml, id_elemento))

		return MATERIAL


class TestPortaDeAssinatura(unittest.TestCase):
	def test_duplo_satisfaz_o_contrato(self):
		self.assertIsInstance(AssinadorFalso(), Assinador)

	def test_material_do_assinador_monta_a_signature(self):
		assinador = AssinadorFalso()
		material = assinador.assinar(b"<NFe/>", "NFe123")
		bloco = montar_signature("NFe123", material)

		self.assertEqual(bloco["Signature"]["SignatureValue"], MATERIAL.assinatura)
		self.assertEqual(assinador.chamadas[0][1], "NFe123")


if __name__ == "__main__":
	unittest.main()
