# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Os padrões de código do projeto, verificados por teste — não só declarados.

`pyproject.toml` declara o lint (`[tool.ruff.lint]`) e o formatador
(`[tool.ruff.format]`) desde o início do projeto. Numa auditoria em 2026-09-03,
descobriu-se que **nunca tinham sido executados**: havia 135 violações do que o próprio
projeto selecionou, e 134 arquivos fora do formatador. Padrão declarado e não verificado
é padrão que existe só no papel.

Este arquivo faz pelo estilo o que `test_arquitetura.py` já faz pela arquitetura:
transforma a regra em teste. Se alguém introduzir uma violação, a suíte acusa antes do
commit — em vez de a dívida crescer em silêncio até uma auditoria.

Por que não depende do `ruff` estar instalado
------------------------------------------------------
`ruff` não é dependência de execução do app: quem só roda o ERPNext não precisa dele.
Os testes abaixo **pulam** quando ele não está presente, em vez de falhar — falhar ali
puniria quem não tem a ferramenta de desenvolvimento, sem nenhum ganho de qualidade.
Onde o desenvolvimento acontece (e na CI), o `ruff` está lá e a verificação roda.
"""

import shutil
import subprocess
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent

TEM_RUFF = shutil.which("ruff") is not None


def _rodar_ruff(*argumentos: str) -> subprocess.CompletedProcess:
	return subprocess.run(
		["ruff", *argumentos],
		cwd=RAIZ,
		capture_output=True,
		text=True,
		check=False,
	)


@unittest.skipUnless(TEM_RUFF, "requer ruff, a ferramenta de lint declarada no pyproject.toml")
class TestLint(unittest.TestCase):
	def test_sem_violacoes_de_lint(self):
		"""As regras selecionadas em `[tool.ruff.lint]` valem de verdade.

		A mensagem de falha traz a saída inteira do `ruff`: quem quebrar o padrão vê o
		que quebrou sem precisar rodar nada à mão.
		"""
		resultado = _rodar_ruff("check", "erpnext_brasil/", "scripts/")

		self.assertEqual(
			resultado.returncode,
			0,
			f"violações de lint encontradas:\n{resultado.stdout}\n{resultado.stderr}",
		)


@unittest.skipUnless(TEM_RUFF, "requer ruff, a ferramenta de formatação declarada no pyproject.toml")
class TestFormatacao(unittest.TestCase):
	def test_codigo_formatado(self):
		"""O estilo de `[tool.ruff.format]` (tab, aspas duplas) vale de verdade.

		Mesma escolha do `erpnext`, para que contribuição circule entre os dois
		repositórios sem reformatação — o motivo está registrado no `pyproject.toml`.
		"""
		resultado = _rodar_ruff("format", "--check", "erpnext_brasil/", "scripts/")

		self.assertEqual(
			resultado.returncode,
			0,
			f"arquivos fora do formatador:\n{resultado.stdout}\n{resultado.stderr}",
		)


if __name__ == "__main__":
	unittest.main()
