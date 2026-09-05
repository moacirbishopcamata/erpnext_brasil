# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Costura da geração do EFD — o que dá para travar sem bench.

`integracao/geracao_efd.py` e `integracao/efd_escrituracao.py` importam `frappe`, então a
execução só existe num site real. O que **pode** ser conferido aqui é o que costuma
divergir em silêncio: os domínios que o código grava contra os que o DocType aceita, e a
honestidade do aviso de arquivo parcial.

Teste-âncora: `test_a_situacao_gravada_existe_no_doctype` — gravar um valor fora do
`Select` não levanta erro no Frappe, some no save, e o registro fica sem situação. Mesma
família dos 31 campos de `docs/gaps.md`.
"""

import ast
import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

_FONTE = (RAIZ / "integracao" / "geracao_efd.py").read_text(encoding="utf-8")


def _opcoes_do_doctype(campo: str) -> set[str]:
	caminho = RAIZ / "registros_fiscais" / "doctype" / "arquivo_sped" / "arquivo_sped.json"
	dados = json.loads(caminho.read_text(encoding="utf-8"))
	definicao = next(c for c in dados["fields"] if c["fieldname"] == campo)

	return {o for o in definicao["options"].splitlines() if o}


def _valor_gravado(campo: str) -> str:
	"""O literal que `gerar_efd` grava naquele campo do `Arquivo SPED`."""
	achado = re.search(rf'"{campo}":\s*"([^"]+)"', _FONTE)

	return achado.group(1) if achado else ""


class TestDominiosGravados(unittest.TestCase):
	def test_a_situacao_gravada_existe_no_doctype(self):
		"""Valor fora do Select some no save, e o registro fica sem situação."""
		self.assertIn(_valor_gravado("situacao"), _opcoes_do_doctype("situacao"))

	def test_o_tipo_gravado_vem_da_constante_e_existe_no_doctype(self):
		from erpnext_brasil.contabil.arquivo_sped_registro import TIPO_EFD_ICMS_IPI

		self.assertIn(TIPO_EFD_ICMS_IPI, _opcoes_do_doctype("tipo"))

	def test_a_finalidade_gravada_existe_no_doctype(self):
		from erpnext_brasil.contabil.arquivo_sped_registro import FINALIDADE_ORIGINAL

		self.assertIn(FINALIDADE_ORIGINAL, _opcoes_do_doctype("finalidade"))

	def test_todo_campo_gravado_existe_no_doctype(self):
		"""A varredura completa: nenhum campo inventado no dicionário de criação."""
		caminho = RAIZ / "registros_fiscais" / "doctype" / "arquivo_sped" / "arquivo_sped.json"
		declarados = {c["fieldname"] for c in json.loads(caminho.read_text(encoding="utf-8"))["fields"]}
		# `doctype` e `name` são do próprio Frappe, não campos do JSON.
		declarados |= {"doctype", "name"}

		arvore = ast.parse(_FONTE)
		gravados: set[str] = set()

		for no in ast.walk(arvore):
			if not isinstance(no, ast.Dict):
				continue

			chaves = [c.value for c in no.keys if isinstance(c, ast.Constant) and isinstance(c.value, str)]

			if "doctype" in chaves:
				gravados |= set(chaves)

		ausentes = sorted(gravados - declarados)

		self.assertEqual(ausentes, [], f"campos gravados e não declarados: {ausentes}")


class TestAvisoDeArquivoParcial(unittest.TestCase):
	"""Prometer arquivo entregável e devolver parcial é o silêncio que este projeto evita."""

	def _blocos_ausentes(self) -> tuple:
		"""Lê a constante por AST em vez de importar: o módulo importa `frappe`, e a suíte
		pura não o alcança. Mesma técnica do resto deste arquivo."""
		for no in ast.walk(ast.parse(_FONTE)):
			if isinstance(no, ast.Assign) and any(
				getattr(alvo, "id", "") == "BLOCOS_SEM_LEITURA_DO_SITE" for alvo in no.targets
			):
				return ast.literal_eval(no.value)

		raise AssertionError("BLOCOS_SEM_LEITURA_DO_SITE não encontrada")

	def test_os_blocos_ausentes_sao_os_que_nao_tem_leitura_do_site(self):
		self.assertEqual(self._blocos_ausentes(), ("D",))

	def test_os_blocos_com_leitura_do_site_nao_estao_entre_os_ausentes(self):
		"""C, E, H e K já são lidos do site."""
		ausentes = self._blocos_ausentes()

		for bloco in ("C", "E", "H", "K"):
			with self.subTest(bloco=bloco):
				self.assertNotIn(bloco, ausentes)

	def test_o_bloco_e_nunca_pode_faltar(self):
		"""É o único que não admite ser declarado vazio — `montar_e001` só aceita "0".

		Por isso ele foi o primeiro dos quatro a ganhar leitura do site: sem ele nenhum
		EFD é aceito, enquanto D/H/K ausentes apenas tornam o arquivo incompleto.
		"""
		self.assertIn('"E": bloco_e_do_periodo', _FONTE)

	def test_o_retorno_carrega_o_aviso(self):
		self.assertIn('"aviso"', _FONTE)
		self.assertIn("não para transmitir", _FONTE)

	def test_os_blocos_ausentes_tem_leiaute_implementado(self):
		"""O que falta é a leitura do site, não o leiaute — a distinção importa para quem
		for retomar."""
		for bloco in ("d", "h", "k"):
			with self.subTest(bloco=bloco):
				self.assertTrue((RAIZ / "contabil" / f"efd_bloco_{bloco}.py").exists())


if __name__ == "__main__":
	unittest.main()
