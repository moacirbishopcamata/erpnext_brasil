app_name = "erpnext_brasil"
app_title = "ERPNext Brasil"
app_publisher = "ERPNext Brasil contributors"
app_description = "Localização fiscal brasileira para o ERPNext"
app_email = "-"
app_license = "MIT"

required_apps = ["frappe/erpnext"]

after_install = "erpnext_brasil.setup.install.after_install"
after_migrate = "erpnext_brasil.setup.install.after_migrate"

# A validação é ligada em `validate` (não em `on_submit`) para que o erro apareça
# enquanto o usuário ainda está no formulário, não depois de submeter.
doc_events = {
	"Company": {
		"validate": [
			"erpnext_brasil.fiscal.party.validar_tax_id",
			"erpnext_brasil.fiscal.party.validar_ie",
		]
	},
	"Customer": {
		"validate": [
			"erpnext_brasil.fiscal.party.validar_tax_id",
			"erpnext_brasil.fiscal.party.validar_ie",
		]
	},
	"Supplier": {
		"validate": [
			"erpnext_brasil.fiscal.party.validar_tax_id",
			"erpnext_brasil.fiscal.party.validar_ie",
		]
	},
	"Address": {"validate": "erpnext_brasil.fiscal.party.validar_codigo_municipio"},
	"Item": {"validate": "erpnext_brasil.fiscal.party.validar_ncm"},
}
