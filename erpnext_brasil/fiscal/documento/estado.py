# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Ciclo de vida do documento fiscal — o agregado e suas transições guardadas.

Por que um agregado, e não campos soltos
----------------------------------------
Um documento fiscal tem ciclo de vida real: rascunho → autorizado → cancelado, com
caminhos laterais para rejeitado e denegado. Quem trata isso como um campo `status` que
qualquer parte do código atribui acaba com nota "cancelada" que nunca foi autorizada, ou
"autorizada" sem protocolo. Aqui o estado é privado e só muda por método com guarda —
de fora se pede a ação, não se atribui o resultado.

A costura crítica
-----------------
O ponto onde bug silencioso mora não é a transição: é o **protocolo de autorização**.
Se a SEFAZ autoriza e o protocolo não persiste, existe nota válida no fisco e rascunho
no sistema — divergência que ninguém percebe até a fiscalização. Por isso `autorizar`
**exige** protocolo e recusa string vazia: é pós-condição do método, não detalhe do
chamador.

Foi assim que o projeto brasileiro anterior morreu — congelou depurando a assinatura,
com o transporte acoplado ao documento. Aqui o agregado não sabe transmitir; ele conhece
só o próprio estado, e o transporte fica atrás da porta em `porta.py`.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

__all__ = [
	"EVENTO_CANCELAMENTO",
	"JUSTIFICATIVA_MAXIMA",
	"JUSTIFICATIVA_MINIMA",
	"PRAZO_CANCELAMENTO",
	"PRAZO_EXTEMPORANEO",
	"DocumentoFiscal",
	"Estado",
	"TransicaoInvalida",
]

# Confirmados no XSD oficial da NF-e (tipo `xJust`).
JUSTIFICATIVA_MINIMA = 15
JUSTIFICATIVA_MAXIMA = 256

# Evento de cancelamento na NF-e.
EVENTO_CANCELAMENTO = "110111"

# Prazo padrão para cancelamento sem ônus, contado da autorização.
PRAZO_CANCELAMENTO = timedelta(hours=24)

# Cancelamento extemporâneo: o Ajuste SINIEF permite recepção até 480 horas, **a critério
# de cada unidade federada** e em geral com penalidade. Por ser facultativo por UF, não é
# o padrão — quem quiser precisa pedir explicitamente.
PRAZO_EXTEMPORANEO = timedelta(hours=480)


class Estado(Enum):
	"""Situação do documento perante o fisco."""

	RASCUNHO = "rascunho"
	AGUARDANDO = "aguardando"
	AUTORIZADO = "autorizado"
	REJEITADO = "rejeitado"
	DENEGADO = "denegado"
	CANCELADO = "cancelado"

	@property
	def final(self) -> bool:
		"""Estados dos quais não se sai.

		Denegado é final e é o mais mal compreendido: a SEFAZ registrou a operação e
		negou por irregularidade do destinatário. Não se cancela nem se reenvia — a
		numeração fica queimada.
		"""
		return self in (Estado.CANCELADO, Estado.DENEGADO)

	@property
	def permite_reenvio(self) -> bool:
		"""Rejeitado volta ao fluxo: corrige-se e transmite de novo, mesma numeração."""
		return self in (Estado.RASCUNHO, Estado.REJEITADO)


class TransicaoInvalida(RuntimeError):
	"""Tentativa de transição que o estado atual não admite."""

	def __init__(self, de: Estado, acao: str, motivo: str = ""):
		self.de = de
		self.acao = acao
		detalhe = f": {motivo}" if motivo else ""
		super().__init__(f"Não é possível {acao} um documento {de.value}{detalhe}")


@dataclass(frozen=True)
class Protocolo:
	"""Retorno da SEFAZ que prova a autorização."""

	numero: str
	recebido_em: datetime
	chave_acesso: str = ""

	def __post_init__(self):
		if not (self.numero or "").strip():
			raise ValueError("O protocolo não pode ser vazio: é a prova da autorização")


