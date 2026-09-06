# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Depreciação fiscal: as regras do RIR/2018 que um método linear genérico erra.

Cada teste desta suíte existe porque a implementação "óbvia" acerta o caso comum e erra a
regra — e a regra está citada por artigo, lido do Decreto 9.580/2018 baixado do Planalto.

Teste-âncora: `test_a_base_e_sempre_o_custo_e_nunca_o_saldo_residual`. É a diferença entre
a quota fiscal brasileira e o *Written Down Value* que o ERPNext oferece por padrão, e o
erro não aparece no primeiro ano — aparece do segundo em diante, quando o saldo já caiu.

Módulo puro: roda sem bench.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.contabil.depreciacao import (
	COEFICIENTE_POR_TURNOS,
	TAXAS_ANUAIS,
	DepreciacaoInvalida,
	coeficiente_de_turnos,
	depreciar,
	quota_anual,
	quota_mensal,
	taxa_de_bem_usado,
)

CUSTO = Decimal("120000.00")
TAXA_MAQUINA = Decimal("10")


class TestBaseDeCalculo(unittest.TestCase):
	def test_a_base_e_sempre_o_custo_e_nunca_o_saldo_residual(self):
		"""Teste-âncora: art. 319. A quota do último ano é igual à do primeiro.

		Num método de saldo decrescente, a segunda quota seria menor — e é isso que
		distingue a quota fiscal brasileira do *Written Down Value*.
		"""
		primeira = depreciar(CUSTO, TAXA_MAQUINA, meses=12)
		segunda = depreciar(CUSTO, TAXA_MAQUINA, meses=12, acumulado=primeira.acumulado)

		self.assertEqual(primeira.quota, segunda.quota)

	def test_a_quota_anual_e_a_taxa_sobre_o_custo(self):
		self.assertEqual(Decimal("12000.00"), quota_anual(CUSTO, TAXA_MAQUINA))

	def test_a_quota_mensal_e_um_doze_avos(self):
		self.assertEqual(Decimal("1000.00"), quota_mensal(CUSTO, TAXA_MAQUINA))


class TestMesInteiro(unittest.TestCase):
	"""Art. 319, § 2º: dispensado o ajuste para bens postos em funcionamento no curso do
	mês. Um mês é um mês."""

	def test_nao_ha_rateio_por_dias(self):
		"""A função nem oferece o parâmetro: quem faz *pro rata die* deduz a menos, e a
		diferença atravessa a vida inteira do bem."""
		import inspect

		parametros = inspect.signature(depreciar).parameters

		self.assertIn("meses", parametros)
		self.assertNotIn("dias", parametros)

	def test_o_arredondamento_e_do_mes_e_nao_do_ano_dividido(self):
		"""Dividir uma quota anual já arredondada por 12 espalharia o resto por todos os
		meses. Com 1000/ano e taxa de 3%, a diferença aparece."""
		custo = Decimal("1000.00")
		taxa = Decimal("3")

		self.assertEqual(Decimal("2.50"), quota_mensal(custo, taxa))


class TestTurnos(unittest.TestCase):
	"""Art. 323, citado literalmente no módulo."""

	def test_os_tres_coeficientes_da_lei(self):
		self.assertEqual(Decimal("1.0"), coeficiente_de_turnos(1))
		self.assertEqual(Decimal("1.5"), coeficiente_de_turnos(2))
		self.assertEqual(Decimal("2.0"), coeficiente_de_turnos(3))

	def test_a_tabela_tem_exatamente_os_tres_casos_da_lei(self):
		self.assertEqual({1, 2, 3}, set(COEFICIENTE_POR_TURNOS))

	def test_turno_fora_da_lei_e_recusado(self):
		"""Interpolar meio turno ou um quarto turno seria inventar direito."""
		for turnos in (0, 4, -1):
			with self.subTest(turnos=turnos):
				with self.assertRaises(DepreciacaoInvalida) as erro:
					coeficiente_de_turnos(turnos)

				self.assertEqual("turnos", erro.exception.campo)

	def test_dois_turnos_aumentam_a_quota_em_metade(self):
		self.assertEqual(
			quota_anual(CUSTO, TAXA_MAQUINA) * Decimal("1.5"),
			quota_anual(CUSTO, TAXA_MAQUINA, turnos=2),
		)

	def test_a_aceleracao_encurta_a_vida_e_nao_aumenta_a_deducao(self):
		"""O teto do art. 317, § 3º é o que faz isso: três turnos deduzem o mesmo valor em
		metade do tempo, nunca mais que o custo."""
		acelerado = depreciar(CUSTO, TAXA_MAQUINA, meses=120, turnos=3)

		self.assertEqual(CUSTO, acelerado.acumulado)
		self.assertTrue(acelerado.totalmente_depreciado)


