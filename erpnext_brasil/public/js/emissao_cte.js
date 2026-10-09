// Copyright (c) 2026, ERPNext Brasil contributors
// License: MIT. See license.txt

/**
 * Botões fiscais da fatura de transporte: emitir CT-e, cancelar e enviar carta de correção.
 *
 * Tarefa 3.5 de `fechar-laco-cte-mdfe`. `integracao.emissao_cte.emitir_cte` e
 * `integracao.eventos_cte` existiam e estavam testados em bench, e nada os chamava de uma tela —
 * o mesmo gap que `emissao_nfe.js` fechou para a NF-e.
 *
 * Só a fatura de transporte
 * -------------------------
 * "Fatura de transporte" é a que tem `br_natureza_transporte` preenchida (o próprio campo diz
 * que decide se este botão aparece). `emissao_nfe.js` faz o inverso e se cala nessa fatura:
 * oferecer "Emitir NF-e" e "Emitir CT-e" lado a lado para a mesma prestação convidaria a emitir o
 * documento errado, e o número da série é consumido.
 *
 * A situação vem do servidor, e só a do CT-e
 * ------------------------------------------
 * `situacao_fiscal` é chamada com `familia: "cte"`. Sem isso, os registros do CT-e seriam lidos
 * como se fossem de NF-e, e a tela anunciaria "NF-e: Autorizado" para uma fatura que nunca teve
 * NF-e.
 *
 * Diferenças para a NF-e
 * ----------------------
 * - **Emissão síncrona**: o CT-e 4.00 não tem lote nem recibo, então não há fila, indicador de
 *   "na fila" nem evento em tempo real. Um clique, uma chamada, o resultado na hora.
 * - **Justificativa de 15 a 255 caracteres** (a NF-e aceita 256): limite do `TJust` do CT-e.
 * - **A carta de correção é uma lista estruturada** (grupo, campo, novo valor), não texto livre.
 *   Cada carta reporta as alterações que traz; as já enviadas não precisam ser repetidas.
 *
 * Os nomes têm sufixo `_cte` de propósito: os `.js` de um mesmo DocType compartilham o escopo
 * global do navegador, e um `const` ou `function` repetido entre `emissao_nfe.js` e este arquivo
 * quebraria um dos dois.
 */

const JUSTIFICATIVA_MINIMA_CTE = 15;
const JUSTIFICATIVA_MAXIMA_CTE = 255;

// Mesmo vocabulário de `fiscal/documento/situacao_fiscal.py`; o que não estiver aqui cai no cinza.
const COR_DA_SITUACAO_CTE = {
	"Não emitido": "gray",
	Rejeitado: "orange",
	Autorizado: "green",
	Denegado: "red",
	Cancelado: "red",
};

frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		// Rascunho não tem CT-e a emitir, e fatura comum não é de transporte.
		if (frm.doc.docstatus !== 1 || !frm.doc.br_natureza_transporte) {
			return;
		}

		frappe.call({
			method: "erpnext_brasil.integracao.situacao_fiscal.situacao_fiscal",
			args: { doctype: frm.doctype, name: frm.docname, familia: "cte" },
			callback(resposta) {
				if (resposta.message) {
					montar_area_cte(frm, resposta.message);
				}
			},
		});
	},
});

function montar_area_cte(frm, situacao) {
	frm.dashboard.add_indicator(
		__("CT-e: {0}", [__(situacao.situacao)]),
		COR_DA_SITUACAO_CTE[situacao.situacao] || "gray",
	);

	if (situacao.cartas_de_correcao > 0) {
		frm.dashboard.add_indicator(
			__("Cartas de correção: {0}", [situacao.cartas_de_correcao]),
			"blue",
		);
	}

	// Denegado conta como existente: o número foi consumido e reemitir com ele é rejeição certa.
	if (!situacao.emitido) {
		frm.add_custom_button(__("Emitir CT-e"), () => confirmar_e_emitir_cte(frm), __("Brasil"));

		return;
	}

	// Cancelar o que já está cancelado, ou corrigir o que foi denegado, é recusa certa da SEFAZ.
	if (!situacao.vale) {
		return;
	}

	frm.add_custom_button(
		__("Cancelar CT-e"),
		() => pedir_justificativa_e_cancelar_cte(frm),
		__("Brasil"),
	);

	frm.add_custom_button(
		__("Carta de Correção do CT-e"),
		() => pedir_correcoes_e_corrigir_cte(frm),
		__("Brasil"),
	);
}

function confirmar_e_emitir_cte(frm) {
	frappe.db.get_value("Company", frm.doc.company, "br_ambiente_sefaz").then((resposta) => {
		const ambiente = (resposta.message || {}).br_ambiente_sefaz || __("não configurado");

		frappe.confirm(
			__(
				"Emitir o CT-e no ambiente <b>{0}</b>?<br><br>O número do CT-e é consumido se a SEFAZ o autorizar ou denegar — desfazer exige cancelamento ou inutilização de faixa.",
				[ambiente],
			),
			() => emitir_cte(frm),
		);
	});
}

