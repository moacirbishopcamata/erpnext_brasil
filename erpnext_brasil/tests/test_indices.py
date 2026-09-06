# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Os índices que as consultas deste app precisam.

Índice ausente não quebra nada: a consulta devolve o resultado certo, e devagar. O custo só
aparece meses depois, quando a tabela cresceu — e aí ninguém associa a lentidão à consulta.
É o oposto de um erro alto, e por isso precisa de teste.

Teste-âncora: `test_a_consulta_mais_quente_tem_indice`. O painel de situação fiscal filtra
`Transmissao Fiscal` por `(documento_tipo, documento)` a **cada `refresh` de formulário**.

Módulo de leitura: roda sem bench.
"""

import ast
import json
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

_INSTALL = (RAIZ / "setup" / "install.py").read_text(encoding="utf-8")
_ARVORE = ast.parse(_INSTALL)


def _indices() -> dict:
	for no in _ARVORE.body:
		if isinstance(no, ast.Assign) and any(
			isinstance(alvo, ast.Name) and alvo.id == "INDICES" for alvo in no.targets
		):
			return ast.literal_eval(no.value)

	raise AssertionError("INDICES não encontrado em install.py")


def _campos(doctype: str) -> set[str]:
	pasta = doctype.lower().replace(" ", "_")
	caminho = RAIZ / "registros_fiscais" / "doctype" / pasta / f"{pasta}.json"

	return {c["fieldname"] for c in json.loads(caminho.read_text(encoding="utf-8"))["fields"]}


class TestOsIndicesDeclarados(unittest.TestCase):
	def test_a_consulta_mais_quente_tem_indice(self):
		"""Teste-âncora: o painel roda esta consulta a cada abertura de formulário."""
		self.assertIn(["documento_tipo", "documento"], _indices()["Transmissao Fiscal"])

	def test_todo_campo_indexado_existe_no_doctype(self):
		"""Índice sobre campo inexistente falha na migração — e a migração é onde menos se
		quer descobrir um nome errado."""
		for doctype, listas in _indices().items():
			declarados = _campos(doctype)

			for campos in listas:
				for campo in campos:
					with self.subTest(doctype=doctype, campo=campo):
						self.assertIn(campo, declarados)

	def test_o_indice_e_composto_e_nao_dois_simples(self):
		"""O banco usa um índice composto inteiro onde usaria só o primeiro de dois
		separados. Declarar dois simples pareceria equivalente e não seria."""
		listas = _indices()["Transmissao Fiscal"]

		self.assertTrue(any(len(campos) > 1 for campos in listas))


class TestOQueNaoSeIndexa(unittest.TestCase):
	def test_numeracao_fiscal_nao_tem_indice(self):
		"""A alocação de número busca **pelo `name`**, e o `autoname` daquele DocType é
		`format:{company}-{modelo}-{serie}` — a chave primária já é a combinação. Um índice
		sobre os três campos duplicaria a chave, custando escrita sem ganhar leitura.

		A primeira redação de `docs/consultas-ao-banco.md` listava esse índice como gap; era
		erro de leitura, e este teste existe para que não volte.
		"""
		self.assertNotIn("Numeracao Fiscal", _indices())

	def test_o_autoname_da_numeracao_continua_sendo_a_combinacao(self):
		"""O teste acima só vale enquanto isto for verdade — se o `autoname` mudar, o
		índice passa a fazer falta."""
		caminho = RAIZ / "registros_fiscais" / "doctype" / "numeracao_fiscal" / "numeracao_fiscal.json"
		definicao = json.loads(caminho.read_text(encoding="utf-8"))

		self.assertEqual("format:{company}-{modelo}-{serie}", definicao["autoname"])


class TestAInstalacao(unittest.TestCase):
	def test_os_indices_sao_criados_no_install_e_no_migrate(self):
		"""Só no `after_install` deixaria de fora todo site já existente — e é justamente
		o site com dados que precisa do índice."""
		chamadas = [linha.strip() for linha in _INSTALL.splitlines() if linha.strip() == "criar_indices()"]

		self.assertEqual(2, len(chamadas))

	def test_a_criacao_confere_a_existencia_do_doctype(self):
		"""Um site sem o DocType (app parcialmente instalado) não deve quebrar a migração."""
		fonte = next(
			ast.get_source_segment(_INSTALL, no)
			for no in ast.walk(_ARVORE)
			if isinstance(no, ast.FunctionDef) and no.name == "criar_indices"
		)

		self.assertIn("frappe.db.exists", fonte)

	def test_usa_add_index_que_e_idempotente(self):
		"""`frappe.db.add_index` confere `has_index` antes de criar — rodar a cada
		`migrate` é barato e devolve o índice se uma migração o tiver removido."""
		fonte = next(
			ast.get_source_segment(_INSTALL, no)
			for no in ast.walk(_ARVORE)
			if isinstance(no, ast.FunctionDef) and no.name == "criar_indices"
		)

		self.assertIn("frappe.db.add_index", fonte)


if __name__ == "__main__":
	unittest.main()
