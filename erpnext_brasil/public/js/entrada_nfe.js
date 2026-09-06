// Copyright (c) 2026, ERPNext Brasil contributors
// License: MIT. See license.txt

/**
 * Botão "Importar XML da NF-e" no Purchase Invoice.
 *
 * Fecha o gap que a varredura de costura encontrou dois commits depois de criá-lo:
 * `integracao.entrada_nfe.importar_nfe` estava exposto por `@frappe.whitelist()` e **nada
 * o chamava de uma tela** — o mesmo formato que a emissão teve antes de `emissao_nfe.js`.
 *
 * O arquivo é lido no navegador, não enviado ao site
 * --------------------------------------------------
 * `FileReader` lê o XML escolhido e manda o **texto** ao método. A alternativa seria um
 * campo `Attach`, que faria upload e criaria um `File` no site — lixo permanente para uma
 * leitura que acontece uma vez. Uma NF-e tem dezenas de KB; cabe no corpo da chamada.
 *
 * As divergências são mostradas, nunca corrigidas
 * -----------------------------------------------
 * O método devolve uma lista de frases sobre o que não bate entre a nota e o documento —
 * total diferente, contagem de itens diferente, XML sem protocolo. Elas aparecem num
 * `msgprint` laranja, e não num alerta verde: importar com divergência **não é sucesso**,
 * é um resultado que alguém precisa olhar. Anunciá-lo em verde convidaria a fechar a
 * janela sem ler.
 */

frappe.ui.form.on("Purchase Invoice", {
	refresh(frm) {
		// Rascunho, não efetivado: a importação grava a chave de acesso, e depois do
		// submit o documento já foi escriturado com o que tem.
		if (frm.doc.docstatus !== 0) {
			return;
		}

		frm.add_custom_button(
			__("Importar XML da NF-e"),
			() => escolher_e_importar(frm),
			__("Brasil"),
		);
	},
});

function escolher_e_importar(frm) {
	const entrada = document.createElement("input");
	entrada.type = "file";
	entrada.accept = ".xml,text/xml,application/xml";

	entrada.addEventListener("change", () => {
		const arquivo = entrada.files && entrada.files[0];

		if (!arquivo) {
			return;
		}

		const leitor = new FileReader();

		leitor.onload = () => importar(frm, leitor.result);
		leitor.onerror = () =>
			frappe.msgprint({
				title: __("Não foi possível ler o arquivo"),
				message: __("O arquivo {0} não pôde ser lido.", [arquivo.name]),
				indicator: "red",
			});

		// UTF-8 explícito: o XML da NF-e é declarado em UTF-8, e deixar o navegador
		// adivinhar corromperia acentos da razão social e da natureza da operação.
		leitor.readAsText(arquivo, "UTF-8");
	});

	entrada.click();
}

function importar(frm, xml) {
	frappe.call({
		method: "erpnext_brasil.integracao.entrada_nfe.importar_nfe",
		args: { doctype: frm.doctype, name: frm.docname, xml },
		freeze: true,
		freeze_message: __("Lendo o XML da NF-e…"),
		callback(resposta) {
			if (!resposta.message) {
				return;
			}

			anunciar(frm, resposta.message);
		},
	});
}

function anunciar(frm, resultado) {
	frm.reload_doc();

	const cabecalho = __("NF-e {0} de {1}, {2} item(ns), total {3}.", [
		resultado.numero,
		resultado.emitente,
		resultado.itens,
		format_currency(resultado.valor_nota, frm.doc.currency),
	]);

	if (!resultado.divergencias || !resultado.divergencias.length) {
		frappe.show_alert({ message: cabecalho, indicator: "green" }, 10);

		return;
	}

	// Laranja e `msgprint`, não alerta verde: ver a nota no topo do arquivo.
	frappe.msgprint({
		title: __("Importado, com divergências"),
		message: `<p>${cabecalho}</p><ul><li>${resultado.divergencias.join("</li><li>")}</li></ul>`,
		indicator: "orange",
	});
}
