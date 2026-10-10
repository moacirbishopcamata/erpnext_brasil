# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) da consulta de CNPJ: o Frappe de verdade, a rede trocada por um duplo.

A regra de sugerir só a lacuna está provada sem Frappe em `tests/test_cadastro_cnpj.py`; a costura com JS,
`hooks.py` e campos, em `tests/test_consulta_cnpj.py`. O que **só** o bench mostra é o que depende do site:
o cache no Redis de verdade (inclusive que serviço fora do ar **não** é guardado e que o 404 é), as chaves de
`site_config` (desligar; lista própria de provedores), a permissão e a criação do `Address` com o vínculo.

A chamada HTTP é injetada (`buscar=`), fora do endpoint exposto — nenhum teste aqui usa a rede. A resposta é a
real do Banco do Brasil (CNPJ de teste público), colhida em 2026-10-10.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_consulta_cnpj
"""

import json
from unittest.mock import Mock

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.integracao import consulta_cnpj as c

MODULOS_COBERTOS = ("consulta_cnpj",)
"""Declarado, não inferido — o módulo é chamado pelo JS e não consta em `hooks.py`."""

CNPJ = "00000000000191"
BB = json.dumps(
	{
		"cnpj": CNPJ,
		"razao_social": "BANCO DO BRASIL SA",
		"nome_fantasia": "DIRECAO GERAL",
		"situacao_cadastral": 2,
		"descricao_situacao_cadastral": "ATIVA",
		"data_situacao_cadastral": "2005-11-03",
		"cnae_fiscal": 6422100,
		"cnae_fiscal_descricao": "Bancos múltiplos, com carteira comercial",
		"natureza_juridica": "Sociedade de Economia Mista",
		"porte": "DEMAIS",
		"opcao_pelo_simples": False,
		"opcao_pelo_mei": False,
		"identificador_matriz_filial": 1,
		"descricao_tipo_de_logradouro": "QUADRA",
		"logradouro": "SAUN QUADRA 5 BLOCO B TORRE I, II, III",
		"numero": "SN",
		"complemento": "ANDAR T I SL S101 A S1602",
		"bairro": "ASA NORTE",
		"cep": "70040912",
		"municipio": "BRASILIA",
		"uf": "DF",
		"codigo_municipio_ibge": 5300108,
		"qsa": [{"nome_socio": "SOCIO FICTICIO UM"}],
	}
).encode()

BAIXADA = json.dumps(
	{**json.loads(BB), "situacao_cadastral": 8, "descricao_situacao_cadastral": "BAIXADA"}
).encode()
NAO_ACHADO = b'{"message": "CNPJ nao encontrado"}'
CLIENTE = "Teste Consulta CNPJ"


def _limpar() -> None:
	c._cache().delete_value(c.PREFIXO_CACHE + CNPJ)


def _apagar_cliente() -> None:
	for link in frappe.get_all(
		"Dynamic Link", {"link_name": CLIENTE, "parenttype": "Address"}, pluck="parent"
	):
		frappe.delete_doc("Address", link, force=True)

	if frappe.db.exists("Customer", CLIENTE):
		frappe.delete_doc("Customer", CLIENTE, force=True)


class TestConsultaCnpj(FrappeTestCase):
	def setUp(self):
		_limpar()

	def tearDown(self):
		_limpar()
		frappe.conf.pop(c.CHAVE_CONFIGURACAO, None)
		frappe.conf.pop(c.CHAVE_PROVEDORES, None)
		frappe.set_user("Administrator")

	# ------------------------------------------------------------------- só a lacuna

	def test_preenche_so_a_lacuna_e_nunca_o_nome_que_o_usuario_digitou(self):
		"""Teste-âncora. O nome já informado manda sobre o cadastro externo."""
		r = c.consultar(
			"Customer", CNPJ, {"customer_name": "Nome que eu digitei"}, buscar=Mock(return_value=(200, BB))
		)

		self.assertEqual(r["situacao"], c.ENCONTRADO)
		self.assertNotIn("customer_name", r["preencher"])

	def test_com_o_nome_vazio_sugere_a_razao_social(self):
		r = c.consultar("Customer", CNPJ, {"customer_name": ""}, buscar=Mock(return_value=(200, BB)))

		self.assertEqual(r["preencher"], {"customer_name": "BANCO DO BRASIL SA"})

	def test_situacao_que_nao_e_ativa_vira_aviso_e_nao_bloqueio(self):
		r = c.consultar("Supplier", CNPJ, buscar=Mock(return_value=(200, BAIXADA)))

		self.assertEqual(r["situacao"], c.ENCONTRADO)
		self.assertFalse(r["ativo"])
		self.assertTrue(r["aviso"])

	def test_o_resumo_nao_traz_socios(self):
		r = c.consultar("Customer", CNPJ, buscar=Mock(return_value=(200, BB)))

		self.assertNotIn("SOCIO FICTICIO", json.dumps(r, ensure_ascii=False))

	def test_o_que_vem_do_navegador_so_e_lido_no_campo_conhecido(self):
		r = c.consultar(
			"Customer", CNPJ, '{"customer_name": "", "owner": "x"}', buscar=Mock(return_value=(200, BB))
		)

		self.assertEqual(set(r["preencher"]), {"customer_name"})

	def test_json_invalido_do_navegador_nao_derruba_a_consulta(self):
		r = c.consultar("Customer", CNPJ, "{isso nao e json", buscar=Mock(return_value=(200, BB)))

		self.assertEqual(r["situacao"], c.ENCONTRADO)

	# ------------------------------------------------------------------- cache e indisponibilidade

	def test_a_segunda_consulta_vem_do_cache_e_nao_da_rede(self):
		buscar = Mock(return_value=(200, BB))

		c.consultar("Customer", CNPJ, buscar=buscar)
		c.consultar("Customer", CNPJ, buscar=buscar)

		self.assertEqual(buscar.call_count, 1)

	def test_cnpj_inexistente_tambem_e_guardado(self):
		buscar = Mock(return_value=(404, NAO_ACHADO))

		r = c.consultar("Customer", CNPJ, buscar=buscar)
		c.consultar("Customer", CNPJ, buscar=buscar)

		self.assertEqual(r["situacao"], c.NAO_ENCONTRADO)
		self.assertEqual(buscar.call_count, 1, "o 404 é a resposta; um provedor só, uma vez")

	def test_servico_fora_do_ar_nao_e_guardado(self):
		"""Se a falha fosse para o cache, a rede voltaria e o usuário continuaria sem resposta por uma hora."""
		fora = Mock(side_effect=OSError("sem rede"))

		self.assertEqual(c.consultar("Customer", CNPJ, buscar=fora)["situacao"], c.INDISPONIVEL)

		buscar = Mock(return_value=(200, BB))

		self.assertEqual(c.consultar("Customer", CNPJ, buscar=buscar)["situacao"], c.ENCONTRADO)
		buscar.assert_called_once()

	def test_limite_de_uso_do_provedor_cai_no_proximo(self):
		buscar = Mock(side_effect=[(429, b""), (200, BB)])

		r = c.consultar("Customer", CNPJ, buscar=buscar)

		self.assertEqual(r["situacao"], c.ENCONTRADO)
		self.assertEqual(buscar.call_count, 2)
		self.assertIn("minhareceita", r["fonte"])

	def test_404_nao_e_repetido_no_outro_provedor(self):
		buscar = Mock(return_value=(404, NAO_ACHADO))

		c.consultar("Customer", CNPJ, buscar=buscar)

		self.assertEqual(buscar.call_count, 1)

	def test_cnpj_invalido_nao_chega_a_rede(self):
		buscar = Mock()

		r = c.consultar("Customer", "00000000000192", buscar=buscar)

		self.assertEqual(r["situacao"], c.INVALIDO)
		buscar.assert_not_called()

	# ------------------------------------------------------------------- configuração do site

	def test_a_consulta_pode_ser_desligada_no_site_config(self):
		buscar = Mock(return_value=(200, BB))
		frappe.conf[c.CHAVE_CONFIGURACAO] = False

		r = c.consultar("Customer", CNPJ, buscar=buscar)

		self.assertEqual(r["situacao"], c.INDISPONIVEL)
		buscar.assert_not_called()

	def test_lista_propria_de_provedores_substitui_os_padrao(self):
		buscar = Mock(return_value=(200, BB))
		frappe.conf[c.CHAVE_PROVEDORES] = ["https://cnpj.interno.example/{cnpj}"]

		c.consultar("Customer", CNPJ, buscar=buscar)

		buscar.assert_called_once_with(f"https://cnpj.interno.example/{CNPJ}")

	def test_lista_configurada_invalida_nao_volta_aos_provedores_padrao(self):
		"""Quem configurou o próprio provedor quis evitar terceiros: a consulta fica indisponível."""
		buscar = Mock(return_value=(200, BB))
		frappe.conf[c.CHAVE_PROVEDORES] = ["http://usuario:senha@host.example/{cnpj}", "sem-marcador"]

		r = c.consultar("Customer", CNPJ, buscar=buscar)

		self.assertEqual(r["situacao"], c.INDISPONIVEL)
		buscar.assert_not_called()

	# ------------------------------------------------------------------- permissão

	def test_usuario_sem_permissao_e_recusado(self):
		frappe.set_user("Guest")

		with self.assertRaises(frappe.PermissionError):
			c.consultar_cnpj("Customer", CNPJ)

		with self.assertRaises(frappe.PermissionError):
			c.criar_endereco_pelo_cnpj("Customer", CLIENTE)

	def test_doctype_fora_dos_tres_cadastros_e_recusado(self):
		with self.assertRaises(frappe.PermissionError):
			c.consultar_cnpj("User", CNPJ)

	# ------------------------------------------------------------------- endereço

	def _cliente(self) -> None:
		_apagar_cliente()
		frappe.get_doc(
			{"doctype": "Customer", "customer_name": CLIENTE, "customer_type": "Company", "tax_id": CNPJ}
		).insert()

	def test_cria_o_endereco_vinculado_quando_a_parte_nao_tem_nenhum(self):
		self._cliente()

		try:
			r = c.criar_endereco("Customer", CLIENTE, buscar=Mock(return_value=(200, BB)))

			self.assertEqual(r["situacao"], "criado")

			endereco = frappe.get_doc("Address", r["endereco"])

			self.assertEqual(endereco.pincode, "70040-912")
			self.assertEqual(endereco.br_codigo_municipio_ibge, "5300108")
			self.assertEqual([(x.link_doctype, x.link_name) for x in endereco.links], [("Customer", CLIENTE)])

			# relê por outro caminho: o vínculo existe de fato no banco
			self.assertTrue(
				frappe.db.exists(
					"Dynamic Link",
					{"link_doctype": "Customer", "link_name": CLIENTE, "parent": endereco.name},
				)
			)
		finally:
			_apagar_cliente()

	def test_nao_cria_segundo_endereco(self):
		self._cliente()

		try:
			buscar = Mock(return_value=(200, BB))

			c.criar_endereco("Customer", CLIENTE, buscar=buscar)
			r = c.criar_endereco("Customer", CLIENTE, buscar=buscar)

			self.assertEqual(r["situacao"], "ja_tem_endereco")
			self.assertEqual(
				frappe.db.count("Dynamic Link", {"link_name": CLIENTE, "parenttype": "Address"}), 1
			)
		finally:
			_apagar_cliente()

	def test_sem_rede_nao_cria_endereco_nem_levanta(self):
		self._cliente()

		try:
			r = c.criar_endereco("Customer", CLIENTE, buscar=Mock(side_effect=OSError("sem rede")))

			self.assertEqual(r["situacao"], c.INDISPONIVEL)
			self.assertFalse(
				frappe.db.exists("Dynamic Link", {"link_name": CLIENTE, "parenttype": "Address"})
			)
		finally:
			_apagar_cliente()
