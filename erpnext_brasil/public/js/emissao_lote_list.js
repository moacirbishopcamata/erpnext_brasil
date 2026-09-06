// Copyright (c) 2026, ERPNext Brasil contributors
// License: MIT. See license.txt

/**
 * Emissão de NF-e em massa, a partir da seleção na lista de Sales Invoice.
 *
 * Antes disto, faturar cem notas eram cem cliques — cada um com a sua espera de até ~25 s,
 * porque a emissão resolvia o recibo dentro da chamada.
 *
 * Por que na lista, e não no formulário
 * -------------------------------------
 * É na lista que se seleciona um conjunto. Um botão no formulário emitiria só o documento
 * aberto, que é exatamente o que o botão do formulário já faz.
 *
 * Um job por documento, não um job para o lote
 * --------------------------------------------
 * Decisão do lado do servidor, e vale repetir aqui: um lote único falharia inteiro por
 * causa de uma nota, e numeração fiscal não permite refazer o que já passou — o que foi
 * autorizado, foi.
 *
 * A confirmação diz quantos, e o ambiente
 * ---------------------------------------
 * Emitir cem notas é irreversível cem vezes. O diálogo mostra o número e o ambiente, pela
 * mesma razão que o botão individual mostra: a diferença entre homologação e produção é a
 * diferença entre um teste e cem documentos que existem perante o Fisco.
 */

frappe.listview_settings["Sales Invoice"] = frappe.listview_settings["Sales Invoice"] || {};

const configuracao_anterior = frappe.listview_settings["Sales Invoice"].onload;

frappe.listview_settings["Sales Invoice"].onload = function (listview) {
	if (configuracao_anterior) {
		// Outro app (ou o próprio ERPNext) pode já ter posto coisa aqui: substituir sem
		// chamar apagaria o que ele configurou, e o sintoma seria um recurso alheio
		// sumindo sem explicação.
		configuracao_anterior(listview);
	}

	listview.page.add_actions_menu_item(__("Emitir NF-e (Brasil)"), () =>
		confirmar_e_enfileirar(listview),
	);
};

function confirmar_e_enfileirar(listview) {
	const selecionados = listview.get_checked_items(true);

	if (!selecionados.length) {
		frappe.msgprint(__("Selecione ao menos um documento."));

		return;
	}

	const empresa = (listview.get_checked_items()[0] || {}).company;

	frappe.db.get_value("Company", empresa, "br_ambiente_sefaz").then((resposta) => {
		const ambiente = (resposta.message || {}).br_ambiente_sefaz || __("não configurado");

		frappe.confirm(
			__(
				"Emitir <b>{0}</b> NF-e no ambiente <b>{1}</b>?<br><br>Cada nota consome um número da série, mesmo se a SEFAZ recusar.",
				[selecionados.length, ambiente],
			),
			() => enfileirar(listview, selecionados),
		);
	});
}

function enfileirar(listview, nomes) {
	frappe.call({
		method: "erpnext_brasil.integracao.fila_fiscal.enfileirar_emissao_em_massa",
		args: { doctype: listview.doctype, names: nomes },
		// `freeze` curto e honesto: aqui só se enfileira, e enfileirar é rápido. A espera
		// da SEFAZ acontece no worker, não nesta chamada — que é todo o ponto.
		freeze: true,
		freeze_message: __("Enfileirando…"),
		callback(resposta) {
			if (resposta.message) {
				anunciar(resposta.message);
			}
		},
	});
}

function anunciar(resultado) {
	const linhas = [];

	if (resultado.enfileirados.length) {
		linhas.push(__("{0} enfileirada(s) para transmissão.", [resultado.enfileirados.length]));
	}

	if (resultado.ja_estavam.length) {
		// Não é erro: significa que o pedido anterior ainda está sendo atendido. Tratá-lo
		// como falha faria o usuário reenfileirar o que já está na fila.
		linhas.push(
			__("{0} já estava(m) na fila e não foram enfileiradas de novo.", [
				resultado.ja_estavam.length,
			]),
		);
	}

	if (resultado.sem_permissao.length) {
		linhas.push(
			__("{0} sem permissão de emissão: {1}.", [
				resultado.sem_permissao.length,
				resultado.sem_permissao.join(", "),
			]),
		);
	}

	// Laranja quando houve qualquer caso não-enfileirado: verde diria "tudo certo" sobre
	// um lote parcialmente atendido, e o usuário fecharia sem ler.
	const tudo_enfileirado = !resultado.ja_estavam.length && !resultado.sem_permissao.length;

	frappe.msgprint({
		title: __("Emissão em massa"),
		message: `<ul><li>${linhas.join("</li><li>")}</li></ul>`,
		indicator: tudo_enfileirado ? "green" : "orange",
	});
}
