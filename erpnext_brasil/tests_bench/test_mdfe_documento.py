# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) do mapeador do MDF-e: `Shipment` → árvore `MDFe`.

A suíte pura prova a regra (`test_mdfe_montagem.py`) e lê o fonte do mapeador
(`test_mdfe_documento.py` em `tests/`), mas **não o executa**: ele importa `frappe`. Este arquivo é a
primeira vez que `integracao/mdfe_documento.py` roda contra um site de verdade — `Shipment`, `Delivery
Note` com chave de acesso, endereços, empresa e o contador de numeração vindos do banco.

Teste-âncora: `test_o_numero_alocado_persiste_e_a_reemissao_o_reaproveita`
--------------------------------------------------------------------------------
Prova a costura que a pura não alcança: o número é alocado **depois** da validação, gravado em
`br_numero_mdfe` do `Shipment` (que **não tem** `company`: a série vem de `pickup_company`), e relido
**por outro caminho** (`frappe.db.get_value`) — não do objeto que o mapeador mexeu.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_mdfe_documento
"""

from decimal import Decimal

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave, montar_chave
from erpnext_brasil.fiscal.mdfe import MdfeInvalido
from erpnext_brasil.integracao.mdfe_documento import montar_mdfe_do_documento
from erpnext_brasil.tests_bench.test_cfop_sugestao import FILIAL, ITEM, LISTA, MATRIZ
from erpnext_brasil.tests_bench.test_cte_documento import TestCteDocumento

MODULOS_COBERTOS = ("mdfe_documento", "cte_extracao", "mapeamento_cte")
"""Declarados, não inferidos — ver `scripts/cobertura_de_bench.py`."""

CAMPOS_DO_MDFE = (
	"br_numero_mdfe",
	"br_placa_mdfe",
	"br_tara_mdfe",
	"br_rodado_mdfe",
	"br_condutor_nome_mdfe",
	"br_condutor_cpf_mdfe",
	"br_placa_reboque_mdfe",
	"br_tara_reboque_mdfe",
)

DESTINATARIO = f"Cliente {FILIAL}"
SERIE = "1"
CONTADOR = f"{MATRIZ}-58-{SERIE}"
MUNICIPIO_ENTREGA = ("1100122", "Ji-Paraná")
ENDERECO_COLETA = f"{MATRIZ}-endereco-Billing"
ENDERECO_ENTREGA = f"{DESTINATARIO}-endereco-Billing"
CHAVE_NFE = montar_chave("11", "2610", "11222333000181", "55", "1", "77", "1", "12345678")


class TestMdfeDocumento(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Reaproveita a fixture do CT-e (empresa, clientes, endereços com IBGE) e acrescenta o que o
		# MDF-e exige a mais: série 58 e o município de entrega diferente do de coleta.
		TestCteDocumento.setUpClass()

		frappe.db.set_value("Company", MATRIZ, "br_serie_mdfe", SERIE, update_modified=False)
		frappe.db.set_value(
			"Address",
			ENDERECO_ENTREGA,
			{"br_codigo_municipio_ibge": MUNICIPIO_ENTREGA[0], "city": MUNICIPIO_ENTREGA[1]},
			update_modified=False,
		)
		frappe.db.commit()

	def setUp(self):
		self._criados: list[tuple[str, str]] = []

	def tearDown(self):
		for doctype, nome in reversed(self._criados):
			frappe.delete_doc(doctype, nome, force=True, ignore_permissions=True)

		frappe.db.commit()

	def _nota(self, chave: str | None = CHAVE_NFE) -> str:
		nota = frappe.get_doc(
			{
				"doctype": "Delivery Note",
				"company": MATRIZ,
				"customer": DESTINATARIO,
				"currency": "BRL",
				"conversion_rate": 1,
				"selling_price_list": LISTA,
				"price_list_currency": "BRL",
				"plc_conversion_rate": 1,
				"items": [{"item_code": ITEM, "qty": 1, "rate": 250, "uom": "Unidade"}],
			}
		)
		nota.flags.ignore_permissions = True
		nota.flags.ignore_mandatory = True
		nota.insert()
		self._criados.append(("Delivery Note", nota.name))

		if chave:
			frappe.db.set_value("Delivery Note", nota.name, "br_chave_acesso", chave, update_modified=False)

		return nota.name

	def _shipment(self, nota: str | None = None, **extras) -> frappe.model.document.Document:
		valores = {
			"doctype": "Shipment",
			"pickup_from_type": "Company",
			"pickup_company": MATRIZ,
			"pickup_address_name": ENDERECO_COLETA,
			"delivery_to_type": "Customer",
			"delivery_customer": DESTINATARIO,
			"delivery_address_name": ENDERECO_ENTREGA,
			"br_placa_mdfe": "ABC1D23",
			"br_tara_mdfe": "8500",
			"br_rodado_mdfe": "Cavalo mecânico",
			"br_condutor_nome_mdfe": "João da Silva",
			"br_condutor_cpf_mdfe": "11144477735",
			"shipment_delivery_note": [{"delivery_note": nota or self._nota(), "grand_total": 250}],
			**extras,
		}
		doc = frappe.get_doc(valores)
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.insert()
		self._criados.append(("Shipment", doc.name))
		# O `validate` do core pode recalcular o peso a partir das parcelas; o teste fixa o que quer.
		frappe.db.set_value("Shipment", doc.name, "total_weight", extras.get("total_weight", 1200.5))

		return frappe.get_doc("Shipment", doc.name)

	def _ultimo_numero(self) -> int:
		return frappe.db.get_value("Numeracao Fiscal", CONTADOR, "ultimo_numero") or 0

	# ---------------------------------------------------------------- campos (4.4)

	def test_os_campos_do_mdfe_existem_no_formulario_do_shipment(self):
		meta = frappe.get_meta("Shipment")
		faltando = [c for c in CAMPOS_DO_MDFE if not meta.has_field(c)]

		self.assertEqual(faltando, [], f"campos declarados e ausentes no site: {faltando}")

	def test_o_shipment_continua_sem_company_e_os_campos_nao_vazam(self):
		self.assertFalse(frappe.get_meta("Shipment").has_field("company"))

		for doctype in ("Sales Invoice", "Delivery Note", "Purchase Invoice"):
			with self.subTest(doctype=doctype):
				self.assertFalse(frappe.get_meta(doctype).has_field("br_placa_mdfe"))

	# ---------------------------------------------------------------- montagem (4.1 a 4.3)

	def test_o_cadastro_vira_arvore_com_a_chave_do_mdfe(self):
		shipment = self._shipment()
		arvore, chave = montar_mdfe_do_documento(shipment, "homologacao")
		info = arvore["MDFe"]["infMDFe"]
		descarga = info["infDoc"]["infMunDescarga"]

		self.assertEqual(ler_chave(chave).modelo, "58")
		self.assertEqual(info["@Id"], f"MDFe{chave}")
		self.assertEqual(info["ide"]["tpAmb"], "2")
		self.assertEqual(info["ide"]["UFIni"], "RO")
		self.assertEqual(info["ide"]["infMunCarrega"][0]["cMunCarrega"], "1100205")
		self.assertEqual(descarga[0]["cMunDescarga"], MUNICIPIO_ENTREGA[0])
		self.assertEqual(descarga[0]["infNFe"], [{"chNFe": CHAVE_NFE}])
		self.assertEqual(info["infModal"]["rodo"]["veicTracao"]["placa"], "ABC1D23")
		self.assertEqual(info["infModal"]["rodo"]["veicTracao"]["tpRod"], "03", "rótulo não traduzido")

	def test_o_total_vem_das_notas_referenciadas_e_nao_de_um_campo_livre(self):
		sem_chave = self._nota(chave=None)
		shipment = self._shipment()
		shipment.append("shipment_delivery_note", {"delivery_note": sem_chave, "grand_total": 9999})

		tot = montar_mdfe_do_documento(shipment, "homologacao")[0]["MDFe"]["infMDFe"]["tot"]

		self.assertEqual(Decimal(tot["vCarga"]), Decimal("250"), "a nota sem chave entrou no valor")
		self.assertEqual(tot["qNFe"], "1")
		self.assertEqual(tot["qCarga"], "1200.5")

	def test_o_numero_alocado_persiste_e_a_reemissao_o_reaproveita(self):
		shipment = self._shipment()
		antes = self._ultimo_numero()

		_, chave = montar_mdfe_do_documento(shipment, "homologacao")

		# Releitura por outro caminho: um `db_set` que não persistiu só aparece aqui.
		numero = frappe.db.get_value("Shipment", shipment.name, "br_numero_mdfe")
		self.assertEqual(int(numero), antes + 1)
		self.assertEqual(self._ultimo_numero(), antes + 1)
		self.assertEqual(ler_chave(chave).numero.lstrip("0"), str(int(numero)))

		_, outra = montar_mdfe_do_documento(frappe.get_doc("Shipment", shipment.name), "homologacao")

		self.assertEqual(self._ultimo_numero(), antes + 1, "a reemissão consumiu outro número")
		self.assertEqual(ler_chave(outra).numero, ler_chave(chave).numero)

	# ---------------------------------------------------------------- recusas, sem consumir número

	def _recusa(self, campo: str, trecho: str, shipment) -> None:
		antes = self._ultimo_numero()

		with self.assertRaises(MdfeInvalido) as contexto:
			montar_mdfe_do_documento(shipment, "homologacao")

		self.assertEqual(contexto.exception.campo, campo)
		self.assertIn(trecho, str(contexto.exception))
		self.assertEqual(self._ultimo_numero(), antes, "a recusa consumiu número da série")
		self.assertFalse(frappe.db.get_value("Shipment", shipment.name, "br_numero_mdfe"))

	def test_sem_nota_com_chave_nao_ha_o_que_manifestar(self):
		shipment = self._shipment(nota=self._nota(chave=None))

		self._recusa("municipios_descarga", "nenhum documento fiscal", shipment)

	def test_sem_placa_o_erro_nomeia_o_dado_e_o_cadastro(self):
		shipment = self._shipment(br_placa_mdfe="")

		self._recusa("veiculo_tracao", "placa do veículo de tração", shipment)

	def test_sem_motorista_o_erro_nomeia_o_dado(self):
		shipment = self._shipment(br_condutor_cpf_mdfe="")

		self._recusa("veiculo_tracao", "CPF do motorista", shipment)

	def test_sem_peso_o_erro_nomeia_o_dado(self):
		shipment = self._shipment(total_weight=0)

		self._recusa("peso_carga", "qCarga", shipment)

	def test_coleta_que_nao_parte_de_uma_company_e_recusada(self):
		shipment = self._shipment(pickup_from_type="Customer", pickup_customer=DESTINATARIO)

		self._recusa("pickup_from_type", "Company", shipment)

	def test_serie_vazia_na_company_recusa_antes_de_alocar(self):
		shipment = self._shipment()
		frappe.db.set_value("Company", MATRIZ, "br_serie_mdfe", "", update_modified=False)

		try:
			self._recusa("serie", "série do MDF-e", shipment)
		finally:
			frappe.db.set_value("Company", MATRIZ, "br_serie_mdfe", SERIE, update_modified=False)
