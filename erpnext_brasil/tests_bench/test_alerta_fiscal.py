# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes reais (bench) do aviso de ambiente de homologação e da prontidão para a EFD.

O que só o bench prova
------------------------------
`avisar_ambiente_de_homologacao` está ligado em `on_submit`, e `on_submit` é o único hook
deste app que **não** roda no `save`. A suíte pura confere que ele está declarado no
`hooks.py`; que o Frappe o execute ao aprovar o documento — e não ao gravá-lo — só o site
mostra.

O aviso é `msgprint`, não `throw`: ele informa e deixa passar. Um teste que só confirmasse
"não levantou" passaria com o hook desligado, então a verificação é sobre a **mensagem
aparecer** em `frappe.message_log`.

Teste-âncora: `test_nao_avisa_quando_nao_ha_chave`
-------------------------------------------------------------
Sem `br_chave_acesso` o documento não foi transmitido a lugar nenhum, e o ambiente é
irrelevante. Avisar ali seria ruído em **todo lançamento manual** — e alerta ruidoso é
alerta ignorado, o que estraga também os avisos que importam. É a condição mais fácil de
perder num refactor, porque removê-la não quebra nada: só faz o aviso aparecer sempre.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_alerta_fiscal
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.integracao.alerta_fiscal import verificar_prontidao_efd
from erpnext_brasil.tests_bench import test_cfop_sugestao
from erpnext_brasil.tests_bench.test_cadeia_do_documento import CHAVE
from erpnext_brasil.tests_bench.test_cfop_sugestao import ITEM, LISTA, MATRIZ, OUTRO_GRUPO

PRODUCAO = "Produção"
HOMOLOGACAO = "Homologação"
"""Os valores exatos das opções do `Select` `br_ambiente_sefaz`."""

MODULOS_COBERTOS = ("alerta_fiscal",)
"""Os módulos de `integracao/` que este arquivo exercita — **declarados**, não inferidos.

Lido por `scripts/cobertura_de_bench.py`.
"""


class TestAlertaFiscal(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		test_cfop_sugestao.TestSugestaoDeCfop.setUpClass()

		ano = str(frappe.utils.now_datetime().year)

		if not frappe.db.exists("Fiscal Year", ano):
			frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year": ano,
					"year_start_date": f"{ano}-01-01",
					"year_end_date": f"{ano}-12-31",
				}
			).insert(ignore_permissions=True)

		frappe.db.commit()

	def _ambiente(self, valor: str) -> None:
		"""⚠️ Os valores são `"Produção"` e `"Homologação"` — com maiúscula e acento, como
		nas opções do `Select`.

		Escrevi `"producao"` na primeira versão e o teste acusou o aviso aparecendo em
		produção, o que parecia bug do app. Não era: `frappe.db.set_value` **não valida as
		opções do Select**, então o valor inválido entrou no campo e o código, corretamente,
		o tratou como "não é produção" e avisou.

		Fica o registro de que a gravação crua contorna a validação — e de que o
		comportamento diante de valor desconhecido é avisar, que é a direção segura.
		"""
		frappe.db.set_value("Company", MATRIZ, "br_ambiente_sefaz", valor)
		frappe.db.commit()

	def _submeter(self, **extras) -> str:
		"""Grava **e aprova** — o hook em questão é de `on_submit`, não de `validate`."""
		doc = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": MATRIZ,
				"customer": f"Cliente {OUTRO_GRUPO}",
				"currency": "BRL",
				"conversion_rate": 1,
				"selling_price_list": LISTA,
				"price_list_currency": "BRL",
				"plc_conversion_rate": 1,
				"debit_to": frappe.db.get_value(
					"Account", {"company": MATRIZ, "account_type": "Receivable", "is_group": 0}, "name"
				),
				"items": [
					{
						"item_code": ITEM,
						"qty": 1,
						"rate": 100,
						"uom": "Unidade",
						"income_account": frappe.db.get_value(
							"Account",
							{"company": MATRIZ, "root_type": "Income", "is_group": 0},
							"name",
						),
						"cost_center": frappe.db.get_value(
							"Cost Center", {"company": MATRIZ, "is_group": 0}, "name"
						),
					}
				],
				**extras,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()

		frappe.message_log.clear()
		doc.submit()

		return doc.name

	def _mensagens(self) -> str:
		"""Tudo o que o Frappe acumulou em `message_log`, como um texto só.

		⚠️ `msgprint` **não** levanta: um teste que só confirmasse "não deu erro" passaria
		com o hook desligado. É a mensagem que precisa ser vista.
		"""
		return " ".join(str(m) for m in frappe.message_log).lower()

	def test_avisa_quando_o_ambiente_e_homologacao(self):
		self._ambiente(HOMOLOGACAO)
		self._submeter(br_chave_acesso=CHAVE)

		mensagens = self._mensagens()

		self.assertIn("homologa", mensagens)
		self.assertIn("valor fiscal", mensagens, "o aviso precisa dizer o que está em jogo")

	def test_nao_avisa_em_producao(self):
		"""Quem já está em produção não precisa do aviso — e recebê-lo todo dia o ensinaria
		a fechar sem ler.

		O aviso diz "não tem valor fiscal": aparecer sobre uma nota **real** não seria só
		ruído, faria o usuário duvidar de um documento válido.
		"""
		self._ambiente(PRODUCAO)
		self._submeter(br_chave_acesso=CHAVE)

		self.assertNotIn("valor fiscal", self._mensagens())

	def test_nao_avisa_quando_nao_ha_chave(self):
		"""Teste-âncora. Sem chave, o documento não foi transmitido e o ambiente é
		irrelevante: avisar seria ruído em todo lançamento manual.

		É a condição mais fácil de perder num refactor, porque removê-la não quebra nada —
		só faz o aviso aparecer sempre, até ninguém mais o ler.
		"""
		self._ambiente(HOMOLOGACAO)
		self._submeter()

		self.assertNotIn("valor fiscal", self._mensagens())

	# ---------------------------------------------------------------- prontidão para a EFD

	def test_a_prontidao_lista_o_que_falta(self):
		"""Método exposto ao Desk: precisa responder sem levantar, mesmo num cadastro
		incompleto — que é justamente quando o usuário o chama."""
		resultado = verificar_prontidao_efd(MATRIZ)

		self.assertIsInstance(resultado, dict)
		self.assertTrue(resultado, "prontidão vazia: a varredura não rodou")

	def test_a_prontidao_respeita_o_limite(self):
		"""O retorno precisa dizer se houve corte, senão passa a falsa impressão de que o
		resto do cadastro está limpo."""
		resultado = verificar_prontidao_efd(MATRIZ, limite_de_itens=1)

		self.assertIn("truncado", " ".join(resultado.keys()).lower() + " " + str(resultado).lower())
