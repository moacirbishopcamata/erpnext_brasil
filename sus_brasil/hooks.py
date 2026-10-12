# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

app_name = "sus_brasil"
app_title = "SUS Brasil"
app_publisher = "ERPNext Brasil contributors"
app_description = (
	"Saúde pública brasileira como módulo avulso: laboratório, farmácia, materiais e armazém, "
	"da solicitação ao resultado, da compra à dispensação"
)
app_email = "-"
app_license = "MIT"

# Avulso: depende só do Frappe. Nenhum outro app (ERPNext, ERPNext Brasil, Healthcare, HRMS) é exigido.
# As pontes com eles são extensões `<Aplicação>_Brasil`, instaladas à parte e ativas só onde o app existe.
required_apps = []
