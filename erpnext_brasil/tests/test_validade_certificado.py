# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/documento/validade_certificado.py` — quando avisar do vencimento."""

import unittest
from datetime import date

from erpnext_brasil.fiscal.documento.validade_certificado import (
	NIVEL_ATENCAO,
	NIVEL_CRITICO,
	NIVEL_VENCIDO,
	avaliar_validade,
	mensagem,
)

HOJE = date(2026, 9, 3)


def _expira_em(dias: int) -> date:
	return date.fromordinal(HOJE.toordinal() + dias)


class TestMarcos(unittest.TestCase):
	"""Nos marcos (30/15/7) avisa uma vez; fora deles, silêncio."""

	def test_trinta_dias_alerta(self):
		resultado = avaliar_validade(_expira_em(30), HOJE)

		self.assertTrue(resultado.deve_alertar)
		self.assertEqual(resultado.nivel, NIVEL_ATENCAO)

	def test_quinze_dias_alerta(self):
		self.assertTrue(avaliar_validade(_expira_em(15), HOJE).deve_alertar)

	def test_sete_dias_alerta(self):
		self.assertTrue(avaliar_validade(_expira_em(7), HOJE).deve_alertar)

	def test_vinte_e_nove_dias_nao_alerta(self):
		"""O dia seguinte ao marco fica em silêncio — é isso que evita o aviso
		diário por trinta dias, que viraria ruído."""
		self.assertFalse(avaliar_validade(_expira_em(29), HOJE).deve_alertar)

	def test_dezesseis_dias_nao_alerta(self):
		self.assertFalse(avaliar_validade(_expira_em(16), HOJE).deve_alertar)

	def test_oito_dias_nao_alerta(self):
		self.assertFalse(avaliar_validade(_expira_em(8), HOJE).deve_alertar)

	def test_cem_dias_nao_alerta(self):
		self.assertFalse(avaliar_validade(_expira_em(100), HOJE).deve_alertar)


class TestUrgencia(unittest.TestCase):
	"""Nos últimos dias o aviso passa a ser diário."""

	def test_tres_dias_alerta(self):
		resultado = avaliar_validade(_expira_em(3), HOJE)

		self.assertTrue(resultado.deve_alertar)
		self.assertEqual(resultado.nivel, NIVEL_CRITICO)

	def test_dois_dias_alerta(self):
		self.assertTrue(avaliar_validade(_expira_em(2), HOJE).deve_alertar)

	def test_um_dia_alerta(self):
		self.assertTrue(avaliar_validade(_expira_em(1), HOJE).deve_alertar)

	def test_no_dia_do_vencimento_alerta_e_ainda_nao_esta_vencido(self):
		"""O dia do vencimento é um dia útil inteiro de emissão."""
		resultado = avaliar_validade(HOJE, HOJE)

		self.assertTrue(resultado.deve_alertar)
		self.assertFalse(resultado.vencido)
		self.assertEqual(resultado.dias_restantes, 0)


class TestVencido(unittest.TestCase):
	def test_vencido_ontem_alerta(self):
		resultado = avaliar_validade(_expira_em(-1), HOJE)

		self.assertTrue(resultado.deve_alertar)
		self.assertTrue(resultado.vencido)
		self.assertEqual(resultado.nivel, NIVEL_VENCIDO)

	def test_vencido_ha_muito_tempo_continua_alertando(self):
		"""Quem deixou passar é justamente quem mais precisa ser avisado."""
		resultado = avaliar_validade(_expira_em(-200), HOJE)

		self.assertTrue(resultado.deve_alertar)
		self.assertTrue(resultado.vencido)


class TestMensagem(unittest.TestCase):
	def test_vencido_diz_que_a_emissao_esta_bloqueada(self):
		expira = _expira_em(-5)
		texto = mensagem(avaliar_validade(expira, HOJE), "Empresa Teste", expira)

		self.assertIn("venceu", texto)
		self.assertIn("29/08/2026", texto)
		self.assertIn("bloqueada", texto)

	def test_no_dia_do_vencimento_diz_hoje(self):
		texto = mensagem(avaliar_validade(HOJE, HOJE), "Empresa Teste", HOJE)

		self.assertIn("hoje", texto)
		self.assertIn("03/09/2026", texto)

	def test_antes_do_vencimento_diz_quantos_dias(self):
		expira = _expira_em(15)
		texto = mensagem(avaliar_validade(expira, HOJE), "Empresa Teste", expira)

		self.assertIn("15 dia(s)", texto)
		self.assertIn("18/09/2026", texto)

	def test_menciona_a_empresa(self):
		expira = _expira_em(7)
		texto = mensagem(avaliar_validade(expira, HOJE), "Comércio do Norte LTDA", expira)

		self.assertIn("Comércio do Norte LTDA", texto)


if __name__ == "__main__":
	unittest.main()
