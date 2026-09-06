# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Transmissão em fila: a tela deixa de travar, e emissão em massa passa a existir.

Os três problemas que este módulo resolve
------------------------------------------------
Levantados em `docs/transmissoes-sincronas-e-assincronas.md`:

1. **A tela travava até ~25 s.** A emissão resolve o recibo dentro da chamada, e o
   `freeze: true` do JS segurava o usuário enquanto isso.
2. **Emissão em massa não tinha caminho.** Faturar cem notas eram cem cliques, cada um com
   a sua espera.
3. **Duplo clique consumia número.** O `freeze` é barreira de tela, não de servidor: dois
   navegadores, ou um `F5` no meio, escapavam dele.

⚠️ O que este módulo **não** faz, e por que isso importa
---------------------------------------------------------------
**Não muda `emissao_nfe.emitir_nfe`.** O trabalho pesado continua exatamente onde estava,
com os mesmos testes; aqui só se decide **quando** ele roda.

A tentação era criar um `Transmissao Fiscal` "Pendente" antes de enfileirar, para a tela ter
o que mostrar. Isso produziria **dois registros** por emissão — o pendente e o que
`emitir_nfe` grava —, e alguém teria de conciliá-los. O estado "enfileirado" não pertence ao
registro fiscal: pertence à fila, e é dela que se pergunta.

`deduplicate` é a barreira que o `freeze` não é
------------------------------------------------------
O `job_id` é **determinístico** — derivado de `(doctype, name)` —, e com `deduplicate=True`
o Frappe recusa enfileirar um segundo job para o mesmo documento enquanto o primeiro não
terminar.

Isso vale mais que o `freeze` da tela: vale para dois navegadores, para `F5` no meio da
espera e para chamadas de API. E é a diferença entre uma trava visual e uma garantia — em
numeração fiscal, número queimado não volta para a série.

Por que a fila `long`
----------------------------
`short` e `default` têm timeout de **300 s**; `long`, de **1500 s**. Uma emissão que precise
consultar o recibo já gasta ~25 s, e a SEFAZ tem dias ruins. Enfileirar na `default` faria a
transmissão morrer por timeout justamente quando o autorizador está lento — o pior momento
para perder o rastro do que foi enviado.

`enqueue_after_commit`
-----------------------------
Sempre `True`. O worker é outro processo com **outra conexão**: enfileirar antes do commit
abre a janela em que o job começa a rodar e não enxerga o que a transação ainda não gravou.
Aqui o request quase não grava nada, mas a regra vale de qualquer modo — a janela é pequena
e o erro que ela produz é intermitente, que é a pior espécie.
"""

import frappe
from frappe import _
from frappe.utils.background_jobs import is_job_enqueued

__all__ = [
	"FILA",
	"TIMEOUT",
	"enfileirar_emissao",
	"enfileirar_emissao_em_massa",
	"esta_na_fila",
	"job_id_da_emissao",
	"transmitir_em_fila",
]

FILA = "long"
"""Timeout de 1500 s contra os 300 s de `short`/`default` — ver docstring do módulo."""

TIMEOUT = 900
"""Teto explícito, abaixo do da fila.

Um job que passa disso não está lento: está preso. Deixar o teto da fila (1500 s) valer
significaria um worker ocupado por 25 minutos com uma transmissão que já não vai voltar.
"""

LIMITE_DO_LOTE = 100
"""Documentos por chamada de emissão em massa.

