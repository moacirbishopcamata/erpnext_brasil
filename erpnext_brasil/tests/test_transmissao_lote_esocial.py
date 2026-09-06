# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Costura da transmissão do `Lote eSocial` — o maior órfão da varredura de 2026-09-06.

A cadeia do eSocial estava inteira e **nada a acionava**: `ContextoEsocial`, que o
transporte exige, só era construído em arquivo de teste. `TransporteEsocial` é o elo que
faltava, e esta suíte trava o que sumiria em silêncio num site.

Teste-âncora: `test_o_contexto_esocial_e_construido_em_producao`. Enquanto o único
`ContextoEsocial(...)` do repositório estivesse num teste, todo o resto era decoração.

Módulo de leitura: roda sem bench.
"""

import ast
import json
import unittest
from pathlib import Path

from erpnext_brasil.tests.ajudantes import sem_docstrings

RAIZ = Path(__file__).resolve().parent.parent

_TRANSMISSAO = (RAIZ / "integracao" / "transmissao_lote_esocial.py").read_text(encoding="utf-8")
_TRANSPORTE = (RAIZ / "integracao" / "transporte_esocial.py").read_text(encoding="utf-8")
_ARVORE = ast.parse(_TRANSMISSAO)

_DOCTYPE = json.loads(
	(RAIZ / "registros_fiscais" / "doctype" / "lote_esocial" / "lote_esocial.json").read_text(
		encoding="utf-8"
	)
)
_FILHO = json.loads(
	(
		RAIZ / "registros_fiscais" / "doctype" / "evento_do_lote_esocial" / "evento_do_lote_esocial.json"
	).read_text(encoding="utf-8")
)


def _funcao(nome: str, fonte: str = _TRANSMISSAO) -> ast.FunctionDef:
	for no in ast.walk(ast.parse(fonte)):
		if isinstance(no, ast.FunctionDef) and no.name == nome:
			return no

	raise AssertionError(f"{nome} não encontrado")


def _opcoes(campo: str) -> set[str]:
	definicao = next(c for c in _DOCTYPE["fields"] if c["fieldname"] == campo)

	return {o for o in definicao["options"].splitlines() if o}


def _campos(definicao: dict) -> set[str]:
	return {c["fieldname"] for c in definicao["fields"]}


class TestOElo(unittest.TestCase):
	def test_o_contexto_esocial_e_construido_em_producao(self):
		"""Teste-âncora: enquanto o único `ContextoEsocial(...)` estivesse em teste, o
		eSocial inteiro era código inalcançável."""
		self.assertIn("ContextoEsocial(", _TRANSPORTE)

	def test_o_transporte_e_o_unico_que_monta_o_contexto(self):
		"""Mesma regra do `ContextoSefaz`: montá-lo fora duplicaria o ciclo de vida dos
		PEM, e é chave privada em disco."""
		self.assertNotIn("ContextoEsocial(", _TRANSMISSAO)

	def test_os_dois_metodos_sao_whitelisted(self):
		for nome in ("transmitir_lote_esocial", "consultar_lote_esocial"):
			with self.subTest(metodo=nome):
				alvos = [d.func if isinstance(d, ast.Call) else d for d in _funcao(nome).decorator_list]

				self.assertTrue(any(getattr(a, "attr", "") == "whitelist" for a in alvos))


class TestOsDoisNiveisDeResposta(unittest.TestCase):
	"""O eSocial responde no nível do lote **e** no de cada evento; confundi-los diria
	que deu tudo certo quando metade da folha foi recusada."""

	def test_cada_evento_vira_uma_linha_da_tabela_filha(self):
		fonte = ast.get_source_segment(_TRANSMISSAO, _funcao("_gravar_retorno"))

		self.assertIn("for evento in resultado.eventos", fonte)
		self.assertIn("lote.append(", fonte)

	def test_todo_campo_gravado_no_filho_existe_no_doctype(self):
		"""Campo inventado numa linha filha some no save, sem erro."""
		fonte = ast.get_source_segment(_TRANSMISSAO, _funcao("_gravar_retorno"))
		gravados = set()

		for no in ast.walk(ast.parse(fonte.strip())):
			if isinstance(no, ast.Dict):
				gravados.update(
					c.value for c in no.keys if isinstance(c, ast.Constant) and isinstance(c.value, str)
				)

		self.assertTrue(gravados, "nenhum campo lido — o teste ficaria vazio")
		self.assertEqual(set(), gravados - _campos(_FILHO))

	def test_as_linhas_antigas_sao_substituidas_e_nao_acumuladas(self):
		"""Uma reconsulta traz o retorno atualizado; acumular versões faria a tabela
		crescer com histórico que ninguém pediu."""
		fonte = ast.get_source_segment(_TRANSMISSAO, _funcao("_gravar_retorno"))

		self.assertIn('lote.set("eventos", [])', fonte)

	def test_usa_save_e_nao_db_set(self):
		"""Tabela filha não persiste por `db_set`; gravar cabeçalho por um caminho e
		filhas por outro os deixaria fora de sincronia."""
		fonte = sem_docstrings(ast.get_source_segment(_TRANSMISSAO, _funcao("_gravar_retorno")))

		self.assertIn("lote.save(", fonte)
		self.assertNotIn("db_set", fonte)


class TestDominios(unittest.TestCase):
	def test_as_situacoes_gravadas_existem_no_select(self):
		"""Valor fora do `Select` some no save, e o lote fica sem situação."""
		opcoes = _opcoes("situacao")

		for situacao in ("Processado", "Rejeitado", "Em processamento"):
			with self.subTest(situacao=situacao):
				self.assertIn(situacao, opcoes)

	def test_todo_campo_gravado_no_lote_existe_no_doctype(self):
		fonte = ast.get_source_segment(_TRANSMISSAO, _funcao("_gravar_retorno"))
		gravados = {
			no.targets[0].attr
			for no in ast.walk(ast.parse(fonte.strip()))
			if isinstance(no, ast.Assign)
			and isinstance(no.targets[0], ast.Attribute)
			and isinstance(no.targets[0].value, ast.Name)
			and no.targets[0].value.id == "lote"
		}

		self.assertTrue(gravados)
		self.assertEqual(set(), gravados - _campos(_DOCTYPE))


class TestOrdemDosEfeitos(unittest.TestCase):
	def test_o_retorno_e_gravado_antes_do_throw(self):
		"""Rejeição do eSocial que não deixa rastro obriga o usuário a adivinhar — mesma
		disciplina de `emissao_nfe` e `eventos_nfe`."""
		fonte = ast.get_source_segment(_TRANSMISSAO, _funcao("transmitir_lote_esocial"))

		self.assertLess(fonte.index("_gravar_retorno"), fonte.rindex("frappe.throw"))

	def test_a_permissao_e_conferida_antes_de_transmitir(self):
		fonte = ast.get_source_segment(_TRANSMISSAO, _funcao("transmitir_lote_esocial"))

		self.assertLess(fonte.index("check_permission"), fonte.index("TransporteEsocial"))

	def test_lote_sem_xml_falha_antes_de_abrir_o_certificado(self):
		"""Transmitir vazio consumiria uma tentativa e voltaria com erro que não diz o
		que houve."""
		fonte = ast.get_source_segment(_TRANSMISSAO, _funcao("transmitir_lote_esocial"))

		self.assertLess(fonte.index("não tem XML montado"), fonte.index("carregar_certificado"))


class TestReconsulta(unittest.TestCase):
	"""Reenviar um lote em processamento **duplicaria os eventos**."""

	def test_a_consulta_nao_reenvia(self):
		fonte = ast.get_source_segment(_TRANSMISSAO, _funcao("consultar_lote_esocial"))

		self.assertIn("transporte.consultar", fonte)
		self.assertNotIn("transporte.enviar", fonte)

	def test_a_consulta_exige_protocolo(self):
		fonte = ast.get_source_segment(_TRANSMISSAO, _funcao("consultar_lote_esocial"))

		self.assertIn("protocolo_envio", fonte)
		self.assertIn("frappe.throw", fonte)

	def test_a_consulta_conta_as_tentativas(self):
		"""O campo existe no DocType e serviria de nada se ninguém o incrementasse."""
		fonte = ast.get_source_segment(_TRANSMISSAO, _funcao("consultar_lote_esocial"))

		self.assertIn("tentativas_de_consulta", fonte)
		self.assertIn("tentativas_de_consulta", _campos(_DOCTYPE))


class TestCicloDeVidaDoCertificado(unittest.TestCase):
	def test_o_transporte_e_usado_como_context_manager(self):
		"""Sem `with`, os PEM ficam no disco temporário até o processo morrer."""
		for nome in ("transmitir_lote_esocial", "consultar_lote_esocial"):
			with self.subTest(metodo=nome):
				usos = [no for no in ast.walk(_funcao(nome)) if isinstance(no, ast.With)]

				self.assertTrue(usos)

	def test_o_tls_e_o_extraido_e_nao_uma_copia(self):
		"""Copiar o ciclo de vida de uma chave privada em disco é o que a extração de
		`tls_certificado` existe para evitar."""
		self.assertIn("from erpnext_brasil.integracao.tls_certificado import ArquivosTls", _TRANSPORTE)
		self.assertNotIn("tempfile", sem_docstrings(_TRANSPORTE))

	def test_o_transporte_nao_herda_do_da_sefaz(self):
		"""Herdar para reusar código, e não comportamento, é o antipadrão que a
		composição resolve: muda o contexto (`ContextoEsocial` não tem UF), a assinatura
		(SHA-256 contra SHA-1), o protocolo (lote com consulta obrigatória contra recibo)
		e os endpoints.

		A conferência é das **bases da classe**, por AST. A primeira versão deste teste
		procurava a string `"TransporteSefaz"` no fonte e reprovava por causa de um
		comentário que explica justamente por que os dois lêem o `.pfx` duas vezes —
		asserção textual mede o que se escreve, não o que se faz.
		"""
		classes = [no for no in ast.parse(_TRANSPORTE).body if isinstance(no, ast.ClassDef)]

		self.assertEqual(["TransporteEsocial"], [c.name for c in classes])
		self.assertEqual([], classes[0].bases, "TransporteEsocial não deve herdar de nada")


if __name__ == "__main__":
	unittest.main()
