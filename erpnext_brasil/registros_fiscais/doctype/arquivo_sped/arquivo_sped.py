# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Controller do DocType `Arquivo SPED` — fino, como os dois anteriores.

A regra está em `contabil/arquivo_sped_registro.py`, pura e testada sem bench.

`registrar_conteudo` calcula o hash aqui, e não na camada pura, por uma razão de
fronteira: o conteúdo do arquivo é o texto pronto do SPED (produzido por
`contabil/sped_texto.py`), e transformar texto em hash é operação de infraestrutura —
o que a regra pura precisa saber é apenas *se* há hash, não como calculá-lo. A escolha
do SHA-256 e da codificação fica registrada num lugar só.
"""

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document

from erpnext_brasil.contabil.arquivo_sped_registro import ArquivoInvalido, validar_arquivo

_CODIFICACAO = "latin-1"
"""O SPED é entregue em ANSI/Latin-1, não UTF-8. Calcular o hash sobre UTF-8 daria um
valor que não corresponde ao arquivo realmente transmitido — o hash tem de ser dos bytes
que saem, não de uma representação intermediária."""


class ArquivoSPED(Document):
	def validate(self):
		try:
			validar_arquivo(self.as_dict())
		except ArquivoInvalido as e:
			frappe.throw(str(e), title=_("Arquivo SPED inconsistente"))

	def registrar_conteudo(self, texto: str) -> None:
		"""Grava hash e contagem de linhas do arquivo gerado.

		Não chama `save()` — quem orquestra decide quando persistir, mesma disciplina de
		`LoteeSocial.registrar_retorno`.
		"""
		bytes_do_arquivo = texto.encode(_CODIFICACAO, errors="replace")

		self.hash_conteudo = hashlib.sha256(bytes_do_arquivo).hexdigest()
		self.quantidade_de_linhas = len([linha for linha in texto.split("\n") if linha.strip()])
