# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Adaptador JSON: um arquivo legível, gravado de forma atômica e protegido por trava entre processos.

Formato: `{"formato": "documentos", "versao_esquema": 1, "colecoes": {colecao: {chave: documento}}}`,
com `indent=1` e chaves ordenadas, o mesmo estilo dos arquivos do Frappe, para que um olho humano (e o
`git diff`) leia sem ferramenta. Arquivo **ausente** é repositório vazio (estado normal de quem acabou de
instalar); arquivo **ilegível** nunca é sobrescrito (`ArquivoIlegivel`).

Uma instância não é segura entre threads; cada thread ou processo abre a sua. A consistência entre elas
vem da trava em arquivo (`<arquivo>.trava`) e da troca atômica do arquivo.
"""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from erpnext_brasil.persistencia.arquivos import Trava, escrever_atomico
from erpnext_brasil.persistencia.documentos import (
	ArquivoIlegivel,
	Documento,
	EsquemaMaisNovo,
	PersistenciaInvalida,
	validar_documento,
	validar_nome,
)

__all__ = ["ESQUEMA_ATUAL", "RepositorioJson"]

ESQUEMA_ATUAL = 1
FORMATO = "documentos"


class RepositorioJson:
	formato = "json"

	def __init__(self, caminho: Path, *, espera_da_trava: float = 5.0):
		self.caminho = Path(caminho)
		self._espera = espera_da_trava
		self._estado: dict[str, dict[str, Documento]] | None = None

	# ------------------------------------------------------------------ leitura do arquivo

	def _ler(self) -> tuple[int, dict[str, dict[str, Documento]]]:
		if not self.caminho.exists():
			return ESQUEMA_ATUAL, {}

		try:
			bruto = json.loads(self.caminho.read_text(encoding="utf-8"))
		except (OSError, ValueError) as erro:
			raise ArquivoIlegivel(self.caminho, str(erro)) from erro

		if not isinstance(bruto, dict) or not isinstance(bruto.get("colecoes"), dict):
			raise ArquivoIlegivel(self.caminho, "não tem o formato de documentos esperado")

		versao = bruto.get("versao_esquema")

		if not isinstance(versao, int):
			raise ArquivoIlegivel(self.caminho, "sem versão de esquema")

		return versao, bruto["colecoes"]

	def _dados(self) -> dict[str, dict[str, Documento]]:
		return self._estado if self._estado is not None else self._ler()[1]

	# ------------------------------------------------------------------ leitura

	def obter(self, colecao: str, chave: str) -> Documento | None:
		validar_nome(colecao, "a coleção")
		validar_nome(chave, "a chave")
		documento = self._dados().get(colecao, {}).get(chave)

		return json.loads(json.dumps(documento)) if documento is not None else None

	def listar(self, colecao: str) -> list[tuple[str, Documento]]:
		validar_nome(colecao, "a coleção")
		documentos = self._dados().get(colecao, {})

		return [(chave, json.loads(json.dumps(documentos[chave]))) for chave in sorted(documentos)]

	def colecoes(self) -> list[str]:
		return sorted(nome for nome, documentos in self._dados().items() if documentos)

	def versao_do_esquema(self) -> int:
		return self._ler()[0]

	# ------------------------------------------------------------------ escrita

	@contextmanager
	def transacao(self) -> Iterator[None]:
		if self._estado is not None:
			raise PersistenciaInvalida("transação aninhada não é permitida")

		with Trava(self.caminho.with_name(self.caminho.name + ".trava"), espera=self._espera):
			versao, colecoes = self._ler()

			if versao > ESQUEMA_ATUAL:
				raise EsquemaMaisNovo(
					f"{self.caminho.name} está na versão de esquema {versao}; esta ferramenta conhece até {ESQUEMA_ATUAL}"
				)

			self._estado = colecoes

			try:
				yield
				self._gravar(colecoes)
			finally:
				self._estado = None

	def _gravar(self, colecoes: dict[str, dict[str, Documento]]) -> None:
		limpas = {nome: documentos for nome, documentos in colecoes.items() if documentos}
		texto = json.dumps(
			{"formato": FORMATO, "versao_esquema": ESQUEMA_ATUAL, "colecoes": limpas},
			indent=1,
			sort_keys=True,
			ensure_ascii=False,
		)
		escrever_atomico(self.caminho, texto + "\n")

	def gravar(self, colecao: str, chave: str, documento: Documento) -> None:
		validar_nome(colecao, "a coleção")
		validar_nome(chave, "a chave")
		normalizado = validar_documento(documento)

		if self._estado is not None:
			self._estado.setdefault(colecao, {})[chave] = normalizado
			return

		with self.transacao():
			self._estado.setdefault(colecao, {})[chave] = normalizado

	def remover(self, colecao: str, chave: str) -> bool:
		validar_nome(colecao, "a coleção")
		validar_nome(chave, "a chave")

		if self._estado is not None:
			return self._estado.get(colecao, {}).pop(chave, None) is not None

		with self.transacao():
			return self._estado.get(colecao, {}).pop(chave, None) is not None
