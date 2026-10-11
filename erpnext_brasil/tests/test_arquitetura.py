# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de arquitetura: regras estruturais que a suíte faz valer.

Uma regra de arquitetura só escrita no README é aspiracional — alguém a viola sem
perceber, e ninguém nota até o dia em que a suíte precisa de um bench para rodar. Estes
testes tornam a regra executável.

A violação que motivou este arquivo foi real: três módulos com `import frappe` estavam
dentro de `fiscal/`, o que fazia a "camada pura" não ser pura.
"""

import ast
import pathlib
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
PURO = RAIZ / "fiscal"
INTEGRACAO = RAIZ / "integracao"


def _modulos(pasta: pathlib.Path) -> list[pathlib.Path]:
	return [p for p in pasta.rglob("*.py") if "__pycache__" not in p.parts]


def _importa(caminho: pathlib.Path, pacote: str) -> bool:
	arvore = ast.parse(caminho.read_text(encoding="utf-8"))

	for no in ast.walk(arvore):
		if isinstance(no, ast.Import):
			if any(a.name == pacote or a.name.startswith(pacote + ".") for a in no.names):
				return True
		elif isinstance(no, ast.ImportFrom):
			modulo = no.module or ""

			if modulo == pacote or modulo.startswith(pacote + "."):
				return True

	return False


class TestCamadaPura(unittest.TestCase):
	"""`fiscal/` contém a regra fiscal e não pode depender do framework."""

	def test_existe_e_nao_esta_vazia(self):
		self.assertTrue(_modulos(PURO), "a camada pura sumiu")

	def test_nenhum_modulo_importa_frappe(self):
		violacoes = [p.relative_to(RAIZ).as_posix() for p in _modulos(PURO) if _importa(p, "frappe")]

		self.assertEqual(
			violacoes,
			[],
			"Módulos em fiscal/ importando frappe deixam de ser testáveis sem bench; "
			"o lugar deles é integracao/",
		)

	def test_nao_depende_da_camada_de_integracao(self):
		"""A dependência aponta em uma direção só: integração conhece fiscal, não o inverso."""
		violacoes = [
			p.relative_to(RAIZ).as_posix() for p in _modulos(PURO) if _importa(p, "erpnext_brasil.integracao")
		]

		self.assertEqual(violacoes, [], "dependência invertida entre as camadas")


PACOTES_PUROS_DAS_FERRAMENTAS = ("persistencia", "sistema", "bancos", "soda", "chantilly")
"""Regra pura das ferramentas de operação (Cherry, Soda e Chantilly): complementos desktop em Python puro."""


class TestPacotesPurosDasFerramentas(unittest.TestCase):
	"""A regra das ferramentas de operação não conhece o framework, a interface nem a camada de integração.

	Sem `frappe`, sem `tkinter` e sem `integracao/`, a regra roda e é testada em qualquer máquina, com a
	biblioteca padrão — é o que faz dessas ferramentas complementos desktop em Python puro.
	"""

	def _pacotes(self):
		return [RAIZ / nome for nome in PACOTES_PUROS_DAS_FERRAMENTAS if (RAIZ / nome).is_dir()]

	def test_existe_ao_menos_a_persistencia(self):
		self.assertTrue((RAIZ / "persistencia").is_dir())

	def test_nenhum_importa_frappe_tkinter_nem_integracao(self):
		proibidos = ("frappe", "tkinter", "erpnext_brasil.integracao")
		violacoes = [
			f"{p.relative_to(RAIZ).as_posix()} importa {proibido}"
			for pacote in self._pacotes()
			for p in _modulos(pacote)
			for proibido in proibidos
			if _importa(p, proibido)
		]

		self.assertEqual(
			violacoes, [], "regra pura das ferramentas dependendo de framework, interface ou integração"
		)


class TestSuiteRodaSemBench(unittest.TestCase):
	def test_nenhum_teste_importa_frappe(self):
		"""Se um teste precisar de frappe, a suíte deixa de rodar em qualquer máquina."""
		testes = _modulos(RAIZ / "tests")
		violacoes = [p.name for p in testes if _importa(p, "frappe")]

		self.assertEqual(violacoes, [])


class TestCamadaDeIntegracao(unittest.TestCase):
	def test_toda_regra_fica_do_lado_puro(self):
		"""A integração é fina: nenhum módulo dela deve ser grande.

		Limite generoso de propósito — o que se quer barrar é regra migrando para cá,
		não estilo. Um módulo de integração que cresce é sinal de lógica no lugar errado.
		"""
		grandes = []

		for caminho in _modulos(INTEGRACAO):
			linhas = len(caminho.read_text(encoding="utf-8").splitlines())

			if linhas > 320:
				grandes.append(f"{caminho.name} ({linhas} linhas)")

		self.assertEqual(grandes, [], "módulo de integração grande demais; extraia a regra")


if __name__ == "__main__":
	unittest.main()
