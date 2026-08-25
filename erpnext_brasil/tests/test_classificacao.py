# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes do leitor de XLSX e da Tabela de Classificação Tributária do IBS/CBS.

O XLSX de teste é montado aqui mesmo, com `zipfile` — não há arquivo binário no
repositório. Assim o teste roda em qualquer lugar, documenta o formato que o leitor
espera, e não depende de baixar 157 KB do Portal da NF-e a cada execução.
"""

import io
import unittest
import zipfile

from erpnext_brasil.fiscal.codigos.classificacao import (
	formato_valido_cclasstrib,
	formato_valido_cst,
	ler_cclasstrib,
	ler_cst,
)
from erpnext_brasil.fiscal.codigos.xlsx import ler_planilha, listar_planilhas

_NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'


def _montar_xlsx(planilhas: dict[str, list[list[str]]]) -> io.BytesIO:
	"""Gera um XLSX mínimo com texto embutido (`inlineStr`), sem shared strings."""
	buffer = io.BytesIO()

	with zipfile.ZipFile(buffer, "w") as z:
		for indice, (_, linhas) in enumerate(planilhas.items(), start=1):
			corpo = []

			for numero, linha in enumerate(linhas, start=1):
				celulas = []

				for coluna, texto in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", linha, strict=False):
					seguro = texto.replace("&", "&amp;").replace("<", "&lt;")
					celulas.append(
						f'<c r="{coluna}{numero}" t="inlineStr"><is><t>{seguro}</t></is></c>'
					)

				corpo.append(f'<row r="{numero}">{"".join(celulas)}</row>')

			z.writestr(
				f"xl/worksheets/sheet{indice}.xml",
				f'<worksheet {_NS}><sheetData>{"".join(corpo)}</sheetData></worksheet>',
			)

	buffer.seek(0)

	return buffer


CABECALHO_CST = ["CST-IBS/CBS", "Descrição CST-IBS/CBS", "ind_gIBSCBS", "ind_gRed", "ind_gDif"]
CABECALHO_CCLASS = [
	"CST-IBS/CBS",
	"Descrição CST-IBS/CBS",
	"cClassTrib",
	"Nome cClassTrib",
	"Descrição cClassTrib",
	"Tipo de Alíquota",
	"pRedIBS",
	"pRedCBS",
	"indNFe",
	"indNFCe",
]


class TestLeitorXlsx(unittest.TestCase):
	def test_le_linhas_e_colunas(self):
		arquivo = _montar_xlsx({"cst": [["A", "B"], ["1", "2"]]})
		linhas = ler_planilha(arquivo)

		self.assertEqual(linhas, [{"A": "A", "B": "B"}, {"A": "1", "B": "2"}])

	def test_descarta_linha_totalmente_vazia(self):
		arquivo = _montar_xlsx({"cst": [["A"], [""], ["B"]]})

		self.assertEqual(ler_planilha(arquivo), [{"A": "A"}, {"A": "B"}])

	def test_lista_planilhas(self):
		arquivo = _montar_xlsx({"um": [["x"]], "dois": [["y"]]})

		self.assertEqual(len(listar_planilhas(arquivo)), 2)


class TestFormatos(unittest.TestCase):
	"""Formatos fixados pelo XSD: TCST = 3 dígitos, TcClassTrib = 6."""

	def test_cst_valido(self):
		for codigo in ("000", "010", "200", "999"):
			with self.subTest(codigo=codigo):
				self.assertTrue(formato_valido_cst(codigo))

	def test_cst_invalido(self):
		# O caso "0" e "00" é o zero à esquerda perdido numa planilha.
		for codigo in ("", None, "0", "00", "0000", "00A", "abc"):
			with self.subTest(codigo=codigo):
				self.assertFalse(formato_valido_cst(codigo))

	def test_cclasstrib_valido(self):
		self.assertTrue(formato_valido_cclasstrib("000001"))

	def test_cclasstrib_invalido(self):
		for codigo in ("", None, "1", "00001", "0000001", "00000A"):
			with self.subTest(codigo=codigo):
				self.assertFalse(formato_valido_cclasstrib(codigo))


class TestLeituraDaTabelaCst(unittest.TestCase):
	def setUp(self):
		self.arquivo = _montar_xlsx(
			{
				"cst": [
					CABECALHO_CST,
					["000", "Tributação integral", "1", "0", "0"],
					["011", "Alíquotas uniformes reduzidas", "1", "1", "0"],
					["", "Legenda:", "", "", ""],
					["", "0 = Não é permitido", "", "", ""],
				]
			}
		)

	def test_le_apenas_linhas_com_codigo_valido(self):
		"""A legenda no fim da planilha oficial não pode virar código."""
		registros = ler_cst(ler_planilha(self.arquivo))

		self.assertEqual([r.codigo for r in registros], ["000", "011"])

	def test_indicadores(self):
		registros = {r.codigo: r for r in ler_cst(ler_planilha(self.arquivo))}

		self.assertTrue(registros["011"].exige("ind_gRed"))
		self.assertFalse(registros["000"].exige("ind_gRed"))

	def test_nao_exigir_significa_proibir(self):
		"""Legenda oficial: 0 = não é permitido. Não existe estado opcional."""
		registros = {r.codigo: r for r in ler_cst(ler_planilha(self.arquivo))}

		self.assertTrue(registros["000"].proibe("ind_gRed"))
		self.assertFalse(registros["011"].proibe("ind_gRed"))

	def test_planilha_errada_e_erro_explicito(self):
		outra = _montar_xlsx({"x": [["Coluna"], ["valor"]]})

		with self.assertRaises(ValueError) as ctx:
			ler_cst(ler_planilha(outra))

		self.assertIn("CST", str(ctx.exception))


class TestLeituraDeCClassTrib(unittest.TestCase):
	def setUp(self):
		self.arquivo = _montar_xlsx(
			{
				"cc": [
					CABECALHO_CCLASS,
					["000", "Tributação integral", "000001", "Integral", "Desc", "Padrão", "0", "0", "1", "1"],
					["000", "Tributação integral", "000002", "Exploração de via", "Desc", "Padrão", "0", "0", "0", "0"],
					["200", "Alíquota reduzida", "200001", "Reduzida", "Desc", "Reduzida", "60", "60", "1", "0"],
				]
			}
		)
		self.registros = {r.codigo: r for r in ler_cclasstrib(ler_planilha(self.arquivo))}

	def test_le_todos_os_codigos(self):
		self.assertEqual(sorted(self.registros), ["000001", "000002", "200001"])

	def test_amarra_ao_cst(self):
		self.assertEqual(self.registros["200001"].cst, "200")

	def test_aplicabilidade_por_documento(self):
		self.assertTrue(self.registros["000001"].vale_para("indNFe"))
		self.assertFalse(self.registros["000002"].vale_para("indNFe"))
		self.assertFalse(self.registros["200001"].vale_para("indNFCe"))

	def test_percentual_de_reducao(self):
		self.assertEqual(self.registros["200001"].reducao_ibs, "60")
		self.assertEqual(self.registros["000001"].reducao_ibs, "0")

	def test_leitura_por_titulo_e_nao_por_posicao(self):
		"""Coluna nova no meio não pode deslocar a leitura.

		A Receita acrescenta colunas entre versões da tabela; ler pela posição faria a
		importação seguinte pegar o campo errado sem falhar.
		"""
		com_coluna_extra = _montar_xlsx(
			{
				"cc": [
					["CST-IBS/CBS", "NOVA COLUNA", "Descrição CST-IBS/CBS", "cClassTrib", "Nome cClassTrib"],
					["000", "ignorar", "Tributação integral", "000001", "Integral"],
				]
			}
		)

		registros = ler_cclasstrib(ler_planilha(com_coluna_extra))

		self.assertEqual(registros[0].codigo, "000001")
		self.assertEqual(registros[0].nome, "Integral")


if __name__ == "__main__":
	unittest.main()
