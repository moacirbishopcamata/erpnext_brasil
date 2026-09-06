// Copyright (c) 2026, ERPNext Brasil contributors
// License: MIT. See license.txt

// Aponta o leitor de código de barras para o resolvedor que entende etiqueta GS1.
//
// A costura possível, e por que é esta
// -------------------------------------
// `erpnext.utils.BarcodeScanner` lê `opts.scan_api` **no construtor** e guarda no objeto:
//
//     this.scan_api = opts.scan_api || "erpnext.stock.utils.scan_barcode";
//
// Quem constrói é cada tela do ERPNext, e não há hook para interferir nisso. O que sobra —
// e é suficiente — é trocar a propriedade na instância já criada, no `refresh` do
// formulário. O resolvedor novo **decora** o do ERPNext (ver
// `integracao/leitura_gs1.py`), então a troca não remove comportamento: acrescenta.
//
// ⚠️ A instância mora em dois lugares diferentes, e isso não é defesa paranoica
// ------------------------------------------------------------------------------
// Foi lido no código do erpnext v16, tela por tela:
//
//   `Stock Reconciliation` → `frm.barcode_scanner`      (stock_reconciliation.js)
//   `Stock Entry`          → `frm.cscript.barcode_scanner`  (via `extend_cscript`)
//   `Delivery Note`, `Purchase Receipt`, `Material Request`
//                          → `frm.cscript.barcode_scanner`  (TransactionController)
//
// Procurar só num dos dois faria a leitura GS1 funcionar em metade das telas — e o pior
// tipo de falha, porque o estoquista aprenderia que "às vezes funciona".
//
// `Pick List` fica de fora: ele cria a instância numa `const` local, sem guardá-la em lugar
// algum alcançável. Está declarado como lacuna em `docs/coletor-gs1.md`.

const METODO_GS1 = "erpnext_brasil.integracao.leitura_gs1.ler_codigo";

function apontar_para_o_leitor_gs1(frm) {
	// Os dois lugares onde o ERPNext guarda a instância — ver a nota acima.
	const instancias = [frm.barcode_scanner, frm.cscript && frm.cscript.barcode_scanner];

	for (const scanner of instancias) {
		if (scanner) {
			scanner.scan_api = METODO_GS1;
		}
	}
}

// `refresh` e não `setup`: no `setup` a instância do ERPNext ainda não existe em todas as
// telas, e trocar a propriedade de um objeto que não nasceu não faz nada — calado.
const TELAS = [
	"Stock Entry",
	"Stock Reconciliation",
	"Delivery Note",
	"Purchase Receipt",
	"Material Request",
];

// Guarda contra registro duplicado: o arquivo é declarado em `doctype_js` para cinco
// telas, e abrir duas delas na mesma sessão o avaliaria duas vezes. O efeito seria
// inofensivo (a atribuição é idempotente), mas um handler registrado em dobro é o tipo de
// coisa que confunde quem for depurar outra coisa aqui depois.
if (!frappe.provide("erpnext_brasil.gs1").registrado) {
	erpnext_brasil.gs1.registrado = true;

	for (const tela of TELAS) {
		frappe.ui.form.on(tela, {
			refresh: apontar_para_o_leitor_gs1,
		});
	}
}
