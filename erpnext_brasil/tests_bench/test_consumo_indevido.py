# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes reais (bench) da guarda de consumo indevido.

Por que este arquivo existe
------------------------------------
A verificação do `cStat 656` foi feita à mão, num script solto, e funcionou. Script solto
prova uma vez; teste prova sempre. O que estava "conferido em bench" na docstring do módulo
passa a estar conferido a cada execução da suíte de bench.

O que só o bench alcança aqui
--------------------------------------
A suíte pura confere **forma**: que a guarda existe, que fica no ponto único, que levanta em
vez de devolver. O que ela não pode conferir é o **comportamento através do banco**:

- que o `autoname` de chave única de fato impede dois registros para o mesmo par;
- que `liberado_em` sai **derivado** pelo controller — e não é só uma linha de código que
  ninguém executou (nome de classe errado faria o Frappe cair no `Document` genérico e o
  campo ficaria vazio, em silêncio);
- que produção e homologação bloqueiam de forma independente **no banco**, não só na função;
- que a guarda relê o bloqueio por um caminho independente de quem o gravou.

Disciplina de costura: grava por um caminho, relê por outro, compara — a mesma que achou os
dois bugs de `certificado_a1.py`.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_consumo_indevido
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.fiscal.consumo_indevido import CARENCIA
from erpnext_brasil.integracao.consumo_indevido import (
	DOCTYPE,
	BloqueadoPorConsumoIndevido,
	bloqueio_ativo,
	chave_do_bloqueio,
	garantir_liberado,
	registrar_resposta,
)

CNPJ = "11.222.333/0001-81"
"""CNPJ com dígitos verificadores válidos — a `Company` o valida no `validate`."""

EMPRESA = "_Teste Consumo Indevido"


