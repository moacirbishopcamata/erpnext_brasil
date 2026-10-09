# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A costura de `integracao/medicao_do_relogio.py`, lida do fonte — tarefas 2.2, 3.1 e 3.2.

O módulo importa `frappe`, então a suíte pura não o executa (o comportamento contra o cache real está
em `tests_bench/test_medicao_do_relogio.py`). O que cabe aqui é a classe de bug que o projeto já
pagou caro: **o que um lado escreve e o outro lê**. A medição é gravada por `guardar` e relida por
`ler_ultima` — se uma chave de um lado mudar de nome e a do outro não, a guarda lê `None`, cai em
`sem_medicao` e **nunca bloqueia**, sem erro nenhum. É um defeito que a suíte de cada função isolada
não pega.

Teste-âncora: `test_o_que_guardar_escreve_e_o_que_ler_ultima_le_sao_as_mesmas_chaves`.
"""

import ast
import pathlib
import unittest

from erpnext_brasil import hooks
from erpnext_brasil.fiscal.relogio_politica import CHAVES

FONTE = pathlib.Path(__file__).resolve().parents[1] / "integracao" / "medicao_do_relogio.py"


def _arvore() -> ast.Module:
	return ast.parse(FONTE.read_text(encoding="utf-8"))


def _funcao(nome: str) -> ast.FunctionDef:
	return next(n for n in ast.walk(_arvore()) if isinstance(n, ast.FunctionDef) and n.name == nome)


def _chaves_escritas() -> set[str]:
	"""As chaves do dict literal que `guardar` passa para o cache na `CHAVE_ULTIMA`."""
	for no in ast.walk(_funcao("guardar")):
		if isinstance(no, ast.Dict):
			return {k.value for k in no.keys if isinstance(k, ast.Constant)}

	raise AssertionError("guardar não grava um dict")


def _chaves_lidas() -> set[str]:
	lidas = set()

	for no in ast.walk(_funcao("ler_ultima")):
		if isinstance(no, ast.Subscript) and isinstance(no.slice, ast.Constant):
			lidas.add(no.slice.value)
		elif (
			isinstance(no, ast.Call)
			and isinstance(no.func, ast.Attribute)
			and no.func.attr == "get"
			and isinstance(no.args[0], ast.Constant)
			and isinstance(no.func.value, ast.Name)
			and no.func.value.id == "bruto"
		):
			lidas.add(no.args[0].value)

	return lidas


class TestCosturaDaMedicao(unittest.TestCase):
	def test_o_que_guardar_escreve_e_o_que_ler_ultima_le_sao_as_mesmas_chaves(self):
		escritas, lidas = _chaves_escritas(), _chaves_lidas()

		self.assertGreater(len(lidas), 5, "o extrator não achou o que devia")
		self.assertEqual(sorted(lidas - escritas), [], "lida e nunca escrita: a guarda leria None")
		self.assertEqual(sorted(escritas - lidas), [], "escrita e nunca lida: dado que ninguém usa")

	def test_ler_ultima_nao_aplica_a_validade(self):
		"""Quem sabe o `ttl_s` é `avaliar`; ler já descartando a medição esconderia 'vencida'."""
		# Só identificadores: o docstring cita `ttl_s` justamente para dizer que a função não o usa.
		identificadores = {
			(n.id if isinstance(n, ast.Name) else n.attr)
			for n in ast.walk(_funcao("ler_ultima"))
			if isinstance(n, ast.Name | ast.Attribute)
		}

		self.assertFalse({i for i in identificadores if "ttl" in i or "idade" in i or "agora" in i})

	def test_a_retencao_no_cache_e_maior_que_a_validade_padrao(self):
		from erpnext_brasil.fiscal.relogio_politica import ConfiguracaoRelogio

		retencao = next(
			ast.literal_eval(n.value)
			for n in _arvore().body
			if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "RETENCAO_S"
		)

		self.assertGreater(retencao, ConfiguracaoRelogio().ttl_s)

	def test_a_tarefa_horaria_esta_ligada_em_hooks_e_existe(self):
		alvo = "erpnext_brasil.integracao.medicao_do_relogio.medir_e_guardar"

		self.assertIn(alvo, hooks.scheduler_events["hourly"])
		self.assertEqual(_funcao("medir_e_guardar").name, alvo.rsplit(".", 1)[1])

	def test_a_tarefa_horaria_e_nova_e_nao_trocou_as_diarias(self):
		diarias = hooks.scheduler_events["daily"]

		self.assertIn(
			"erpnext_brasil.integracao.alerta_certificado.verificar_validade_dos_certificados", diarias
		)

	def test_o_cache_aceita_o_v15_e_o_v16(self):
		"""`frappe.cache` é função no v15 e objeto no v16 — o piso declarado do app é o v15."""
		corpo = ast.unparse(_funcao("_cache"))

		self.assertIn("callable(cache)", corpo)

	def test_a_configuracao_invalida_nao_para_a_emissao_mas_fica_registrada(self):
		corpo = ast.unparse(_funcao("configuracao"))

		self.assertIn("ConfiguracaoInvalida", corpo)
		self.assertIn("log_error", corpo)
		self.assertNotIn("throw", corpo)

	def test_a_falha_de_medicao_e_registrada_com_a_causa(self):
		corpo = ast.unparse(_funcao("_registrar_falha_de_medicao"))

		self.assertIn("log_error", corpo)
		self.assertIn("rodada.erros", corpo)

	def test_o_aviso_usa_o_canal_dos_outros_alertas_fiscais(self):
		fonte = FONTE.read_text(encoding="utf-8")

		self.assertIn("from erpnext_brasil.integracao.notificacao import notificar_responsaveis", fonte)

	def test_as_chaves_de_configuracao_sao_unicas_e_prefixadas(self):
		valores = list(CHAVES.values())

		self.assertEqual(len(valores), len(set(valores)))
		self.assertTrue(all(v.startswith("brasil_ntp_") for v in valores))


if __name__ == "__main__":
	unittest.main()
