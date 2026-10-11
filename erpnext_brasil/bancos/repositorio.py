# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Os perfis de banco do bench: a regra do Cherry sobre a porta de persistência.

O `PerfisDeBanco` é o **único escritor** dos perfis; o Soda e o Chantilly os leem por `LeitorDePerfis`
(`perfis.py`). Não sabe se o armazenamento é JSON, SQLite ou memória, e não toca o `common_site_config.json`: quem
grava o padrão lá é a função `publicar_padrao`, injetada (o Cherry passa a que escreve o arquivo). Assim a regra é
testável sem bench nenhum.

Contratos
---------
- **Pré-condição:** nome válido e único sem diferença de maiúsculas; tipo, host, porta e usuário válidos.
- **Invariante:** com ao menos um perfil, **exatamente um** é o padrão. Remover o padrão com outros perfis existindo
  é recusado (escolha outro antes). Um perfil em uso por instância não é removido, nem muda de tipo, host ou porta.
- **Pós-condição:** o que um repositório grava, outro relê; o padrão publicado é o gravado. Nenhum perfil guarda
  senha (o modelo não tem o campo).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from erpnext_brasil.bancos.modelo import (
	TIPOS,
	PerfilDeBanco,
	PerfilInvalido,
	UltimoTeste,
	chave_do_nome,
)
from erpnext_brasil.persistencia.documentos import RepositorioDeDocumentos

__all__ = [
	"CHAVE_META",
	"COLECAO_META",
	"COLECAO_PERFIS",
	"ESQUEMA",
	"NomeRepetido",
	"PerfilEmUso",
	"PerfilInexistente",
	"PerfisDeBanco",
	"PerfisMaisNovos",
	"SemPadrao",
	"Uso",
	"adotar_configuracao_existente",
]

ESQUEMA = 1
COLECAO_PERFIS = "perfis"
COLECAO_META = "meta"
CHAVE_META = "esquema"


@dataclass(frozen=True)
class Uso:
	"""Uma instância do Soda que usa um perfil: o descritivo e o UUID abreviado, que é o que se diz ao usuário."""

	descritivo: str
	uuid_abreviado: str

	def __str__(self) -> str:
		return f"{self.descritivo} ({self.uuid_abreviado})"


class NomeRepetido(ValueError):
	def __init__(self, existente: PerfilDeBanco):
		super().__init__(f'já existe o perfil "{existente.nome}" (a comparação ignora maiúsculas)')
		self.existente = existente


class PerfilInexistente(LookupError):
	pass


class SemPadrao(ValueError):
	"""A operação removeria o padrão com outros perfis existindo."""


class PerfilEmUso(ValueError):
	def __init__(self, nome: str, acao: str, usos: Sequence[Uso]):
		lista = ", ".join(str(uso) for uso in usos)
		super().__init__(
			f'o perfil "{nome}" é usado por {len(usos)} instância(s) do Soda: {lista}; não é possível {acao}'
		)
		self.usos = tuple(usos)


class PerfisMaisNovos(RuntimeError):
	"""Os perfis foram gravados por uma versão mais nova do Cherry; esta não grava neles."""


def _agora_utc() -> datetime:
	return datetime.now(timezone.utc)


def _sem_usos(nome: str) -> Sequence[Uso]:
	return ()


def _nao_publica(perfil: PerfilDeBanco) -> None:
	return None


