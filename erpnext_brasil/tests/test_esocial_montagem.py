# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_montagem.py` — a orquestração serializar→assinar→mesclar.

`_AssinadorFalso` prova que o módulo é mesmo puro: a orquestração inteira roda sem
`cryptography`/`lxml` instalados, porque o assinador é injetado. Um segundo bloco de
testes (`TestComAssinadorDeVerdade`) roda a mesma orquestração com
`AssinadorLocalEsocial` de verdade, provando que a peça pura e a peça criptográfica
realmente se encaixam — não só cada uma isolada.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.folha.esocial_assinatura import AssinaturaInvalida, MaterialAssinatura
from erpnext_brasil.folha.esocial_montagem import montar_evento_assinado
from erpnext_brasil.folha.esocial_s1200 import (
	AMBIENTE_PRODUCAO,
	INDICADOR_APURACAO_MENSAL,
	DmDev,
	IdeEmpregador,
	IdeEstabLot,
	IdeEvento,
	IdeTrabalhador,
	InfoPerApur,
	ItemRemuneracao,
	RemunPerApur,
)
from erpnext_brasil.folha.esocial_serializacao import montar_evt_remun

try:
	import cryptography  # noqa: F401
	import lxml  # noqa: F401

	TEM_DEPENDENCIAS = True
except ImportError:
	TEM_DEPENDENCIAS = False


class _AssinadorFalso:
	"""Implementa o `Protocol` `Assinador` sem nenhuma criptografia — devolve
	material fixo, só registra o que recebeu para os testes conferirem."""

	def __init__(self):
		self.chamadas = []

	def assinar(self, xml: bytes, id_elemento: str) -> MaterialAssinatura:
		self.chamadas.append((xml, id_elemento))

		return MaterialAssinatura(
			digest="digestFalso==", assinatura="assinaturaFalsa==", certificado="certFalso=="
		)


def _arvore_minima(id_evento: str = "ID1234567890") -> dict:
	ide_evento = IdeEvento(
		ind_retif=1,
		ind_apuracao=INDICADOR_APURACAO_MENSAL,
		per_apur="2026-01",
		tp_amb=AMBIENTE_PRODUCAO,
		proc_emi=1,
		ver_proc="ERPNextBrasil-1.0",
	)
	ide_empregador = IdeEmpregador(tp_insc=1, nr_insc="12345678000199")
	ide_trabalhador = IdeTrabalhador(cpf_trab="12345678901")
	item = ItemRemuneracao(cod_rubr="9001", vr_rubr=Decimal("155.68"))
	remun = RemunPerApur(itens_remun=(item,))
	estab_lot = IdeEstabLot(tp_insc=1, nr_insc="12345678000199", cod_lotacao="1", remun_per_apur=(remun,))
	dm_dev = DmDev(ide_dm_dev="1", cod_categ=101, info_per_apur=InfoPerApur(ide_estab_lot=(estab_lot,)))

	return montar_evt_remun(id_evento, ide_evento, ide_empregador, ide_trabalhador, (dm_dev,))


