# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `AssinadorLocal` com certificado autoassinado.

Não é um certificado A1 real — é gerado em memória, só para exercitar o código de
verdade (carregar PKCS#12, checar validade, canonicalizar, assinar) sem depender de um
certificado emitido por autoridade certificadora. O que se prova aqui é que o
**mecanismo** funciona; a aceitação pela SEFAZ depende de um certificado de verdade, que
este teste não substitui.

Toda a suíte é pulada quando `cryptography`/`lxml` não estão instalados — como no
ambiente puro fora do bench, antes desta dependência ter sido instalada nesta sessão.
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

from erpnext_brasil.fiscal.documento.assinatura import AssinaturaInvalida, CertificadoExpirado


def _gerar_pfx(dias_validade: int = 365, comeca_em_dias: int = 0, senha: str = "teste123") -> bytes:
	"""Monta um certificado autoassinado + chave, empacotados em PKCS#12."""
	chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)

	nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Emissor de Teste")])
	agora = datetime.now(timezone.utc)

	certificado = (
		x509.CertificateBuilder()
		.subject_name(nome)
		.issuer_name(nome)
		.public_key(chave.public_key())
		.serial_number(x509.random_serial_number())
		.not_valid_before(agora + timedelta(days=comeca_em_dias))
		.not_valid_after(agora + timedelta(days=comeca_em_dias + dias_validade))
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
class TestCarregarCertificado(unittest.TestCase):
	def test_carrega_certificado_valido(self):
		from erpnext_brasil.integracao.assinador_local import carregar_certificado

		chave, certificado = carregar_certificado(_gerar_pfx(), "teste123")

		self.assertIsNotNone(chave)
		self.assertIsNotNone(certificado)

	def test_senha_errada_e_erro_claro(self):
		from erpnext_brasil.integracao.assinador_local import carregar_certificado

		with self.assertRaises(AssinaturaInvalida) as ctx:
			carregar_certificado(_gerar_pfx(senha="correta"), "errada")

		self.assertIn("senha", str(ctx.exception).lower())

	def test_arquivo_vazio_e_erro(self):
		from erpnext_brasil.integracao.assinador_local import carregar_certificado

		with self.assertRaises(AssinaturaInvalida):
			carregar_certificado(b"", "qualquer")

	def test_certificado_vencido_e_erro_especifico(self):
		"""Vencido produz assinatura tecnicamente correta e documento rejeitado —
		por isso tem tipo de erro próprio, não um AssinaturaInvalida genérico."""
		from erpnext_brasil.integracao.assinador_local import carregar_certificado

		vencido = _gerar_pfx(dias_validade=10, comeca_em_dias=-30)

		with self.assertRaises(CertificadoExpirado):
			carregar_certificado(vencido, "teste123")

	def test_certificado_ainda_nao_valido_e_erro(self):
		from erpnext_brasil.integracao.assinador_local import carregar_certificado

		futuro = _gerar_pfx(comeca_em_dias=30)

		with self.assertRaises(CertificadoExpirado):
			carregar_certificado(futuro, "teste123")

	def test_certificado_expirado_e_subclasse_de_assinatura_invalida(self):
		"""Quem só trata o erro genérico continua funcionando."""
		self.assertTrue(issubclass(CertificadoExpirado, AssinaturaInvalida))


@unittest.skipUnless(TEM_DEPENDENCIAS, "requer cryptography e lxml, disponíveis no bench")
class TestAssinarDeVerdade(unittest.TestCase):
	"""Assina com o certificado de teste e confere com a chave pública — não confia
	cegamente no que `assinar()` devolve."""

	def setUp(self):
		from erpnext_brasil.integracao.assinador_local import AssinadorLocal

		self.pfx = _gerar_pfx()
		self.assinador = AssinadorLocal(self.pfx, "teste123")
		self.xml = b'<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe Id="NFe123"><a>1</a></infNFe></NFe>'

	def test_material_tem_as_tres_partes(self):
		material = self.assinador.assinar(self.xml, "NFe123")

		self.assertTrue(material.digest)
		self.assertTrue(material.assinatura)
		self.assertTrue(material.certificado)

	def test_assinatura_verifica_com_a_chave_publica(self):
		"""Não basta a função devolver algo — a assinatura precisa ser válida de verdade."""
		import base64

		from cryptography.exceptions import InvalidSignature
		from cryptography.hazmat.primitives.asymmetric import padding

		from erpnext_brasil.fiscal.documento.assinatura import montar_signed_info
		from erpnext_brasil.fiscal.documento.serializacao import para_xml

		material = self.assinador.assinar(self.xml, "NFe123")

		chave_publica, certificado = pkcs12.load_key_and_certificates(
			self.pfx, b"teste123"
		)[1].public_key(), None

		signed_info = montar_signed_info("NFe123", material.digest)
		xml_signed_info = para_xml(signed_info, namespace="http://www.w3.org/2000/09/xmldsig#")

		from lxml import etree

		elemento = etree.fromstring(xml_signed_info.encode("utf-8"))
		canonicalizado = etree.tostring(elemento, method="c14n", exclusive=False, with_comments=False)

		try:
			chave_publica.verify(
				base64.b64decode(material.assinatura),
				canonicalizado,
				padding.PKCS1v15(),
				hashes.SHA1(),
			)
		except InvalidSignature:
			self.fail("A assinatura produzida não confere com a chave pública do certificado")

	def test_digest_muda_se_o_conteudo_mudar(self):
		outro_xml = b'<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe Id="NFe123"><a>2</a></infNFe></NFe>'

		digest1 = self.assinador.assinar(self.xml, "NFe123").digest
		digest2 = self.assinador.assinar(outro_xml, "NFe123").digest

		self.assertNotEqual(digest1, digest2)

	def test_id_inexistente_e_erro(self):
		with self.assertRaises(AssinaturaInvalida):
			self.assinador.assinar(self.xml, "NFeNaoExiste")

	def test_certificado_no_material_bate_com_o_carregado(self):
		import base64

		from cryptography.hazmat.primitives.serialization import Encoding

		_, certificado = pkcs12.load_key_and_certificates(self.pfx, b"teste123")[:2]
		esperado = base64.b64encode(certificado.public_bytes(Encoding.DER)).decode("ascii")

		material = self.assinador.assinar(self.xml, "NFe123")

		self.assertEqual(material.certificado, esperado)


if __name__ == "__main__":
	unittest.main()
