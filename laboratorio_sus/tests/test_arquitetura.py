# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Regras estruturais do módulo avulso, executáveis.

- `puro/` não conhece framework, interface nem outro módulo do projeto: roda em qualquer máquina.
- O módulo inteiro é **avulso**: não importa `erpnext_brasil`, `healthcare` nem `erpnext`. Integração com eles
  só por adaptador opcional, que mora em pasta própria e não é carregada pela regra.
"""

import ast
import pathlib
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[1]

PROIBIDOS_NA_REGRA = ("frappe", "tkinter", "erpnext_brasil", "erpnext", "healthcare", "scripts")
PROIBIDOS_NO_MODULO = ("erpnext_brasil", "erpnext", "healthcare")


def _modulos(pasta: pathlib.Path, ignorar: tuple[str, ...] = ()) -> list[pathlib.Path]:
	return [
		p
		for p in pasta.rglob("*.py")
		if "__pycache__" not in p.parts and not any(parte in ignorar for parte in p.relative_to(pasta).parts)
	]


def importa(caminho: pathlib.Path, pacote: str) -> bool:
	arvore = ast.parse(caminho.read_text(encoding="utf-8"))

	for no in ast.walk(arvore):
		if isinstance(no, ast.Import):
			if any(a.name == pacote or a.name.startswith(pacote + ".") for a in no.names):
				return True
		elif isinstance(no, ast.ImportFrom):
			modulo = no.module or ""

			if no.level == 0 and (modulo == pacote or modulo.startswith(pacote + ".")):
				return True

	return False


def violacoes(pasta: pathlib.Path, proibidos: tuple[str, ...], ignorar: tuple[str, ...] = ()) -> list[str]:
	return [
		f"{p.name} importa {proibido}"
		for p in _modulos(pasta, ignorar)
		for proibido in proibidos
		if importa(p, proibido)
	]


class TestCamadaPura(unittest.TestCase):
	def test_existe_e_nao_esta_vazia(self):
		self.assertTrue(_modulos(RAIZ / "puro"))

	def test_nao_importa_framework_interface_nem_outro_modulo(self):
		self.assertEqual(violacoes(RAIZ / "puro", PROIBIDOS_NA_REGRA), [])


class TestModuloAvulso(unittest.TestCase):
	def test_nenhum_arquivo_importa_outro_app(self):
		self.assertEqual(
			violacoes(RAIZ, PROIBIDOS_NO_MODULO, ignorar=("tests", "adaptadores")),
			[],
			"o módulo é avulso: integração com outro app só em adaptadores/",
		)


class TestAProprioRegraFalha(unittest.TestCase):
	"""A regra só vale se de fato falha quando violada: injeta a violação numa pasta temporária."""

	def test_detecta_import_de_frappe(self):
		with tempfile.TemporaryDirectory() as tmp:
			pasta = pathlib.Path(tmp)
			(pasta / "ruim.py").write_text("import frappe\n", encoding="utf-8")
			(pasta / "ruim2.py").write_text("from frappe.utils import now\n", encoding="utf-8")
			(pasta / "ok.py").write_text("import json\nfrom . import x\n", encoding="utf-8")

			achados = violacoes(pasta, PROIBIDOS_NA_REGRA)

		self.assertEqual(sorted(achados), ["ruim.py importa frappe", "ruim2.py importa frappe"])

	def test_detecta_import_de_outro_app(self):
		with tempfile.TemporaryDirectory() as tmp:
			pasta = pathlib.Path(tmp)
			(pasta / "x.py").write_text("from erpnext_brasil.fiscal import chave\n", encoding="utf-8")

			self.assertEqual(violacoes(pasta, PROIBIDOS_NO_MODULO), ["x.py importa erpnext_brasil"])


if __name__ == "__main__":
	unittest.main()
