# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Costura da montagem do `Lote eSocial`.

A composição que faltava: cada peça do eSocial estava pronta e nada as compunha. Aqui se
confere o que sumiria em silêncio num site — domínio gravado fora do `Select`, campo
inventado, e as decisões de ordem que só aparecem sob carga.

Teste-âncora: `test_o_certificado_e_aberto_uma_vez_para_o_lote`. Abrir o PKCS#12 por evento
decifraria a chave privada uma vez por empregado — numa folha de cem, cem operações caras de
criptografia. O código funciona igual; só fica lento de um jeito que ninguém relaciona à
causa.

Módulo de leitura: roda sem bench.
"""

import ast
import json
import unittest
from pathlib import Path

from erpnext_brasil.tests.ajudantes import sem_comentarios_js, sem_docstrings

RAIZ = Path(__file__).resolve().parent.parent

_FONTE = (RAIZ / "integracao" / "montagem_lote_esocial.py").read_text(encoding="utf-8")
_ARVORE = ast.parse(_FONTE)

_DOCTYPE = json.loads(
	(RAIZ / "registros_fiscais" / "doctype" / "lote_esocial" / "lote_esocial.json").read_text(
		encoding="utf-8"
	)
)


def _funcao(nome: str) -> ast.FunctionDef:
	for no in ast.walk(_ARVORE):
		if isinstance(no, ast.FunctionDef) and no.name == nome:
			return no

	raise AssertionError(f"{nome} não existe em montagem_lote_esocial.py")


def _constante(nome: str):
	for no in _ARVORE.body:
		if isinstance(no, ast.Assign) and any(
			isinstance(alvo, ast.Name) and alvo.id == nome for alvo in no.targets
		):
			return ast.literal_eval(no.value)

	raise AssertionError(f"{nome} não encontrado")


def _opcoes(campo: str) -> set[str]:
	definicao = next(c for c in _DOCTYPE["fields"] if c["fieldname"] == campo)

	return {o for o in definicao["options"].splitlines() if o}


def _campos_gravados() -> set[str]:
	"""As chaves do dicionário passado a `frappe.get_doc`."""
	for no in ast.walk(_funcao("montar_lote_de_holerites")):
		if isinstance(no, ast.Call) and getattr(no.func, "attr", "") == "get_doc":
			return {
				c.value for c in no.args[0].keys if isinstance(c, ast.Constant) and isinstance(c.value, str)
			}

	raise AssertionError("frappe.get_doc não encontrado")


class TestCicloDoCertificado(unittest.TestCase):
	def test_o_certificado_e_aberto_uma_vez_para_o_lote(self):
		"""Teste-âncora: o `with` fica **em volta** do laço, não dentro.

		Dentro, o PKCS#12 seria decifrado uma vez por empregado. O código funcionaria
		igual e ficaria lento de um jeito que ninguém relaciona à causa.
		"""
		funcao = _funcao("montar_lote_de_holerites")
		with_no = next(no for no in ast.walk(funcao) if isinstance(no, ast.With))
		laco = next(no for no in ast.walk(funcao) if isinstance(no, ast.For))

		self.assertLess(with_no.lineno, laco.lineno)

	def test_o_assinador_vem_do_transporte(self):
		"""`TransporteEsocial` expõe `assinador` justamente para isto — criar um segundo
		do mesmo `.pfx` pediria a senha outra vez."""
		fonte = ast.get_source_segment(_FONTE, _funcao("montar_lote_de_holerites"))

		self.assertIn("transporte.assinador", fonte)


class TestDominiosGravados(unittest.TestCase):
	"""Valor fora do `Select` some no save, e o lote fica sem o campo."""

	def test_a_situacao_inicial_existe_no_doctype(self):
		self.assertIn(_constante("SITUACAO_INICIAL"), _opcoes("situacao"))

	def test_os_dois_ambientes_gravados_existem_no_doctype(self):
		fonte = ast.get_source_segment(_FONTE, _funcao("montar_lote_de_holerites"))
		opcoes = _opcoes("ambiente")

		for rotulo in opcoes:
			with self.subTest(rotulo=rotulo):
				self.assertIn(rotulo, fonte)

	def test_todo_campo_gravado_existe_no_doctype(self):
		declarados = {c["fieldname"] for c in _DOCTYPE["fields"]} | {"doctype"}
		gravados = _campos_gravados()

		self.assertTrue(gravados, "nenhum campo lido — o teste ficaria vazio")
		self.assertEqual(set(), gravados - declarados)


class TestUmaEmpresaPorLote(unittest.TestCase):
	def test_holerites_de_empresas_diferentes_sao_recusados(self):
		"""O `ideEmpregador` é um por lote: misturar produziria um envelope que declara
		uma empresa e contém eventos de outra."""
		fonte = ast.get_source_segment(_FONTE, _funcao("_conferir_mesma_empresa"))

		self.assertIn("len(empresas) > 1", fonte)
		self.assertIn("frappe.throw", fonte)

	def test_a_mensagem_lista_as_empresas(self):
		"""Dizer só "empresas diferentes" mandaria o usuário conferir holerite a
		holerite."""
		fonte = ast.get_source_segment(_FONTE, _funcao("_conferir_mesma_empresa"))

		self.assertIn("join(sorted(", fonte)


class TestOLoteNasceEmRascunho(unittest.TestCase):
	def test_montar_nao_transmite(self):
		"""Montar e transmitir são decisões diferentes, e em eSocial o que foi transmitido
		não se desfaz — retificar exige outro evento, com o recibo do primeiro."""
		corpo = sem_docstrings(_FONTE)

		self.assertNotIn("transmitir_lote_esocial", corpo)
		self.assertNotIn("transporte.enviar", corpo)

	def test_o_rotulo_da_situacao_inicial_e_declarado_como_impreciso(self):
		"""O `Select` diz "Enviado" e o lote nasce montado. Trocar o rótulo mudaria dado
		gravado em site existente, então o que se faz é declarar."""
		self.assertIn("mente um pouco", _FONTE)


class TestDeterminismo(unittest.TestCase):
	def test_o_momento_e_injetavel(self):
		"""Mesma razão de `gerar_id_evento` receber o horário: sem isso o `Id` do evento
		muda a cada execução e não há como testar."""
		parametros = [a.arg for a in _funcao("montar_lote_de_holerites").args.args]

		self.assertIn("momento", parametros)

	def test_o_sequencial_do_id_comeca_em_um(self):
		"""`gerar_id_evento` recusa sequencial zero; um `enumerate` sem `start` produziria
		o primeiro evento inválido do lote."""
		fonte = ast.get_source_segment(_FONTE, _funcao("montar_lote_de_holerites"))

		self.assertIn("start=1", fonte)


class TestSuposicoesDeclaradas(unittest.TestCase):
	def test_o_grupo_do_lote_e_declarado_como_nao_confirmado(self):
		"""O significado dos valores de `grupo` não foi confirmado em fonte primária —
		está anotado assim em `esocial_lote.py` desde o início."""
		self.assertEqual(1, _constante("GRUPO_PADRAO"))
		self.assertIn("não foi confirmado", _FONTE)

	def test_a_versao_do_processo_nao_carrega_o_numero_da_versao(self):
		"""Amarrar a versão faria cada `bump` mudar o conteúdo de eventos idênticos."""
		versao = _constante("VERSAO_PROCESSO")

		self.assertNotIn(".", versao)
		self.assertLessEqual(len(versao), 20)

	def test_nao_fatia_o_lote_automaticamente(self):
		"""Fatiar sem pedir produziria vários `Lote eSocial` de um clique, e quem
		transmitisse o primeiro acharia que transmitiu tudo."""
		corpo = sem_docstrings(_FONTE)

		self.assertNotIn("LIMITE_MAXIMO_EVENTOS_POR_LOTE", corpo)


class TestATela(unittest.TestCase):
	def test_o_ponto_de_entrada_e_whitelisted(self):
		alvos = [d.func if isinstance(d, ast.Call) else d for d in _funcao("montar_lote").decorator_list]

		self.assertTrue(any(getattr(a, "attr", "") == "whitelist" for a in alvos))

	def test_a_lista_de_holerites_tem_o_botao(self):
		js = (RAIZ / "public" / "js" / "lote_esocial_list.js").read_text(encoding="utf-8")
		hooks = (RAIZ / "hooks.py").read_text(encoding="utf-8")

		self.assertIn("montagem_lote_esocial.montar_lote", sem_comentarios_js(js))
		self.assertIn("lote_esocial_list.js", hooks)


if __name__ == "__main__":
	unittest.main()
