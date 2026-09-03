# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes dos grupos `transp` e `pag`.

O teste mais importante é `TestRegraDoVPag`: o XSD documenta que `vPag` só é dispensado
quando `tPag=90`, e qualquer outra forma sem valor é rejeição. É uma regra condicional
fácil de esquecer porque a maioria dos campos opcionais realmente pode ficar de fora.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.documento.pagamento import (
	FORMAS_PAGAMENTO,
	SEM_PAGAMENTO,
	PagamentoInvalido,
	montar_pag,
)
from erpnext_brasil.fiscal.documento.transporte import (
	MODALIDADES_FRETE,
	TransporteInvalido,
	montar_transp,
)


class TestModalidadeDeFrete(unittest.TestCase):
	def test_todas_as_modalidades_aceitas(self):
		for modalidade in MODALIDADES_FRETE:
			with self.subTest(modalidade=modalidade):
				grupo = montar_transp(modalidade)["transp"]
				self.assertEqual(grupo["modFrete"], modalidade)

	def test_sem_ocorrencia_de_transporte_e_valido(self):
		"""modFrete é obrigatório mesmo quando não há transporte a relatar."""
		grupo = montar_transp("9")["transp"]

		self.assertEqual(grupo["modFrete"], "9")
		self.assertNotIn("transporta", grupo)

	def test_modalidade_invalida(self):
		with self.assertRaises(TransporteInvalido) as ctx:
			montar_transp("5")

		self.assertEqual(ctx.exception.campo, "modalidade_frete")


class TestTransportador(unittest.TestCase):
	def test_cnpj_do_transportador(self):
		grupo = montar_transp("0", transportador_cnpj_cpf="11.222.333/0001-81")["transp"]

		self.assertEqual(grupo["transporta"]["CNPJ"], "11222333000181")

	def test_cpf_do_transportador(self):
		grupo = montar_transp("0", transportador_cnpj_cpf="111.444.777-35")["transp"]

		self.assertIn("CPF", grupo["transporta"])

	def test_documento_invalido(self):
		with self.assertRaises(TransporteInvalido):
			montar_transp("0", transportador_cnpj_cpf="11222333000182")

	def test_endereco_solto_nao_agrupado(self):
		"""O XSD usa xEnder/xMun/UF soltos — diferente de enderEmit/enderDest."""
		grupo = montar_transp(
			"0",
			transportador_cnpj_cpf="11222333000181",
			transportador_endereco={"xEnder": "Rua X", "xMun": "São Paulo", "UF": "SP"},
		)["transp"]

		self.assertEqual(grupo["transporta"]["xEnder"], "Rua X")
		self.assertNotIn("enderTransp", grupo["transporta"])


class TestVolumes(unittest.TestCase):
	def test_volumes_como_lista(self):
		grupo = montar_transp("9", volumes=[{"qVol": "2", "esp": "Caixa"}])["transp"]

		self.assertEqual(len(grupo["vol"]), 1)

	def test_sem_volumes_nao_aparece(self):
		self.assertNotIn("vol", montar_transp("9")["transp"])


class TestFormasDePagamento(unittest.TestCase):
	def test_pix_esta_na_tabela(self):
		self.assertEqual(FORMAS_PAGAMENTO["17"], "Pagamento Instantâneo (PIX)")

	def test_dinheiro(self):
		grupo = montar_pag([{"forma": "01", "valor": Decimal("100.00")}])["pag"]

		self.assertEqual(grupo["detPag"][0]["tPag"], "01")
		self.assertEqual(grupo["detPag"][0]["vPag"], "100.00")

	def test_forma_desconhecida_e_erro(self):
		with self.assertRaises(PagamentoInvalido) as ctx:
			montar_pag([{"forma": "77", "valor": Decimal("1")}])

		self.assertEqual(ctx.exception.campo, "forma")


class TestRegraDoVPag(unittest.TestCase):
	"""O XSD documenta: vPag só é dispensado quando tPag=90."""

	def test_sem_pagamento_dispensa_o_valor(self):
		grupo = montar_pag([{"forma": SEM_PAGAMENTO, "valor": None}])["pag"]

		self.assertNotIn("vPag", grupo["detPag"][0])
		self.assertEqual(grupo["detPag"][0]["tPag"], "90")

	def test_qualquer_outra_forma_sem_valor_e_erro(self):
		for forma in ("01", "03", "17", "99"):
			with self.subTest(forma=forma):
				with self.assertRaises(PagamentoInvalido) as ctx:
					montar_pag([{"forma": forma, "valor": None, "descricao": "x"}])

				self.assertEqual(ctx.exception.campo, "valor")

	def test_pagamento_a_prazo_tambem_exige_valor(self):
		"""Nem "a prazo" nem parcial dispensam vPag — só tPag=90."""
		with self.assertRaises(PagamentoInvalido):
			montar_pag([{"forma": "01", "valor": None, "indicador": "2"}])


