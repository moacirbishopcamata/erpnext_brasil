// Copyright (c) 2026, ERPNext Brasil contributors
// License: MIT. See license.txt

/**
 * Botões fiscais do Sales Invoice: emitir NF-e, cancelar e enviar carta de correção.
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
 *
 * Cancelamento e carta de correção: o mesmo gap, do outro lado
 * ------------------------------------------------------------
 * `integracao.eventos_nfe` expôs `cancelar_nfe` e `enviar_carta_correcao`, e valia a mesma
 * frase: nada os chamava de uma tela. Os dois botões só aparecem quando há chave de acesso
 * — sem nota autorizada não há evento a enviar, e o método recusaria de todo jeito.
 *
 * Por que os limites de tamanho aparecem no diálogo
 * -------------------------------------------------
 * A justificativa do cancelamento tem de 15 a 256 caracteres, e o texto da CC-e de 15 a
 * 1000 — limites do XSD, não deste app. Quem valida é o domínio puro
 * (`fiscal/documento/evento.py`); o diálogo apenas **diz a regra antes**, para o usuário
 * não descobrir o limite por uma rejeição depois de já ter escrito. Espelho da regra real,
 * nunca a única barreira.
 */

const JUSTIFICATIVA_MINIMA = 15;
const CORRECAO_MINIMA = 15;

// Cor do indicador por situação. O vocabulário vem de
// `fiscal/documento/situacao_fiscal.py`; uma situação nova que não apareça aqui cai no
// cinza, que é o certo — melhor "não sei dizer" do que uma cor que afirme o que não foi
// verificado.
const COR_DA_SITUACAO = {
	"Não emitido": "gray",
	Rejeitado: "orange",
	Autorizado: "green",
	Denegado: "red",
	Cancelado: "red",
};

frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) {
			return;
		}

		// A situação vem do servidor, não de `br_chave_acesso`. O campo local diz que
		// houve emissão e nada além: uma nota cancelada continua com a chave preenchida,
		// e decidir por ele oferecia "Cancelar NF-e" para algo já cancelado.
		frappe.call({
			method: "erpnext_brasil.integracao.situacao_fiscal.situacao_fiscal",
			args: { doctype: frm.doctype, name: frm.docname },
			callback(resposta) {
				if (resposta.message) {
					montar_area_fiscal(frm, resposta.message);
				}
			},
		});
	},
});

function montar_area_fiscal(frm, situacao) {
	frm.dashboard.add_indicator(
		__("NF-e: {0}", [__(situacao.situacao)]),
		COR_DA_SITUACAO[situacao.situacao] || "gray",
	);

	// Estado que não é do domínio fiscal: o documento não tem situação perante o Fisco
	// ainda, tem uma tarefa pendente. Por isso é indicador à parte, e não uma sexta cor
	// na tabela acima — misturá-los faria "em transmissão" parecer uma situação fiscal.
	if (situacao.em_fila) {
		frm.dashboard.add_indicator(__("Transmissão na fila"), "blue");

		// Sem botão enquanto há job: o servidor recusaria o segundo pedido (deduplicate),
		// mas oferecer um botão que não faz nada é pior que não oferecer.
		return;
	}

	if (situacao.cartas_de_correcao > 0) {
		frm.dashboard.add_indicator(
			__("Cartas de correção: {0}", [situacao.cartas_de_correcao]),
			"blue",
		);
	}

	// Só se emite o que ainda não existe perante o Fisco. Denegado conta como existente:
	// o número foi consumido, e reemitir com ele é impossível — oferecer o botão ali
	// convidaria a uma rejeição garantida.
	if (!situacao.emitido) {
		frm.add_custom_button(__("Emitir NF-e"), () => confirmar_e_emitir(frm), __("Brasil"));

		return;
	}

	// Evento só faz sentido sobre documento que vale: cancelar o que já está cancelado, ou
	// corrigir o que foi denegado, é recusa certa da SEFAZ.
	if (!situacao.vale) {
		return;
	}

	frm.add_custom_button(
		__("Cancelar NF-e"),
		() => pedir_justificativa_e_cancelar(frm),
		__("Brasil"),
	);

	frm.add_custom_button(
		__("Carta de Correção"),
		() => pedir_texto_e_corrigir(frm),
		__("Brasil"),
	);
}

function pedir_justificativa_e_cancelar(frm) {
	frappe.prompt(
		{
			label: __("Justificativa"),
			fieldname: "justificativa",
			fieldtype: "Small Text",
			reqd: 1,
			length: 256,
			description: __("De {0} a 256 caracteres, exigidos pela SEFAZ.", [
				JUSTIFICATIVA_MINIMA,
			]),
		},
		(valores) => {
			const justificativa = (valores.justificativa || "").trim();

			if (justificativa.length < JUSTIFICATIVA_MINIMA) {
				frappe.msgprint(
					__("A justificativa precisa de ao menos {0} caracteres.", [
						JUSTIFICATIVA_MINIMA,
					]),
				);

				return;
			}

			// Confirmação depois de escrever, não antes: cancelamento homologado não se
			// desfaz, e a nota cancelada não volta a valer.
			frappe.confirm(
				__("Cancelar a NF-e na SEFAZ? A operação não pode ser desfeita."),
				() => cancelar(frm, justificativa),
			);
		},
		__("Cancelar NF-e"),
		__("Enviar cancelamento"),
	);
}

