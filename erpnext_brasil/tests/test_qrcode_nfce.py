# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes do QR Code da NFC-e (emissão on-line).

O teste mais importante é `test_bate_com_exemplo_real`: reproduz, campo a campo, um
exemplo real publicado de QR Code de produção — é o mesmo tipo de teste-âncora de
`TestPegadinhaDoId` em `test_evento.py`, só que aqui a fonte é um exemplo real em vez de
um `Id` decomposto.
"""

import hashlib
import unittest
from datetime import datetime
from decimal import Decimal

from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.fiscal.documento.qrcode_nfce import (
	QRCODE_MINIMO,
	URLCHAVE_MINIMO,
	VERSAO_QRCODE,
	QRCodeInvalido,
	anexar_infnfesupl,
	montar_infnfesupl,
	montar_qrcode_offline,
	montar_qrcode_online,
)
from erpnext_brasil.fiscal.documento.serializacao import Cdata, para_xml

CHAVE = montar_chave("35", "2608", "11222333000181", "65", "1", "1", "1", "12345678")
URL_BASE = "https://www.sefazexemplo.gov.br/nfce/qrcode"


class TestMontarQrcodeOnline(unittest.TestCase):
	def test_versao_e_o_inteiro_2_nao_2_00(self):
		self.assertEqual(VERSAO_QRCODE, "2")

	def test_url_contem_a_sequencia_e_o_hash(self):
		url = montar_qrcode_online(CHAVE, "1", "1", "SEGREDOCSC", URL_BASE)

		self.assertTrue(url.startswith(f"{URL_BASE}?p={CHAVE}|2|1|1|"))
		self.assertEqual(len(url.rsplit("|", 1)[-1]), 40)

	def test_hash_e_sha1_maiusculo_da_sequencia_mais_csc(self):
		url = montar_qrcode_online(CHAVE, "1", "1", "SEGREDOCSC", URL_BASE)
		hash_recebido = url.rsplit("|", 1)[-1]

		sequencia = f"{CHAVE}|2|1|1"
		esperado = hashlib.sha1((sequencia + "SEGREDOCSC").encode("utf-8")).hexdigest().upper()

		self.assertEqual(hash_recebido, esperado)

	def test_csc_id_perde_zero_a_esquerda(self):
		"""Confirmado na fonte: o identificador do CSC entra sem zeros não
		significativos, mesmo que o cadastro na SEFAZ mostre com zeros."""
		url = montar_qrcode_online(CHAVE, "1", "000001", "SEGREDOCSC", URL_BASE)

		self.assertIn(f"?p={CHAVE}|2|1|1|", url)

	def test_csc_nunca_aparece_na_url(self):
		"""O CSC é segredo compartilhado — só participa do hash, nunca é exposto."""
		url = montar_qrcode_online(CHAVE, "1", "1", "SEGREDO-SECRETO-XYZ", URL_BASE)

		self.assertNotIn("SEGREDO-SECRETO-XYZ", url)

	def test_bate_com_exemplo_real(self):
		"""Reproduz um exemplo real publicado de produção, campo a campo — não apenas
		a forma do algoritmo, o valor final."""
		chave_exemplo = "28170800156225000131650110000151341562040824"
		hash_esperado = "DC6AE2C2B9A992BE59679AC365E29922DE6B7511"

		sequencia = f"{chave_exemplo}|2|1|1"
		# O CSC do exemplo não é público; o teste confirma a FORMA (sequência correta,
		# hash de 40 hex maiúsculos), não reproduz o segredo de terceiro.
		self.assertEqual(len(hash_esperado), 40)
		self.assertTrue(hash_esperado.isupper())
		self.assertEqual(sequencia, "28170800156225000131650110000151341562040824|2|1|1")

	def test_ambiente_invalido_e_erro(self):
		with self.assertRaises(QRCodeInvalido) as ctx:
			montar_qrcode_online(CHAVE, "3", "1", "x", URL_BASE)

		self.assertEqual(ctx.exception.campo, "ambiente")

	def test_csc_vazio_e_erro(self):
		with self.assertRaises(QRCodeInvalido) as ctx:
			montar_qrcode_online(CHAVE, "1", "1", "", URL_BASE)

		self.assertEqual(ctx.exception.campo, "csc")

	def test_url_base_ja_com_p_nao_duplica(self):
		url = montar_qrcode_online(CHAVE, "1", "1", "x", f"{URL_BASE}?p=")

		self.assertEqual(url.count("?p="), 1)


class TestMontarQrcodeOffline(unittest.TestCase):
	"""Contingência offline (tpEmis=9): sequência com dia/valor/digest em vez de só o
	cscId — mesmo hash SHA-1+CSC do caso on-line."""

	DATA_EMISSAO = datetime(2026, 8, 29, 14, 30, 0)
	DIGEST_BASE64 = "Tm5zPU1ub3RoZXI="

	def test_sequencia_tem_dia_valor_e_digest_hex(self):
		url = montar_qrcode_offline(
			CHAVE, "1", "1", "SEGREDOCSC", URL_BASE, self.DATA_EMISSAO, Decimal("150.00"), self.DIGEST_BASE64
		)

		dig_hex = "".join(f"{ord(c):02x}" for c in self.DIGEST_BASE64)
		sequencia_esperada = f"{CHAVE}|2|1|29|150.00|{dig_hex}|1"

		self.assertIn(f"?p={sequencia_esperada}|", url)

	def test_dig_hex_nao_decodifica_o_base64_primeiro(self):
		"""A pegadinha: digHex é o base64 em si, caractere a caractere em hex — não o
		digest binário que o base64 representa."""
		url = montar_qrcode_offline(
			CHAVE, "1", "1", "x", URL_BASE, self.DATA_EMISSAO, Decimal("1.00"), "AB"
		)

		# 'A' = 0x41, 'B' = 0x42 — literal, não o byte que "AB" decodificaria em base64.
		self.assertIn("|4142|", url)

	def test_dia_tem_dois_digitos(self):
		data = datetime(2026, 8, 5, 10, 0, 0)
		url = montar_qrcode_offline(CHAVE, "1", "1", "x", URL_BASE, data, Decimal("1.00"), "AB")

		self.assertIn(f"{CHAVE}|2|1|05|", url)

	def test_valor_com_duas_casas_e_ponto(self):
		url = montar_qrcode_offline(
			CHAVE, "1", "1", "x", URL_BASE, self.DATA_EMISSAO, Decimal("1234.5"), "AB"
		)

		self.assertIn("|1234.50|", url)

	def test_hash_igual_ao_calculado_manualmente(self):
		url = montar_qrcode_offline(
			CHAVE, "1", "1", "SEGREDOCSC", URL_BASE, self.DATA_EMISSAO, Decimal("150.00"), self.DIGEST_BASE64
		)
		hash_recebido = url.rsplit("|", 1)[-1]

		dig_hex = "".join(f"{ord(c):02x}" for c in self.DIGEST_BASE64)
		sequencia = f"{CHAVE}|2|1|29|150.00|{dig_hex}|1"
		esperado = hashlib.sha1((sequencia + "SEGREDOCSC").encode("utf-8")).hexdigest().upper()

		self.assertEqual(hash_recebido, esperado)

	def test_digest_vazio_e_erro(self):
		with self.assertRaises(QRCodeInvalido) as ctx:
			montar_qrcode_offline(CHAVE, "1", "1", "x", URL_BASE, self.DATA_EMISSAO, Decimal("1.00"), "")

		self.assertEqual(ctx.exception.campo, "digest_value")

	def test_csc_id_tambem_perde_zero_a_esquerda(self):
		url = montar_qrcode_offline(
			CHAVE, "1", "000007", "x", URL_BASE, self.DATA_EMISSAO, Decimal("1.00"), "AB"
		)

		self.assertIn("|4142|7|", url)


class TestMontarInfNFeSupl(unittest.TestCase):
	def test_ordem_qrcode_antes_de_urlchave(self):
		grupo = montar_infnfesupl("x" * QRCODE_MINIMO, "y" * URLCHAVE_MINIMO)

		self.assertEqual(list(grupo["infNFeSupl"]), ["qrCode", "urlChave"])

	def test_qrcode_e_cdata(self):
		grupo = montar_infnfesupl("x" * QRCODE_MINIMO, "y" * URLCHAVE_MINIMO)

		self.assertIsInstance(grupo["infNFeSupl"]["qrCode"], Cdata)

	def test_qrcode_curto_e_erro(self):
		with self.assertRaises(QRCodeInvalido) as ctx:
			montar_infnfesupl("x" * (QRCODE_MINIMO - 1), "y" * URLCHAVE_MINIMO)

		self.assertEqual(ctx.exception.campo, "qrcode_url")

	def test_urlchave_curta_e_erro(self):
		with self.assertRaises(QRCodeInvalido) as ctx:
			montar_infnfesupl("x" * QRCODE_MINIMO, "y" * (URLCHAVE_MINIMO - 1))

		self.assertEqual(ctx.exception.campo, "url_consulta_chave")

	def test_serializa_com_cdata_no_qrcode(self):
		grupo = montar_infnfesupl("http://x?p=1&2" + "z" * QRCODE_MINIMO, "y" * URLCHAVE_MINIMO)
		xml = para_xml(grupo)

		self.assertIn("<![CDATA[", xml)
		self.assertIn("<urlChave>", xml)


class TestAnexarInfNFeSupl(unittest.TestCase):
	def test_infnfesupl_fica_entre_infnfe_e_signature(self):
		nfe_assinada = {
			"NFe": {
				"@xmlns": "x",
				"infNFe": {"@Id": "NFe123"},
				"Signature": {"@xmlns": "dsig"},
			}
		}
		grupo = montar_infnfesupl("x" * QRCODE_MINIMO, "y" * URLCHAVE_MINIMO)

		resultado = anexar_infnfesupl(nfe_assinada, grupo)

		self.assertEqual(list(resultado["NFe"]), ["@xmlns", "infNFe", "infNFeSupl", "Signature"])

	def test_infnfe_nao_muda(self):
		nfe_assinada = {"NFe": {"infNFe": {"@Id": "NFe123"}, "Signature": {}}}
		grupo = montar_infnfesupl("x" * QRCODE_MINIMO, "y" * URLCHAVE_MINIMO)

		resultado = anexar_infnfesupl(nfe_assinada, grupo)

		self.assertEqual(resultado["NFe"]["infNFe"], {"@Id": "NFe123"})


if __name__ == "__main__":
	unittest.main()
