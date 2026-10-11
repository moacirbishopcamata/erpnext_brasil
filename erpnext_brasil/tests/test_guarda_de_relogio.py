# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A guarda de relógio no ponto de emissão, lida do fonte — tarefas 4.1 e 4.2 de `fonte-de-tempo-ntp-br`.

Os módulos de emissão importam `frappe`, então a suíte pura não os executa (o efeito está em
`tests_bench/test_emissao_cte.py`). O que cabe aqui é a **posição** da chamada, que é o que dá sentido
à guarda: ela só protege a série se rodar **antes** de alocar número.

Teste-âncora: `test_a_guarda_e_a_primeira_instrucao_de_cada_emissao`. A guarda de consumo indevido é
injetada no `TransporteSefaz`, que nasce depois da alocação do número; copiar esse lugar para a de
relógio queimaria um número da série a cada recusa.
"""

import ast
import pathlib
import unittest

INTEGRACAO = pathlib.Path(__file__).resolve().parents[1] / "integracao"

EMISSOES = {"emissao_nfe": "emitir_nfe", "emissao_cte": "emitir_cte", "emissao_mdfe": "emitir_mdfe"}
"""A emissão da NFC-e (`emitir-nfce-do-pos`) entra aqui quando existir; ver as tarefas dessa mudança."""

QUEM_ALOCA_OU_TRANSMITE = {
	"numero_do_documento",
	"montar_nfe_do_documento",
	"montar_cte_do_documento",
	"montar_mdfe_do_documento",
	"TransporteSefaz",
	"carregar_certificado_da_empresa",
}


def _arvore(modulo: str) -> ast.Module:
	return ast.parse((INTEGRACAO / f"{modulo}.py").read_text(encoding="utf-8"))


def _funcao(modulo: str, nome: str) -> ast.FunctionDef:
	return next(n for n in ast.walk(_arvore(modulo)) if isinstance(n, ast.FunctionDef) and n.name == nome)


def _instrucoes(funcao: ast.FunctionDef) -> list[ast.stmt]:
	corpo = list(funcao.body)

	if corpo and isinstance(corpo[0], ast.Expr) and isinstance(corpo[0].value, ast.Constant):
		corpo = corpo[1:]  # docstring

	return corpo


def _nome_da_chamada(no: ast.AST) -> str:
	if isinstance(no, ast.Call):
		return no.func.id if isinstance(no.func, ast.Name) else getattr(no.func, "attr", "")

	return ""


class TestPosicaoDaGuarda(unittest.TestCase):
	def test_a_guarda_e_a_primeira_instrucao_de_cada_emissao(self):
		for modulo, funcao in EMISSOES.items():
			with self.subTest(emissao=f"{modulo}.{funcao}"):
				primeira = _instrucoes(_funcao(modulo, funcao))[0]

				self.assertIsInstance(primeira, ast.Expr)
				self.assertEqual(_nome_da_chamada(primeira.value), "garantir_relogio_confiavel")

	def test_a_guarda_vem_antes_de_alocar_numero_ou_transmitir(self):
		for modulo, funcao in EMISSOES.items():
			with self.subTest(emissao=f"{modulo}.{funcao}"):
				linhas_da_guarda = None
				primeira_que_aloca = None

				for no in ast.walk(_funcao(modulo, funcao)):
					nome = _nome_da_chamada(no)

					if nome == "garantir_relogio_confiavel":
						linhas_da_guarda = no.lineno
					elif nome in QUEM_ALOCA_OU_TRANSMITE and (
						primeira_que_aloca is None or no.lineno < primeira_que_aloca
					):
						primeira_que_aloca = no.lineno

				self.assertIsNotNone(linhas_da_guarda)
				self.assertIsNotNone(primeira_que_aloca, "o teste deixou de achar quem aloca número")
				self.assertLess(linhas_da_guarda, primeira_que_aloca)

	def test_cada_emissao_importa_a_guarda_do_lugar_certo(self):
		for modulo in EMISSOES:
			with self.subTest(modulo=modulo):
				fonte = (INTEGRACAO / f"{modulo}.py").read_text(encoding="utf-8")

				self.assertIn(
					"from erpnext_brasil.integracao.guarda_de_relogio import garantir_relogio_confiavel",
					fonte,
				)

	def test_a_guarda_de_consumo_indevido_continua_no_transporte_e_nao_foi_trocada(self):
		"""São duas guardas, em dois lugares, por duas razões; uma não substitui a outra."""
		fonte = (INTEGRACAO / "emissao_nfe.py").read_text(encoding="utf-8")

		self.assertIn("guarda=garantir_liberado", fonte)


class TestComportamentoDaGuarda(unittest.TestCase):
	def _modulo(self) -> ast.Module:
		return _arvore("guarda_de_relogio")

	def test_nunca_abre_socket_nem_chama_a_sonda(self):
		"""A sonda leva segundos quando uma fonte não responde: emissão não espera serviço público."""
		importados = {
			n.module if isinstance(n, ast.ImportFrom) else a.name
			for n in ast.walk(self._modulo())
			if isinstance(n, ast.Import | ast.ImportFrom)
			for a in (n.names if isinstance(n, ast.Import) else [n])
		}

		self.assertNotIn("socket", importados)
		self.assertNotIn("erpnext_brasil.integracao.relogio_oficial", importados)

	def test_so_o_critico_levanta(self):
		funcao = _funcao("guarda_de_relogio", "garantir_relogio_confiavel")
		lancamentos = [n for n in ast.walk(funcao) if _nome_da_chamada(n) == "throw"]

		self.assertEqual(len(lancamentos), 1)

		condicionais = [
			n
			for n in ast.walk(funcao)
			if isinstance(n, ast.If) and any(lancamentos[0] is d for d in ast.walk(n))
		]

		self.assertTrue(any("critico" in ast.unparse(c.test) for c in condicionais))

	def test_guarda_desligada_nem_consulta_a_medicao(self):
		funcao = _funcao("guarda_de_relogio", "garantir_relogio_confiavel")
		desligada = next(
			n for n in funcao.body if isinstance(n, ast.If) and "guarda_ligada" in ast.unparse(n.test)
		)

		self.assertNotIn("ler_ultima", ast.unparse(desligada))
		self.assertIsInstance(desligada.body[-1], ast.Return)

	def test_sem_medicao_registra_no_log_do_app_e_nao_no_error_log(self):
		corpo = ast.unparse(_funcao("guarda_de_relogio", "garantir_relogio_confiavel"))

		self.assertIn("frappe.logger", corpo)
		self.assertNotIn("log_error", corpo)


if __name__ == "__main__":
	unittest.main()