function pedir_justificativa_e_cancelar_cte(frm) {
	frappe.prompt(
		{
			label: __("Justificativa"),
			fieldname: "justificativa",
			fieldtype: "Small Text",
			reqd: 1,
			length: JUSTIFICATIVA_MAXIMA_CTE,
			description: __("De {0} a {1} caracteres, exigidos pela SEFAZ.", [
				JUSTIFICATIVA_MINIMA_CTE,
				JUSTIFICATIVA_MAXIMA_CTE,
			]),
		},
		(valores) => {
			const justificativa = (valores.justificativa || "").trim();

			if (justificativa.length < JUSTIFICATIVA_MINIMA_CTE) {
				frappe.msgprint(
					__("A justificativa precisa de ao menos {0} caracteres.", [
						JUSTIFICATIVA_MINIMA_CTE,
					]),
				);

				return;
			}

			// Confirmação depois de escrever: cancelamento registrado não se desfaz.
			frappe.confirm(
				__("Cancelar o CT-e na SEFAZ? A operação não pode ser desfeita."),
				() => cancelar_cte(frm, justificativa),
			);
		},
		__("Cancelar CT-e"),
		__("Enviar cancelamento"),
	);
}

function pedir_correcoes_e_corrigir_cte(frm) {
	frappe.prompt(
		{
			label: __("Correções"),
			fieldname: "correcoes",
			fieldtype: "Table",
			reqd: 1,
			cannot_add_rows: false,
			in_place_edit: true,
			data: [],
			description: __(
				"Uma linha por campo corrigido: o grupo do XML, o campo e o novo valor. A carta reporta só o que está nesta lista.",
			),
			fields: [
				{
					fieldname: "grupo_alterado",
					label: __("Grupo"),
					fieldtype: "Data",
					in_list_view: 1,
					reqd: 1,
					length: 20,
				},
				{
					fieldname: "campo_alterado",
					label: __("Campo"),
					fieldtype: "Data",
					in_list_view: 1,
					reqd: 1,
					length: 20,
				},
				{
					fieldname: "valor_alterado",
					label: __("Novo valor"),
					fieldtype: "Data",
					in_list_view: 1,
					reqd: 1,
					length: 500,
				},
				{
					fieldname: "numero_item_alterado",
					label: __("Item (se for lista)"),
					fieldtype: "Int",
					in_list_view: 1,
				},
			],
		},
		(valores) => {
			const correcoes = (valores.correcoes || []).map(montar_correcao_cte);

			if (!correcoes.length) {
				frappe.msgprint(__("Informe ao menos uma correção."));

				return;
			}

			corrigir_cte(frm, correcoes);
		},
		__("Carta de Correção do CT-e"),
		__("Enviar carta"),
	);
}

// O número do item só vai quando preenchido: o servidor trata a ausência e o zero de formas
// diferentes (zero é recusado, ausência é "não é lista").
function montar_correcao_cte(linha) {
	const correcao = {
		grupo_alterado: (linha.grupo_alterado || "").trim(),
		campo_alterado: (linha.campo_alterado || "").trim(),
		valor_alterado: (linha.valor_alterado || "").trim(),
	};

	if (linha.numero_item_alterado) {
		correcao.numero_item_alterado = linha.numero_item_alterado;
	}

	return correcao;
}

// Cada chamada monta o `method:` por extenso, e não por template string: `test_costura_cliente`
// varre os `.js` atrás de `method: "<literal>"` e confere que existe no Python e está exposto.

function emitir_cte(frm) {
	frappe.call({
		// Síncrono: o CT-e não tem lote nem recibo, a resposta vem na própria chamada.
		method: "erpnext_brasil.integracao.emissao_cte.emitir_cte",
		args: { doctype: frm.doctype, name: frm.docname },
		// Fala com a SEFAZ e demora; sem `freeze` o segundo clique transmitiria de novo.
		freeze: true,
		freeze_message: __("Emitindo o CT-e na SEFAZ…"),
		callback(resposta) {
			if (!resposta.message) {
				return;
			}

			frappe.show_alert(
				{
					message: __("CT-e autorizado. Protocolo {0}.", [resposta.message.protocolo]),
					indicator: "green",
				},
				10,
			);

			frm.reload_doc();
		},
	});
}

function cancelar_cte(frm, justificativa) {
	frappe.call({
		method: "erpnext_brasil.integracao.eventos_cte.cancelar_cte",
		args: { doctype: frm.doctype, name: frm.docname, justificativa },
		freeze: true,
		freeze_message: __("Cancelando o CT-e na SEFAZ…"),
		callback: (resposta) => anunciar_evento_cte(frm, resposta),
	});
}

function corrigir_cte(frm, correcoes) {
	frappe.call({
		method: "erpnext_brasil.integracao.eventos_cte.corrigir_cte",
		args: { doctype: frm.doctype, name: frm.docname, correcoes },
		freeze: true,
		freeze_message: __("Enviando a carta de correção do CT-e…"),
		callback: (resposta) => anunciar_evento_cte(frm, resposta),
	});
}

function anunciar_evento_cte(frm, resposta) {
	if (!resposta.message) {
		return;
	}

	frappe.show_alert(
		{
			message: __("Evento registrado pela SEFAZ. Registro {0}.", [resposta.message.registro]),
			indicator: "green",
		},
		10,
	);

	frm.reload_doc();
}
