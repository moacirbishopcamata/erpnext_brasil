# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes do grupo `rastro` — rastreabilidade de lote.

Confirmado no XSD principal (`rastro`, `minOccurs="0" maxOccurs="500"`), gap real que
não estava coberto em `produto.py` até o usuário perguntar por rastreabilidade fiscal.
Não confundir com o SNCM (ANVISA, DataMatrix) — sistema à parte, que não se integra com
estes campos.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.documento.produto import (
	MAXIMO_LOTES_POR_ITEM,
	ProdutoInvalido,
	montar_prod,
	montar_rastro,
)


def lote(**ajustes):
	valores = {
		"numero_lote": "LOTE2026A",
		"quantidade_lote": Decimal("100"),
		"data_fabricacao": "2026-01-15",
		"data_validade": "2028-01-15",
	}
	valores.update(ajustes)

	return montar_rastro(**valores)


class TestMontarRastro(unittest.TestCase):
	def test_campos_obrigatorios(self):
		grupo = lote()

		self.assertEqual(grupo["nLote"], "LOTE2026A")
		self.assertEqual(grupo["dFab"], "2026-01-15")
		self.assertEqual(grupo["dVal"], "2028-01-15")

	def test_ordem_dos_campos(self):
		self.assertEqual(list(lote()), ["nLote", "qLote", "dFab", "dVal"])

	def test_cagreg_opcional(self):
		self.assertNotIn("cAgreg", lote())
		self.assertEqual(lote(codigo_agregacao="AGR1")["cAgreg"], "AGR1")

	def test_numero_de_lote_vazio_e_erro(self):
		with self.assertRaises(ProdutoInvalido) as ctx:
			lote(numero_lote="")

		self.assertEqual(ctx.exception.campo, "numero_lote")

	def test_numero_de_lote_longo_demais_e_erro(self):
		with self.assertRaises(ProdutoInvalido):
			lote(numero_lote="x" * 21)

	def test_vinte_caracteres_e_o_limite_aceito(self):
		grupo = lote(numero_lote="x" * 20)

		self.assertEqual(len(grupo["nLote"]), 20)

	def test_sem_data_de_fabricacao_e_erro(self):
		with self.assertRaises(ProdutoInvalido):
			lote(data_fabricacao="")

	def test_sem_data_de_validade_e_erro(self):
		with self.assertRaises(ProdutoInvalido):
			lote(data_validade="")


class TestQuantidadeDoLote(unittest.TestCase):
	"""qLote (TDec_0803v) aceita 1 a 3 casas — formatar sempre com 3 é sempre válido."""

	def test_quantidade_inteira(self):
		self.assertEqual(lote(quantidade_lote=Decimal("100"))["qLote"], "100.000")

	def test_quantidade_fracionaria(self):
		self.assertEqual(lote(quantidade_lote=Decimal("12.5"))["qLote"], "12.500")

	def test_quantidade_zero_usa_o_literal(self):
		"""O padrão do XSD tem "0" como alternativa própria, separada de "0.000"."""
		self.assertEqual(lote(quantidade_lote=Decimal("0"))["qLote"], "0")

	def test_tres_casas_e_o_maximo_do_tipo(self):
		grupo = lote(quantidade_lote=Decimal("1.123456"))

		self.assertEqual(grupo["qLote"], "1.123")


class TestMontarProdComRastro(unittest.TestCase):
	def setUp(self):
		self.base = {
			"codigo": "MED-1",
			"descricao": "Medicamento de exemplo",
			"ncm": "30049099",
			"cfop": "5102",
			"unidade": "CX",
			"quantidade": 10,
			"valor_unitario": "50.00",
			"valor_total": "500.00",
		}

	def test_sem_lotes_o_grupo_nao_aparece(self):
		grupo = montar_prod(**self.base)

		self.assertNotIn("rastro", grupo)

	def test_com_um_lote(self):
		grupo = montar_prod(**self.base, lotes=[lote()])

		self.assertEqual(len(grupo["rastro"]), 1)
		self.assertEqual(grupo["rastro"][0]["nLote"], "LOTE2026A")

	def test_com_varios_lotes(self):
		"""Um item pode combinar estoque de lotes diferentes na mesma nota."""
		grupo = montar_prod(
			**self.base,
			lotes=[lote(numero_lote="L1"), lote(numero_lote="L2")],
		)

		self.assertEqual([l["nLote"] for l in grupo["rastro"]], ["L1", "L2"])

	def test_mais_de_quinhentos_lotes_e_erro(self):
		lotes = [lote(numero_lote=f"L{n}") for n in range(MAXIMO_LOTES_POR_ITEM + 1)]

		with self.assertRaises(ProdutoInvalido) as ctx:
			montar_prod(**self.base, lotes=lotes)

		self.assertEqual(ctx.exception.campo, "lotes")

	def test_limite_de_quinhentos_e_aceito(self):
		lotes = [lote(numero_lote=f"L{n}") for n in range(MAXIMO_LOTES_POR_ITEM)]
		grupo = montar_prod(**self.base, lotes=lotes)

		self.assertEqual(len(grupo["rastro"]), MAXIMO_LOTES_POR_ITEM)

	def test_rastro_vem_depois_de_cest_antes_de_cfop(self):
		"""A posição no dicionário decide a ordem de serialização — precisa bater
		com a sequência confirmada no XSD."""
		grupo = montar_prod(**self.base, cest="1234567", lotes=[lote()])
		chaves = list(grupo)

		self.assertLess(chaves.index("CEST"), chaves.index("rastro"))
		self.assertLess(chaves.index("rastro"), chaves.index("CFOP"))


class TestConformidadeDeTags(unittest.TestCase):
	def setUp(self):
		import json
		import pathlib

		manifesto = (
			pathlib.Path(__file__).resolve().parents[1]
			/ "fiscal"
			/ "documento"
			/ "elementos_nfe.json"
		)
		self.elementos = set(json.loads(manifesto.read_text(encoding="utf-8")))

	def test_tags_do_rastro_existem_no_xsd(self):
		grupo = montar_prod(
			codigo="1",
			descricao="Produto",
			ncm="30049099",
			cfop="5102",
			unidade="UN",
			quantidade=1,
			valor_unitario="1.00",
			valor_total="1.00",
			lotes=[lote(codigo_agregacao="A1")],
		)

		desconhecidas = (set(grupo["rastro"][0]) | {"rastro"}) - self.elementos

		self.assertEqual(desconhecidas, set(), f"fora do layout: {sorted(desconhecidas)}")


if __name__ == "__main__":
	unittest.main()
