// Copyright (c) 2026, ERPNext Brasil contributors
// License: MIT. See license.txt

// Consulta de CEP e busca de logradouro no formulário do endereço.
//
// Quem decide é o servidor
// -------------------------
// Este arquivo só mostra e aplica o que `integracao/consulta_cep.py` devolve. O servidor recebe
// os valores que o formulário tem hoje e responde com `preencher` (o que está **vazio** e pode ser
// preenchido) e `divergencias` (o que o cadastro contradiz no ViaCEP). Aqui:
//
//   - só `preencher` entra no formulário: o que o usuário já digitou nunca é trocado;
//   - `divergencias` é **avisado**, não corrigido — o ViaCEP pode estar mais genérico que o
//     endereço real, e quem conhece o endereço é o usuário;
//   - o preenchimento é anunciado (faixa amarela) até o salvamento, para que um valor sugerido
//     não se confunda com um valor que alguém confirmou.
//
// Quando roda
// ------------
// Só em endereço do Brasil, só com os 8 dígitos do CEP e só quando o usuário muda o campo — nunca
// ao abrir o formulário e nunca em lote. O ViaCEP é um serviço gratuito sem SLA que avisa sobre
// bloqueio por uso massivo; consultar sob demanda é parte do desenho.
//
// Sem rede o formulário continua exatamente como era: a mensagem diz que a consulta está
// indisponível e o usuário preenche à mão.

frappe.provide("erpnext_brasil.endereco_cep");

