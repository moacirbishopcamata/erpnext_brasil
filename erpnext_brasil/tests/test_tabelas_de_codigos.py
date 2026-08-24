# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes das tabelas normativas de códigos fiscais.

São dados, não algoritmo — então o que se testa é a integridade estrutural: códigos
sem duplicata, sem espaço perdido, comprimentos coerentes com o leiaute da NF-e, e as
faixas que a norma define (CST de IPI separa entrada de saída; CSOSN começa por 1, 2,
3, 4, 5 ou 9). Um erro de digitação numa dessas listas vira rejeição da SEFAZ meses
depois, e é barato barrá-lo aqui.
"""

import unittest

from erpnext_brasil.fiscal.codigos.tabelas import (
	CSOSN,
	CST_ICMS,
	CST_IPI,
	CST_PIS_COFINS,
	ORIGEM_MERCADORIA,
	TABELAS,
	opcoes_select,
)


class TestIntegridadeDasTabelas(unittest.TestCase):
	def test_nenhuma_tabela_esta_vazia(self):
		for tabela in TABELAS:
			with self.subTest(tabela=tabela.nome):
				self.assertGreater(len(tabela.codigos), 0)

	def test_nomes_de_tabela_sao_unicos(self):
		nomes = [tabela.nome for tabela in TABELAS]
		self.assertEqual(len(nomes), len(set(nomes)))

	def test_codigos_e_titulos_sem_espaco_perdido(self):
		for tabela in TABELAS:
			for codigo, titulo in tabela.codigos.items():
				with self.subTest(tabela=tabela.nome, codigo=codigo):
					self.assertEqual(codigo, codigo.strip())
					self.assertEqual(titulo, titulo.strip())
					self.assertTrue(titulo, "título não pode ser vazio")

	def test_todo_codigo_e_numerico(self):
		for tabela in TABELAS:
			for codigo in tabela.codigos:
				with self.subTest(tabela=tabela.nome, codigo=codigo):
					self.assertTrue(codigo.isdigit())

	def test_metadados_preenchidos(self):
		for tabela in TABELAS:
			with self.subTest(tabela=tabela.nome):
				self.assertTrue(tabela.titulo)
				self.assertTrue(tabela.descricao)
				self.assertTrue(tabela.publicador)


class TestFaixasNormativas(unittest.TestCase):
	def test_origem_da_mercadoria_vai_de_0_a_8(self):
		self.assertEqual(set(ORIGEM_MERCADORIA.codigos), {str(n) for n in range(9)})

	def test_cst_icms_tem_dois_digitos(self):
		for codigo in CST_ICMS.codigos:
			with self.subTest(codigo=codigo):
				self.assertEqual(len(codigo), 2)

	def test_csosn_tem_tres_digitos_e_prefixo_valido(self):
		for codigo in CSOSN.codigos:
			with self.subTest(codigo=codigo):
				self.assertEqual(len(codigo), 3)
				self.assertIn(codigo[0], "123459")

	def test_cst_ipi_separa_entrada_de_saida(self):
		# A norma reserva 00-49 para entrada e 50-99 para saída; a descrição precisa
		# acompanhar a faixa, senão o usuário escolhe o código certo com o rótulo errado.
		#
		# Compara-se o radical, não o começo da frase: "Outras entradas" e "Outras
		# saídas" são rótulos corretos que não começam pelo lado da operação.
		for codigo, titulo in CST_IPI.codigos.items():
			with self.subTest(codigo=codigo):
				entrada = int(codigo) < 50
				radical, oposto = ("ntrada", "aída") if entrada else ("aída", "ntrada")

				self.assertIn(
					radical,
					titulo,
					f"CST IPI {codigo} está na faixa de {'entrada' if entrada else 'saída'} "
					f"mas o título diz '{titulo}'",
				)
				self.assertNotIn(oposto, titulo, f"CST IPI {codigo}: título mistura entrada e saída")

	def test_cst_pis_cofins_tem_dois_digitos(self):
		for codigo in CST_PIS_COFINS.codigos:
			with self.subTest(codigo=codigo):
				self.assertEqual(len(codigo), 2)

	def test_cst_pis_cofins_cobre_as_familias_da_efd(self):
		# Saída (0x/49), crédito (5x), crédito presumido (6x), aquisição (7x) e outras.
		prefixos = {codigo[0] for codigo in CST_PIS_COFINS.codigos}
		self.assertTrue({"0", "4", "5", "6", "7", "9"}.issubset(prefixos))


class TestOpcoesSelect(unittest.TestCase):
	def test_primeira_opcao_e_vazia(self):
		linhas = opcoes_select(CST_ICMS).split("\n")
		self.assertEqual(linhas[0], "")

	def test_uma_linha_por_codigo(self):
		linhas = opcoes_select(CST_ICMS).split("\n")
		self.assertEqual(len(linhas), len(CST_ICMS.codigos) + 1)

	def test_formato_codigo_espaco_traco_espaco_titulo(self):
		linhas = opcoes_select(CSOSN).split("\n")[1:]

		for linha, (codigo, titulo) in zip(linhas, CSOSN.codigos.items(), strict=True):
			with self.subTest(codigo=codigo):
				self.assertEqual(linha, f"{codigo} - {titulo}")

	def test_campo_do_item_usa_a_tabela_normativa(self):
		"""O Select de origem e o Code List precisam sair da mesma fonte."""
		from erpnext_brasil.setup.custom_fields import ORIGENS_MERCADORIA

		self.assertEqual(ORIGENS_MERCADORIA, opcoes_select(ORIGEM_MERCADORIA))


if __name__ == "__main__":
	unittest.main()
