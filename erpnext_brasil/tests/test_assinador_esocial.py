# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `AssinadorLocalEsocial` com certificado autoassinado — mesmo padrão de
`test_assinador_local.py` (NF-e): certificado gerado em memória, prova que o
**mecanismo** funciona (canonicaliza, calcula digest SHA-256, assina RSA-SHA256,
verifica com a chave pública), não que um certificado real seria aceito pelo eSocial.

Toda a suíte é pulada quando `cryptography`/`lxml` não estão instalados.
"""

import unittest
from datetime import datetime, timedelta, timezone

try:
	from cryptography import x509
	from cryptography.hazmat.primitives import hashes, serialization
	from cryptography.hazmat.primitives.asymmetric import rsa
	from cryptography.hazmat.primitives.serialization import pkcs12
	from cryptography.x509.oid import NameOID

	TEM_DEPENDENCIAS = True
except ImportError:
	TEM_DEPENDENCIAS = False

from erpnext_brasil.folha.esocial_assinatura import AssinaturaInvalida


def _gerar_pfx(senha: str = "teste123") -> bytes:
	"""Mesmo gerador de `test_assinador_local.py` — duplicado deliberadamente para
	manter os dois arquivos de teste independentes (nenhum importa do outro)."""
	chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)

	nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Emissor de Teste")])
	agora = datetime.now(timezone.utc)

	certificado = (
		x509.CertificateBuilder()
		.subject_name(nome)
		.issuer_name(nome)
		.public_key(chave.public_key())
		.serial_number(x509.random_serial_number())
		.not_valid_before(agora - timedelta(days=1))
		.not_valid_after(agora + timedelta(days=365))
		.sign(chave, hashes.SHA256())
	)

	return pkcs12.serialize_key_and_certificates(
		name=b"teste",
		key=chave,
		cert=certificado,
		cas=None,
		encryption_algorithm=serialization.BestAvailableEncryption(senha.encode("utf-8")),
	)


@unittest.skipUnless(TEM_DEPENDENCIAS, "requer cryptography e lxml, disponíveis no bench")
class TestAssinadorLocalEsocial(unittest.TestCase):
	def setUp(self):
		from erpnext_brasil.integracao.assinador_esocial import AssinadorLocalEsocial

		self.pfx = _gerar_pfx()
		self.assinador = AssinadorLocalEsocial(self.pfx, "teste123")
		self.xml = (
			b'<eSocial xmlns="http://www.esocial.gov.br/schema/evt/evtRemun/v_S_01_03_00">'
			b'<evtRemun Id="ID1234567890"><a>1</a></evtRemun></eSocial>'
		)

	def test_material_tem_as_tres_partes(self):
		material = self.assinador.assinar(self.xml, "ID1234567890")

		self.assertTrue(material.digest)
		self.assertTrue(material.assinatura)
		self.assertTrue(material.certificado)

	def test_assinatura_verifica_com_a_chave_publica_usando_sha256(self):
		"""Prova o ponto central da divergência com a NF-e: a verificação só passa
		com SHA-256 — verificar com SHA-1 (o hash da NF-e) tem que falhar."""
		import base64

		from cryptography.exceptions import InvalidSignature
		from cryptography.hazmat.primitives.asymmetric import padding

		from erpnext_brasil.fiscal.documento.serializacao import para_xml
		from erpnext_brasil.folha.esocial_assinatura import montar_signed_info

		material = self.assinador.assinar(self.xml, "ID1234567890")

		chave_publica = pkcs12.load_key_and_certificates(self.pfx, b"teste123")[1].public_key()

		signed_info = montar_signed_info("ID1234567890", material.digest)
		xml_signed_info = para_xml(signed_info, namespace="http://www.w3.org/2000/09/xmldsig#")

		from lxml import etree

		elemento = etree.fromstring(xml_signed_info.encode("utf-8"))
		canonicalizado = etree.tostring(elemento, method="c14n", exclusive=False, with_comments=False)

		try:
			chave_publica.verify(
				base64.b64decode(material.assinatura), canonicalizado, padding.PKCS1v15(), hashes.SHA256()
			)
		except InvalidSignature:
			self.fail("A assinatura produzida não confere com a chave pública usando SHA-256")

		with self.assertRaises(InvalidSignature):
			chave_publica.verify(
				base64.b64decode(material.assinatura), canonicalizado, padding.PKCS1v15(), hashes.SHA1()
			)

	def test_digest_muda_se_o_conteudo_mudar(self):
		outro_xml = self.xml.replace(b"<a>1</a>", b"<a>2</a>")

		digest1 = self.assinador.assinar(self.xml, "ID1234567890").digest
		digest2 = self.assinador.assinar(outro_xml, "ID1234567890").digest

		self.assertNotEqual(digest1, digest2)

	def test_id_inexistente_e_erro(self):
		with self.assertRaises(AssinaturaInvalida):
			self.assinador.assinar(self.xml, "IDNaoExiste")

	def test_certificado_no_material_bate_com_o_carregado(self):
		import base64

		from cryptography.hazmat.primitives.serialization import Encoding

		_, certificado = pkcs12.load_key_and_certificates(self.pfx, b"teste123")[:2]
		esperado = base64.b64encode(certificado.public_bytes(Encoding.DER)).decode("ascii")

		material = self.assinador.assinar(self.xml, "ID1234567890")

		self.assertEqual(material.certificado, esperado)


if __name__ == "__main__":
	unittest.main()