(function () {
	const METODO_CEP = "erpnext_brasil.integracao.consulta_cep.consultar_cep";
	const METODO_BUSCA = "erpnext_brasil.integracao.consulta_cep.buscar_logradouro";

	const CAMPOS = [
		"pincode",
		"address_line1",
		"br_bairro",
		"city",
		"state",
		"br_codigo_municipio_ibge",
	];

	const ROTULOS = {
		pincode: __("CEP"),
		address_line1: __("Logradouro"),
		br_bairro: __("Bairro"),
		city: __("Município"),
		state: __("UF"),
		br_codigo_municipio_ibge: __("Código IBGE"),
	};

	const UFS = [
		"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA",
		"PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
	];

	function e_brasil(frm) {
		return frm.doc.country === "Brazil";
	}

	function valores_atuais(frm) {
		const atual = {};

		CAMPOS.forEach((campo) => {
			atual[campo] = frm.doc[campo] || "";
		});

		return atual;
	}

	function digitos(texto) {
		return String(texto || "").replace(/\D/g, "");
	}

	function avisar(mensagem, indicador) {
		frappe.show_alert({ message: mensagem, indicator: indicador || "orange" }, 7);
	}

	function avisar_divergencias(divergencias) {
		if (!divergencias || !divergencias.length) {
			return;
		}

		const linhas = divergencias
			.map(
				(d) =>
					`<li><b>${frappe.utils.escape_html(d.rotulo)}</b>: ` +
					__("o cadastro diz {0}, o ViaCEP diz {1}", [
						frappe.utils.escape_html(d.atual),
						frappe.utils.escape_html(d.sugerido),
					]) +
					"</li>"
			)
			.join("");

		frappe.msgprint({
			title: __("O CEP não confere com o cadastro"),
			indicator: "orange",
			message:
				"<p>" +
				__("Nada foi alterado. Confira qual está certo e corrija à mão, se for o caso.") +
				"</p><ul>" +
				linhas +
				"</ul>",
		});
	}

	function aplicar(frm, resposta) {
		const preencher = resposta.preencher || {};
		const campos = Object.keys(preencher);

		// Marca antes de gravar valores: `set_value` de `pincode` dispararia nova consulta.
		frm.__consulta_cep_aplicando = true;

		const promessas = campos.map((campo) => frm.set_value(campo, preencher[campo]));

		Promise.all(promessas).finally(() => {
			frm.__consulta_cep_aplicando = false;
		});

		if (campos.length) {
			frm.set_intro(
				__("Pré-preenchido pelo ViaCEP: {0}. Confira e salve.", [
					campos.map((c) => ROTULOS[c]).join(", "),
				]),
				"yellow"
			);
		}

		avisar_divergencias(resposta.divergencias);
	}

	function tratar(frm, resposta) {
		if (resposta.situacao === "encontrado") {
			aplicar(frm, resposta);

			return;
		}

		avisar(resposta.mensagem || __("Consulta de CEP indisponível agora."));
	}

	function consultar(frm) {
		const cep = digitos(frm.doc.pincode);

		if (!e_brasil(frm) || cep.length !== 8 || frm.__consulta_cep_aplicando) {
			return;
		}

		frappe.call({
			method: METODO_CEP,
			args: { cep: cep, atual: JSON.stringify(valores_atuais(frm)) },
			callback: (r) => r.message && tratar(frm, r.message),
			error: () => avisar(__("Consulta de CEP indisponível agora. Preencha o endereço manualmente.")),
		});
	}

	function linha_do_resultado(r, i) {
		return (
			`<tr class="br-cep-linha" data-i="${i}" style="cursor:pointer">` +
			`<td>${frappe.utils.escape_html(r.rotulo)}</td></tr>`
		);
	}

	function abrir_busca(frm) {
		const uf_atual = String(frm.doc.state || "").toUpperCase();
		let resultados = [];

		const dialogo = new frappe.ui.Dialog({
			title: __("Buscar CEP pelo logradouro"),
			fields: [
				{
					fieldname: "uf",
					fieldtype: "Select",
					label: __("UF"),
					options: UFS.join("\n"),
					default: UFS.includes(uf_atual) ? uf_atual : "",
					reqd: 1,
				},
				{
					fieldname: "cidade",
					fieldtype: "Data",
					label: __("Município"),
					default: frm.doc.city || "",
					reqd: 1,
					description: __("Ao menos 3 letras."),
				},
				{
					fieldname: "logradouro",
					fieldtype: "Data",
					label: __("Logradouro"),
					default: frm.doc.address_line1 || "",
					reqd: 1,
					description: __("Ao menos 3 letras. Até 50 resultados."),
				},
				{ fieldname: "resultados", fieldtype: "HTML" },
			],
			primary_action_label: __("Buscar"),
			primary_action: (valores) => {
				frappe.call({
					method: METODO_BUSCA,
					args: valores,
					callback: (r) => {
						const resposta = r.message || {};

						if (resposta.situacao !== "encontrado") {
							dialogo.fields_dict.resultados.$wrapper.html(
								`<p class="text-muted">${frappe.utils.escape_html(
									resposta.mensagem || __("Busca indisponível agora.")
								)}</p>`
							);

							return;
						}

						resultados = resposta.resultados || [];
						dialogo.fields_dict.resultados.$wrapper.html(
							`<p class="text-muted">${__("Clique na linha para usar o CEP.")}</p>` +
								`<table class="table table-bordered"><tbody>${resultados
									.map(linha_do_resultado)
									.join("")}</tbody></table>`
						);
					},
					error: () =>
						dialogo.fields_dict.resultados.$wrapper.html(
							`<p class="text-muted">${__("Busca indisponível agora.")}</p>`
						),
				});
			},
		});

		// Escolher uma linha é uma decisão explícita do usuário: o CEP escolhido substitui o do
		// formulário. Os demais campos seguem a regra de sempre (o servidor só preenche lacuna).
		dialogo.$wrapper.on("click", ".br-cep-linha", function () {
			const escolhido = resultados[Number($(this).data("i"))];

			if (!escolhido) {
				return;
			}

			dialogo.hide();
			frm.set_value("pincode", escolhido.cep);
		});

		dialogo.show();
	}

	erpnext_brasil.endereco_cep = { consultar, abrir_busca, aplicar, valores_atuais };

	frappe.ui.form.on("Address", {
		refresh(frm) {
			if (!e_brasil(frm)) {
				return;
			}

			frm.add_custom_button(__("Buscar CEP pelo logradouro"), () => abrir_busca(frm), __("Brasil"));
		},

		pincode(frm) {
			consultar(frm);
		},

		after_save(frm) {
			// Depois de salvo, o endereço deixou de ser sugestão.
			frm.set_intro("");
		},
	});
})();
