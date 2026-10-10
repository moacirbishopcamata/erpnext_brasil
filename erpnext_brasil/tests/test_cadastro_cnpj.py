# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Consulta de CNPJ (`fiscal/cadastro_cnpj.py`) — a parte que não depende de rede nem de Frappe.

A fixture é a resposta **real** de `brasilapi.com.br/api/cnpj/v1/00000000000191` e de
`minhareceita.org/00000000000191` (Banco do Brasil, empresa pública), colhida em 2026-10-10. As duas
devolvem o mesmo esquema — a BrasilAPI usa a base do Minha Receita — e o que a verificação ao vivo ensinou
está travado aqui:

- `codigo_municipio` (9701) é o código da **Receita**, não o do IBGE; o IBGE de 7 dígitos é
  `codigo_municipio_ibge` (5300108). Trocar um pelo outro grava um município errado sem dar erro;
- `numero` vem como `SN`;
- CNPJ **alfanumérico** é formato válido para os dois provedores (404, não 400);
- erro vem em JSON: 400 para dígito inválido, 404 para inexistente.

Privacidade: o quadro de sócios (`qsa`) traz nome e CPF mascarado de pessoas físicas, e nada nele é usado —
o teste `test_o_quadro_de_socios_nunca_aparece` garante que ele não sai deste módulo. Os nomes de MEI abaixo
são fictícios; nenhuma pessoa real foi consultada.

