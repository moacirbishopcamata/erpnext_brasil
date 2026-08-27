# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da inversão de dependência entre a regra e a fonte das tabelas.

O ganho concreto da refatoração está aqui: `problemas_dos_itens` orquestra a validação
de um documento inteiro e é testável **sem bench**, porque recebe o repositório em vez de
buscá-lo. Antes, essa lógica só rodava com site e banco.
"""

import unittest

from erpnext_brasil.fiscal.codigos.classificacao import ClassificacaoTributaria, CstIbsCbs
from erpnext_brasil.fiscal.codigos.compatibilidade import validar_com_repositorio
from erpnext_brasil.fiscal.codigos.repositorio import (
	RepositorioClassificacao,
	RepositorioEmMemoria,
)

CST = {
	"000": CstIbsCbs(codigo="000", descricao="Tributação integral", indicadores={"ind_gIBSCBS": "1"}),
	"200": CstIbsCbs(codigo="200", descricao="Alíquota reduzida", indicadores={"ind_gRed": "1"}),
}

CCLASS = {
	"000001": ClassificacaoTributaria(
		codigo="000001",
		cst="000",
		nome="Integral",
		descricao="",
		documentos={"indNFe": "1", "indNFCe": "1"},
	),
	"200001": ClassificacaoTributaria(
		codigo="200001",
		cst="200",
		nome="Reduzida",
		descricao="",
		documentos={"indNFe": "1", "indNFCe": "0"},
	),
}


def repositorio() -> RepositorioEmMemoria:
	return RepositorioEmMemoria(cst=CST, classificacoes=CCLASS)


class TestContratoDoRepositorio(unittest.TestCase):
	def test_implementacao_satisfaz_a_interface(self):
		self.assertIsInstance(repositorio(), RepositorioClassificacao)

	def test_vazio_tambem_satisfaz(self):
		self.assertIsInstance(RepositorioEmMemoria(), RepositorioClassificacao)

	def test_leitura_devolve_copia_e_nao_referencia(self):
		"""Quem lê não pode alterar o estado interno do repositório."""
		repo = repositorio()
		obtido = repo.cst()
		obtido.pop("000")

		self.assertIn("000", repo.cst())

	def test_construtor_copia_o_que_recebe(self):
		origem = dict(CST)
		repo = RepositorioEmMemoria(cst=origem)
		origem.clear()

		self.assertEqual(len(repo.cst()), 2)


class TestValidacaoPelaInterface(unittest.TestCase):
	def test_par_valido(self):
		self.assertEqual(validar_com_repositorio("000", "000001", repositorio()), [])

	def test_par_invalido(self):
		problemas = validar_com_repositorio("200", "000001", repositorio())

		self.assertTrue(any("pertence ao CST 000" in p.mensagem for p in problemas))

	def test_repositorio_vazio_nao_acusa(self):
		self.assertEqual(validar_com_repositorio("000", "000001", RepositorioEmMemoria()), [])

	def test_documento_diferente_muda_o_resultado(self):
		self.assertEqual(validar_com_repositorio("200", "200001", repositorio(), "indNFe"), [])
		self.assertTrue(validar_com_repositorio("200", "200001", repositorio(), "indNFCe"))


class TestOrquestracaoDosItens(unittest.TestCase):
	"""Roda a validação de um documento inteiro, sem bench."""

	def setUp(self):
		from erpnext_brasil.fiscal.codigos.compatibilidade import problemas_dos_itens

		self.validar = problemas_dos_itens

	def test_documento_todo_correto(self):
		itens = [
			{"idx": 1, "br_cst_ibs_cbs": "000", "br_cclasstrib": "000001"},
			{"idx": 2, "br_cst_ibs_cbs": "200", "br_cclasstrib": "200001"},
		]

		self.assertEqual(self.validar(itens, repositorio(), "indNFe"), [])

	def test_mensagem_aponta_o_item(self):
		itens = [
			{"idx": 1, "br_cst_ibs_cbs": "000", "br_cclasstrib": "000001"},
			{"idx": 2, "br_cst_ibs_cbs": "200", "br_cclasstrib": "000001"},
		]

		mensagens = self.validar(itens, repositorio(), "indNFe")

		self.assertEqual(len(mensagens), 1)
		self.assertTrue(mensagens[0].startswith("Item 2:"))

	def test_item_sem_classificacao_e_ignorado(self):
		"""Rascunho precisa poder ser salvo antes de o fiscal ser preenchido."""
		itens = [{"idx": 1, "br_cst_ibs_cbs": "", "br_cclasstrib": ""}]

		self.assertEqual(self.validar(itens, repositorio(), "indNFe"), [])

	def test_classificacao_pela_metade_e_acusada(self):
		"""Preencher só um dos dois campos é erro — eles andam juntos."""
		itens = [{"idx": 1, "br_cst_ibs_cbs": "000", "br_cclasstrib": ""}]

		self.assertTrue(self.validar(itens, repositorio(), "indNFe"))

	def test_pos_invoice_valida_contra_nfce(self):
		itens = [{"idx": 1, "br_cst_ibs_cbs": "200", "br_cclasstrib": "200001"}]

		self.assertEqual(self.validar(itens, repositorio(), "indNFe"), [])
		self.assertTrue(self.validar(itens, repositorio(), "indNFCe"))

	def test_sem_idx_usa_a_posicao(self):
		itens = [{"br_cst_ibs_cbs": "200", "br_cclasstrib": "000001"}]

		self.assertTrue(self.validar(itens, repositorio(), "indNFe")[0].startswith("Item 1:"))

	def test_varios_itens_com_problema_reportam_todos(self):
		itens = [
			{"idx": 1, "br_cst_ibs_cbs": "200", "br_cclasstrib": "000001"},
			{"idx": 2, "br_cst_ibs_cbs": "000", "br_cclasstrib": "999999"},
		]

		self.assertEqual(len(self.validar(itens, repositorio(), "indNFe")), 2)


if __name__ == "__main__":
	unittest.main()
