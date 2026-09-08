# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes reais (bench) da apuração de perdas no estoque.

O que estes testes fecham
---------------------------------
`docs/estoque-estado.md` declarava: *"as duas recusas estão provadas por forma, não por
comportamento"*. Este arquivo é o que troca uma coisa pela outra.

A diferença não é acadêmica. A suíte pura confere que o texto da guarda existe e que o hook
está escrito no `hooks.py`. O que ela **não** pode confirmar é que o Frappe de fato chama
esse hook ao gravar um `Stock Entry` — e um hook declarado que nunca roda é exatamente o
gap de costura que este projeto trata como pior que bug.

Teste-âncora: `test_recusa_perda_em_transferencia`. Ele grava um documento de verdade, com
`purpose = "Material Transfer"` e tipo de perda preenchido, e exige que o **save** falhe.
Se o hook não estivesse ligado, o documento salvaria em silêncio — e o estorno de crédito
de mercadoria que continua na empresa passaria despercebido.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_perda_estoque
"""

import frappe
from frappe.tests.utils import FrappeTestCase

MODULOS_COBERTOS = ("perda_estoque",)
"""Os módulos de `integracao/` que este arquivo exercita — **declarados**, não inferidos.

Lido por `scripts/cobertura_de_bench.py`. A declaração existe porque as duas inferências
óbvias erram, em direções opostas: por **nome de arquivo**, um teste que cobre três módulos
conta como um; por **import**, um teste que exercita o hook através do `save` — sem importar
o módulo, que é a forma mais forte de testar — conta como zero.

