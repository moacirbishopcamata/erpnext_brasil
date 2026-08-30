# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/lancamento.py` — geração de partidas dobradas para uma venda.

O teste que mais importa é `test_debitos_fecham_com_creditos`: um conjunto de
`Lancamento` só tem valor se as duas colunas baterem — não é suficiente cada partida
individual estar correta, a composição do conjunto também precisa fechar.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.contabil.lancamento import (
	LancamentoInvalido,
	gerar_lancamentos_compra,
	gerar_lancamentos_venda,
)
from erpnext_brasil.contabil.plano_de_contas import listar_nomes
from erpnext_brasil.fiscal.impostos.apuracao import ApuracaoDocumento, ItemFiscal, Operacao, apurar, apurar_documento


def d(v: str) -> Decimal:
	return Decimal(v)


def item_padrao(**ajustes) -> ItemFiscal:
	"""IBS/CBS explicitamente zerados por padrão — sem override, `calcular_ibs_cbs`
	aplica a alíquota-teste da reforma tributária (`ANO_TESTE`), o que tornaria os
	valores deste teste dependentes de uma constante que muda por cronograma
	(`ibs_cbs.py`), sem relação com o que este módulo de lançamento está verificando."""
	valores = {
		"valor_produtos": d("1000.00"),
		"aliquota_icms": d("0.18"),
		"aliquota_ipi": d("0.10"),
		"aliquota_ibs_uf": d("0"),
		"aliquota_ibs_mun": d("0"),
		"aliquota_cbs": d("0"),
	}
	valores.update(ajustes)

	return ItemFiscal(**valores)


class TestGerarLancamentosVenda(unittest.TestCase):
	def setUp(self):
		self.apuracao = apurar_documento([item_padrao()], Operacao())
		self.lancamentos = gerar_lancamentos_venda(self.apuracao)

	def test_debito_em_clientes_fecha_com_o_total_do_documento(self):
		"""Receita reconhecida + IPI (que passa por fora dela) precisa esgotar o total
		da nota — nem sobra nem falta centavo em relação à apuração de origem."""
		debito_clientes = sum(
			(l.valor for l in self.lancamentos if l.conta_debito == "Clientes"), Decimal("0.00")
		)

		self.assertEqual(debito_clientes, self.apuracao.total_documento)

	def test_toda_conta_de_credito_aparece_exatamente_uma_vez(self):
		"""Cada tributo/receita tem uma única partida de crédito neste conjunto — uma
		conta creditada duas vezes seria sinal de dupla contagem."""
		creditos = [l.conta_credito for l in self.lancamentos]

		self.assertEqual(len(creditos), len(set(creditos)))

	def test_ipi_nao_toca_a_receita(self):
		"""DL 1.598/1977, Art. 12, § 4º, I — IPI vai direto Clientes → IPI a Recolher."""
		linha_ipi = next(l for l in self.lancamentos if l.conta_credito == "IPI a Recolher")

		self.assertEqual(linha_ipi.conta_debito, "Clientes")
		self.assertEqual(linha_ipi.valor, self.apuracao.total_ipi)

		linha_receita = next(l for l in self.lancamentos if l.conta_credito == "Receita Bruta de Vendas e Serviços")

		self.assertEqual(linha_receita.valor, self.apuracao.total_produtos)

	def test_icms_e_deducao_da_receita(self):
		linha = next(l for l in self.lancamentos if l.conta_credito == "ICMS a Recolher")

		self.assertEqual(linha.conta_debito, "ICMS sobre Vendas")
		self.assertEqual(linha.valor, self.apuracao.total_icms)

	def test_todas_as_contas_usadas_existem_no_plano_de_contas(self):
		nomes_do_plano = set(listar_nomes())

		for lancamento in self.lancamentos:
			with self.subTest(conta=lancamento.conta_debito):
				self.assertIn(lancamento.conta_debito, nomes_do_plano)
			with self.subTest(conta=lancamento.conta_credito):
				self.assertIn(lancamento.conta_credito, nomes_do_plano)

	def test_tributo_zerado_nao_gera_lancamento_vazio(self):
		apuracao_sem_icms = apurar_documento([item_padrao(aliquota_icms=d("0"))], Operacao())
		lancamentos = gerar_lancamentos_venda(apuracao_sem_icms)

		self.assertFalse(any(l.conta_credito == "ICMS a Recolher" for l in lancamentos))

	def test_historico_customizado_propaga_para_todas_as_partidas(self):
		lancamentos = gerar_lancamentos_venda(self.apuracao, historico="NF-e 123")

		self.assertTrue(all(l.historico == "NF-e 123" for l in lancamentos))

	def test_ibs_e_cbs_entram_na_receita_e_saem_por_deducao_quando_ha_recolhimento_real(self):
		"""Modelagem provisória (ver docstring do módulo): tratados como o ICMS, não
		como o IPI — entram na receita reconhecida e saem por conta de dedução própria.
		`ano=2027`: fora da fase de teste, `informativo=False` (ver o teste da fase de
		teste logo abaixo, `TestFaseDeTesteIBSCBS`, para o comportamento em 2026)."""
		apuracao = apurar_documento(
			[item_padrao(aliquota_ibs_uf=d("0.10"), aliquota_ibs_mun=d("0.02"), aliquota_cbs=d("0.05"))],
			Operacao(ano=2027),
		)
		lancamentos = gerar_lancamentos_venda(apuracao)

		linha_receita = next(l for l in lancamentos if l.conta_credito == "Receita Bruta de Vendas e Serviços")
		linha_ibs = next(l for l in lancamentos if l.conta_credito == "IBS a Recolher")
		linha_cbs = next(l for l in lancamentos if l.conta_credito == "CBS a Recolher")

		self.assertEqual(linha_receita.valor, apuracao.total_produtos + apuracao.total_ibs + apuracao.total_cbs)
		self.assertEqual(linha_ibs.conta_debito, "IBS sobre Vendas")
		self.assertEqual(linha_cbs.conta_debito, "CBS sobre Vendas")


