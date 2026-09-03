# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/ecf_bloco_p.py` — Bloco P (Lucro Presumido) da ECF, núcleo
mínimo (abertura/encerramento)."""

import unittest

from erpnext_brasil.contabil.ecf_bloco_p import montar_p001, montar_p990


class TestMontarP001(unittest.TestCase):
	def test_com_dados(self):
		self.assertEqual(montar_p001(tem_dados=True), {"REG": "P001", "IND_DAD": "0"})

	def test_sem_dados(self):
		self.assertEqual(montar_p001(tem_dados=False), {"REG": "P001", "IND_DAD": "1"})


class TestMontarP990(unittest.TestCase):
	def test_contagem(self):
		self.assertEqual(montar_p990(3), {"REG": "P990", "QTD_LIN": "3"})


if __name__ == "__main__":
	unittest.main()
