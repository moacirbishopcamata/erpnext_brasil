// Copyright (c) 2026, ERPNext Brasil contributors
// License: MIT. See license.txt

// Consulta de CNPJ no cadastro de cliente, fornecedor e empresa.
//
// Quem decide é o servidor
// -------------------------
// Este arquivo só mostra e aplica o que `integracao/consulta_cnpj.py` devolve. O servidor recebe o CNPJ e o nome que o
// formulário já tem, e responde com `preencher` (o que está **vazio** e pode ser preenchido), `aviso` (a situação cadastral,
// quando não é ATIVA) e `resumo`. Aqui:
//
//   - só `preencher` entra no formulário: o nome que o usuário já digitou (por exemplo, o nome fantasia) nunca é trocado;
//   - a situação cadastral é **aviso**, não bloqueio: a base é mensal e pode estar defasada;
//   - o preenchimento é anunciado (faixa amarela) até o salvamento, para um valor sugerido não se confundir com um confirmado;
//   - o endereço do estabelecimento só vira `Address` por clique explícito, e o servidor recusa se a parte já tem endereço.
//
// Quando roda
// ------------
// Só com os 14 caracteres do CNPJ (numérico ou alfanumérico) e só quando o usuário muda o campo — nunca ao abrir o formulário
// e nunca em lote. Em Fornecedor e Empresa, só se o país for o Brasil (Cliente não tem país). O que sai do servidor é só o CNPJ.
//
// Sem rede o formulário continua como era: a mensagem diz que a consulta está indisponível e o usuário preenche à mão.

frappe.provide("erpnext_brasil.consulta_cnpj");

