# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Costura da importação do XML da NF-e de entrada.

`integracao/entrada_nfe.py` importa `frappe`, então a execução só existe num site. O que se
confere aqui é o que sumiria em silêncio: campo gravado e não declarado, ordem entre
conferir e gravar, e a fronteira que o módulo se impôs — não criar item nenhum.

Teste-âncora: `test_o_destinatario_e_conferido_antes_de_gravar`. Gravar primeiro e conferir
depois deixaria a chave de outra empresa no documento mesmo com o erro levantado, porque
`db_set` escreve na hora.
"""

import ast
import unittest
from pathlib import Path

from erpnext_brasil.setup.custom_fields import get_custom_fields

RAIZ = Path(__file__).resolve().parent.parent

_FONTE = (RAIZ / "integracao" / "entrada_nfe.py").read_text(encoding="utf-8")
_ARVORE = ast.parse(_FONTE)


def _funcao(nome: str) -> ast.FunctionDef:
	for no in ast.walk(_ARVORE):
		if isinstance(no, ast.FunctionDef) and no.name == nome:
			return no

	raise AssertionError(f"{nome} não existe em entrada_nfe.py")


def _campos_preenchidos() -> dict[str, str]:
	"""`CAMPOS_PREENCHIDOS`, lido por AST — o módulo importa `frappe`."""
	for no in ast.walk(_ARVORE):
		if isinstance(no, ast.Assign) and any(
			isinstance(alvo, ast.Name) and alvo.id == "CAMPOS_PREENCHIDOS" for alvo in no.targets
		):
			return {
				chave.value: valor.value
				for chave, valor in zip(no.value.keys, no.value.values, strict=True)
				if isinstance(chave, ast.Constant) and isinstance(valor, ast.Constant)
			}

	raise AssertionError("CAMPOS_PREENCHIDOS não encontrado")


def _linhas(funcao: ast.FunctionDef, alvo: str) -> list[int]:
	achadas = []

	for no in ast.walk(funcao):
		if isinstance(no, ast.Call):
			chamado = no.func
			nome = chamado.id if isinstance(chamado, ast.Name) else getattr(chamado, "attr", "")

			if nome == alvo:
				achadas.append(no.lineno)

	return sorted(achadas)


class TestCamposGravados(unittest.TestCase):
	"""Campo não declarado some no save, sem erro — a família dos 31 de `docs/gaps.md`."""

	def test_todo_campo_preenchido_esta_declarado_no_purchase_invoice(self):
		declarados = {c["fieldname"] for c in get_custom_fields()["Purchase Invoice"]}
		preenchidos = set(_campos_preenchidos())

		self.assertTrue(preenchidos, "nenhum campo lido — o teste ficaria vazio")
		self.assertEqual(set(), preenchidos - declarados)

	def test_todo_atributo_lido_existe_na_nota(self):
		"""Um nome errado aqui gravaria `None` sem levantar nada."""
		from erpnext_brasil.fiscal.documento.leitura_nfe import NotaLida

		nota = NotaLida(chave_acesso="")

		for atributo in _campos_preenchidos().values():
			with self.subTest(atributo=atributo):
				self.assertTrue(hasattr(nota, atributo))


class TestOrdemDosEfeitos(unittest.TestCase):
	def test_o_destinatario_e_conferido_antes_de_gravar(self):
		"""Teste-âncora: `db_set` escreve na hora. Gravar primeiro deixaria a chave de
		outra empresa no documento mesmo com o erro levantado depois."""
		funcao = _funcao("importar_nfe")

		self.assertLess(
			_linhas(funcao, "_conferir_destinatario")[0],
			_linhas(funcao, "db_set")[0],
		)

	def test_a_permissao_e_conferida_antes_de_qualquer_leitura(self):
		funcao = _funcao("importar_nfe")

		self.assertLess(_linhas(funcao, "check_permission")[0], _linhas(funcao, "ler_nfe")[0])


class TestFronteira(unittest.TestCase):
	"""O módulo se proíbe de adivinhar — e o teste trava a proibição."""

	def test_nao_cria_nem_altera_itens(self):
		"""O `cProd` da nota é o código **do fornecedor**. Casá-lo por descrição ou EAN
		daria entrada no item errado, contaminando custo médio, saldo e escrituração."""
		for proibido in ("doc.append(", '"Item"', "insert("):
			with self.subTest(proibido=proibido):
				self.assertNotIn(proibido, _corpo_executavel())

	def test_nao_grava_valor_nem_imposto(self):
		"""Valor vem do que foi negociado, não do que o fornecedor declarou; divergência
		é para ser vista, não absorvida."""
		gravados = set(_campos_preenchidos())

		for campo in ("br_valor_icms", "br_aliquota_icms", "grand_total"):
			with self.subTest(campo=campo):
				self.assertNotIn(campo, gravados)

	def test_a_divergencia_e_relatada_e_nao_corrigida(self):
		funcao = _funcao("_divergencias")
		nomes = {no.attr for no in ast.walk(funcao) if isinstance(no, ast.Attribute)}

		self.assertNotIn("db_set", nomes)


class TestOHelperDeAusencia(unittest.TestCase):
	"""As asserções de ausência valem o que `_corpo_executavel` valer.

	Se ele parar de remover docstrings, todo teste de "não faz X" passa a medir a prosa que
	explica por que não se faz X — e vira vácuo verde. Já aconteceu duas vezes neste
	projeto; aqui a ferramenta tem teste próprio.
	"""

	def test_remove_o_texto_que_so_existe_em_docstring(self):
		corpo = _corpo_executavel()

		self.assertNotIn("Deliberado", corpo)
		self.assertNotIn("custo médio", corpo)

	def test_preserva_o_codigo_e_as_mensagens_ao_usuario(self):
		"""Mensagem de `_()` não é docstring: ela precisa continuar visível."""
		corpo = _corpo_executavel()

		self.assertIn("db_set", corpo)
		self.assertIn("crédito indevido", corpo)


class TestSuperficieExposta(unittest.TestCase):
	def test_importar_nfe_e_whitelisted(self):
		decoradores = _funcao("importar_nfe").decorator_list
		alvos = [d.func if isinstance(d, ast.Call) else d for d in decoradores]

		self.assertTrue(any(getattr(a, "attr", "") == "whitelist" for a in alvos))

	def test_a_comparacao_de_cnpj_e_por_digitos(self):
		"""`12.345.678/0001-99` e `12345678000199` são o mesmo CNPJ, e o `tax_id` da
		`Company` costuma vir formatado."""
		self.assertIn("_digitos", _corpo_executavel())


def _corpo_executavel() -> str:
	"""O fonte sem docstrings, para asserções de ausência.

	Sem isto, a docstring que explica por que **não** se cria item reprovaria o próprio
	teste que a defende — armadilha já vivida em `test_costura_cliente`.
	"""
	sem_docstring = []

	for no in ast.walk(_ARVORE):
		if (
			isinstance(no, ast.Expr)
			and isinstance(no.value, ast.Constant)
			and isinstance(no.value.value, str)
		):
			sem_docstring.append((no.lineno, no.end_lineno))

	proibidas = {linha for inicio, fim in sem_docstring for linha in range(inicio, fim + 1)}

	return "\n".join(
		texto for numero, texto in enumerate(_FONTE.splitlines(), start=1) if numero not in proibidas
	)


if __name__ == "__main__":
	unittest.main()
