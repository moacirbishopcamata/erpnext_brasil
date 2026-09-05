// Copyright (c) 2026, ERPNext Brasil contributors
// License: MIT. See license.txt

/**
 * Botão "Gerar EFD-ICMS/IPI" na lista de Arquivo SPED.
 *
 * `integracao.geracao_efd.gerar_efd` existia, exposto por `@frappe.whitelist()`, e nada o
 * chamava de uma tela — a mesma lacuna que o botão de emissão fechou para a NF-e.
 *
 * Por que na **lista** e não no formulário
 * ----------------------------------------
 * O `Arquivo SPED` é o **resultado** da geração, não a entrada dela. Um botão no
 * formulário só existiria depois de o registro existir, o que é tarde demais. A lista é
 * onde se está quando se quer um arquivo novo.
 *
 * O diálogo pede o que o back-end se recusa a adivinhar
 * ----------------------------------------------------
 * O endereço é obrigatório e não é deduzido: a `Company` pode ter vários vinculados, e o
 * ERPNext não tem "endereço fiscal" único sem ambiguidade. `montar_identificacao_0000`
 * registra esse motivo, e a tela repassa a decisão a quem sabe respondê-la.
 *
 * O aviso de arquivo parcial é mostrado como aviso, não como sucesso
 * -----------------------------------------------------------------
 * O arquivo ainda não tem o Bloco D nem os cadastros do Bloco 0. Mostrar "gerado com
 * sucesso" e deixar a ressalva no retorno seria convidar alguém a tentar transmitir.
 */

frappe.listview_settings["Arquivo SPED"] = {
	onload(lista) {
		lista.page.add_inner_button(__("Gerar EFD-ICMS/IPI"), () => abrir_dialogo());
	},
};

function abrir_dialogo() {
	const dialogo = new frappe.ui.Dialog({
		title: __("Gerar EFD-ICMS/IPI"),
		fields: [
			{
				fieldname: "company",
				fieldtype: "Link",
				options: "Company",
				label: __("Empresa"),
				reqd: 1,
				default: frappe.defaults.get_user_default("Company"),
				onchange() {
					// Limpa o endereço ao trocar de empresa: manter o anterior geraria o
					// arquivo com o estabelecimento errado, e o número seria plausível.
					dialogo.set_value("address", "");
				},
			},
			{
				fieldname: "address",
				fieldtype: "Link",
				options: "Address",
				label: __("Endereço fiscal"),
				reqd: 1,
				description: __(
					"A empresa pode ter vários endereços; o EFD declara um. A escolha é sua porque o sistema não tem como decidir sem ambiguidade.",
				),
				get_query() {
					return {
						filters: { link_doctype: "Company", link_name: dialogo.get_value("company") },
					};
				},
			},
			{ fieldtype: "Section Break" },
			{
				fieldname: "data_inicial",
				fieldtype: "Date",
				label: __("Data inicial"),
				reqd: 1,
				default: frappe.datetime.month_start(),
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "data_final",
				fieldtype: "Date",
				label: __("Data final"),
				reqd: 1,
				default: frappe.datetime.month_end(),
			},
		],
		primary_action_label: __("Gerar"),
		primary_action(valores) {
			dialogo.hide();
			gerar(valores);
		},
	});

	dialogo.show();
}

function gerar(valores) {
	frappe.call({
		method: "erpnext_brasil.integracao.geracao_efd.gerar_efd",
		args: valores,
		// A geração varre os documentos do período inteiro; sem `freeze` o usuário clica
		// de novo e produz um segundo arquivo idêntico.
		freeze: true,
		freeze_message: __("Lendo os documentos do período e montando o arquivo…"),
		callback(resposta) {
			if (!resposta.message) {
				return;
			}

			const { registro, linhas, aviso } = resposta.message;

			// `msgprint` com indicador laranja, não `show_alert` verde: o arquivo é
			// parcial, e anunciar sucesso convidaria a tentar transmitir.
			frappe.msgprint({
				title: __("Arquivo gerado"),
				indicator: "orange",
				message: `${__("{0} — {1} linhas.", [registro, linhas])}<br><br>${aviso}`,
			});

			frappe.set_route("Form", "Arquivo SPED", registro);
		},
	});
}
