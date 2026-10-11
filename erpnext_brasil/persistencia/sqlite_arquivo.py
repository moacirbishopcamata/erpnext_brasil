# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Adaptador SQLite: transação e trava entre processos pelo próprio banco, sem servidor.

Esquema versionado por `PRAGMA user_version`. Na abertura, um arquivo de esquema **anterior** recebe as
migrações numeradas dentro de uma transação (ou fica intacto se alguma falhar); um de esquema **posterior**
ao que a ferramenta conhece só abre para leitura (`EsquemaMaisNovo` para gravar). Arquivo que não é um
banco SQLite é `ArquivoIlegivel` e nunca é sobrescrito.

O esquema tem uma única tabela, `documentos(colecao, chave, json)`: nenhuma coluna é destinada a senha ou
segredo, e `validar_documento` barra chaves de segredo antes de gravar. Cada operação abre a sua conexão,
o que dispensa pensar em threads; a trava entre processos é a do SQLite (`BEGIN IMMEDIATE`), com espera.

Leitura somente leitura (`somente_leitura=True`) usa `mode=ro`, pensada para a interface do Windows lendo o
arquivo do WSL; num compartilhamento de rede o modo WAL pode exigir escrita no arquivo auxiliar, e por isso
existe também `imutavel=True` (instantâneo, sem trava), a opção para ler um arquivo que ninguém está gravando.
"""

import json
import sqlite3
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

from erpnext_brasil.persistencia.documentos import (
	ArquivoIlegivel,
	Documento,
	EsquemaMaisNovo,
	PersistenciaInvalida,
	validar_documento,
	validar_nome,
)

__all__ = ["ESQUEMA_ATUAL", "MIGRACOES", "RepositorioSqlite"]

MIGRACOES: dict[int, tuple[str, ...]] = {
	1: (
		"CREATE TABLE documentos ("
		" colecao TEXT NOT NULL,"
		" chave TEXT NOT NULL,"
		" json TEXT NOT NULL,"
		" PRIMARY KEY (colecao, chave)"
		") WITHOUT ROWID",
	),
}
"""Versão do esquema → instruções que a levam da anterior a ela. Só se acrescenta; nunca se reescreve."""

ESQUEMA_ATUAL = max(MIGRACOES)


class RepositorioSqlite:
	formato = "sqlite"

	def __init__(
		self,
		caminho: Path,
		*,
		somente_leitura: bool = False,
		imutavel: bool = False,
		migracoes: Mapping[int, tuple[str, ...]] = MIGRACOES,
		espera: float = 5.0,
	):
		self.caminho = Path(caminho)
		self._somente_leitura = somente_leitura or imutavel
		self._imutavel = imutavel
		self._migracoes = dict(migracoes)
		self._atual = max(self._migracoes)
		self._espera = espera
		self._conexao: sqlite3.Connection | None = None

	# ------------------------------------------------------------------ conexão

	def _com_espera(self, acao):
		"""Repete a ação enquanto o banco responde "locked": a conversão para WAL e a primeira migração pedem
		trava exclusiva, e o tempo de espera da conexão não as cobre quando várias conexões criam o banco juntas."""
		limite = time.monotonic() + self._espera

		while True:
			try:
				return acao()
			except sqlite3.OperationalError as erro:
				if "locked" not in str(erro) or time.monotonic() >= limite:
					raise

				time.sleep(0.01)

	def _abrir(self) -> sqlite3.Connection:
		if self._somente_leitura:
			sufixo = "?mode=ro&immutable=1" if self._imutavel else "?mode=ro"
			conexao = sqlite3.connect(
				self.caminho.resolve().as_uri() + sufixo, uri=True, timeout=self._espera, isolation_level=None
			)
		else:
			self.caminho.parent.mkdir(parents=True, exist_ok=True)
			conexao = sqlite3.connect(self.caminho, timeout=self._espera, isolation_level=None)

		try:
			return self._preparar(conexao)
		except BaseException:
			conexao.close()
			raise

	def _preparar(self, conexao: sqlite3.Connection) -> sqlite3.Connection:
		try:
			versao = conexao.execute("PRAGMA user_version").fetchone()[0]
		except sqlite3.DatabaseError as erro:
			raise ArquivoIlegivel(self.caminho, str(erro)) from erro

		if versao > self._atual:
			if not self._somente_leitura:
				raise EsquemaMaisNovo(
					f"{self.caminho.name} está na versão de esquema {versao}; esta ferramenta conhece até {self._atual}"
				)

			return conexao

		if not self._somente_leitura:
			self._com_espera(lambda: conexao.execute("PRAGMA journal_mode=WAL"))
			conexao.execute("PRAGMA foreign_keys=ON")
			self._com_espera(lambda: self._migrar(conexao, versao))

		return conexao

	def _migrar(self, conexao: sqlite3.Connection, versao: int) -> None:
		if versao >= self._atual:
			return

		conexao.execute("BEGIN IMMEDIATE")

		try:
			# Relê a versão **dentro** da transação: outra conexão pode ter migrado entre a leitura e a trava
			# (várias ferramentas abrindo o banco novo ao mesmo tempo), e repetir a migração falharia.
			versao = conexao.execute("PRAGMA user_version").fetchone()[0]

			for destino in range(versao + 1, self._atual + 1):
				for instrucao in self._migracoes[destino]:
					conexao.execute(instrucao)

				conexao.execute(f"PRAGMA user_version = {int(destino)}")

			conexao.execute("COMMIT")
		except BaseException:
			conexao.execute("ROLLBACK")
			raise

	@contextmanager
	def _usar(self) -> Iterator[sqlite3.Connection]:
		"""A conexão da transação em curso, ou uma própria só para esta operação."""
		if self._conexao is not None:
			yield self._conexao
			return

		conexao = self._abrir()

		try:
			yield conexao
		finally:
			conexao.close()

	def _tabela_existe(self, conexao: sqlite3.Connection) -> bool:
		return (
			conexao.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='documentos'").fetchone()
			is not None
		)

	def _existe(self) -> bool:
		return self.caminho.exists()

	# ------------------------------------------------------------------ leitura

	def obter(self, colecao: str, chave: str) -> Documento | None:
		validar_nome(colecao, "a coleção")
		validar_nome(chave, "a chave")

		if self._somente_leitura and not self._existe():
			return None

		with self._usar() as conexao:
			if not self._tabela_existe(conexao):
				return None

			linha = conexao.execute(
				"SELECT json FROM documentos WHERE colecao = ? AND chave = ?", (colecao, chave)
			).fetchone()

		return json.loads(linha[0]) if linha else None

	def listar(self, colecao: str) -> list[tuple[str, Documento]]:
		validar_nome(colecao, "a coleção")

		if self._somente_leitura and not self._existe():
			return []

		with self._usar() as conexao:
			if not self._tabela_existe(conexao):
				return []

			linhas = conexao.execute(
				"SELECT chave, json FROM documentos WHERE colecao = ? ORDER BY chave", (colecao,)
			).fetchall()

		return [(chave, json.loads(bruto)) for chave, bruto in linhas]

	def colecoes(self) -> list[str]:
		if self._somente_leitura and not self._existe():
			return []

		with self._usar() as conexao:
			if not self._tabela_existe(conexao):
				return []

			return [
				linha[0]
				for linha in conexao.execute("SELECT DISTINCT colecao FROM documentos ORDER BY colecao")
			]

	def versao_do_esquema(self) -> int:
		if self._somente_leitura and not self._existe():
			return 0

		with self._usar() as conexao:
			return conexao.execute("PRAGMA user_version").fetchone()[0]

	# ------------------------------------------------------------------ escrita

	@contextmanager
	def transacao(self) -> Iterator[None]:
		if self._conexao is not None:
			raise PersistenciaInvalida("transação aninhada não é permitida")

		if self._somente_leitura:
			raise PersistenciaInvalida("repositório aberto somente para leitura")

		conexao = self._abrir()
		self._conexao = conexao

		try:
			conexao.execute("BEGIN IMMEDIATE")

			try:
				yield
				conexao.execute("COMMIT")
			except BaseException:
				conexao.execute("ROLLBACK")
				raise
		finally:
			self._conexao = None
			conexao.close()

	def gravar(self, colecao: str, chave: str, documento: Documento) -> None:
		validar_nome(colecao, "a coleção")
		validar_nome(chave, "a chave")
		normalizado = json.dumps(validar_documento(documento), sort_keys=True, ensure_ascii=False)
		self._escrever(
			"INSERT INTO documentos (colecao, chave, json) VALUES (?, ?, ?)"
			" ON CONFLICT (colecao, chave) DO UPDATE SET json = excluded.json",
			(colecao, chave, normalizado),
		)

	def remover(self, colecao: str, chave: str) -> bool:
		validar_nome(colecao, "a coleção")
		validar_nome(chave, "a chave")

		return self._escrever("DELETE FROM documentos WHERE colecao = ? AND chave = ?", (colecao, chave)) > 0

	def _escrever(self, instrucao: str, parametros: tuple) -> int:
		if self._somente_leitura:
			raise PersistenciaInvalida("repositório aberto somente para leitura")

		if self._conexao is not None:
			return self._conexao.execute(instrucao, parametros).rowcount

		with self.transacao():
			return self._conexao.execute(instrucao, parametros).rowcount
