# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Diário de operação: a intenção fica registrada **antes** do primeiro passo.

Por que existe (mudança `resiliencia-e-seguranca-das-ferramentas`)
------------------------------------------------------------------
Criar, remover e trocar de formato têm vários passos. Se a energia cair, a janela fechar ou a conexão com o bench
cair no meio, o ambiente fica pela metade. O diário guarda o plano e o último passo concluído; na abertura seguinte
a operação sem desfecho aparece como **interrompida**, com o que já foi feito, e a ferramenta oferece desfazer ou
retomar. Sem o diário, a única pista de uma interrupção seria o estado inconsistente em si.

O diário mora na mesma porta de persistência do registro (JSON ou SQLite). Guarda só **nomes e estados**: nunca
senha, nunca saída de comando (o `detalhe` é curto e vem de mensagens nossas).
"""

import enum
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from erpnext_brasil.persistencia.documentos import RepositorioDeDocumentos

__all__ = ["COLECAO_OPERACOES", "Diario", "EstadoDaOperacao", "Operacao"]

COLECAO_OPERACOES = "operacoes"
TAMANHO_MAXIMO_DO_DETALHE = 300
OPERACOES_GUARDADAS = 100


class EstadoDaOperacao(str, enum.Enum):
	EM_ANDAMENTO = "em_andamento"
	CONCLUIDA = "concluida"
	FALHOU = "falhou"
	INTERROMPIDA = "interrompida"


@dataclass(frozen=True)
class Operacao:
	id: str
	tipo: str
	instancia: str
	plano: tuple[str, ...]
	concluidos: tuple[str, ...]
	estado: EstadoDaOperacao
	iniciada_em: str
	dono: int
	"""PID do processo que executa a operação: é como se sabe se ele ainda está vivo."""
	terminada_em: str | None = None
	detalhe: str = ""

	@property
	def proximo_passo(self) -> str | None:
		restantes = [p for p in self.plano if p not in self.concluidos]

		return restantes[0] if restantes else None

	def para_documento(self) -> dict[str, Any]:
		return {
			"id": self.id,
			"tipo": self.tipo,
			"instancia": self.instancia,
			"plano": list(self.plano),
			"concluidos": list(self.concluidos),
			"estado": self.estado.value,
			"iniciada_em": self.iniciada_em,
			"dono": self.dono,
			"terminada_em": self.terminada_em,
			"detalhe": self.detalhe,
		}

	@classmethod
	def de_documento(cls, documento: dict[str, Any]) -> "Operacao":
		return cls(
			id=documento["id"],
			tipo=documento["tipo"],
			instancia=documento["instancia"],
			plano=tuple(documento["plano"]),
			concluidos=tuple(documento["concluidos"]),
			estado=EstadoDaOperacao(documento["estado"]),
			iniciada_em=documento["iniciada_em"],
			dono=documento["dono"],
			terminada_em=documento.get("terminada_em"),
			detalhe=documento.get("detalhe", ""),
		)


def _agora_utc() -> datetime:
	return datetime.now(timezone.utc)


class Diario:
	def __init__(
		self,
		repositorio: RepositorioDeDocumentos,
		*,
		dono: int,
		agora: Callable[[], datetime] = _agora_utc,
		gerar_id: Callable[[], str] = lambda: uuid.uuid4().hex[:16],
	):
		self._repo = repositorio
		self._dono = dono
		self._agora = agora
		self._gerar_id = gerar_id

	def _gravar(self, operacao: Operacao) -> Operacao:
		self._repo.gravar(COLECAO_OPERACOES, operacao.id, operacao.para_documento())

		return operacao

	def obter(self, identificador: str) -> Operacao | None:
		documento = self._repo.obter(COLECAO_OPERACOES, identificador)

		return Operacao.de_documento(documento) if documento is not None else None

	def listar(self) -> list[Operacao]:
		return sorted(
			(Operacao.de_documento(doc) for _, doc in self._repo.listar(COLECAO_OPERACOES)),
			key=lambda o: (o.iniciada_em, o.id),
		)

	def abrir(self, tipo: str, instancia: str, plano: tuple[str, ...]) -> Operacao:
		"""Registra a intenção, **antes** do primeiro passo."""
		return self._gravar(
			Operacao(
				id=self._gerar_id(),
				tipo=tipo,
				instancia=instancia,
				plano=tuple(plano),
				concluidos=(),
				estado=EstadoDaOperacao.EM_ANDAMENTO,
				iniciada_em=self._agora().isoformat(),
				dono=self._dono,
			)
		)

	def passo_concluido(self, identificador: str, passo: str) -> Operacao:
		with self._repo.transacao():
			atual = self._exigir(identificador)

			if passo in atual.concluidos:
				return atual

			return self._gravar(replace(atual, concluidos=(*atual.concluidos, passo)))

	def encerrar(self, identificador: str, estado: EstadoDaOperacao, detalhe: str = "") -> Operacao:
		with self._repo.transacao():
			atual = self._exigir(identificador)

			return self._gravar(
				replace(
					atual,
					estado=estado,
					terminada_em=self._agora().isoformat(),
					detalhe=detalhe[:TAMANHO_MAXIMO_DO_DETALHE],
				)
			)

	def _exigir(self, identificador: str) -> Operacao:
		operacao = self.obter(identificador)

		if operacao is None:
			raise LookupError(f"não existe operação {identificador}")

		return operacao

	def em_andamento(self) -> list[Operacao]:
		return [o for o in self.listar() if o.estado == EstadoDaOperacao.EM_ANDAMENTO]

	def marcar_interrompidas(self, dono_vivo: Callable[[int], bool]) -> list[Operacao]:
		"""Toda operação "em andamento" cujo dono não existe mais é uma operação interrompida.

		Quem pergunta se o dono está vivo é `dono_vivo(pid)`; sem prova de que está morto, a operação continua em
		andamento (fail-closed: não se declara interrupção por suposição).
		"""
		marcadas = []

		for operacao in self.em_andamento():
			if not dono_vivo(operacao.dono):
				marcadas.append(
					self.encerrar(
						operacao.id,
						EstadoDaOperacao.INTERROMPIDA,
						f"o processo {operacao.dono} não existe mais; último passo concluído: "
						f"{operacao.concluidos[-1] if operacao.concluidos else 'nenhum'}",
					)
				)

		return marcadas

	def limitar(self, manter: int = OPERACOES_GUARDADAS) -> int:
		"""Descarta as operações **terminadas** mais antigas além do limite. Nunca toca nas em andamento."""
		terminadas = [o for o in self.listar() if o.estado != EstadoDaOperacao.EM_ANDAMENTO]
		excedentes = terminadas[: max(0, len(terminadas) - manter)]

		for operacao in excedentes:
			self._repo.remover(COLECAO_OPERACOES, operacao.id)

		return len(excedentes)
