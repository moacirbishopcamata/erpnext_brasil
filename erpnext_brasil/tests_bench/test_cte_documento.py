# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) do mapeador do CT-e: `Sales Invoice` de transporte → árvore `CTe`.

A suíte pura prova a regra (`test_cte_montagem.py`) e lê o fonte do mapeador
(`test_cte_documento.py` em `tests/`), mas **não o executa**: ele importa `frappe`. Este arquivo
é a primeira vez que `integracao/cte_documento.py` roda contra um site de verdade — fatura,
empresa, clientes, endereços e o contador de numeração vindos do banco.

Teste-âncora: `test_o_numero_alocado_persiste_e_a_reemissao_o_reaproveita`
--------------------------------------------------------------------------------
Prova a costura que a pura não alcança: o número é alocado **depois** da validação, gravado em
`br_numero_cte` da fatura, e relido **por outro caminho** (`frappe.db.get_value`) — não do objeto
que o mapeador mexeu. Um `db_set` que não persistiu só aparece relendo.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_cte_documento
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.fiscal.codigos_de_erro import (
	DOCUMENTO_CTE_DADO_INVALIDO,
	DOCUMENTO_CTE_DADO_OBRIGATORIO_AUSENTE,
)
from erpnext_brasil.fiscal.cte import CteInvalido
from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave
from erpnext_brasil.integracao.cte_documento import montar_cte_do_documento
from erpnext_brasil.tests_bench import test_cfop_sugestao
from erpnext_brasil.tests_bench.test_cfop_sugestao import (
	FILIAL,
	ITEM,
	LISTA,
	MATRIZ,
	OUTRO_GRUPO,
)

MODULOS_COBERTOS = ("cte_documento", "numeracao_fiscal")
"""Declarados, não inferidos — ver `scripts/cobertura_de_bench.py`."""

CAMPOS_DO_CTE = (
	"br_numero_cte",
	"br_natureza_transporte",
	"br_cfop_transporte",
	"br_tomador_cte",
	"br_remetente_cte",
	"br_destinatario_cte",
	"br_produto_predominante",
	"br_valor_carga",
	"br_quantidade_carga",
	"br_unidade_carga",
	"br_tipo_medida_carga",
	"br_cst_icms_cte",
	"br_aliquota_icms_cte",
	"br_reducao_base_icms_cte",
)

REMETENTE = f"Cliente {OUTRO_GRUPO}"
DESTINATARIO = f"Cliente {FILIAL}"
SERIE = "1"
CONTADOR = f"{MATRIZ}-57-{SERIE}"


