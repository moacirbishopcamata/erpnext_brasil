# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/cfop_transporte.py` — CFOP de prestação de serviço de transporte."""

import unittest

from erpnext_brasil.fiscal.cfop import CfopInvalido
from erpnext_brasil.fiscal.cfop_transporte import (
	FINALIDADE_COMERCIAL,
	FINALIDADE_COMUNICACAO,
	FINALIDADE_DISPENSADO_NF,
	FINALIDADE_ENERGIA,
	FINALIDADE_INDUSTRIAL,
	FINALIDADE_NAO_CONTRIBUINTE,
	FINALIDADE_PRODUTOR_RURAL,
	FINALIDADE_SUBSTITUTO_TRIBUTARIO,
	cfop_prestacao_transporte,
	cfop_subcontratacao_transporte,
)


class TestCfopPrestacaoTransporte(unittest.TestCase):
	def test_todos_os_perfis_mesmo_estado(self):
		"""Os oito perfis, mesmo estado — cada um com seu sufixo confirmado nas três
		fontes cruzadas (ver docstring do módulo)."""
		casos = {
			FINALIDADE_INDUSTRIAL: "5352",
			FINALIDADE_COMERCIAL: "5353",
			FINALIDADE_COMUNICACAO: "5354",
			FINALIDADE_ENERGIA: "5355",
			FINALIDADE_PRODUTOR_RURAL: "5356",
			FINALIDADE_NAO_CONTRIBUINTE: "5357",
			FINALIDADE_DISPENSADO_NF: "5359",
			FINALIDADE_SUBSTITUTO_TRIBUTARIO: "5360",
		}

		for finalidade, esperado in casos.items():
			with self.subTest(finalidade=finalidade):
				self.assertEqual(
					cfop_prestacao_transporte(mesmo_estado=True, finalidade=finalidade), esperado
				)

	def test_todos_os_perfis_outro_estado(self):
		"""Mesmos oito perfis, outro estado — só o primeiro dígito muda (5→6), mesmo
		padrão estrutural já confirmado para CFOP de mercadoria em `fiscal/cfop.py`."""
		casos = {
			FINALIDADE_INDUSTRIAL: "6352",
			FINALIDADE_COMERCIAL: "6353",
			FINALIDADE_COMUNICACAO: "6354",
			FINALIDADE_ENERGIA: "6355",
			FINALIDADE_PRODUTOR_RURAL: "6356",
			FINALIDADE_NAO_CONTRIBUINTE: "6357",
			FINALIDADE_DISPENSADO_NF: "6359",
			FINALIDADE_SUBSTITUTO_TRIBUTARIO: "6360",
		}

		for finalidade, esperado in casos.items():
			with self.subTest(finalidade=finalidade):
				self.assertEqual(
					cfop_prestacao_transporte(mesmo_estado=False, finalidade=finalidade), esperado
				)

	def test_finalidade_desconhecida_levanta_cfop_invalido(self):
		with self.assertRaises(CfopInvalido):
			cfop_prestacao_transporte(mesmo_estado=True, finalidade="perfil_inexistente")

	def test_reusa_a_mesma_excecao_de_fiscal_cfop(self):
		"""CfopInvalido é importado de fiscal/cfop.py, não redefinido — um só tipo de
		exceção para todo erro de determinação de CFOP, mercadoria ou serviço."""
		from erpnext_brasil.fiscal.cfop import CfopInvalido as CfopInvalidoOriginal

		self.assertIs(CfopInvalido, CfopInvalidoOriginal)


class TestCfopSubcontratacaoTransporte(unittest.TestCase):
	def test_mesmo_estado(self):
		self.assertEqual(cfop_subcontratacao_transporte(mesmo_estado=True), "5351")

	def test_outro_estado(self):
		self.assertEqual(cfop_subcontratacao_transporte(mesmo_estado=False), "6351")


if __name__ == "__main__":
	unittest.main()
