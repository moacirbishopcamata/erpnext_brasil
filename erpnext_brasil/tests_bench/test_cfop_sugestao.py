# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes reais (bench) da sugestão de CFOP, incluindo a transferência entre estabelecimentos.

Por que este módulo, e não outro
----------------------------------------
Dos onze módulos de `integracao/` ligados em `hooks.py`, este é o que escreve numa **linha
filha** (`Sales Invoice Item.br_cfop_sugerido`), e escrever em campo de tabela filha é onde
o Frappe engole o valor com mais facilidade: nome errado não levanta erro, o `save` passa, e
o campo volta vazio. Só a releitura independente denuncia.

E é onde vive a decisão mais nova do app: **transferência entre estabelecimentos do mesmo
titular**, escrita em 2026-09-07 e até aqui provada só por forma.

Teste-âncora: `test_grupo_economico_nao_e_transferencia`. Duas empresas do mesmo cadastro
com **raízes de CNPJ diferentes** vendem uma à outra com incidência normal — e o
`is_internal_customer` do ERPNext, sozinho, não distingue isso. Tratar grupo econômico como
titular único deixaria de tributar uma operação tributável, e o CFOP errado seria o primeiro
sintoma. É a única coisa que separa `5102` de `5152`.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_cfop_sugestao
"""

import frappe
from frappe.tests.utils import FrappeTestCase

MATRIZ = "_Teste CFOP Matriz"
FILIAL = "_Teste CFOP Filial"
OUTRO_GRUPO = "_Teste CFOP Outro Grupo"

CNPJ_MATRIZ = "11.222.333/0001-81"
CNPJ_FILIAL = "11.222.333/0002-62"
"""Mesma raiz `11222333`, ordem diferente — é o que define "mesmo titular"."""

CNPJ_OUTRO = "04.252.011/0001-10"
"""Raiz diferente: grupo econômico, não mesmo titular."""

ITEM = "_Teste CFOP"
LISTA = "_Teste CFOP Precos"
UF = "RO"


def _uf_de(nome: str, doctype: str) -> None:
	"""Endereço com UF, sem o qual `cfop_sugestao` **não faz nada**.

	`_mesmo_estado` devolve `None` quando não consegue afirmar a UF dos dois lados, e a
	sugestão sai calada — comportamento correto (não assume mesmo estado por omissão) que,
	num teste, se confunde com "o hook não rodou". Por isso todo participante ganha
	endereço.
	"""
	titulo = f"{nome}-endereco"

	if frappe.db.exists("Address", f"{titulo}-Billing"):
		return

	endereco = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": titulo,
			"address_type": "Billing",
			"address_line1": "Rua de Teste, 1",
			"city": "Porto Velho",
			"state": UF,
			"country": "Brazil",
			"is_primary_address": 1,
			"links": [{"link_doctype": doctype, "link_name": nome}],
		}
	)
	endereco.insert(ignore_permissions=True)


class TestSugestaoDeCfop(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# Quinta exigência de configuração desta série (ver a tabela em
		# `docs/estoque-estado.md`): criar `Address` pede um `Address Template` padrão, e o
		# erro — "No default Address Template found" — manda o leitor para a tela de
		# impressão, longe da causa real, que é site sem assistente de configuração.
		if not frappe.db.exists("Address Template", {"is_default": 1}):
			frappe.get_doc(
				{
					"doctype": "Address Template",
					"country": "Brazil",
					"is_default": 1,
					"template": "{{ address_line1 }}<br>{{ city }} - {{ state }}<br>",
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Warehouse Type", "Transit"):
			frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)

		for nome, abreviacao, cnpj in (
			(MATRIZ, "_TCM", CNPJ_MATRIZ),
			(FILIAL, "_TCF", CNPJ_FILIAL),
			(OUTRO_GRUPO, "_TCO", CNPJ_OUTRO),
		):
			if not frappe.db.exists("Company", nome):
				frappe.get_doc(
					{
						"doctype": "Company",
						"company_name": nome,
						"abbr": abreviacao,
						"default_currency": "BRL",
						"country": "Brazil",
						"tax_id": cnpj,
					}
				).insert(ignore_permissions=True)

			_uf_de(nome, "Company")

		# Sexta exigência: `Sales Invoice` recusa sem lista de preços — e o erro cita três
		# campos (`selling_price_list`, `price_list_currency`, `plc_conversion_rate`) sem
		# dizer que basta criar uma lista e informá-la.
		if not frappe.db.exists("Price List", LISTA):
			frappe.get_doc(
				{
					"doctype": "Price List",
					"price_list_name": LISTA,
					"currency": "BRL",
					"selling": 1,
					"enabled": 1,
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Item Group", "Teste GS1"):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": "Teste GS1", "is_group": 0}).insert(
				ignore_permissions=True
			)

		if not frappe.db.exists("UOM", "Unidade"):
			frappe.get_doc({"doctype": "UOM", "uom_name": "Unidade"}).insert(ignore_permissions=True)

		if not frappe.db.exists("Item", ITEM):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": ITEM,
					"item_name": "Item de teste de CFOP",
					"item_group": "Teste GS1",
					"stock_uom": "Unidade",
					"is_stock_item": 0,
				}
			).insert(ignore_permissions=True)

		# Mercadoria adquirida de terceiros: `5102` na venda, `5152` na transferência.
		# Fora do `if not exists` — setup idempotente por existência não incorpora mudança
		# no cadastro, e o item de uma execução anterior sobreviveria sem o campo.
		frappe.db.set_value("Item", ITEM, "br_producao_propria", 0, update_modified=False)

		cls._cliente(OUTRO_GRUPO, interno=False)
		cls._cliente(FILIAL, interno=True)

		frappe.db.commit()

	@classmethod
	def _cliente(cls, empresa: str, interno: bool) -> str:
		"""Um `Customer` que representa `empresa`. Interno ou não, conforme o caso."""
		nome = f"Cliente {empresa}"

		if not frappe.db.exists("Customer", nome):
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": nome,
					"customer_type": "Company",
					"tax_id": frappe.db.get_value("Company", empresa, "tax_id"),
					"is_internal_customer": 1 if interno else 0,
					"represents_company": empresa if interno else None,
					# ⚠️ Sétima exigência, e só do cliente **interno**: sem a empresa em
					# `companies` ("Allowed To Transact With"), o ERPNext recusa a nota com
					# "Customer not allowed to transact with". É proteção dele contra
					# faturamento cruzado entre empresas do mesmo cadastro — legítima, e
					# invisível para quem só leu a documentação de `is_internal_customer`.
					"companies": [{"company": MATRIZ}] if interno else [],
				}
			).insert(ignore_permissions=True)

		_uf_de(nome, "Customer")

		return nome

	def _venda(self, cliente: str) -> str:
		"""Grava uma `Sales Invoice` em rascunho e devolve o nome."""
		doc = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": MATRIZ,
				"customer": cliente,
				"currency": "BRL",
				"conversion_rate": 1,
				"selling_price_list": LISTA,
				"price_list_currency": "BRL",
				"plc_conversion_rate": 1,
				"items": [{"item_code": ITEM, "qty": 1, "rate": 100, "uom": "Unidade"}],
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()

		return doc.name

	def _cfop_relido(self, nota: str) -> str:
		"""⚠️ Relê da **linha filha**, no banco — não do objeto que o `insert` devolveu.

		Escrever num campo de tabela filha que não existe não levanta erro no Frappe: o
		`save` passa e o valor some. O objeto em memória ainda o mostraria.
		"""
		return frappe.db.get_value("Sales Invoice Item", {"parent": nota}, "br_cfop_sugerido")

	def test_venda_comum_recebe_cfop_de_venda(self):
		"""Linha de base: sem transferência, o CFOP é o de venda de mercadoria de
		terceiros, dentro do estado."""
		nota = self._venda(f"Cliente {OUTRO_GRUPO}")

		self.assertEqual("5102", self._cfop_relido(nota))

	def test_grupo_economico_nao_e_transferencia(self):
		"""Teste-âncora. `Cliente _Teste CFOP Outro Grupo` **não** é interno, e mesmo que
		fosse teria raiz de CNPJ diferente: é venda, com incidência normal.

		Tratar grupo econômico como titular único deixaria de tributar uma operação
		tributável — e o CFOP errado seria o primeiro sintoma.
		"""
		nota = self._venda(f"Cliente {OUTRO_GRUPO}")

		self.assertNotEqual("5152", self._cfop_relido(nota))

	def test_mesmo_titular_recebe_cfop_de_transferencia(self):
		"""Matriz e filial: mesma raiz de CNPJ, cliente interno representando a filial.

		`5152` — transferência de mercadoria adquirida de terceiros —, e não `5102`.
		"""
		nota = self._venda(f"Cliente {FILIAL}")

		self.assertEqual("5152", self._cfop_relido(nota))

	def test_o_campo_da_linha_filha_existe_de_verdade(self):
		"""Se `br_cfop_sugerido` não existisse na tabela filha, todos os testes acima
		leriam `None` e falhariam por igual — sem dizer que a causa é o campo.

		Este confere a coluna direto, para que a causa apareça nomeada.
		"""
		self.assertTrue(frappe.db.has_column("Sales Invoice Item", "br_cfop_sugerido"))