Quanto melhor o teste de bench, menos ele importa o módulo que prova.
"""


EMPRESA = "_Teste Consumo Indevido"
"""Reusa a empresa do outro teste de bench: criar uma segunda custaria um plano de contas
inteiro para não provar nada a mais."""

ITEM = "_Teste Perda"
ORIGEM = "Stores - _TCI"
DESTINO = "Finished Goods - _TCI"


class TestPerdaNoEstoque(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		if not frappe.db.exists("UOM", "Unidade"):
			frappe.get_doc({"doctype": "UOM", "uom_name": "Unidade"}).insert(ignore_permissions=True)

		if not frappe.db.exists("Item Group", "Teste GS1"):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": "Teste GS1", "is_group": 0}).insert(
				ignore_permissions=True
			)

		# `Stock Entry Type` é Link obrigatório do `Stock Entry`, e num site que nunca rodou
		# o assistente de configuração a tabela está vazia — o erro que aparece é
		# `LinkValidationError: Could not find Stock Entry Type`, sem relação aparente com o
		# que se está testando.
		for finalidade in ("Material Issue", "Material Transfer", "Material Receipt"):
			if not frappe.db.exists("Stock Entry Type", finalidade):
				frappe.get_doc(
					{
						"doctype": "Stock Entry Type",
						"name": finalidade,
						"purpose": finalidade,
					}
				).insert(ignore_permissions=True)

		if not frappe.db.exists("Item", ITEM):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": ITEM,
					"item_name": "Item de teste de perda",
					"item_group": "Teste GS1",
					"stock_uom": "Unidade",
					"is_stock_item": 1,
					# Sem `valuation_rate` o ERPNext recusa a baixa: "Valuation Rate for the
					# Item is required to do accounting entries". A alternativa seria marcar
					# `allow_zero_valuation_rate` na linha, e aí `total_outgoing_value` sairia
					# zero — a guarda recusaria por "perda sem valor", que não é o que se
					# quer provar aqui.
					"valuation_rate": 100,
				}
			).insert(ignore_permissions=True)

		# Submeter um lançamento de estoque exige **ano fiscal ativo** — o razão contábil
		# precisa saber em que exercício lançar. Site sem assistente de configuração não tem
		# nenhum, e o erro é `FiscalYearError`, que não menciona configuração faltando.
		#
		# Sem `companies` preenchido, o ano fiscal vale para todas as empresas — que é o que
		# se quer num ambiente de teste.
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

		# ⚠️ Fora do `if not exists`, e de propósito.
		#
		# Setup idempotente por existência não incorpora mudança no cadastro: o item criado
		# numa execução anterior, sem `valuation_rate`, sobreviveria à correção e os testes
		# continuariam falhando com "Valuation Rate is required" — erro que aponta para o
		# ERPNext quando a causa é o setup. Aconteceu ao escrever este arquivo.
		frappe.db.set_value("Item", ITEM, "valuation_rate", 100, update_modified=False)

		frappe.db.commit()

	def _lancamento(self, finalidade: str, **extras):
		"""Monta um `Stock Entry` em rascunho — não submetido.

		Rascunho basta: o hook é de `validate`, que roda no `save`. Submeter exigiria saldo
		real e razão contábil, e nada disso muda o que se quer provar.

		⚠️ `Material Transfer` exige **os dois** armazéns; `Material Issue`, só a origem.
		Faltando o destino, o ERPNext recusa com "Target warehouse is mandatory" — e o teste
		passaria a medir a validação dele em vez da nossa.
		"""
		linha = {
			"item_code": ITEM,
			"qty": extras.pop("qty", 1),
			"uom": "Unidade",
			"basic_rate": 100,
		}

		if finalidade == "Material Receipt":
			linha["t_warehouse"] = ORIGEM
		else:
			linha["s_warehouse"] = ORIGEM

		if finalidade == "Material Transfer":
			linha["t_warehouse"] = DESTINO

		doc = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": finalidade,
				"purpose": finalidade,
				"company": EMPRESA,
				"items": [linha],
				**extras,
			}
		)
		doc.flags.ignore_permissions = True

		return doc

	def test_recusa_perda_em_transferencia(self):
		"""Teste-âncora. Prova que o hook está **ligado**, não só escrito.

		Transferência não é perda: a mercadoria continua na empresa, e estornar o crédito
		dela criaria passivo fiscal sem fato gerador. O ERPNext aceitaria este documento
		sem reclamar — a recusa é nossa.
		"""
		doc = self._lancamento("Material Transfer", br_tipo_de_perda="Vencimento")

		with self.assertRaises(frappe.ValidationError) as capturado:
			doc.insert()

		self.assertIn("perda", str(capturado.exception).lower())

	def test_baixa_sem_tipo_de_perda_salva_normalmente(self):
		"""Uma `Material Issue` costuma ser consumo, não perda. Obrigar a escolher um motivo
		transformaria toda requisição de material em declaração de sinistro."""
		doc = self._lancamento("Material Issue")
		doc.insert()

		self.assertTrue(frappe.db.exists("Stock Entry", doc.name))
		self.assertFalse(frappe.db.get_value("Stock Entry", doc.name, "br_perda_estorna_credito"))

	def test_o_resultado_e_gravado_e_relido(self):
		"""Costura: grava por um caminho (o `save` do Frappe, disparando o hook), relê por
		outro (`frappe.db.get_value`, direto no banco).

		⚠️ Escrever num campo não declarado **não levanta erro** no Frappe — o valor some no
		save. Só a releitura independente prova que os três campos existem de verdade.
		"""
		doc = self._lancamento(
			"Material Issue",
			br_tipo_de_perda="Vencimento",
			br_credito_icms_tomado=18,
			br_credito_pis_tomado=1.65,
		)
		doc.insert()

		estorna, credito, total = frappe.db.get_value(
			"Stock Entry",
			doc.name,
			["br_perda_estorna_credito", "br_credito_estornado", "br_custo_total_da_perda"],
		)

		self.assertEqual(1, estorna, "vencimento estorna crédito (LC 87/1996, art. 21)")
		self.assertEqual(19.65, float(credito), "estorna exatamente o que foi creditado")
		self.assertGreater(float(total), float(credito), "o total soma o estoque baixado")

	def test_quebra_normal_do_processo_preserva_o_credito(self):
		"""A exceção que muda tudo: perda inerente ao processo integra o custo de produção e
		**não** estorna — a mercadoria foi consumida pela atividade tributada."""
		doc = self._lancamento(
			"Material Issue",
			br_tipo_de_perda="Quebra normal do processo",
			br_credito_icms_tomado=18,
		)
		doc.insert()

		estorna, credito = frappe.db.get_value(
			"Stock Entry", doc.name, ["br_perda_estorna_credito", "br_credito_estornado"]
		)

		self.assertEqual(0, estorna)
		self.assertEqual(0.0, float(credito))

	def test_apagar_o_tipo_limpa_o_resultado(self):
		"""Sem a limpeza, sobraria um 'crédito a estornar' de uma classificação que não
		existe mais — número órfão na tela, que ninguém sabe de onde veio."""
		doc = self._lancamento("Material Issue", br_tipo_de_perda="Furto ou roubo", br_credito_icms_tomado=18)
		doc.insert()

		self.assertEqual(18.0, float(frappe.db.get_value("Stock Entry", doc.name, "br_credito_estornado")))

		doc.br_tipo_de_perda = ""
		doc.save()

		self.assertEqual(0.0, float(frappe.db.get_value("Stock Entry", doc.name, "br_credito_estornado")))

	def _dar_entrada(self, quantidade: int) -> None:
		"""Cria saldo de verdade no armazém, submetendo uma entrada.

		⚠️ Saldo **real**, e não `difference_amount` forçado num campo. Forçar o valor
		provaria a nossa função e não a integração — e é justamente a integração que estes
		testes existem para provar: quem calcula `difference_amount`, e com que sinal, é o
		ERPNext.
		"""
		entrada = self._lancamento("Material Receipt", qty=quantidade)
		entrada.insert()
		entrada.submit()

	def test_recusa_sobra_de_inventario(self):
		"""Segundo teste-âncora, e o mais sutil da frente de estoque.

		No `Stock Reconciliation` o **sinal** de `difference_amount` é a única coisa que
		separa falta de sobra — e sinal não é classificação fiscal. Contando **mais** do que
		o sistema registra, a diferença é positiva: apareceu mercadoria, não sumiu. Apurar
		perda aí calcularia estorno de crédito em cima de um ganho, e o ERPNext não levantaria
		um único erro.
		"""
		self._dar_entrada(10)

		contagem = frappe.get_doc(
			{
				"doctype": "Stock Reconciliation",
				"company": EMPRESA,
				"purpose": "Stock Reconciliation",
				"expense_account": frappe.db.get_value(
					"Account", {"company": EMPRESA, "account_type": "Stock Adjustment"}, "name"
				),
				"items": [{"item_code": ITEM, "warehouse": ORIGEM, "qty": 15, "valuation_rate": 100}],
				"br_tipo_de_perda": "Ajuste de inventário",
			}
		)
		contagem.flags.ignore_permissions = True

		with self.assertRaises(frappe.ValidationError) as capturado:
			contagem.insert()

		self.assertIn("sobra", str(capturado.exception).lower())