Teste-âncora: `TestLacunas.test_nunca_sobrescreve_o_que_o_usuario_ja_informou`.
"""

import json
import unittest

from erpnext_brasil.fiscal import cadastro_cnpj as c

BB = {
	"cnpj": "00000000000191",
	"razao_social": "BANCO DO BRASIL SA",
	"nome_fantasia": "DIRECAO GERAL",
	"situacao_cadastral": 2,
	"descricao_situacao_cadastral": "ATIVA",
	"data_situacao_cadastral": "2005-11-03",
	"motivo_situacao_cadastral": 0,
	"descricao_motivo_situacao_cadastral": "SEM MOTIVO",
	"cnae_fiscal": 6422100,
	"cnae_fiscal_descricao": "Bancos múltiplos, com carteira comercial",
	"codigo_natureza_juridica": 2038,
	"natureza_juridica": "Sociedade de Economia Mista",
	"porte": "DEMAIS",
	"opcao_pelo_simples": False,
	"opcao_pelo_mei": False,
	"identificador_matriz_filial": 1,
	"descricao_identificador_matriz_filial": "MATRIZ",
	"descricao_tipo_de_logradouro": "QUADRA",
	"logradouro": "SAUN QUADRA 5 BLOCO B TORRE I, II, III",
	"numero": "SN",
	"complemento": "ANDAR T I SL S101 A S1602",
	"bairro": "ASA NORTE",
	"cep": "70040912",
	"municipio": "BRASILIA",
	"uf": "DF",
	"codigo_municipio": 9701,
	"codigo_municipio_ibge": 5300108,
	"ddd_telefone_1": "6134939002",
	"email": None,
	"capital_social": 120000000000,
	"qsa": [{"nome_socio": "SOCIO FICTICIO UM", "cnpj_cpf_do_socio": "***123456**"}],
	"cnaes_secundarios": [{"codigo": 6499999, "descricao": "Outras atividades"}],
}


def _corpo(**mudancas) -> str:
	return json.dumps({**BB, **mudancas})


def _ler(**mudancas) -> c.CadastroCnpj:
	return c.interpretar_resposta(200, _corpo(**mudancas))


class TestCnpjNormalizado(unittest.TestCase):
	def test_aceita_com_e_sem_mascara(self):
		for entrada in ("00000000000191", "00.000.000/0001-91", " 00.000.000/0001-91 "):
			with self.subTest(entrada=entrada):
				self.assertEqual(c.normalizar_cnpj(entrada), "00000000000191")

	def test_aceita_o_cnpj_alfanumerico_valido(self):
		"""Em produção desde julho de 2026 (IN RFB 2.229/2024); as duas APIs o aceitam como formato válido."""
		self.assertEqual(c.normalizar_cnpj("12.abc.345/01de-35"), "12ABC34501DE35")

	def test_recusa_digito_errado_e_lixo_antes_de_sair(self):
		for entrada in ("", "123", "00000000000190", "11111111111111", "12ABC34501DE36", "CPF", None):
			with self.subTest(entrada=entrada), self.assertRaises(c.CnpjInvalido):
				c.normalizar_cnpj(entrada)

	def test_cpf_nao_e_cnpj(self):
		with self.assertRaises(c.CnpjInvalido):
			c.normalizar_cnpj("529.982.247-25")


class TestModelosDeUrl(unittest.TestCase):
	def test_monta_a_url_com_o_cnpj_limpo(self):
		self.assertEqual(
			c.url_do_provedor("https://brasilapi.com.br/api/cnpj/v1/{cnpj}", "00.000.000/0001-91"),
			"https://brasilapi.com.br/api/cnpj/v1/00000000000191",
		)

	def test_o_modelo_precisa_do_marcador_uma_vez(self):
		for modelo in (
			"https://x.example/api",
			"https://x.example/{cnpj}/{cnpj}",
			"",
			None,
		):
			with self.subTest(modelo=modelo), self.assertRaises(c.ModeloInvalido):
				c.url_do_provedor(modelo, "00000000000191")

	def test_so_http_e_https_sem_credencial_na_url(self):
		for modelo in (
			"ftp://x.example/{cnpj}",
			"file:///etc/{cnpj}",
			"https://usuario:senha@x.example/{cnpj}",
			"//x.example/{cnpj}",
			"https:///{cnpj}",
		):
			with self.subTest(modelo=modelo), self.assertRaises(c.ModeloInvalido):
				c.url_do_provedor(modelo, "00000000000191")

	def test_instancia_propria_em_http_e_aceita(self):
		"""Minha Receita hospedado pela própria empresa, na rede interna, costuma ser `http`."""
		self.assertEqual(
			c.url_do_provedor("http://minhareceita.interno:8000/{cnpj}", "00000000000191"),
			"http://minhareceita.interno:8000/00000000000191",
		)

	def test_padroes_sao_os_dois_provedores_verificados(self):
		self.assertEqual(
			c.MODELOS_PADRAO,
			("https://brasilapi.com.br/api/cnpj/v1/{cnpj}", "https://minhareceita.org/{cnpj}"),
		)


class TestInterpretarResposta(unittest.TestCase):
	def test_resposta_real(self):
		cad = _ler()

		self.assertEqual(cad.cnpj, "00000000000191")
		self.assertEqual(cad.razao_social, "BANCO DO BRASIL SA")
		self.assertEqual(cad.nome_fantasia, "DIRECAO GERAL")
		self.assertEqual((cad.situacao, cad.situacao_descricao), (2, "ATIVA"))
		self.assertEqual(cad.data_situacao, "2005-11-03")
		self.assertEqual(cad.cnae_codigo, "6422100")
		self.assertEqual(cad.natureza_juridica, "Sociedade de Economia Mista")
		self.assertTrue(cad.ativo)

	def test_usa_o_codigo_do_ibge_e_nao_o_da_receita(self):
		"""Teste-âncora do esquema. `codigo_municipio` (9701) é código interno da Receita."""
		endereco = _ler().endereco

		self.assertEqual(endereco.codigo_municipio_ibge, "5300108")
		self.assertNotEqual(endereco.codigo_municipio_ibge, "9701")

	def test_ibge_malformado_vira_vazio(self):
		self.assertEqual(_ler(codigo_municipio_ibge=None).endereco.codigo_municipio_ibge, "")
		self.assertEqual(_ler(codigo_municipio_ibge=530).endereco.codigo_municipio_ibge, "")
		self.assertEqual(_ler(codigo_municipio_ibge="abc").endereco.codigo_municipio_ibge, "")

	def test_cep_sai_formatado(self):
		self.assertEqual(_ler().endereco.cep, "70040-912")
		self.assertEqual(_ler(cep="1001000").endereco.cep, "01001-000", "zero à esquerda que a base perde")
		self.assertEqual(_ler(cep="").endereco.cep, "")

	def test_aceita_bytes_e_dicionario(self):
		self.assertEqual(c.interpretar_resposta(200, _corpo().encode("utf-8")), _ler())
		self.assertEqual(c.interpretar_resposta(200, dict(BB)), _ler())

	def test_optante_matriz_e_mei(self):
		cad = _ler(opcao_pelo_simples=True, opcao_pelo_mei=True, identificador_matriz_filial=2)

		self.assertIs(cad.optante_simples, True)
		self.assertIs(cad.mei, True)
		self.assertIs(cad.matriz, False)
		self.assertIs(_ler().matriz, True)

	def test_campo_ausente_nao_vira_afirmacao(self):
		"""Sem `opcao_pelo_simples` na resposta, "não optante" seria inventar: fica `None`."""
		dados = {k: v for k, v in BB.items() if k not in ("opcao_pelo_simples", "opcao_pelo_mei")}
		cad = c.interpretar_resposta(200, dados)

		self.assertIsNone(cad.optante_simples)
		self.assertIsNone(cad.mei)

	def test_situacao_pelo_codigo_quando_falta_a_descricao(self):
		dados = {k: v for k, v in BB.items() if k != "descricao_situacao_cadastral"}
		dados["situacao_cadastral"] = "8"
		cad = c.interpretar_resposta(200, dados)

		self.assertEqual((cad.situacao, cad.situacao_descricao), (8, "BAIXADA"))
		self.assertFalse(cad.ativo)

	def test_o_quadro_de_socios_nunca_aparece(self):
		"""Privacidade: nome e CPF mascarado de sócios não são usados e não saem deste módulo."""
		cad = _ler()
		tudo = repr(cad) + repr(c.resumo(cad)) + repr(c.campos_do_endereco(cad))

		self.assertNotIn("SOCIO FICTICIO", tudo)
		self.assertNotIn("qsa", tudo.lower())
		self.assertFalse(hasattr(cad, "qsa"))

	def test_contato_do_estabelecimento_tambem_nao_sai(self):
		"""Telefone e e-mail podem ser de pessoa física (empresário individual): não são lidos."""
		tudo = repr(_ler(email="fulano@example.com", ddd_telefone_1="1199999999"))

		self.assertNotIn("fulano@example.com", tudo)
		self.assertNotIn("1199999999", tudo)


class TestStatusHttp(unittest.TestCase):
	def test_404_e_cnpj_inexistente_e_nao_erro(self):
		self.assertIsNone(
			c.interpretar_resposta(404, '{"message": "CNPJ 12.ABC.345/01DE-35 não encontrado."}')
		)

	def test_400_e_resposta_invalida_porque_o_cnpj_ja_foi_validado_antes(self):
		with self.assertRaises(c.RespostaCnpjInvalida):
			c.interpretar_resposta(400, '{"message": "CNPJ 123 inválido."}')

	def test_limite_de_uso_e_erro_de_servidor_sao_provedor_indisponivel(self):
		for status in (429, 500, 502, 503, 504, 403, 408):
			with self.subTest(status=status), self.assertRaises(c.ProvedorIndisponivel):
				c.interpretar_resposta(status, "")

	def test_200_com_corpo_que_nao_e_json_e_invalido(self):
		with self.assertRaises(c.RespostaCnpjInvalida):
			c.interpretar_resposta(200, "<html>fora do ar</html>")

	def test_200_sem_razao_social_e_invalido(self):
		with self.assertRaises(c.RespostaCnpjInvalida):
			c.interpretar_resposta(200, '{"cnpj": "00000000000191"}')

	def test_200_lista_e_invalido(self):
		with self.assertRaises(c.RespostaCnpjInvalida):
			c.interpretar_resposta(200, "[]")


class TestNomeSugerido(unittest.TestCase):
	def test_razao_social_comum(self):
		self.assertEqual(c.razao_social_sugerida(_ler()), "BANCO DO BRASIL SA")

	def test_formato_novo_do_mei_fica_como_a_receita_registra(self):
		"""Desde 12/12/2022 o nome do MEI é "<8 dígitos do CNPJ> <nome>" — o nome oficial, e não se altera."""
		nome = "12.345.678 FULANO FICTICIO DA SILVA"

		self.assertEqual(c.razao_social_sugerida(_ler(razao_social=nome)), nome)

	def test_formato_antigo_do_mei_traz_o_cpf_e_nao_e_sugerido(self):
		"""Registros que o titular não atualizou ainda trazem "<nome> <CPF>": dado pessoal que não vai ao cadastro."""
		for nome in (
			"FULANO FICTICIO DA SILVA 00000000000",
			"FULANO FICTICIO 11122233344",
			"BELTRANO 123.456.789-09",
		):
			with self.subTest(nome=nome):
				self.assertEqual(c.razao_social_sugerida(_ler(razao_social=nome)), "")
				self.assertTrue(c.tem_cpf_no_nome(nome))

	def test_numero_no_meio_do_nome_nao_e_cpf(self):
		for nome in ("PADARIA 24 HORAS LTDA", "COMERCIO 123 SA", "A 12345678901234 B"):
			with self.subTest(nome=nome):
				self.assertFalse(c.tem_cpf_no_nome(nome))

	def test_espacos_sao_aparados(self):
		self.assertEqual(c.razao_social_sugerida(_ler(razao_social="  ACME   LTDA  ")), "ACME LTDA")


class TestLacunas(unittest.TestCase):
	def test_cada_doctype_tem_o_seu_campo_de_nome(self):
		cad = _ler()

		self.assertEqual(c.lacunas_da_parte("Customer", {}, cad), {"customer_name": "BANCO DO BRASIL SA"})
		self.assertEqual(c.lacunas_da_parte("Supplier", {}, cad), {"supplier_name": "BANCO DO BRASIL SA"})
		self.assertEqual(c.lacunas_da_parte("Company", {}, cad), {"company_name": "BANCO DO BRASIL SA"})

	def test_nunca_sobrescreve_o_que_o_usuario_ja_informou(self):
		"""Teste-âncora. Cliente costuma ter nome fantasia no cadastro; trocá-lo pela razão social apagaria a escolha."""
		self.assertEqual(c.lacunas_da_parte("Customer", {"customer_name": "BB Matriz"}, _ler()), {})

	def test_espaco_em_branco_conta_como_vazio(self):
		self.assertEqual(
			c.lacunas_da_parte("Customer", {"customer_name": "   "}, _ler()),
			{"customer_name": "BANCO DO BRASIL SA"},
		)

	def test_doctype_desconhecido_nao_preenche_nada(self):
		self.assertEqual(c.lacunas_da_parte("Item", {}, _ler()), {})

	def test_nome_com_cpf_deixa_a_lacuna_aberta(self):
		self.assertEqual(
			c.lacunas_da_parte("Customer", {}, _ler(razao_social="FULANO FICTICIO 11122233344")), {}
		)


class TestSituacao(unittest.TestCase):
	def test_ativa_nao_gera_aviso(self):
		self.assertEqual(c.aviso_de_situacao(_ler()), "")

	def test_demais_situacoes_geram_aviso_com_a_data(self):
		for codigo, nome in ((1, "NULA"), (3, "SUSPENSA"), (4, "INAPTA"), (8, "BAIXADA")):
			with self.subTest(situacao=nome):
				aviso = c.aviso_de_situacao(
					_ler(
						situacao_cadastral=codigo,
						descricao_situacao_cadastral=nome,
						data_situacao_cadastral="2024-03-09",
					)
				)

				self.assertIn(nome, aviso)
				self.assertIn("09/03/2024", aviso)

	def test_o_motivo_entra_no_aviso_quando_existe(self):
		aviso = c.aviso_de_situacao(
			_ler(
				situacao_cadastral=8,
				descricao_situacao_cadastral="BAIXADA",
				descricao_motivo_situacao_cadastral="EXTINCAO",
			)
		)

		self.assertIn("EXTINCAO", aviso)

	def test_situacao_desconhecida_avisa_em_vez_de_afirmar_que_esta_ativa(self):
		dados = {
			k: v for k, v in BB.items() if k not in ("situacao_cadastral", "descricao_situacao_cadastral")
		}

		self.assertIn("não informada", c.aviso_de_situacao(c.interpretar_resposta(200, dados)))

	def test_os_dados_abertos_sao_mensais_e_o_aviso_diz_isso(self):
		"""A situação de uma base mensal pode estar defasada: o resumo avisa, para ninguém tratá-la como consulta em tempo real."""
		self.assertIn("mensal", c.AVISO_DE_DEFASAGEM.lower())
		self.assertEqual(c.resumo(_ler())["aviso_de_defasagem"], c.AVISO_DE_DEFASAGEM)


class TestEnderecoParaAddress(unittest.TestCase):
	def test_mapeia_para_os_campos_do_address(self):
		campos = c.campos_do_endereco(_ler(descricao_tipo_de_logradouro="RUA", logradouro="CAPITAO CRUZ"))

		self.assertEqual(
			campos,
			{
				"address_line1": "RUA CAPITAO CRUZ",
				"address_line2": "ANDAR T I SL S101 A S1602",
				"br_numero_endereco": "SN",
				"br_bairro": "ASA NORTE",
				"city": "BRASILIA",
				"state": "DF",
				"pincode": "70040-912",
				"br_codigo_municipio_ibge": "5300108",
				"country": "Brazil",
			},
		)

	def test_tipo_de_logradouro_que_ja_esta_no_nome_nao_se_repete(self):
		"""A base traz `QUADRA` + `SAUN QUADRA 5…` e `RUA` + `RUA XV`: repetir daria "QUADRA SAUN QUADRA…"."""
		self.assertEqual(
			c.campos_do_endereco(_ler())["address_line1"], "SAUN QUADRA 5 BLOCO B TORRE I, II, III"
		)
		self.assertEqual(
			c.campos_do_endereco(_ler(descricao_tipo_de_logradouro="RUA", logradouro="RUA XV DE NOVEMBRO"))[
				"address_line1"
			],
			"RUA XV DE NOVEMBRO",
		)

	def test_omite_o_que_a_resposta_nao_traz(self):
		campos = c.campos_do_endereco(_ler(complemento="", bairro="", cep=""))

		for ausente in ("address_line2", "br_bairro", "pincode"):
			self.assertNotIn(ausente, campos)

	def test_a_uf_vai_como_sigla(self):
		self.assertEqual(c.campos_do_endereco(_ler())["state"], "DF")

	def test_sem_logradouro_nao_ha_endereco_para_criar(self):
		self.assertEqual(c.campos_do_endereco(_ler(logradouro="")), {})


class TestResumo(unittest.TestCase):
	def test_traz_o_que_ajuda_a_decidir_e_nada_de_pessoa(self):
		r = c.resumo(_ler())

		self.assertEqual(r["razao_social"], "BANCO DO BRASIL SA")
		self.assertEqual(r["situacao"], "ATIVA")
		self.assertEqual(r["data_situacao"], "03/11/2005")
		self.assertTrue(r["ativo"])
		self.assertEqual(r["cnae"], "6422100 — Bancos múltiplos, com carteira comercial")
		self.assertEqual(r["matriz_filial"], "Matriz")
		self.assertEqual(r["simples"], "Não optante")
		self.assertNotIn("qsa", r)
		self.assertNotIn("email", r)

	def test_simples_desconhecido_fica_em_branco(self):
		dados = {k: v for k, v in BB.items() if k != "opcao_pelo_simples"}

		self.assertEqual(c.resumo(c.interpretar_resposta(200, dados))["simples"], "")


if __name__ == "__main__":
	unittest.main()