class TestCteDocumento(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Reaproveita a fixture que já resolveu as sete exigências de configuração do site
		# (template de endereço, lista de preços, item, empresas, clientes).
		test_cfop_sugestao.TestSugestaoDeCfop.setUpClass()

		# O que o CT-e exige a mais e a fixture de CFOP não tem: dados de transportadora na
		# `Company` e cadastro completo de endereço/IE nos clientes. `set_value` direto no
		# banco, de propósito: o que se prova aqui é a leitura, não a validação do cadastro.
		frappe.db.set_value(
			"Company",
			MATRIZ,
			{
				"br_inscricao_estadual": "00000000625213",
				"br_regime_tributario": "Regime Normal",
				"br_serie_cte": SERIE,
				"br_rntrc": "12345678",
			},
			update_modified=False,
		)

		for nome, doctype in ((MATRIZ, "Company"), (REMETENTE, "Customer"), (DESTINATARIO, "Customer")):
			cls._completar_endereco(nome)

			if doctype == "Customer":
				frappe.db.set_value(
					"Customer", nome, "br_indicador_ie", "Não Contribuinte", update_modified=False
				)

		frappe.db.commit()

	@classmethod
	def _completar_endereco(cls, nome: str) -> None:
		endereco = f"{nome}-endereco-Billing"
		frappe.db.set_value(
			"Address",
			endereco,
			{
				"br_numero_endereco": "10",
				"br_bairro": "Centro",
				"br_codigo_municipio_ibge": "1100205",
				"pincode": "76800-000",
			},
			update_modified=False,
		)

	def _fatura(self, **extras) -> frappe.model.document.Document:
		valores = {
			"doctype": "Sales Invoice",
			"company": MATRIZ,
			"customer": DESTINATARIO,
			"currency": "BRL",
			"conversion_rate": 1,
			"selling_price_list": LISTA,
			"price_list_currency": "BRL",
			"plc_conversion_rate": 1,
			"items": [{"item_code": ITEM, "qty": 1, "rate": 100, "uom": "Unidade"}],
			"br_natureza_transporte": "Prestação de serviço de transporte",
			"br_cfop_transporte": "5353",
			"br_modal_cte": "Rodoviário",
			"br_tipo_servico_cte": "Normal",
			"br_municipio_inicio": "1100205",
			"br_municipio_inicio_nome": "Porto Velho",
			"br_uf_inicio": "RO",
			"br_municipio_fim": "1100122",
			"br_municipio_fim_nome": "Ji-Paraná",
			"br_uf_fim": "RO",
			"br_tomador_cte": "Destinatário",
			"br_remetente_cte": REMETENTE,
			"br_destinatario_cte": DESTINATARIO,
			"br_produto_predominante": "Grãos",
			"br_valor_carga": 5000,
			"br_quantidade_carga": 1000,
			"br_unidade_carga": "KG",
			"br_tipo_medida_carga": "PESO BRUTO",
			"br_cst_icms_cte": "00",
			"br_aliquota_icms_cte": 17,
			**extras,
		}
		doc = frappe.get_doc(valores)
		doc.flags.ignore_permissions = True
		doc.insert()

		return frappe.get_doc("Sales Invoice", doc.name)

	def _ultimo_numero(self) -> int:
		return frappe.db.get_value("Numeracao Fiscal", CONTADOR, "ultimo_numero") or 0

	# ---------------------------------------------------------------- campos (2.5)

	def test_os_campos_do_cte_existem_no_formulario_da_fatura(self):
		"""Critério da 2.5: depois do `migrate`, os campos estão de fato no `Sales Invoice`."""
		meta = frappe.get_meta("Sales Invoice")
		faltando = [c for c in CAMPOS_DO_CTE if not meta.has_field(c)]

		self.assertEqual(faltando, [], f"campos declarados e ausentes no site: {faltando}")

	def test_os_campos_do_cte_nao_existem_em_outros_documentos(self):
		for doctype in ("Delivery Note", "Purchase Invoice", "Purchase Receipt", "POS Invoice"):
			with self.subTest(doctype=doctype):
				self.assertFalse(frappe.get_meta(doctype).has_field("br_cst_icms_cte"))

	def test_os_selects_oferecem_exatamente_os_rotulos_traduziveis(self):
		from erpnext_brasil.setup import campos_documento as c

		meta = frappe.get_meta("Sales Invoice")
		pares = {
			"br_modal_cte": c.MODAL_CTE_POR_ROTULO,
			"br_tipo_servico_cte": c.TIPO_SERVICO_CTE_POR_ROTULO,
			"br_tomador_cte": c.TOMADOR_CTE_POR_ROTULO,
			"br_unidade_carga": c.UNIDADE_CARGA_POR_ROTULO,
		}

		for campo, tabela in pares.items():
			with self.subTest(campo=campo):
				opcoes = {o for o in (meta.get_field(campo).options or "").split("\n") if o}
				self.assertEqual(opcoes, set(tabela))

	# ---------------------------------------------------------------- montagem (2.1)

	def test_o_cadastro_vira_arvore_com_a_chave_do_cte(self):
		fatura = self._fatura()
		arvore, chave = montar_cte_do_documento(fatura, "homologacao")
		info = arvore["CTe"]["infCte"]

		self.assertEqual(ler_chave(chave).modelo, "57")
		self.assertEqual(info["@Id"], f"CTe{chave}")
		self.assertEqual(info["ide"]["modal"], "01", "o rótulo 'Rodoviário' não foi traduzido")
		self.assertEqual(info["ide"]["tpAmb"], "2")
		self.assertEqual(info["vPrest"]["vTPrest"], "100.00")
		self.assertEqual(info["imp"]["ICMS"]["ICMS00"]["vICMS"], "17.00")
		self.assertEqual(info["infCTeNorm"]["infModal"]["rodo"]["RNTRC"], "12345678")
		self.assertTrue(info["ide"]["dhEmi"][-6] in "+-", "dhEmi sem fuso horário")

	# ---------------------------------------------------------------- numeração (2.3)

	def test_o_numero_alocado_persiste_e_a_reemissao_o_reaproveita(self):
		"""Teste-âncora. Relê o número do banco, por caminho independente do objeto."""
		fatura = self._fatura()
		antes = self._ultimo_numero()

		arvore, chave = montar_cte_do_documento(fatura, "homologacao")
		numero = arvore["CTe"]["infCte"]["ide"]["nCT"]

		self.assertEqual(self._ultimo_numero(), antes + 1, "a emissão não consumiu exatamente um número")
		self.assertEqual(frappe.db.get_value("Sales Invoice", fatura.name, "br_numero_cte"), numero)
		self.assertEqual(int(ler_chave(chave).numero), int(numero))

		releitura = frappe.get_doc("Sales Invoice", fatura.name)
		_, chave2 = montar_cte_do_documento(releitura, "homologacao")

		self.assertEqual(self._ultimo_numero(), antes + 1, "reemitir consumiu outro número")
		self.assertEqual(int(ler_chave(chave2).numero), int(numero))

	def test_dado_faltando_recusa_sem_consumir_numero(self):
		fatura = self._fatura(br_remetente_cte=None)
		antes = self._ultimo_numero()

		with self.assertRaises(CteInvalido) as erro:
			montar_cte_do_documento(fatura, "homologacao")

		self.assertEqual(erro.exception.codigo, DOCUMENTO_CTE_DADO_OBRIGATORIO_AUSENTE)
		self.assertIn("remetente", str(erro.exception).lower())
		self.assertEqual(self._ultimo_numero(), antes, "a recusa consumiu número da série")
		self.assertFalse(frappe.db.get_value("Sales Invoice", fatura.name, "br_numero_cte"))

	def test_cst_nao_suportado_recusa_como_invalido_sem_consumir_numero(self):
		fatura = self._fatura(br_cst_icms_cte="40")
		frappe.db.set_value("Sales Invoice", fatura.name, "br_cst_icms_cte", "60", update_modified=False)
		fatura = frappe.get_doc("Sales Invoice", fatura.name)
		antes = self._ultimo_numero()

		with self.assertRaises(CteInvalido) as erro:
			montar_cte_do_documento(fatura, "homologacao")

		self.assertEqual(erro.exception.codigo, DOCUMENTO_CTE_DADO_INVALIDO)
		self.assertEqual(self._ultimo_numero(), antes)

	def test_serie_vazia_na_company_recusa_antes_de_alocar(self):
		fatura = self._fatura()
		frappe.db.set_value("Company", MATRIZ, "br_serie_cte", "", update_modified=False)

		try:
			with self.assertRaises(CteInvalido) as erro:
				montar_cte_do_documento(fatura, "homologacao")
		finally:
			frappe.db.set_value("Company", MATRIZ, "br_serie_cte", SERIE, update_modified=False)

		self.assertEqual(erro.exception.codigo, DOCUMENTO_CTE_DADO_OBRIGATORIO_AUSENTE)
		self.assertIn("br_serie_cte", str(erro.exception))
