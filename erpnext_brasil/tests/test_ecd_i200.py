# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/ecd_i200.py` — registros I200/I250 (lançamento contábil).

O teste que mais importa é `test_vl_dc_das_duas_partidas_fecha_com_vl_lcto`: a mesma
disciplina de balanceamento verificada em `lancamento.py` (débito == crédito), agora na
travessia para o formato da ECD — nada pode se perder na conversão.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.contabil.ecd_i200 import ContaDesconhecida, montar_i200_i250, montar_i200_i250_multiplo
from erpnext_brasil.contabil.lancamento import Lancamento, LancamentoMultiplo, Partida

DATA = "01012026"


def d(v: str) -> Decimal:
	return Decimal(v)


def lancamento(conta_debito: str, conta_credito: str, valor: str, historico: str = "teste") -> Lancamento:
	return Lancamento(
		conta_debito=conta_debito, conta_credito=conta_credito, valor=d(valor), historico=historico
	)


class TestMontarI200I250(unittest.TestCase):
	def test_um_par_por_lancamento(self):
		lancamentos = [
			lancamento("Clientes", "Receita Bruta de Vendas e Serviços", "1000.00"),
			lancamento("ICMS sobre Vendas", "ICMS a Recolher", "180.00"),
		]
		pares = montar_i200_i250(lancamentos, DATA)

		self.assertEqual(len(pares), 2)

	def test_i200_tem_reg_num_dt_vl_ind(self):
		pares = montar_i200_i250(
			[lancamento("Clientes", "Receita Bruta de Vendas e Serviços", "1000.00")], DATA
		)
		i200, _partidas = pares[0]

		self.assertEqual(list(i200), ["REG", "NUM_LCTO", "DT_LCTO", "VL_LCTO", "IND_LCTO"])
		self.assertEqual(i200["REG"], "I200")
		self.assertEqual(i200["DT_LCTO"], DATA)
		self.assertEqual(i200["VL_LCTO"], d("1000.00"))
		self.assertEqual(i200["IND_LCTO"], "N")

	def test_numeracao_sequencial_a_partir_do_numero_inicial(self):
		pares = montar_i200_i250(
			[
				lancamento("Clientes", "Receita Bruta de Vendas e Serviços", "1000.00"),
				lancamento("ICMS sobre Vendas", "ICMS a Recolher", "180.00"),
			],
			DATA,
			numero_inicial=42,
		)

		self.assertEqual(pares[0][0]["NUM_LCTO"], "42")
		self.assertEqual(pares[1][0]["NUM_LCTO"], "43")

	def test_duas_partidas_debito_e_credito(self):
		_i200, partidas = montar_i200_i250(
			[lancamento("Clientes", "Receita Bruta de Vendas e Serviços", "1000.00")], DATA
		)[0]

		self.assertEqual(len(partidas), 2)
		self.assertEqual(partidas[0]["IND_DC"], "D")
		self.assertEqual(partidas[1]["IND_DC"], "C")

	def test_ordem_dos_campos_de_i250(self):
		_i200, partidas = montar_i200_i250(
			[lancamento("Clientes", "Receita Bruta de Vendas e Serviços", "1000.00")], DATA
		)[0]

		self.assertEqual(
			list(partidas[0]),
			["REG", "COD_CTA", "COD_CCUS", "VL_DC", "IND_DC", "NUM_ARQ", "COD_HIST_PAD", "HIST", "COD_PART"],
		)

	def test_cod_cta_resolvido_pelo_nome_da_conta(self):
		from erpnext_brasil.contabil.plano_de_contas import montar_codigos

		codigos = montar_codigos()
		_i200, partidas = montar_i200_i250(
			[lancamento("Clientes", "Receita Bruta de Vendas e Serviços", "1000.00")], DATA
		)[0]

		self.assertEqual(partidas[0]["COD_CTA"], codigos["Clientes"])
		self.assertEqual(partidas[1]["COD_CTA"], codigos["Receita Bruta de Vendas e Serviços"])

	def test_vl_dc_das_duas_partidas_fecha_com_vl_lcto(self):
		i200, partidas = montar_i200_i250(
			[lancamento("Clientes", "Receita Bruta de Vendas e Serviços", "1000.00")], DATA
		)[0]

		self.assertEqual(partidas[0]["VL_DC"], i200["VL_LCTO"])
		self.assertEqual(partidas[1]["VL_DC"], i200["VL_LCTO"])

	def test_historico_propaga_para_o_campo_hist(self):
		_i200, partidas = montar_i200_i250(
			[lancamento("Clientes", "Receita Bruta de Vendas e Serviços", "1000.00", historico="NF-e 123")],
			DATA,
		)[0]

		self.assertEqual(partidas[0]["HIST"], "NF-e 123")
		self.assertEqual(partidas[1]["HIST"], "NF-e 123")

	def test_conta_desconhecida_levanta_erro(self):
		with self.assertRaises(ContaDesconhecida):
			montar_i200_i250(
				[lancamento("Conta Inventada", "Receita Bruta de Vendas e Serviços", "1.00")], DATA
			)

	def test_lista_vazia_devolve_lista_vazia(self):
		self.assertEqual(montar_i200_i250([], DATA), [])


