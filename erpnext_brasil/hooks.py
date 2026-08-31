app_name = "erpnext_brasil"
app_title = "ERPNext Brasil"
app_publisher = "ERPNext Brasil contributors"
app_description = "Localização fiscal brasileira para o ERPNext"
app_email = "-"
app_license = "MIT"

required_apps = ["frappe/erpnext"]

# Transições/animações discretas do Desk (identidade visual) — só opacity/transform
# (aceleradas por GPU, sem reflow de layout) e um único listener de evento, para não
# pesar no desempenho do sistema. Ver `docs/desk-transicoes.md`.
app_include_css = "/assets/erpnext_brasil/css/desk_transitions.css"
app_include_js = "/assets/erpnext_brasil/js/desk_transitions.js"

# O bloco fiscal roda sem RH nenhum instalado — `hrms` não é obrigatório. Este hook só
# tem efeito quando `hrms` também está instalado: é ele quem lê `regional_overrides`
# (via `hrms.allow_regional`), erpnext_brasil não precisa verificar a presença dele
# aqui. Ver `docs/rh-estado-hrms.md` e `integracao/folha.py`.
regional_overrides = {
	"Brazil": {
		"hrms.payroll.doctype.salary_slip.salary_slip.apply_regional_deductions": (
			"erpnext_brasil.integracao.folha.apply_regional_deductions"
		),
	}
}

after_install = "erpnext_brasil.setup.install.after_install"
after_migrate = "erpnext_brasil.setup.install.after_migrate"

# A validação é ligada em `validate` (não em `on_submit`) para que o erro apareça
# enquanto o usuário ainda está no formulário, não depois de submeter.
doc_events = {
	"Company": {
		"validate": [
			"erpnext_brasil.integracao.party.validar_tax_id",
			"erpnext_brasil.integracao.party.validar_ie",
		]
	},
	"Customer": {
		"validate": [
			"erpnext_brasil.integracao.party.validar_tax_id",
			"erpnext_brasil.integracao.party.validar_ie",
		]
	},
	"Supplier": {
		"validate": [
			"erpnext_brasil.integracao.party.validar_tax_id",
			"erpnext_brasil.integracao.party.validar_ie",
		]
	},
	"Address": {"validate": "erpnext_brasil.integracao.party.validar_codigo_municipio"},
	"Item": {"validate": "erpnext_brasil.integracao.party.validar_ncm"},
}

# A apuração roda em `validate` para que o usuário veja os impostos enquanto ainda pode
# corrigir o documento — em `on_submit` seria tarde. A sugestão de CFOP roda junto
# nesses quatro (documentos com apuração fiscal completa) e também em Pedidos/
# Subcontratação, que não têm apuração (documento interno, sem chave de acesso) mas
# ainda se beneficiam de saber qual CFOP usar quando virarem NF-e depois.
for _doctype in (
	"Sales Invoice",
	"Delivery Note",
	"Purchase Invoice",
	"Purchase Receipt",
):
	doc_events[_doctype] = {
		"validate": [
			# A classificação é conferida antes: não faz sentido apurar impostos de um
			# item cuja combinação de CST e cClassTrib a SEFAZ recusaria.
			"erpnext_brasil.integracao.validacao_fiscal.validar_classificacao_dos_itens",
			"erpnext_brasil.integracao.documento.apurar_impostos",
			"erpnext_brasil.integracao.cfop_sugestao.sugerir_cfop_compra_venda",
		]
	}

for _doctype in ("Sales Order", "Purchase Order"):
	doc_events[_doctype] = {
		"validate": ["erpnext_brasil.integracao.cfop_sugestao.sugerir_cfop_compra_venda"]
	}

for _doctype in ("Subcontracting Order", "Subcontracting Receipt"):
	doc_events[_doctype] = {
		"validate": ["erpnext_brasil.integracao.cfop_sugestao.sugerir_cfop_subcontratacao"]
	}
