// Copyright (c) 2026, ERPNext Brasil contributors
// License: MIT. See license.txt

/**
 * Monta um Lote eSocial a partir dos holerites selecionados, na lista de Salary Slip.
 *
 * O último elo. A cadeia do eSocial estava inteira — montagem do S-1200, assinatura, lote,
 * transporte, transmissão — e **nenhuma tela a acionava**. Do ponto de vista de quem usa o
 * sistema, o app não declarava folha.
 *
 * Por que na lista de Salary Slip, e não na de Lote eSocial
 * ---------------------------------------------------------
 * O lote **nasce** daqui: é a seleção de holerites que o define. A lista de `Lote eSocial`
 * mostra o que já existe, e ali o que faz sentido é transmitir, não montar.
 *
 * Montar não transmite
 * --------------------
 * O lote nasce em rascunho, de propósito: em eSocial, o que foi transmitido **não se
 * desfaz** — retificar exige outro evento, com o número do recibo do primeiro. Separar as
 * duas ações dá ao usuário o momento de conferir, e é a mesma razão de a importação de XML
 * não criar o documento sozinha.
 */

frappe.listview_settings["Salary Slip"] = frappe.listview_settings["Salary Slip"] || {};

const configuracao_anterior = frappe.listview_settings["Salary Slip"].onload;

frappe.listview_settings["Salary Slip"].onload = function (listview) {
	if (configuracao_anterior) {
		// O `hrms` configura coisas aqui: substituir sem chamar apagaria o que ele pôs, e
		// o sintoma seria um recurso alheio sumindo sem explicação.
		configuracao_anterior(listview);
	}

	listview.page.add_actions_menu_item(__("Montar Lote eSocial (Brasil)"), () =>
		montar(listview),
	);
};

function montar(listview) {
	const selecionados = listview.get_checked_items(true);

	if (!selecionados.length) {
		frappe.msgprint(__("Selecione ao menos um holerite."));

		return;
	}

	frappe.confirm(
		__(
			"Montar um lote do eSocial com <b>{0}</b> holerite(s)?<br><br>O lote é criado em rascunho — <b>nada é transmitido agora</b>.",
			[selecionados.length],
		),
		() => chamar(selecionados),
	);
}

function chamar(holerites) {
	frappe.call({
		method: "erpnext_brasil.integracao.montagem_lote_esocial.montar_lote",
		args: { holerites },
		// A montagem assina cada evento, e assinar custa: com dezenas de holerites, leva
		// segundos. Diferente da transmissão, aqui não há rede — por isso ainda vale o
		// `freeze` em vez de fila.
		freeze: true,
		freeze_message: __("Montando e assinando os eventos…"),
		callback(resposta) {
			if (!resposta.message) {
				return;
			}

			const { lote, eventos } = resposta.message;

			frappe.msgprint({
				title: __("Lote montado"),
				message: __(
					"Lote {0} criado com {1} evento(s), em rascunho.<br><br>Confira e transmita pelo próprio lote.",
					[
						`<a href="/app/lote-esocial/${encodeURIComponent(lote)}">${frappe.utils.escape_html(lote)}</a>`,
						eventos,
					],
				),
				indicator: "green",
			});
		},
	});
}
