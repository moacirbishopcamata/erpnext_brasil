# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Todo DocType e campo que o app **lê** existe mesmo no site.

MODULOS_COBERTOS declarado abaixo; ver `scripts/cobertura_de_bench.py`.

Por que este arquivo é o mais importante de `tests_bench/`
--------------------------------------------------------------------
Os outros testes de bench provam que **o nosso** código funciona. Este prova que a
**premissa** dele continua verdadeira.

`setup/leituras_do_erpnext.py` lista 13 DocTypes que o app lê sem acrescentar campo nem
ligar hook. São dependências de estrutura alheia, e o modo de falhar delas é o pior que
existe neste projeto:

- o ERPNext renomeia `Work Order.actual_start_date`;
- o Bloco K da EFD passa a sair com data vazia;
- **a suíte pura continua verde** — ela não conhece o ERPNext;
- o arquivo é entregue ao Fisco errado.

Teste-âncora: `test_todo_campo_lido_e_coluna_de_verdade`. É a única coisa em todo o projeto
que pega esse cenário, e pega **na atualização**, não na entrega.

⚠️ Este teste falhando depois de um `bench update` não é bug nosso: é o ERPNext tendo mudado
por baixo. A correção é ler o que mudou e ajustar a leitura **e** a declaração juntas — nunca
só a declaração, que faria o teste passar sem consertar o app.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_leituras_do_erpnext
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.setup.leituras_do_erpnext import (
	LEITURAS,
	NOMES_USADOS_COMO_CHAVE,
	todos_os_doctypes_lidos,
)

MODULOS_COBERTOS = ()
"""Nenhum módulo de `integracao/` em particular: este arquivo confere a **premissa** de
vários ao mesmo tempo, e atribuí-lo a um deles daria a impressão errada de cobertura.
"""

SEM_COLUNA = frozenset({"name"})
"""Campos que existem em toda tabela do Frappe e não aparecem como coluna declarada.

`name` é a chave primária: `has_column` responde `True`, mas conferi-lo não prova nada sobre
o DocType — todo DocType tem. Fica de fora para que o teste meça só o que é específico.
"""


class TestAsLeiturasDoErpnext(FrappeTestCase):
	def test_todo_doctype_lido_existe(self):
		"""DocType renomeado faz toda leitura dele devolver vazio — e vazio, no Frappe, não
		levanta erro."""
		for doctype in sorted(todos_os_doctypes_lidos()):
			with self.subTest(doctype=doctype):
				self.assertTrue(
					frappe.db.exists("DocType", doctype),
					f"{doctype} não existe neste site — a leitura devolveria vazio em silêncio",
				)

	def test_todo_campo_lido_e_coluna_de_verdade(self):
		"""Teste-âncora. Campo renomeado é o cenário que nenhum outro teste do projeto pega."""
		for doctype, campos in sorted(LEITURAS.items()):
			for campo in sorted(set(campos) - SEM_COLUNA):
				with self.subTest(doctype=doctype, campo=campo):
					self.assertTrue(
						frappe.db.has_column(doctype, campo),
						f"{doctype}.{campo} não é coluna — quem lê isso recebe None sem erro",
					)

	def test_os_nomes_usados_como_chave_existem(self):
		"""Não se lê campo deles, mas o **nome** é comparado. Renomeado, a chave não casa e o
		mapa cai no padrão — sem aviso."""
		for doctype in sorted(NOMES_USADOS_COMO_CHAVE):
			with self.subTest(doctype=doctype):
				self.assertTrue(frappe.db.exists("DocType", doctype))

	def test_a_declaracao_nao_esta_vazia(self):
		"""Se `LEITURAS` esvaziasse, os testes acima passariam sem conferir nada — iterar
		sobre lista vazia nunca falha."""
		self.assertGreaterEqual(len(LEITURAS), 10)
		self.assertGreater(sum(len(c) for c in LEITURAS.values()), 20)

	def test_os_campos_da_efd_estao_entre_os_conferidos(self):
		"""Os dois DocTypes que alimentam arquivo entregue ao Fisco. Se algum dia saírem da
		declaração, o Bloco H e o Bloco K voltam a depender de estrutura não conferida."""
		for doctype, campo in (
			("Work Order", "actual_start_date"),
			("Stock Ledger Entry", "qty_after_transaction"),
		):
			with self.subTest(doctype=doctype):
				self.assertIn(campo, LEITURAS[doctype])
				self.assertTrue(frappe.db.has_column(doctype, campo))