class TestMontarI200I250Multiplo(unittest.TestCase):
	def test_uma_linha_i250_por_partida(self):
		lancamento = LancamentoMultiplo(
			debitos=(
				Partida("Despesas com Vendas", d("300.00")),
				Partida("Despesas Gerais e Administrativas", d("200.00")),
			),
			creditos=(Partida("Disponibilidades", d("500.00")),),
			historico="Rateio",
		)
		_i200, partidas = montar_i200_i250_multiplo([lancamento], DATA)[0]

		self.assertEqual(len(partidas), 3)

	def test_vl_lcto_e_o_valor_total(self):
		lancamento = LancamentoMultiplo(
			debitos=(
				Partida("Despesas com Vendas", d("300.00")),
				Partida("Despesas Gerais e Administrativas", d("200.00")),
			),
			creditos=(Partida("Disponibilidades", d("500.00")),),
			historico="Rateio",
		)
		i200, _partidas = montar_i200_i250_multiplo([lancamento], DATA)[0]

		self.assertEqual(i200["VL_LCTO"], d("500.00"))

	def test_soma_dos_ind_dc_fecha_com_vl_lcto(self):
		lancamento = LancamentoMultiplo(
			debitos=(
				Partida("Despesas com Vendas", d("300.00")),
				Partida("Despesas Gerais e Administrativas", d("200.00")),
			),
			creditos=(Partida("Disponibilidades", d("500.00")),),
			historico="Rateio",
		)
		i200, partidas = montar_i200_i250_multiplo([lancamento], DATA)[0]

		soma_debitos = sum((p["VL_DC"] for p in partidas if p["IND_DC"] == "D"), d("0.00"))
		soma_creditos = sum((p["VL_DC"] for p in partidas if p["IND_DC"] == "C"), d("0.00"))

		self.assertEqual(soma_debitos, i200["VL_LCTO"])
		self.assertEqual(soma_creditos, i200["VL_LCTO"])

	def test_conta_desconhecida_levanta_erro(self):
		lancamento = LancamentoMultiplo(
			debitos=(Partida("Conta Inventada", d("100.00")),),
			creditos=(Partida("Disponibilidades", d("100.00")),),
			historico="teste",
		)

		with self.assertRaises(ContaDesconhecida):
			montar_i200_i250_multiplo([lancamento], DATA)

	def test_lista_vazia_devolve_lista_vazia(self):
		self.assertEqual(montar_i200_i250_multiplo([], DATA), [])


if __name__ == "__main__":
	unittest.main()