@dataclass
class DocumentoFiscal:
	"""Agregado com estado privado e transições guardadas.

	O estado é exposto para leitura (`estado`) mas só muda por método. Isso é a
	*imutabilidade de fronteira*: a mutação existe, mas fica contida dentro do agregado;
	de fora ninguém faz o documento mentir sobre a própria situação.
	"""

	numero: str
	serie: str
	_estado: Estado = field(default=Estado.RASCUNHO, repr=False)
	_protocolo: Protocolo | None = field(default=None, repr=False)
	_motivo: str = field(default="", repr=False)
	_justificativa: str = field(default="", repr=False)

	@property
	def estado(self) -> Estado:
		return self._estado

	@property
	def protocolo(self) -> Protocolo | None:
		return self._protocolo

	@property
	def motivo(self) -> str:
		"""Motivo da rejeição ou denegação, como devolvido pela SEFAZ."""
		return self._motivo

	@property
	def justificativa(self) -> str:
		return self._justificativa

	@property
	def autorizado(self) -> bool:
		return self._estado is Estado.AUTORIZADO

	# -- transições ---------------------------------------------------------------

	def transmitir(self) -> None:
		"""Marca o envio à SEFAZ. Só rascunho e rejeitado podem ser transmitidos."""
		if not self._estado.permite_reenvio:
			raise TransicaoInvalida(self._estado, "transmitir")

		self._estado = Estado.AGUARDANDO
		self._motivo = ""

	def autorizar(self, protocolo: Protocolo) -> None:
		"""Registra a autorização. **Exige** protocolo — sem ele não há autorização.

		Aceita apenas a partir de `AGUARDANDO`: autorizar um rascunho significaria que
		alguém pulou a transmissão, e o documento estaria afirmando um fato que não
		aconteceu.
		"""
		if self._estado is not Estado.AGUARDANDO:
			raise TransicaoInvalida(self._estado, "autorizar", "só documento transmitido é autorizado")

		if protocolo is None:
			raise ValueError("Autorização sem protocolo: o retorno da SEFAZ não pode se perder")

		self._estado = Estado.AUTORIZADO
		self._protocolo = protocolo
		self._motivo = ""

	def rejeitar(self, motivo: str) -> None:
		"""Registra rejeição. O documento volta ao fluxo e pode ser corrigido."""
		if self._estado is not Estado.AGUARDANDO:
			raise TransicaoInvalida(self._estado, "rejeitar")

		if not (motivo or "").strip():
			raise ValueError("A rejeição precisa do motivo devolvido pela SEFAZ")

		self._estado = Estado.REJEITADO
		self._motivo = motivo.strip()

	def denegar(self, motivo: str) -> None:
		"""Registra denegação — estado final, com a numeração queimada."""
		if self._estado is not Estado.AGUARDANDO:
			raise TransicaoInvalida(self._estado, "denegar")

		if not (motivo or "").strip():
			raise ValueError("A denegação precisa do motivo devolvido pela SEFAZ")

		self._estado = Estado.DENEGADO
		self._motivo = motivo.strip()

	def cancelar(
		self,
		justificativa: str,
		agora: datetime,
		permitir_extemporaneo: bool = False,
	) -> None:
		"""Cancela um documento autorizado, dentro do prazo.

		`agora` é parâmetro e não `datetime.now()`: uma regra que lê o relógio por conta
		própria não se testa e não se audita. Quem chama informa o instante.

		`permitir_extemporaneo` cobre a recepção até 480 horas que o Ajuste SINIEF
		faculta a cada UF, em geral com penalidade — por ser facultativo, exige pedido
		explícito em vez de acontecer sozinho.
		"""
		if self._estado is not Estado.AUTORIZADO:
			raise TransicaoInvalida(
				self._estado, "cancelar", "apenas documento autorizado pode ser cancelado"
			)

		texto = (justificativa or "").strip()

		if not (JUSTIFICATIVA_MINIMA <= len(texto) <= JUSTIFICATIVA_MAXIMA):
			raise ValueError(
				f"A justificativa deve ter de {JUSTIFICATIVA_MINIMA} a "
				f"{JUSTIFICATIVA_MAXIMA} caracteres, recebidos {len(texto)}"
			)

		limite = PRAZO_EXTEMPORANEO if permitir_extemporaneo else PRAZO_CANCELAMENTO

		# O protocolo sempre existe aqui: AUTORIZADO só se alcança com ele.
		decorrido = agora - self._protocolo.recebido_em

		if decorrido > limite:
			raise TransicaoInvalida(
				self._estado,
				"cancelar",
				f"prazo esgotado ({decorrido} desde a autorização, limite de {limite}). "
				"Fora do prazo, a correção se faz por NF-e de estorno",
			)

		self._estado = Estado.CANCELADO
		self._justificativa = texto

	# -- reconstituição -----------------------------------------------------------

	@classmethod
	def reconstituir(
		cls,
		numero: str,
		serie: str,
		estado: Estado,
		protocolo: Protocolo | None = None,
		motivo: str = "",
		justificativa: str = "",
	) -> "DocumentoFiscal":
		"""Recria o agregado a partir do que está persistido.

		Existe porque carregar do banco não é o mesmo que criar: aqui não se aplicam as
		guardas de transição, já que o estado gravado é fato consumado. Mas o invariante
		continua valendo, e é conferido: autorizado sem protocolo é dado corrompido, e
		falhar alto na leitura é melhor que propagar a mentira.
		"""
		if estado in (Estado.AUTORIZADO, Estado.CANCELADO) and protocolo is None:
			raise ValueError(
				f"Documento {numero}/{serie} está {estado.value} sem protocolo: "
				"dado inconsistente, a autorização não foi persistida"
			)

		return cls(
			numero=numero,
			serie=serie,
			_estado=estado,
			_protocolo=protocolo,
			_motivo=motivo,
			_justificativa=justificativa,
		)

	def instantaneo(self) -> dict:
		"""Projeção para persistência — o documento como bag de campos.

		Devolve uma cópia: quem lê não recebe referência para o estado interno.
		"""
		return {
			"numero": self.numero,
			"serie": self.serie,
			"estado": self._estado.value,
			"protocolo": self._protocolo.numero if self._protocolo else "",
			"protocolo_em": self._protocolo.recebido_em if self._protocolo else None,
			"chave_acesso": self._protocolo.chave_acesso if self._protocolo else "",
			"motivo": self._motivo,
			"justificativa": self._justificativa,
		}
