# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Costura entre o JavaScript do cliente e o Python que ele chama.

Mesma classe de gap dos 31 campos de `docs/gaps.md`: o navegador chama um método por
**string**, e uma string errada não quebra nada em teste — quebra no clique do usuário,
com "método não encontrado" e nenhuma pista de onde está o erro.

Aqui a verificação é de texto contra código: todo `method:` citado num `.js` deste app
existe como função com `@frappe.whitelist()`. Roda sem bench, porque as duas fontes são
arquivos.

O que **não** substitui: clicar no botão num site real. A lacuna segue em `docs/gaps.md`.
"""

import ast
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

_CHAMADA = re.compile(r'method:\s*["\']([\w.]+)["\']')


def _metodos_chamados() -> set[str]:
	chamados: set[str] = set()

	for arquivo in (RAIZ / "public" / "js").glob("*.js"):
		chamados |= set(_CHAMADA.findall(arquivo.read_text(encoding="utf-8")))

	return {m for m in chamados if m.startswith("erpnext_brasil.")}


def _tem_whitelist(caminho: Path, funcao: str) -> bool:
	"""Confere no AST que a função existe **e** está exposta.

	Procurar `@frappe.whitelist()` por texto acharia o decorador de outra função no mesmo
	arquivo — o que é justamente o erro que este teste existe para pegar.
	"""
	arvore = ast.parse(caminho.read_text(encoding="utf-8"))

	for no in ast.walk(arvore):
		if not isinstance(no, ast.FunctionDef) or no.name != funcao:
			continue

		for decorador in no.decorator_list:
			alvo = decorador.func if isinstance(decorador, ast.Call) else decorador

			if isinstance(alvo, ast.Attribute) and alvo.attr == "whitelist":
				return True

	return False


class TestMetodosChamadosPeloCliente(unittest.TestCase):
	def test_ha_chamadas_a_conferir(self):
		"""Sem isto, os testes abaixo passariam por vacuidade se o regex quebrasse."""
		self.assertTrue(_metodos_chamados(), "nenhuma chamada encontrada — regex quebrou?")

	def test_todo_metodo_chamado_existe_e_esta_exposto(self):
		for caminho_ponto in sorted(_metodos_chamados()):
			modulo, funcao = caminho_ponto.rsplit(".", 1)
			arquivo = RAIZ.parent / (modulo.replace(".", "/") + ".py")

			with self.subTest(metodo=caminho_ponto):
				self.assertTrue(arquivo.exists(), f"módulo inexistente: {arquivo}")
				self.assertTrue(
					_tem_whitelist(arquivo, funcao),
					f"{funcao} não existe em {modulo} ou não tem @frappe.whitelist()",
				)

	def test_todo_js_do_app_esta_ligado_em_hooks(self):
		"""JavaScript que ninguém carrega é código morto com aparência de recurso."""
		hooks = (RAIZ / "hooks.py").read_text(encoding="utf-8")

		for arquivo in (RAIZ / "public" / "js").glob("*.js"):
			with self.subTest(arquivo=arquivo.name):
				self.assertIn(arquivo.name, hooks)


class TestBotaoDeEmissao(unittest.TestCase):
	def _fonte(self) -> str:
		return (RAIZ / "public" / "js" / "emissao_nfe.js").read_text(encoding="utf-8")

	def test_so_aparece_em_documento_efetivado(self):
		"""Rascunho não tem NF-e a emitir: o número seria consumido por algo que ainda
		pode mudar."""
		self.assertIn("docstatus !== 1", self._fonte())

	def test_nao_aparece_se_ja_ha_chave_de_acesso(self):
		"""Documento com chave já foi emitido — reemitir queimaria outro número."""
		self.assertIn("br_chave_acesso", self._fonte())

	def test_pede_confirmacao_antes_de_emitir(self):
		"""Emitir é irreversível: o número é consumido mesmo se a SEFAZ recusar."""
		self.assertIn("frappe.confirm", self._fonte())

	def test_a_confirmacao_diz_o_ambiente(self):
		"""A diferença entre homologação e produção é a diferença entre um teste e um
		documento que existe perante o Fisco."""
		self.assertIn("br_ambiente_sefaz", self._fonte())

	def test_congela_a_tela_durante_a_transmissao(self):
		"""Sem `freeze`, o segundo clique consome outro número."""
		self.assertIn("freeze: true", self._fonte())


if __name__ == "__main__":
	unittest.main()
