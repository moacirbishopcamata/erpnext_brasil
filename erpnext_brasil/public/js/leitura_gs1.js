// Copyright (c) 2026, ERPNext Brasil contributors
// License: MIT. See license.txt

// Aponta o leitor de código de barras para o resolvedor que entende etiqueta GS1.
//
// A costura, e por que é no protótipo
// ------------------------------------
// `erpnext.utils.BarcodeScanner` guarda o método no construtor:
//
//     this.scan_api = opts.scan_api || "erpnext.stock.utils.scan_barcode";
//
// mas quem o **usa** é `scan_api_call`, que lê `this.scan_api` **na hora da chamada**:
//
//     scan_api_call(input, callback) {
//         frappe.call({ method: this.scan_api, args: { search_value: input, ctx: {...} } })
//     }
//
// Essa diferença é tudo. Trocar a propriedade na instância exigiria **alcançar** a
// instância — e cada tela do ERPNext a guarda num lugar diferente:
//
//     `Stock Reconciliation` → frm.barcode_scanner
//     `Stock Entry` e as de transação → frm.cscript.barcode_scanner
//     `Pick List` → uma `const` local, inalcançável de fora
//
// Envolvendo `scan_api_call` no **protótipo**, nada disso importa: o patch vale para toda
// instância, criada antes ou depois, guardada em qualquer lugar — inclusive a do
// `Pick List`, que por isso deixou de ser a exceção declarada.
//
// ⚠️ Isto NÃO é alterar o ERPNext
// -------------------------------
// Nenhum arquivo do erpnext é tocado. O que se faz é substituir um método em memória, no
// nosso próprio JS — o mesmo mecanismo que o Frappe usa para `override_doctype_class` e
// `override_whitelisted_methods`, só que do lado do cliente, onde não existe hook
// equivalente.
//
// O contrato é preservado de propósito: o método original é **chamado**, não reescrito, e o
// nosso resolvedor decora o do ERPNext em vez de substituí-lo (ver
// `integracao/leitura_gs1.py`). Se o ERPNext mudar `scan_api_call`, a mudança dele continua
// valendo — só o método consultado é outro.

const METODO_GS1 = "erpnext_brasil.integracao.leitura_gs1.ler_codigo";
const METODO_DO_ERPNEXT = "erpnext.stock.utils.scan_barcode";

function instalar_leitor_gs1() {
	const Leitor =
		typeof erpnext !== "undefined" && erpnext.utils && erpnext.utils.BarcodeScanner;

	if (!Leitor || !Leitor.prototype || !Leitor.prototype.scan_api_call) {
		// O ERPNext mudou de forma. Não é motivo para quebrar a tela: sem o patch, a
		// leitura simples continua funcionando pelo caminho de sempre — só a etiqueta GS1
		// deixa de ser entendida.
		return;
	}

	if (Leitor.prototype.__br_gs1_instalado) {
		return;
	}

	const original = Leitor.prototype.scan_api_call;

	Leitor.prototype.scan_api_call = function (input, callback) {
		// Só assume o lugar do **padrão**. Se alguém passou um `scan_api` próprio em
		// `opts`, essa escolha é deliberada e não cabe a nós desfazê-la.
		if (this.scan_api === METODO_DO_ERPNEXT) {
			this.scan_api = METODO_GS1;
		}

		return original.call(this, input, callback);
	};

	Leitor.prototype.__br_gs1_instalado = true;
}

// `doctype_js` carrega este arquivo nas seis telas de estoque que têm leitor. Instalar já
// na avaliação basta: o bundle do erpnext é carregado antes do JS específico do DocType, e
// o patch é no protótipo — não depende de nenhuma instância existir ainda.
instalar_leitor_gs1();
