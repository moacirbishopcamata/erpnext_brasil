// Copyright (c) 2026, ERPNext Brasil contributors
// License: MIT. See license.txt

/**
 * Botão "Emitir NF-e" no Sales Invoice.
 *
 * Fecha o maior gap de uso que restava (docs/gaps.md): `integracao.emissao_nfe.emitir_nfe`
 * existia, exposto por `@frappe.whitelist()` e chamável só com `(doctype, name)` — e
 * **nada o chamava de uma tela**. Do ponto de vista de quem usa o sistema, o app não
 * emitia nota.
 *
 * O botão só aparece quando faz sentido
 * -------------------------------------
 * Documento em rascunho não tem NF-e a emitir (o número seria consumido por algo que ainda
 * pode mudar), e documento que já tem chave de acesso já foi emitido. Mostrar o botão nos
 * dois casos convidaria ao erro que a numeração sequencial torna caro: número queimado não
 * volta para a série.
 *
 * A confirmação não é formalidade
 * -------------------------------
 * Emitir é irreversível do ponto de vista fiscal: o número é consumido mesmo se a SEFAZ
 * recusar, e desfazer exige cancelamento ou inutilização de faixa. Por isso há diálogo de
 * confirmação, e ele diz **em qual ambiente** vai emitir — a diferença entre homologação e
 * produção é a diferença entre um teste e um documento que existe perante o Fisco.
 */

frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.br_chave_acesso) {
			return;
		}

		frm.add_custom_button(
			__("Emitir NF-e"),
			() => confirmar_e_emitir(frm),
			__("Brasil"),
		);
	},
});

function confirmar_e_emitir(frm) {
	frappe.db.get_value("Company", frm.doc.company, "br_ambiente_sefaz").then((resposta) => {
		const ambiente = (resposta.message || {}).br_ambiente_sefaz || __("não configurado");

		frappe.confirm(
			__("Emitir a NF-e no ambiente <b>{0}</b>?<br><br>O número da nota é consumido mesmo se a SEFAZ recusar — desfazer exige cancelamento ou inutilização de faixa.", [
				ambiente,
			]),
			() => emitir(frm),
		);
	});
}

function emitir(frm) {
	frappe.call({
		method: "erpnext_brasil.integracao.emissao_nfe.emitir_nfe",
		args: { doctype: frm.doctype, name: frm.docname },
		// `freeze` porque a chamada fala com a SEFAZ e pode levar segundos: sem isso o
		// usuário clica de novo, e o segundo clique consome outro número.
		freeze: true,
		freeze_message: __("Montando, assinando e transmitindo à SEFAZ…"),
		callback(resposta) {
			if (!resposta.message) {
				return;
			}

			frappe.show_alert(
				{
					message: __("NF-e autorizada. Protocolo {0}.", [resposta.message.protocolo]),
					indicator: "green",
				},
				10,
			);

			frm.reload_doc();
		},
	});
}
