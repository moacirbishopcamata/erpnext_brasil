# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A tela de navegação pelo endereçamento, e o que ela não pode fazer errado.

Teste-âncora: `test_soma_por_lft_rgt_e_nao_por_recursao`. `Warehouse` é um *nested set*, e
numa árvore de endereçamento real — rua, prédio, nível, apartamento — descer nó a nó faria
centenas de consultas para responder o que `lft`/`rgt` respondem numa. Não quebraria nada:
a tela ficaria lenta no galpão, que é onde ninguém tem paciência.

Segundo eixo: `test_todo_valor_vai_parametrizado`. Estas funções recebem nome de armazém e
de item vindos da tela. Interpolar isso em SQL seria injeção — e o módulo monta condições
por concatenação, então a conferência precisa existir de verdade.

`integracao/navegador_estoque.py` importa `frappe`: conferência por AST e texto.

Módulo puro: roda sem bench.
"""

import ast
import json
import unittest
from pathlib import Path

from erpnext_brasil.tests.ajudantes import sem_comentarios_js, sem_docstrings

RAIZ = Path(__file__).resolve().parent.parent

_FONTE = (RAIZ / "integracao" / "navegador_estoque.py").read_text(encoding="utf-8")
_SEM_DOC = sem_docstrings(_FONTE)
_ARVORE = ast.parse(_FONTE)

_PAGINA = RAIZ / "estoque" / "page" / "navegador_de_estoque"
_JS = sem_comentarios_js((_PAGINA / "navegador_de_estoque.js").read_text(encoding="utf-8"))
_JSON = json.loads((_PAGINA / "navegador_de_estoque.json").read_text(encoding="utf-8"))

_HOOKS = (RAIZ / "hooks.py").read_text(encoding="utf-8")
_MODULOS = (RAIZ / "modules.txt").read_text(encoding="utf-8")

METODOS_EXPOSTOS = {"conteudo_do_endereco", "enderecos_do_item", "filhos_do_endereco"}


class TestAsConsultas(unittest.TestCase):
	def test_soma_por_lft_rgt_e_nao_por_recursao(self):
		"""Teste-âncora. Descer a árvore nó a nó não quebra — só fica lento onde ninguém
		tem paciência."""
		self.assertIn("lft", _SEM_DOC)
		self.assertIn("rgt", _SEM_DOC)
		self.assertNotIn("get_descendants_of", _SEM_DOC)

	def test_todo_valor_vai_parametrizado(self):
		"""Segundo eixo. As condições são concatenadas; os **valores**, nunca."""
		for proibido in ('f"{endereco', "f'{endereco", 'f"{item', "+ endereco", "+ item"):
			with self.subTest(proibido=proibido):
				self.assertNotIn(proibido, _SEM_DOC)

		self.assertIn("%(lft)s", _SEM_DOC)
		self.assertIn("%(empresa)s", _SEM_DOC)

	def test_le_o_saldo_do_bin(self):
		"""O `Bin` é o saldo já materializado; somar `Stock Ledger Entry` daria o mesmo
		número por um caminho caro."""
		self.assertIn("tabBin", _SEM_DOC)
		self.assertNotIn("Stock Ledger Entry", _SEM_DOC)

	def test_toda_consulta_exposta_tem_teto(self):
		"""Um endereço com milhares de itens travaria a tela do coletor.

		Conferido **por função**, e não contando ocorrências no arquivo: a contagem passaria
		com três tetos na mesma função e nenhum nas outras duas.
		"""
		for no in ast.walk(_ARVORE):
			if isinstance(no, ast.FunctionDef) and no.name in METODOS_EXPOSTOS:
				with self.subTest(funcao=no.name):
					self.assertIn("LIMITE", ast.get_source_segment(_FONTE, no))

	def test_ignora_saldo_zerado(self):
		"""Listar prateleira vazia é mandar o operador andar até ela para não achar nada."""
		self.assertIn("actual_qty != 0", _SEM_DOC)

	def test_ignora_armazem_desabilitado(self):
		self.assertIn('"disabled": 0', _SEM_DOC)

	def test_os_tres_metodos_estao_expostos(self):
		"""Sem `@frappe.whitelist()` a tela chama e recebe erro de permissão."""
		expostos = {
			no.name
			for no in ast.walk(_ARVORE)
			if isinstance(no, ast.FunctionDef)
			and any(
				isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "whitelist"
				for d in no.decorator_list
			)
		}

		self.assertEqual(METODOS_EXPOSTOS, expostos)

	def test_o_modulo_nao_escreve_nada(self):
		"""A tela navega; quem move estoque são os documentos do ERPNext."""
		for escrita in ("db.set_value", "db.sql(\n\t\t\tupdate", "insert(", "delete_doc", ".save("):
			with self.subTest(escrita=escrita):
				self.assertNotIn(escrita, _SEM_DOC)


class TestAPagina(unittest.TestCase):
	def test_a_pagina_esta_no_modulo_declarado(self):
		"""Módulo fora do `modules.txt` faz a página não ser instalada."""
		self.assertEqual("Estoque", _JSON["module"])
		self.assertIn("Estoque", _MODULOS.split("\n"))

	def test_a_pagina_e_padrao_do_app(self):
		"""`standard: No` faria a página virar registro de banco, e sumir num site novo."""
		self.assertEqual("Yes", _JSON["standard"])

	def test_a_pagina_tem_papel_de_estoque(self):
		"""Sem papel declarado, só o Administrator enxerga — e o estoquista não é."""
		papeis = {p["role"] for p in _JSON["roles"]}

		self.assertIn("Stock User", papeis)

	def test_o_nome_do_arquivo_bate_com_o_name(self):
		"""O Frappe procura o `.js` pelo `name` da página; divergir carrega tela em branco."""
		self.assertEqual("navegador-de-estoque", _JSON["name"])
		self.assertIn('frappe.pages["navegador-de-estoque"]', _JS)


class TestOReusoDoLeitor(unittest.TestCase):
	def test_a_leitura_reusa_o_resolvedor_gs1(self):
		"""Uma segunda forma de resolver código de barras divergiria da primeira sem
		ninguém perceber."""
		self.assertIn("erpnext_brasil.integracao.leitura_gs1.ler_codigo", _JS)

	def test_a_tela_nao_reimplementa_a_busca_por_codigo(self):
		self.assertNotIn("Item Barcode", _JS)
		self.assertNotIn("scan_barcode", _JS)

	def test_o_item_lido_tem_precedencia_sobre_o_armazem(self):
		"""O resolvedor pode devolver os dois; o item é o mais específico."""
		self.assertLess(_JS.index("dados.item_code"), _JS.index("dados.warehouse"))

	def test_o_css_esta_registrado(self):
		"""CSS não declarado nunca é servido, e a tela sai sem alvo de toque."""
		self.assertIn("css/navegador_de_estoque.css", _HOOKS)

	def test_o_html_escapa_o_que_vem_do_banco(self):
		"""Nome de armazém é texto livre do usuário; interpolá-lo cru no HTML é XSS."""
		self.assertIn("escape_html", _JS)
		self.assertGreaterEqual(_JS.count("escape_html"), 10)


if __name__ == "__main__":
	unittest.main()