function pedir_texto_e_corrigir(frm) {
	frappe.prompt(
		{
			label: __("Texto da correção"),
			fieldname: "texto_correcao",
			fieldtype: "Small Text",
			reqd: 1,
			length: 1000,
			// Regra de negócio da SEFAZ, não deste app: cada CC-e substitui a anterior
			// para efeito de exibição. Quem envia só a correção nova apaga as antigas da
			// vista, e o aviso aqui é o único lugar onde o usuário pode saber disso a
			// tempo.
			description: __(
				"De {0} a 1000 caracteres. Cada carta substitui a anterior: repita também as correções já enviadas.",
				[CORRECAO_MINIMA],
			),
		},
		(valores) => {
			const texto_correcao = (valores.texto_correcao || "").trim();

			if (texto_correcao.length < CORRECAO_MINIMA) {
				frappe.msgprint(
					__("O texto da correção precisa de ao menos {0} caracteres.", [CORRECAO_MINIMA]),
				);

				return;
			}

			corrigir(frm, texto_correcao);
		},
		__("Carta de Correção"),
		__("Enviar carta"),
	);
}

// Cada evento monta o seu `frappe.call` com o `method:` escrito por extenso, e não por
// template string com o nome montado em variável. O motivo é de teste, não de estilo:
// `test_costura_cliente` varre os `.js` procurando `method: "<literal>"` e confere que o
// método existe no Python e está exposto por `@frappe.whitelist()`. Um nome montado em
// tempo de execução passa despercebido pela varredura — e um erro de digitação só
// apareceria no primeiro clique de um usuário real, que é tarde. O que se repete entre os
// dois é o desfecho, e esse está fatorado em `anunciar_evento`.

function cancelar(frm, justificativa) {
	frappe.call({
		method: "erpnext_brasil.integracao.eventos_nfe.cancelar_nfe",
		args: { doctype: frm.doctype, name: frm.docname, justificativa },
		// Mesmo motivo do botão de emissão: a chamada fala com a SEFAZ e demora.
		freeze: true,
		freeze_message: __("Cancelando na SEFAZ…"),
		callback: (resposta) => anunciar_evento(frm, resposta),
	});
}

function corrigir(frm, texto_correcao) {
	frappe.call({
		method: "erpnext_brasil.integracao.eventos_nfe.enviar_carta_correcao",
		args: { doctype: frm.doctype, name: frm.docname, texto_correcao },
		freeze: true,
		freeze_message: __("Enviando a carta de correção…"),
		callback: (resposta) => anunciar_evento(frm, resposta),
	});
}

function anunciar_evento(frm, resposta) {
	if (!resposta.message) {
		return;
	}

	frappe.show_alert(
		{
			message: __("Evento aceito pela SEFAZ. Registro {0}.", [resposta.message.registro]),
			indicator: "green",
		},
		10,
	);

	frm.reload_doc();
}

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
		// Enfileira e volta na hora. A conversa com a SEFAZ acontece no worker: antes
		// disto, a tela ficava travada até ~25 s enquanto o recibo era consultado.
		method: "erpnext_brasil.integracao.fila_fiscal.enfileirar_emissao",
		args: { doctype: frm.doctype, name: frm.docname },
		// `freeze` curto e honesto: só o enfileiramento, que é rápido.
		freeze: true,
		freeze_message: __("Enfileirando a emissão…"),
		callback(resposta) {
			if (!resposta.message) {
				return;
			}

			// `ja_estava` não é erro: o pedido anterior ainda está sendo atendido, e
			// enfileirar de novo consumiria outro número da série.
			const mensagem = resposta.message.ja_estava
				? __("Esta nota já está na fila de transmissão.")
				: __("Emissão enfileirada. O resultado aparece aqui quando a SEFAZ responder.");

			frappe.show_alert(
				{ message: mensagem, indicator: resposta.message.ja_estava ? "orange" : "blue" },
				10,
			);

			frm.reload_doc();
		},
	});
}

// O worker avisa quando termina, e a tela se atualiza sozinha — sem isso o usuário
// precisaria recarregar para saber se a nota passou.
frappe.realtime.on("erpnext_brasil:emissao_concluida", (dados) => {
	const frm = cur_frm;

	if (!frm || frm.doctype !== dados.doctype || frm.docname !== dados.name) {
		return;
	}

	frappe.show_alert(
		{ message: __("NF-e autorizada. Protocolo {0}.", [dados.protocolo]), indicator: "green" },
		10,
	);

	frm.reload_doc();
});
