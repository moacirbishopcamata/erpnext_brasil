# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""`frappe.throw` desfaz a transação: o `Transmissao Fiscal` da rejeição precisa de `commit` antes.

`emissao_nfe` e `emissao_cte` importam `frappe`, então a suíte pura não os executa; o que se trava
aqui, lendo o fonte, é a ordem — `frappe.db.commit()` antes do `frappe.throw` que recusa a
resposta da SEFAZ. A prova de comportamento está em `tests_bench/test_emissao_cte.py`.
"""

import ast
import pathlib
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[1] / "integracao"


def _chamadas(modulo: str, funcao: str) -> list[tuple[int, str]]:
	arvore = ast.parse((RAIZ / f"{modulo}.py").read_text(encoding="utf-8"))
	alvo = next(n for n in ast.walk(arvore) if isinstance(n, ast.FunctionDef) and n.name == funcao)

	return sorted(
		(no.lineno, ast.unparse(no.func))
		for no in ast.walk(alvo)
		if isinstance(no, ast.Call) and ast.unparse(no.func) in ("frappe.db.commit", "frappe.throw")
	)


class TestCommitAntesDoThrow(unittest.TestCase):
	def test_a_rejeicao_e_commitada_antes_de_virar_erro(self):
		for modulo, funcao in (("emissao_nfe", "emitir_nfe"), ("emissao_cte", "emitir_cte")):
			with self.subTest(modulo=modulo):
				nomes = [nome for _, nome in _chamadas(modulo, funcao)]
				ultimo_throw = len(nomes) - 1 - nomes[::-1].index("frappe.throw")

				self.assertEqual(nomes[ultimo_throw - 1], "frappe.db.commit")
