# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes do grupo `imposto` do item.

O teste que mais importa é `TestExclusividadeMercadoriaServico`: ICMS/IPI e ISSQN nunca
coexistem no mesmo item, e CST e CSOSN também são exclusivos entre si. Informar dois é
erro explícito, não escolha silenciosa — mesma disciplina já aplicada em `dest`.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.documento.imposto_item import ImpostoInvalido, montar_imposto_item
from erpnext_brasil.fiscal.impostos.apuracao import ItemFiscal, Operacao, apurar


def apuracao(**ajustes):
	valores = {
		"valor_produtos": Decimal("1000.00"),
		"aliquota_icms": Decimal("0.18"),
		"aliquota_ipi": Decimal("0.10"),
		"cst_ibs_cbs": "000",
		"classificacao_tributaria": "000001",
	}
	valores.update(ajustes)

	return apurar(ItemFiscal(**valores), Operacao())


class TestICMSIntegral(unittest.TestCase):
	def setUp(self):
		self.grupo = montar_imposto_item(apuracao(), cst_icms="00")["imposto"]

	def test_estrutura(self):
		self.assertIn("ICMS00", self.grupo["ICMS"])

	def test_valores_da_apuracao(self):
		icms = self.grupo["ICMS"]["ICMS00"]

		self.assertEqual(icms["vBC"], "1000.00")
		self.assertEqual(icms["pICMS"], "18.0000")
		self.assertEqual(icms["vICMS"], "180.00")

	def test_ipi_pis_cofins_presentes(self):
		self.assertIn("IPI", self.grupo)
		self.assertIn("PIS", self.grupo)
		self.assertIn("COFINS", self.grupo)


def apuracao_com_reducao(**ajustes):
	from erpnext_brasil.fiscal.impostos.icms import calcular_icms

	item = ItemFiscal(
		valor_produtos=Decimal("1000.00"),
		aliquota_icms=Decimal("0.18"),
		reducao_icms=Decimal("0.30"),
		aliquota_ipi=Decimal("0.10"),
		cst_ibs_cbs="000",
		classificacao_tributaria="000001",
	)
	apurada = apurar(item, Operacao())

	# Confere a própria base do teste: a apuração precisa refletir a redução informada.
	assert calcular_icms(item.valor_liquido, item.aliquota_icms, item.reducao_icms).base == (
		apurada.icms.base
	)

	return apurada


class TestICMSReduzido(unittest.TestCase):
	def test_percentual_de_reducao(self):
		grupo = montar_imposto_item(apuracao_com_reducao(), cst_icms="20")["imposto"]

		bloco = grupo["ICMS"]["ICMS20"]
		self.assertEqual(bloco["pRedBC"], "30.0000")
		self.assertEqual(bloco["vBC"], "700.00")

	def test_sem_reducao_e_erro(self):
		item = ItemFiscal(
			valor_produtos=Decimal("1000.00"), aliquota_icms=Decimal("0.18")
		)
		apurada = apurar(item)

		with self.assertRaises(ImpostoInvalido) as ctx:
			montar_imposto_item(apurada, cst_icms="20")

		self.assertEqual(ctx.exception.campo, "reducao_icms")


class TestICMSIsentoNaoTributado(unittest.TestCase):
	def test_sem_base_nem_aliquota(self):
		grupo = montar_imposto_item(apuracao(aliquota_icms=Decimal("0")), cst_icms="40")[
			"imposto"
		]

		icms40 = grupo["ICMS"]["ICMS40"]
		self.assertEqual(set(icms40), {"orig", "CST"})

	def test_csts_aceitos(self):
		for cst in ("40", "41", "60"):
			with self.subTest(cst=cst):
				grupo = montar_imposto_item(apuracao(), cst_icms=cst)["imposto"]
				self.assertIn(f"ICMS{cst}", grupo["ICMS"])


class TestSimplesNacional(unittest.TestCase):
	def test_csosn_102_sem_credito(self):
		grupo = montar_imposto_item(apuracao(), csosn="102")["imposto"]
		bloco = grupo["ICMS"]["ICMSSN102"]

		self.assertEqual(bloco["CSOSN"], "102")
		self.assertNotIn("pCredSN", bloco)

	def test_csosn_101_com_credito(self):
		grupo = montar_imposto_item(apuracao(), csosn="101")["imposto"]
		bloco = grupo["ICMS"]["ICMSSN101"]

		self.assertIn("pCredSN", bloco)
		self.assertIn("vCredICMSSN", bloco)


