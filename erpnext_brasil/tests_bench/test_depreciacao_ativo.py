# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes reais (bench) da depreciação fiscal no `Asset`.

MODULOS_COBERTOS declarado abaixo; ver `scripts/cobertura_de_bench.py`.

O que só o bench prova aqui
------------------------------------
`depreciacao_ativo.py` recusa duas configurações que o **ERPNext aceita sem reclamar** —
elas são válidas para outros países. A suíte pura confere que a recusa está escrita; que o
Frappe a execute ao gravar um `Asset`, e que as duas configurações sejam mesmo alcançáveis
pelo formulário, só o site mostra.

E há uma parte que a suíte pura **não tem como** verificar: `instalar_livro_fiscal` e
`instalar_turnos` rodam no `after_migrate`. Um erro ali não aparece em teste nenhum — o
`Finance Book` simplesmente não existiria, e o usuário veria um campo vazio.

Teste-âncora: `test_recusa_metodo_sobre_saldo_residual`
-------------------------------------------------------------------
*Written Down Value* aplica a taxa sobre o saldo residual; o art. 319 do RIR/2018 manda
aplicá-la sobre o **custo de aquisição**. ⚠️ A primeira quota dos dois métodos é
**idêntica** — a divergência só aparece do segundo período em diante, quando ninguém mais
está olhando a configuração. É o tipo de erro que um aviso amarelo não evita, porque o aviso
é clicado sem ler.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_depreciacao_ativo
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.contabil.depreciacao import COEFICIENTE_POR_TURNOS
from erpnext_brasil.integracao.depreciacao_ativo import LIVRO_FISCAL, METODO_EXIGIDO, TURNOS_POR_NOME
from erpnext_brasil.tests_bench import test_cfop_sugestao
from erpnext_brasil.tests_bench.test_cfop_sugestao import MATRIZ

MODULOS_COBERTOS = ("depreciacao_ativo",)
"""Os módulos de `integracao/` que este arquivo exercita — **declarados**, não inferidos.

Lido por `scripts/cobertura_de_bench.py`. A declaração existe porque as duas inferências
óbvias erram, em direções opostas: por **nome de arquivo**, um teste que cobre três módulos
conta como um; por **import**, um teste que exercita o hook através do `save` — sem importar
o módulo, que é a forma mais forte de testar — conta como zero.

Quanto melhor o teste de bench, menos ele importa o módulo que prova.
"""

CATEGORIA = "_Teste Depreciacao"
ITEM_ATIVO = "_Teste Bem"
LOCAL = "_Teste Local"
LIVRO_SOCIETARIO = "_Teste Societario"