Não é limite da SEFAZ nem do Frappe: é para que um clique distraído não encha a fila com
milhares de jobs que ninguém pediu. Quem precisa de mais chama de novo.
"""


def job_id_da_emissao(doctype: str, name: str) -> str:
	"""O identificador determinístico do job de emissão deste documento.

	Determinístico de propósito: é o que permite ao `deduplicate` reconhecer o segundo
	pedido, e à tela perguntar se já há um job em andamento sem guardar nada.
	"""
	return f"erpnext_brasil::emitir_nfe::{doctype}::{name}"


def esta_na_fila(doctype: str, name: str) -> bool:
	"""Há job de emissão enfileirado ou em execução para este documento."""
	return is_job_enqueued(job_id_da_emissao(doctype, name))


def transmitir_em_fila(doctype: str, name: str) -> None:
	"""O que o worker executa. **Não é chamada diretamente pela tela.**

	Sem `@frappe.whitelist()`: expor isto permitiria pular a fila e a deduplicação, que são
	justamente o que este módulo acrescenta.

	Erros não são engolidos. `emitir_nfe` grava o `Transmissao Fiscal` antes de levantar, e
	a exceção sobe para o RQ — que a registra em `Error Log` com o traceback. Capturá-la
	aqui para "não sujar o log" esconderia a única pista de uma emissão que falhou sem
	ninguém olhando.
	"""
	from erpnext_brasil.integracao.emissao_nfe import emitir_nfe

	resultado = emitir_nfe(doctype, name)

	# A tela do documento é notificada para atualizar o indicador sem que o usuário
	# precise recarregar. `after_commit` porque o worker ainda não fechou a transação: o
	# aviso não pode chegar antes do dado que ele anuncia.
	frappe.publish_realtime(
		"erpnext_brasil:emissao_concluida",
		message={"doctype": doctype, "name": name, **resultado},
		doctype=doctype,
		docname=name,
		after_commit=True,
	)


@frappe.whitelist()
def enfileirar_emissao(doctype: str, name: str) -> dict:
	"""Põe a emissão na fila e devolve na hora, sem esperar a SEFAZ.

	Devolve `{"enfileirado": bool, "ja_estava": bool, "job": str}`. `ja_estava` é `True`
	quando havia job em andamento — e nesse caso **nada é enfileirado**, o que é resposta,
	não erro: significa que o pedido anterior ainda está sendo atendido.
	"""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("submit")

	job = job_id_da_emissao(doctype, name)
	ja_estava = esta_na_fila(doctype, name)

	if not ja_estava:
		frappe.enqueue(
			"erpnext_brasil.integracao.fila_fiscal.transmitir_em_fila",
			queue=FILA,
			timeout=TIMEOUT,
			job_id=job,
			deduplicate=True,
			enqueue_after_commit=True,
			doctype=doctype,
			name=name,
		)

	return {"enfileirado": not ja_estava, "ja_estava": ja_estava, "job": job}


@frappe.whitelist()
def enfileirar_emissao_em_massa(doctype: str, names: list[str] | str) -> dict:
	"""Enfileira a emissão de vários documentos de uma vez.

	`names` aceita lista ou JSON — o Desk manda a seleção da lista como string.

	Devolve `{"enfileirados", "ja_estavam", "sem_permissao"}` com os nomes em cada
	situação. **Um documento sem permissão não interrompe os demais**: interromper faria o
	usuário descobrir o problema documento a documento, e reenfileirar tudo de novo a cada
	descoberta.

	⚠️ Cada documento vira **um job**, não um job que emite cem notas. Um lote único
	falharia inteiro por causa de uma nota, e a numeração fiscal não permite refazer o que
	já passou: o que foi autorizado, foi.
	"""
	if isinstance(names, str):
		names = frappe.parse_json(names)

	if not names:
		frappe.throw(_("Nenhum documento selecionado."))

	if len(names) > LIMITE_DO_LOTE:
		frappe.throw(
			_("Selecione no máximo {0} documentos por vez; foram {1}.").format(LIMITE_DO_LOTE, len(names))
		)

	enfileirados: list[str] = []
	ja_estavam: list[str] = []
	sem_permissao: list[str] = []

	for nome in names:
		try:
			resultado = enfileirar_emissao(doctype, nome)
		except frappe.PermissionError:
			sem_permissao.append(nome)

			continue

		(ja_estavam if resultado["ja_estava"] else enfileirados).append(nome)

	return {
		"enfileirados": enfileirados,
		"ja_estavam": ja_estavam,
		"sem_permissao": sem_permissao,
	}
