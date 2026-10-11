# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Constrói a imagem do ERPNext Brasil (Frappe, ERPNext e erpnext_brasil na versão 16).

    python docker/construir.py                      # usa docker/apps.json
    python docker/construir.py --apps docker/apps.local.json --tag 2026.10

Complemento em Python puro (só a biblioteca padrão), igual em Windows e em Linux.

Como funciona
-------------
Reaproveita a receita em camadas do projeto `frappe_docker` (`images/layered/Containerfile`), usada como
**contexto remoto fixado por commit**: a mesma construção parte da mesma base. A lista de aplicativos é passada
como *build secret* (`--secret id=apps_json`), que **não entra nas camadas da imagem**. É por isso que um
`apps.local.json` com credencial de leitura do repositório privado pode ser usado sem vazar para a imagem.

Contratos
---------
- O comando é montado como **lista de argumentos** e executado sem shell.
- O conteúdo do `apps.json` nunca aparece no comando, só o caminho do arquivo.
- O commit do `frappe_docker` é validado (40 caracteres hexadecimais): ramo móvel não é aceito.
- Etiqueta, nome de imagem e ramo passam por padrões estritos antes de chegar ao Docker.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

__all__ = ["FRAPPE_DOCKER_COMMIT", "ConstrucaoInvalida", "comando_de_build", "main"]

FRAPPE_DOCKER_COMMIT = "2b26e9ab8d751e5ea33bb7b930aea3550bb81ded"
"""Commit do `frappe/frappe_docker` de 2026-10-09 (conferido em 2026-10-11). Atualizar é decisão consciente."""

REPOSITORIO_DA_RECEITA = "https://github.com/frappe/frappe_docker.git"
RECEITA = "images/layered/Containerfile"
FRAPPE_URL = "https://github.com/frappe/frappe"
APPS_PADRAO = Path(__file__).resolve().parent / "apps.json"

_COMMIT = re.compile(r"[0-9a-f]{40}")
_TAG = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}")
_IMAGEM = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*")
_RAMO = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,100}")


class ConstrucaoInvalida(ValueError):
	"""Pré-condição violada: nada é executado."""


def _exigir(padrao: re.Pattern, valor: str, o_que: str) -> str:
	if not isinstance(valor, str) or not padrao.fullmatch(valor):
		raise ConstrucaoInvalida(f"{o_que} não é válido: {valor!r}")

	return valor


def _conferir_apps(apps: Path) -> Path:
	"""O arquivo existe e é uma lista de aplicativos; o conteúdo (que pode ter credencial) nunca é repetido."""
	apps = Path(apps)

	if not apps.is_file():
		raise ConstrucaoInvalida(f"a lista de aplicativos não existe: {apps}")

	try:
		dados = json.loads(apps.read_text(encoding="utf-8"))
	except (OSError, ValueError) as erro:
		raise ConstrucaoInvalida(f"a lista de aplicativos não pôde ser lida como JSON: {apps}") from erro

	if (
		not isinstance(dados, list)
		or not dados
		or not all(isinstance(a, dict) and a.get("url") for a in dados)
	):
		raise ConstrucaoInvalida(f"{apps} precisa ser uma lista não vazia de aplicativos com `url`")

	return apps.resolve()


def comando_de_build(
	*,
	apps: Path,
	imagem: str = "erpnext-brasil",
	tag: str = "version-16",
	ramo: str = "version-16",
	commit: str = FRAPPE_DOCKER_COMMIT,
	docker: str = "docker",
) -> list[str]:
	"""O `docker build` como lista de argumentos. Não executa nada."""
	_exigir(_COMMIT, commit, "o commit do frappe_docker (40 caracteres hexadecimais)")
	_exigir(_IMAGEM, imagem, "o nome da imagem")
	_exigir(_TAG, tag, "a etiqueta")
	_exigir(_RAMO, ramo, "o ramo do Frappe")
	arquivo = _conferir_apps(apps)

	return [
		docker,
		"build",
		"--build-arg",
		f"FRAPPE_BRANCH={ramo}",
		"--build-arg",
		f"FRAPPE_PATH={FRAPPE_URL}",
		"--secret",
		f"id=apps_json,src={arquivo}",
		"--tag",
		f"{imagem}:{tag}",
		"--file",
		RECEITA,
		f"{REPOSITORIO_DA_RECEITA}#{commit}",
	]


def main(argv: list[str] | None = None) -> int:
	analisador = argparse.ArgumentParser(description="Constrói a imagem Docker do ERPNext Brasil.")
	analisador.add_argument("--apps", type=Path, default=APPS_PADRAO, help="lista de aplicativos (apps.json)")
	analisador.add_argument("--imagem", default="erpnext-brasil")
	analisador.add_argument("--tag", default="version-16")
	analisador.add_argument("--ramo", default="version-16", help="ramo do Frappe")
	analisador.add_argument("--commit", default=FRAPPE_DOCKER_COMMIT, help="commit do frappe_docker (fixado)")
	analisador.add_argument("--mostrar", action="store_true", help="só mostra o comando e sai")
	argumentos = analisador.parse_args(argv)

	try:
		comando = comando_de_build(
			apps=argumentos.apps,
			imagem=argumentos.imagem,
			tag=argumentos.tag,
			ramo=argumentos.ramo,
			commit=argumentos.commit,
		)
	except ConstrucaoInvalida as erro:
		print(f"Não foi possível: {erro}", file=sys.stderr)
		return 2

	if argumentos.mostrar:
		print(" ".join(comando))
		return 0

	if shutil.which(comando[0]) is None:
		print(
			"Não foi possível: o Docker não foi encontrado. Instale o Docker (no Windows, o Docker Desktop).",
			file=sys.stderr,
		)
		return 3

	print("Construindo a imagem; a primeira vez baixa gigabytes e leva dezenas de minutos.")

	return subprocess.run(comando, check=False, env={**os.environ, "DOCKER_BUILDKIT": "1"}).returncode


if __name__ == "__main__":
	sys.exit(main())
