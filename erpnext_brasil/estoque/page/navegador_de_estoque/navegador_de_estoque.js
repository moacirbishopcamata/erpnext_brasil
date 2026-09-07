// Copyright (c) 2026, ERPNext Brasil contributors
// License: MIT. See license.txt

// Navegador do endereçamento — a tela que o estoquista usa de pé, no galpão.
//
// Por que uma página e não um relatório
// -------------------------------------
// O ERPNext já tem as duas metades: a árvore de `Warehouse` mostra a **estrutura** e nenhum
// saldo; o relatório de saldo mostra **números** e não deixa navegar. Quem junta as duas
// hoje é o operador, trocando de tela no meio do corredor.
//
// Um relatório não resolveria: relatório é para quem senta e filtra. Aqui a interação é
// "toco no endereço e desço um nível", e a resposta precisa caber numa tela pequena, de
// coletor, segurada com uma mão só.
//
// As duas perguntas que a tela responde
// -------------------------------------
// São sempre as mesmas duas, e é por isso que só existem dois modos:
//
//   1. "O que tem neste endereço?"  → navegação pela árvore
//   2. "Onde está este item?"       → busca por item
//
// O campo de leitura decide **sozinho** qual das duas o operador fez: bipar a etiqueta da
// prateleira responde a primeira; bipar o produto responde a segunda. O mesmo gesto, dois
// significados — decididos pelo que foi lido, não por um botão de modo que alguém esquece
// de trocar.
//
// A leitura reusa `erpnext_brasil.integracao.leitura_gs1.ler_codigo`, o mesmo resolvedor
// dos formulários: entende etiqueta GS1 e delega ao ERPNext no resto. Uma segunda forma de
// resolver código de barras divergiria da primeira sem ninguém perceber.

frappe.pages["navegador-de-estoque"].on_page_load = function (wrapper) {
	const pagina = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Navegador de Estoque"),
		single_column: true,
	});

	new NavegadorDeEstoque(pagina);
};

class NavegadorDeEstoque {
	constructor(pagina) {
		this.pagina = pagina;
		this.caminho = []; // a trilha de volta, do topo até onde se está
		this.montar_controles();
		this.montar_corpo();
		this.navegar_para(null);
	}