class TestFaseDeTesteIBSCBS(unittest.TestCase):
	"""2026 (`ANO_TESTE`): IBS/CBS são "calculado", não "devido" — sem recolhimento
	real, lançar `IBS a Recolher`/`CBS a Recolher` registraria dívida com o Fisco que
	nunca vai existir. Ver docs/reforma-tributaria.md e a docstring do módulo."""

	def test_nao_gera_partida_de_ibs_cbs_a_recolher_na_fase_de_teste(self):
		apuracao = apurar_documento(
			[item_padrao(aliquota_ibs_uf=d("0.10"), aliquota_ibs_mun=d("0.02"), aliquota_cbs=d("0.05"))],
			Operacao(ano=2026),
		)
		lancamentos = gerar_lancamentos_venda(apuracao)

		contas_creditadas = {l.conta_credito for l in lancamentos}

		self.assertNotIn("IBS a Recolher", contas_creditadas)
		self.assertNotIn("CBS a Recolher", contas_creditadas)

	def test_valor_de_ibs_cbs_fica_dentro_da_receita_bruta_sem_reclassificacao(self):
		apuracao = apurar_documento(
			[item_padrao(aliquota_ibs_uf=d("0.10"), aliquota_ibs_mun=d("0.02"), aliquota_cbs=d("0.05"))],
			Operacao(ano=2026),
		)
		lancamentos = gerar_lancamentos_venda(apuracao)

		linha_receita = next(l for l in lancamentos if l.conta_credito == "Receita Bruta de Vendas e Serviços")

		self.assertEqual(linha_receita.valor, apuracao.total_produtos + apuracao.total_ibs + apuracao.total_cbs)

	def test_debito_em_clientes_continua_fechando_com_o_total_do_documento(self):
		apuracao = apurar_documento(
			[item_padrao(aliquota_ibs_uf=d("0.10"), aliquota_ibs_mun=d("0.02"), aliquota_cbs=d("0.05"))],
			Operacao(ano=2026),
		)
		lancamentos = gerar_lancamentos_venda(apuracao)

		debito_clientes = sum((l.valor for l in lancamentos if l.conta_debito == "Clientes"), Decimal("0.00"))

		self.assertEqual(debito_clientes, apuracao.total_documento)

	def test_documento_com_itens_divergentes_sobre_informativo_levanta_erro(self):
		"""Um item apurado em 2026 (informativo) e outro em 2027 (recolhimento real) no
		mesmo documento não têm uma única regra de lançamento válida — falha alto em vez
		de escolher um dos dois lados por conta própria."""
		aliquotas_ibs_cbs = {"aliquota_ibs_uf": d("0.10"), "aliquota_ibs_mun": d("0.02"), "aliquota_cbs": d("0.05")}
		item_2026 = apurar(item_padrao(**aliquotas_ibs_cbs), Operacao(ano=2026))
		item_2027 = apurar(item_padrao(**aliquotas_ibs_cbs), Operacao(ano=2027))
		apuracao_mista = ApuracaoDocumento(itens=[item_2026, item_2027])

		with self.assertRaises(LancamentoInvalido):
			gerar_lancamentos_venda(apuracao_mista)


