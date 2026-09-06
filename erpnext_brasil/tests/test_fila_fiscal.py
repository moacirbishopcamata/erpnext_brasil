# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Costura da transmissão em fila.

`integracao/fila_fiscal.py` importa `frappe`, então a execução só existe num site. O que se
confere aqui é o que decide se a fila **de fato** protege:

- o `job_id` determinístico, sem o qual o `deduplicate` não reconhece o segundo pedido;
- a fila e o timeout escolhidos, que decidem se a transmissão morre no meio;
- `enqueue_after_commit`, sem o qual o worker pode correr na frente da transação;
- a ausência de `@frappe.whitelist()` no que roda no worker.

Teste-âncora: `test_o_job_id_e_deterministico`. Se ele deixar de ser, o `deduplicate` para
de funcionar **em silêncio** — dois cliques passam a enfileirar dois jobs, e cada um consome
um número da série. Nada quebra; só se emite nota a mais.

Módulo de leitura: roda sem bench.
"""

import ast
import unittest
from pathlib import Path

from erpnext_brasil.tests.ajudantes import sem_comentarios_js, sem_docstrings

RAIZ = Path(__file__).resolve().parent.parent

_FONTE = (RAIZ / "integracao" / "fila_fiscal.py").read_text(encoding="utf-8")
_ARVORE = ast.parse(_FONTE)

_JS_FORM = (RAIZ / "public" / "js" / "emissao_nfe.js").read_text(encoding="utf-8")
_JS_LISTA = (RAIZ / "public" / "js" / "emissao_lote_list.js").read_text(encoding="utf-8")
_HOOKS = (RAIZ / "hooks.py").read_text(encoding="utf-8")


def _funcao(nome: str) -> ast.FunctionDef:
	for no in ast.walk(_ARVORE):
		if isinstance(no, ast.FunctionDef) and no.name == nome:
			return no

	raise AssertionError(f"{nome} não existe em fila_fiscal.py")


def _constante(nome: str):
	for no in _ARVORE.body:
		if isinstance(no, ast.Assign) and any(
			isinstance(alvo, ast.Name) and alvo.id == nome for alvo in no.targets
		):
			return ast.literal_eval(no.value)

	raise AssertionError(f"{nome} não encontrado")


def _argumentos_do_enqueue() -> dict:
	"""Os argumentos nomeados passados a `frappe.enqueue`."""
	for no in ast.walk(_funcao("enfileirar_emissao")):
		if isinstance(no, ast.Call) and getattr(no.func, "attr", "") == "enqueue":
			return {kw.arg: kw.value for kw in no.keywords}

	raise AssertionError("frappe.enqueue não encontrado em enfileirar_emissao")


class TestDeduplicacao(unittest.TestCase):
	"""A barreira que o `freeze` da tela não é."""

	def test_o_job_id_e_deterministico(self):
		"""Teste-âncora: mesmo par `(doctype, name)` tem de dar o mesmo id.

		Se deixar de dar, o `deduplicate` para de funcionar **em silêncio**: dois cliques
		enfileiram dois jobs, cada um consome um número da série, e nada quebra — só se
		emite nota a mais.
		"""
		fonte = ast.get_source_segment(_FONTE, _funcao("job_id_da_emissao"))

		self.assertIn("{doctype}", fonte)
		self.assertIn("{name}", fonte)
		# Nada de aleatório nem de relógio: os dois destruiriam o determinismo.
		for proibido in ("uuid", "random", "now()", "time."):
			with self.subTest(proibido=proibido):
				self.assertNotIn(proibido, fonte)

	def test_o_enqueue_pede_deduplicacao_com_o_job_id(self):
		"""`deduplicate` **exige** `job_id`; um sem o outro não protege nada."""
		argumentos = _argumentos_do_enqueue()

		self.assertIn("job_id", argumentos)
		self.assertTrue(argumentos["deduplicate"].value)

	def test_nao_enfileira_quando_ja_ha_job(self):
		"""Antes de enfileirar, pergunta — e responder `ja_estava` não é erro: significa
		que o pedido anterior ainda está sendo atendido."""
		fonte = ast.get_source_segment(_FONTE, _funcao("enfileirar_emissao"))

		self.assertIn("if not ja_estava:", fonte)
		self.assertIn("ja_estava", fonte)


class TestFilaETimeout(unittest.TestCase):
	def test_usa_a_fila_longa(self):
		"""`short` e `default` têm timeout de 300 s; uma emissão que consulte recibo já
		gasta ~25 s, e a SEFAZ tem dias ruins."""
		self.assertEqual("long", _constante("FILA"))

	def test_o_timeout_e_explicito_e_menor_que_o_da_fila(self):
		"""Um job que passa disso não está lento: está preso. Deixar o teto da fila
		(1500 s) valer ocuparia um worker por 25 minutos com algo que não vai voltar."""
		timeout = _constante("TIMEOUT")

		self.assertGreater(timeout, 300)
		self.assertLess(timeout, 1500)

	def test_o_enqueue_passa_a_fila_e_o_timeout(self):
		argumentos = _argumentos_do_enqueue()

		self.assertIn("queue", argumentos)
		self.assertIn("timeout", argumentos)


class TestOrdemComOCommit(unittest.TestCase):
	def test_enfileira_depois_do_commit(self):
		"""O worker é outro processo com outra conexão: enfileirar antes do commit abre a
		janela em que o job roda e não enxerga o que a transação ainda não gravou."""
		self.assertTrue(_argumentos_do_enqueue()["enqueue_after_commit"].value)

	def test_o_aviso_ao_navegador_tambem_e_depois_do_commit(self):
		"""O aviso não pode chegar antes do dado que ele anuncia."""
		fonte = ast.get_source_segment(_FONTE, _funcao("transmitir_em_fila"))

		self.assertIn("after_commit=True", fonte)


class TestSuperficieExposta(unittest.TestCase):
	def test_o_que_roda_no_worker_nao_e_whitelisted(self):
		"""Expor `transmitir_em_fila` permitiria pular a fila e a deduplicação — que são
		justamente o que este módulo acrescenta."""
		decoradores = _funcao("transmitir_em_fila").decorator_list

		self.assertEqual([], decoradores)

	def test_os_dois_pontos_de_entrada_sao_whitelisted(self):
		for nome in ("enfileirar_emissao", "enfileirar_emissao_em_massa"):
			with self.subTest(metodo=nome):
				alvos = [d.func if isinstance(d, ast.Call) else d for d in _funcao(nome).decorator_list]

				self.assertTrue(any(getattr(a, "attr", "") == "whitelist" for a in alvos))

	def test_a_permissao_e_conferida_antes_de_enfileirar(self):
		fonte = ast.get_source_segment(_FONTE, _funcao("enfileirar_emissao"))

		self.assertLess(fonte.index("check_permission"), fonte.index("frappe.enqueue"))


class TestEmissaoEmMassa(unittest.TestCase):
	def test_um_job_por_documento_e_nao_um_job_para_o_lote(self):
		"""Um lote único falharia inteiro por causa de uma nota, e numeração fiscal não
		permite refazer o que já passou."""
		fonte = ast.get_source_segment(_FONTE, _funcao("enfileirar_emissao_em_massa"))

		self.assertIn("for nome in names:", fonte)
		self.assertIn("enfileirar_emissao(doctype, nome)", fonte)

	def test_documento_sem_permissao_nao_interrompe_os_demais(self):
		"""Interromper faria o usuário descobrir o problema documento a documento."""
		fonte = sem_docstrings(ast.get_source_segment(_FONTE, _funcao("enfileirar_emissao_em_massa")))

		self.assertIn("except frappe.PermissionError:", fonte)
		self.assertIn("continue", fonte)

	def test_ha_teto_para_o_lote(self):
		"""Para que um clique distraído não encha a fila com milhares de jobs."""
		self.assertGreater(_constante("LIMITE_DO_LOTE"), 0)

		fonte = ast.get_source_segment(_FONTE, _funcao("enfileirar_emissao_em_massa"))

		self.assertIn("LIMITE_DO_LOTE", fonte)


class TestATela(unittest.TestCase):
	def test_o_formulario_enfileira_em_vez_de_emitir_direto(self):
		"""Era isto que travava a tela por até ~25 s."""
		corpo = sem_comentarios_js(_JS_FORM)

		self.assertIn("fila_fiscal.enfileirar_emissao", corpo)
		self.assertNotIn("emissao_nfe.emitir_nfe", corpo)

	def test_o_indicador_de_fila_e_separado_da_situacao_fiscal(self):
		"""Um documento enfileirado não tem situação perante o Fisco: tem tarefa pendente.
		Misturá-los faria "em transmissão" parecer uma situação fiscal."""
		corpo = sem_comentarios_js(_JS_FORM)

		self.assertIn("em_fila", corpo)

		from erpnext_brasil.fiscal.documento.situacao_fiscal import SITUACOES_DO_DOCUMENTO

		self.assertNotIn("Transmissão na fila", SITUACOES_DO_DOCUMENTO)

	def test_sem_botao_de_emitir_enquanto_ha_job(self):
		"""O servidor recusaria o segundo pedido, mas oferecer um botão que não faz nada é
		pior que não oferecer."""
		corpo = sem_comentarios_js(_JS_FORM)

		self.assertLess(corpo.index("em_fila"), corpo.index("Emitir NF-e"))

	def test_a_lista_tem_o_botao_de_massa_e_esta_ligada(self):
		self.assertIn("fila_fiscal.enfileirar_emissao_em_massa", _JS_LISTA)
		self.assertIn("emissao_lote_list.js", _HOOKS)

	def test_a_lista_preserva_configuracao_de_outro_app(self):
		"""Substituir `onload` sem chamar o anterior apagaria o que outro app configurou,
		e o sintoma seria um recurso alheio sumindo sem explicação."""
		corpo = sem_comentarios_js(_JS_LISTA)

		self.assertIn("configuracao_anterior", corpo)

	def test_lote_parcialmente_atendido_nao_e_anunciado_em_verde(self):
		"""Verde diria "tudo certo" sobre um lote em que houve caso não-enfileirado."""
		corpo = sem_comentarios_js(_JS_LISTA)

		self.assertIn("tudo_enfileirado", corpo)
		self.assertIn('"orange"', corpo)


if __name__ == "__main__":
	unittest.main()
