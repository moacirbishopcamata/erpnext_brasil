# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes do grupo `imposto` do item.

O teste que mais importa é `TestExclusividadeMercadoriaServico`: ICMS/IPI e ISSQN nunca
coexistem no mesmo item, e CST e CSOSN também são exclusivos entre si. Informar dois é
erro explícito, não escolha silenciosa — mesma disciplina já aplicada em `dest`.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.documento.imposto_item import (
	ImpostoInvalido,
	montar_icms_uf_dest,
	montar_imposto_item,
)
from erpnext_brasil.fiscal.impostos.apuracao import ItemFiscal, Operacao, apurar
from erpnext_brasil.fiscal.impostos.icms import calcular_difal


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


class TestMontarIcmsUfDest(unittest.TestCase):
	"""DIFAL (EC 87/2015) — `fiscal/impostos/icms.calcular_difal` já calculava o
	diferencial; este grupo é o que faltava para ele entrar no XML."""

	def _resultado(self, aliquota_fcp=Decimal("0")):
		return calcular_difal(
			valor_operacao=Decimal("1000.00"),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			aliquota_fcp=aliquota_fcp,
		)

	def test_estrutura_sem_fcp(self):
		grupo = montar_icms_uf_dest(
			self._resultado(),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			percentual_partilha_destino=Decimal("1"),
		)

		self.assertNotIn("vBCFCPUFDest", grupo)
		self.assertNotIn("pFCPUFDest", grupo)
		self.assertNotIn("vFCPUFDest", grupo)
		self.assertIn("vBCUFDest", grupo)
		self.assertIn("vICMSUFDest", grupo)
		self.assertIn("vICMSUFRemet", grupo)

	def test_estrutura_com_fcp(self):
		grupo = montar_icms_uf_dest(
			self._resultado(aliquota_fcp=Decimal("0.02")),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			percentual_partilha_destino=Decimal("1"),
			aliquota_fcp=Decimal("0.02"),
		)

		self.assertIn("vBCFCPUFDest", grupo)
		self.assertIn("pFCPUFDest", grupo)
		self.assertIn("vFCPUFDest", grupo)

	def test_partilha_100_por_cento_zera_vicmsufremet(self):
		"""Regime vigente desde 2019: toda a partilha vai para o destino."""
		grupo = montar_icms_uf_dest(
			self._resultado(),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			percentual_partilha_destino=Decimal("1"),
		)

		self.assertEqual(grupo["vICMSUFRemet"], "0.00")

	def test_partilha_parcial_reparte_entre_origem_e_destino(self):
		"""Regime de transição (2016-2018), só para provar que a divisão funciona —
		não sugere que este percentual valha hoje."""
		resultado = self._resultado()
		grupo = montar_icms_uf_dest(
			resultado,
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			percentual_partilha_destino=Decimal("0.60"),
		)

		esperado_destino = (resultado["difal"] * Decimal("0.60")).quantize(Decimal("0.01"))
		esperado_remet = resultado["difal"] - esperado_destino

		self.assertEqual(Decimal(grupo["vICMSUFDest"]), esperado_destino)
		self.assertEqual(Decimal(grupo["vICMSUFRemet"]), esperado_remet)

	def test_percentual_fora_de_0_a_1_e_erro(self):
		with self.assertRaises(ImpostoInvalido):
			montar_icms_uf_dest(
				self._resultado(),
				aliquota_interestadual=Decimal("0.12"),
				aliquota_interna_destino=Decimal("0.18"),
				percentual_partilha_destino=Decimal("1.5"),
			)

	def test_todos_os_campos_estao_no_manifesto_oficial(self):
		import json
		import pathlib

		manifesto = (
			pathlib.Path(__file__).resolve().parents[1] / "fiscal" / "documento" / "elementos_nfe.json"
		)
		elementos = set(json.loads(manifesto.read_text(encoding="utf-8")))

		grupo = montar_icms_uf_dest(
			self._resultado(aliquota_fcp=Decimal("0.02")),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			percentual_partilha_destino=Decimal("1"),
			aliquota_fcp=Decimal("0.02"),
		)

		self.assertEqual(set(grupo) - elementos, set())


class TestIcmsUfDestDentroDoGrupoIcms(unittest.TestCase):
	"""Confirma o posicionamento oficial: ICMSUFDest é irmão de ICMS00 dentro de
	ICMS, não um grupo separado no nível de `imposto` (det/imposto/ICMS/ICMSUFDest)."""

	def test_fica_dentro_de_icms_irmao_do_cst(self):
		resultado = calcular_difal(
			valor_operacao=Decimal("1000.00"),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
		)
		icms_uf_dest = montar_icms_uf_dest(
			resultado,
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			percentual_partilha_destino=Decimal("1"),
		)

		grupo = montar_imposto_item(apuracao(), cst_icms="00", icms_uf_dest=icms_uf_dest)["imposto"]

		self.assertIn("ICMS00", grupo["ICMS"])
		self.assertIn("ICMSUFDest", grupo["ICMS"])

	def test_icms_uf_dest_com_issqn_e_erro(self):
		icms_uf_dest = montar_icms_uf_dest(
			calcular_difal(Decimal("1000.00"), Decimal("0.12"), Decimal("0.18")),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			percentual_partilha_destino=Decimal("1"),
		)

		with self.assertRaises(ImpostoInvalido):
			montar_imposto_item(
				apuracao(),
				issqn={
					"base": Decimal("1000.00"),
					"aliquota": Decimal("0.05"),
					"municipio": "3550308",
					"item_lista_servico": "01.01",
				},
				icms_uf_dest=icms_uf_dest,
			)


if __name__ == "__main__":
	unittest.main()
