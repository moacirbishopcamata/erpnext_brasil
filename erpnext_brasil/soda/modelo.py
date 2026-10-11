# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""O que é uma instância para o Soda: dados imutáveis, estados e as transições permitidas.

`Instancia` e `Aposentada` são `dataclass(frozen=True)`: quem lê o registro recebe uma reconstituição fresca, e
ninguém segura referência para mudar o objeto por conta própria (imutabilidade de fronteira). A mudança de
estado é do `Registro`, que guarda as transições.

Documentos: `para_documento` e `de_documento` são a costura entre o objeto de domínio e a forma de
persistência. `de_documento` é **estrito** nos campos que conhece e **ignora campos desconhecidos**, para que
um registro gravado por uma versão mais nova do Soda continue identificável por uma mais antiga (contrato de
identidade: campo novo não quebra leitor).
"""

import enum
import re
from dataclasses import dataclass
from typing import Any

from erpnext_brasil.soda import identidade as ident

__all__ = [
	"APLICATIVOS_OBRIGATORIOS",
	"APLICATIVOS_OPCIONAIS",
	"ESTADOS_COM_PROCESSO",
	"ESTADOS_QUE_IMPEDEM_REMOVER",
	"TIPOS_DE_BANCO",
	"TRANSICOES",
	"TRANSICOES_DA_CONCILIACAO",
	"Aposentada",
	"DocumentoInvalido",
	"Estado",
	"Instancia",
]

TIPOS_DE_BANCO = ("mariadb", "postgres")
APLICATIVOS_OBRIGATORIOS = ("erpnext", "erpnext_brasil")
"""O ERPNext Brasil é o ERPNext inteiro mais a tropicalização: toda instância tem os dois."""
APLICATIVOS_OPCIONAIS = ("hrms", "healthcare")

_NOME_DE_PERFIL = re.compile(r"[A-Za-z0-9_.\-]{1,200}")
_APP = re.compile(r"[a-z][a-z0-9_]{0,60}")


class DocumentoInvalido(ValueError):
	"""Um documento do registro não tem a forma de uma instância."""


class Estado(str, enum.Enum):
	CRIANDO = "criando"
	PARADA = "parada"
	SUBINDO = "subindo"
	NO_AR = "no_ar"
	CAIU = "caiu"
	FALHOU_AO_SUBIR = "falhou_ao_subir"
	CRIACAO_INTERROMPIDA = "criacao_interrompida"


TRANSICOES: dict[Estado, frozenset[Estado]] = {
	Estado.CRIANDO: frozenset({Estado.PARADA, Estado.CRIACAO_INTERROMPIDA}),
	Estado.PARADA: frozenset({Estado.SUBINDO}),
	Estado.SUBINDO: frozenset({Estado.NO_AR, Estado.FALHOU_AO_SUBIR, Estado.PARADA}),
	Estado.NO_AR: frozenset({Estado.PARADA, Estado.CAIU}),
	Estado.CAIU: frozenset({Estado.SUBINDO, Estado.PARADA}),
	Estado.FALHOU_AO_SUBIR: frozenset({Estado.SUBINDO, Estado.PARADA}),
	Estado.CRIACAO_INTERROMPIDA: frozenset(),
}
"""Ações do usuário: o que cada estado permite fazer a seguir. Criação interrompida só se desfaz."""

TRANSICOES_DA_CONCILIACAO: dict[Estado, frozenset[Estado]] = {
	Estado.CRIANDO: frozenset({Estado.CRIACAO_INTERROMPIDA}),
	Estado.PARADA: frozenset({Estado.NO_AR}),
	Estado.SUBINDO: frozenset({Estado.NO_AR, Estado.FALHOU_AO_SUBIR}),
	Estado.NO_AR: frozenset({Estado.CAIU}),
	Estado.CAIU: frozenset({Estado.NO_AR}),
	Estado.FALHOU_AO_SUBIR: frozenset({Estado.NO_AR}),
	Estado.CRIACAO_INTERROMPIDA: frozenset(),
}
"""O que a conciliação com a realidade pode constatar, além das ações do usuário (por exemplo, "caiu")."""

ESTADOS_COM_PROCESSO = frozenset({Estado.SUBINDO, Estado.NO_AR})
ESTADOS_QUE_IMPEDEM_REMOVER = frozenset({Estado.SUBINDO, Estado.NO_AR, Estado.CRIANDO})


def _texto(documento: dict[str, Any], campo: str) -> str:
	valor = documento.get(campo)

	if not isinstance(valor, str) or not valor:
		raise DocumentoInvalido(f"o campo {campo!r} precisa ser um texto não vazio")

	return valor


@dataclass(frozen=True)
class Instancia:
	uuid: str
	descritivo: str
	host: str
	porta: int
	estado: Estado
	perfil_de_banco: str
	tipo_de_banco: str
	aplicativos: tuple[str, ...]
	criada_em: str
	expoe_na_rede: bool = False

	@property
	def abreviado(self) -> str:
		return ident.abreviar(self.uuid)

	@property
	def chave(self) -> str:
		"""A forma comparável do descritivo (sem acento nem caixa)."""
		return ident.chave_de_unicidade(self.descritivo)

	def para_documento(self) -> dict[str, Any]:
		return {
			"uuid": self.uuid,
			"descritivo": self.descritivo,
			"host": self.host,
			"porta": self.porta,
			"estado": self.estado.value,
			"perfil_de_banco": self.perfil_de_banco,
			"tipo_de_banco": self.tipo_de_banco,
			"aplicativos": list(self.aplicativos),
			"criada_em": self.criada_em,
			"expoe_na_rede": self.expoe_na_rede,
		}

	@classmethod
	def de_documento(cls, documento: Any) -> "Instancia":
		if not isinstance(documento, dict):
			raise DocumentoInvalido(f"a instância precisa ser um objeto, recebido {type(documento).__name__}")

		try:
			identificador = ident.normalizar_uuid(_texto(documento, "uuid"))
			descritivo = ident.validar_descritivo(_texto(documento, "descritivo"))
		except (ident.UuidInvalido, ident.DescritivoInvalido) as erro:
			raise DocumentoInvalido(str(erro)) from erro

		porta = documento.get("porta")

		if isinstance(porta, bool) or not isinstance(porta, int) or not 1 <= porta <= 65535:
			raise DocumentoInvalido(f"a porta precisa ser um inteiro de 1 a 65535, recebido {porta!r}")

		try:
			estado = Estado(documento.get("estado"))
		except ValueError as erro:
			raise DocumentoInvalido(f"estado desconhecido: {documento.get('estado')!r}") from erro

		tipo = _texto(documento, "tipo_de_banco")

		if tipo not in TIPOS_DE_BANCO:
			raise DocumentoInvalido(f"tipo de banco desconhecido: {tipo!r}")

		perfil = _texto(documento, "perfil_de_banco")

		if not _NOME_DE_PERFIL.fullmatch(perfil):
			raise DocumentoInvalido(f"nome de perfil de banco inválido: {perfil!r}")

		aplicativos = documento.get("aplicativos")

		if (
			not isinstance(aplicativos, list)
			or not aplicativos
			or not all(isinstance(a, str) and _APP.fullmatch(a) for a in aplicativos)
		):
			raise DocumentoInvalido("os aplicativos precisam ser uma lista de nomes de aplicativo")

		return cls(
			uuid=identificador,
			descritivo=descritivo,
			host=_texto(documento, "host"),
			porta=porta,
			estado=estado,
			perfil_de_banco=perfil,
			tipo_de_banco=tipo,
			aplicativos=tuple(aplicativos),
			criada_em=_texto(documento, "criada_em"),
			expoe_na_rede=documento.get("expoe_na_rede") is True,
		)


@dataclass(frozen=True)
class Aposentada:
	"""O rastro de uma instância removida: o UUID nunca mais será reutilizado."""

	uuid: str
	ultimo_descritivo: str
	aposentada_em: str

	def para_documento(self) -> dict[str, Any]:
		return {
			"uuid": self.uuid,
			"ultimo_descritivo": self.ultimo_descritivo,
			"aposentada_em": self.aposentada_em,
		}

	@classmethod
	def de_documento(cls, documento: Any) -> "Aposentada":
		if not isinstance(documento, dict):
			raise DocumentoInvalido(
				f"a aposentada precisa ser um objeto, recebido {type(documento).__name__}"
			)

		try:
			identificador = ident.normalizar_uuid(_texto(documento, "uuid"))
		except ident.UuidInvalido as erro:
			raise DocumentoInvalido(str(erro)) from erro

		return cls(
			uuid=identificador,
			ultimo_descritivo=_texto(documento, "ultimo_descritivo"),
			aposentada_em=_texto(documento, "aposentada_em"),
		)
