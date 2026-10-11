# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Abre o repositório no formato escolhido e troca de formato sem perda.

A escolha entre JSON e SQLite é **configuração**, não código da ferramenta: ela chama `abrir(caminho,
formato)` e recebe um `RepositorioDeDocumentos`. A troca de formato lê tudo pela origem, grava tudo no
destino numa transação, confere por releitura e **só então** devolve o resultado; a origem nunca é tocada.
O arquivo anterior fica ao lado até o usuário confirmar (`descartar_anterior`), que o move para uma cópia
de quarentena em vez de apagá-lo.
"""

from dataclasses import dataclass
from pathlib import Path

from erpnext_brasil.persistencia.arquivos import quarentena
from erpnext_brasil.persistencia.documentos import (
	PersistenciaInvalida,
	RepositorioDeDocumentos,
	migrar,
)
from erpnext_brasil.persistencia.json_arquivo import RepositorioJson
from erpnext_brasil.persistencia.sqlite_arquivo import RepositorioSqlite

__all__ = [
	"FORMATOS",
	"ResultadoDaTroca",
	"abrir",
	"descartar_anterior",
	"extensao_do_formato",
	"trocar_formato",
]

FORMATOS = ("json", "sqlite")
_EXTENSAO = {"json": ".json", "sqlite": ".sqlite"}


def extensao_do_formato(formato: str) -> str:
	if formato not in _EXTENSAO:
		raise PersistenciaInvalida(f"formato de persistência desconhecido: {formato!r} (use json ou sqlite)")

	return _EXTENSAO[formato]


def abrir(caminho: Path, formato: str, **opcoes) -> RepositorioDeDocumentos:
	extensao_do_formato(formato)

	if formato == "json":
		return RepositorioJson(Path(caminho), **opcoes)

	return RepositorioSqlite(Path(caminho), **opcoes)


@dataclass(frozen=True)
class ResultadoDaTroca:
	total: int
	origem: Path
	destino: Path
	formato_destino: str


def trocar_formato(
	origem: Path, formato_origem: str, destino: Path, formato_destino: str
) -> ResultadoDaTroca:
	"""Migra `origem` para `destino`. Pré-condição: caminhos diferentes, e a origem existe.

	O destino deve estar vazio ou ser um subconjunto da origem (assim repetir a troca é idempotente).
	Qualquer falha deixa a origem intacta e utilizável.
	"""
	origem, destino = Path(origem), Path(destino)

	if origem.resolve() == destino.resolve():
		raise PersistenciaInvalida("origem e destino precisam ser arquivos diferentes")

	if not origem.exists():
		raise PersistenciaInvalida(f"{origem} não existe; não há o que migrar")

	total = migrar(abrir(origem, formato_origem), abrir(destino, formato_destino))

	return ResultadoDaTroca(total, origem, destino, formato_destino)


def descartar_anterior(arquivo_anterior: Path) -> Path:
	"""Depois que o usuário confirma a troca: move o arquivo do formato anterior para a quarentena."""
	return quarentena(Path(arquivo_anterior))
