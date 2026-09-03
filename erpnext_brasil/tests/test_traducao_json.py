# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da tradução da árvore do documento para o formato JSON.

O teste-âncora é `test_atributo_de_negocio_vira_chave_comum`: reproduz o exemplo oficial
da especificação da ACBr API, em que `xCampo` (atributo em XML) aparece no JSON como
chave comum sem `@`. É a evidência que motivou o módulo, não um caso inventado.
"""

import unittest

from erpnext_brasil.fiscal.documento.traducao_json import (
	ATRIBUTOS_DE_INFRAESTRUTURA,
	para_json,
)


class TestConversaoBasica(unittest.TestCase):
	def test_atributo_de_negocio_vira_chave_comum(self):
		"""`@xCampo` não é infraestrutura: converte, não remove."""
		self.assertEqual(para_json({"@xCampo": "Pedido"}), {"xCampo": "Pedido"})

	def test_elemento_comum_nao_muda(self):
		self.assertEqual(para_json({"xTexto": "abc"}), {"xTexto": "abc"})

	def test_recursivo_em_dicionario_aninhado(self):
		arvore = {"a": {"@b": "1", "c": "2"}}

		self.assertEqual(para_json(arvore), {"a": {"b": "1", "c": "2"}})

	def test_recursivo_em_lista(self):
		arvore = {"obsCont": [{"@xCampo": "Pedido", "xTexto": "1"}, {"@xCampo": "Vendedor", "xTexto": "x"}]}

		self.assertEqual(
			para_json(arvore),
			{"obsCont": [{"xCampo": "Pedido", "xTexto": "1"}, {"xCampo": "Vendedor", "xTexto": "x"}]},
		)

	def test_valor_escalar_nao_e_alterado(self):
		self.assertEqual(para_json("texto"), "texto")
		self.assertEqual(para_json(42), 42)
		self.assertIsNone(para_json(None))


class TestExemploOficialDaAcbrApi(unittest.TestCase):
	"""Reproduz o exemplo da especificação: xCampo é atributo em XML, chave comum em JSON."""

	def test_atributo_de_negocio_vira_chave_comum(self):
		arvore_xml = {"obsCont": [{"@xCampo": "xCampo", "xTexto": "xTexto"}]}

		self.assertEqual(para_json(arvore_xml), {"obsCont": [{"xCampo": "xCampo", "xTexto": "xTexto"}]})


class TestAtributosDeInfraestrutura(unittest.TestCase):
	def test_removidos_por_padrao(self):
		arvore = {"infNFe": {"@versao": "4.00", "@Id": "NFe123", "ide": {}}}

		resultado = para_json(arvore)

		self.assertNotIn("versao", resultado["infNFe"])
		self.assertNotIn("Id", resultado["infNFe"])
		self.assertIn("ide", resultado["infNFe"])

	def test_lista_de_atributos_de_infraestrutura(self):
		self.assertEqual(set(ATRIBUTOS_DE_INFRAESTRUTURA), {"@versao", "@Id", "@xmlns", "@nItem"})

	def test_preservados_quando_desligado(self):
		arvore = {"infNFe": {"@versao": "4.00"}}

		resultado = para_json(arvore, remover_atributos_infraestrutura=False)

		self.assertEqual(resultado["infNFe"]["versao"], "4.00")

	def test_atributo_de_negocio_nunca_e_removido(self):
		"""Só a lista de infraestrutura é descartada; xCampo, por exemplo, sempre fica."""
		arvore = {"obsCont": {"@xCampo": "Pedido", "@versao": "4.00"}}

		resultado = para_json(arvore)

		self.assertIn("xCampo", resultado["obsCont"])
		self.assertNotIn("versao", resultado["obsCont"])


class TestNaoMutaAOriginal(unittest.TestCase):
	def test_arvore_de_entrada_permanece_intacta(self):
		original = {"@Id": "NFe123", "det": [{"@nItem": "1"}]}
		copia = {"@Id": "NFe123", "det": [{"@nItem": "1"}]}

		para_json(original)

		self.assertEqual(original, copia)


if __name__ == "__main__":
	unittest.main()
