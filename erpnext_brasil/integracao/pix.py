# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Ponte entre `contabil/pix.py` (payload puro) e o Frappe: de onde vêm chave,
nome e cidade do recebedor.

Camada fina de propósito, como `integracao/documento.py`: a regra (montagem do
payload, sanitização, CRC) está inteira em `contabil/pix.py`; aqui só a leitura do
cadastro e a tradução de erro para `frappe.throw`.

Cidade não é inferida — dado explícito de quem chama
------------------------------------------------------------
`Company` não tem um campo de cidade direto (mora no endereço padrão, cujo caminho
de busca é frágil o bastante para não valer a pena encadear aqui) — mesma
disciplina de `contabil/pix.py` não validar formato de chave Pix: dado que
depende de outra fonte fica com quem chama, não inferido.

Estado de verificação: não exercitado contra um bench real
------------------------------------------------------------------------
Mesma situação de `integracao/documento.py`/`integracao/party.py`: depende do
Frappe, sem bench disponível nesta sessão para rodar de ponta a ponta — a regra
pura (`contabil/pix.py`) está testada exaustivamente sem bench, esta camada não.
"""

import frappe
from frappe import _

from erpnext_brasil.contabil.pix import PixInvalido, montar_payload


@frappe.whitelist()
def gerar_payload_pix(company: str, cidade: str, valor: str | None = None, txid: str | None = None) -> str:
	"""Monta o payload Pix ("Copia e Cola") da empresa — `Company.chave_pix` precisa
	estar cadastrada. `valor` chega como string (convenção de método whitelisted do
	Frappe, que não distingue `Decimal` na chamada) e é convertido aqui, não em
	`contabil/pix.py`."""
	from decimal import Decimal, InvalidOperation

	frappe.has_permission("Company", "read", company, throw=True)

	chave, nome = frappe.db.get_value("Company", company, ["br_chave_pix", "company_name"])

	if not chave:
		frappe.throw(
			_("A empresa {0} não tem Chave Pix cadastrada (campo 'Chave Pix' em Company).").format(company),
			title=_("Pix não configurado"),
		)

	valor_decimal = None

	if valor:
		try:
			valor_decimal = Decimal(str(valor))
		except InvalidOperation:
			frappe.throw(_("Valor inválido para o Pix: {0}").format(valor))

	try:
		return montar_payload(
			chave_pix=chave,
			nome_recebedor=nome or company,
			cidade_recebedor=cidade,
			valor=valor_decimal,
			txid=txid or "***",
		)
	except PixInvalido as e:
		frappe.throw(str(e), title=_("Pix inválido"))
