# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) da consulta de CEP: o Frappe de verdade, a rede trocada por um duplo.

A regra de sugerir só a lacuna está provada sem Frappe em `tests/test_endereco_cep.py`; a costura com
JS, `hooks.py` e campos, em `tests/test_consulta_cep.py`. O que **só** o bench mostra é o que depende do
site: o cache no Redis de verdade (inclusive que resposta de serviço fora do ar **não** é guardada), a
chave de `site_config` que desliga a consulta, e a permissão do `Address`.

A chamada ao ViaCEP é injetada (`buscar=`/`http=`), fora do endpoint exposto — nenhum teste aqui usa a rede.
As respostas são as reais do serviço, colhidas em 2026-10-10.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_consulta_cep
"""

from unittest.mock import Mock

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.fiscal.endereco_cep import url_por_cep, url_por_logradouro
from erpnext_brasil.integracao import consulta_cep as c

MODULOS_COBERTOS = ("consulta_cep",)
"""Declarado, não inferido — o módulo é chamado pelo JS e não consta em `hooks.py`."""

SE = (
	'{"cep": "01001-000", "logradouro": "Praça da Sé", "complemento": "lado ímpar", "unidade": "",'
	' "bairro": "Sé", "localidade": "São Paulo", "uf": "SP", "estado": "São Paulo", "regiao": "Sudeste",'
	' "ibge": "3550308", "gia": "1004", "ddd": "11", "siafi": "7107"}'
).encode()

BUSCA = (
	'[{"cep": "91790-072", "logradouro": "Rua Domingos José Poli", "complemento": "", "unidade": "",'
	' "bairro": "Restinga", "localidade": "Porto Alegre", "uf": "RS", "estado": "Rio Grande do Sul",'
	' "regiao": "Sul", "ibge": "4314902", "gia": "", "ddd": "51", "siafi": "8801"},'
	' {"cep": "91910-420", "logradouro": "Rua José Domingos Varella", "complemento": "", "unidade": "",'
	' "bairro": "Cavalhada", "localidade": "Porto Alegre", "uf": "RS", "estado": "Rio Grande do Sul",'
	' "regiao": "Sul", "ibge": "4314902", "gia": "", "ddd": "51", "siafi": "8801"}]'
).encode()

INEXISTENTE = b'{"erro": "true"}'
HTML_400 = b"<!DOCTYPE HTML><html><body><h1>Http 400</h1></body></html>"

CEPS = ("01001000", "99999999", "91790072", "91910420")


def _limpar() -> None:
	cache = c._cache()

	for cep in CEPS:
		cache.delete_value(c.PREFIXO_CACHE + cep)

	cache.delete_value(c._chave_da_busca("RS", "Porto Alegre", "Domingos José"))
	cache.delete_value(c._chave_da_busca("RS", "Porto Alegre", "Nada Existe Aqui"))


class TestConsultaCep(FrappeTestCase):
	def setUp(self):
		_limpar()

	def tearDown(self):
		_limpar()

	# ------------------------------------------------------------------- só a lacuna

	def test_preenche_so_a_lacuna_e_nunca_o_que_o_usuario_digitou(self):
		"""Teste-âncora. O valor já informado manda sobre o cadastro externo."""
		buscar = Mock(return_value=SE)
		r = c.consultar(
			"01001-000", {"address_line1": "Rua que eu digitei, 10", "city": "Cidade X"}, buscar=buscar
		)

		self.assertEqual(r["situacao"], c.ENCONTRADO)
		self.assertNotIn("address_line1", r["preencher"])
		self.assertNotIn("city", r["preencher"])
		self.assertEqual(r["preencher"]["br_codigo_municipio_ibge"], "3550308")
		self.assertEqual(r["preencher"]["state"], "SP")

	def test_o_complemento_do_viacep_nunca_e_proposto(self):
		r = c.consultar("01001000", {}, buscar=Mock(return_value=SE))

		self.assertNotIn("address_line2", r["preencher"])
		self.assertNotIn("lado ímpar", r["preencher"].values())

	def test_divergencia_e_avisada_e_nao_aplicada(self):
		r = c.consultar("01001000", {"state": "RJ", "city": "Rio de Janeiro"}, buscar=Mock(return_value=SE))

		self.assertEqual({d["campo"] for d in r["divergencias"]}, {"state", "city"})
		self.assertNotIn("state", r["preencher"])
		self.assertNotIn("city", r["preencher"])

	# ------------------------------------------------------------------- cache

	def test_a_segunda_consulta_vem_do_cache_e_nao_da_rede(self):
		buscar = Mock(return_value=SE)

		c.consultar("01001000", {}, buscar=buscar)
		c.consultar("01001-000", {}, buscar=buscar)

		self.assertEqual(buscar.call_count, 1)
		buscar.assert_called_once_with(url_por_cep("01001000"))

	def test_cep_inexistente_tambem_e_guardado(self):
		buscar = Mock(return_value=INEXISTENTE)

		primeira = c.consultar("99999999", {}, buscar=buscar)
		segunda = c.consultar("99999999", {}, buscar=buscar)

		self.assertEqual(primeira["situacao"], c.NAO_ENCONTRADO)
		self.assertEqual(segunda["situacao"], c.NAO_ENCONTRADO)
		self.assertEqual(
			buscar.call_count, 1, "um erro de digitação repetido não deve custar uma chamada cada"
		)

	def test_servico_fora_do_ar_nao_e_guardado(self):
		"""Se o serviço cair e a falha fosse guardada, um CEP bom ficaria "indisponível" por dias."""
		buscar = Mock(side_effect=[OSError("sem rede"), SE])

		fora = c.consultar("01001000", {}, buscar=buscar)
		de_volta = c.consultar("01001000", {}, buscar=buscar)

		self.assertEqual(fora["situacao"], c.INDISPONIVEL)
		self.assertEqual(de_volta["situacao"], c.ENCONTRADO)
		self.assertEqual(buscar.call_count, 2)

	def test_pagina_de_erro_do_servico_e_indisponivel_e_nao_e_guardada(self):
		buscar = Mock(side_effect=[HTML_400, SE])

		self.assertEqual(c.consultar("01001000", {}, buscar=buscar)["situacao"], c.INDISPONIVEL)
		self.assertEqual(c.consultar("01001000", {}, buscar=buscar)["situacao"], c.ENCONTRADO)

	# ------------------------------------------------------------------- o que nem sai

	def test_cep_malformado_nao_chega_a_rede(self):
		buscar = Mock(return_value=SE)

		for cep in ("123", "0100100A", "010010000", ""):
			with self.subTest(cep=cep):
				self.assertEqual(c.consultar(cep, {}, buscar=buscar)["situacao"], c.INVALIDO)

		buscar.assert_not_called()

	def test_a_consulta_pode_ser_desligada_no_site_config(self):
		buscar = Mock(return_value=SE)
		frappe.conf[c.CHAVE_CONFIGURACAO] = False

		try:
			r = c.consultar("01001000", {}, buscar=buscar)
		finally:
			frappe.conf.pop(c.CHAVE_CONFIGURACAO, None)

		self.assertEqual(r["situacao"], c.INDISPONIVEL)
		buscar.assert_not_called()

	def test_o_que_vem_do_navegador_so_e_lido_nos_campos_conhecidos(self):
		atual = c._atual('{"pincode": "01001-000", "city": "SP", "customer_name": "Fulano", "x": 1}')

		self.assertEqual(set(atual), set(c.CAMPOS_DO_ENDERECO))
		self.assertEqual(atual["city"], "SP")
		self.assertEqual(c._atual(None), {})
		self.assertEqual(c._atual(["lista"]), {})
		self.assertEqual(c._atual("isto não é json["), {}, "texto malformado não pode derrubar a consulta")

	# ------------------------------------------------------------------- busca por logradouro

	def test_busca_devolve_os_enderecos_e_alimenta_o_cache_por_cep(self):
		"""Escolher uma linha da lista não pode custar uma segunda chamada."""
		http = Mock(return_value=BUSCA)

		r = c.buscar("RS", "Porto Alegre", "Domingos José", http=http)

		self.assertEqual(r["situacao"], c.ENCONTRADO)
		self.assertEqual([x["cep"] for x in r["resultados"]], ["91790-072", "91910-420"])
		http.assert_called_once_with(url_por_logradouro("RS", "Porto Alegre", "Domingos José"))

		cep = Mock(return_value=SE)
		escolhido = c.consultar("91790-072", {}, buscar=cep)

		self.assertEqual(escolhido["situacao"], c.ENCONTRADO)
		cep.assert_not_called()

	def test_a_busca_repetida_vem_do_cache(self):
		http = Mock(return_value=BUSCA)

		c.buscar("RS", "Porto Alegre", "Domingos José", http=http)
		c.buscar("rs", "porto  alegre", "domingos josé", http=http)

		self.assertEqual(http.call_count, 1)

	def test_busca_sem_resultado(self):
		r = c.buscar("RS", "Porto Alegre", "Nada Existe Aqui", http=Mock(return_value=b"[]"))

		self.assertEqual(r["situacao"], c.NAO_ENCONTRADO)
		self.assertEqual(r["resultados"], [])

	def test_busca_com_texto_curto_ou_uf_invalida_nao_chega_a_rede(self):
		http = Mock(return_value=BUSCA)

		self.assertEqual(c.buscar("RS", "Po", "Domingos", http=http)["situacao"], c.INVALIDO)
		self.assertEqual(c.buscar("XX", "Porto Alegre", "Domingos", http=http)["situacao"], c.INVALIDO)
		http.assert_not_called()

	def test_busca_com_servico_fora_do_ar(self):
		r = c.buscar("RS", "Porto Alegre", "Domingos José", http=Mock(side_effect=OSError("sem rede")))

		self.assertEqual(r["situacao"], c.INDISPONIVEL)

	# ------------------------------------------------------------------- permissão

	def test_usuario_sem_permissao_no_endereco_e_recusado(self):
		frappe.set_user("Guest")

		try:
			with self.assertRaises(frappe.PermissionError):
				c.consultar_cep("01001000")

			with self.assertRaises(frappe.PermissionError):
				c.buscar_logradouro("RS", "Porto Alegre", "Domingos")
		finally:
			frappe.set_user("Administrator")

	def test_quem_pode_cadastrar_endereco_passa_na_checagem(self):
		c._exigir_permissao()  # Administrator: não levanta
