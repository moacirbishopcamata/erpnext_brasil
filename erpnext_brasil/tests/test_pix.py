# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/pix.py` — payload Pix (BR Code / "Copia e Cola")."""

import unittest
from decimal import Decimal

from erpnext_brasil.contabil.pix import (
	CODIGO_PAIS,
	MOEDA_REAL,
	PONTO_INICIACAO_DINAMICO,
	PONTO_INICIACAO_ESTATICO,
	PixInvalido,
	_crc16_ccitt_false,
	montar_payload,
)


def _decodificar_tlv(payload: str) -> dict:
	"""Parser TLV independente da montagem — usado só para os testes conferirem a
	estrutura de verdade, não confiar cegamente no que `montar_payload` produziu."""
	campos = {}
	i = 0

	while i < len(payload):
		id_campo = payload[i : i + 2]
		tamanho = int(payload[i + 2 : i + 4])
		valor = payload[i + 4 : i + 4 + tamanho]
		campos[id_campo] = valor
		i += 4 + tamanho

	return campos


class TestCrc16CcittFalse(unittest.TestCase):
	def test_vetor_de_teste_padrao(self):
		"""CRC16-CCITT-FALSE("123456789") == 0x29B1 — vetor de teste universal
		desta variante, citado por praticamente toda implementação de referência."""
		self.assertEqual(_crc16_ccitt_false(b"123456789"), "29B1")

	def test_string_vazia(self):
		self.assertEqual(_crc16_ccitt_false(b""), "FFFF")


class TestMontarPayload(unittest.TestCase):
	def test_estrutura_basica(self):
		payload = montar_payload(
			chave_pix="12345678901", nome_recebedor="Maria Silva", cidade_recebedor="Sao Paulo"
		)
		campos = _decodificar_tlv(payload)

		self.assertEqual(campos["00"], "01")
		self.assertEqual(campos["01"], PONTO_INICIACAO_ESTATICO)
		self.assertEqual(campos["52"], "0000")
		self.assertEqual(campos["53"], MOEDA_REAL)
		self.assertEqual(campos["58"], CODIGO_PAIS)
		self.assertEqual(campos["59"], "Maria Silva")
		self.assertEqual(campos["60"], "Sao Paulo")

	def test_conta_carrega_gui_e_chave(self):
		payload = montar_payload(
			chave_pix="12345678901", nome_recebedor="Maria Silva", cidade_recebedor="Sao Paulo"
		)
		campos = _decodificar_tlv(payload)
		subcampos = _decodificar_tlv(campos["26"])

		self.assertEqual(subcampos["00"], "br.gov.bcb.pix")
		self.assertEqual(subcampos["01"], "12345678901")

	def test_dinamico_usa_ponto_de_iniciacao_12(self):
		payload = montar_payload(
			chave_pix="12345678901", nome_recebedor="Maria Silva", cidade_recebedor="Sao Paulo", dinamico=True
		)
		campos = _decodificar_tlv(payload)

		self.assertEqual(campos["01"], PONTO_INICIACAO_DINAMICO)

	def test_valor_omitido_por_padrao(self):
		payload = montar_payload(
			chave_pix="12345678901", nome_recebedor="Maria Silva", cidade_recebedor="Sao Paulo"
		)
		campos = _decodificar_tlv(payload)

		self.assertNotIn("54", campos)

	def test_valor_informado_aparece_com_duas_casas(self):
		payload = montar_payload(
			chave_pix="12345678901",
			nome_recebedor="Maria Silva",
			cidade_recebedor="Sao Paulo",
			valor=Decimal("25.7"),
		)
		campos = _decodificar_tlv(payload)

		self.assertEqual(campos["54"], "25.70")

	def test_valor_zero_ou_negativo_e_erro(self):
		with self.assertRaises(PixInvalido):
			montar_payload(
				chave_pix="12345678901",
				nome_recebedor="Maria Silva",
				cidade_recebedor="Sao Paulo",
				valor=Decimal("0"),
			)

	def test_txid_padrao_e_asteriscos(self):
		payload = montar_payload(
			chave_pix="12345678901", nome_recebedor="Maria Silva", cidade_recebedor="Sao Paulo"
		)
		campos = _decodificar_tlv(payload)
		additional = _decodificar_tlv(campos["62"])

		self.assertEqual(additional["05"], "***")

	def test_txid_informado(self):
		payload = montar_payload(
			chave_pix="12345678901",
			nome_recebedor="Maria Silva",
			cidade_recebedor="Sao Paulo",
			txid="PEDIDO123",
		)
		campos = _decodificar_tlv(payload)
		additional = _decodificar_tlv(campos["62"])

		self.assertEqual(additional["05"], "PEDIDO123")

	def test_acentos_sao_removidos(self):
		payload = montar_payload(
			chave_pix="12345678901", nome_recebedor="José São João", cidade_recebedor="São Paulo"
		)
		campos = _decodificar_tlv(payload)

		self.assertEqual(campos["59"], "Jose Sao Joao")
		self.assertEqual(campos["60"], "Sao Paulo")

	def test_nome_truncado_em_25_caracteres(self):
		nome_longo = "Empresa Comercial Ltda de Produtos e Servicos"
		payload = montar_payload(
			chave_pix="12345678901", nome_recebedor=nome_longo, cidade_recebedor="Sao Paulo"
		)
		campos = _decodificar_tlv(payload)

		self.assertEqual(len(campos["59"]), 25)
		self.assertEqual(campos["59"], nome_longo[:25])

	def test_chave_vazia_e_erro(self):
		with self.assertRaises(PixInvalido):
			montar_payload(chave_pix="", nome_recebedor="Maria Silva", cidade_recebedor="Sao Paulo")

	def test_nome_vazio_e_erro(self):
		with self.assertRaises(PixInvalido):
			montar_payload(chave_pix="12345678901", nome_recebedor="", cidade_recebedor="Sao Paulo")

	def test_crc_no_final_bate_com_o_recalculo(self):
		"""O CRC dos últimos 4 caracteres precisa bater com o CRC recalculado sobre
		tudo antes dele — prova de auto-consistência, não só de formato."""
		payload = montar_payload(
			chave_pix="12345678901",
			nome_recebedor="Maria Silva",
			cidade_recebedor="Sao Paulo",
			valor=Decimal("100.00"),
			txid="ABC123",
		)

		crc_no_payload = payload[-4:]
		recalculado = _crc16_ccitt_false(payload[:-4].encode("utf-8"))

		self.assertEqual(crc_no_payload, recalculado)

	def test_payload_comeca_com_000201(self):
		"""Todo payload Pix/EMV MPM válido começa com 000201 (Payload Format
		Indicator = versão 01) — confirmado por múltiplas fontes concordantes."""
		payload = montar_payload(
			chave_pix="12345678901", nome_recebedor="Maria Silva", cidade_recebedor="Sao Paulo"
		)

		self.assertTrue(payload.startswith("000201"))


if __name__ == "__main__":
	unittest.main()