class TestMontarEventoAssinadoComAssinadorFalso(unittest.TestCase):
	def test_devolve_xml_com_signature(self):
		assinador = _AssinadorFalso()

		xml = montar_evento_assinado(_arvore_minima(), "ID1234567890", assinador)

		self.assertIn("<Signature", xml)
		self.assertIn("<SignatureValue>assinaturaFalsa==</SignatureValue>", xml)

	def test_signature_e_irma_do_elemento_do_evento_nao_filha(self):
		assinador = _AssinadorFalso()

		xml = montar_evento_assinado(_arvore_minima(), "ID1234567890", assinador)

		# Signature fecha depois de evtRemun já ter fechado — irmã, não filha.
		posicao_fim_evt_remun = xml.index("</evtRemun>")
		posicao_signature = xml.index("<Signature")

		self.assertGreater(posicao_signature, posicao_fim_evt_remun)

	def test_assinador_recebe_o_xml_sem_assinatura_e_o_id_correto(self):
		assinador = _AssinadorFalso()

		montar_evento_assinado(_arvore_minima(), "ID1234567890", assinador)

		self.assertEqual(len(assinador.chamadas), 1)
		xml_recebido, id_recebido = assinador.chamadas[0]

		self.assertEqual(id_recebido, "ID1234567890")
		self.assertNotIn(b"Signature", xml_recebido)
		self.assertIn(b'Id="ID1234567890"', xml_recebido)

	def test_arvore_com_raiz_multipla_e_erro(self):
		assinador = _AssinadorFalso()

		with self.assertRaises(AssinaturaInvalida):
			montar_evento_assinado({"A": {}, "B": {}}, "ID1", assinador)

	def test_resultado_e_xml_bem_formado(self):
		try:
			from lxml import etree
		except ImportError:
			self.skipTest("requer lxml, disponível no bench")

		assinador = _AssinadorFalso()
		xml = montar_evento_assinado(_arvore_minima(), "ID1234567890", assinador)

		etree.fromstring(xml.encode("utf-8"))  # não deve lançar


@unittest.skipUnless(TEM_DEPENDENCIAS, "requer cryptography e lxml, disponíveis no bench")
class TestComAssinadorDeVerdade(unittest.TestCase):
	"""A peça pura (`montar_evento_assinado`) e a peça criptográfica
	(`AssinadorLocalEsocial`) encaixadas de ponta a ponta — não só cada uma isolada."""

	def test_evento_assinado_de_verdade_analisa_sem_erro_e_verifica(self):
		import base64
		from datetime import datetime, timedelta, timezone

		from cryptography import x509
		from cryptography.hazmat.primitives import hashes, serialization
		from cryptography.hazmat.primitives.asymmetric import padding, rsa
		from cryptography.hazmat.primitives.serialization import pkcs12
		from cryptography.x509.oid import NameOID
		from lxml import etree

		from erpnext_brasil.fiscal.documento.serializacao import para_xml
		from erpnext_brasil.folha.esocial_assinatura import montar_signed_info
		from erpnext_brasil.integracao.assinador_esocial import AssinadorLocalEsocial

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
		pfx = pkcs12.serialize_key_and_certificates(
			name=b"teste",
			key=chave,
			cert=certificado,
			cas=None,
			encryption_algorithm=serialization.BestAvailableEncryption(b"teste123"),
		)

		assinador = AssinadorLocalEsocial(pfx, "teste123")

		xml_assinado = montar_evento_assinado(_arvore_minima(), "ID1234567890", assinador)

		raiz = etree.fromstring(xml_assinado.encode("utf-8"))
		self.assertEqual(etree.QName(raiz).localname, "eSocial")

		# A assinatura dentro do XML final confere com a chave pública do
		# certificado — não só "o XML tem uma tag Signature".
		digest_element = raiz.find(".//{http://www.w3.org/2000/09/xmldsig#}DigestValue")
		signature_value_element = raiz.find(".//{http://www.w3.org/2000/09/xmldsig#}SignatureValue")

		signed_info = montar_signed_info("ID1234567890", digest_element.text)
		xml_signed_info = para_xml(signed_info, namespace="http://www.w3.org/2000/09/xmldsig#")
		elemento_signed_info = etree.fromstring(xml_signed_info.encode("utf-8"))
		canonicalizado = etree.tostring(
			elemento_signed_info, method="c14n", exclusive=False, with_comments=False
		)

		chave_publica = pkcs12.load_key_and_certificates(pfx, b"teste123")[1].public_key()

		chave_publica.verify(
			base64.b64decode(signature_value_element.text),
			canonicalizado,
			padding.PKCS1v15(),
			hashes.SHA256(),
		)  # não deve lançar InvalidSignature


if __name__ == "__main__":
	unittest.main()
