# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Consulta de CEP e logradouro (`fiscal/endereco_cep.py`) — a parte que não depende de rede nem de Frappe.

As respostas abaixo são **as reais do ViaCEP**, colhidas em 2026-10-10, não escritas de memória:
o que ficou de fora do que a documentação diz é justamente o que morde.

- CEP inexistente volta **HTTP 200** com `{"erro": "true"}` — o valor é o *texto* `"true"`, não o
  booleano que a página descreve;
- CEP malformado volta **HTTP 400 com uma página HTML**, não JSON;
- o campo `complemento` de `01001-000` é `"lado ímpar"`: uma nota sobre a faixa do CEP, **não** o
  complemento do endereço do cliente (apartamento, sala), e por isso nunca preenche o cadastro;
- `ibge` traz o código do município com 7 dígitos, que é o dado que hoje se digita à mão.

Teste-âncora: `TestLacunas.test_nunca_sobrescreve_o_que_o_usuario_ja_informou`. Sugestão preenche
lacuna; não corrige quem já decidiu — o valor salvo manda sobre o cadastro externo.
"""

import json
import unittest

from erpnext_brasil.fiscal import endereco_cep as c

SE = """{
  "cep": "01001-000", "logradouro": "Praça da Sé", "complemento": "lado ímpar", "unidade": "",
  "bairro": "Sé", "localidade": "São Paulo", "uf": "SP", "estado": "São Paulo", "regiao": "Sudeste",
  "ibge": "3550308", "gia": "1004", "ddd": "11", "siafi": "7107"
}"""

BUSCA = """[
  {"cep": "91790-072", "logradouro": "Rua Domingos José Poli", "complemento": "", "unidade": "",
   "bairro": "Restinga", "localidade": "Porto Alegre", "uf": "RS", "estado": "Rio Grande do Sul",
   "regiao": "Sul", "ibge": "4314902", "gia": "", "ddd": "51", "siafi": "8801"},
  {"cep": "91910-420", "logradouro": "Rua José Domingos Varella", "complemento": "", "unidade": "",
   "bairro": "Cavalhada", "localidade": "Porto Alegre", "uf": "RS", "estado": "Rio Grande do Sul",
   "regiao": "Sul", "ibge": "4314902", "gia": "", "ddd": "51", "siafi": "8801"}
]"""

INEXISTENTE = '{\n  "erro": "true"\n}'
HTML_400 = "<!DOCTYPE HTML><html><head><title>ViaCEP 400</title></head><body><h1>Http 400</h1></body></html>"


class TestCepNormalizado(unittest.TestCase):
	def test_aceita_com_e_sem_mascara_e_com_espacos(self):
		for entrada in ("01001000", "01001-000", " 01.001-000 ", "01001 000"):
			with self.subTest(entrada=entrada):
				self.assertEqual(c.normalizar_cep(entrada), "01001000")

	def test_recusa_o_que_o_viacep_responderia_400(self):
		"""A documentação manda validar antes: 9 dígitos, letras ou tamanho errado dão HTTP 400."""
		for entrada in ("", "123", "010010000", "0100100A", "abcdefgh", None):
			with self.subTest(entrada=entrada), self.assertRaises(c.CepInvalido):
				c.normalizar_cep(entrada)

	def test_formata_com_hifen(self):
		self.assertEqual(c.formatar_cep("01001000"), "01001-000")

	def test_cep_so_de_zeros_e_recusado(self):
		with self.assertRaises(c.CepInvalido):
			c.normalizar_cep("00000000")


class TestUrls(unittest.TestCase):
	def test_url_por_cep(self):
		self.assertEqual(c.url_por_cep("01001-000"), "https://viacep.com.br/ws/01001000/json/")

	def test_url_por_logradouro_e_a_forma_do_exemplo_do_proprio_viacep(self):
		"""`%20` na cidade e `+` no logradouro: é a forma do exemplo da documentação e a que funciona."""
		self.assertEqual(
			c.url_por_logradouro("RS", "Porto Alegre", "Domingos José"),
			"https://viacep.com.br/ws/RS/Porto%20Alegre/Domingos+Jos%C3%A9/json/",
		)

	def test_mais_no_logradouro_e_busca_por_palavras_e_na_cidade_nao_pode(self):
		"""Conferido ao vivo (2026-10-10): `Domingos+José` achou 3 ruas, `Domingos%20José` só 2 (a frase
		exata), e `+` no segmento da cidade devolve uma página de erro, não JSON."""
		url = c.url_por_logradouro("RS", "Porto Alegre do Sul", "domingos josé poli")

		self.assertIn("/Porto%20Alegre%20do%20Sul/", url)
		self.assertIn("/domingos+jos%C3%A9+poli/", url)
		self.assertNotIn("Porto+", url)

	def test_um_mais_digitado_pelo_usuario_nao_vira_separador(self):
		"""O `+` do texto é dado, não pontuação da URL: vira `%2B`, e só o espaço vira `+`."""
		self.assertIn("/a%2Bb/", c.url_por_logradouro("RS", "Porto Alegre", "a+b"))

	def test_uf_em_minusculas_vira_maiuscula(self):
		self.assertIn("/ws/RS/", c.url_por_logradouro("rs", "Porto Alegre", "Domingos"))

	def test_barra_e_interrogacao_nao_escapam_do_caminho(self):
		"""Texto digitado pelo usuário vai para um caminho de URL: `/` ou `?` não podem abri-lo."""
		url = c.url_por_logradouro("RS", "Porto Alegre", "a/b?c#d")

		self.assertEqual(url.count("/"), 8, url)  # só as do próprio formato da URL do serviço
		self.assertNotIn("?", url)
		self.assertNotIn("#", url)

	def test_recusa_o_que_o_viacep_responderia_400(self):
		casos = [
			("XX", "Porto Alegre", "Domingos"),
			("RS", "Po", "Domingos"),
			("RS", "Porto Alegre", "Do"),
			("RS", "  ", "Domingos"),
			("", "Porto Alegre", "Domingos"),
		]

		for uf, cidade, logradouro in casos:
			with self.subTest(uf=uf, cidade=cidade, logradouro=logradouro), self.assertRaises(c.CepInvalido):
				c.url_por_logradouro(uf, cidade, logradouro)

	def test_recusa_texto_absurdamente_longo(self):
		with self.assertRaises(c.CepInvalido):
			c.url_por_logradouro("RS", "Porto Alegre", "a" * 300)


class TestInterpretarCep(unittest.TestCase):
	def test_resposta_real(self):
		e = c.interpretar_cep(SE)

		self.assertEqual((e.cep, e.logradouro, e.bairro), ("01001-000", "Praça da Sé", "Sé"))
		self.assertEqual((e.cidade, e.uf, e.codigo_municipio), ("São Paulo", "SP", "3550308"))

	def test_aceita_bytes_e_dicionario(self):
		self.assertEqual(c.interpretar_cep(SE.encode("utf-8")), c.interpretar_cep(SE))
		self.assertEqual(c.interpretar_cep(json.loads(SE)), c.interpretar_cep(SE))

	def test_cep_inexistente_e_none_e_nao_erro(self):
		"""HTTP 200 com `"erro": "true"` (texto). É resultado normal de consulta, não falha."""
		self.assertIsNone(c.interpretar_cep(INEXISTENTE))

	def test_erro_booleano_tambem_e_inexistente(self):
		"""A documentação descreve `true`; a resposta real traz `"true"`. Os dois valem."""
		self.assertIsNone(c.interpretar_cep({"erro": True}))
		self.assertIsNone(c.interpretar_cep({"erro": "true"}))

	def test_pagina_html_do_400_e_resposta_invalida(self):
		with self.assertRaises(c.RespostaCepInvalida):
			c.interpretar_cep(HTML_400)

	def test_lista_onde_se_esperava_objeto_e_invalida(self):
		with self.assertRaises(c.RespostaCepInvalida):
			c.interpretar_cep(BUSCA)

	def test_objeto_sem_cep_e_invalido(self):
		with self.assertRaises(c.RespostaCepInvalida):
			c.interpretar_cep('{"logradouro": "X"}')

	def test_ibge_malformado_nao_vira_codigo(self):
		"""Um código que não tem 7 dígitos é descartado — melhor lacuna que dado errado."""
		e = c.interpretar_cep({**json.loads(SE), "ibge": "35503"})

		self.assertEqual(e.codigo_municipio, "")

	def test_espacos_sao_aparados(self):
		e = c.interpretar_cep({**json.loads(SE), "logradouro": "  Praça da Sé  "})

		self.assertEqual(e.logradouro, "Praça da Sé")


class TestInterpretarBusca(unittest.TestCase):
	def test_resposta_real_com_varios_resultados(self):
		achados = c.interpretar_busca(BUSCA)

		self.assertEqual([a.cep for a in achados], ["91790-072", "91910-420"])
		self.assertEqual({a.codigo_municipio for a in achados}, {"4314902"})

	def test_lista_vazia_e_nenhum_resultado(self):
		self.assertEqual(c.interpretar_busca("[]"), [])

	def test_erro_e_nenhum_resultado(self):
		self.assertEqual(c.interpretar_busca(INEXISTENTE), [])

	def test_html_e_resposta_invalida(self):
		with self.assertRaises(c.RespostaCepInvalida):
			c.interpretar_busca(HTML_400)

	def test_objeto_unico_e_invalido(self):
		with self.assertRaises(c.RespostaCepInvalida):
			c.interpretar_busca(SE)

	def test_nunca_passa_de_cinquenta(self):
		"""O ViaCEP limita a 50; se a resposta vier maior, cortamos — a tela não é lista infinita."""
		muitos = [{**json.loads(SE), "cep": f"01001-{i:03d}"} for i in range(80)]

		self.assertEqual(len(c.interpretar_busca(muitos)), 50)


class TestCamposDoEndereco(unittest.TestCase):
	def test_mapeia_para_os_campos_do_address(self):
		campos = c.campos_do_endereco(c.interpretar_cep(SE))

		self.assertEqual(
			campos,
			{
				"pincode": "01001-000",
				"address_line1": "Praça da Sé",
				"br_bairro": "Sé",
				"city": "São Paulo",
				"state": "SP",
				"br_codigo_municipio_ibge": "3550308",
			},
		)

	def test_o_complemento_do_viacep_nao_vira_complemento_do_cliente(self):
		"""`lado ímpar` descreve a faixa do CEP. Em `address_line2` ele iria para `xCpl` da nota."""
		campos = c.campos_do_endereco(c.interpretar_cep(SE))

		self.assertNotIn("address_line2", campos)
		self.assertNotIn("lado ímpar", campos.values())

	def test_omite_o_que_a_resposta_nao_tem(self):
		"""CEP geral de cidade pequena vem sem logradouro e sem bairro: nada de gravar vazio."""
		e = c.interpretar_cep({**json.loads(SE), "logradouro": "", "bairro": ""})
		campos = c.campos_do_endereco(e)

		self.assertNotIn("address_line1", campos)
		self.assertNotIn("br_bairro", campos)
		self.assertIn("city", campos)

	def test_a_uf_e_a_sigla_porque_e_o_que_a_nota_e_a_validacao_usam(self):
		self.assertEqual(c.campos_do_endereco(c.interpretar_cep(SE))["state"], "SP")


class TestLacunas(unittest.TestCase):
	def setUp(self):
		self.sugestao = c.interpretar_cep(SE)

	def test_cadastro_vazio_recebe_tudo(self):
		self.assertEqual(c.lacunas({}, self.sugestao), c.campos_do_endereco(self.sugestao))

	def test_nunca_sobrescreve_o_que_o_usuario_ja_informou(self):
		"""Teste-âncora. O valor salvo manda; o cadastro externo só preenche o que falta."""
		atual = {"address_line1": "Rua que eu digitei, 10", "br_bairro": "Meu bairro", "city": "Cidade X"}
		preencher = c.lacunas(atual, self.sugestao)

		for campo in atual:
			self.assertNotIn(campo, preencher, f"{campo} já tinha valor e foi proposto para troca")

		self.assertEqual(preencher["br_codigo_municipio_ibge"], "3550308")

	def test_espaco_em_branco_conta_como_vazio(self):
		preencher = c.lacunas({"address_line1": "   ", "br_bairro": None}, self.sugestao)

		self.assertEqual(preencher["address_line1"], "Praça da Sé")
		self.assertEqual(preencher["br_bairro"], "Sé")

	def test_cadastro_completo_nao_recebe_nada(self):
		self.assertEqual(c.lacunas(c.campos_do_endereco(self.sugestao), self.sugestao), {})


class TestDivergencias(unittest.TestCase):
	"""O que o ViaCEP diz e o cadastro contradiz é **avisado**, não corrigido em silêncio."""

	def setUp(self):
		self.sugestao = c.interpretar_cep(SE)

	def test_uf_diferente_e_divergencia(self):
		d = c.divergencias({"state": "RJ"}, self.sugestao)

		self.assertEqual([x.campo for x in d], ["state"])
		self.assertEqual((d[0].atual, d[0].sugerido), ("RJ", "SP"))

	def test_nome_do_estado_por_extenso_equivale_a_sigla(self):
		"""O Frappe guarda `state` como texto livre; "São Paulo" e "SP" são o mesmo estado."""
		self.assertEqual(c.divergencias({"state": "São Paulo"}, self.sugestao), [])

	def test_cidade_com_outra_grafia_de_acento_ou_caixa_nao_diverge(self):
		self.assertEqual(c.divergencias({"city": "SAO PAULO"}, self.sugestao), [])

	def test_cidade_diferente_diverge(self):
		self.assertEqual([x.campo for x in c.divergencias({"city": "Campinas"}, self.sugestao)], ["city"])

	def test_ibge_diferente_diverge(self):
		d = c.divergencias({"br_codigo_municipio_ibge": "3304557"}, self.sugestao)

		self.assertEqual([x.campo for x in d], ["br_codigo_municipio_ibge"])

	def test_campo_vazio_nao_e_divergencia_e_sim_lacuna(self):
		self.assertEqual(c.divergencias({"state": "", "city": None}, self.sugestao), [])

	def test_logradouro_e_bairro_nao_entram_na_comparacao(self):
		"""`Rua X` e `R. X` são o mesmo lugar; comparar texto de rua só geraria alarme falso."""
		self.assertEqual(
			c.divergencias({"address_line1": "R. da Se", "br_bairro": "Centro"}, self.sugestao), []
		)


if __name__ == "__main__":
	unittest.main()