class TestDepreciacaoFiscalDoAtivo(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		test_cfop_sugestao.TestSugestaoDeCfop.setUpClass()

		# Um segundo livro, para provar que a guarda **não** o confere. O ERPNext exige
		# nome em todas as linhas quando há mais de um livro ("Finance Book should not be
		# empty since you're using multiple"), então não dá para deixá-lo vazio.
		if not frappe.db.exists("Finance Book", LIVRO_SOCIETARIO):
			frappe.get_doc({"doctype": "Finance Book", "finance_book_name": LIVRO_SOCIETARIO}).insert(
				ignore_permissions=True
			)

		if not frappe.db.exists("Location", LOCAL):
			frappe.get_doc({"doctype": "Location", "location_name": LOCAL}).insert(ignore_permissions=True)

		if not frappe.db.exists("Asset Category", CATEGORIA):
			frappe.get_doc(
				{
					"doctype": "Asset Category",
					"asset_category_name": CATEGORIA,
					"accounts": [
						{
							"company_name": MATRIZ,
							"fixed_asset_account": cls._conta("Fixed Asset"),
							"accumulated_depreciation_account": cls._conta("Accumulated Depreciation"),
							"depreciation_expense_account": cls._conta("Depreciation"),
						}
					],
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Item", ITEM_ATIVO):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": ITEM_ATIVO,
					"item_name": "Bem de teste",
					"item_group": "Teste GS1",
					"stock_uom": "Unidade",
					"is_stock_item": 0,
					"is_fixed_asset": 1,
					"asset_category": CATEGORIA,
				}
			).insert(ignore_permissions=True)

		frappe.db.commit()

	@classmethod
	def _conta(cls, tipo: str) -> str:
		return frappe.db.get_value(
			"Account", {"company": MATRIZ, "account_type": tipo, "is_group": 0}, "name"
		)

	def _ativo(self, **livro):
		"""Um `Asset` com uma linha no livro fiscal, montada a partir de `livro`."""
		linha = {
			"finance_book": LIVRO_FISCAL,
			"depreciation_method": METODO_EXIGIDO,
			"total_number_of_depreciations": 60,
			"frequency_of_depreciation": 1,
			"depreciation_start_date": "2026-10-31",
			**livro,
		}

		doc = frappe.get_doc(
			{
				"doctype": "Asset",
				"item_code": ITEM_ATIVO,
				"asset_name": frappe.generate_hash(length=8),
				"company": MATRIZ,
				"asset_category": CATEGORIA,
				"location": LOCAL,
				"purchase_date": "2026-09-01",
				"available_for_use_date": "2026-09-01",
				"gross_purchase_amount": 10000,
				# `net_purchase_amount` é obrigatório e **não** é derivado do bruto: sem ele,
				# o `Asset` recusa com "Net Purchase Amount is mandatory" antes de qualquer
				# validação nossa rodar — e o teste passaria a medir a exigência do ERPNext.
				"net_purchase_amount": 10000,
				"asset_quantity": 1,
				"calculate_depreciation": 1,
				"finance_books": [linha],
			}
		)
		doc.flags.ignore_permissions = True

		return doc

	# ---------------------------------------------------------------- o que a instalação criou

	def test_o_livro_fiscal_foi_criado_pela_instalacao(self):
		"""`instalar_livro_fiscal` roda no `after_migrate`. Se falhasse, nenhum teste
		acusaria: o `Finance Book` simplesmente não existiria, e o usuário veria um campo
		vazio sem saber por quê."""
		self.assertTrue(frappe.db.exists("Finance Book", LIVRO_FISCAL))

	def test_os_tres_turnos_existem_com_os_coeficientes_da_lei(self):
		"""Art. 323 do RIR/2018: 1,0 / 1,5 / 2,0.

		Os fatores são relidos **do banco** e comparados com `COEFICIENTE_POR_TURNOS`, que é
		a fonte pura. Digitá-los aqui criaria uma terceira cópia do mesmo número.
		"""
		for nome, turnos in TURNOS_POR_NOME.items():
			with self.subTest(turno=nome):
				gravado = frappe.db.get_value("Asset Shift Factor", nome, "shift_factor")

				self.assertIsNotNone(gravado, f"{nome} não foi criado pela instalação")
				self.assertEqual(COEFICIENTE_POR_TURNOS[turnos], float(gravado))

	# ---------------------------------------------------------------- as duas recusas

	def test_recusa_metodo_sobre_saldo_residual(self):
		"""Teste-âncora. ⚠️ A primeira quota é idêntica à do método correto — a divergência
		só aparece do segundo período em diante."""
		with self.assertRaises(frappe.ValidationError) as capturado:
			self._ativo(depreciation_method="Written Down Value").insert()

		self.assertIn("319", str(capturado.exception))

	def test_recusa_rateio_diario(self):
		"""Art. 319, § 2º **dispensa** o ajuste para bens postos em funcionamento ou baixados
		no curso do mês. Ratear por dias deduz a menos, e a diferença atravessa a vida
		inteira do bem."""
		with self.assertRaises(frappe.ValidationError) as capturado:
			self._ativo(daily_prorata_based=1).insert()

		self.assertIn("319", str(capturado.exception))

	def test_a_configuracao_correta_e_aceita(self):
		"""Guarda que recusa tudo não é guarda, é bloqueio. Linear, sem rateio diário, no
		livro fiscal: tem de gravar."""
		ativo = self._ativo()
		ativo.insert()

		self.assertTrue(frappe.db.exists("Asset", ativo.name))

	def test_outro_livro_nao_e_conferido(self):
		"""Os demais livros são do contador, e o método contábil **pode** legitimamente ser
		outro. Conferir todos impediria a depreciação societária de existir."""
		ativo = self._ativo()
		ativo.append(
			"finance_books",
			{
				"finance_book": LIVRO_SOCIETARIO,
				"depreciation_method": "Written Down Value",
				"total_number_of_depreciations": 60,
				"frequency_of_depreciation": 1,
				"depreciation_start_date": "2026-10-31",
			},
		)
		ativo.insert()

		self.assertTrue(frappe.db.exists("Asset", ativo.name))