class TestGuardaDeConsumoIndevido(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# `Warehouse Type: Transit` é pré-requisito de `Company` no erpnext v16, e num site
		# que nunca rodou o assistente de configuração ele não existe. Descoberto ao criar
		# a primeira empresa deste bench.
		if not frappe.db.exists("Warehouse Type", "Transit"):
			frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)

		if not frappe.db.exists("Company", EMPRESA):
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": EMPRESA,
					"abbr": "_TCI",
					"default_currency": "BRL",
					"country": "Brazil",
					"tax_id": CNPJ,
				}
			).insert(ignore_permissions=True)

		frappe.db.commit()

	def setUp(self):
		self._limpar()

	def tearDown(self):
		self._limpar()

	def _limpar(self):
		"""⚠️ Limpeza explícita, e não rollback.

		`registrar_resposta` faz `commit` de propósito — a rejeição costuma vir num caminho
		que termina em exceção, e o rollback levaria o registro do bloqueio junto. O preço
		é que o `FrappeTestCase` não desfaz estes registros sozinho.
		"""
		for ambiente in ("homologacao", "producao"):
			nome = chave_do_bloqueio(CNPJ, ambiente)

			if frappe.db.exists(DOCTYPE, nome):
				frappe.delete_doc(DOCTYPE, nome, force=True, ignore_permissions=True)

		frappe.db.commit()

	def test_resposta_normal_nao_bloqueia(self):
		"""`cStat 100` é autorização. Bloquear aqui pararia a operação de quem acertou."""
		self.assertFalse(registrar_resposta(CNPJ, "homologacao", "100", "Autorizado", company=EMPRESA))
		self.assertFalse(frappe.db.exists(DOCTYPE, chave_do_bloqueio(CNPJ, "homologacao")))
		self.assertIsNone(garantir_liberado(CNPJ, "homologacao"))

	def test_o_656_bloqueia_e_a_guarda_passa_a_recusar(self):
		"""Teste-âncora: grava por um caminho, e a guarda relê por outro.

		`registrar_resposta` insere o documento; `garantir_liberado` consulta com
		`frappe.db.get_value`. Se a gravação não tivesse chegado ao banco, a guarda deixaria
		passar — e o teste não teria como saber pelo retorno da primeira função.
		"""
		self.assertTrue(registrar_resposta(CNPJ, "homologacao", "656", "Consumo indevido", company=EMPRESA))

		with self.assertRaises(BloqueadoPorConsumoIndevido):
			garantir_liberado(CNPJ, "homologacao")

	def test_liberado_em_sai_derivado_pelo_controller(self):
		"""⚠️ O campo é calculado em `BloqueioSefaz.before_save`. Um nome de classe errado
		faria o Frappe cair no `Document` genérico, o `before_save` nunca rodaria, e este
		campo ficaria **vazio** — sem erro nenhum.

		Relido do banco, não do objeto devolvido pelo `insert`.
		"""
		registrar_resposta(CNPJ, "homologacao", "656", "Consumo indevido", company=EMPRESA)

		inicio, fim = frappe.db.get_value(
			DOCTYPE, chave_do_bloqueio(CNPJ, "homologacao"), ["bloqueado_em", "liberado_em"]
		)

		self.assertIsNotNone(fim, "liberado_em vazio: o controller não rodou")
		self.assertEqual(CARENCIA, frappe.utils.get_datetime(fim) - frappe.utils.get_datetime(inicio))

	def test_o_cnpj_e_gravado_limpo(self):
		"""Com e sem máscara seriam duas chaves para o mesmo CNPJ, e uma delas liberaria a
		transmissão."""
		registrar_resposta(CNPJ, "homologacao", "656", "", company=EMPRESA)

		self.assertEqual(
			"11222333000181",
			frappe.db.get_value(DOCTYPE, chave_do_bloqueio(CNPJ, "homologacao"), "cnpj"),
		)

	def test_os_ambientes_bloqueiam_de_forma_independente(self):
		"""Um bloqueio em homologação não pode parar a emissão real."""
		registrar_resposta(CNPJ, "homologacao", "656", "", company=EMPRESA)

		self.assertIsNotNone(bloqueio_ativo(CNPJ, "homologacao"))
		self.assertIsNone(bloqueio_ativo(CNPJ, "producao"))
		self.assertIsNone(garantir_liberado(CNPJ, "producao"))

	def test_o_segundo_656_reinicia_a_janela_no_mesmo_registro(self):
		"""Dois registros para o mesmo par seriam duas verdades sobre a mesma espera — o
		`autoname` de chave única existe para isso, e só o banco prova que funciona."""
		registrar_resposta(CNPJ, "homologacao", "656", "primeira", company=EMPRESA)
		primeiro = frappe.db.get_value(DOCTYPE, chave_do_bloqueio(CNPJ, "homologacao"), "bloqueado_em")

		registrar_resposta(CNPJ, "homologacao", "656", "segunda", company=EMPRESA)
		registros = frappe.get_all(DOCTYPE, filters={"cnpj": "11222333000181", "ambiente": "homologacao"})
		segundo, mensagem = frappe.db.get_value(
			DOCTYPE, chave_do_bloqueio(CNPJ, "homologacao"), ["bloqueado_em", "mensagem"]
		)

		self.assertEqual(1, len(registros), "o segundo 656 criou um registro paralelo")
		self.assertEqual("segunda", mensagem)
		self.assertGreaterEqual(frappe.utils.get_datetime(segundo), frappe.utils.get_datetime(primeiro))

	def test_bloqueio_vencido_deixa_de_valer(self):
		"""O desbloqueio é automático: passada a hora, a guarda tem de liberar sem que
		ninguém apague o registro."""
		registrar_resposta(CNPJ, "homologacao", "656", "", company=EMPRESA)

		nome = chave_do_bloqueio(CNPJ, "homologacao")
		vencido = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=-2)
		frappe.db.set_value(DOCTYPE, nome, "bloqueado_em", vencido, update_modified=False)
		frappe.db.commit()

		self.assertIsNone(bloqueio_ativo(CNPJ, "homologacao"))
		self.assertIsNone(garantir_liberado(CNPJ, "homologacao"))
		self.assertTrue(frappe.db.exists(DOCTYPE, nome), "o registro não deve ser apagado")
