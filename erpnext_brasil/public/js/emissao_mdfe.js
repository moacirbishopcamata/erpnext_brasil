// Copyright (c) 2026, ERPNext Brasil contributors
// License: MIT. See license.txt

/**
 * Botões fiscais do `Shipment`: emitir o MDF-e, encerrar a viagem e cancelar o manifesto.
 *
 * Tarefa 5.5 de `fechar-laco-cte-mdfe`. `integracao.emissao_mdfe.emitir_mdfe` e
 * `integracao.eventos_mdfe` existem e estão testados em bench, e nada os chamava de uma tela —
 * o mesmo gap que `emissao_nfe.js` e `emissao_cte.js` fecharam para os outros documentos.
 *
 * O estado decide os botões (uma tabela, não uma cascata de `if`)
 * ---------------------------------------------------------------
 * `estado_do_mdfe` devolve a situação fiscal **e** se a viagem já foi encerrada — o encerramento
 * não muda a situação fiscal (o manifesto continua autorizado), então não cabe em `situacao`.
 * `ACOES_POR_ESTADO` mapeia o estado ao conjunto de botões; um estado que não está na tabela não
 * oferece nada, o que é o comportamento seguro.
 *
 *   não emitido / rejeitado → Emitir MDF-e
 *   autorizado              → Encerrar MDF-e e Cancelar MDF-e
 *   encerrado, cancelado,
 *   denegado                → nada (a SEFAZ recusaria)
 *
 * O que NÃO tem botão aqui
 * ------------------------
 * Condutor, inclusão de DF-e, pagamento e confirmação de serviço existem no domínio, mas não têm
 * gatilho no cadastro — ver `docs/mdfe-estado.md`. Um botão sem dado para alimentá-lo convidaria a
 * digitar à mão o que o sistema deveria saber.
 *
 * Funciona em qualquer largura: só usa botões do grupo "Brasil", diálogos e alertas do Desk, que
 * já são responsivos; nada de largura fixa nem de passar o mouse. Não foi aberto em navegador.
 *
 * Os nomes têm sufixo `_mdfe` de propósito: os `.js` de um mesmo DocType compartilham o escopo
 * global do navegador, e um `const` ou `function` repetido entre arquivos quebraria um dos dois.
 */

const JUSTIFICATIVA_MINIMA_MDFE = 15;
const JUSTIFICATIVA_MAXIMA_MDFE = 255;

// Mesmo vocabulário de `fiscal/documento/situacao_fiscal.py`; o que não estiver aqui cai no cinza.
const COR_DA_SITUACAO_MDFE = {
	"Não emitido": "gray",
	Rejeitado: "orange",
	Autorizado: "green",
	Denegado: "red",
	Cancelado: "red",
};

// O estado do manifesto → os botões que fazem sentido nele. Ausente = nenhum botão.
const ACOES_POR_ESTADO_MDFE = {
	"Não emitido": ["emitir"],
	Rejeitado: ["emitir"],
	Autorizado: ["encerrar", "cancelar"],
};

const BOTOES_MDFE = {
	emitir: { rotulo: __("Emitir MDF-e"), acao: confirmar_e_emitir_mdfe },
	encerrar: { rotulo: __("Encerrar MDF-e"), acao: confirmar_e_encerrar_mdfe },
	cancelar: { rotulo: __("Cancelar MDF-e"), acao: pedir_justificativa_e_cancelar_mdfe },
};

frappe.ui.form.on("Shipment", {
	refresh(frm) {
		// Rascunho não tem manifesto a emitir.
		if (frm.doc.docstatus !== 1) {
			return;
		}

		frappe.call({
			method: "erpnext_brasil.integracao.eventos_mdfe.estado_do_mdfe",
			args: { name: frm.docname },
			callback(resposta) {
				if (resposta.message) {
					montar_area_mdfe(frm, resposta.message);
				}
			},
		});
	},
});

function estado_do_botao_mdfe(estado) {
	// Encerrado é um estado à parte: o manifesto segue "Autorizado", mas nada mais se faz com ele.
	return estado.encerrado ? "Encerrado" : estado.situacao;
}

function montar_area_mdfe(frm, estado) {
	const nome = estado_do_botao_mdfe(estado);

	frm.dashboard.add_indicator(
		__("MDF-e: {0}", [__(nome)]),
		nome === "Encerrado" ? "blue" : COR_DA_SITUACAO_MDFE[estado.situacao] || "gray",
	);

	(ACOES_POR_ESTADO_MDFE[nome] || []).forEach((chave) => {
		const botao = BOTOES_MDFE[chave];

		frm.add_custom_button(botao.rotulo, () => botao.acao(frm), __("Brasil"));
	});
}

