# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste diferencial contra a implementação de referência da Receita Federal.

Origem
------
A Receita publica, em documentos-tecnicos/cnpj, um pacote com implementações de
referência do cálculo do dígito verificador do CNPJ alfanumérico (Java, Python e
TypeScript). `_dv_referencia` abaixo é a transcrição fiel da versão Python (`dv.py`),
inclusive na forma como ela monta os pesos: repete `range(2, 10)`, trunca no tamanho
da base e **inverte**.

Por que este teste existe
-------------------------
Os demais testes validam a implementação contra ela mesma — provam consistência
aritmética, não aderência à norma. Este aqui compara com a fonte oficial sobre milhares
de bases geradas, o que é a diferença entre "meu código é coerente" e "meu código
concorda com a Receita".

A geração é semeada (`Random(20260701)`) para que uma falha seja sempre reproduzível.
"""

import random
import string
import unittest
from math import ceil

from erpnext_brasil.fiscal.validators import ValidacaoFiscalError, validar_cnpj

ALFABETO = string.digits + string.ascii_uppercase


def _dv_referencia(base: str) -> int:
	"""Transcrição fiel de `DigitoVerificador.calcula` da referência oficial."""
	pesos: list[int] = []

	for _ in range(ceil(len(base) / 8)):
		pesos.extend(range(2, 10))

	pesos = pesos[: len(base)]
	pesos.reverse()

	soma = sum((ord(c) - 48) * p for c, p in zip(base, pesos, strict=True))
	resto = soma % 11

	return 0 if resto < 2 else 11 - resto


def _cnpj_referencia(base: str) -> str:
	"""Monta o CNPJ completo de 14 posições pelo caminho oficial."""
	dv1 = _dv_referencia(base)
	dv2 = _dv_referencia(base + str(dv1))

	return f"{base}{dv1}{dv2}"


class TestExemploOficial(unittest.TestCase):
	def test_exemplo_do_manual_da_receita(self):
		# O README oficial documenta: 12.ABC.345/01DE -> DV 35.
		self.assertEqual(_cnpj_referencia("12ABC34501DE"), "12ABC34501DE35")
		self.assertEqual(validar_cnpj("12.ABC.345/01DE-35"), "12ABC34501DE35")

	def test_exemplo_invalido_do_manual(self):
		# O mesmo README mostra ...-36 como inválido.
		with self.assertRaises(ValidacaoFiscalError):
			validar_cnpj("12ABC34501DE36")


class TestConcordanciaComAReferencia(unittest.TestCase):
	"""Compara as duas implementações sobre uma amostra ampla e semeada."""

	AMOSTRA = 3000

	def _bases(self):
		aleatorio = random.Random(20260701)

		for _ in range(self.AMOSTRA):
			yield "".join(aleatorio.choice(ALFABETO) for _ in range(12))

	def test_aceita_todo_cnpj_que_a_referencia_gera(self):
		for base in self._bases():
			cnpj = _cnpj_referencia(base)

			with self.subTest(cnpj=cnpj):
				self.assertEqual(validar_cnpj(cnpj), cnpj)

	def test_rejeita_todo_dv_que_a_referencia_nao_produz(self):
		for base in self._bases():
			correto = _cnpj_referencia(base)
			dv_correto = correto[12:]

			# Um único DV errado por base já basta e mantém o teste rápido.
			dv_errado = f"{(int(dv_correto) + 1) % 100:02d}"

			if dv_errado == dv_correto:
				continue

			with self.subTest(base=base, dv=dv_errado):
				with self.assertRaises(ValidacaoFiscalError):
					validar_cnpj(base + dv_errado)

	def test_cnpjs_numericos_legados_tambem_concordam(self):
		"""Empresas antigas não foram recadastradas: o mesmo código precisa aceitá-las."""
		aleatorio = random.Random(19980101)

		for _ in range(500):
			base = "".join(aleatorio.choice(string.digits) for _ in range(12))

			if len(set(base)) == 1:
				continue  # divergência conhecida, coberta em TestDivergenciaConhecida

			cnpj = _cnpj_referencia(base)

			with self.subTest(cnpj=cnpj):
				self.assertEqual(validar_cnpj(cnpj), cnpj)


class TestDivergenciaConhecida(unittest.TestCase):
	"""A única divergência intencional em relação à referência oficial.

	A referência é um calculador de DV puro e valida "00000000000000". Aqui a base
	numérica toda igual é recusada, porque é valor-lixo consagrado e sujaria o cadastro
	fiscal. A mesma recusa **não** se aplica a base alfanumérica, que não tem essa
	convenção contra si.
	"""

	def test_referencia_aceita_todos_zeros_mas_nos_recusamos(self):
		self.assertEqual(_cnpj_referencia("000000000000"), "00000000000000")

		with self.assertRaises(ValidacaoFiscalError):
			validar_cnpj("00000000000000")

	def test_base_numerica_repetida_e_recusada(self):
		for digito in string.digits:
			base = digito * 12

			with self.subTest(base=base):
				with self.assertRaises(ValidacaoFiscalError):
					validar_cnpj(_cnpj_referencia(base))

	def test_base_alfanumerica_repetida_e_aceita(self):
		# Nenhuma norma torna "AAAAAAAAAAAA" inválido; recusá-la travaria um
		# cadastro legítimo, então acompanhamos a referência aqui.
		for letra in "ABZ":
			cnpj = _cnpj_referencia(letra * 12)

			with self.subTest(cnpj=cnpj):
				self.assertEqual(validar_cnpj(cnpj), cnpj)


if __name__ == "__main__":
	unittest.main()
