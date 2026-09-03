# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Validação do campo `br_chave_acesso` em documentos fiscais.

Por que existe — fecha o gap identificado em `integracao/mapeamento_cte.py`
------------------------------------------------------------------------------
`docs/integracao-cte-mapeamento.md` registrou que o ERPNext não tinha nenhum campo
para guardar a chave de acesso de um documento fiscal (NF-e emitida, ou CT-e/NF-e de
terceiro recebida) — um gap anterior e maior que a integração do CT-e em si. Este
módulo é a primeira metade do que falta: o **campo e a validação de formato**.

Deliberadamente não é a segunda metade — transmissão de verdade
------------------------------------------------------------------------------
Isto **não** liga a transmissão real ao SEFAZ (`integracao/transporte_sefaz.py`) a
nenhum evento. Preencher `br_chave_acesso` automaticamente depois de uma autorização
de verdade exigiria gerenciar certificado A1, ambiente de produção/homologação e
tratamento de erro de rede — infraestrutura que esta investigação não tem como testar
de ponta a ponta sem um certificado real e um ambiente de homologação da SEFAZ. Por
isso o campo é preenchido manualmente por enquanto (ou por uma integração futura que
grave nele) — o que este módulo garante é que, preenchido, o valor é uma chave válida.

Mesma disciplina de `party.validar_tax_id`: campo vazio é aceito
------------------------------------------------------------------------------
Obrigatoriedade é decisão de configuração do DocType, não desta validação — mesmo
padrão de `validar_tax_id`/`validar_ie`. Reusa `fiscal.documento.chave_acesso.
validar_chave` (a mesma validação de layout e dígito verificador usada em toda a
família NF-e/CT-e/MDF-e), não reimplementa nada.
"""

import frappe
from frappe import _

from erpnext_brasil.fiscal.documento.leitura_codigo import LeituraInvalida, extrair_chave

__all__ = ["validar_chave_acesso"]


def validar_chave_acesso(doc, method=None):
	"""Valida `br_chave_acesso` quando preenchida, e normaliza (remove máscara).

	Aceita leitura de código de barras direto no campo
	--------------------------------------------------------
	Passou a usar `leitura_codigo.extrair_chave` em vez de `chave_acesso.validar_chave`
	direto: o leitor **1D** do DANFE entrega os 44 dígitos (que já funcionavam), mas o
	leitor **2D** do cupom da NFC-e entrega a **URL inteira** do QR Code, com a chave no
	meio. Antes, escanear o cupom colava a URL e a validação recusava — e o usuário
	concluía, erradamente, que "o leitor 2D não funciona".

	`extrair_chave` continua validando layout e dígito verificador, então nada foi
	afrouxado: o campo aceita mais formas de **entrada**, e guarda exatamente o mesmo
	valor canônico de sempre.
	"""
	valor = doc.get("br_chave_acesso")

	if not valor:
		return

	try:
		limpa = extrair_chave(valor)
	except LeituraInvalida as e:
		frappe.throw(
			_("Chave de acesso inválida em {0}: {1}").format(doc.doctype, str(e)),
			title=_("Chave de acesso inválida"),
		)
		return

	doc.br_chave_acesso = limpa
