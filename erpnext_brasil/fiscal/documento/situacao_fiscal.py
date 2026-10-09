# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Qual é a situação fiscal de um documento, dado tudo o que já se transmitiu por ele.

Por que isto não é "pegar o registro mais recente"
--------------------------------------------------------
Essa é a armadilha, e ela parece inofensiva. Um documento acumula registros de tipos
diferentes — autorização, cancelamento, carta de correção — e cada um tem a **sua** noção
de situação. Uma carta de correção homologada é gravada como `Autorizado`, porque o evento
foi autorizado; ler o registro mais recente faria uma CC-e transformar em "autorizado" um
documento que está cancelado.

A situação do **documento** depende do **tipo** de cada registro, não da ordem em que
chegaram. Cancelamento homologado vence tudo; carta de correção não muda situação nenhuma.

Por que a regra vive aqui, e não na camada Frappe
--------------------------------------------------------
É decisão de domínio: "esta nota vale ou não vale perante o Fisco". Escrevê-la dentro do
adaptador a tornaria inalcançável para teste sem bench — e é justamente o tipo de regra que
precisa de teste exaustivo, porque errar significa mostrar ao usuário que uma nota
cancelada continua valendo.

Funções puras: nenhuma dependência do Frappe.

Denegação não é rejeição
------------------------------
Rejeitado significa "tente de novo": a SEFAZ não recebeu o documento e o número continua
disponível. Denegado significa que o documento **existe** e o número foi consumido por
irregularidade do destinatário — reemitir com o mesmo número é impossível. Tratar os dois
como a mesma coisa esconderia de quem precisa reemitir a única informação que importa.
"""

from dataclasses import dataclass, field

from erpnext_brasil.fiscal.documento.transmissao_registro import (
	SITUACAO_AUTORIZADO,
	SITUACAO_CANCELADO,
	SITUACAO_DENEGADO,
	SITUACAO_REJEITADO,
	TIPO_AUTORIZACAO,
	TIPO_CANCELAMENTO,
	TIPO_CARTA_DE_CORRECAO,
)

__all__ = [
	"FAMILIA_CTE",
	"FAMILIA_NFE",
	"SITUACAO_NAO_EMITIDO",
	"SITUACOES_DO_DOCUMENTO",
	"RegistroLido",
	"SituacaoFiscal",
	"da_familia",
	"situacao_do_documento",
]

FAMILIA_NFE = "nfe"
FAMILIA_CTE = "cte"
_MODELO_CTE = "57"

SITUACAO_NAO_EMITIDO = "Não emitido"
"""Nenhuma transmissão registrada. **Não** é o mesmo que rejeitado.

Um documento sem registro nunca foi apresentado à SEFAZ; um rejeitado foi e voltou. A
diferença decide o que a tela oferece — emitir, no primeiro caso, e reemitir, no segundo.
"""

SITUACOES_DO_DOCUMENTO = (
	SITUACAO_NAO_EMITIDO,
	SITUACAO_REJEITADO,
	SITUACAO_AUTORIZADO,
	SITUACAO_DENEGADO,
	SITUACAO_CANCELADO,
)
"""Em ordem de precedência crescente: quanto mais tarde na tupla, mais definitivo.

A ordem **é** a regra, e por isso está declarada como dado e não espalhada em `if`. Ler de
cima para baixo: não emitido cede a qualquer registro; rejeitado cede a uma autorização
posterior (a segunda tentativa passou); autorizado cede à denegação e ao cancelamento, que
são finais.
"""

_PRECEDENCIA = {situacao: posicao for posicao, situacao in enumerate(SITUACOES_DO_DOCUMENTO)}

_SITUACAO_POR_TIPO = {
	TIPO_AUTORIZACAO: {
		SITUACAO_AUTORIZADO: SITUACAO_AUTORIZADO,
		SITUACAO_DENEGADO: SITUACAO_DENEGADO,
		SITUACAO_REJEITADO: SITUACAO_REJEITADO,
	},
	TIPO_CANCELAMENTO: {SITUACAO_CANCELADO: SITUACAO_CANCELADO},
}
"""O que cada tipo de registro afirma **sobre o documento**.

`TIPO_CARTA_DE_CORRECAO` está deliberadamente ausente: uma CC-e homologada é gravada como
`Autorizado` — o evento foi autorizado —, e mapeá-la aqui faria uma correção "reautorizar"
um documento cancelado. Correção emenda texto; não muda situação.