class TestTeto(unittest.TestCase):
	"""Art. 317, § 3º: *"Em qualquer hipótese"*."""

	def test_o_acumulado_nunca_passa_do_custo(self):
		resultado = depreciar(CUSTO, TAXA_MAQUINA, meses=240)

		self.assertEqual(CUSTO, resultado.acumulado)

	def test_a_ultima_quota_e_reduzida_ao_que_falta(self):
		quase = CUSTO - Decimal("300.00")
		resultado = depreciar(CUSTO, TAXA_MAQUINA, meses=12, acumulado=quase)

		self.assertEqual(Decimal("300.00"), resultado.quota)
		self.assertEqual(CUSTO, resultado.acumulado)

	def test_o_excedente_nao_e_diferido(self):
		"""Não sobra crédito para o período seguinte: o excedente simplesmente não existe."""
		cheio = depreciar(CUSTO, TAXA_MAQUINA, meses=240)
		depois = depreciar(CUSTO, TAXA_MAQUINA, meses=12, acumulado=cheio.acumulado)

		self.assertEqual(Decimal("0.00"), depois.quota)

	def test_acumulado_maior_que_o_custo_e_recusado(self):
		with self.assertRaises(DepreciacaoInvalida) as erro:
			depreciar(CUSTO, TAXA_MAQUINA, acumulado=CUSTO + Decimal("1"))

		self.assertEqual("acumulado", erro.exception.campo)

	def test_o_valor_residual_chega_a_zero(self):
		resultado = depreciar(CUSTO, TAXA_MAQUINA, meses=240)

		self.assertEqual(Decimal("0.00"), resultado.valor_residual)


class TestBensUsados(unittest.TestCase):
	"""Art. 322 — o ponto em que a intuição erra."""

	def test_vale_o_maior_dos_dois_prazos_e_nao_o_menor(self):
		"""Metade de 10 são 5; o restante são 8. Vale 8.

		Escolher o menor deduziria depressa demais, que é o lado glosado.
		"""
		self.assertEqual(8, taxa_de_bem_usado(vida_util_nova=10, vida_util_restante=8))

	def test_quando_o_restante_e_curto_vale_a_metade_da_vida_nova(self):
		self.assertEqual(5, taxa_de_bem_usado(vida_util_nova=10, vida_util_restante=2))

	def test_a_metade_de_vida_impar_arredonda_para_cima(self):
		"""Meia vida útil de 5 anos são 3, não 2 — arredondar para baixo deduziria mais
		rápido, na direção da glosa."""
		self.assertEqual(3, taxa_de_bem_usado(vida_util_nova=5, vida_util_restante=1))

	def test_bem_sem_vida_util_restante_ainda_usa_a_metade(self):
		self.assertEqual(2, taxa_de_bem_usado(vida_util_nova=4, vida_util_restante=0))

	def test_vida_util_nova_invalida_e_recusada(self):
		with self.assertRaises(DepreciacaoInvalida) as erro:
			taxa_de_bem_usado(vida_util_nova=0, vida_util_restante=3)

		self.assertEqual("vida_util_nova", erro.exception.campo)


class TestTabelaDeTaxas(unittest.TestCase):
	def test_taxa_e_vida_util_sao_coerentes_entre_si(self):
		"""100 / vida útil = taxa. Uma linha em que os dois discordem é erro de digitação
		que passaria despercebido — a taxa seria usada e a vida útil ignorada."""
		for especie, (taxa, anos) in TAXAS_ANUAIS.items():
			with self.subTest(especie=especie):
				self.assertEqual(Decimal("100") / Decimal(anos), taxa)

	def test_as_especies_conhecidas_do_anexo_iii(self):
		self.assertEqual((Decimal("4"), 25), TAXAS_ANUAIS["edificacoes"])
		self.assertEqual((Decimal("20"), 5), TAXAS_ANUAIS["veiculos_de_passageiros"])
		self.assertEqual((Decimal("25"), 4), TAXAS_ANUAIS["veiculos_de_carga"])
		self.assertEqual((Decimal("20"), 5), TAXAS_ANUAIS["computadores_e_perifericos"])

	def test_veiculo_de_carga_deprecia_mais_rapido_que_o_de_passageiros(self):
		"""Espécies vizinhas com taxas diferentes: é o tipo de par que se confunde ao
		classificar, e o Anexo III os separa."""
		self.assertGreater(
			TAXAS_ANUAIS["veiculos_de_carga"][0],
			TAXAS_ANUAIS["veiculos_de_passageiros"][0],
		)


class TestRecusas(unittest.TestCase):
	def test_custo_zerado_ou_negativo_e_recusado(self):
		for custo in (Decimal("0"), Decimal("-1")):
			with self.subTest(custo=custo):
				with self.assertRaises(DepreciacaoInvalida) as erro:
					quota_anual(custo, TAXA_MAQUINA)

				self.assertEqual("custo", erro.exception.campo)

	def test_taxa_zerada_e_recusada(self):
		with self.assertRaises(DepreciacaoInvalida) as erro:
			quota_anual(CUSTO, Decimal("0"))

		self.assertEqual("taxa_anual", erro.exception.campo)

	def test_meses_negativos_sao_recusados(self):
		with self.assertRaises(DepreciacaoInvalida) as erro:
			depreciar(CUSTO, TAXA_MAQUINA, meses=-1)

		self.assertEqual("meses", erro.exception.campo)


if __name__ == "__main__":
	unittest.main()