function confirmar_e_emitir_mdfe(frm) {
	// O `Shipment` não tem `company`: o ambiente é o da empresa de origem da coleta.
	frappe.db.get_value("Company", frm.doc.pickup_company, "br_ambiente_sefaz").then((resposta) => {
		const ambiente = (resposta.message || {}).br_ambiente_sefaz || __("não configurado");

		frappe.confirm(
			__(
				"Emitir o MDF-e no ambiente <b>{0}</b>?<br><br>O número do MDF-e é consumido na série; a SEFAZ pode levar alguns segundos para processar o lote.",
				[ambiente],
			),
			() => emitir_mdfe(frm),
		);
	});
}

function confirmar_e_encerrar_mdfe(frm) {
	frappe.confirm(
		__(
			"Encerrar o MDF-e? Isso informa à SEFAZ que a viagem terminou no município de descarga do Shipment, e não pode ser desfeito.",
		),
		() => encerrar_mdfe(frm),
	);
}

function pedir_justificativa_e_cancelar_mdfe(frm) {
	frappe.prompt(
		{
			label: __("Justificativa"),
			fieldname: "justificativa",
			fieldtype: "Small Text",
			reqd: 1,
			length: JUSTIFICATIVA_MAXIMA_MDFE,
			description: __("De {0} a {1} caracteres, exigidos pela SEFAZ.", [
				JUSTIFICATIVA_MINIMA_MDFE,
				JUSTIFICATIVA_MAXIMA_MDFE,
			]),
		},
		(valores) => {
			const justificativa = (valores.justificativa || "").trim();

			if (justificativa.length < JUSTIFICATIVA_MINIMA_MDFE) {
				frappe.msgprint(
					__("A justificativa precisa de ao menos {0} caracteres.", [
						JUSTIFICATIVA_MINIMA_MDFE,
					]),
				);

				return;
			}

			// Confirmação depois de escrever: cancelamento registrado não se desfaz.
			frappe.confirm(
				__("Cancelar o MDF-e na SEFAZ? A operação não pode ser desfeita."),
				() => cancelar_mdfe(frm, justificativa),
			);
		},
		__("Cancelar MDF-e"),
		__("Enviar cancelamento"),
	);
}

// Cada chamada monta o `method:` por extenso, e não por template string: `test_costura_cliente`
// varre os `.js` atrás de `method: "<literal>"` e confere que existe no Python e está exposto.

function emitir_mdfe(frm) {
	frappe.call({
		method: "erpnext_brasil.integracao.emissao_mdfe.emitir_mdfe",
		args: { doctype: frm.doctype, name: frm.docname },
		// Fala com a SEFAZ e demora (lote e recibo); sem `freeze` o segundo clique transmitiria de novo.
		freeze: true,
		freeze_message: __("Emitindo o MDF-e na SEFAZ…"),
		callback(resposta) {
			if (!resposta.message) {
				return;
			}

			concluir_mdfe(
				frm,
				__("MDF-e autorizado. Protocolo {0}.", [resposta.message.protocolo]),
			);
		},
	});
}

function encerrar_mdfe(frm) {
	frappe.call({
		method: "erpnext_brasil.integracao.eventos_mdfe.encerrar_mdfe",
		args: { name: frm.docname },
		freeze: true,
		freeze_message: __("Encerrando o MDF-e na SEFAZ…"),
		callback(resposta) {
			if (!resposta.message) {
				return;
			}

			concluir_mdfe(
				frm,
				__("MDF-e encerrado. Protocolo {0}.", [resposta.message.protocolo]),
			);
		},
	});
}

function cancelar_mdfe(frm, justificativa) {
	frappe.call({
		method: "erpnext_brasil.integracao.eventos_mdfe.cancelar_mdfe",
		args: { name: frm.docname, justificativa: justificativa },
		freeze: true,
		freeze_message: __("Cancelando o MDF-e na SEFAZ…"),
		callback(resposta) {
			if (!resposta.message) {
				return;
			}

			concluir_mdfe(
				frm,
				__("MDF-e cancelado. Protocolo {0}.", [resposta.message.protocolo]),
			);
		},
	});
}

// Toda ação confirma o que mudou (alerta com o protocolo) e recarrega: o indicador e os botões
// são derivados do estado, então a tela se refaz sozinha, sem manipular o DOM.
function concluir_mdfe(frm, mensagem) {
	frappe.show_alert({ message: mensagem, indicator: "green" }, 10);
	frm.reload_doc();
}
