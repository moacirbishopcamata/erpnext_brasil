# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Prepara os segredos do Docker: cria `docker/segredos/db_password` e `admin_password`.

    python docker/preparar.py

Complemento em Python puro (só a biblioteca padrão), igual em Windows e em Linux.

Contratos (Design by Contract)
------------------------------
- **Nunca sobrescreve** um segredo existente: criar com `O_EXCL` é atômico, então duas execuções
  simultâneas não se atropelam. Um arquivo existente e vazio é recusado (`SegredoInvalido`), nunca
  "consertado" em silêncio.
- **Nunca imprime** o valor gerado. Só diz o nome do arquivo e se foi criado ou mantido.
- **Permissão restrita ao dono** (`0600`) onde o sistema permite. No Windows a permissão POSIX não existe e
  vale o controle de acesso da pasta do usuário; o script avisa.
- Valores de `secrets.token_urlsafe`: aleatórios criptograficamente seguros e seguros para o shell
  (só letras, dígitos, `-` e `_`), porque o serviço de criação de site os lê dentro de um script de shell.
"""

import argparse
import os
import secrets
import sys
from collections.abc import Callable
from pathlib import Path

__all__ = ["NOMES_DOS_SEGREDOS", "SegredoInvalido", "gerar_segredos", "main"]

NOMES_DOS_SEGREDOS = ("db_password", "admin_password")
PASTA_PADRAO = Path(__file__).resolve().parent / "segredos"
TAMANHO = 24


class SegredoInvalido(ValueError):
	"""Um arquivo de segredo existe, mas não serve (vazio). O script não o altera."""


def _novo_valor() -> str:
	return secrets.token_urlsafe(TAMANHO)


def gerar_segredos(pasta: Path, *, gerar: Callable[[], str] = _novo_valor) -> dict[str, str]:
	"""Cria os segredos que faltam e devolve `{nome: "criado" | "mantido"}`. Nunca devolve o valor."""
	pasta = Path(pasta)
	pasta.mkdir(parents=True, exist_ok=True)
	situacao: dict[str, str] = {}

	for nome in NOMES_DOS_SEGREDOS:
		caminho = pasta / nome

		try:
			descritor = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
		except FileExistsError:
			if caminho.stat().st_size == 0:
				raise SegredoInvalido(
					f"{caminho} existe e está vazio; apague-o ou preencha-o antes de continuar"
				) from None

			situacao[nome] = "mantido"
			continue

		with os.fdopen(descritor, "w", encoding="utf-8", newline="") as arquivo:
			arquivo.write(gerar())

		situacao[nome] = "criado"

	return situacao


def main(argv: list[str] | None = None) -> int:
	analisador = argparse.ArgumentParser(
		description="Cria os arquivos de segredo do Docker, sem imprimir os valores."
	)
	analisador.add_argument("--pasta", type=Path, default=PASTA_PADRAO, help="onde criar os segredos")
	argumentos = analisador.parse_args(argv)

	try:
		situacao = gerar_segredos(argumentos.pasta)
	except SegredoInvalido as erro:
		print(f"Não foi possível: {erro}", file=sys.stderr)
		return 2

	for nome, estado in situacao.items():
		print(f"{nome}: {estado}")

	if os.name == "nt":
		print(
			"Aviso: no Windows a permissão 0600 não existe; mantenha a pasta de segredos num diretório só seu.",
			file=sys.stderr,
		)

	print("Próximo passo: copie docker/.env.example para docker/.env e rode o Compose (veja docs/docker.md).")

	return 0


if __name__ == "__main__":
	sys.exit(main())
