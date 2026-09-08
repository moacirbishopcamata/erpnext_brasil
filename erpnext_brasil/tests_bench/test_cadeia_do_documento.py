# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes reais (bench) dos três hooks restantes da cadeia de `validate` do `Sales Invoice`.

`chave_acesso_documento`, `natureza_sugestao` e `validacao_fiscal` são os últimos módulos
ligados em `hooks.py` que rodam nesta cadeia e não tinham prova de comportamento. Vêm num
arquivo só porque compartilham exatamente os mesmos sete cadastros — separá-los custaria o
setup três vezes sem provar nada além.

Teste-âncora: `test_a_natureza_sai_do_cfop_que_o_hook_anterior_acabou_de_gravar`
--------------------------------------------------------------------------------------------
`sugerir_natureza_operacao` lê `br_cfop_sugerido` **das linhas**, e quem grava esse campo é
`sugerir_cfop_compra_venda`, no **mesmo** `validate`. A ordem em `hooks.py` não é decoração:

    "erpnext_brasil.integracao.cfop_sugestao.sugerir_cfop_compra_venda",
    # Depois do CFOP, nunca antes.
    "erpnext_brasil.integracao.natureza_sugestao.sugerir_natureza_operacao",

Invertida, a natureza leria um campo ainda vazio e sairia **em branco** — sem erro, sem
aviso. A suíte pura só consegue conferir a ordem no **texto** do `hooks.py`; que o Frappe
respeite essa ordem ao executar, só o bench mostra.

Segundo eixo: a chave de acesso aceita a **URL do QR Code** da NFC-e, não só os 44 dígitos.
O leitor 2D do cupom entrega a URL inteira; antes, escanear o cupom colava a URL e a
validação recusava — e o usuário concluía que "o leitor 2D não funciona".

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_cadeia_do_documento
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.tests_bench import test_cfop_sugestao
from erpnext_brasil.tests_bench.test_cfop_sugestao import ITEM, LISTA, MATRIZ, OUTRO_GRUPO

MODULOS_COBERTOS = ("chave_acesso_documento", "natureza_sugestao", "validacao_fiscal")
"""Os módulos de `integracao/` que este arquivo exercita — **declarados**, não inferidos.

Lido por `scripts/cobertura_de_bench.py`. A declaração existe porque as duas inferências
óbvias erram, em direções opostas: por **nome de arquivo**, um teste que cobre três módulos
conta como um; por **import**, um teste que exercita o hook através do `save` — sem importar
o módulo, que é a forma mais forte de testar — conta como zero.

Quanto melhor o teste de bench, menos ele importa o módulo que prova.
"""


CHAVE = "11260911222333000181550010000000421123456781"
"""Chave de 44 posições com dígito verificador correto.

Fixada como literal, e **não** gerada por `montar_chave` no teste: gerar faria o teste
concordar com o cálculo do DV por construção, e um erro no cálculo passaria despercebido
nos dois lados. Este valor foi produzido uma vez e conferido.
"""

URL_DO_QRCODE = f"https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx?p={CHAVE}|2|1|1|abc123def456"
"""O que o leitor 2D do cupom da NFC-e entrega — a chave vem no meio da URL."""


