# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de costura entre `setup/custom_fields.py` e os módulos puros do EFD.

O que estes testes protegem não é uma função: é a **consistência entre a tela e o
arquivo**. Um campo Select que ofereça um valor que a montagem do registro recusa
produz um erro que só aparece no fim — o usuário escolhe na tela, salva, e o arquivo
falha na geração (ou pior, é recusado pelo Fisco). Duas listas escritas separadamente
divergem na primeira alteração; estes testes garantem que continuam sendo a mesma.

`custom_fields.py` não importa `frappe` (só devolve dicionários de definição), por isso
dá para testá-lo na suíte pura.
"""

import unittest

from erpnext_brasil.contabil.efd_bloco_0 import TIPOS_ITEM, Item
from erpnext_brasil.setup.custom_fields import TIPOS_ITEM_EFD, get_custom_fields


def _campo(doctype: str, fieldname: str) -> dict:
	campos = get_custom_fields()[doctype]

	return next(campo for campo in campos if campo["fieldname"] == fieldname)


class TestTipoItemNaoDiverge(unittest.TestCase):
	def test_o_select_oferece_exatamente_os_codigos_que_o_registro_aceita(self):
		"""A costura que importa: tela e arquivo saem da mesma tabela."""
		codigos_do_select = {
			linha.split(" - ", 1)[0] for linha in TIPOS_ITEM_EFD.split("\n") if linha
		}

		self.assertEqual(codigos_do_select, set(TIPOS_ITEM))

	def test_todo_valor_do_select_e_aceito_pelo_registro_0200(self):
		"""Prova de verdade, não só comparação de listas: cada opção da tela é usada
		para construir um `Item` real."""
		for linha in TIPOS_ITEM_EFD.split("\n"):
			if not linha:
				continue

			codigo = linha.split(" - ", 1)[0]

			with self.subTest(opcao=linha):
				Item(codigo="P1", descricao="P", unidade_inventario="UN", tipo=codigo)

	def test_o_campo_do_item_usa_a_lista_derivada(self):
		campo = _campo("Item", "br_efd_tipo_item")

		self.assertEqual(campo["options"], TIPOS_ITEM_EFD)
		self.assertEqual(campo["fieldtype"], "Select")


class TestCamposDaCompanyParaORegistro0000(unittest.TestCase):
	def test_perfil_oferece_os_tres_valores_do_layout(self):
		campo = _campo("Company", "br_efd_perfil")

		self.assertEqual(set(campo["options"].split("\n")) - {""}, {"A", "B", "C"})

	def test_atividade_tem_as_duas_opcoes_do_layout(self):
		campo = _campo("Company", "br_efd_atividade")
		opcoes = set(campo["options"].split("\n")) - {""}

		self.assertEqual(len(opcoes), 2)
		self.assertTrue(any(o.startswith("Industrial") for o in opcoes))

	def test_company_ganhou_suframa(self):
		"""Achado real: Customer/Supplier já tinham; a Company não."""
		campo = _campo("Company", "suframa")

		self.assertEqual(campo["fieldtype"], "Data")

	def test_versao_do_leiaute_e_configuravel(self):
		"""Muda com o tempo — constante no código envelheceria em silêncio."""
		campo = _campo("Company", "br_efd_versao_leiaute")

		self.assertEqual(campo["fieldtype"], "Data")


if __name__ == "__main__":
	unittest.main()
