# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da compatibilidade entre CST, cClassTrib e os grupos do XML.

Dois comportamentos aqui são deliberados e fáceis de desfazer sem perceber numa
refatoração, então cada um tem teste próprio: tabela vazia **não** acusa erro (não dá
para afirmar invalidez sem a tabela), e informar grupo a mais é erro tanto quanto omitir
um obrigatório — a legenda oficial é binária, sem estado opcional.
"""

import unittest

from erpnext_brasil.fiscal.codigos.classificacao import ClassificacaoTributaria, CstIbsCbs
from erpnext_brasil.fiscal.codigos.compatibilidade import (
	validar_classificacao,
	validar_grupos_informados,
)

TABELA_CST = {
	"000": CstIbsCbs(
		codigo="000",
		descricao="Tributação integral",
		indicadores={"ind_gIBSCBS": "1", "ind_gRed": "0", "ind_gDif": "0"},
	),
	"200": CstIbsCbs(
		codigo="200",
		descricao="Alíquota reduzida",
		indicadores={"ind_gIBSCBS": "1", "ind_gRed": "1", "ind_gDif": "0"},
	),
}

TABELA_CCLASS = {
	"000001": ClassificacaoTributaria(
		codigo="000001",
		cst="000",
		nome="Tributação integral",
		descricao="",
		documentos={"indNFe": "1", "indNFCe": "1", "indNFSe": "0"},
	),
	"000002": ClassificacaoTributaria(
		codigo="000002",
		cst="000",
		nome="Exploração de via",
		descricao="",
		documentos={"indNFe": "0", "indNFCe": "0", "indNFSe": "1"},
	),
	"200001": ClassificacaoTributaria(
		codigo="200001",
		cst="200",
		nome="Alíquota reduzida",
		descricao="",
		documentos={"indNFe": "1", "indNFCe": "0"},
	),
}


def validar(cst, cclass, documento="indNFe"):
	return validar_classificacao(cst, cclass, TABELA_CST, TABELA_CCLASS, documento)


class TestCombinacaoValida(unittest.TestCase):
	def test_par_correto_nao_acusa(self):
		self.assertEqual(validar("000", "000001"), [])

	def test_outro_par_correto(self):
		self.assertEqual(validar("200", "200001"), [])


class TestFormato(unittest.TestCase):
	def test_cst_com_zero_perdido(self):
		problemas = validar("0", "000001")

		self.assertEqual(problemas[0].campo, "cst")
		self.assertIn("planilha", problemas[0].mensagem)

	def test_cclasstrib_curto(self):
		self.assertEqual(validar("000", "1")[0].campo, "cclasstrib")

	def test_formato_invalido_interrompe_antes_de_consultar_a_tabela(self):
		"""Sem formato válido não faz sentido reportar "não consta na tabela"."""
		problemas = validar("00", "12345")

		self.assertEqual(len(problemas), 2)
		self.assertTrue(all("consta" not in p.mensagem for p in problemas))


class TestAmarracaoEntreOsCampos(unittest.TestCase):
	def test_cclasstrib_de_outro_cst_e_erro(self):
		problemas = validar("200", "000001")

		self.assertEqual(len(problemas), 1)
		self.assertIn("pertence ao CST 000", problemas[0].mensagem)

	def test_cst_desconhecido(self):
		problemas = validar("999", "000001")

		self.assertTrue(any(p.campo == "cst" for p in problemas))

	def test_cclasstrib_desconhecido_orienta_a_importar(self):
		problemas = validar("000", "999999")

		self.assertIn("Importe a versão vigente", problemas[0].mensagem)


class TestAplicabilidadePorDocumento(unittest.TestCase):
	def test_codigo_de_nfse_recusado_em_nfe(self):
		problemas = validar("000", "000002")

		self.assertTrue(any("não é aceito em indNFe" in p.mensagem for p in problemas))

	def test_mensagem_diz_onde_o_codigo_vale(self):
		problemas = validar("000", "000002")

		self.assertIn("indNFSe", problemas[0].mensagem)

	def test_mesmo_codigo_aceito_no_documento_certo(self):
		self.assertEqual(validar("000", "000002", documento="indNFSe"), [])

	def test_codigo_valido_para_nfe_recusado_em_nfce(self):
		problemas = validar("200", "200001", documento="indNFCe")

		self.assertTrue(any("não é aceito" in p.mensagem for p in problemas))


class TestTabelaAusente(unittest.TestCase):
	"""Sem a tabela importada não se pode afirmar que a combinação é inválida."""

	def test_tabelas_vazias_nao_acusam(self):
		self.assertEqual(validar_classificacao("000", "000001", {}, {}), [])

	def test_formato_ainda_e_verificado_sem_tabela(self):
		problemas = validar_classificacao("0", "1", {}, {})

		self.assertEqual(len(problemas), 2)


class TestGruposDoXml(unittest.TestCase):
	def test_grupo_exigido_presente(self):
		self.assertEqual(validar_grupos_informados("000", {"gIBSCBS"}, TABELA_CST), [])

	def test_grupo_exigido_ausente(self):
		problemas = validar_grupos_informados("000", set(), TABELA_CST)

		self.assertIn("exige o grupo gIBSCBS", problemas[0].mensagem)

	def test_grupo_vedado_informado_tambem_e_erro(self):
		"""Legenda oficial: 0 = não é permitido. Informar a mais é rejeição."""
		problemas = validar_grupos_informados("000", {"gIBSCBS", "gRed"}, TABELA_CST)

		self.assertEqual(len(problemas), 1)
		self.assertIn("não permite o grupo gRed", problemas[0].mensagem)

	def test_reducao_exigida_no_cst_200(self):
		problemas = validar_grupos_informados("200", {"gIBSCBS"}, TABELA_CST)

		self.assertIn("exige o grupo gRed", problemas[0].mensagem)

	def test_cst_desconhecido_nao_acusa_grupos(self):
		self.assertEqual(validar_grupos_informados("999", set(), TABELA_CST), [])

	def test_acusa_todos_os_problemas_de_uma_vez(self):
		problemas = validar_grupos_informados("200", {"gDif"}, TABELA_CST)
		mensagens = " ".join(p.mensagem for p in problemas)

		self.assertIn("gIBSCBS", mensagens)
		self.assertIn("gRed", mensagens)
		self.assertIn("gDif", mensagens)


class TestContraATabelaOficial(unittest.TestCase):
	"""Sanidade contra a estrutura real, se o arquivo oficial estiver disponível.

	O teste não baixa nada e é pulado quando o arquivo não está presente — a suíte
	precisa rodar offline.
	"""

	def test_pares_reais_sao_coerentes(self):
		import pathlib

		arquivo = pathlib.Path(
			"C:/Users/ninte/.claude/jobs/3566b866/tmp/classtrib.bin"
		)

		if not arquivo.exists():
			self.skipTest("tabela oficial não disponível neste ambiente")

		from erpnext_brasil.fiscal.codigos.classificacao import ler_cclasstrib, ler_cst
		from erpnext_brasil.fiscal.codigos.xlsx import ler_planilha

		cst = {r.codigo: r for r in ler_cst(ler_planilha(arquivo, "xl/worksheets/sheet1.xml"))}
		cclass = {
			r.codigo: r for r in ler_cclasstrib(ler_planilha(arquivo, "xl/worksheets/sheet2.xml"))
		}

		# Todo cClassTrib aplicável a NF-e deve passar quando informado com o seu
		# próprio CST — se não passar, a validação está rejeitando combinação legítima.
		for registro in cclass.values():
			if not registro.vale_para("indNFe"):
				continue

			with self.subTest(cclasstrib=registro.codigo):
				self.assertEqual(
					validar_classificacao(registro.cst, registro.codigo, cst, cclass), []
				)


if __name__ == "__main__":
	unittest.main()
