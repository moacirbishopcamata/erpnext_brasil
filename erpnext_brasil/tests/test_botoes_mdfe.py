# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A costura da tela do MDF-e: JS ↔ Python ↔ `hooks.py`.

`integracao/emissao_mdfe.py` e `integracao/eventos_mdfe.py` importam `frappe`, então a suíte pura não os
executa (o comportamento está em `tests_bench/test_emissao_mdfe.py` e `test_eventos_mdfe.py`). O que cabe
aqui é o que se quebra **sem erro**: um nome de método trocado no JS, um endpoint sem `whitelist`, um botão
oferecido num estado em que a SEFAZ recusaria, um evento sem gatilho que ganhou botão por engano.

Teste-âncora: `test_so_o_estado_autorizado_oferece_encerrar_e_cancelar`.
"""

import ast
import pathlib
import re
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
JS = RAIZ / "public" / "js" / "emissao_mdfe.js"

METODOS_ESPERADOS = {
	"erpnext_brasil.integracao.emissao_mdfe.emitir_mdfe",
	"erpnext_brasil.integracao.eventos_mdfe.estado_do_mdfe",
	"erpnext_brasil.integracao.eventos_mdfe.encerrar_mdfe",
	"erpnext_brasil.integracao.eventos_mdfe.cancelar_mdfe",
}


def _js() -> str:
	return JS.read_text(encoding="utf-8")


def _funcoes(modulo: str) -> dict[str, ast.FunctionDef]:
	arvore = ast.parse((RAIZ / "integracao" / f"{modulo}.py").read_text(encoding="utf-8"))

	return {n.name: n for n in arvore.body if isinstance(n, ast.FunctionDef)}


def _decoradores(funcao: ast.FunctionDef) -> list[str]:
	return [ast.unparse(d.func if isinstance(d, ast.Call) else d) for d in funcao.decorator_list]


def _tabela(nome: str) -> dict[str, list[str]]:
	bloco = re.search(rf"const {nome} = \{{(.*?)\n\}};", _js(), re.S).group(1)

	return {
		chave.strip('"'): re.findall(r'"(\w+)"', valor)
		for chave, valor in re.findall(r'("?[\w ãé]+"?):\s*\[(.*?)\]', bloco)
	}


class TestMetodosChamados(unittest.TestCase):
	def test_os_metodos_do_js_sao_os_esperados(self):
		self.assertEqual(set(re.findall(r'method: "([\w.]+)"', _js())), METODOS_ESPERADOS)

	def test_todo_metodo_chamado_existe_e_e_whitelist(self):
		for caminho in METODOS_ESPERADOS:
			*_, modulo, nome = caminho.split(".")

			with self.subTest(metodo=caminho):
				funcoes = _funcoes(modulo)

				self.assertIn(nome, funcoes)
				self.assertIn("frappe.whitelist", _decoradores(funcoes[nome]))

	def test_nenhum_outro_endpoint_e_exposto(self):
		for modulo, esperados in (
			("emissao_mdfe", {"emitir_mdfe"}),
			("eventos_mdfe", {"estado_do_mdfe", "encerrar_mdfe", "cancelar_mdfe"}),
		):
			expostas = {n for n, f in _funcoes(modulo).items() if "frappe.whitelist" in _decoradores(f)}

			with self.subTest(modulo=modulo):
				self.assertEqual(expostas, esperados)

	def test_os_endpoints_checam_permissao_do_documento(self):
		"""Quem emite, encerra ou cancela é quem teria permissão no `Shipment`: ler, enviar e cancelar."""
		eventos = (RAIZ / "integracao" / "eventos_mdfe.py").read_text(encoding="utf-8")
		emissao = (RAIZ / "integracao" / "emissao_mdfe.py").read_text(encoding="utf-8")

		self.assertIn('doc.check_permission("read")', eventos)
		self.assertIn('_contexto(name, "submit")', eventos)
		self.assertIn('_contexto(name, "cancel")', eventos)
		self.assertIn('doc.check_permission("submit")', emissao)


class TestBotoesPorEstado(unittest.TestCase):
	def test_so_o_estado_autorizado_oferece_encerrar_e_cancelar(self):
		"""Teste-âncora. Encerrar ou cancelar fora de "autorizado" é recusa certa da SEFAZ."""
		acoes = _tabela("ACOES_POR_ESTADO_MDFE")

		for estado, botoes in acoes.items():
			ofereceu = {"encerrar", "cancelar"} & set(botoes)

			with self.subTest(estado=estado):
				self.assertEqual(bool(ofereceu), estado == "Autorizado")

	def test_emitir_so_onde_nao_ha_manifesto_autorizado(self):
		acoes = _tabela("ACOES_POR_ESTADO_MDFE")

		self.assertEqual({e for e, b in acoes.items() if "emitir" in b}, {"Não emitido", "Rejeitado"})

	def test_encerrado_cancelado_e_denegado_nao_oferecem_nada(self):
		acoes = _tabela("ACOES_POR_ESTADO_MDFE")

		for estado in ("Encerrado", "Cancelado", "Denegado"):
			with self.subTest(estado=estado):
				self.assertNotIn(estado, acoes)

	def test_todo_botao_da_tabela_existe(self):
		botoes = set(re.findall(r"^\t(\w+): \{ rotulo", _js(), re.M))
		usados = {b for lista in _tabela("ACOES_POR_ESTADO_MDFE").values() for b in lista}

		self.assertEqual(usados, botoes)

	def test_nenhum_evento_sem_gatilho_ganha_botao(self):
		"""Condutor, inclusão de DF-e, pagamento e confirmação de serviço não têm dado no cadastro (5.6)."""
		js = _js()

		for evento in ("condutor", "inclusao", "pagamento", "confirmacao", "incluir"):
			with self.subTest(evento=evento):
				self.assertNotRegex(js, rf"add_custom_button\([^)]*{evento}")
				self.assertNotIn(f"_{evento}_mdfe", js.replace("_mdfe(", "_mdfe ("))

	def test_a_situacao_vem_do_servidor_nao_do_campo_local(self):
		"""Uma chave local sobrevive ao cancelamento; só os registros dizem a verdade."""
		js = _js()

		self.assertIn("estado_do_mdfe", js)
		self.assertNotIn("br_chave_acesso", js)

	def test_ha_confirmacao_antes_de_cada_acao_irreversivel(self):
		js = _js()

		for funcao in (
			"confirmar_e_emitir_mdfe",
			"confirmar_e_encerrar_mdfe",
			"pedir_justificativa_e_cancelar_mdfe",
		):
			with self.subTest(funcao=funcao):
				self.assertIn(f"function {funcao}", js)

		self.assertGreaterEqual(js.count("frappe.confirm("), 3)

	def test_o_clique_nao_dispara_duas_vezes(self):
		"""Fala com a SEFAZ e demora: sem `freeze` o segundo clique transmitiria de novo."""
		self.assertEqual(_js().count("freeze: true"), 3)


class TestRegistroNoHooks(unittest.TestCase):
	def test_o_js_esta_ligado_ao_shipment(self):
		arvore = ast.parse((RAIZ / "hooks.py").read_text(encoding="utf-8"))
		doctype_js = next(
			n.value
			for n in arvore.body
			if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "doctype_js"
		)
		mapa = {ast.literal_eval(k): v for k, v in zip(doctype_js.keys, doctype_js.values, strict=True)}

		self.assertEqual(ast.literal_eval(mapa["Shipment"]), "public/js/emissao_mdfe.js")
		self.assertTrue(JS.exists())


if __name__ == "__main__":
	unittest.main()
