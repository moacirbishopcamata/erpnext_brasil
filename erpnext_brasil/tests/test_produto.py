# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes dos grupos `prod` e `ICMSTot`.

Dois comportamentos aqui são exigência do layout e parecem redundância: `cEAN` informa o
literal `SEM GTIN` em vez de ficar vazio, e as unidades tributáveis repetem as comerciais
quando não informadas. Omitir qualquer um é rejeição, então ambos têm teste.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.documento.produto import (
	SEM_GTIN,
	ProdutoInvalido,
	montar_icmstot,
	montar_prod,
)
from erpnext_brasil.fiscal.impostos.apuracao import ItemFiscal, apurar


def produto(**ajustes) -> dict:
	valores = {
		"codigo": "PROD-1",
		"descricao": "Produto de exemplo",
		"ncm": "84713012",
		"cfop": "5102",
		"unidade": "UN",
		"quantidade": 2,
		"valor_unitario": "500.00",
		"valor_total": "1000.00",
	}
	valores.update(ajustes)

	return montar_prod(**valores)


class TestProd(unittest.TestCase):
	def setUp(self):
		self.grupo = produto()

	def test_campos_obrigatorios(self):
		for campo in ("cProd", "cEAN", "xProd", "NCM", "CFOP", "uCom", "qCom", "vUnCom", "vProd"):
			with self.subTest(campo=campo):
				self.assertIn(campo, self.grupo)

	def test_sem_gtin_em_vez_de_vazio(self):
		"""Deixar cEAN vazio é rejeição; inventar um EAN é pior."""
		self.assertEqual(self.grupo["cEAN"], SEM_GTIN)
		self.assertEqual(self.grupo["cEANTrib"], SEM_GTIN)

	def test_ean_informado_e_usado(self):
		grupo = produto(ean="7891234567895")

		self.assertEqual(grupo["cEAN"], "7891234567895")

	def test_unidades_tributaveis_repetem_as_comerciais(self):
		self.assertEqual(self.grupo["uTrib"], self.grupo["uCom"])
		self.assertEqual(self.grupo["qTrib"], self.grupo["qCom"])
		self.assertEqual(self.grupo["vUnTrib"], self.grupo["vUnCom"])

	def test_unidade_tributavel_distinta_e_respeitada(self):
		"""Quem vende em caixa e tributa em unidade precisa das duas."""
		grupo = produto(unidade="CX", unidade_tributavel="UN", quantidade_tributavel=24)

		self.assertEqual(grupo["uCom"], "CX")
		self.assertEqual(grupo["uTrib"], "UN")
		self.assertEqual(grupo["qTrib"], "24.0000")

	def test_quantidade_com_quatro_casas(self):
		self.assertEqual(self.grupo["qCom"], "2.0000")

	def test_valor_com_duas_casas(self):
		self.assertEqual(self.grupo["vProd"], "1000.00")

	def test_ncm_com_pontos_e_limpo(self):
		self.assertEqual(produto(ncm="8471.30.12")["NCM"], "84713012")

	def test_ncm_invalido(self):
		for ncm in ("", "123", "8471301A"):
			with self.subTest(ncm=ncm):
				with self.assertRaises(ProdutoInvalido):
					produto(ncm=ncm)

	def test_cfop_invalido(self):
		for cfop in ("", "51022", "510A"):
			with self.subTest(cfop=cfop):
				with self.assertRaises(ProdutoInvalido):
					produto(cfop=cfop)

	def test_acessorios_so_entram_quando_ha_valor(self):
		for campo in ("vFrete", "vSeg", "vDesc", "vOutro"):
			self.assertNotIn(campo, self.grupo)

		com = produto(frete="50.00", desconto="10.00")
		self.assertEqual(com["vFrete"], "50.00")
		self.assertEqual(com["vDesc"], "10.00")
		self.assertNotIn("vSeg", com)

	def test_indtot(self):
		self.assertEqual(self.grupo["indTot"], "1")
		self.assertEqual(produto(compoe_total=False)["indTot"], "0")

	def test_cest_opcional(self):
		self.assertNotIn("CEST", self.grupo)
		self.assertEqual(produto(cest="2104300")["CEST"], "2104300")

	def test_campo_obrigatorio_vazio_aponta_o_nome(self):
		with self.assertRaises(ProdutoInvalido) as ctx:
			produto(descricao="  ")

		self.assertEqual(ctx.exception.campo, "descrição do produto")


def apuracao(valor="1000.00"):
	return apurar(
		ItemFiscal(
			valor_produtos=Decimal(valor),
			aliquota_icms=Decimal("0.18"),
			aliquota_ipi=Decimal("0.10"),
		)
	)


class TestIcmsTot(unittest.TestCase):
	def setUp(self):
		self.totais = montar_icmstot([apuracao()])["ICMSTot"]

	def test_valores_da_apuracao(self):
		self.assertEqual(self.totais["vProd"], "1000.00")
		self.assertEqual(self.totais["vICMS"], "180.00")
		self.assertEqual(self.totais["vIPI"], "100.00")
		self.assertEqual(self.totais["vPIS"], "5.33")
		self.assertEqual(self.totais["vCOFINS"], "24.60")

	def test_campos_sem_valor_saem_zerados_e_nao_omitidos(self):
		"""Omitir campo de total é rejeição, não economia."""
		for campo in ("vICMSDeson", "vFCP", "vBCST", "vST", "vII", "vIPIDevol"):
			with self.subTest(campo=campo):
				self.assertEqual(self.totais[campo], "0.00")

	def test_total_da_nota_soma_apenas_o_que_e_por_fora(self):
		"""ICMS, PIS e COFINS já estão no preço; só o IPI se acrescenta."""
		self.assertEqual(self.totais["vNF"], "1100.00")

	def test_soma_de_varios_itens(self):
		totais = montar_icmstot([apuracao("1000.00"), apuracao("500.00")])["ICMSTot"]

		self.assertEqual(totais["vProd"], "1500.00")
		self.assertEqual(totais["vICMS"], "270.00")

	def test_acessorios_vem_dos_produtos_informados(self):
		produtos = [produto(frete="50.00", desconto="10.00")]
		totais = montar_icmstot([apuracao()], produtos)["ICMSTot"]

		self.assertEqual(totais["vFrete"], "50.00")
		self.assertEqual(totais["vDesc"], "10.00")
		self.assertEqual(totais["vNF"], "1140.00")

	def test_sem_itens_e_erro(self):
		with self.assertRaises(ProdutoInvalido):
			montar_icmstot([])


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

	def test_tags_de_prod_existem_no_xsd(self):
		desconhecidas = set(produto(frete="1", cest="2104300")) - self.elementos

		self.assertEqual(desconhecidas, set(), f"fora do layout: {sorted(desconhecidas)}")

	def test_tags_de_icmstot_existem_no_xsd(self):
		totais = montar_icmstot([apuracao()])
		nomes = set(totais) | set(totais["ICMSTot"])

		self.assertEqual(nomes - self.elementos, set())


if __name__ == "__main__":
	unittest.main()
