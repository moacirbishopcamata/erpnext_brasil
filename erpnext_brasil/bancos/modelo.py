# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""O perfil de banco de dados: o que o Cherry configura e o Soda e o Chantilly consomem.

Um perfil é uma configuração nomeada de servidor de banco (MariaDB ou PostgreSQL): tipo, host, porta e usuário
administrador. **Não tem campo de senha, de propósito**: a senha é informada na hora do teste ou da criação do site e
nunca é persistida (mudança `cherry-perfis-de-banco`). `de_documento` ignora qualquer chave desconhecida, o que inclui
uma eventual `senha` gravada por engano à mão: ela não entra no objeto.

`PerfilDeBanco` é imutável; quem muda um perfil é o `PerfisDeBanco` (repositório), que guarda as regras.
"""

import re
from dataclasses import dataclass
from typing import Any

__all__ = [
	"MARIADB",
	"NIVEIS_DE_TESTE",
	"PORTA_PADRAO",
	"POSTGRES",
	"TIPOS",
	"PerfilDeBanco",
	"PerfilInvalido",
	"UltimoTeste",
	"chave_do_nome",
	"validar_nome_do_perfil",
]

MARIADB = "mariadb"
POSTGRES = "postgres"
TIPOS = (MARIADB, POSTGRES)
PORTA_PADRAO = {MARIADB: 3306, POSTGRES: 5432}
NIVEIS_DE_TESTE = ("autenticacao", "tcp")
"""Os níveis do teste de conexão do Cherry, do mais forte ao mais fraco."""

TAMANHO_MAXIMO_DO_NOME = 60
_NOME = re.compile(r"[A-Za-z0-9_.\-]{1,60}")
_SEGURO = re.compile(r"[A-Za-z0-9._:@\-]+")
_MAXIMO_TEXTO = 200


class PerfilInvalido(ValueError):
	"""Um perfil, ou um documento de perfil, não respeita as pré-condições."""


def validar_nome_do_perfil(nome: Any) -> str:
	"""O nome do perfil: letras, dígitos, ponto, hífen e sublinhado, de 1 a 60 (é o que o Soda grava na instância)."""
	if not isinstance(nome, str) or not _NOME.fullmatch(nome):
		raise PerfilInvalido(
			f"o nome do perfil precisa ter de 1 a {TAMANHO_MAXIMO_DO_NOME} caracteres entre letras, dígitos, "
			f"ponto, hífen e sublinhado, recebido {nome!r}"
		)

	return nome


def chave_do_nome(nome: str) -> str:
	"""A forma comparável do nome: sem diferença de maiúsculas."""
	return validar_nome_do_perfil(nome).casefold()


@dataclass(frozen=True)
class UltimoTeste:
	"""O resultado do último teste de conexão: data, nível alcançado e sucesso. Nunca a senha usada."""

	quando: str
	nivel: str
	ok: bool

	def para_documento(self) -> dict[str, Any]:
		return {"quando": self.quando, "nivel": self.nivel, "ok": self.ok}

	@classmethod
	def de_documento(cls, documento: Any) -> "UltimoTeste":
		if not isinstance(documento, dict):
			raise PerfilInvalido("o último teste precisa ser um objeto")

		quando, nivel, ok = documento.get("quando"), documento.get("nivel"), documento.get("ok")

		if (
			not isinstance(quando, str)
			or not quando
			or not isinstance(nivel, str)
			or not isinstance(ok, bool)
		):
			raise PerfilInvalido("o último teste precisa de data, nível e resultado")

		return cls(quando, nivel[:_MAXIMO_TEXTO], ok)


def _texto_seguro(valor: Any, o_que: str, *, vazio_ok: bool = False) -> str:
	if not isinstance(valor, str):
		raise PerfilInvalido(f"{o_que} precisa ser um texto")

	valor = valor.strip()

	if not valor and vazio_ok:
		return valor

	if not valor or len(valor) > _MAXIMO_TEXTO or not _SEGURO.fullmatch(valor):
		raise PerfilInvalido(f"{o_que} tem caracteres que não são aceitos: {valor!r}")

	return valor


@dataclass(frozen=True)
class PerfilDeBanco:
	nome: str
	tipo: str
	host: str = "127.0.0.1"
	porta: int = 0
	usuario_root: str = ""
	padrao: bool = False
	ultimo_teste: UltimoTeste | None = None

	def __post_init__(self):
		validar_nome_do_perfil(self.nome)

		if self.tipo not in TIPOS:
			raise PerfilInvalido(
				f"tipo de banco desconhecido: {self.tipo!r} (use {MARIADB!r} ou {POSTGRES!r})"
			)

		object.__setattr__(self, "host", _texto_seguro(self.host, "o servidor"))
		object.__setattr__(self, "usuario_root", _texto_seguro(self.usuario_root, "o usuário", vazio_ok=True))
		porta = self.porta or PORTA_PADRAO[self.tipo]

		if isinstance(porta, bool) or not isinstance(porta, int) or not 1 <= porta <= 65535:
			raise PerfilInvalido(f"a porta precisa ser um inteiro de 1 a 65535, recebido {self.porta!r}")

		object.__setattr__(self, "porta", porta)

	@property
	def chave(self) -> str:
		return chave_do_nome(self.nome)

	@property
	def servidor(self) -> tuple[str, str, int]:
		"""O que identifica o servidor: trocar qualquer parte disso muda para onde as instâncias apontam."""
		return (self.tipo, self.host, self.porta)

	def chaves_common_config(self) -> dict[str, Any]:
		"""As chaves que o `bench new-site` lê do `common_site_config.json`. Nunca `root_password`."""
		chaves: dict[str, Any] = {"db_type": self.tipo, "db_host": self.host, "db_port": self.porta}

		if self.usuario_root:
			chaves["root_login"] = self.usuario_root

		return chaves

	def para_documento(self) -> dict[str, Any]:
		return {
			"nome": self.nome,
			"tipo": self.tipo,
			"host": self.host,
			"porta": self.porta,
			"usuario_root": self.usuario_root,
			"padrao": self.padrao,
			"ultimo_teste": self.ultimo_teste.para_documento() if self.ultimo_teste else None,
		}

	@classmethod
	def de_documento(cls, documento: Any) -> "PerfilDeBanco":
		if not isinstance(documento, dict):
			raise PerfilInvalido(f"o perfil precisa ser um objeto, recebido {type(documento).__name__}")

		porta = documento.get("porta")

		if isinstance(porta, bool) or not isinstance(porta, int):
			raise PerfilInvalido(f"a porta precisa ser um inteiro, recebido {porta!r}")

		teste = documento.get("ultimo_teste")

		return cls(
			nome=documento.get("nome"),
			tipo=documento.get("tipo"),
			host=documento.get("host"),
			porta=porta,
			usuario_root=documento.get("usuario_root", ""),
			padrao=documento.get("padrao") is True,
			ultimo_teste=UltimoTeste.de_documento(teste) if teste is not None else None,
		)
