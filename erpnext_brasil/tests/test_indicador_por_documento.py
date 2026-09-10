# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""O mapa de indicador cobre exatamente os DocTypes ligados à validação de classificação.

O perigo está no padrão, não na falta
--------------------------------------------
`validar_classificacao_dos_itens` lê o indicador com
`INDICADOR_POR_DOCUMENTO.get(doc.doctype, "indNFe")`. O padrão é o que torna a omissão
perigosa: um DocType ligado ao hook e **ausente do mapa** não levanta erro — ele é
classificado como **nota modelo 55**.

Para um documento de cupom isso está errado de um jeito específico: a Tabela de
Classificação Tributária tem aplicabilidade por tipo de documento, e a combinação
CST/cClassTrib passaria por uma tabela que não é a dele. O item seria aprovado aqui e
rejeitado pela SEFAZ.

Teste-âncora: `test_todo_doctype_ligado_esta_no_mapa`. Ele compara o mapa com o
**`doc_events` real** do `hooks.py`, importado como dado — não com o texto do arquivo. Texto
casaria com o nome numa docstring; o dicionário não.

Segundo eixo: `test_o_mapa_nao_tem_entrada_inalcancavel`. `POS Invoice` estava no mapa vivo e
a função nunca o recebia. Código inalcançável dentro de uma estrutura viva é pior que
ausência: dá a impressão de que o caso está coberto.

Módulo puro: roda sem bench.
"""

import ast
import unittest
from pathlib import Path

from erpnext_brasil import hooks

RAIZ = Path(__file__).resolve().parent.parent


def _mapa(nome: str) -> dict:
	"""Lê um dicionário de `validacao_fiscal.py` **sem importar o módulo**.

	⚠️ `integracao/validacao_fiscal.py` importa `frappe`, e a suíte pura roda sem bench —
	importá-lo aqui derrubaria o arquivo inteiro no `ImportError`. Mesma técnica que
	`test_prefixo_dos_campos` usa para ler `RENOMES` do patch: `ast.literal_eval` sobre a
	atribuição, que lê o **dado declarado** sem executar nada em volta.

	`hooks.py`, ao contrário, não importa `frappe` — por isso ele é importado de verdade
	logo acima, e a comparação é contra o `doc_events` real.
	"""
	fonte = (RAIZ / "integracao" / "validacao_fiscal.py").read_text(encoding="utf-8")

	for no in ast.parse(fonte).body:
		# ⚠️ Os dois casos: `X = {...}` é `Assign`, e `X: dict[str, str] = {}` é
		# `AnnAssign`. Aceitar só o primeiro fez este leitor não achar o mapa no dia em que
		# ele ficou vazio e ganhou anotação — e o teste morreu no import, sem conferir nada.
		if isinstance(no, ast.AnnAssign):
			alvos = [no.target]
		elif isinstance(no, ast.Assign):
			alvos = no.targets
		else:
			continue

		if any(isinstance(alvo, ast.Name) and alvo.id == nome for alvo in alvos):
			return ast.literal_eval(no.value)

	raise AssertionError(f"{nome} não encontrado em validacao_fiscal.py")


INDICADOR_POR_DOCUMENTO = _mapa("INDICADOR_POR_DOCUMENTO")
INDICADOR_QUANDO_LIGARMOS = _mapa("INDICADOR_QUANDO_LIGARMOS")

VALIDACAO = "erpnext_brasil.integracao.validacao_fiscal.validar_classificacao_dos_itens"

INDICADORES_VALIDOS = frozenset({"indNFe", "indNFCe"})
"""Os dois valores que a Tabela de Classificação Tributária admite.

Fixados aqui e não derivados do mapa: derivar faria o teste concordar com o código por
construção, e um valor inventado passaria nos dois lados.
"""


def _ligados() -> set[str]:
	"""Os DocTypes que o `hooks.py` de fato manda passar pela validação."""
	return {
		doctype
		for doctype, eventos in hooks.doc_events.items()
		if VALIDACAO in (eventos.get("validate") or [])
	}


class TestOIndicadorPorDocumento(unittest.TestCase):
	def test_todo_doctype_ligado_esta_no_mapa(self):
		"""Teste-âncora. Ausente do mapa, o documento cai no padrão `indNFe` sem erro."""
		faltando = sorted(_ligados() - set(INDICADOR_POR_DOCUMENTO))

		self.assertEqual(
			[],
			faltando,
			f"ligados ao hook e fora do mapa: {faltando} — cairiam em indNFe silenciosamente",
		)

	def test_o_mapa_nao_tem_entrada_inalcancavel(self):
		"""Segundo eixo. Entrada para DocType que a função nunca recebe dá impressão falsa
		de cobertura."""
		sobrando = sorted(set(INDICADOR_POR_DOCUMENTO) - _ligados())

		self.assertEqual(
			[],
			sobrando,
			f"no mapa vivo e não ligado: {sobrando} — mova para INDICADOR_QUANDO_LIGARMOS",
		)

	def test_a_intencao_nao_se_mistura_com_o_vivo(self):
		"""`INDICADOR_QUANDO_LIGARMOS` é decisão registrada, não comportamento. Um nome nos
		dois faria alguém achar que já está valendo."""
		self.assertEqual(set(), set(INDICADOR_QUANDO_LIGARMOS) & set(INDICADOR_POR_DOCUMENTO))

	def test_o_que_nao_esta_ligado_realmente_nao_esta(self):
		"""Se `POS Invoice` for ligado um dia, a entrada tem de migrar — senão volta a ser o
		padrão silencioso, e para um documento de cupom o padrão é o valor errado."""
		for doctype in INDICADOR_QUANDO_LIGARMOS:
			with self.subTest(doctype=doctype):
				self.assertNotIn(doctype, _ligados())

	def test_todo_indicador_e_um_dos_dois_valores(self):
		"""`indNFe` ou `indNFCe`. Um terceiro valor não existe na tabela, e passaria como
		filtro que nunca casa — nenhum item seria conferido."""
		for mapa in (INDICADOR_POR_DOCUMENTO, INDICADOR_QUANDO_LIGARMOS):
			for doctype, indicador in mapa.items():
				with self.subTest(doctype=doctype):
					self.assertIn(indicador, INDICADORES_VALIDOS)

	def test_ha_doctypes_ligados(self):
		"""Se `_ligados` parasse de casar, os dois primeiros testes passariam comparando
		conjuntos vazios — e não conferiram nada."""
		self.assertGreaterEqual(len(_ligados()), 4)


if __name__ == "__main__":
	unittest.main()
