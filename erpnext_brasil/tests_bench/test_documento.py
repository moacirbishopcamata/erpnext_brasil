# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes reais (bench) da apuração de impostos — o módulo do gap 1.2-bis.

Por que este módulo importa mais que os outros
--------------------------------------------------------
`docs/gaps.md`, seção 1.2-bis: *"O maior de todos: a apuração de impostos lia 29 campos
inexistentes"*. O hook estava ligado, o cálculo estava certo, e **nada acontecia** — porque
os campos que ele lia e escrevia não existiam no site.

Foi o maior gap de costura já encontrado no projeto, e até aqui a garantia de que ele
continua pago era a suíte pura conferindo declaração de campo. Declaração e coluna são
coisas diferentes: um `Custom Field` declarado e não instalado passa na suíte pura e falha
no site.

Teste-âncora: `test_os_campos_calculados_voltam_do_banco`. Grava uma nota de verdade e relê
**cada** campo de imposto da linha filha por `frappe.db.get_value`. Se algum não existisse,
o `linha.set(campo, valor)` do módulo passaria em silêncio — o Frappe não reclama de campo
inexistente — e a releitura devolveria `None`.

Reusa as empresas e o item de `test_cfop_sugestao`: os dois exercitam a mesma cadeia de
`doc_events` do `Sales Invoice`, e duplicar o cenário custaria sete cadastros a mais sem
provar nada além.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_documento
"""

import frappe
from frappe.tests.utils import FrappeTestCase

# ⚠️ Importa-se o **módulo**, não a classe de teste.
#
# `from ... import TestSugestaoDeCfop` liga o nome da classe a este módulo, e o coletor do
# unittest a encontra duas vezes: os quatro testes do CFOP rodavam de novo aqui. Não
# quebrava nada — só inflava a contagem e o tempo, e mascarava de qual arquivo veio a falha.
from erpnext_brasil.tests_bench import test_cfop_sugestao
from erpnext_brasil.tests_bench.test_cfop_sugestao import ITEM, LISTA, MATRIZ, OUTRO_GRUPO

MODULOS_COBERTOS = ("documento",)
"""Os módulos de `integracao/` que este arquivo exercita — **declarados**, não inferidos.

Lido por `scripts/cobertura_de_bench.py`. A declaração existe porque as duas inferências
óbvias erram, em direções opostas: por **nome de arquivo**, um teste que cobre três módulos
conta como um; por **import**, um teste que exercita o hook através do `save` — sem importar
o módulo, que é a forma mais forte de testar — conta como zero.

Quanto melhor o teste de bench, menos ele importa o módulo que prova.
"""


CAMPOS_CALCULADOS = (
	"br_base_icms",
	"br_valor_icms",
	"br_valor_ipi",
	"br_ipi_na_base_icms",
	"br_base_pis_cofins",
	"br_valor_pis",
	"br_valor_cofins",
	"br_base_ibs_cbs",
	"br_valor_ibs",
	"br_valor_cbs",
)
"""Tudo o que `mapeamento.resultado_para_campos` devolve, e que o módulo grava na linha.

