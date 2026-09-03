# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes do grupo `infAdic`.

O teste que guarda a decisão de design é `test_vazio_devolve_none`: o grupo inteiro é
opcional no layout, e um `infAdic` com todas as chaves vazias não deveria existir no
documento — devolver `None` em vez de `{"infAdic": {}}` é o que permite ao chamador
testar com `if resultado:` sem lógica extra.
"""

import unittest

from erpnext_brasil.fiscal.documento.informacoes_adicionais import montar_infadic


class TestCamposIndividuais(unittest.TestCase):
	def test_informacoes_complementares(self):
		grupo = montar_infadic(informacoes_complementares="Venda à vista")["infAdic"]

		self.assertEqual(grupo["infCpl"], "Venda à vista")

	def test_informacoes_ao_fisco(self):
		grupo = montar_infadic(informacoes_ao_fisco="Isenção conforme convênio X")["infAdic"]

		self.assertEqual(grupo["infAdFisco"], "Isenção conforme convênio X")

	def test_os_dois_juntos(self):
		grupo = montar_infadic(informacoes_complementares="A", informacoes_ao_fisco="B")["infAdic"]

		self.assertEqual(grupo["infCpl"], "A")
		self.assertEqual(grupo["infAdFisco"], "B")


class TestObservacoesEstruturadas(unittest.TestCase):
	def test_observacao_do_contribuinte(self):
		grupo = montar_infadic(observacoes_contribuinte={"Pedido": "12345"})["infAdic"]

		self.assertEqual(grupo["obsCont"], [{"@xCampo": "Pedido", "xTexto": "12345"}])

	def test_observacao_do_fisco(self):
		grupo = montar_infadic(observacoes_fisco={"Regime": "Especial"})["infAdic"]

		self.assertEqual(grupo["obsFisco"], [{"@xCampo": "Regime", "xTexto": "Especial"}])

	def test_varias_observacoes_viram_lista(self):
		grupo = montar_infadic(observacoes_contribuinte={"Pedido": "1", "Vendedor": "João"})["infAdic"]

		self.assertEqual(len(grupo["obsCont"]), 2)

	def test_xcampo_e_atributo_nao_elemento(self):
		"""A identificação da observação é atributo (@xCampo), não filho."""
		grupo = montar_infadic(observacoes_contribuinte={"Pedido": "12345"})["infAdic"]
		obs = grupo["obsCont"][0]

		self.assertTrue(any(chave.startswith("@") for chave in obs))
		self.assertIn("xTexto", obs)


class TestVazio(unittest.TestCase):
	def test_vazio_devolve_none(self):
		"""O grupo é opcional; um infAdic sem conteúdo não deveria existir no documento."""
		self.assertIsNone(montar_infadic())

	def test_observacoes_vazias_tambem_devolvem_none(self):
		self.assertIsNone(montar_infadic(observacoes_contribuinte={}, observacoes_fisco={}))

	def test_string_vazia_nao_conta_como_preenchida(self):
		self.assertIsNone(montar_infadic(informacoes_complementares="", informacoes_ao_fisco="  "))


if __name__ == "__main__":
	unittest.main()
