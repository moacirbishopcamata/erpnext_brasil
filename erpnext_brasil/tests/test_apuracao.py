# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da apuração — a ordem em que as bases se compõem.

O teste que importa é o par revenda/consumidor final: a mesma mercadoria, com os mesmos
valores, produz ICMS e PIS/COFINS diferentes só porque muda a natureza do destinatário.
Calcular os tributos isoladamente e somar acertaria o total e erraria a composição.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.apuracao import (
	ItemFiscal,
	Operacao,
	apurar,
	apurar_documento,
)


def d(v: str) -> Decimal:
	return Decimal(v)


def item_padrao(**ajustes) -> ItemFiscal:
	valores = {
		"valor_produtos": d("1000.00"),
		"aliquota_icms": d("0.18"),
		"aliquota_ipi": d("0.10"),
	}
	valores.update(ajustes)

	return ItemFiscal(**valores)


class TestRevendaEntreContribuintes(unittest.TestCase):
	"""IPI fora da base do ICMS."""

	def setUp(self):
		self.a = apurar(item_padrao(), Operacao())

	def test_ipi_nao_compoe(self):
		self.assertFalse(self.a.ipi_na_base_do_icms)
		self.assertEqual(self.a.base_icms, d("1000.00"))

	def test_valores(self):
		self.assertEqual(self.a.ipi.valor, d("100.00"))
		self.assertEqual(self.a.icms.valor, d("180.00"))

	def test_icms_sai_da_base_de_pis_cofins(self):
		self.assertEqual(self.a.pis_cofins.base, d("820.00"))
		self.assertEqual(self.a.pis_cofins.pis, d("5.33"))
		self.assertEqual(self.a.pis_cofins.cofins, d("24.60"))

	def test_ibs_cbs_por_fora_sobre_o_valor_da_operacao(self):
		self.assertEqual(self.a.ibs_cbs.base, d("1000.00"))
		self.assertEqual(self.a.ibs_cbs.ibs, d("1.00"))
		self.assertEqual(self.a.ibs_cbs.cbs, d("9.00"))

	def test_total_soma_apenas_os_tributos_por_fora(self):
		# 1000 + IPI 100 + IBS 1 + CBS 9. O ICMS não entra: já está no preço.
		self.assertEqual(self.a.total_item, d("1110.00"))


class TestVendaAConsumidorFinal(unittest.TestCase):
	"""IPI dentro da base do ICMS — mesma mercadoria, tributos diferentes."""

	def setUp(self):
		self.a = apurar(
			item_padrao(),
			Operacao(destinado_a_industrializacao_ou_comercio=False),
		)

	def test_ipi_compoe(self):
		self.assertTrue(self.a.ipi_na_base_do_icms)
		self.assertEqual(self.a.base_icms, d("1100.00"))

	def test_icms_maior(self):
		self.assertEqual(self.a.icms.valor, d("198.00"))

	def test_pis_cofins_menor_porque_o_icms_e_maior(self):
		"""Efeito em cascata: ICMS maior reduz a base de PIS/COFINS."""
		self.assertEqual(self.a.pis_cofins.base, d("802.00"))
		self.assertEqual(self.a.pis_cofins.pis, d("5.21"))
		self.assertEqual(self.a.pis_cofins.cofins, d("24.06"))


class TestComparacaoEntreAsDuasOperacoes(unittest.TestCase):
	def setUp(self):
		self.revenda = apurar(item_padrao(), Operacao())
		self.consumidor = apurar(item_padrao(), Operacao(destinado_a_industrializacao_ou_comercio=False))

	def test_o_total_e_o_mesmo(self):
		"""O ICMS é por dentro: muda o imposto, não o que o cliente paga."""
		self.assertEqual(self.revenda.total_item, self.consumidor.total_item)

	def test_mas_a_composicao_muda(self):
		self.assertEqual(self.consumidor.icms.valor - self.revenda.icms.valor, d("18.00"))
		self.assertLess(self.consumidor.pis_cofins.total, self.revenda.pis_cofins.total)


class TestDestinatarioNaoContribuinte(unittest.TestCase):
	def test_ipi_compoe_mesmo_destinado_a_comercio(self):
		a = apurar(item_padrao(), Operacao(destinatario_contribuinte=False))

		self.assertTrue(a.ipi_na_base_do_icms)
		self.assertEqual(a.base_icms, d("1100.00"))


class TestAcessoriosEDescontos(unittest.TestCase):
	def test_frete_e_seguro_entram_no_valor_liquido(self):
		a = apurar(item_padrao(frete=d("80.00"), seguro=d("20.00")))

		self.assertEqual(a.item.valor_liquido, d("1100.00"))
		self.assertEqual(a.ipi.valor, d("110.00"))
		self.assertEqual(a.icms.valor, d("198.00"))

	def test_desconto_reduz_todas_as_bases(self):
		a = apurar(item_padrao(descontos=d("100.00")))

		self.assertEqual(a.item.valor_liquido, d("900.00"))
		self.assertEqual(a.ipi.valor, d("90.00"))
		self.assertEqual(a.icms.valor, d("162.00"))

	def test_desconto_maior_que_o_valor_e_erro(self):
		with self.assertRaises(ValueError):
			apurar(item_padrao(descontos=d("5000.00")))


class TestImpostoSeletivo(unittest.TestCase):
	def test_integra_a_base_de_ibs_cbs_e_o_total(self):
		a = apurar(item_padrao(imposto_seletivo=d("50.00")))

		self.assertEqual(a.ibs_cbs.base, d("1050.00"))
		self.assertEqual(a.ibs_cbs.ibs, d("1.05"))
		self.assertEqual(a.ibs_cbs.cbs, d("9.45"))
		self.assertEqual(a.total_item, d("1160.50"))

	def test_nao_afeta_icms_nem_ipi(self):
		com = apurar(item_padrao(imposto_seletivo=d("50.00")))
		sem = apurar(item_padrao())

		self.assertEqual(com.icms.valor, sem.icms.valor)
		self.assertEqual(com.ipi.valor, sem.ipi.valor)


class TestRegimeNaoCumulativo(unittest.TestCase):
	def test_aliquotas_maiores_sobre_a_mesma_base(self):
		a = apurar(item_padrao(), Operacao(regime_pis_cofins="nao_cumulativo"))

		self.assertEqual(a.pis_cofins.base, d("820.00"))
		self.assertEqual(a.pis_cofins.pis, d("13.53"))
		self.assertEqual(a.pis_cofins.cofins, d("62.32"))


class TestDocumento(unittest.TestCase):
	def setUp(self):
		self.doc = apurar_documento([item_padrao(), item_padrao(valor_produtos=d("500.00"))])

	def test_totais(self):
		self.assertEqual(self.doc.total_produtos, d("1500.00"))
		self.assertEqual(self.doc.total_ipi, d("150.00"))
		self.assertEqual(self.doc.total_icms, d("270.00"))
		self.assertEqual(self.doc.total_ibs, d("1.50"))
		self.assertEqual(self.doc.total_cbs, d("13.50"))

	def test_total_e_soma_dos_itens(self):
		self.assertEqual(self.doc.total_documento, sum(i.total_item for i in self.doc.itens))

	def test_documento_sem_itens_e_erro(self):
		with self.assertRaises(ValueError):
			apurar_documento([])


if __name__ == "__main__":
	unittest.main()
