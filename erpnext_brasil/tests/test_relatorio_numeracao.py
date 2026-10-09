# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Cálculo puro do relatório "Lacunas de Numeracao" (`fiscal/relatorio_numeracao.py`).

Teste-âncora: `test_rejeitado_nao_fecha_o_numero`. Um número rejeitado foi consumido e não existe na SEFAZ: se o
relatório o desse por resolvido, a lacuna passaria sem inutilização.
"""

import unittest

from erpnext_brasil.fiscal.relatorio_numeracao import faixas_sem_desfecho


class TestFaixasSemDesfecho(unittest.TestCase):
	def test_serie_sem_lacuna_devolve_vazio(self):
		self.assertEqual(faixas_sem_desfecho(3, {1: {"Autorizado"}, 2: {"Autorizado"}, 3: {"Denegado"}}), [])

	def test_numero_sem_registro_e_lacuna(self):
		faixas = faixas_sem_desfecho(3, {1: {"Autorizado"}, 3: {"Autorizado"}})

		self.assertEqual(faixas, [{"inicio": 2, "fim": 2, "motivo": "Sem registro", "quantidade": 1}])

	def test_numeros_consecutivos_viram_uma_faixa(self):
		faixas = faixas_sem_desfecho(6, {1: {"Autorizado"}, 6: {"Autorizado"}})

		self.assertEqual(faixas, [{"inicio": 2, "fim": 5, "motivo": "Sem registro", "quantidade": 4}])

	def test_rejeitado_nao_fecha_o_numero(self):
		faixas = faixas_sem_desfecho(2, {1: {"Autorizado"}, 2: {"Rejeitado"}})

		self.assertEqual(faixas[0]["motivo"], "Só rejeitado")

	def test_autorizado_depois_de_rejeitado_fecha(self):
		self.assertEqual(faixas_sem_desfecho(1, {1: {"Rejeitado", "Autorizado"}}), [])

	def test_cancelado_e_denegado_fecham(self):
		self.assertEqual(faixas_sem_desfecho(2, {1: {"Cancelado"}, 2: {"Denegado"}}), [])

	def test_pendente_e_apontado_como_pendente(self):
		self.assertEqual(faixas_sem_desfecho(1, {1: {"Pendente"}})[0]["motivo"], "Pendente")

	def test_motivos_diferentes_nao_se_fundem(self):
		faixas = faixas_sem_desfecho(3, {2: {"Rejeitado"}})

		self.assertEqual(
			[(f["inicio"], f["fim"], f["motivo"]) for f in faixas],
			[
				(1, 1, "Sem registro"),
				(2, 2, "Só rejeitado"),
				(3, 3, "Sem registro"),
			],
		)

	def test_numero_acima_do_contador_e_ignorado(self):
		self.assertEqual(faixas_sem_desfecho(1, {1: {"Autorizado"}, 99: set()}), [])

	def test_contador_zero_nao_tem_lacuna(self):
		self.assertEqual(faixas_sem_desfecho(0, {}), [])


if __name__ == "__main__":
	unittest.main()
