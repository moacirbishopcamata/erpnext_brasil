# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Modelo de endereço brasileiro (`setup/modelo_de_endereco.py`) — tarefa 1.3 de `tropicalizar-demais-modulos`.

O instalador importa `frappe`, então a suíte pura não o executa (o efeito está em
`tests_bench/test_modelo_de_endereco.py`, onde o Jinja do Frappe renderiza o texto). Aqui se trava a forma do
texto e a costura com a instalação.

Teste-âncora: `test_o_modelo_mostra_numero_e_bairro`. Os dois campos existem no `Address` e o modelo padrão do
Frappe não os imprime — o dado estava lá e não aparecia.
"""

import ast
import pathlib
import re
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
FONTE = RAIZ / "setup" / "modelo_de_endereco.py"


def _modelo() -> str:
	for no in ast.parse(FONTE.read_text(encoding="utf-8")).body:
		if isinstance(no, ast.Assign) and getattr(no.targets[0], "id", "") == "MODELO":
			return ast.literal_eval(no.value)

	raise AssertionError("MODELO não encontrado")


class TestTextoDoModelo(unittest.TestCase):
	def test_o_modelo_mostra_numero_e_bairro(self):
		modelo = _modelo()

		self.assertIn("br_numero_endereco", modelo)
		self.assertIn("br_bairro", modelo)

	def test_a_ordem_e_a_de_um_endereco_brasileiro(self):
		modelo = _modelo()
		ordem = [
			modelo.index(campo)
			for campo in ("address_line1", "br_numero_endereco", "br_bairro", "city", "pincode")
		]

		self.assertEqual(ordem, sorted(ordem))

	def test_cidade_vem_com_uf_e_o_cep_e_rotulado(self):
		modelo = _modelo()

		self.assertRegex(modelo, r"\{\{ city \}\}\{% if state %\} - \{\{ state \}\}")
		self.assertIn("CEP {{ pincode }}", modelo)

	def test_campos_opcionais_nao_deixam_linha_vazia(self):
		"""Cada campo opcional está dentro de um `if` — um endereço sem bairro não imprime `<br>` solto."""
		modelo = _modelo()

		for campo in ("br_numero_endereco", "br_bairro", "address_line2", "pincode", "phone", "email_id"):
			with self.subTest(campo=campo):
				self.assertRegex(modelo, r"\{% if " + campo + r" %\}")

	def test_telefone_fax_e_email_continuam_como_no_modelo_padrao_do_frappe(self):
		modelo = _modelo()

		for rotulo in ('_("Phone")', '_("Fax")', '_("Email")'):
			self.assertIn(rotulo, modelo)

	def test_so_usa_campos_que_o_address_tem(self):
		"""Campo inexistente renderiza vazio em silêncio — o mesmo defeito, do outro lado."""
		from erpnext_brasil.setup import custom_fields

		declarados = {c["fieldname"] for c in custom_fields.get_custom_fields().get("Address", [])}
		do_core = {
			"address_line1", "address_line2", "city", "state", "pincode", "country", "phone", "fax", "email_id"
		}  # fmt: skip
		usados = set(re.findall(r"\{\{\s*([a-z_0-9]+)\s*\}\}", _modelo())) | set(
			re.findall(r"\{% if ([a-z_0-9]+) %\}", _modelo())
		)

		self.assertEqual(sorted(usados - declarados - do_core), [], "campos do modelo que o Address não tem")

	def test_jinja_valido_quando_disponivel(self):
		try:
			import jinja2
		except ModuleNotFoundError:
			self.skipTest("jinja2 não está no ambiente puro; a renderização é conferida em tests_bench")

		jinja2.Environment().parse(_modelo())


class TestCosturaDaInstalacao(unittest.TestCase):
	def _funcao(self, arquivo: str, nome: str) -> ast.FunctionDef:
		arvore = ast.parse((RAIZ / "setup" / arquivo).read_text(encoding="utf-8"))

		return next(n for n in ast.walk(arvore) if isinstance(n, ast.FunctionDef) and n.name == nome)

	def test_instalacao_e_migracao_chamam_o_instalador(self):
		for gancho in ("after_install", "after_migrate"):
			with self.subTest(gancho=gancho):
				self.assertIn(
					"instalar_modelo_de_endereco()", ast.unparse(self._funcao("install.py", gancho))
				)

	def test_so_cria_quando_falta_modelo_do_brasil_e_ha_padrao(self):
		corpo = ast.unparse(self._funcao("modelo_de_endereco.py", "instalar_modelo_de_endereco"))

		self.assertIn("'country': PAIS", corpo)
		self.assertIn("'is_default': 1", corpo, "sem modelo padrão o Frappe promoveria o nosso a padrão")
		self.assertIn("'is_default': 0", corpo)
		self.assertNotIn(".delete", corpo)
		self.assertNotIn("set_value", corpo, "não sobrescreve modelo existente")

	def test_devolve_o_motivo_de_nao_instalar(self):
		corpo = ast.unparse(self._funcao("modelo_de_endereco.py", "instalar_modelo_de_endereco"))

		for motivo in ("criado", "ja_existia", "sem_padrao", "sem_pais"):
			self.assertIn(f"'{motivo}'", corpo)


if __name__ == "__main__":
	unittest.main()