	montar_controles() {
		this.empresa = this.pagina.add_field({
			fieldname: "empresa",
			label: __("Empresa"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			change: () => this.navegar_para(null),
		});

		this.leitura = this.pagina.add_field({
			fieldname: "leitura",
			label: __("Ler etiqueta ou buscar"),
			fieldtype: "Data",
			description: __("Bipe a prateleira para ver o conteúdo, ou o produto para ver onde ele está"),
			change: () => this.resolver_leitura(),
		});

		this.pagina.set_secondary_action(__("Voltar ao topo"), () => this.navegar_para(null));
	}

	montar_corpo() {
		this.corpo = $('<div class="br-navegador"></div>').appendTo(this.pagina.main);
	}

	// --- navegação ------------------------------------------------------------------

	navegar_para(endereco, rotulo) {
		// A trilha é reconstruída aqui, e não no servidor: quem sabe por onde o operador
		// desceu é a tela. Pedir o caminho ao banco daria o caminho *da árvore*, que pode
		// não ser o percorrido quando se chega por leitura de etiqueta.
		if (endereco === null) {
			this.caminho = [];
		} else {
			const ja_visitado = this.caminho.findIndex((n) => n.nome === endereco);

			if (ja_visitado >= 0) {
				this.caminho = this.caminho.slice(0, ja_visitado + 1);
			} else {
				this.caminho.push({ nome: endereco, rotulo: rotulo || endereco });
			}
		}

		frappe.call({
			method: "erpnext_brasil.integracao.navegador_estoque.filhos_do_endereco",
			args: { pai: endereco, empresa: this.empresa.get_value() },
			callback: (r) => {
				const filhos = r.message || [];

				if (endereco && !filhos.length) {
					// Folha: não há para onde descer, então a pergunta vira "o que tem aqui".
					this.mostrar_conteudo(endereco);
					return;
				}

				this.desenhar(this.html_da_trilha() + this.html_dos_filhos(filhos));
			},
		});
	}

	mostrar_conteudo(endereco) {
		frappe.call({
			method: "erpnext_brasil.integracao.navegador_estoque.conteudo_do_endereco",
			args: { endereco: endereco, empresa: this.empresa.get_value() },
			callback: (r) => {
				this.desenhar(this.html_da_trilha() + this.html_do_conteudo(r.message || []));
			},
		});
	}

	mostrar_enderecos_do_item(item) {
		frappe.call({
			method: "erpnext_brasil.integracao.navegador_estoque.enderecos_do_item",
			args: { item: item, empresa: this.empresa.get_value() },
			callback: (r) => {
				this.desenhar(this.html_dos_enderecos(item, r.message || []));
			},
		});
	}

	// --- leitura --------------------------------------------------------------------

	resolver_leitura() {
		const lido = (this.leitura.get_value() || "").trim();

		if (!lido) {
			return;
		}

		this.leitura.set_value("");

		frappe.call({
			method: "erpnext_brasil.integracao.leitura_gs1.ler_codigo",
			args: { search_value: lido },
			callback: (r) => {
				const dados = r.message || {};

				// A ordem importa: um armazém lido responde "o que tem aqui"; um item lido
				// responde "onde está". Se viesse os dois, o item é o mais específico.
				if (dados.item_code) {
					this.mostrar_enderecos_do_item(dados.item_code);
				} else if (dados.warehouse) {
					this.navegar_para(dados.warehouse);
				} else {
					frappe.show_alert({
						message: __("Não reconheci {0}", [frappe.utils.escape_html(lido)]),
						indicator: "orange",
					});
				}
			},
		});
	}

	// --- desenho --------------------------------------------------------------------

	desenhar(html) {
		this.corpo.html(html);

		this.corpo.find("[data-endereco]").on("click", (e) => {
			const alvo = $(e.currentTarget);
			this.navegar_para(alvo.attr("data-endereco"), alvo.attr("data-rotulo"));
		});

		this.corpo.find("[data-conteudo]").on("click", (e) => {
			this.mostrar_conteudo($(e.currentTarget).attr("data-conteudo"));
		});
	}

	html_da_trilha() {
		const atual = this.caminho[this.caminho.length - 1];
		const passos = [
			`<a class="text-muted" data-endereco="">${__("Topo")}</a>`,
			...this.caminho.map(
				(n) =>
					`<a data-endereco="${frappe.utils.escape_html(n.nome)}">${frappe.utils.escape_html(
						n.rotulo
					)}</a>`
			),
		];

		// O botão "ver o que tem aqui" só aparece dentro de um endereço: no topo ele
		// significaria "o estoque inteiro", que é relatório, não navegação.
		const ver_conteudo = atual
			? `<button class="btn btn-xs btn-default" data-conteudo="${frappe.utils.escape_html(
					atual.nome
				)}">${__("Ver o que tem aqui")}</button>`
			: "";

		return `<div class="br-trilha">${passos.join(
			' <span class="text-muted">›</span> '
		)} ${ver_conteudo}</div>`;
	}

	html_dos_filhos(filhos) {
		if (!filhos.length) {
			return `<p class="text-muted">${__("Nenhum endereço aqui.")}</p>`;
		}

		const linhas = filhos
			.map((f) => {
				// "Vazio" é informação, não ausência dela: poupa a caminhada até a prateleira.
				const marca = f.itens
					? `<span class="indicator-pill blue">${f.itens} ${__("itens")}</span>`
					: `<span class="indicator-pill gray">${__("vazio")}</span>`;
				const tipo = f.warehouse_type
					? `<span class="text-muted small">${frappe.utils.escape_html(f.warehouse_type)}</span>`
					: "";

				return `<div class="br-no" data-endereco="${frappe.utils.escape_html(
					f.name
				)}" data-rotulo="${frappe.utils.escape_html(f.warehouse_name)}">
					<div>${frappe.utils.escape_html(f.warehouse_name)} ${tipo}</div>
					<div>${marca}</div>
				</div>`;
			})
			.join("");

		return `<div class="br-lista">${linhas}</div>`;
	}

	html_do_conteudo(itens) {
		if (!itens.length) {
			return `<p class="text-muted">${__("Endereço vazio.")}</p>`;
		}

		const linhas = itens
			.map(
				(i) => `<tr>
					<td>${frappe.utils.escape_html(i.item_code)}<br>
						<span class="text-muted small">${frappe.utils.escape_html(i.item_name || "")}</span></td>
					<td>${frappe.utils.escape_html(i.warehouse)}</td>
					<td class="text-right">${format_number(i.actual_qty)} ${frappe.utils.escape_html(
						i.stock_uom || ""
					)}</td>
				</tr>`
			)
			.join("");

		return `<table class="table table-sm br-conteudo">
			<thead><tr><th>${__("Item")}</th><th>${__("Endereço")}</th><th class="text-right">${__(
				"Saldo"
			)}</th></tr></thead>
			<tbody>${linhas}</tbody></table>`;
	}

	html_dos_enderecos(item, enderecos) {
		if (!enderecos.length) {
			return `<p class="text-muted">${__("O item {0} não tem saldo em nenhum endereço.", [
				frappe.utils.escape_html(item),
			])}</p>`;
		}

		const linhas = enderecos
			.map(
				(e) => `<tr>
					<td><a data-endereco="${frappe.utils.escape_html(e.warehouse)}" data-rotulo="${frappe.utils.escape_html(
						e.warehouse
					)}">${frappe.utils.escape_html(e.warehouse)}</a></td>
					<td class="text-right">${format_number(e.actual_qty)} ${frappe.utils.escape_html(
						e.stock_uom || ""
					)}</td>
				</tr>`
			)
			.join("");

		return `<h5>${__("Onde está")} ${frappe.utils.escape_html(item)}</h5>
			<table class="table table-sm br-conteudo">
			<thead><tr><th>${__("Endereço")}</th><th class="text-right">${__("Saldo")}</th></tr></thead>
			<tbody>${linhas}</tbody></table>`;
	}
}
