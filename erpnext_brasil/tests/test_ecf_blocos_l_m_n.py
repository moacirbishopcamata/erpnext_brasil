# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/ecf_bloco_l.py`/`ecf_bloco_m.py`/`ecf_bloco_n.py` — núcleo do
Lucro Real da ECF, núcleo mínimo (abertura/encerramento). Um arquivo só, porque os três
blocos, neste incremento, têm exatamente a mesma forma trivial."""

import unittest

from erpnext_brasil.contabil.ecf_bloco_l import montar_l001, montar_l990
from erpnext_brasil.contabil.ecf_bloco_m import montar_m001, montar_m990
from erpnext_brasil.contabil.ecf_bloco_n import montar_n001, montar_n990


class TestBlocoL(unittest.TestCase):
	def test_l001_com_dados(self):
		self.assertEqual(montar_l001(tem_dados=True), {"REG": "L001", "IND_DAD": "0"})

	def test_l001_sem_dados(self):
		self.assertEqual(montar_l001(tem_dados=False), {"REG": "L001", "IND_DAD": "1"})

	def test_l990_contagem(self):
		self.assertEqual(montar_l990(5), {"REG": "L990", "QTD_LIN": "5"})


class TestBlocoM(unittest.TestCase):
	def test_m001_com_dados(self):
		self.assertEqual(montar_m001(tem_dados=True), {"REG": "M001", "IND_DAD": "0"})

	def test_m001_sem_dados(self):
		self.assertEqual(montar_m001(tem_dados=False), {"REG": "M001", "IND_DAD": "1"})

	def test_m990_contagem(self):
		self.assertEqual(montar_m990(0), {"REG": "M990", "QTD_LIN": "0"})


class TestBlocoN(unittest.TestCase):
	def test_n001_com_dados(self):
		self.assertEqual(montar_n001(tem_dados=True), {"REG": "N001", "IND_DAD": "0"})

	def test_n001_sem_dados(self):
		self.assertEqual(montar_n001(tem_dados=False), {"REG": "N001", "IND_DAD": "1"})

	def test_n990_contagem(self):
		self.assertEqual(montar_n990(12), {"REG": "N990", "QTD_LIN": "12"})


if __name__ == "__main__":
	unittest.main()
