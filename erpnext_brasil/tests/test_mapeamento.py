# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da costura entre o ERPNext e a apuração.

Costura mal feita é onde bug silencioso mora, e aqui há duas conversões que erram calado:
percentual↔fração (o ERPNext guarda `18`, a apuração exige `0.18`) e a decisão de quais
linhas de imposto gravar. Um erro de fator 100 não levanta exceção — produz imposto cem
vezes maior ou menor e passa.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.apuracao import apurar, apurar_documento
from erpnext_brasil.integracao.mapeamento import (
	CAMPOS_RESULTADO,
	MARCA_AUTOMATICA,
	fracao,
	item_fiscal_de_linha,
	linhas_de_imposto,
	operacao_de_documento,
	percentual,
	reconciliar_tabela_de_impostos,
	resultado_para_campos,
)


def d(v: str) -> Decimal:
	return Decimal(v)


LINHA = {
	"net_amount": 1000.0,
	"br_aliquota_icms": 18.0,
	"br_aliquota_ipi": 10.0,
	"br_cst_ibs_cbs": "000",
	"br_cclasstrib": "000001",
}

CONTAS = {
	"ICMS": "ICMS a Recolher - _TC",
	"IPI": "IPI a Recolher - _TC",
	"PIS": "PIS a Recolher - _TC",
	"COFINS": "COFINS a Recolher - _TC",
	"IBS": "IBS a Recolher - _TC",
	"CBS": "CBS a Recolher - _TC",
}


class TestConversaoDeAliquota(unittest.TestCase):
	def test_percentual_do_erpnext_vira_fracao(self):
		self.assertEqual(fracao(18), d("0.18"))
		self.assertEqual(fracao(0.9), d("0.009"))
		self.assertEqual(fracao("1.65"), d("0.0165"))

	def test_vazio_e_zero(self):
		for entrada in (None, "", 0):
			with self.subTest(entrada=entrada):
				self.assertEqual(fracao(entrada), d("0"))

	def test_ida_e_volta_preserva_o_valor(self):
		for valor in ("18", "0.9", "1.65", "7.6"):
			with self.subTest(valor=valor):
				self.assertEqual(percentual(fracao(valor)), Decimal(valor))

	def test_float_do_erpnext_nao_contamina_o_decimal(self):
		"""O ERPNext entrega float; passar direto a Decimal traria o lixo binário."""
		self.assertEqual(fracao(7.6), d("0.076"))


class TestLinhaDeItem(unittest.TestCase):
	def test_monta_item_fiscal(self):
		item = item_fiscal_de_linha(LINHA)

		self.assertEqual(item.valor_produtos, d("1000"))
		self.assertEqual(item.aliquota_icms, d("0.18"))
		self.assertEqual(item.aliquota_ipi, d("0.10"))
		self.assertEqual(item.cst_ibs_cbs, "000")

	def test_campos_ausentes_valem_zero(self):
		item = item_fiscal_de_linha({"net_amount": 500})

		self.assertEqual(item.aliquota_icms, d("0"))
		self.assertEqual(item.frete, d("0"))

	def test_aliquota_de_ibs_em_branco_fica_none(self):
		"""None faz a apuração usar a alíquota do ano; zero seria isenção declarada."""
		item = item_fiscal_de_linha(LINHA)

		self.assertIsNone(item.aliquota_ibs_uf)

	def test_aliquota_de_ibs_informada_e_respeitada(self):
		item = item_fiscal_de_linha({**LINHA, "br_aliquota_ibs_uf": 0.1})

		self.assertEqual(item.aliquota_ibs_uf, d("0.001"))

	def test_usa_amount_quando_nao_ha_net_amount(self):
		self.assertEqual(item_fiscal_de_linha({"amount": 250}).valor_produtos, d("250"))


class TestOperacao(unittest.TestCase):
	def test_indicador_de_ie_decide_contribuinte(self):
		self.assertTrue(
			operacao_de_documento({"br_indicador_ie": "Contribuinte ICMS"}).destinatario_contribuinte
		)
		self.assertFalse(
			operacao_de_documento({"br_indicador_ie": "Não Contribuinte"}).destinatario_contribuinte
		)

	def test_isento_nao_e_contribuinte_para_efeito_do_ipi(self):
		operacao = operacao_de_documento(
			{"br_indicador_ie": "Contribuinte isento de Inscrição no cadastro de Contribuintes"}
		)

		self.assertFalse(operacao.destinatario_contribuinte)

	def test_padroes_do_cabecalho_vazio(self):
		operacao = operacao_de_documento({})

		self.assertEqual(operacao.regime_pis_cofins, "cumulativo")
		self.assertTrue(operacao.excluir_icms_de_pis_cofins)

	def test_ano_de_competencia(self):
		self.assertEqual(operacao_de_documento({"br_ano_competencia": 2027}).ano, 2027)


class TestResultadoParaCampos(unittest.TestCase):
	def setUp(self):
		self.campos = resultado_para_campos(apurar(item_fiscal_de_linha(LINHA)))

	def test_cobre_exatamente_os_campos_declarados(self):
		"""A lista de campos e a gravação saem da mesma fonte — não podem divergir."""
		self.assertEqual(set(self.campos), set(CAMPOS_RESULTADO))

	def test_valores(self):
		self.assertEqual(self.campos["br_valor_icms"], d("180.00"))
		self.assertEqual(self.campos["br_valor_ipi"], d("100.00"))
		self.assertEqual(self.campos["br_base_pis_cofins"], d("820.00"))

	def test_check_e_inteiro_e_nao_booleano(self):
		"""O Frappe grava Check como 0/1; booleano do Python entraria como True."""
		self.assertIn(self.campos["br_ipi_na_base_icms"], (0, 1))


