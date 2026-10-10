# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A costura da consulta de CEP: Python ↔ JS ↔ `hooks.py` ↔ campos declarados.

`integracao/consulta_cep.py` importa `frappe`, então a suíte pura não o executa (o comportamento é
provado em `tests_bench/test_consulta_cep.py`). O que cabe aqui é o que se quebra **sem erro**: um nome de
método trocado no JS, um campo que o JS preenche e a instalação nunca criou, um parâmetro que deixaria o
navegador injetar a função de rede, uma chamada sem prazo.

Teste-âncora: `test_o_navegador_nao_consegue_injetar_a_funcao_de_rede`. Os dois endpoints expostos têm a
chamada HTTP como parâmetro das funções **internas** (`consultar`, `buscar`), para o teste trocá-la — e esses
parâmetros não podem aparecer nas funções que o navegador alcança.
"""

import ast
import pathlib
import re
import unittest

from erpnext_brasil.fiscal.endereco_cep import CAMPOS_DO_ENDERECO
from erpnext_brasil.setup import custom_fields

RAIZ = pathlib.Path(__file__).resolve().parents[1]
MODULO = RAIZ / "integracao" / "consulta_cep.py"
JS = RAIZ / "public" / "js" / "endereco_cep.js"

FUNCOES_EXPOSTAS = {"consultar_cep", "buscar_logradouro"}


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
		"""O ViaCEP avisa que uso massivo pode levar a bloqueio por tempo indeterminado."""
		for nome in FUNCOES_EXPOSTAS:
			with self.subTest(funcao=nome):
				self.assertIn("rate_limit", _decoradores(_funcoes()[nome]))

	def test_o_navegador_nao_consegue_injetar_a_funcao_de_rede(self):
		"""Teste-âncora. Argumento de endpoint vem do cliente; `buscar`/`http` só existem nas internas."""
		for nome in FUNCOES_EXPOSTAS:
			args = {a.arg for a in _funcoes()[nome].args.args}

			with self.subTest(funcao=nome):
				self.assertFalse(args & {"buscar", "http"}, f"{nome} expõe a chamada de rede ao cliente")

	def test_as_internas_aceitam_a_chamada_de_rede_para_o_teste(self):
		self.assertIn("buscar", {a.arg for a in _funcoes()["consultar"].args.args})
		self.assertIn("http", {a.arg for a in _funcoes()["buscar"].args.args})

	def test_exige_permissao_antes_de_qualquer_consulta(self):
		"""A primeira instrução (depois da docstring) é a checagem de permissão."""
		for nome in FUNCOES_EXPOSTAS:
			instrucoes = [
				n
				for n in _funcoes()[nome].body
				if not isinstance(n, ast.Expr) or not isinstance(n.value, ast.Constant)
			]

			with self.subTest(funcao=nome):
				self.assertEqual(ast.unparse(instrucoes[0]), "_exigir_permissao()")


class TestNuncaTravaOCadastro(unittest.TestCase):
	def test_a_unica_excecao_levantada_e_a_de_permissao(self):
		"""Serviço fora do ar e CEP inexistente são resultado, não falha: nada além de permissão sobe."""
		levantadas = [
			ast.unparse(n.exc.func if isinstance(n.exc, ast.Call) else n.exc)
			for n in ast.walk(ast.parse(MODULO.read_text(encoding="utf-8")))
			if isinstance(n, ast.Raise) and n.exc is not None
		]

		self.assertEqual(levantadas, ["frappe.PermissionError"])

	def test_a_chamada_de_rede_tem_prazo_curto(self):
		fonte = MODULO.read_text(encoding="utf-8")
		prazo = int(re.search(r"^ESPERA_S\s*=\s*(\d+)", fonte, re.M).group(1))

		self.assertIn("timeout=ESPERA_S", fonte)
		self.assertLessEqual(prazo, 10, "o usuário está parado esperando o campo; o fallback é digitar")

	def test_so_chama_urls_montadas_pela_camada_pura(self):
		"""Texto do usuário nunca entra numa URL sem passar por `url_por_*` (que o codifica)."""
		fonte = MODULO.read_text(encoding="utf-8")

		self.assertIn("url_por_cep(", fonte)
		self.assertIn("url_por_logradouro(", fonte)
		self.assertNotIn("viacep.com.br", fonte, "a URL base mora na camada pura")

	def test_nenhum_dado_de_pessoa_vai_ao_servico(self):
		"""Só CEP e texto de busca saem; nome e documento não existem neste módulo."""
		codigo = "\n".join(
			linha
			for linha in MODULO.read_text(encoding="utf-8").splitlines()
			if not linha.strip().startswith("#")
		)

		for proibido in ("customer_name", "tax_id", "first_name", "email_id", "phone"):
			with self.subTest(campo=proibido):
				self.assertNotIn(proibido, codigo)


class TestJsContraOServidor(unittest.TestCase):
	def test_os_metodos_chamados_existem_e_sao_whitelist(self):
		chamados = set(re.findall(r'"erpnext_brasil\.integracao\.consulta_cep\.(\w+)"', _js()))

		self.assertEqual(chamados, FUNCOES_EXPOSTAS)

	def test_os_campos_do_js_sao_os_que_o_servidor_conhece(self):
		bloco = re.search(r"const CAMPOS = \[(.*?)\];", _js(), re.S).group(1)
		no_js = tuple(re.findall(r'"(\w+)"', bloco))

		self.assertEqual(no_js, CAMPOS_DO_ENDERECO)

	def test_todo_campo_que_a_consulta_preenche_esta_declarado(self):
		"""O `br_*` que o JS preenche e a instalação não cria some ao salvar, sem erro."""
		declarados = {c["fieldname"] for c in custom_fields.get_custom_fields()["Address"]}
		padrao_do_frappe = {"pincode", "address_line1", "city", "state"}

		for campo in CAMPOS_DO_ENDERECO:
			with self.subTest(campo=campo):
				self.assertIn(campo, declarados | padrao_do_frappe)

	def test_so_roda_em_endereco_do_brasil_e_com_oito_digitos(self):
		js = _js()

		self.assertIn('frm.doc.country === "Brazil"', js)
		self.assertIn("cep.length !== 8", js)

	def test_nao_consulta_ao_abrir_o_formulario(self):
		"""Consulta é do evento de mudança do CEP, nunca do `refresh` (que roda a cada abertura)."""
		refresh = re.search(r"refresh\(frm\) \{(.*?)\n\t\t\},", _js(), re.S).group(1)

		self.assertNotIn("consultar(", refresh)

	def test_so_preenche_o_que_o_servidor_mandou_preencher(self):
		"""Nenhum campo é gravado por nome: o laço percorre `preencher`, devolvido pelo servidor."""
		js = _js()

		self.assertIn("resposta.preencher", js)
		self.assertNotRegex(
			js, r'set_value\(\s*"(address_line1|city|state|br_bairro|br_codigo_municipio_ibge)"'
		)

	def test_divergencia_e_avisada_nunca_aplicada(self):
		js = _js()
		avisar = js.split("function avisar_divergencias")[1].split("function aplicar")[0]

		self.assertIn("avisar_divergencias(resposta.divergencias)", js)
		self.assertNotIn(
			"set_value", avisar, "a divergência é mostrada ao usuário, não aplicada ao formulário"
		)

	def test_o_texto_vindo_do_servico_e_escapado_antes_de_virar_html(self):
		js = _js()

		self.assertGreaterEqual(js.count("escape_html("), 4)

	def test_a_faixa_de_sugestao_sai_depois_de_salvar(self):
		self.assertRegex(_js(), r'after_save\(frm\) \{[^}]*set_intro\(""\)')


class TestRegistroNoHooks(unittest.TestCase):
	def test_o_js_esta_ligado_ao_address(self):
		arvore = ast.parse((RAIZ / "hooks.py").read_text(encoding="utf-8"))
		doctype_js = next(
			n.value
			for n in arvore.body
			if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "doctype_js"
		)
		mapa = {ast.literal_eval(k): v for k, v in zip(doctype_js.keys, doctype_js.values, strict=True)}

		self.assertEqual(ast.literal_eval(mapa["Address"]), "public/js/endereco_cep.js")
		self.assertTrue((RAIZ / "public" / "js" / "endereco_cep.js").exists())


if __name__ == "__main__":
	unittest.main()
