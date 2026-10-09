# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Regras do registro de uma transmissão fiscal — puras, sem DocType nem Frappe.

O DocType `Transmissao Fiscal` é onde o resultado de falar com a SEFAZ passa a existir
como dado; este módulo é o que decide **o que é um registro coerente**. A separação é a
mesma de sempre: o schema (JSON) diz quais campos existem, o controller grava, e a regra
— testável sem bench — mora aqui.

Por que um DocType, e por que só agora
----------------------------------------------
Até aqui o app guardava `br_chave_acesso` e `br_protocolo_autorizacao` como campos do
próprio documento. Isso basta enquanto o dado é **atributo** de uma nota. Não basta para
o que tem vida própria: um documento tem **várias** interações com a SEFAZ ao longo do
tempo (autorização, depois talvez uma carta de correção, depois um cancelamento), cada
uma com seu protocolo, sua data, seu XML de ida e volta. Campo não guarda histórico;
registro guarda.

As invariantes que este módulo protege
----------------------------------------------
Cada uma existe porque o estado oposto seria mentira sobre o que aconteceu:

- **Autorizado exige protocolo.** Protocolo é a prova da autorização (mesma regra que
  `fiscal/documento/estado.Protocolo` já impunha). "Autorizado sem protocolo" é um
  registro que afirma algo que não pode comprovar.
- **Rejeitado e denegado exigem motivo.** Um registro que diz "rejeitado" sem dizer por
  quê não ajuda ninguém a corrigir — e o `xMotivo` sempre vem na resposta.
- **Inutilização não tem chave de acesso.** Inutilizar é declarar que uma faixa de
  numeração não foi usada; não existe documento, logo não existe chave. Exigir uma ali
  levaria alguém a inventar.
- **Chave, quando houver, é chave de verdade.** Valida layout e dígito verificador
  reaproveitando `chave_acesso.validar_chave`, a mesma da família NF-e/CT-e/MDF-e.

Funções puras: nenhuma dependência do Frappe.
"""

from erpnext_brasil.fiscal.documento.chave_acesso import ChaveInvalida, validar_chave

__all__ = [
	"SITUACAO_AUTORIZADO",
	"SITUACOES",
	"SITUACOES_QUE_EXIGEM_MOTIVO",
	"TIPOS",
	"TIPO_INUTILIZACAO",
	"RegistroInvalido",
	"validar_registro",
]

SITUACAO_PENDENTE = "Pendente"
SITUACAO_AUTORIZADO = "Autorizado"
SITUACAO_REJEITADO = "Rejeitado"
SITUACAO_DENEGADO = "Denegado"
SITUACAO_CANCELADO = "Cancelado"

SITUACOES = (
	SITUACAO_PENDENTE,
	SITUACAO_AUTORIZADO,
	SITUACAO_REJEITADO,
	SITUACAO_DENEGADO,
	SITUACAO_CANCELADO,
)

SITUACOES_QUE_EXIGEM_MOTIVO = (SITUACAO_REJEITADO, SITUACAO_DENEGADO)

TIPO_AUTORIZACAO = "Autorização"
TIPO_CANCELAMENTO = "Cancelamento"
TIPO_CARTA_DE_CORRECAO = "Carta de Correção"
TIPO_INUTILIZACAO = "Inutilização"
TIPO_CONSULTA = "Consulta"
TIPO_ENCERRAMENTO = "Encerramento"
TIPO_OUTRO = "Outro"

TIPOS = (
	TIPO_AUTORIZACAO,
	TIPO_CANCELAMENTO,
	TIPO_CARTA_DE_CORRECAO,
	TIPO_INUTILIZACAO,
	TIPO_CONSULTA,
	TIPO_ENCERRAMENTO,
	TIPO_OUTRO,
)

AMBIENTES = ("Homologação", "Produção")


class RegistroInvalido(ValueError):
	"""Estado que faria o registro mentir sobre o que aconteceu na SEFAZ."""


def validar_registro(dados: dict) -> None:
	"""Confere as invariantes de um registro de transmissão.

	Recebe um dicionário com os campos do DocType — assim a regra é testável sem
	instanciar `Document`, e o controller vira uma linha.
	"""
	tipo = (dados.get("tipo") or "").strip()
	situacao = (dados.get("situacao") or "").strip()
	ambiente = (dados.get("ambiente") or "").strip()

	if tipo not in TIPOS:
		raise RegistroInvalido(f"tipo deve ser um de {list(TIPOS)}, recebido {tipo!r}")

	if situacao not in SITUACOES:
		raise RegistroInvalido(f"situação deve ser uma de {list(SITUACOES)}, recebido {situacao!r}")

	if ambiente not in AMBIENTES:
		raise RegistroInvalido(f"ambiente deve ser um de {list(AMBIENTES)}, recebido {ambiente!r}")

	_validar_chave(tipo, (dados.get("chave_acesso") or "").strip())
	_validar_faixa(tipo, dados)
	_validar_coerencia_do_resultado(situacao, dados)


def _inteiro(valor) -> int:
	try:
		return int(valor or 0)
	except (TypeError, ValueError):
		return -1


def _validar_faixa(tipo: str, dados: dict) -> None:
	"""A faixa (`nNFIni`–`nNFFin`) é de inutilização e só dela.

	Inutilização sem faixa não diz o que foi inutilizado; faixa em outro tipo seria um número que não pertence a
	nenhuma transmissão. O Frappe grava 0 em `Int` vazio, então 0 significa "sem faixa".
	"""
	inicial, final = _inteiro(dados.get("numero_inicial")), _inteiro(dados.get("numero_final"))

	if tipo != TIPO_INUTILIZACAO:
		if inicial or final:
			raise RegistroInvalido("faixa de numeração só existe em inutilização")

		return

	if inicial < 1 or final < inicial:
		raise RegistroInvalido(
			f"inutilização exige faixa válida (inicial >= 1 e final >= inicial), recebido {inicial}-{final}"
		)


def _validar_chave(tipo: str, chave: str) -> None:
	if tipo == TIPO_INUTILIZACAO:
		if chave:
			raise RegistroInvalido(
				"inutilização não tem chave de acesso: inutilizar é declarar que a faixa "
				"de numeração não foi usada, então não existe documento nem chave"
			)

		return

	if not chave:
		return

	try:
		validar_chave(chave)
	except ChaveInvalida as e:
		raise RegistroInvalido(f"chave de acesso inválida: {e}") from e


def _validar_coerencia_do_resultado(situacao: str, dados: dict) -> None:
	if situacao == SITUACAO_AUTORIZADO and not (dados.get("protocolo") or "").strip():
		raise RegistroInvalido(
			"transmissão autorizada exige protocolo — ele é a prova da autorização, e um "
			"registro que afirma 'autorizado' sem ele não comprova nada"
		)

	if situacao in SITUACOES_QUE_EXIGEM_MOTIVO and not (dados.get("mensagem") or "").strip():
		raise RegistroInvalido(
			f"transmissão com situação {situacao!r} exige a mensagem devolvida pela SEFAZ "
			"— sem o motivo, ninguém sabe o que corrigir"
		)
