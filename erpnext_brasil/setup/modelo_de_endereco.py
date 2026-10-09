# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Modelo de endereço brasileiro (`Address Template`).

O ERPNext traz modelos por país em `erpnext/regional/address_template/templates/` (Croácia, Alemanha,
Estados Unidos…). **O Brasil não está lá.** O modelo padrão do Frappe imprime `logradouro / cidade / UF / CEP /
país` e ignora `Número` e `Bairro`, que este app declara no `Address` (`br_numero_endereco`, `br_bairro`):
o dado existe e não aparece na etiqueta, na fatura nem na tela.

Quando instala, e quando **não**
---------------------------------
- Só se o site **não tem** modelo para o Brasil: o administrador pode ter ajustado o dele, e sobrescrever seria
  desfazer trabalho. O `country` do `Address Template` é único, então também não há como duplicar.
- Só se **já existe um modelo padrão**. O `validate` do Frappe promove a padrão qualquer modelo criado num site
  sem nenhum — e o modelo brasileiro viraria o formato de endereços estrangeiros. Num site ainda sem assistente
  de configuração concluído, nada é feito agora; o `after_migrate` seguinte instala.
- Idempotente: a segunda migração encontra o modelo e não faz nada.
"""

import frappe

__all__ = ["MODELO", "PAIS", "instalar_modelo_de_endereco"]

PAIS = "Brazil"

MODELO = """{{ address_line1 }}{% if br_numero_endereco %}, {{ br_numero_endereco }}{% endif %}<br>
{% if address_line2 %}{{ address_line2 }}<br>{% endif -%}
{% if br_bairro %}{{ br_bairro }}<br>{% endif -%}
{{ city }}{% if state %} - {{ state }}{% endif %}<br>
{% if pincode %}CEP {{ pincode }}<br>{% endif -%}
{{ country }}<br>
<br>
{% if phone %}{{ _("Phone") }}: {{ phone }}<br>{% endif -%}
{% if fax %}{{ _("Fax") }}: {{ fax }}<br>{% endif -%}
{% if email_id %}{{ _("Email") }}: {{ email_id }}<br>{% endif -%}
"""
"""Logradouro e número, complemento, bairro, cidade com UF e CEP — a ordem de um endereço brasileiro. Telefone, fax
e e-mail ficam como no modelo padrão do Frappe, para quem já os usa."""


def instalar_modelo_de_endereco() -> str:
	"""Cria o modelo do Brasil se couber. Devolve o que aconteceu: `"criado"`, `"ja_existia"`, `"sem_padrao"`
	ou `"sem_pais"` — para o `bench console` mostrar por que não instalou, em vez de calar."""
	if frappe.db.exists("Address Template", {"country": PAIS}):
		return "ja_existia"

	if not frappe.db.exists("Address Template", {"is_default": 1}):
		return "sem_padrao"

	if not frappe.db.exists("Country", PAIS):
		return "sem_pais"

	frappe.get_doc(
		{"doctype": "Address Template", "country": PAIS, "is_default": 0, "template": MODELO}
	).insert(ignore_permissions=True)

	return "criado"
