# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Transferência entre estabelecimentos do mesmo titular, e a alíquota que a limita.

Teste-âncora: `test_o_espirito_santo_recebe_a_sete_mas_nao_manda_a_sete`. O ES é Sudeste e
mesmo assim é **destino** da alíquota reduzida sem ser **origem** dela — a exceção que uma
tabela por região silencia, e o erro seria de cinco pontos percentuais numa nota que
ninguém confere.

Segundo eixo: `test_entrada_e_saida_nao_sao_espelho`. Na transferência, quem remete
classifica pela **origem** da mercadoria e quem recebe classifica pelo **destino** que vai
dar a ela — diferente de venda/devolução, onde os dois lados usam o mesmo par. Tratar igual
produziria um código válido, existente, e errado.

Módulos puros: rodam sem bench.
"""

import unittest
from decimal import Decimal
from pathlib import Path

from erpnext_brasil.fiscal.cfop import (
	FINALIDADE_COMERCIALIZACAO,
	FINALIDADE_INDUSTRIALIZACAO,
	CfopInvalido,
	cfop_transferencia_ativo_imobilizado,
	cfop_transferencia_entrada,
	cfop_transferencia_saida,
	cfop_transferencia_uso_e_consumo,
	cfop_venda,
)
from erpnext_brasil.fiscal.impostos.aliquota_interestadual import (
	ALIQUOTA_GERAL,
	ALIQUOTA_IMPORTADO,
	ALIQUOTA_REDUZIDA,
	UfInvalida,
	aliquota_interestadual,
)
from erpnext_brasil.fiscal.transferencia import (
	BASE_CUSTO_DE_PRODUCAO,
	BASE_VALOR_MEDIO_DE_ENTRADA,
	TAMANHO_DA_RAIZ,
	TransferenciaInvalida,
	mesmo_titular,
	transferir_credito,
)
from erpnext_brasil.tests.ajudantes import sem_docstrings

_COSTURA = sem_docstrings(
	(Path(__file__).resolve().parent.parent / "integracao" / "cfop_sugestao.py").read_text(encoding="utf-8")
)


class TestAliquotaInterestadual(unittest.TestCase):
	def test_o_espirito_santo_recebe_a_sete_mas_nao_manda_a_sete(self):
		"""Teste-âncora. O ES é Sudeste, e a Resolução SF 22/1989 o põe no grupo de
		**destino** da alíquota reduzida, não no de origem."""
		self.assertEqual(ALIQUOTA_REDUZIDA, aliquota_interestadual("SP", "ES"))
		self.assertEqual(ALIQUOTA_GERAL, aliquota_interestadual("ES", "RO"))

	def test_sul_e_sudeste_para_o_norte_e_sete_por_cento(self):
		for origem in ("SP", "RJ", "MG", "PR", "SC", "RS"):
			with self.subTest(origem=origem):
				self.assertEqual(ALIQUOTA_REDUZIDA, aliquota_interestadual(origem, "RO"))

	def test_o_norte_manda_a_doze_por_cento(self):
		"""Rondônia remetendo para São Paulo: a regra geral, não a reduzida."""
		self.assertEqual(ALIQUOTA_GERAL, aliquota_interestadual("RO", "SP"))

	def test_entre_estados_do_sul_e_doze_por_cento(self):
		"""A reduzida exige destino no grupo certo; Sul para Sudeste não é."""
		self.assertEqual(ALIQUOTA_GERAL, aliquota_interestadual("PR", "SP"))

	def test_importado_e_quatro_por_cento_em_qualquer_par(self):
		"""Resolução SF 13/2012 substitui as outras duas, não se soma a elas."""
		self.assertEqual(ALIQUOTA_IMPORTADO, aliquota_interestadual("SP", "RO", importado=True))
		self.assertEqual(ALIQUOTA_IMPORTADO, aliquota_interestadual("RO", "SP", importado=True))

	def test_recusa_operacao_interna(self):
		"""Devolver 12% para uma operação dentro do mesmo estado seria dar um número
		plausível para uma pergunta que não existe."""
		with self.assertRaises(UfInvalida):
			aliquota_interestadual("RO", "RO")

	def test_recusa_sigla_invalida(self):
		for par in (("XX", "SP"), ("SP", "XX"), ("", "SP")):
			with self.subTest(par=par), self.assertRaises(UfInvalida):
				aliquota_interestadual(*par)

	def test_aceita_minusculas_e_espacos(self):
		self.assertEqual(ALIQUOTA_REDUZIDA, aliquota_interestadual(" sp ", "ro"))

	def test_as_aliquotas_sao_fracao(self):
		"""Alíquota é fração em todo o app: 0.12, nunca 12."""
		for aliquota in (ALIQUOTA_GERAL, ALIQUOTA_REDUZIDA, ALIQUOTA_IMPORTADO):
			self.assertLess(aliquota, Decimal(1))


class TestCfopDeTransferencia(unittest.TestCase):
	def test_entrada_e_saida_nao_sao_espelho(self):
		"""Teste-âncora do CFOP. A saída pergunta "de onde veio"; a entrada, "para que
		vai" — e as duas perguntas dão respostas diferentes para a mesma remessa.

		Mercadoria comprada de terceiro e transferida para ser industrializada no destino:
		sai como `5152` (recebida de terceiros) e entra como `1151` (para
		industrialização). Se fossem espelho, entraria como `1152`.
		"""
		self.assertEqual("5152", cfop_transferencia_saida(mesmo_estado=True, producao_propria=False))
		self.assertEqual(
			"1151",
			cfop_transferencia_entrada(mesmo_estado=True, finalidade=FINALIDADE_INDUSTRIALIZACAO),
		)

	def test_saida_de_producao_propria(self):
		self.assertEqual("5151", cfop_transferencia_saida(mesmo_estado=True, producao_propria=True))
		self.assertEqual("6151", cfop_transferencia_saida(mesmo_estado=False, producao_propria=True))

	def test_saida_de_mercadoria_de_terceiros(self):
		self.assertEqual("5152", cfop_transferencia_saida(mesmo_estado=True, producao_propria=False))
		self.assertEqual("6152", cfop_transferencia_saida(mesmo_estado=False, producao_propria=False))

	def test_entrada_pelas_duas_finalidades(self):
		self.assertEqual("1151", cfop_transferencia_entrada(True, FINALIDADE_INDUSTRIALIZACAO))
		self.assertEqual("1152", cfop_transferencia_entrada(True, FINALIDADE_COMERCIALIZACAO))
		self.assertEqual("2151", cfop_transferencia_entrada(False, FINALIDADE_INDUSTRIALIZACAO))
		self.assertEqual("2152", cfop_transferencia_entrada(False, FINALIDADE_COMERCIALIZACAO))

	def test_entrada_recusa_finalidade_invalida(self):
		with self.assertRaises(CfopInvalido):
			cfop_transferencia_entrada(True, "qualquer coisa")

	def test_uso_e_consumo_tem_codigo_proprio(self):
		"""Material de uso e consumo não é mercadoria e não gera crédito; classificá-lo
		como `5152` daria a entender que gera."""
		self.assertEqual("5557", cfop_transferencia_uso_e_consumo(mesmo_estado=True))
		self.assertEqual("6557", cfop_transferencia_uso_e_consumo(mesmo_estado=False))
		self.assertEqual("1557", cfop_transferencia_uso_e_consumo(True, entrada=True))
		self.assertEqual("2557", cfop_transferencia_uso_e_consumo(False, entrada=True))

	def test_ativo_imobilizado_tem_codigo_proprio(self):
		"""O ativo tem crédito em 48 parcelas; uso e consumo não tem nenhum."""
		self.assertEqual("5552", cfop_transferencia_ativo_imobilizado(mesmo_estado=True))
		self.assertEqual("6552", cfop_transferencia_ativo_imobilizado(mesmo_estado=False))
		self.assertEqual("1552", cfop_transferencia_ativo_imobilizado(True, entrada=True))
		self.assertEqual("2552", cfop_transferencia_ativo_imobilizado(False, entrada=True))

	def test_transferencia_nao_colide_com_venda(self):
		"""`5101`/`5102` e `5151`/`5152` são operações diferentes: uma troca de titular, a
		outra não."""
		for producao_propria in (True, False):
			with self.subTest(producao_propria=producao_propria):
				self.assertNotEqual(
					cfop_venda(True, producao_propria),
					cfop_transferencia_saida(True, producao_propria),
				)


class TestCreditoDaTransferencia(unittest.TestCase):
	def test_credito_abaixo_do_limite_passa_inteiro(self):
		resultado = transferir_credito(
			valor_da_base=Decimal("1000.00"),
			aliquota_interestadual=Decimal("0.12"),
			credito_apropriado=Decimal("100.00"),
		)

		self.assertEqual(Decimal("100.00"), resultado.credito_transferido)
		self.assertEqual(Decimal("120.00"), resultado.limite)
		self.assertFalse(resultado.limitado)
		self.assertEqual(Decimal("0.00"), resultado.credito_retido_na_origem)

	def test_credito_acima_do_limite_e_cortado(self):
		"""E a diferença **fica no remetente** — quem vê só o transferido não sabe que
		sobrou crédito para trás."""
		resultado = transferir_credito(
			valor_da_base=Decimal("1000.00"),
			aliquota_interestadual=Decimal("0.07"),
			credito_apropriado=Decimal("180.00"),
		)

		self.assertEqual(Decimal("70.00"), resultado.credito_transferido)
		self.assertTrue(resultado.limitado)
		self.assertEqual(Decimal("110.00"), resultado.credito_retido_na_origem)

	def test_a_base_escolhida_fica_registrada(self):
		"""Duas transferências com limites diferentes não se explicam sozinhas depois."""
		resultado = transferir_credito(
			Decimal("500.00"), Decimal("0.12"), Decimal("10.00"), BASE_CUSTO_DE_PRODUCAO
		)

		self.assertEqual(BASE_CUSTO_DE_PRODUCAO, resultado.base_utilizada)

	def test_a_base_padrao_e_o_valor_medio_de_entrada(self):
		resultado = transferir_credito(Decimal("500.00"), Decimal("0.12"), Decimal("10.00"))

		self.assertEqual(BASE_VALOR_MEDIO_DE_ENTRADA, resultado.base_utilizada)

	def test_recusa_base_fora_da_clausula_quarta(self):
		with self.assertRaises(TransferenciaInvalida):
			transferir_credito(Decimal("500.00"), Decimal("0.12"), Decimal("10.00"), "chute")

	def test_a_equiparacao_recusa_transferir_credito(self):
		"""Quem optou pela cláusula sexta tributa a operação; devolver um número aqui daria
		ao optante uma segunda conta de ICMS, paralela à correta."""
		with self.assertRaises(TransferenciaInvalida):
			transferir_credito(Decimal("500.00"), Decimal("0.12"), Decimal("10.00"), equiparado=True)

	def test_recusa_aliquota_em_percentual(self):
		"""12 em vez de 0.12 daria um limite cem vezes maior."""
		with self.assertRaises(TransferenciaInvalida):
			transferir_credito(Decimal("500.00"), Decimal("12"), Decimal("10.00"))

	def test_recusa_base_nao_positiva(self):
		for base in (Decimal("0.00"), Decimal("-1.00")):
			with self.subTest(base=base), self.assertRaises(TransferenciaInvalida):
				transferir_credito(base, Decimal("0.12"), Decimal("10.00"))

	def test_recusa_credito_negativo(self):
		with self.assertRaises(TransferenciaInvalida):
			transferir_credito(Decimal("500.00"), Decimal("0.12"), Decimal("-1.00"))

	def test_recusa_float(self):
		"""Dinheiro é `Decimal` em todo o app."""
		with self.assertRaises(TransferenciaInvalida):
			transferir_credito(1000.0, Decimal("0.12"), Decimal("10.00"))

	def test_credito_zero_e_valido(self):
		"""Mercadoria que entrou sem crédito — Simples Nacional, isenta — transfere zero,
		e isso não é erro."""
		resultado = transferir_credito(Decimal("1000.00"), Decimal("0.12"), Decimal("0.00"))

		self.assertEqual(Decimal("0.00"), resultado.credito_transferido)
		self.assertFalse(resultado.limitado)

	def test_o_limite_usa_a_aliquota_do_modulo_de_aliquotas(self):
		"""Integração das duas peças: RO para SP são 12%, e o limite acompanha."""
		aliquota = aliquota_interestadual("RO", "SP")
		resultado = transferir_credito(Decimal("2000.00"), aliquota, Decimal("500.00"))

		self.assertEqual(Decimal("240.00"), resultado.limite)


class TestMesmoTitular(unittest.TestCase):
	"""A pergunta que separa transferência de venda."""

	MATRIZ = "11.222.333/0001-81"
	FILIAL = "11.222.333/0002-62"
	OUTRA_EMPRESA = "99.888.777/0001-00"

	def test_matriz_e_filial_sao_o_mesmo_titular(self):
		self.assertTrue(mesmo_titular(self.MATRIZ, self.FILIAL))

	def test_raizes_diferentes_nao_sao(self):
		"""Teste-âncora desta classe: duas empresas do mesmo **grupo econômico** vendem uma
		à outra com incidência normal. Tratar grupo como titular único deixaria de tributar
		uma operação tributável."""
		self.assertFalse(mesmo_titular(self.MATRIZ, self.OUTRA_EMPRESA))

	def test_ignora_a_mascara(self):
		self.assertTrue(mesmo_titular("11222333000181", self.FILIAL))

	def test_cnpj_ausente_degrada_para_venda(self):
		"""Sem os dois CNPJ não se pode **afirmar** que é transferência, e a resposta segura
		é a que mantém o imposto."""
		for par in ((None, self.FILIAL), (self.MATRIZ, None), ("", ""), ("123", self.FILIAL)):
			with self.subTest(par=par):
				self.assertFalse(mesmo_titular(*par))

	def test_a_raiz_tem_oito_caracteres(self):
		"""Doze faria dois estabelecimentos nunca serem do mesmo titular — a ordem do
		estabelecimento é exatamente o que os diferencia."""
		self.assertEqual(8, TAMANHO_DA_RAIZ)

	def test_aceita_cnpj_alfanumerico(self):
		"""`limpar` preserva letras; a raiz alfanumérica compara igual."""
		self.assertTrue(mesmo_titular("AB.222.333/0001-81", "AB222333000262"))
		self.assertFalse(mesmo_titular("AB.222.333/0001-81", "CD222333000262"))


class TestACosturaDoCfopDeTransferencia(unittest.TestCase):
	"""Sem a ligação, os módulos acima seriam mais um `perdas.py`: corretos e inalcançáveis."""

	def test_a_sugestao_usa_o_cfop_de_transferencia(self):
		self.assertIn("cfop_transferencia_saida", _COSTURA)
		self.assertIn("cfop_transferencia_entrada", _COSTURA)

	def test_a_sugestao_confere_o_mesmo_titular(self):
		"""`is_internal_customer` sozinho inclui grupo econômico — não basta."""
		self.assertIn("mesmo_titular", _COSTURA)

	def test_confere_os_dois_campos_do_erpnext(self):
		"""Nomes distintos para a mesma ideia, lidos nos JSON e não deduzidos um do outro."""
		self.assertIn("is_internal_customer", _COSTURA)
		self.assertIn("is_internal_supplier", _COSTURA)
		self.assertIn("represents_company", _COSTURA)

	def test_a_venda_continua_sendo_o_caminho_padrao(self):
		"""Degradação segura: sem prova de mesmo titular, a operação é venda."""
		self.assertIn("cfop_transferencia_saida if transferencia else cfop_venda", _COSTURA)
		self.assertIn("cfop_transferencia_entrada if transferencia else cfop_compra", _COSTURA)


if __name__ == "__main__":
	unittest.main()
