# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A costura da consulta de CNPJ: Python ↔ JS ↔ `hooks.py` ↔ campos declarados.

`integracao/consulta_cnpj.py` importa `frappe`, então a suíte pura não o executa (o comportamento é
provado em `tests_bench/test_consulta_cnpj.py`). O que cabe aqui é o que se quebra **sem erro**: um nome de
método trocado no JS, um campo que a consulta grava e a instalação nunca criou, um parâmetro que deixaria o
navegador injetar a função de rede, uma chamada sem prazo, um dado de pessoa que passou a sair do servidor.

Teste-âncora: `test_o_navegador_nao_consegue_injetar_a_funcao_de_rede`.
"""

import ast
import pathlib
import re
import unittest

from erpnext_brasil.fiscal.cadastro_cnpj import (
	CAMPO_NOME_POR_DOCTYPE,
	CadastroCnpj,
	EnderecoCnpj,
	campos_do_endereco,
)
from erpnext_brasil.setup import custom_fields

RAIZ = pathlib.Path(__file__).resolve().parents[1]
MODULO = RAIZ / "integracao" / "consulta_cnpj.py"
JS = RAIZ / "public" / "js" / "consulta_cnpj.js"

FUNCOES_EXPOSTAS = {"consultar_cnpj", "criar_endereco_pelo_cnpj"}


def _funcoes() -> dict[str, ast.FunctionDef]:
	arvore = ast.parse(MODULO.read_text(encoding="utf-8"))

	return {n.name: n for n in arvore.body if isinstance(n, ast.FunctionDef)}


def _decoradores(funcao: ast.FunctionDef) -> list[str]:
	return [ast.unparse(d.func if isinstance(d, ast.Call) else d) for d in funcao.decorator_list]


def _js() -> str:
	return JS.read_text(encoding="utf-8")


class TestEndpointsExpostos(unittest.TestCase):
	def test_so_duas_funcoes_sao_whitelist(self):
		expostas = {n for n, f in _funcoes().items() if "frappe.whitelist" in _decoradores(f)}

		self.assertEqual(expostas, FUNCOES_EXPOSTAS)

	def test_ambas_tem_limite_de_uso(self):
		"""Os provedores públicos limitam por IP; um laço no navegador não pode esgotar o do servidor."""
		for nome in FUNCOES_EXPOSTAS:
			with self.subTest(funcao=nome):
				self.assertIn("rate_limit", _decoradores(_funcoes()[nome]))

	def test_o_navegador_nao_consegue_injetar_a_funcao_de_rede(self):
		"""Teste-âncora. Argumento de endpoint vem do cliente; `buscar` só existe nas internas."""
		for nome in FUNCOES_EXPOSTAS:
			args = {a.arg for a in _funcoes()[nome].args.args}

			with self.subTest(funcao=nome):
				self.assertFalse(args & {"buscar", "http"}, f"{nome} expõe a chamada de rede ao cliente")

	def test_as_internas_aceitam_a_chamada_de_rede_para_o_teste(self):
		for nome in ("consultar", "criar_endereco"):
			with self.subTest(funcao=nome):
				self.assertIn("buscar", {a.arg for a in _funcoes()[nome].args.args})

	def test_exige_permissao_antes_de_qualquer_consulta(self):
		"""A primeira instrução (depois da docstring) é a checagem de permissão."""
		for nome in FUNCOES_EXPOSTAS:
			instrucoes = [
				n
				for n in _funcoes()[nome].body
				if not isinstance(n, ast.Expr) or not isinstance(n.value, ast.Constant)
			]

			with self.subTest(funcao=nome):
				self.assertEqual(ast.unparse(instrucoes[0]), "_exigir_permissao(doctype)")

	def test_so_os_tres_cadastros_com_cnpj_sao_aceitos(self):
		self.assertEqual(set(CAMPO_NOME_POR_DOCTYPE), {"Customer", "Supplier", "Company"})


class TestNuncaTravaOCadastro(unittest.TestCase):
	def test_a_unica_excecao_levantada_e_a_de_permissao(self):
		"""Provedor fora do ar, CNPJ inexistente e resposta estranha são resultado, não falha."""
		levantadas = [
			ast.unparse(n.exc.func if isinstance(n.exc, ast.Call) else n.exc)
			for n in ast.walk(ast.parse(MODULO.read_text(encoding="utf-8")))
			if isinstance(n, ast.Raise) and n.exc is not None
		]

		self.assertEqual(levantadas, ["frappe.PermissionError"])

	def test_a_chamada_de_rede_tem_prazo_curto_e_nao_segue_redirecionamento(self):
		fonte = MODULO.read_text(encoding="utf-8")
		prazo = int(re.search(r"^ESPERA_S\s*=\s*(\d+)", fonte, re.M).group(1))

		self.assertIn("timeout=ESPERA_S", fonte)
		self.assertIn("allow_redirects=False", fonte)
		self.assertLessEqual(prazo, 10, "o usuário está parado esperando o campo; o fallback é digitar")

	def test_as_urls_vem_so_da_camada_pura(self):
		"""O CNPJ entra na URL só por `url_do_provedor` (que valida o modelo); nenhum provedor fixo aqui."""
		fonte = MODULO.read_text(encoding="utf-8")

		self.assertIn("url_do_provedor(", fonte)

		for provedor in ("brasilapi.com.br", "minhareceita.org"):
			with self.subTest(provedor=provedor):
				self.assertNotIn(
					provedor, fonte.replace(provedor + "`", ""), "a URL base mora na camada pura"
				)

	def test_lista_configurada_invalida_nao_volta_aos_provedores_padrao(self):
		"""Quem configurou o próprio provedor quis evitar terceiros; cair nos padrão reintroduziria o envio."""
		modelos = _funcoes()["_modelos"]
		retornos = [ast.unparse(n.value) for n in ast.walk(modelos) if isinstance(n, ast.Return)]

		self.assertEqual(sum("MODELOS_PADRAO" in r for r in retornos), 1, "só quando nada foi configurado")


class TestPrivacidade(unittest.TestCase):
	def test_nada_de_pessoa_alem_do_cnpj_sai_ou_e_lido(self):
		"""Sócios, e-mail e telefone da Receita nunca são lidos nem guardados."""
		codigo = MODULO.read_text(encoding="utf-8").lower()

		for proibido in ("qsa", "socios", "email", "ddd_telefone", "telefone"):
			if proibido in ("email", "telefone"):
				# aparecem só na docstring que diz que **não** são lidos
				continue

			with self.subTest(campo=proibido):
				self.assertNotIn(proibido, codigo)

	def test_o_cadastro_nao_tem_campo_de_pessoa(self):
		campos = set(CadastroCnpj.__dataclass_fields__) | set(EnderecoCnpj.__dataclass_fields__)

		for proibido in ("socios", "qsa", "email", "telefone", "ddd_telefone_1", "cpf"):
			with self.subTest(campo=proibido):
				self.assertNotIn(proibido, campos)


class TestJsContraOServidor(unittest.TestCase):
	def test_os_metodos_chamados_existem_e_sao_whitelist(self):
		chamados = set(re.findall(r'"erpnext_brasil\.integracao\.consulta_cnpj\.(\w+)"', _js()))

		self.assertEqual(chamados, FUNCOES_EXPOSTAS)

	def test_o_campo_de_nome_do_js_e_o_do_servidor(self):
		bloco = re.search(r"const CAMPO_NOME = \{(.*?)\};", _js(), re.S).group(1)
		no_js = dict(re.findall(r"(\w+):\s*\"(\w+)\"", bloco))

		self.assertEqual(no_js, CAMPO_NOME_POR_DOCTYPE)

	def test_todo_campo_do_endereco_criado_esta_declarado(self):
		"""O `br_*` que o `Address` recebe e a instalação não cria some ao salvar, sem erro."""
		cadastro_endereco = EnderecoCnpj(
			logradouro="RUA X",
			numero="1",
			complemento="",
			bairro="B",
			cep="70040-912",
			municipio="Brasília",
			uf="DF",
			codigo_municipio_ibge="5300108",
		)
		cadastro = CadastroCnpj(**{**_modelo_minimo(), "endereco": cadastro_endereco})
		declarados = {c["fieldname"] for c in custom_fields.get_custom_fields()["Address"]}
		padrao_do_frappe = {"pincode", "address_line1", "address_line2", "city", "state", "country"}

		for campo in campos_do_endereco(cadastro):
			with self.subTest(campo=campo):
				self.assertIn(campo, declarados | padrao_do_frappe)

	def test_nao_consulta_ao_abrir_o_formulario(self):
		"""Consulta é do evento de mudança do CNPJ e do botão, nunca do `refresh` (roda a cada abertura)."""
		refresh = re.search(r"refresh\(frm\) \{(.*?)\n\t\t\t\},", _js(), re.S).group(1)

		self.assertNotRegex(refresh, r"(?<!\")consultar\(frm\)\s*[;,]?\s*$", "só dentro do clique")
		self.assertIn("() => consultar(frm)", refresh)
		self.assertNotIn("frappe.call", refresh)

	def test_so_roda_com_quatorze_caracteres_e_no_brasil(self):
		js = _js()

		self.assertIn("cnpj.length !== 14", js)
		self.assertIn('frm.doc.country !== "Brazil"', js)

	def test_so_preenche_o_que_o_servidor_mandou_preencher(self):
		"""Nenhum campo é gravado por nome: o laço percorre `preencher`, devolvido pelo servidor."""
		js = _js()

		self.assertIn("resposta.preencher", js)
		self.assertNotRegex(js, r'set_value\(\s*"')

	def test_o_endereco_so_nasce_por_clique(self):
		js = _js()
		chamadas = [m.start() for m in re.finditer(r"METODO_ENDERECO", js)]
		dentro_de_criar = js.split("function criar_endereco")[1].split("erpnext_brasil.consulta_cnpj =")[0]

		self.assertEqual(len(chamadas), 2, "a constante e um único uso")
		self.assertIn("METODO_ENDERECO", dentro_de_criar)
		self.assertIn('__("Criar endereço pelo CNPJ"), () => criar_endereco(frm)', js)

	def test_o_texto_vindo_do_servico_e_escapado_antes_de_virar_html(self):
		self.assertGreaterEqual(_js().count("escape_html("), 6)

	def test_a_faixa_de_sugestao_sai_depois_de_salvar(self):
		self.assertRegex(_js(), r'after_save\(frm\) \{[^}]*set_intro\(""\)')


class TestRegistroNoHooks(unittest.TestCase):
	def test_o_js_esta_ligado_aos_tres_cadastros(self):
		arvore = ast.parse((RAIZ / "hooks.py").read_text(encoding="utf-8"))
		doctype_js = next(
			n.value
			for n in arvore.body
			if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "doctype_js"
		)
		mapa = {ast.literal_eval(k): v for k, v in zip(doctype_js.keys, doctype_js.values, strict=True)}

		for doctype in CAMPO_NOME_POR_DOCTYPE:
			with self.subTest(doctype=doctype):
				self.assertEqual(ast.literal_eval(mapa[doctype]), "public/js/consulta_cnpj.js")

		self.assertTrue(JS.exists())


def _modelo_minimo() -> dict:
	return {
		"cnpj": "00000000000191",
		"razao_social": "EMPRESA",
		"nome_fantasia": "",
		"situacao": 2,
		"situacao_descricao": "ATIVA",
		"data_situacao": "2005-11-03",
		"motivo_situacao": "",
		"cnae_codigo": "",
		"cnae_descricao": "",
		"natureza_juridica": "",
		"porte": "",
		"optante_simples": None,
		"mei": None,
		"matriz": True,
	}


if __name__ == "__main__":
	unittest.main()
