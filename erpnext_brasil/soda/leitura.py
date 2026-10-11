# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""O contrato de identidade: o que o Cherry, o Chantilly e qualquer outra ferramenta podem ler do Soda.

O **Soda é o único escritor** da identidade das instâncias. Os demais só leem, por este leitor, que:

- **não tem operação de escrita** (nem `gravar`, nem `transacao`) e **não toma a trava de escrita**: ler durante
  uma criação devolve o último registro consistente (a escrita atômica garante que nunca se vê arquivo pela metade);
- **tolera campo novo**: uma versão posterior do Soda pode acrescentar campos sem quebrar este leitor;
- **informa versão de esquema mais nova** (`mais_nova`) em vez de recusar: mostra o que consegue identificar;
- **não explode com registro ruim**: instância malformada é pulada com aviso, arquivo ilegível devolve uma leitura
  vazia marcada como ilegível. Quem consome degrada, não quebra;
- lê **JSON ou SQLite** com o mesmo resultado.

Os campos lidos são só os da identidade (UUID, descritivo, host, porta, estado, banco). O `estado` é texto, e não o
`Enum` do Soda: um estado novo de uma versão futura continua identificável.

Também define a **identidade no `site_config`** de cada instância (`soda_instance_id` e `soda_descritivo`), que
permite reconhecer uma instância mesmo com o Soda fechado e de dentro do processo do Frappe.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from erpnext_brasil.persistencia.documentos import ArquivoIlegivel, EsquemaMaisNovo, RepositorioDeDocumentos
from erpnext_brasil.soda import identidade as ident
from erpnext_brasil.soda.configuracao import abrir_repositorio
from erpnext_brasil.soda.registro import (
	CHAVE_META,
	COLECAO_APOSENTADAS,
	COLECAO_INSTANCIAS,
	COLECAO_META,
	ESQUEMA,
)

__all__ = [
	"CHAVES_PROTEGIDAS",
	"CHAVE_DESCRITIVO",
	"CHAVE_UUID",
	"AposentadaLida",
	"IdentidadeDoSite",
	"InstanciaLida",
	"LeitorDeInstancias",
	"Leitura",
	"chaves_para_site_config",
	"identidade_do_site",
]

CHAVE_UUID = "soda_instance_id"
CHAVE_DESCRITIVO = "soda_descritivo"
CHAVES_PROTEGIDAS = (CHAVE_UUID, CHAVE_DESCRITIVO)
"""As ferramentas consumidoras nunca escrevem nestas chaves; só o Soda."""


@dataclass(frozen=True)
class InstanciaLida:
	uuid: str
	descritivo: str
	host: str
	porta: int
	estado: str
	tipo_de_banco: str
	perfil_de_banco: str
	criada_em: str

	@property
	def abreviado(self) -> str:
		return ident.abreviar(self.uuid)


@dataclass(frozen=True)
class AposentadaLida:
	uuid: str
	ultimo_descritivo: str
	aposentada_em: str


@dataclass(frozen=True)
class Leitura:
	instancias: tuple[InstanciaLida, ...] = ()
	aposentadas: tuple[AposentadaLida, ...] = ()
	versao_do_esquema: int = ESQUEMA
	mais_nova: bool = False
	"""O registro foi gravado por uma versão mais nova do Soda: leia o que der, não grave nada."""
	ilegivel: bool = False
	avisos: tuple[str, ...] = ()


@dataclass(frozen=True)
class IdentidadeDoSite:
	uuid: str
	descritivo: str


def identidade_do_site(site_config: Mapping[str, Any]) -> IdentidadeDoSite | None:
	"""A identidade de uma instância lida do `site_config` do site, ou `None` se o site não é de uma instância."""
	bruto = site_config.get(CHAVE_UUID)

	if bruto is None:
		return None

	try:
		identificador = ident.normalizar_uuid(bruto)
	except ident.UuidInvalido:
		return None

	descritivo = site_config.get(CHAVE_DESCRITIVO)

	return IdentidadeDoSite(identificador, descritivo if isinstance(descritivo, str) else "")


def chaves_para_site_config(identificador: str, descritivo: str) -> dict[str, str]:
	"""O que o Soda grava no `site_config` da instância."""
	return {
		CHAVE_UUID: ident.normalizar_uuid(identificador),
		CHAVE_DESCRITIVO: ident.validar_descritivo(descritivo),
	}


def _inteiro_valido(valor: Any) -> bool:
	return isinstance(valor, int) and not isinstance(valor, bool) and 1 <= valor <= 65535