class TestExclusividadeMercadoriaServico(unittest.TestCase):
	def test_cst_e_csosn_juntos_e_erro(self):
		with self.assertRaises(ImpostoInvalido) as ctx:
			montar_imposto_item(apuracao(), cst_icms="00", csosn="102")

		self.assertEqual(ctx.exception.campo, "cst_icms")

	def test_issqn_com_icms_e_erro(self):
		with self.assertRaises(ImpostoInvalido) as ctx:
			montar_imposto_item(
				apuracao(),
				cst_icms="00",
				issqn={
					"base": Decimal("1000.00"),
					"aliquota": Decimal("0.05"),
					"municipio": "3550308",
					"item_lista_servico": "01.01",
				},
			)

		self.assertEqual(ctx.exception.campo, "issqn")

	def test_cst_desconhecido_e_erro_explicito(self):
		with self.assertRaises(ImpostoInvalido):
			montar_imposto_item(apuracao(), cst_icms="51")


class TestIPI(unittest.TestCase):
	def test_tributado_usa_ipitrib(self):
		grupo = montar_imposto_item(apuracao(), cst_icms="00", ipi_tributado=True)["imposto"]

		self.assertIn("IPITrib", grupo["IPI"])
		self.assertEqual(grupo["IPI"]["IPITrib"]["vIPI"], "100.00")

	def test_nao_tributado_usa_ipint(self):
		grupo = montar_imposto_item(apuracao(), cst_icms="00", ipi_tributado=False)["imposto"]

		self.assertIn("IPINT", grupo["IPI"])
		self.assertEqual(grupo["IPI"]["IPINT"], {"CST": "53"})


class TestPISCOFINS(unittest.TestCase):
	def test_valores(self):
		grupo = montar_imposto_item(apuracao(), cst_icms="00")["imposto"]

		self.assertEqual(grupo["PIS"]["PISAliq"]["vPIS"], "5.33")
		self.assertEqual(grupo["COFINS"]["COFINSAliq"]["vCOFINS"], "24.60")

	def test_base_igual_para_pis_e_cofins(self):
		grupo = montar_imposto_item(apuracao(), cst_icms="00")["imposto"]

		self.assertEqual(grupo["PIS"]["PISAliq"]["vBC"], grupo["COFINS"]["COFINSAliq"]["vBC"])


class TestISSQN(unittest.TestCase):
	def test_item_de_servico(self):
		grupo = montar_imposto_item(
			apuracao(),
			issqn={
				"base": Decimal("1000.00"),
				"aliquota": Decimal("0.05"),
				"municipio": "3550308",
				"item_lista_servico": "01.01",
			},
		)["imposto"]

		self.assertEqual(grupo["ISSQN"]["vISSQN"], "50.00")
		self.assertEqual(grupo["ISSQN"]["cMunFG"], "3550308")
		self.assertNotIn("ICMS", grupo)
		self.assertNotIn("IPI", grupo)

	def test_ibscbs_presente_mesmo_em_servico(self):
		"""A reforma alcança mercadoria e serviço; IBS/CBS não é exclusivo de ICMS."""
		grupo = montar_imposto_item(
			apuracao(),
			issqn={
				"base": Decimal("1000.00"),
				"aliquota": Decimal("0.05"),
				"municipio": "3550308",
				"item_lista_servico": "01.01",
			},
		)["imposto"]

		self.assertIn("IBSCBS", grupo)

	def test_sem_municipio_e_erro(self):
		with self.assertRaises(ImpostoInvalido):
			montar_imposto_item(
				apuracao(),
				issqn={
					"base": Decimal("1000.00"),
					"aliquota": Decimal("0.05"),
					"municipio": "",
					"item_lista_servico": "01.01",
				},
			)


class TestIBSCBSSempreEncaixado(unittest.TestCase):
	def test_grupo_ibscbs_presente(self):
		grupo = montar_imposto_item(apuracao(), cst_icms="00")["imposto"]

		self.assertIn("IBSCBS", grupo)
		self.assertEqual(grupo["IBSCBS"]["cClassTrib"], "000001")


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

	def _tags(self, no, achadas=None):
		achadas = achadas if achadas is not None else set()

		if isinstance(no, dict):
			for chave, valor in no.items():
				if not chave.startswith("@"):
					achadas.add(chave)

				self._tags(valor, achadas)

		return achadas

	def test_mercadoria_icms00(self):
		grupo = montar_imposto_item(apuracao(), cst_icms="00")
		desconhecidas = self._tags(grupo) - self.elementos

		self.assertEqual(desconhecidas, set(), f"fora do layout: {sorted(desconhecidas)}")

	def test_simples_nacional(self):
		grupo = montar_imposto_item(apuracao(), csosn="101")
		self.assertEqual(self._tags(grupo) - self.elementos, set())

	def test_servico(self):
		grupo = montar_imposto_item(
			apuracao(),
			issqn={
				"base": Decimal("1000.00"),
				"aliquota": Decimal("0.05"),
				"municipio": "3550308",
				"item_lista_servico": "01.01",
			},
		)
		self.assertEqual(self._tags(grupo) - self.elementos, set())


if __name__ == "__main__":
	unittest.main()
