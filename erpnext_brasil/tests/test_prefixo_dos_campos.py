# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Todo campo que este app cria em DocType alheio começa com `br_`.

⚠️ A regra existe porque o app **acrescenta campos a DocTypes de outros apps** — 20 do
ERPNext, 1 do Frappe, 1 do hrms. Um campo nosso chamado `ncm` e um campo futuro do ERPNext
chamado `ncm` disputariam a mesma coluna, e o perdedor seria descoberto por dado errado, não
por erro.

Não havia colisão quando isto foi escrito. Havia **23 campos sem marca de app**, que é a
condição para que uma apareça.

Teste-âncora: `test_todo_campo_comeca_com_br`. É uma regra sem exceção de propósito — os
próprios breaks de layout entram, para que não haja caso especial a memorizar.

Módulo puro: roda sem bench.
"""

import ast
import unittest
from pathlib import Path

from erpnext_brasil.setup.campos import MAPAS, todos_os_campos
from erpnext_brasil.tests.ajudantes import sem_docstrings

RAIZ = Path(__file__).resolve().parent.parent

PREFIXO = "br_"


class TestOPrefixo(unittest.TestCase):
	def test_todo_campo_comeca_com_br(self):
		"""Teste-âncora: sem exceção, inclusive os breaks de layout."""
		fora = sorted(
			f"{doctype}.{campo['fieldname']}"
			for doctype, campos in todos_os_campos().items()
			for campo in campos
			if not campo["fieldname"].startswith(PREFIXO)
		)

		self.assertEqual([], fora, f"campos sem o prefixo {PREFIXO!r}: {fora}")

	def test_nenhum_campo_tem_prefixo_duplicado(self):
		"""`br_br_` é o sintoma de um renome aplicado duas vezes."""
		duplicados = sorted(
			campo["fieldname"]
			for campos in todos_os_campos().values()
			for campo in campos
			if campo["fieldname"].startswith("br_br_")
		)

		self.assertEqual([], duplicados)

	def test_todo_insert_after_de_campo_nosso_aponta_para_nome_com_prefixo(self):
		"""`insert_after` que aponta para o nome antigo põe o campo no lugar errado — e
		isso não levanta erro, só desarruma o formulário."""
		nossos = {campo["fieldname"] for campos in todos_os_campos().values() for campo in campos}
		quebrados = []

		for doctype, campos in todos_os_campos().items():
			for campo in campos:
				ancora = campo.get("insert_after")

				# Âncora em campo nativo do ERPNext é legítima e não tem prefixo.
				if ancora and f"{PREFIXO}{ancora}" in nossos:
					quebrados.append(f"{doctype}.{campo['fieldname']} -> {ancora}")

		self.assertEqual([], quebrados)

	def test_a_uniao_cobre_todos_os_mapas(self):
		"""Um quarto mapa esquecido aqui faria a regra valer só para três."""
		total = sum(len(campos) for mapa in MAPAS for campos in mapa().values())
		unidos = sum(len(campos) for campos in todos_os_campos().values())

		self.assertEqual(total, unidos)


class TestOPatchDeRenome(unittest.TestCase):
	"""Sem o patch, um site já instalado perde o dado das colunas renomeadas."""

	def _patch(self) -> ast.Module:
		caminho = RAIZ / "patches" / "v0_177_renomear_campos_com_prefixo_br.py"

		return ast.parse(caminho.read_text(encoding="utf-8"))

	def _renomes(self) -> dict:
		for no in self._patch().body:
			if isinstance(no, ast.Assign) and any(
				isinstance(alvo, ast.Name) and alvo.id == "RENOMES" for alvo in no.targets
			):
				return ast.literal_eval(no.value)

		raise AssertionError("RENOMES não encontrado no patch")

	def test_o_patch_esta_registrado(self):
		"""Patch fora do `patches.txt` nunca roda."""
		registro = (RAIZ / "patches.txt").read_text(encoding="utf-8")

		self.assertIn("v0_177_renomear_campos_com_prefixo_br", registro)

	def test_todo_destino_do_renome_existe_hoje(self):
		"""Renomear para um campo que o app não declara criaria coluna órfã."""
		declarados = {
			(doctype, campo["fieldname"]) for doctype, campos in todos_os_campos().items() for campo in campos
		}

		for doctype, pares in self._renomes().items():
			for _antigo, novo in pares:
				with self.subTest(doctype=doctype, campo=novo):
					self.assertIn((doctype, novo), declarados)

	def test_o_renome_e_sempre_do_nome_sem_prefixo_para_o_com(self):
		for doctype, pares in self._renomes().items():
			for antigo, novo in pares:
				with self.subTest(doctype=doctype, campo=novo):
					self.assertFalse(antigo.startswith(PREFIXO))
					self.assertEqual(f"{PREFIXO}{antigo}", novo)

	def test_o_patch_tolera_doctype_ausente(self):
		"""`Salary Component` vem do `hrms`, opcional — e o patch roda em todo site."""
		fonte = (RAIZ / "patches" / "v0_177_renomear_campos_com_prefixo_br.py").read_text(encoding="utf-8")

		self.assertIn('frappe.db.exists("DocType", doctype)', fonte)

	def test_o_patch_tolera_site_novo(self):
		"""Num site que já nasceu com os nomes novos não há coluna antiga a renomear."""
		fonte = (RAIZ / "patches" / "v0_177_renomear_campos_com_prefixo_br.py").read_text(encoding="utf-8")

		self.assertIn("has_column", fonte)

	def test_usa_rename_field_e_nao_sql(self):
		"""Um `ALTER TABLE` moveria só a coluna, e o `Custom Field` continuaria apontando
		para um nome que não existe mais."""
		fonte = sem_docstrings(
			(RAIZ / "patches" / "v0_177_renomear_campos_com_prefixo_br.py").read_text(encoding="utf-8")
		)

		self.assertIn("rename_field", fonte)
		self.assertNotIn("ALTER TABLE", fonte)


if __name__ == "__main__":
	unittest.main()