(function () {
	const METODO_CNPJ = "erpnext_brasil.integracao.consulta_cnpj.consultar_cnpj";
	const METODO_ENDERECO = "erpnext_brasil.integracao.consulta_cnpj.criar_endereco_pelo_cnpj";

	const CAMPO_NOME = {
		Customer: "customer_name",
		Supplier: "supplier_name",
		Company: "company_name",
	};

	const ROTULOS_DO_RESUMO = [
		["razao_social", __("Razão social")],
		["nome_fantasia", __("Nome fantasia")],
		["situacao", __("Situação cadastral")],
		["data_situacao", __("Desde")],
		["matriz_filial", __("Matriz ou filial")],
		["cnae", __("Atividade principal (CNAE)")],
		["natureza_juridica", __("Natureza jurídica")],
		["porte", __("Porte")],
		["simples", __("Simples Nacional")],
		["mei", __("MEI")],
		["endereco", __("Endereço")],
	];

	function cnpj_do_formulario(frm) {
		return String(frm.doc.tax_id || "").replace(/[^0-9A-Za-z]/g, "").toUpperCase();
	}

	function fora_do_brasil(frm) {
		// Cliente não tem `country`; Fornecedor e Empresa têm.
		return Boolean(frm.doc.country) && frm.doc.country !== "Brazil";
	}

	function avisar(mensagem, indicador) {
		frappe.show_alert({ message: mensagem, indicator: indicador || "orange" }, 7);
	}

	function mostrar_situacao(frm, resposta) {
		frm.dashboard.clear_headline();

		const r = resposta.resumo || {};
		const situacao = frappe.utils.escape_html(r.situacao || __("não informada"));
		const desde = r.data_situacao ? " " + __("desde {0}", [frappe.utils.escape_html(r.data_situacao)]) : "";
		const corpo = resposta.aviso
			? frappe.utils.escape_html(resposta.aviso)
			: __("Situação cadastral na Receita: {0}{1}.", [situacao, desde]);

		frm.dashboard.set_headline_alert(
			corpo + ` <span class="text-muted">${frappe.utils.escape_html(r.aviso_de_defasagem || "")}</span>`,
			resposta.ativo ? "green" : "red"
		);
	}

	function aplicar(frm, resposta) {
		const preencher = resposta.preencher || {};
		const campos = Object.keys(preencher);

		// Marca antes de gravar: `set_value` de campo do próprio formulário não deve disparar nova consulta.
		frm.__consulta_cnpj_aplicando = true;

		Promise.all(campos.map((campo) => frm.set_value(campo, preencher[campo]))).finally(() => {
			frm.__consulta_cnpj_aplicando = false;
		});

		if (campos.length) {
			frm.set_intro(__("Pré-preenchido pela consulta de CNPJ: {0}. Confira e salve.", [campos.join(", ")]), "yellow");
		}

		if (resposta.aviso_nome) {
			frappe.msgprint({
				title: __("Razão social não sugerida"),
				indicator: "orange",
				message: frappe.utils.escape_html(resposta.aviso_nome),
			});
		}

		mostrar_situacao(frm, resposta);
		frm.__resumo_cnpj = resposta.resumo;
		frm.__pode_criar_endereco = Boolean(resposta.pode_criar_endereco);
	}

	function tratar(frm, resposta) {
		if (resposta.situacao === "encontrado") {
			aplicar(frm, resposta);

			return;
		}

		avisar(resposta.mensagem || __("Consulta de CNPJ indisponível agora."));
	}

	function consultar(frm) {
		const cnpj = cnpj_do_formulario(frm);

		if (cnpj.length !== 14 || fora_do_brasil(frm) || frm.__consulta_cnpj_aplicando) {
			return;
		}

		const campo = CAMPO_NOME[frm.doctype];
		const atual = {};
		atual[campo] = frm.doc[campo] || "";

		frappe.call({
			method: METODO_CNPJ,
			args: { doctype: frm.doctype, cnpj: cnpj, atual: JSON.stringify(atual) },
			callback: (r) => r.message && tratar(frm, r.message),
			error: () => avisar(__("Consulta de CNPJ indisponível agora. Preencha o cadastro manualmente.")),
		});
	}

	function ver_dados(frm) {
		const r = frm.__resumo_cnpj;

		if (!r) {
			avisar(__("Informe um CNPJ válido para consultar."), "blue");

			return;
		}

		const linhas = ROTULOS_DO_RESUMO.filter(([chave]) => r[chave])
			.map(
				([chave, rotulo]) =>
					`<tr><td class="text-muted" style="width:35%">${rotulo}</td><td>${frappe.utils.escape_html(String(r[chave]))}</td></tr>`
			)
			.join("");

		frappe.msgprint({
			title: __("Dados da Receita"),
			message:
				`<table class="table table-bordered"><tbody>${linhas}</tbody></table>` +
				`<p class="text-muted">${frappe.utils.escape_html(r.aviso_de_defasagem || "")}</p>`,
		});
	}

	function criar_endereco(frm) {
		frappe.call({
			method: METODO_ENDERECO,
			args: { doctype: frm.doctype, name: frm.doc.name },
			freeze: true,
			callback: (r) => {
				const resposta = r.message || {};

				if (resposta.situacao === "criado") {
					avisar(resposta.mensagem, "green");
					frappe.set_route("Form", "Address", resposta.endereco);

					return;
				}

				avisar(resposta.mensagem || __("Não foi possível criar o endereço."));
			},
		});
	}

	erpnext_brasil.consulta_cnpj = { consultar, ver_dados, criar_endereco, aplicar };

	Object.keys(CAMPO_NOME).forEach((doctype) => {
		frappe.ui.form.on(doctype, {
			refresh(frm) {
				if (fora_do_brasil(frm)) {
					return;
				}

				frm.add_custom_button(__("Consultar CNPJ"), () => consultar(frm), __("Brasil"));
				frm.add_custom_button(__("Ver dados da Receita"), () => ver_dados(frm), __("Brasil"));

				if (!frm.is_new()) {
					frm.add_custom_button(__("Criar endereço pelo CNPJ"), () => criar_endereco(frm), __("Brasil"));
				}
			},

			tax_id(frm) {
				consultar(frm);
			},

			after_save(frm) {
				// Depois de salvo, o cadastro deixou de ser sugestão.
				frm.set_intro("");
			},
		});
	});
})();