class TestCadeiaDoDocumento(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
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
				"items": [{"item_code": ITEM, "qty": 1, "rate": 100, "uom": "Unidade"}],
				**extras,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert()

		return doc.name

	# ---------------------------------------------------------------- natureza da operação

	def test_a_natureza_sai_do_cfop_que_o_hook_anterior_acabou_de_gravar(self):
		"""Teste-âncora. Prova que a **ordem** dos hooks vale na execução, não só no texto.

		`5102` é venda de mercadoria adquirida de terceiros; a natureza correspondente tem
		de aparecer sozinha, derivada de um campo que outro hook preencheu no mesmo `save`.
		"""
		nota = self._nota()
		cfop, natureza = (
			frappe.db.get_value("Sales Invoice Item", {"parent": nota}, "br_cfop_sugerido"),
			frappe.db.get_value("Sales Invoice", nota, "br_natureza_operacao"),
		)

		self.assertEqual("5102", cfop)
		self.assertTrue(natureza, "natureza vazia: o CFOP ainda não estava gravado quando ela rodou")
		self.assertLessEqual(len(natureza), 60, "o limite do XSD da NF-e é 60")

	def test_a_natureza_escrita_pelo_usuario_nao_e_sobrescrita(self):
		"""Sugestão preenche lacuna; não corrige quem já decidiu. Sobrescrever apagaria a
		descrição que o usuário escolheu, e ele só descobriria na nota emitida."""
		escolhida = "Remessa em bonificação"
		nota = self._nota(br_natureza_operacao=escolhida)

		self.assertEqual(escolhida, frappe.db.get_value("Sales Invoice", nota, "br_natureza_operacao"))

	# ---------------------------------------------------------------- chave de acesso

	def test_a_chave_sem_mascara_sobrevive_ao_save(self):
		nota = self._nota(br_chave_acesso=CHAVE)

		self.assertEqual(CHAVE, frappe.db.get_value("Sales Invoice", nota, "br_chave_acesso"))

	def test_a_url_do_qrcode_vira_chave(self):
		"""Segundo eixo. O leitor 2D do cupom entrega a URL inteira; o campo guarda os 44
		dígitos, que é o valor canônico de sempre."""
		nota = self._nota(br_chave_acesso=URL_DO_QRCODE)

		self.assertEqual(CHAVE, frappe.db.get_value("Sales Invoice", nota, "br_chave_acesso"))

	def test_chave_com_digito_errado_e_recusada(self):
		"""⚠️ Trocar **um** dígito produz uma chave que parece certa: 44 posições, só
		números. Sem a conferência do DV, ela entraria no documento e só a SEFAZ recusaria —
		depois de a nota já ter sido gravada."""
		quebrada = CHAVE[:-1] + ("0" if CHAVE[-1] != "0" else "9")

		with self.assertRaises(frappe.ValidationError) as capturado:
			self._nota(br_chave_acesso=quebrada)

		self.assertIn("chave", str(capturado.exception).lower())

	def test_campo_vazio_nao_e_erro(self):
		"""A maioria das notas não tem chave até serem emitidas. Exigir aqui impediria de
		gravar rascunho."""
		nota = self._nota()

		self.assertFalse(frappe.db.get_value("Sales Invoice", nota, "br_chave_acesso"))

	# ---------------------------------------------------------------- classificação fiscal

	def test_classificacao_pela_metade_e_recusada(self):
		"""`validacao_fiscal` roda **antes** da apuração, e é essa ordem que faz sentido: não
		há por que calcular imposto de um item cuja combinação a SEFAZ recusaria.

		Preencher `cClassTrib` **sem** o CST do IBS/CBS é classificação pela metade, e a
		guarda recusa antes de qualquer conferência de compatibilidade entre os dois. É a
		recusa mais valiosa: meio preenchido é o estado que passa despercebido, porque o
		formulário mostra um campo respondido.

		📌 Este teste começou mirando outra coisa — um par CST/cClassTrib **incompatível** —
		e o site mostrou que a guarda de completude dispara primeiro. Ficou como está porque
		testar o que o código faz vale mais que testar o que eu imaginei que ele faria.
		"""
		with self.assertRaises(frappe.ValidationError) as capturado:
			self._nota(
				items=[
					{
						"item_code": ITEM,
						"qty": 1,
						"rate": 100,
						"uom": "Unidade",
						"br_cclasstrib": "000001",
					}
				]
			)

		mensagem = str(capturado.exception).lower()

		self.assertIn("cst", mensagem)
		self.assertIn("item 1", mensagem, "a mensagem precisa dizer qual linha")

	def test_documento_sem_classificacao_passa(self):
		"""A guarda não pode exigir classificação de quem não a informou: a maioria das
		notas de teste e de rascunho não tem CST nenhum, e recusá-las impediria de gravar."""
		nota = self._nota()

		self.assertTrue(frappe.db.exists("Sales Invoice", nota))
