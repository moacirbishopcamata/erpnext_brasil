# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Regras do registro de um arquivo SPED gerado — puras, sem DocType nem Frappe.

Terceiro DocType do app, e o que fecha o ciclo do bloco contábil: os módulos de EFD, ECD
e ECF montam o arquivo e o devolvem, e até aqui **nada registrava que ele existiu**. Não
havia como responder perguntas que uma fiscalização faz: qual período foi entregue,
quando, e se o que está no disco hoje é o mesmo que foi transmitido.

O hash é o que dá sentido ao registro
----------------------------------------------
Guardar "gerei a EFD de janeiro" sem guardar **o que** foi gerado registra pouco. O
`hash` do conteúdo permite responder à pergunta que importa: *o arquivo que tenho aqui é
o que foi entregue?* Regerar a mesma escrituração com dado corrigido produz hash
diferente — e é exatamente essa diferença que distingue uma reentrega legítima de uma
confusão de versões.

A invariante que os módulos de montagem não tinham
-------------------------------------------------------------
`ecf_bloco_0.IdentificacaoEcf` já modelava `retificadora` e `numero_recibo_anterior`, mas
**sem exigir coerência entre os dois** — os campos eram texto livre, deliberadamente
(aquele módulo não cataloga significado de código). No registro do arquivo, porém, a
coerência é o ponto: declarar-se **retificador sem informar o recibo do original** é
declarar que se está corrigindo algo, sem dizer o quê. O Fisco não tem como ligar a
retificação ao arquivo substituído, e a entrega falha.

O inverso também é incoerente: informar recibo anterior num arquivo **original** afirma
que ele substitui algo, contradizendo a própria finalidade declarada.

Período: fim não pode anteceder o início
------------------------------------------------
Óbvio o bastante para ninguém escrever, e é justamente por isso que passa. Um período
invertido gera um arquivo que o validador recusa depois de o usuário ter esperado a
geração inteira.

Funções puras: nenhuma dependência do Frappe.
"""

from datetime import date

__all__ = [
	"FINALIDADES",
	"FINALIDADE_ORIGINAL",
	"FINALIDADE_SUBSTITUTO",
	"TIPOS",
	"ArquivoInvalido",
	"validar_arquivo",
]

TIPO_EFD_ICMS_IPI = "EFD-ICMS/IPI"
TIPO_EFD_CONTRIBUICOES = "EFD-Contribuições"
TIPO_ECD = "ECD"
TIPO_ECF = "ECF"

TIPOS = (TIPO_EFD_ICMS_IPI, TIPO_EFD_CONTRIBUICOES, TIPO_ECD, TIPO_ECF)
"""Só as escriturações que este projeto monta de verdade — listar o que não se gera
criaria a expectativa de que se gera."""

FINALIDADE_ORIGINAL = "Original"
FINALIDADE_SUBSTITUTO = "Substituto"

FINALIDADES = (FINALIDADE_ORIGINAL, FINALIDADE_SUBSTITUTO)


class ArquivoInvalido(ValueError):
	"""Estado que tornaria o registro do arquivo inútil ou contraditório."""


def validar_arquivo(dados: dict) -> None:
	"""Confere as invariantes de um registro de arquivo SPED gerado."""
	tipo = (dados.get("tipo") or "").strip()
	finalidade = (dados.get("finalidade") or "").strip()

	if tipo not in TIPOS:
		raise ArquivoInvalido(f"tipo deve ser um de {list(TIPOS)}, recebido {tipo!r}")

	if finalidade not in FINALIDADES:
		raise ArquivoInvalido(f"finalidade deve ser uma de {list(FINALIDADES)}, recebido {finalidade!r}")

	_validar_periodo(dados.get("data_inicial"), dados.get("data_final"))
	_validar_retificacao(finalidade, (dados.get("recibo_anterior") or "").strip())


def _validar_periodo(inicial, final) -> None:
	if not isinstance(inicial, date) or not isinstance(final, date):
		raise ArquivoInvalido("data inicial e data final do período são obrigatórias")

	if final < inicial:
		raise ArquivoInvalido(
			f"o período termina ({final.isoformat()}) antes de começar ({inicial.isoformat()})"
		)


def _validar_retificacao(finalidade: str, recibo_anterior: str) -> None:
	if finalidade == FINALIDADE_SUBSTITUTO and not recibo_anterior:
		raise ArquivoInvalido(
			"arquivo substituto exige o recibo da entrega anterior: sem ele o Fisco não "
			"tem como ligar a retificação ao arquivo que ela substitui"
		)

	if finalidade == FINALIDADE_ORIGINAL and recibo_anterior:
		raise ArquivoInvalido(
			"arquivo original não tem recibo anterior: informar um afirma que ele "
			"substitui outra entrega, contradizendo a finalidade declarada"
		)
