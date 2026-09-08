# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Código (número) para máquinas, mensagem para usuários.

Teste-âncora: `test_nenhum_codigo_invade_a_faixa_do_cstat`. O `cStat` da SEFAZ tem três
dígitos e significado normativo — `100` autorizado, `137` nenhum documento localizado, `656`
consumo indevido. Um código nosso na mesma faixa mandaria quem investiga procurar na tabela
do Fisco e concluir que a SEFAZ recusou algo que ela nunca viu.

Segundo eixo: `test_nao_ha_codigo_repetido`. Dois nomes com o mesmo número é o defeito mais
caro possível num registro de códigos, porque quem trata a condição antiga passa a tratar a
nova sem saber — e o sintoma aparece longe da causa.

Módulo puro: roda sem bench.
"""

import ast
import unittest
from pathlib import Path

from erpnext_brasil.fiscal import codigos_de_erro
from erpnext_brasil.fiscal.codigos_de_erro import PRIMEIRO_CODIGO, TODOS, formatar
from erpnext_brasil.tests.ajudantes import sem_docstrings

RAIZ = Path(__file__).resolve().parent.parent

GUARDAS_COM_CODIGO = (
	"chave_acesso_documento",
	"consumo_indevido",
	"documento",
	"party",
	"perda_estoque",
	"validacao_fiscal",
)
"""Os módulos de `integracao/` cujas recusas já foram convertidas.

⚠️ Lista explícita, e não "todos os módulos": a conversão é incremental, e um teste que
exigisse código em todo `frappe.throw` do app reprovaria as 50+ recusas antigas de uma vez.
O que se trava aqui é que **o que já foi convertido não regride** — e cada módulo novo entra
nesta lista quando for convertido.
"""


class TestORegistroDeCodigos(unittest.TestCase):
	def test_nenhum_codigo_invade_a_faixa_do_cstat(self):
		"""Teste-âncora. Ver a explicação na docstring do módulo."""
		for codigo in TODOS:
			with self.subTest(codigo=codigo):
				self.assertGreaterEqual(codigo, PRIMEIRO_CODIGO)

	def test_o_piso_esta_acima_dos_tres_digitos(self):
		"""999 é o maior `cStat` possível; o piso precisa passar disso."""
		self.assertGreater(PRIMEIRO_CODIGO, 999)

	def test_nao_ha_codigo_repetido(self):
		"""Segundo eixo. `TODOS` é conjunto de propósito — duas constantes com o mesmo
		número colapsariam nele, e é a contagem que denuncia."""
		declarados = [
			no.value.value
			for no in ast.parse((RAIZ / "fiscal" / "codigos_de_erro.py").read_text(encoding="utf-8")).body
			if isinstance(no, ast.Assign)
			and isinstance(no.value, ast.Constant)
			and isinstance(no.value.value, int)
			and getattr(no.targets[0], "id", "").isupper()
			and getattr(no.targets[0], "id", "") != "PRIMEIRO_CODIGO"
		]

		self.assertEqual(len(declarados), len(set(declarados)), "há código repetido")
		self.assertEqual(set(declarados), TODOS, "TODOS não bate com as constantes declaradas")

	def test_todo_codigo_esta_em_todos(self):
		"""Código fora de `TODOS` escapa das conferências acima — inclusive da de faixa."""
		publicados = {
			valor
			for nome, valor in vars(codigos_de_erro).items()
			if nome.isupper() and isinstance(valor, int) and nome != "PRIMEIRO_CODIGO"
		}

		self.assertEqual(publicados, TODOS)


class TestAFormatacao(unittest.TestCase):
	def test_o_codigo_vem_primeiro(self):
		"""Fica visível numa captura de tela cortada, e quem procura por prefixo acha sem
		varrer o texto inteiro."""
		self.assertTrue(formatar(1001, "qualquer coisa").startswith("[1001] "))

	def test_a_mensagem_sobrevive_inteira(self):
		"""O número **não** substitui a explicação: quem lê a tela precisa saber o que
		fazer, e um número não diz isso."""
		texto = "Deixe o tipo de perda em branco."

		self.assertIn(texto, formatar(1002, texto))


class TestAsGuardasConvertidas(unittest.TestCase):
	def test_toda_recusa_convertida_leva_codigo(self):
		"""`frappe.throw` sem `formatar` é mensagem sem código — o estado anterior."""
		for modulo in GUARDAS_COM_CODIGO:
			fonte = sem_docstrings((RAIZ / "integracao" / f"{modulo}.py").read_text(encoding="utf-8"))

			with self.subTest(modulo=modulo):
				self.assertEqual(
					fonte.count("frappe.throw("),
					fonte.count("formatar("),
					f"{modulo}: há recusa sem código",
				)

	def test_os_codigos_usados_estao_registrados(self):
		"""Número solto no `throw` não é código: é literal que ninguém sabe de onde veio."""
		for modulo in GUARDAS_COM_CODIGO:
			arvore = ast.parse((RAIZ / "integracao" / f"{modulo}.py").read_text(encoding="utf-8"))
			importados = {
				alias.name
				for no in ast.walk(arvore)
				if isinstance(no, ast.ImportFrom) and no.module == "erpnext_brasil.fiscal.codigos_de_erro"
				for alias in no.names
			}

			with self.subTest(modulo=modulo):
				self.assertIn("formatar", importados)
				self.assertTrue(
					importados - {"formatar"}, f"{modulo}: usa formatar sem importar código nenhum"
				)


if __name__ == "__main__":
	unittest.main()