Fixado aqui de propósito: a lista é o **contrato** entre o cálculo e o formulário. Derivá-la
do próprio `resultado_para_campos` faria o teste concordar com o código por construção — e
um campo removido do dicionário sairia da lista sem que nada acusasse.
"""


class TestApuracaoNoDocumento(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# Os mesmos sete cadastros que `test_cfop_sugestao` prepara. Chamar o `setUpClass`
		# dele é mais honesto que copiar: se as exigências do ERPNext mudarem, muda num
		# lugar só.
		test_cfop_sugestao.TestSugestaoDeCfop.setUpClass()

	def _nota(self, **extras) -> str:
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
				"items": [{"item_code": ITEM, "qty": 2, "rate": 500, "uom": "Unidade"}],
				**extras,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()

		return doc.name

	def _linha(self, nota: str, campos):
		"""⚠️ Relê a linha filha **do banco**, não do objeto devolvido pelo `insert`.

		É a diferença que dá sentido ao teste: `linha.set(campo, valor)` num campo que não
		existe não levanta erro, e o objeto em memória mostraria o valor mesmo assim.
		"""
		return frappe.db.get_value("Sales Invoice Item", {"parent": nota}, campos, as_dict=True)

	def test_os_campos_calculados_voltam_do_banco(self):
		"""Teste-âncora do gap 1.2-bis: os campos existem **como coluna**, não só como
		declaração."""
		nota = self._nota()
		lidos = self._linha(nota, list(CAMPOS_CALCULADOS))

		self.assertIsNotNone(lidos, "nenhuma linha encontrada para a nota")

		for campo in CAMPOS_CALCULADOS:
			with self.subTest(campo=campo):
				self.assertIn(campo, lidos)
				self.assertIsNotNone(lidos[campo], f"{campo} voltou vazio: o hook não gravou")

	def test_as_colunas_existem_de_verdade(self):
		"""Separado do âncora para que a causa apareça nomeada.

		Sem ele, um campo faltando faria o teste acima falhar com "voltou vazio", que também
		é o sintoma de o hook não ter rodado — dois problemas com o mesmo sintoma.
		"""
		for campo in CAMPOS_CALCULADOS:
			with self.subTest(campo=campo):
				self.assertTrue(
					frappe.db.has_column("Sales Invoice Item", campo),
					f"{campo} não é coluna de Sales Invoice Item",
				)

	def test_a_base_do_icms_acompanha_o_valor_da_linha(self):
		"""Duas unidades a 500 dão 1.000 de mercadoria. A base do ICMS parte daí — o número
		exato depende de CST e alíquota, mas **zero** significaria que o cálculo não rodou.
		"""
		nota = self._nota()
		lidos = self._linha(nota, ["br_base_icms", "amount"])

		self.assertEqual(1000.0, float(lidos["amount"]))
		self.assertGreater(float(lidos["br_base_icms"]), 0, "base zerada: a apuração não rodou")

	def test_o_escape_desliga_a_apuracao(self):
		"""`br_apurar_impostos = 0` é o escape consciente para documento importado de
		terceiro: recalcular sobre os impostos do emitente produziria valores que não
		conferem com o XML recebido.

		O teste prova que o escape **desliga de verdade**, e não só está escrito.
		"""
		nota = self._nota(br_apurar_impostos=0)
		lidos = self._linha(nota, ["br_base_icms", "br_valor_icms"])

		self.assertEqual(0.0, float(lidos["br_base_icms"] or 0))
		self.assertEqual(0.0, float(lidos["br_valor_icms"] or 0))

	def test_com_aliquota_o_imposto_sai_calculado(self):
		"""A alíquota do ICMS vive **na linha**, não no item nem na empresa.

		⚠️ Consequência que este teste registra: uma linha sem `br_aliquota_icms` produz
		base calculada e **imposto zero**, sem aviso. É correto — a alíquota depende de CST,
		UF e produto, e inventar um padrão seria pior —, mas explica por que a primeira
		versão deste teste esperava imposto onde não havia: ele media um documento sem
		classificação fiscal.

		Com 17,5% sobre 1.000, o valor sai de verdade.
		"""
		nota = self._nota(
			items=[
				{
					"item_code": ITEM,
					"qty": 2,
					"rate": 500,
					"uom": "Unidade",
					"br_aliquota_icms": 17.5,
				}
			]
		)
		lidos = self._linha(nota, ["br_base_icms", "br_valor_icms"])

		self.assertEqual(1000.0, float(lidos["br_base_icms"]))
		self.assertEqual(175.0, float(lidos["br_valor_icms"]))

	def test_a_apuracao_e_ligada_por_padrao(self):
		"""`doc.get("br_apurar_impostos", True)` — ausente significa **ligado**.

		Se o padrão fosse desligado, todo documento novo sairia sem imposto, e o sintoma
		seria idêntico ao do gap 1.2-bis: hook ligado, nada acontecendo. Mede-se pela
		**base**, que é calculada mesmo sem alíquota — ver o teste acima.
		"""
		nota = self._nota()

		self.assertGreater(float(self._linha(nota, ["br_base_icms"])["br_base_icms"] or 0), 0)
