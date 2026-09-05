# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/natureza_operacao.py` e do limite de 60 caracteres do `natOp`.

Teste-âncora: `test_natureza_longa_demais_e_recusada_na_montagem` — antes da varredura de
2026-09-04 uma natureza de 200 caracteres era montada, assinada e transmitida, para ser
recusada pela SEFAZ no fim da cadeia.
"""

import unittest

from erpnext_brasil.fiscal.cfop import (
	FINALIDADE_COMERCIALIZACAO,
	FINALIDADE_INDUSTRIALIZACAO,
	cfop_compra,
	cfop_devolucao_compra,
	cfop_devolucao_venda,
	cfop_remessa_para_industrializacao,
	cfop_retorno_de_industrializacao,
	cfop_venda,
)
from erpnext_brasil.fiscal.natureza_operacao import (
	NATUREZAS_PADRAO,
	TAMANHO_MAXIMO,
	NaturezaInvalida,
	natureza_do_cfop,
	validar_natureza,
)


class TestValidacao(unittest.TestCase):
	def test_o_limite_e_o_do_xsd_oficial(self):
		"""60, lido em `leiauteNFe_v4.00.xsd` e confirmado em `cteTiposBasico_v4.00.xsd`."""
		self.assertEqual(TAMANHO_MAXIMO, 60)

	def test_natureza_no_limite_passa(self):
		self.assertEqual(len(validar_natureza("A" * 60)), 60)

	def test_natureza_acima_do_limite_e_erro(self):
		with self.assertRaises(NaturezaInvalida):
			validar_natureza("A" * 61)

	def test_vazia_e_erro(self):
		with self.assertRaises(NaturezaInvalida):
			validar_natureza("   ")

	def test_none_e_erro(self):
		with self.assertRaises(NaturezaInvalida):
			validar_natureza(None)

	def test_espaco_em_branco_e_colapsado_antes_de_medir(self):
		"""A SEFAZ mede o texto que recebe, não o que o usuário digitou."""
		self.assertEqual(validar_natureza("  Venda   de \n mercadoria  "), "Venda de mercadoria")

	def test_o_colapso_pode_salvar_uma_natureza_no_limite(self):
		"""62 caracteres digitados viram 60 depois do colapso — e passam."""
		com_espacos = "A" * 29 + "   " + "B" * 30

		self.assertEqual(len(com_espacos), 62)
		self.assertEqual(len(validar_natureza(com_espacos)), 60)


class TestNaturezasPadrao(unittest.TestCase):
	def test_toda_natureza_padrao_cabe_no_limite(self):
		"""Sugestão que não cabe no campo é pior que sugestão nenhuma."""
		for cfop, texto in NATUREZAS_PADRAO.items():
			with self.subTest(cfop=cfop):
				self.assertLessEqual(len(texto), TAMANHO_MAXIMO)
				validar_natureza(texto)

	def test_cobre_exatamente_os_cfops_que_o_projeto_determina(self):
		"""Se um módulo cobrir código que o outro não cobre, os dois divergem sobre a
		mesma operação."""
		determinados = set()

		for mesmo_estado in (True, False):
			determinados.add(cfop_compra(mesmo_estado, FINALIDADE_INDUSTRIALIZACAO))
			determinados.add(cfop_compra(mesmo_estado, FINALIDADE_COMERCIALIZACAO))
			determinados.add(cfop_venda(mesmo_estado, producao_propria=True))
			determinados.add(cfop_venda(mesmo_estado, producao_propria=False))
			determinados.add(cfop_devolucao_venda(mesmo_estado, producao_propria=True))
			determinados.add(cfop_devolucao_venda(mesmo_estado, producao_propria=False))
			determinados.add(cfop_devolucao_compra(mesmo_estado, FINALIDADE_INDUSTRIALIZACAO))
			determinados.add(cfop_devolucao_compra(mesmo_estado, FINALIDADE_COMERCIALIZACAO))
			determinados.add(cfop_remessa_para_industrializacao(mesmo_estado))
			determinados.add(cfop_retorno_de_industrializacao(mesmo_estado))

		sem_natureza = sorted(determinados - set(NATUREZAS_PADRAO))

		self.assertEqual(sem_natureza, [], f"CFOPs determinados sem natureza: {sem_natureza}")

	def test_o_cfop_de_venda_tem_a_natureza_de_venda(self):
		self.assertEqual(natureza_do_cfop("5102"), "Venda de mercadoria adquirida de terceiros")
		self.assertEqual(natureza_do_cfop("6102"), natureza_do_cfop("5102"))

	def test_dentro_e_fora_do_estado_descrevem_a_mesma_operacao(self):
		"""O primeiro dígito muda o âmbito, não a natureza."""
		for interno, interestadual in (("1101", "2101"), ("5201", "6201"), ("5901", "6901")):
			with self.subTest(par=(interno, interestadual)):
				self.assertEqual(natureza_do_cfop(interno), natureza_do_cfop(interestadual))

	def test_cfop_desconhecido_devolve_vazio_e_nao_erro(self):
		"""Não ter sugestão é normal: a tabela tem centenas de códigos."""
		self.assertEqual(natureza_do_cfop("5949"), "")
		self.assertEqual(natureza_do_cfop(""), "")
		self.assertEqual(natureza_do_cfop(None), "")

	def test_as_naturezas_sao_ascii(self):
		"""Escolha conservadora: campo livre que atravessa assinatura e transmissão."""
		for cfop, texto in NATUREZAS_PADRAO.items():
			with self.subTest(cfop=cfop):
				self.assertTrue(texto.isascii())


class TestMontagemDaNFe(unittest.TestCase):
	def _identificacao(self, natureza):
		from datetime import datetime

		from erpnext_brasil.fiscal.documento.nfe import Identificacao

		return Identificacao(
			uf="35",
			municipio_fato_gerador="3550308",
			natureza_operacao=natureza,
			serie="1",
			numero="123",
			codigo_numerico="12345678",
			emissao=datetime(2026, 1, 15, 10, 0, 0),
		)

	def test_natureza_longa_demais_e_recusada_na_montagem(self):
		"""O teste-âncora: antes, isto passava e voltava rejeitado pela SEFAZ."""
		from erpnext_brasil.fiscal.documento.nfe import NFeInvalida, montar_ide

		with self.assertRaises(NFeInvalida) as erro:
			montar_ide(self._identificacao("Venda " * 40), "3" * 44)

		self.assertEqual(erro.exception.campo, "natureza_operacao")

	def test_natureza_no_limite_e_aceita(self):
		from erpnext_brasil.fiscal.documento.nfe import montar_ide

		grupo = montar_ide(self._identificacao("A" * 60), "3" * 44)

		self.assertEqual(grupo["natOp"], "A" * 60)

	def test_natureza_vazia_continua_recusada(self):
		from erpnext_brasil.fiscal.documento.nfe import NFeInvalida, montar_ide

		with self.assertRaises(NFeInvalida):
			montar_ide(self._identificacao("  "), "3" * 44)


if __name__ == "__main__":
	unittest.main()
