# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A identidade de uma instância: UUID único e imutável, descritivo único e nome de host.

Por que existe
--------------
Uma instância do ERPNext Brasil precisa de uma identidade que não se repita e que as outras ferramentas
(Cherry, Chantilly) reconheçam (mudança `soda-instancias-do-erp`). Duas coisas com papéis diferentes:

- **UUID versão 4**: a identidade para sempre. Gerado uma vez, nunca muda, nunca é reutilizado, nem depois de a
  instância ser removida. É a chave de tudo que uma ferramenta guarda por instância.
- **Descritivo**: o rótulo humano ("NF-e em homologação"). Único sem diferença de maiúsculas e de acentos,
  renomeável. Renomear não muda o UUID, o host nem a porta.

O **nome de host** deriva dos dois (`descritivo-xxxxxxxx.localhost`). Host próprio importa porque o navegador
compartilha cookies entre portas do mesmo host: duas instâncias em `localhost:8101` e `localhost:8102` se
derrubariam.

Contratos
---------
Pré-condições recusadas com exceção própria antes de qualquer efeito; funções puras, sem I/O.
"""

import re
import unicodedata
import uuid
from collections.abc import Callable, Container
from dataclasses import dataclass

__all__ = [
	"MAXIMO_DO_DESCRITIVO",
	"MINIMO_DO_DESCRITIVO",
	"DescritivoInvalido",
	"SorteioDeUuid",
	"UuidEsgotado",
	"UuidInvalido",
	"abreviar",
	"chave_de_unicidade",
	"nome_do_host",
	"normalizar_uuid",
	"slug",
	"sortear_uuid",
	"validar_descritivo",
]

MINIMO_DO_DESCRITIVO = 3
MAXIMO_DO_DESCRITIVO = 60
TAMANHO_DA_ABREVIACAO = 8
TAMANHO_DO_SLUG = 30
DOMINIO = "localhost"

_CONTROLE = re.compile(r"[\x00-\x1f\x7f]")


class DescritivoInvalido(ValueError):
	"""O descritivo não serve (tamanho, caracteres de controle, sem letra nem dígito)."""


class UuidInvalido(ValueError):
	"""O texto não é um UUID versão 4 na forma canônica."""


class UuidEsgotado(RuntimeError):
	"""O gerador só devolveu UUIDs já usados: não deveria acontecer, e é denunciado em vez de repetido."""


def _sem_acentos(texto: str) -> str:
	return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def validar_descritivo(texto: str) -> str:
	"""Devolve o descritivo limpo (espaços colapsados) ou recusa.

	Pré-condição: texto de 3 a 60 caracteres depois de limpo, sem caractere de controle (nem quebra de linha),
	com ao menos uma letra ou dígito.
	"""
	if not isinstance(texto, str):
		raise DescritivoInvalido(f"o descritivo precisa ser texto, recebido {type(texto).__name__}")

	if _CONTROLE.search(texto):
		raise DescritivoInvalido(
			"o descritivo não pode ter quebra de linha, tabulação nem outro caractere de controle"
		)

	limpo = " ".join(texto.split())

	if not MINIMO_DO_DESCRITIVO <= len(limpo) <= MAXIMO_DO_DESCRITIVO:
		raise DescritivoInvalido(
			f"o descritivo precisa ter de {MINIMO_DO_DESCRITIVO} a {MAXIMO_DO_DESCRITIVO} caracteres, "
			f"recebido {len(limpo)}"
		)

	if not any(c.isalnum() for c in limpo):
		raise DescritivoInvalido("o descritivo precisa ter ao menos uma letra ou um dígito")

	return limpo


def chave_de_unicidade(descritivo: str) -> str:
	"""A forma comparável do descritivo: sem acentos, sem diferença de caixa, espaços colapsados."""
	return " ".join(_sem_acentos(validar_descritivo(descritivo)).casefold().split())


def slug(descritivo: str) -> str:
	"""Parte do nome de host: minúsculas, dígitos e hífen, até 30 caracteres, nunca vazia."""
	base = _sem_acentos(validar_descritivo(descritivo)).lower()
	base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
	base = base[:TAMANHO_DO_SLUG].strip("-")

	return base or "instancia"


def normalizar_uuid(texto: str) -> str:
	"""A forma canônica (minúsculas, com hífens) de um UUID versão 4, ou recusa."""
	if not isinstance(texto, str):
		raise UuidInvalido(f"o UUID precisa ser texto, recebido {type(texto).__name__}")

	try:
		valor = uuid.UUID(texto.strip())
	except ValueError as erro:
		raise UuidInvalido(f"não é um UUID: {texto!r}") from erro

	canonico = str(valor)

	if texto.strip().lower() != canonico:
		raise UuidInvalido(f"o UUID precisa estar na forma canônica com hífens: {texto!r}")

	if valor.version != 4 or valor.variant != uuid.RFC_4122:
		raise UuidInvalido(f"o UUID precisa ser da versão 4: {texto!r}")

	return canonico


def abreviar(identificador: str) -> str:
	"""O trecho curto do UUID (8 hexadecimais) usado em nomes e na tela."""
	return normalizar_uuid(identificador).replace("-", "")[:TAMANHO_DA_ABREVIACAO]


def nome_do_host(descritivo: str, identificador: str) -> str:
	"""`descritivo-xxxxxxxx.localhost`: único porque o trecho do UUID é único."""
	return f"{slug(descritivo)}-{abreviar(identificador)}.{DOMINIO}"


@dataclass(frozen=True)
class SorteioDeUuid:
	uuid: str
	colisoes: int
	"""Quantos UUIDs sorteados já estavam em uso antes de achar um livre (quase sempre zero)."""


def sortear_uuid(
	indisponiveis: Container[str],
	*,
	gerar: Callable[[], uuid.UUID] = uuid.uuid4,
	tentativas: int = 20,
) -> SorteioDeUuid:
	"""Sorteia um UUID versão 4 que não esteja entre as instâncias nem entre as aposentadas.

	Colisão de 122 bits aleatórios é teoricamente possível e praticamente nunca acontece; o tratamento existe
	porque "nunca reutilizado" é uma promessa, e a colisão é contada para ser registrada.
	"""
	colisoes = 0

	for _ in range(tentativas):
		candidato = normalizar_uuid(str(gerar()))

		if candidato not in indisponiveis:
			return SorteioDeUuid(candidato, colisoes)

		colisoes += 1

	raise UuidEsgotado(f"{tentativas} sorteios seguidos devolveram UUIDs já usados")
