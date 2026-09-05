# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Estrutura dos DocTypes próprios — o que o Frappe exige em disco.

Escrito depois de um achado do bench em 2026-09-04: `Evento do Lote eSocial` tinha JSON e
`__init__.py` mas **não tinha o módulo Python**, e o Frappe importa `<doctype>.py` em todo
`on_doctype_update`. O `bench migrate` inteiro morria com "Module import failed ... the
DocType you're trying to open might be deleted".

O teste puro não olhava para isso porque não havia nada a importar — e é justamente o
formato de gap que este projeto já conhece: arquivo declarado, nada verificando que o
Frappe o aceita. Aqui a verificação é de **disco**, então roda sem bench.

O que ele **não** substitui: `bench migrate` de verdade. Um JSON com campo inválido passa
por aqui e quebra lá. A lacuna segue em `docs/gaps.md`.
"""

import ast
import json
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MODULOS = ("registros_fiscais",)


def _pastas_de_doctype() -> list[Path]:
	pastas = []

	for modulo in MODULOS:
		raiz = RAIZ / modulo / "doctype"

		if raiz.exists():
			pastas.extend(p for p in raiz.iterdir() if p.is_dir() and not p.name.startswith("__"))

	return sorted(pastas)


class TestArquivosObrigatorios(unittest.TestCase):
	def test_ha_doctypes_para_conferir(self):
		"""Se a varredura não achar nada, os testes abaixo passam por vacuidade."""
		self.assertGreater(len(_pastas_de_doctype()), 0)

	def test_todo_doctype_tem_modulo_python(self):
		"""O achado: sem `<doctype>.py`, o `bench migrate` inteiro morre."""
		sem_modulo = [p.name for p in _pastas_de_doctype() if not (p / f"{p.name}.py").exists()]

		self.assertEqual(sem_modulo, [], f"DocTypes sem controller Python: {sem_modulo}")

	def test_todo_doctype_tem_json(self):
		sem_json = [p.name for p in _pastas_de_doctype() if not (p / f"{p.name}.json").exists()]

		self.assertEqual(sem_json, [], f"DocTypes sem JSON: {sem_json}")

	def test_todo_doctype_tem_init(self):
		"""Sem `__init__.py` a pasta não é pacote, e o import falha do mesmo jeito."""
		sem_init = [p.name for p in _pastas_de_doctype() if not (p / "__init__.py").exists()]

		self.assertEqual(sem_init, [], f"DocTypes sem __init__.py: {sem_init}")


class TestCoerenciaDoJson(unittest.TestCase):
	def _json(self, pasta: Path) -> dict:
		return json.loads((pasta / f"{pasta.name}.json").read_text(encoding="utf-8"))

	def test_o_modulo_declarado_existe_no_modules_txt(self):
		"""Módulo que o `modules.txt` não lista não é instalado."""
		declarados = {
			linha.strip()
			for linha in (RAIZ / "modules.txt").read_text(encoding="utf-8").splitlines()
			if linha.strip()
		}

		for pasta in _pastas_de_doctype():
			with self.subTest(doctype=pasta.name):
				self.assertIn(self._json(pasta)["module"], declarados)

	def test_o_field_order_cobre_todos_os_campos(self):
		"""Campo fora do `field_order` não aparece na tela — some sem erro."""
		for pasta in _pastas_de_doctype():
			dados = self._json(pasta)

			if "field_order" not in dados:
				continue

			nomes = {campo["fieldname"] for campo in dados["fields"]}
			ordenados = set(dados["field_order"])

			with self.subTest(doctype=pasta.name):
				self.assertEqual(nomes - ordenados, set(), "campos fora do field_order")
				self.assertEqual(ordenados - nomes, set(), "field_order cita campo inexistente")

	def test_todo_campo_tem_fieldtype(self):
		for pasta in _pastas_de_doctype():
			for campo in self._json(pasta)["fields"]:
				with self.subTest(doctype=pasta.name, campo=campo.get("fieldname")):
					self.assertIn("fieldtype", campo)

	def test_link_sempre_declara_options(self):
		"""`Link` sem `options` não sabe para qual DocType aponta."""
		for pasta in _pastas_de_doctype():
			for campo in self._json(pasta)["fields"]:
				if campo.get("fieldtype") not in ("Link", "Table"):
					continue

				with self.subTest(doctype=pasta.name, campo=campo["fieldname"]):
					self.assertTrue(campo.get("options"), "Link/Table sem options")


class TestNomeDaClasse(unittest.TestCase):
	"""A regra que o Frappe aplica sem avisar — e cuja violação apaga o DocType.

	`base_document.get_controller` procura a classe por
	`doctype.replace(" ", "").replace("-", "")`, preservando a caixa do nome. Se não
	achar, levanta `ImportError` — e `remove_orphan_doctypes` trata **todo** `ImportError`
	como "DocType órfão" e **apaga o registro** na migração seguinte, em silêncio.

	Aconteceu em 2026-09-04: `EventoDoLoteESocial` (que é o que o bom senso do Python
	sugere) em vez de `EventodoLoteeSocial`. O DocType foi apagado duas vezes antes de a
	causa aparecer.
	"""

	def _classes_declaradas(self, pasta: Path) -> set[str]:
		fonte = (pasta / f"{pasta.name}.py").read_text(encoding="utf-8")

		return {no.name for no in ast.walk(ast.parse(fonte)) if isinstance(no, ast.ClassDef)}

	def test_a_classe_tem_o_nome_que_o_frappe_procura(self):
		for pasta in _pastas_de_doctype():
			dados = json.loads((pasta / f"{pasta.name}.json").read_text(encoding="utf-8"))
			esperada = dados["name"].replace(" ", "").replace("-", "")

			with self.subTest(doctype=dados["name"]):
				self.assertIn(
					esperada,
					self._classes_declaradas(pasta),
					f"o Frappe procura a classe {esperada!r} e não a encontra — "
					"o DocType será apagado como órfão na próxima migração",
				)


if __name__ == "__main__":
	unittest.main()