Um cancelamento **rejeitado** também não entra: a tentativa falhou, e o documento continua
como estava. Só o par `(Cancelamento, Cancelado)` cancela.
"""


@dataclass(frozen=True)
class RegistroLido:
	"""Um `Transmissao Fiscal` reduzido ao que decide a situação.

	Existe para que a regra seja testável sem Frappe: a camada de integração lê o site e
	monta estes; este módulo nunca vê um `Document`.
	"""

	tipo: str
	situacao: str
	chave_acesso: str = ""
	protocolo: str = ""
	nome: str = ""


@dataclass(frozen=True)
class SituacaoFiscal:
	"""O que dizer ao usuário sobre este documento."""

	situacao: str = SITUACAO_NAO_EMITIDO
	chave_acesso: str = ""
	protocolo: str = ""
	registro: str = ""
	cartas_de_correcao: int = 0
	registros: int = 0
	motivos: tuple[str, ...] = field(default_factory=tuple)

	@property
	def emitido(self) -> bool:
		"""Houve documento perante o Fisco — inclusive cancelado ou denegado.

		Denegado conta: o número foi consumido, e é isso que impede reemitir com ele.
		"""
		return self.situacao in (SITUACAO_AUTORIZADO, SITUACAO_DENEGADO, SITUACAO_CANCELADO)

	@property
	def vale(self) -> bool:
		"""O documento vale perante o Fisco neste momento."""
		return self.situacao == SITUACAO_AUTORIZADO


def da_familia(registros, familia: str) -> tuple[RegistroLido, ...]:
	"""Só os registros da família pedida: o CT-e (modelo 57) ou o resto (NF-e e NFC-e).

	Uma fatura de transporte acumula `Transmissao Fiscal` do CT-e no mesmo `documento`; lidos juntos
	com os da NF-e, um CT-e autorizado apareceria como "NF-e: Autorizado". O modelo está nas
	posições 21-22 da chave de acesso (`chave_acesso.ler_chave`) — lido por fatia, e não por
	`ler_chave`, que valida o dígito verificador: aqui basta separar, e uma chave malformada deve
	continuar visível na tela em vez de sumir. Registro sem chave fica na família da NF-e, como
	sempre ficou.
	"""
	if familia not in (FAMILIA_NFE, FAMILIA_CTE):
		raise ValueError(f"família desconhecida: {familia!r}")

	def eh_cte(registro: RegistroLido) -> bool:
		return len(registro.chave_acesso) == 44 and registro.chave_acesso[20:22] == _MODELO_CTE

	return tuple(r for r in registros if eh_cte(r) == (familia == FAMILIA_CTE))


def _mais_definitiva(uma: str, outra: str) -> str:
	return uma if _PRECEDENCIA[uma] >= _PRECEDENCIA[outra] else outra


def situacao_do_documento(registros) -> SituacaoFiscal:
	"""Reduz os registros de um documento a uma situação e às referências que a sustentam.

	Recebe qualquer iterável de `RegistroLido`; a ordem não importa, porque a precedência é
	por tipo (ver docstring do módulo). Registro de tipo que não afirma nada sobre o
	documento — consulta, inutilização, carta de correção — é contado e ignorado na
	decisão.

	A chave de acesso e o protocolo vêm **sempre da autorização**, mesmo quando a situação
	é cancelada: é a autorização que os produziu, e um cancelamento sem chave à vista
	deixaria o usuário sem o que informar ao contador.
	"""
	lidos = tuple(registros)

	situacao = SITUACAO_NAO_EMITIDO
	chave = ""
	protocolo = ""
	nome = ""
	cartas = 0
	motivos: list[str] = []

	for registro in lidos:
		if registro.tipo == TIPO_CARTA_DE_CORRECAO and registro.situacao == SITUACAO_AUTORIZADO:
			cartas += 1

		afirmada = _SITUACAO_POR_TIPO.get(registro.tipo, {}).get(registro.situacao)

		if afirmada is None:
			continue

		if registro.tipo == TIPO_AUTORIZACAO and registro.situacao in (
			SITUACAO_AUTORIZADO,
			SITUACAO_DENEGADO,
		):
			# A referência sai da autorização, não do último registro — ver docstring.
			chave = registro.chave_acesso or chave
			protocolo = registro.protocolo or protocolo
			nome = registro.nome or nome

		anterior = situacao
		situacao = _mais_definitiva(situacao, afirmada)

		if situacao != anterior and not nome:
			nome = registro.nome

	if situacao == SITUACAO_REJEITADO:
		motivos = [r.nome for r in lidos if r.tipo == TIPO_AUTORIZACAO and r.situacao == SITUACAO_REJEITADO]

	return SituacaoFiscal(
		situacao=situacao,
		chave_acesso=chave,
		protocolo=protocolo,
		registro=nome,
		cartas_de_correcao=cartas,
		registros=len(lidos),
		motivos=tuple(motivos),
	)