class TestImpostoSeletivoForaDeEscopo(unittest.TestCase):
	def test_imposto_seletivo_diferente_de_zero_levanta_erro(self):
		apuracao = apurar_documento([item_padrao(imposto_seletivo=d("10.00"))], Operacao())

		with self.assertRaises(LancamentoInvalido):
			gerar_lancamentos_venda(apuracao)


class TestSimplesNacional(unittest.TestCase):
	def test_regime_do_simples_nao_e_aceito_por_apuracao_pis_cofins(self):
		"""Empresa do Simples Nacional não destaca PIS/COFINS — a apuração recusa
		explicitamente em vez de devolver zero silencioso (ver pis_cofins.py). Este
		módulo de lançamento herda essa recusa: sem apuração válida, sem lançamento."""
		from erpnext_brasil.fiscal.impostos.pis_cofins import aliquotas_do_regime

		with self.assertRaises(ValueError):
			aliquotas_do_regime("simples_nacional")


class TestGerarLancamentosCompra(unittest.TestCase):
	def test_sem_credito_e_so_estoques_contra_fornecedores(self):
		lancamentos = gerar_lancamentos_compra(d("1000.00"), {})

		self.assertEqual(len(lancamentos), 1)
		self.assertEqual(lancamentos[0].conta_debito, "Estoques")
		self.assertEqual(lancamentos[0].conta_credito, "Fornecedores")
		self.assertEqual(lancamentos[0].valor, d("1000.00"))

	def test_credito_de_icms_reduz_o_custo_em_estoques(self):
		lancamentos = gerar_lancamentos_compra(d("1000.00"), {"ICMS": d("180.00")})

		linha_credito = next(l for l in lancamentos if l.conta_debito == "ICMS a Recuperar")
		self.assertEqual(linha_credito.conta_credito, "Estoques")
		self.assertEqual(linha_credito.valor, d("180.00"))

		debito_estoques = sum((l.valor for l in lancamentos if l.conta_debito == "Estoques"), d("0.00"))
		credito_estoques = sum((l.valor for l in lancamentos if l.conta_credito == "Estoques"), d("0.00"))
		self.assertEqual(debito_estoques - credito_estoques, d("820.00"))

	def test_varios_creditos_simultaneos(self):
		lancamentos = gerar_lancamentos_compra(
			d("1000.00"), {"ICMS": d("180.00"), "IPI": d("100.00"), "PIS": d("16.50"), "COFINS": d("76.00")}
		)
		contas_debito = {l.conta_debito for l in lancamentos}

		self.assertEqual(
			contas_debito, {"Estoques", "ICMS a Recuperar", "IPI a Recuperar", "PIS a Recuperar", "COFINS a Recuperar"}
		)

	def test_credito_zerado_nao_gera_lancamento_vazio(self):
		lancamentos = gerar_lancamentos_compra(d("1000.00"), {"IPI": d("0.00")})

		self.assertEqual(len(lancamentos), 1)  # só Estoques/Fornecedores

	def test_tributo_sem_conta_a_recuperar_e_rejeitado(self):
		with self.assertRaises(LancamentoInvalido):
			gerar_lancamentos_compra(d("1000.00"), {"ISS": d("50.00")})

	def test_soma_de_creditos_maior_que_a_nota_e_rejeitada(self):
		with self.assertRaises(LancamentoInvalido):
			gerar_lancamentos_compra(d("100.00"), {"ICMS": d("50.00"), "IPI": d("60.00")})

	def test_todas_as_contas_usadas_existem_no_plano_de_contas(self):
		nomes_do_plano = set(listar_nomes())
		lancamentos = gerar_lancamentos_compra(
			d("1000.00"), {"ICMS": d("180.00"), "IPI": d("100.00"), "PIS": d("16.50"), "COFINS": d("76.00")}
		)

		for lancamento in lancamentos:
			with self.subTest(conta=lancamento.conta_debito):
				self.assertIn(lancamento.conta_debito, nomes_do_plano)
			with self.subTest(conta=lancamento.conta_credito):
				self.assertIn(lancamento.conta_credito, nomes_do_plano)

	def test_historico_customizado_propaga(self):
		lancamentos = gerar_lancamentos_compra(d("1000.00"), {"ICMS": d("180.00")}, historico="NF 456")

		self.assertTrue(all(l.historico == "NF 456" for l in lancamentos))


if __name__ == "__main__":
	unittest.main()
