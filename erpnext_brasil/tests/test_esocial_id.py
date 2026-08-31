# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_id.py` — geração do `Id` de 36 caracteres do evento."""

import unittest
from datetime import datetime

from erpnext_brasil.folha.esocial_id import (
	TIPO_INSCRICAO_CNPJ,
	TIPO_INSCRICAO_CPF,
	EsocialIdInvalido,
	gerar_id_evento,
)


class TestGerarIdEvento(unittest.TestCase):
	def test_tamanho_e_sempre_36(self):
		id_evento = gerar_id_evento(TIPO_INSCRICAO_CNPJ, "12345678000199", datetime(2026, 1, 15, 13, 42, 47))

		self.assertEqual(len(id_evento), 36)

	def test_estrutura_posicao_a_posicao_com_cnpj(self):
		"""Confere a aritmética das posições (2+1+14+8+6+5=36) contra um CNPJ que já
		tem os 14 dígitos — não precisa de padding."""
		id_evento = gerar_id_evento(
			TIPO_INSCRICAO_CNPJ, "12345678000199", datetime(2026, 1, 15, 13, 42, 47), sequencial=1
		)

		self.assertEqual(id_evento[0:2], "ID")
		self.assertEqual(id_evento[2:3], "1")
		self.assertEqual(id_evento[3:17], "12345678000199")
		self.assertEqual(id_evento[17:25], "20260115")
		self.assertEqual(id_evento[25:31], "134247")
		self.assertEqual(id_evento[31:36], "00001")

	def test_cpf_completa_com_zeros_a_direita_nao_a_esquerda(self):
		"""CPF tem 11 dígitos — precisa de 3 zeros para completar os 14 do Id, à
		direita (não deformando o número real, que continua legível no início)."""
		id_evento = gerar_id_evento(TIPO_INSCRICAO_CPF, "12345678901", datetime(2026, 1, 15, 13, 42, 47))

		self.assertEqual(id_evento[3:17], "12345678901000")

	def test_sequencial_e_formatado_com_5_digitos(self):
		id_evento = gerar_id_evento(
			TIPO_INSCRICAO_CNPJ, "12345678000199", datetime(2026, 1, 15, 13, 42, 47), sequencial=42
		)

		self.assertEqual(id_evento[31:36], "00042")

	def test_tipo_de_inscricao_invalido_e_erro(self):
		with self.assertRaises(EsocialIdInvalido):
			gerar_id_evento(3, "12345678000199", datetime(2026, 1, 15, 13, 42, 47))

	def test_nr_insc_nao_numerico_e_erro(self):
		with self.assertRaises(EsocialIdInvalido):
			gerar_id_evento(TIPO_INSCRICAO_CNPJ, "1234567800019A", datetime(2026, 1, 15, 13, 42, 47))

	def test_nr_insc_maior_que_14_digitos_e_erro(self):
		with self.assertRaises(EsocialIdInvalido):
			gerar_id_evento(TIPO_INSCRICAO_CNPJ, "1" * 15, datetime(2026, 1, 15, 13, 42, 47))

	def test_sequencial_zero_e_erro(self):
		with self.assertRaises(EsocialIdInvalido):
			gerar_id_evento(TIPO_INSCRICAO_CNPJ, "12345678000199", datetime(2026, 1, 15, 13, 42, 47), sequencial=0)

	def test_sequencial_acima_de_99999_e_erro(self):
		with self.assertRaises(EsocialIdInvalido):
			gerar_id_evento(
				TIPO_INSCRICAO_CNPJ, "12345678000199", datetime(2026, 1, 15, 13, 42, 47), sequencial=100000
			)

	def test_apenas_o_sequencial_muda_entre_dois_eventos_no_mesmo_segundo(self):
		momento = datetime(2026, 1, 15, 13, 42, 47)

		id1 = gerar_id_evento(TIPO_INSCRICAO_CNPJ, "12345678000199", momento, sequencial=1)
		id2 = gerar_id_evento(TIPO_INSCRICAO_CNPJ, "12345678000199", momento, sequencial=2)

		self.assertEqual(id1[:31], id2[:31])
		self.assertNotEqual(id1[31:], id2[31:])


if __name__ == "__main__":
	unittest.main()