class TestLinhasDeImposto(unittest.TestCase):
	def setUp(self):
		self.apuracao = apurar_documento([item_fiscal_de_linha(LINHA)])
		self.linhas = linhas_de_imposto(self.apuracao.itens, CONTAS)

	def test_uma_linha_por_tributo_com_valor(self):
		self.assertEqual(
			[l["description"] for l in self.linhas], ["ICMS", "IPI", "PIS", "COFINS", "IBS", "CBS"]
		)

	def test_valores_batem_com_a_apuracao(self):
		por_tributo = {l["description"]: l["tax_amount"] for l in self.linhas}

		self.assertEqual(por_tributo["ICMS"], d("180.00"))
		self.assertEqual(por_tributo["IPI"], d("100.00"))
		self.assertEqual(por_tributo["CBS"], d("9.00"))

	def test_charge_type_actual_impede_recalculo_pelo_erpnext(self):
		for linha in self.linhas:
			with self.subTest(tributo=linha["description"]):
				self.assertEqual(linha["charge_type"], "Actual")

	def test_tributos_por_dentro_sao_marcados(self):
		por_dentro = {
			l["description"]: l["included_in_print_rate"] for l in self.linhas
		}

		self.assertEqual(por_dentro["ICMS"], 1)
		self.assertEqual(por_dentro["PIS"], 1)
		self.assertEqual(por_dentro["COFINS"], 1)
		self.assertEqual(por_dentro["IPI"], 0)
		self.assertEqual(por_dentro["IBS"], 0)
		self.assertEqual(por_dentro["CBS"], 0)

	def test_tributo_sem_conta_e_omitido(self):
		"""Melhor não lançar do que lançar em conta errada: some na conciliação."""
		linhas = linhas_de_imposto(self.apuracao.itens, {"ICMS": "ICMS a Recolher - _TC"})

		self.assertEqual([l["description"] for l in linhas], ["ICMS"])

	def test_tributo_zerado_nao_gera_linha(self):
		apuracao = apurar_documento([item_fiscal_de_linha({"net_amount": 1000})])
		linhas = linhas_de_imposto(apuracao.itens, CONTAS)

		self.assertNotIn("ICMS", [l["description"] for l in linhas])
		self.assertIn("CBS", [l["description"] for l in linhas])

	def test_sem_apuracao_nao_ha_linhas(self):
		self.assertEqual(linhas_de_imposto([], CONTAS), [])

	def test_soma_dos_itens_e_nao_recalculo(self):
		dois = apurar_documento([item_fiscal_de_linha(LINHA), item_fiscal_de_linha(LINHA)])
		linhas = linhas_de_imposto(dois.itens, CONTAS)
		por_tributo = {l["description"]: l["tax_amount"] for l in linhas}

		self.assertEqual(por_tributo["ICMS"], d("360.00"))


class TestReconciliacaoDaTabelaDeImpostos(unittest.TestCase):
	"""O que o usuário lançou à mão não pode ser destruído pela apuração."""

	def setUp(self):
		self.manual = {
			"charge_type": "Actual",
			"account_head": "Frete - _TC",
			"description": "Frete contratado",
			"tax_amount": d("150.00"),
		}
		self.automatica = {
			"charge_type": "Actual",
			"account_head": "ICMS a Recolher - _TC",
			"description": "ICMS",
			"tax_amount": d("100.00"),
			MARCA_AUTOMATICA: 1,
		}
		self.nova = {
			"charge_type": "Actual",
			"account_head": "ICMS a Recolher - _TC",
			"description": "ICMS",
			"tax_amount": d("180.00"),
		}

	def test_linha_manual_sobrevive(self):
		final = reconciliar_tabela_de_impostos([self.manual], [self.nova])

		self.assertEqual(final[0], self.manual)

	def test_linha_automatica_anterior_e_substituida(self):
		final = reconciliar_tabela_de_impostos([self.automatica], [self.nova])

		self.assertEqual(len(final), 1)
		self.assertEqual(final[0]["tax_amount"], d("180.00"))

	def test_reapuracao_nao_acumula_linhas(self):
		"""Salvar duas vezes não pode dobrar o imposto — o erro clássico deste padrão."""
		primeira = reconciliar_tabela_de_impostos([], [self.nova])
		segunda = reconciliar_tabela_de_impostos(primeira, [self.nova])

		self.assertEqual(len(primeira), len(segunda))
		self.assertEqual(
			sum(l["tax_amount"] for l in segunda), sum(l["tax_amount"] for l in primeira)
		)

	def test_manuais_vem_antes_e_na_ordem_original(self):
		outro_manual = {**self.manual, "description": "Seguro"}
		final = reconciliar_tabela_de_impostos([self.manual, self.automatica, outro_manual], [self.nova])

		self.assertEqual(
			[l["description"] for l in final], ["Frete contratado", "Seguro", "ICMS"]
		)

	def test_novas_linhas_recebem_a_marca(self):
		final = reconciliar_tabela_de_impostos([], [self.nova])

		self.assertEqual(final[0][MARCA_AUTOMATICA], 1)

	def test_nao_muta_as_listas_recebidas(self):
		"""A função não pode alterar o que recebeu: o chamador ainda usa `geradas`."""
		geradas = [dict(self.nova)]
		reconciliar_tabela_de_impostos([], geradas)

		self.assertNotIn(MARCA_AUTOMATICA, geradas[0])

	def test_sem_nada_gerado_as_automaticas_antigas_somem(self):
		"""Zerar as alíquotas precisa limpar os impostos, não deixar o valor antigo."""
		final = reconciliar_tabela_de_impostos([self.manual, self.automatica], [])

		self.assertEqual([l["description"] for l in final], ["Frete contratado"])


if __name__ == "__main__":
	unittest.main()
