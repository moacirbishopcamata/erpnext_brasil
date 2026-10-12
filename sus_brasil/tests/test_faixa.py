# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

import unittest

from sus_brasil.puro.faixa import FaixaEsgotada, FaixaReservada, UsoDaFaixa, reconciliar


class TestFaixa(unittest.TestCase):
	def setUp(self):
		self.faixa = FaixaReservada("estacao-1", 100, 109)

	def test_faixa_invalida(self):
		for inicio, fim in ((0, 5), (10, 9)):
			with self.assertRaises(ValueError):
				FaixaReservada("e", inicio, fim)

	def test_contem_e_tamanho(self):
		self.assertIn(100, self.faixa)
		self.assertIn(109, self.faixa)
		self.assertNotIn(110, self.faixa)
		self.assertNotIn("100", self.faixa)
		self.assertEqual(self.faixa.tamanho, 10)

	def test_consumo_em_sequencia_e_esgotamento(self):
		uso = UsoDaFaixa(self.faixa)
		self.assertEqual([uso.consumir() for _ in range(10)], list(range(100, 110)))
		self.assertEqual(uso.restantes, 0)

		with self.assertRaises(FaixaEsgotada):
			uso.consumir()

	def test_retomar_do_proximo_e_recusar_fora(self):
		self.assertEqual(UsoDaFaixa(self.faixa).proximo, 100)
		self.assertEqual(UsoDaFaixa(self.faixa, proximo=105).consumir(), 105)

		with self.assertRaises(ValueError):
			UsoDaFaixa(self.faixa, proximo=300)

	def test_reconciliar_caminho_feliz_anula_o_que_sobrou(self):
		r = reconciliar(self.faixa, [100, 101, 102])
		self.assertEqual(r.usados, (100, 101, 102))
		self.assertEqual(r.quarentena, ())
		self.assertEqual(r.anulados, tuple(range(103, 110)))

	def test_reconciliar_identificador_duplicado_entre_estacoes_vai_a_quarentena(self):
		r = reconciliar(self.faixa, [100, 101], ja_usados_por_outras=[101])
		self.assertEqual(r.usados, (100,))
		self.assertEqual(r.quarentena, ((101, "já usado por outra estação"),))
		self.assertNotIn(101, r.anulados)

	def test_reconciliar_fora_da_faixa_e_repetido(self):
		r = reconciliar(self.faixa, [100, 100, 500])
		self.assertEqual(r.usados, (100,))
		self.assertEqual({n for n, _ in r.quarentena}, {100, 500})

	def test_nada_e_usado_e_anulado_ao_mesmo_tempo(self):
		r = reconciliar(self.faixa, [100, 103, 105, 999], [104])
		self.assertFalse(set(r.usados) & set(r.anulados))
		self.assertEqual(
			set(r.usados) | set(r.anulados) | {104},
			set(range(100, 110)),
			"todo número da faixa tem destino: usado, anulado ou de outra estação",
		)

	def test_sem_uso_anula_a_faixa_inteira(self):
		self.assertEqual(reconciliar(self.faixa, []).anulados, tuple(range(100, 110)))


if __name__ == "__main__":
	unittest.main()