class PerfisDeBanco:
	def __init__(
		self,
		repositorio: RepositorioDeDocumentos,
		*,
		usos: Callable[[str], Sequence[Uso]] = _sem_usos,
		publicar_padrao: Callable[[PerfilDeBanco], None] = _nao_publica,
		agora: Callable[[], datetime] = _agora_utc,
	):
		self._repo = repositorio
		self._usos = usos
		self._publicar = publicar_padrao
		self._agora = agora

	# ------------------------------------------------------------------ leitura (reconstituição fresca)

	def listar(self) -> list[PerfilDeBanco]:
		perfis = [PerfilDeBanco.de_documento(doc) for _, doc in self._repo.listar(COLECAO_PERFIS)]

		return sorted(perfis, key=lambda p: p.chave)

	def obter(self, nome: str) -> PerfilDeBanco | None:
		documento = self._repo.obter(COLECAO_PERFIS, chave_do_nome(nome))

		return PerfilDeBanco.de_documento(documento) if documento is not None else None

	def padrao(self) -> PerfilDeBanco | None:
		return next((p for p in self.listar() if p.padrao), None)

	def versao_do_esquema(self) -> int:
		meta = self._repo.obter(COLECAO_META, CHAVE_META)
		versao = meta.get("versao_esquema") if isinstance(meta, dict) else None

		return versao if isinstance(versao, int) and not isinstance(versao, bool) else ESQUEMA

	# ------------------------------------------------------------------ escrita (sempre dentro da transação)

	def _exigir_gravavel(self) -> None:
		if self.versao_do_esquema() > ESQUEMA:
			raise PerfisMaisNovos(
				f"os perfis estão na versão de esquema {self.versao_do_esquema()} e esta versão do Cherry conhece "
				f"até {ESQUEMA}; atualize o Cherry antes de alterá-los"
			)

	def _gravar(self, perfil: PerfilDeBanco) -> PerfilDeBanco:
		self._repo.gravar(COLECAO_PERFIS, perfil.chave, perfil.para_documento())

		return perfil

	def _exigir(self, nome: str) -> PerfilDeBanco:
		perfil = self.obter(nome)

		if perfil is None:
			raise PerfilInexistente(f'não existe o perfil "{nome}"')

		return perfil

	def criar(
		self,
		nome: str,
		tipo: str,
		host: str = "127.0.0.1",
		porta: int = 0,
		usuario_root: str = "",
		*,
		publicar: bool = True,
	) -> PerfilDeBanco:
		"""Cria um perfil. O primeiro perfil do bench nasce como padrão e, com `publicar`, é publicado."""
		novo = PerfilDeBanco(nome, tipo, host, porta, usuario_root)

		with self._repo.transacao():
			self._exigir_gravavel()
			existente = self.obter(nome)

			if existente is not None:
				raise NomeRepetido(existente)

			primeiro = not self.listar()
			criado = self._gravar(replace(novo, padrao=primeiro))

			if self._repo.obter(COLECAO_META, CHAVE_META) is None:
				self._repo.gravar(COLECAO_META, CHAVE_META, {"versao_esquema": ESQUEMA})

		if primeiro and publicar:
			self._publicar(criado)

		return criado

	def alterar(
		self,
		nome: str,
		*,
		tipo: str | None = None,
		host: str | None = None,
		porta: int | None = None,
		usuario_root: str | None = None,
	) -> PerfilDeBanco:
		"""Altera o que for passado. Tipo, host ou porta de perfil em uso não mudam: apontariam as instâncias a outro servidor."""
		with self._repo.transacao():
			self._exigir_gravavel()
			atual = self._exigir(nome)
			novo = PerfilDeBanco(
				atual.nome,
				atual.tipo if tipo is None else tipo,
				atual.host if host is None else host,
				atual.porta if porta is None else porta,
				atual.usuario_root if usuario_root is None else usuario_root,
				atual.padrao,
				atual.ultimo_teste,
			)

			if novo.servidor != atual.servidor:
				usos = self._usos(atual.nome)

				if usos:
					raise PerfilEmUso(atual.nome, "trocar o tipo, o servidor ou a porta", usos)

				novo = replace(novo, ultimo_teste=None)  # o teste antigo era de outro servidor

			self._gravar(novo)

		if novo.padrao:
			self._publicar(novo)

		return novo

	def definir_padrao(self, nome: str) -> PerfilDeBanco:
		"""Torna o perfil o padrão: o anterior deixa de ser, e o novo é publicado no `common_site_config.json`."""
		with self._repo.transacao():
			self._exigir_gravavel()
			alvo = self._exigir(nome)

			for perfil in self.listar():
				if perfil.padrao and perfil.chave != alvo.chave:
					self._gravar(replace(perfil, padrao=False))

			alvo = self._gravar(replace(alvo, padrao=True))

		self._publicar(alvo)

		return alvo

	def remover(self, nome: str) -> None:
		with self._repo.transacao():
			self._exigir_gravavel()
			alvo = self._exigir(nome)
			usos = self._usos(alvo.nome)

			if usos:
				raise PerfilEmUso(alvo.nome, "removê-lo", usos)

			if alvo.padrao and len(self.listar()) > 1:
				raise SemPadrao(
					f'o perfil "{alvo.nome}" é o padrão; defina outro perfil como padrão antes de removê-lo'
				)

			self._repo.remover(COLECAO_PERFIS, alvo.chave)

	def registrar_teste(self, nome: str, *, ok: bool, nivel: str) -> PerfilDeBanco:
		"""Guarda o resultado do último teste: data, nível e sucesso. A senha usada nunca chega até aqui."""
		with self._repo.transacao():
			self._exigir_gravavel()
			atual = self._exigir(nome)

			return self._gravar(
				replace(atual, ultimo_teste=UltimoTeste(self._agora().isoformat(), nivel, ok))
			)


def adotar_configuracao_existente(
	perfis: PerfisDeBanco, common_site_config: Mapping[str, Any], nome: str = "padrao"
) -> PerfilDeBanco | None:
	"""Na primeira abertura de um bench que já tem banco configurado e nenhum perfil, cria o perfil padrão a partir
	do `common_site_config.json`, **sem alterar o arquivo** (a leitura é por mapeamento e nada é publicado de volta).

	Devolve o perfil criado, ou `None` quando já há perfis ou a configuração não tem banco reconhecível.
	"""
	tipo = common_site_config.get("db_type")

	if perfis.listar() or tipo not in TIPOS:
		return None

	porta = common_site_config.get("db_port")

	try:
		return perfis.criar(
			nome,
			tipo,
			common_site_config.get("db_host") or "127.0.0.1",
			porta if isinstance(porta, int) and not isinstance(porta, bool) else 0,
			common_site_config.get("root_login") or "",
			publicar=False,
		)
	except PerfilInvalido:
		return None
