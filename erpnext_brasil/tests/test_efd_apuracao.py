# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Costura da apuração do Bloco E — o que dá para travar sem bench.

`integracao/efd_apuracao.py` importa `frappe`, então a execução só existe num site real.
O que se pode conferir aqui é a decisão que o módulo toma e que erra em silêncio se
mudar: **de que lado cada documento entra**.

Teste-âncora: `test_a_direcao_vem_do_cfop_e_nao_do_doctype` — devolução de venda é
registrada como compra e ainda assim é crédito; ler o DocType em vez do CFOP colocaria
metade das devoluções do lado errado da apuração, e o total fecharia com um número
plausível e falso.
"""

import ast
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

_FONTE = (RAIZ / "integracao" / "efd_apuracao.py").read_text(encoding="utf-8")


def _constante(nome: str) -> frozenset:
	"""Lê a constante do arquivo por AST — o módulo importa `frappe` e a suíte pura não o
	alcança.

	`ast.literal_eval` não avalia `frozenset({...})`, que é uma **chamada**, não um
	literal. O conjunto de dentro é literal, então avalia-se ele e envolve-se aqui.
	"""
	for no in ast.walk(ast.parse(_FONTE)):
		if not (isinstance(no, ast.Assign) and any(getattr(a, "id", "") == nome for a in no.targets)):
			continue

		valor = no.value

		if isinstance(valor, ast.Call) and getattr(valor.func, "id", "") == "frozenset":
			return frozenset(ast.literal_eval(valor.args[0]))

		return frozenset(ast.literal_eval(valor))

	raise AssertionError(f"{nome} não encontrada")


class TestDirecaoPeloCfop(unittest.TestCase):
	def test_a_direcao_vem_do_cfop_e_nao_do_doctype(self):
		"""O teste-âncora: o módulo lê `br_cfop_sugerido`, não `doc.doctype`, para decidir
		débito ou crédito."""
		self.assertIn("cfop[0] in CFOP_DE_SAIDA", _FONTE)
		self.assertIn("cfop[0] in CFOP_DE_ENTRADA", _FONTE)

	def test_os_dominios_sao_os_do_leiaute(self):
		"""1/2/3 entrada, 5/6/7 saída — como a própria tabela de CFOP se organiza."""
		self.assertEqual(_constante("CFOP_DE_ENTRADA"), frozenset({"1", "2", "3"}))
		self.assertEqual(_constante("CFOP_DE_SAIDA"), frozenset({"5", "6", "7"}))

	def test_entrada_e_saida_nao_se_sobrepoem(self):
		"""Um CFOP em ambos os conjuntos seria contado duas vezes."""
		self.assertEqual(_constante("CFOP_DE_ENTRADA") & _constante("CFOP_DE_SAIDA"), frozenset())

	def test_o_quatro_e_o_oito_ficam_de_fora(self):
		"""`4` não existe na tabela e `8` é de sistemas próprios — nenhum é operação com
		ICMS a apurar, e incluí-los somaria o que não é débito nem crédito."""
		ambos = _constante("CFOP_DE_ENTRADA") | _constante("CFOP_DE_SAIDA")

		self.assertNotIn("4", ambos)
		self.assertNotIn("8", ambos)

	def test_a_mesma_direcao_do_bloco_d(self):
		"""O `D190` aplica a mesma regra; duas leituras diferentes do CFOP produziriam
		blocos que discordam sobre o sentido da mesma operação."""
		from erpnext_brasil.contabil.efd_bloco_d import CFOP_INICIAIS_POR_OPERACAO

		self.assertEqual(CFOP_INICIAIS_POR_OPERACAO["0"], _constante("CFOP_DE_ENTRADA"))
		self.assertEqual(CFOP_INICIAIS_POR_OPERACAO["1"], _constante("CFOP_DE_SAIDA"))


class TestEscopoDeclarado(unittest.TestCase):
	"""O que o módulo se recusa a fazer, e que precisa continuar recusando."""

	def test_documento_cancelado_nao_entra_na_apuracao(self):
		"""Ele existe no Bloco C com COD_SIT 02 para a numeração fechar, mas não gera
		imposto — somá-lo cobraria de operação que não aconteceu."""
		self.assertIn('"docstatus": 1', _FONTE)

	def test_nao_gera_ajuste_e111(self):
		"""O código do ajuste vem da tabela da UF, não modelada — inventar um declararia
		natureza que ninguém escolheu."""
		self.assertNotIn("montar_e111", _FONTE)

	def test_o_saldo_credor_anterior_fica_declarado(self):
		"""Sai zerado, o que **aumenta** o imposto a recolher: erra para o lado seguro,
		mas erra, e por isso está escrito."""
		self.assertIn("saldo credor de período anterior", _FONTE.lower())

	def test_o_bloco_e_nunca_e_vazio(self):
		"""`montar_e001` não recebe parâmetro; o bloco sempre tem os quatro registros."""
		self.assertIn("montar_e001()", _FONTE)


if __name__ == "__main__":
	unittest.main()