def _texto(documento: Mapping[str, Any], campo: str, padrao: str = "") -> str:
	valor = documento.get(campo)

	return valor if isinstance(valor, str) else padrao


def _ler_instancia(chave: str, documento: Any) -> tuple[InstanciaLida | None, str | None]:
	"""Leitura tolerante: devolve a instância ou o aviso de por que foi pulada."""
	if not isinstance(documento, dict):
		return None, f"a instância {chave} não é um objeto; ignorada"

	try:
		identificador = ident.normalizar_uuid(documento.get("uuid"))
	except ident.UuidInvalido:
		return None, f"a instância {chave} tem UUID inválido; ignorada"

	descritivo = _texto(documento, "descritivo")

	if not descritivo or not _inteiro_valido(documento.get("porta")):
		return None, f"a instância {identificador} está sem descritivo ou com porta inválida; ignorada"

	return (
		InstanciaLida(
			uuid=identificador,
			descritivo=descritivo,
			host=_texto(documento, "host"),
			porta=documento["porta"],
			estado=_texto(documento, "estado", "desconhecido"),
			tipo_de_banco=_texto(documento, "tipo_de_banco"),
			perfil_de_banco=_texto(documento, "perfil_de_banco"),
			criada_em=_texto(documento, "criada_em"),
		),
		None,
	)


class LeitorDeInstancias:
	"""Somente leitura: não existe aqui nenhum método de escrita."""

	def __init__(self, repositorio: RepositorioDeDocumentos):
		self._repo = repositorio

	@classmethod
	def abrir(cls, pasta: Path) -> "LeitorDeInstancias":
		"""O leitor do registro da pasta do Soda, no formato em uso, aberto somente para leitura."""
		return cls(abrir_repositorio(pasta, somente_leitura=True))

	def ler(self) -> Leitura:
		avisos: list[str] = []

		try:
			meta = self._repo.obter(COLECAO_META, CHAVE_META)
			versao = meta.get("versao_esquema", ESQUEMA) if isinstance(meta, dict) else ESQUEMA
			documentos = self._repo.listar(COLECAO_INSTANCIAS)
			rastros = self._repo.listar(COLECAO_APOSENTADAS)
		except (ArquivoIlegivel, EsquemaMaisNovo) as erro:
			return Leitura(ilegivel=True, avisos=(str(erro),))

		if not isinstance(versao, int) or isinstance(versao, bool):
			avisos.append("a versão do esquema do registro é ilegível; tratada como a conhecida")
			versao = ESQUEMA

		mais_nova = versao > ESQUEMA

		if mais_nova:
			avisos.append(
				f"o registro está na versão de esquema {versao} e este leitor conhece até {ESQUEMA}; "
				"mostrando o que é identificável, sem gravar nada"
			)

		instancias = []

		for chave, documento in documentos:
			instancia, aviso = _ler_instancia(chave, documento)

			if aviso:
				avisos.append(aviso)
			else:
				instancias.append(instancia)

		aposentadas = []

		for chave, documento in rastros:
			try:
				aposentadas.append(
					AposentadaLida(
						uuid=ident.normalizar_uuid(documento.get("uuid")),
						ultimo_descritivo=_texto(documento, "ultimo_descritivo"),
						aposentada_em=_texto(documento, "aposentada_em"),
					)
				)
			except (ident.UuidInvalido, AttributeError):
				avisos.append(f"a aposentada {chave} está malformada; ignorada")

		return Leitura(
			instancias=tuple(sorted(instancias, key=lambda i: (i.descritivo.casefold(), i.uuid))),
			aposentadas=tuple(sorted(aposentadas, key=lambda a: a.uuid)),
			versao_do_esquema=versao,
			mais_nova=mais_nova,
			avisos=tuple(avisos),
		)

	def por_uuid(self, identificador: str) -> InstanciaLida | None:
		try:
			alvo = ident.normalizar_uuid(identificador)
		except ident.UuidInvalido:
			return None

		return next((i for i in self.ler().instancias if i.uuid == alvo), None)

	def por_descritivo(self, descritivo: str) -> InstanciaLida | None:
		try:
			chave = ident.chave_de_unicidade(descritivo)
		except ident.DescritivoInvalido:
			return None

		for instancia in self.ler().instancias:
			try:
				if ident.chave_de_unicidade(instancia.descritivo) == chave:
					return instancia
			except ident.DescritivoInvalido:
				continue

		return None

	def por_site(self, nome_do_site: str) -> InstanciaLida | None:
		return next((i for i in self.ler().instancias if i.host == nome_do_site), None)
