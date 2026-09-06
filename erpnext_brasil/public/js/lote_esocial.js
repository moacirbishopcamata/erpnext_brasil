// Copyright (c) 2026, ERPNext Brasil contributors
// License: MIT. See license.txt

/**
 * Transmitir e reconsultar um Lote eSocial.
 *
 * Fecha a cadeia: `montagem_lote_esocial` monta o lote a partir dos holerites, e daqui ele
 * sai. Sem estes dois botões, `transmissao_lote_esocial` continuaria exposto e sem tela —
 * o formato de gap que este projeto já pagou meia dúzia de vezes.
 *
 * ⚠️ Reconsultar não é retransmitir
 * ---------------------------------
 * São botões separados de propósito. Quando o lote fica "Em processamento", o eSocial já o
 * recebeu — **reenviar duplicaria os eventos**, e o eSocial não desfaz o que recebeu:
 * retificar exige outro evento, com o número do recibo do primeiro.
 *
 * Por isso "Transmitir" some assim que há protocolo, e "Consultar" aparece no lugar.
 */

frappe.ui.form.on("Lote eSocial", {
	refresh(frm) {
		if (frm.doc.__islocal) {
			return;
		}

		// Com protocolo, o lote já foi recebido: o caminho é consultar, nunca reenviar.
		if (frm.doc.protocolo_envio) {
			frm.add_custom_button(
				__("Consultar processamento"),
				() => chamar(frm, "consultar_lote_esocial", __("Consultando o eSocial…")),
				__("Brasil"),
			);

			return;
		}

		if (!frm.doc.xml_enviado) {
			// Sem XML não há o que transmitir. O método recusaria de todo jeito, e um
			// botão que só produz erro é pior que nenhum botão.
			return;
		}

		frm.add_custom_button(
			__("Transmitir ao eSocial"),
			() => confirmar_e_transmitir(frm),
			__("Brasil"),
		);
	},
});

function confirmar_e_transmitir(frm) {
	frappe.confirm(
		__(
			"Transmitir o lote no ambiente <b>{0}</b>?<br><br>O eSocial <b>não desfaz</b> o que recebe: corrigir depois exige um evento de retificação.",
			[__(frm.doc.ambiente || "não configurado")],
		),
		() => chamar(frm, "transmitir_lote_esocial", __("Transmitindo ao eSocial…")),
	);
}

// Os dois `method:` escritos por extenso, e não montados em variável: `test_costura_cliente`
// varre os `.js` procurando `method: "<literal>"` e confere que o método existe no Python e
// está exposto. Nome montado em tempo de execução passa despercebido pela varredura.
function chamar(frm, metodo, mensagem) {
	const chamadas = {
		transmitir_lote_esocial: {
			method: "erpnext_brasil.integracao.transmissao_lote_esocial.transmitir_lote_esocial",
		},
		consultar_lote_esocial: {
			method: "erpnext_brasil.integracao.transmissao_lote_esocial.consultar_lote_esocial",
		},
	};

	frappe.call({
		...chamadas[metodo],
		args: { name: frm.docname },
		// Ainda com `freeze`: diferente da emissão de NF-e, o eSocial não ganhou fila
		// nesta rodada — está declarado em `docs/fila-e-jobs.md` como candidato natural.
		freeze: true,
		freeze_message: mensagem,
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

	// Laranja quando o lote ainda não terminou: verde diria "pronto" sobre algo que ainda
	// vai mudar, e o usuário fecharia sem voltar para consultar.
	const concluido = resultado.situacao === "Processado";

	frappe.msgprint({
		title: __("Lote {0}", [__(resultado.situacao)]),
		message: __("Protocolo {0}. {1} evento(s). Resposta {2}: {3}", [
			resultado.protocolo || "—",
			resultado.eventos,
			resultado.codigo,
			frappe.utils.escape_html(resultado.descricao || ""),
		]),
		indicator: concluido ? "green" : "orange",
	});
}
