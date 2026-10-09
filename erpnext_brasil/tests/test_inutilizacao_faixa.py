# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Faixa a inutilizar e faixa no registro (`fiscal/documento/inutilizacao.py`, `transmissao_registro.py`).

Teste-âncora: `test_numero_com_desfecho_na_faixa_e_recusado`. Inutilizar número já autorizado seria pedir à SEFAZ o
que ela recusa — e deixar um registro de rejeição sem necessidade.
"""

import unittest

from erpnext_brasil.fiscal.documento.inutilizacao import InutilizacaoInvalida, validar_faixa_a_inutilizar
from erpnext_brasil.fiscal.documento.transmissao_registro import RegistroInvalido, validar_registro


class TestFaixaAInutilizar(unittest.TestCase):
	def test_faixa_consumida_e_sem_desfecho_passa(self):
		validar_faixa_a_inutilizar(2, 3, 5, {1, 4, 5})

	def test_numero_com_desfecho_na_faixa_e_recusado(self):
		with self.assertRaises(InutilizacaoInvalida) as ctx:
			validar_faixa_a_inutilizar(2, 4, 5, {3})

		self.assertIn("[3]", str(ctx.exception))

	def test_numero_ainda_nao_alocado_e_recusado(self):
		with self.assertRaises(InutilizacaoInvalida):
			validar_faixa_a_inutilizar(4, 6, 5, set())

	def test_faixa_invertida_ou_zero_e_recusada(self):
		for inicio, fim in ((3, 2), (0, 2)):
			with self.subTest(faixa=(inicio, fim)), self.assertRaises(InutilizacaoInvalida):
				validar_faixa_a_inutilizar(inicio, fim, 5, set())


def _inutilizacao(**extra):
	return {
		"tipo": "Inutilização",
		"situacao": "Autorizado",
		"ambiente": "Homologação",
		"protocolo": "135260000000001",
		"numero_inicial": 2,
		"numero_final": 3,
		**extra,
	}


class TestFaixaNoRegistro(unittest.TestCase):
	def test_inutilizacao_com_faixa_valida_passa(self):
		validar_registro(_inutilizacao())

	def test_inutilizacao_sem_faixa_e_recusada(self):
		for extra in (
			{"numero_inicial": 0, "numero_final": 0},
			{"numero_final": 1},
			{"numero_inicial": None},
		):
			with self.subTest(extra=extra), self.assertRaises(RegistroInvalido):
				validar_registro(_inutilizacao(**extra))

	def test_faixa_em_outro_tipo_e_recusada(self):
		with self.assertRaises(RegistroInvalido):
			validar_registro(_inutilizacao(tipo="Cancelamento"))

	def test_registro_comum_sem_faixa_continua_valido(self):
		validar_registro(
			{"tipo": "Autorização", "situacao": "Autorizado", "ambiente": "Homologação", "protocolo": "1"}
		)
		validar_registro(
			{"tipo": "Autorização", "situacao": "Autorizado", "ambiente": "Homologação", "protocolo": "1",
			 "numero_inicial": 0, "numero_final": 0}
		)  # fmt: skip


if __name__ == "__main__":
	unittest.main()
