# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

import itertools
import unittest

from laboratorio_sus.puro.estados import (
	TRANSICOES,
	Estado,
	TransicaoInvalida,
	e_terminal,
	permitidas,
	transicionar,
)


class TestEstados(unittest.TestCase):
	def test_toda_transicao_da_tabela_e_aceita(self):
		for atual, destinos in TRANSICOES.items():
			for novo in destinos:
				self.assertEqual(transicionar(atual, novo), novo)

	def test_todo_par_fora_da_tabela_e_recusado(self):
		for atual, novo in itertools.product(Estado, Estado):
			if novo in TRANSICOES[atual]:
				continue

			with self.assertRaises(TransicaoInvalida, msg=f"{atual} -> {novo}"):
				transicionar(atual, novo)

	def test_salto_de_estado(self):
		with self.assertRaises(TransicaoInvalida):
			transicionar(Estado.SOLICITADO, Estado.EM_ANALISE)

	def test_nao_se_libera_sem_resultado(self):
		with self.assertRaises(TransicaoInvalida):
			transicionar(Estado.EM_ANALISE, Estado.LIBERADO)

	def test_terminais_nao_saem(self):
		for estado in (Estado.CANCELADO, Estado.REJEITADO, Estado.DESCARTADO):
			self.assertTrue(e_terminal(estado))
			self.assertEqual(permitidas(estado), frozenset())

		self.assertFalse(e_terminal(Estado.LIBERADO))

	def test_toda_a_tabela_cobre_todos_os_estados(self):
		self.assertEqual(set(TRANSICOES), set(Estado))

	def test_cancelamento_so_antes_da_coleta(self):
		for estado in Estado:
			pode = Estado.CANCELADO in TRANSICOES[estado]
			self.assertEqual(pode, estado is Estado.SOLICITADO, estado)

	def test_repeticao_volta_a_analise_sem_pular_para_liberado(self):
		self.assertIn(Estado.EM_ANALISE, TRANSICOES[Estado.RESULTADO_DISPONIVEL])
		self.assertNotIn(Estado.LIBERADO, TRANSICOES[Estado.EM_ANALISE])

	def test_todo_estado_nao_terminal_chega_a_um_terminal(self):
		for inicio in Estado:
			vistos, fila = {inicio}, [inicio]

			while fila:
				for prox in TRANSICOES[fila.pop()]:
					if prox not in vistos:
						vistos.add(prox)
						fila.append(prox)

			self.assertTrue(any(e_terminal(e) for e in vistos), inicio)


if __name__ == "__main__":
	unittest.main()