class TestFormaOutros(unittest.TestCase):
	def test_99_exige_descricao(self):
		with self.assertRaises(PagamentoInvalido) as ctx:
			montar_pag([{"forma": "99", "valor": Decimal("10.00")}])

		self.assertEqual(ctx.exception.campo, "descricao")

	def test_99_com_descricao_passa(self):
		grupo = montar_pag([{"forma": "99", "valor": Decimal("10.00"), "descricao": "Permuta"}])["pag"]

		self.assertEqual(grupo["detPag"][0]["xPag"], "Permuta")


class TestCartao(unittest.TestCase):
	def test_dados_do_cartao(self):
		grupo = montar_pag(
			[
				{
					"forma": "03",
					"valor": Decimal("100.00"),
					"cartao": {"tipo_integracao": "1", "bandeira": "01", "autorizacao": "123456"},
				}
			]
		)["pag"]

		card = grupo["detPag"][0]["card"]
		self.assertEqual(card["tpIntegra"], "1")
		self.assertEqual(card["tBand"], "01")
		self.assertEqual(card["cAut"], "123456")

	def test_tipo_integracao_padrao(self):
		grupo = montar_pag([{"forma": "03", "valor": Decimal("100.00"), "cartao": {}}])["pag"]

		self.assertEqual(grupo["detPag"][0]["card"]["tpIntegra"], "2")

	def test_cartao_vazio_nao_e_confundido_com_ausente(self):
		"""`{}` significa "cartão com os padrões", não "sem cartão" — dict vazio é falso
		em Python, e `if cartao` o descartaria em silêncio."""
		com_cartao_vazio = montar_pag([{"forma": "03", "valor": Decimal("1"), "cartao": {}}])["pag"]
		sem_cartao = montar_pag([{"forma": "03", "valor": Decimal("1")}])["pag"]

		self.assertIn("card", com_cartao_vazio["detPag"][0])
		self.assertNotIn("card", sem_cartao["detPag"][0])


class TestMultiplosPagamentosETroco(unittest.TestCase):
	def test_varios_pagamentos(self):
		grupo = montar_pag(
			[
				{"forma": "01", "valor": Decimal("50.00")},
				{"forma": "03", "valor": Decimal("50.00")},
			]
		)["pag"]

		self.assertEqual(len(grupo["detPag"]), 2)

	def test_troco(self):
		grupo = montar_pag([{"forma": "01", "valor": Decimal("100.00")}], troco=Decimal("10.00"))["pag"]

		self.assertEqual(grupo["vTroco"], "10.00")

	def test_sem_troco_nao_aparece(self):
		grupo = montar_pag([{"forma": "01", "valor": Decimal("100.00")}])["pag"]

		self.assertNotIn("vTroco", grupo)

	def test_lista_vazia_e_erro(self):
		with self.assertRaises(PagamentoInvalido):
			montar_pag([])


class TestConformidadeDeTags(unittest.TestCase):
	def setUp(self):
		import json
		import pathlib

		manifesto = (
			pathlib.Path(__file__).resolve().parents[1] / "fiscal" / "documento" / "elementos_nfe.json"
		)
		self.elementos = set(json.loads(manifesto.read_text(encoding="utf-8")))

	def _tags(self, no, achadas=None):
		achadas = achadas if achadas is not None else set()

		if isinstance(no, dict):
			for chave, valor in no.items():
				if not chave.startswith("@"):
					achadas.add(chave)

				self._tags(valor, achadas)
		elif isinstance(no, list):
			for item in no:
				self._tags(item, achadas)

		return achadas

	def test_transp_completo(self):
		grupo = montar_transp(
			"0",
			transportador_cnpj_cpf="11222333000181",
			transportador_endereco={"xEnder": "x", "xMun": "y", "UF": "SP"},
			volumes=[{"qVol": "1"}],
		)

		self.assertEqual(self._tags(grupo) - self.elementos, set())

	def test_pag_completo(self):
		grupo = montar_pag(
			[{"forma": "03", "valor": Decimal("10.00"), "cartao": {"bandeira": "01"}}],
			troco=Decimal("1.00"),
		)

		self.assertEqual(self._tags(grupo) - self.elementos, set())


if __name__ == "__main__":
	unittest.main()
