# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Quais módulos ligados em `hooks.py` já têm teste de bench, e quais não têm.

Por que existe
--------------
A pergunta "o que testar em bench a seguir?" tem uma resposta objetiva — os módulos que o
`hooks.py` manda o Frappe executar e que nenhum teste de bench exercita —, e respondê-la de
cabeça produz a escolha errada. Este script a responde em segundo.

⚠️ Lê uma **declaração**, porque as duas inferências óbvias erram
------------------------------------------------------------------------
Tentei as duas antes de chegar aqui, e cada uma errou para um lado:

- **Por nome de arquivo** (`test_<modulo>.py`): perde os arquivos que cobrem mais de um
  módulo. `test_cadeia_do_documento.py` exercita três, e os três apareciam como
  descobertos.
- **Por import**: perde os testes que exercitam o hook **através do `save`**, sem importar
  o módulo. E esses são os melhores — quanto mais o teste passa pela cadeia real do Frappe,
  menos ele precisa importar o que prova.

A segunda inferência é pior que a primeira, porque **penaliza justamente o teste bom**.

Por isso cada arquivo de `tests_bench/` declara `MODULOS_COBERTOS`, e este script lê a
declaração. Dado explícito no lugar de heurística — a mesma escolha de `MAPAS` em
`setup/campos.py` e de `RENOMES` no patch de prefixo.

Uso
---
    python scripts/cobertura_de_bench.py
"""

import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent / "erpnext_brasil"

LIGADOS = re.compile(r"erpnext_brasil\.integracao\.(\w+)\.")
DECLARADOS = re.compile(r"MODULOS_COBERTOS\s*=\s*\(([^)]*)\)", re.S)


def ligados_em_hooks() -> set[str]:
	"""Os módulos de `integracao/` que o `hooks.py` manda o Frappe executar."""
	return set(LIGADOS.findall((RAIZ / "hooks.py").read_text(encoding="utf-8")))


def cobertos_por_bench() -> set[str]:
	"""Os módulos que os arquivos de `tests_bench/` **declaram** cobrir."""
	cobertos: set[str] = set()

	for caminho in (RAIZ / "tests_bench").glob("test_*.py"):
		achado = DECLARADOS.search(caminho.read_text(encoding="utf-8"))

		if not achado:
			print(f"  aviso: {caminho.name} não declara MODULOS_COBERTOS")
			continue

		cobertos |= {parte.strip().strip("\"'") for parte in achado.group(1).split(",") if parte.strip()}

	return cobertos


def main() -> int:
	ligados = ligados_em_hooks()
	cobertos = cobertos_por_bench()
	faltando = sorted(ligados - cobertos)

	print(f"Módulos de integracao/ ligados em hooks.py: {len(ligados)}")

	for modulo in sorted(ligados):
		print(("  [ok]" if modulo in cobertos else "  [  ]"), modulo)

	print()
	print(f"Cobertura de bench: {len(ligados) - len(faltando)}/{len(ligados)}")

	if faltando:
		print("Sem teste de bench:", ", ".join(faltando))

	# Nunca falha: é medição, não portão. Transformá-lo em portão obrigaria a cobrir tudo
	# antes de ligar qualquer hook novo, e o efeito seria hook fora do `hooks.py` — o gap
	# que este projeto mais combate.
	return 0


if __name__ == "__main__":
	sys.exit(main())
