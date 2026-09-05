# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/efd_bloco_d.py` — documentos de serviço de transporte.

Três testes-âncora, um por achado:

- `test_o_ind_frt_do_d100_nao_aceita_o_dominio_do_c100` — mesmo nome de campo, domínios
  diferentes no mesmo arquivo;
- `test_o_analitico_do_transporte_tem_tres_campos_a_menos` — `D190` não é `C190`;
- `test_cfop_de_saida_em_documento_de_entrada_e_erro` — o CFOP tem de concordar com o
  sentido da operação.
"""

import unittest
from datetime import date
from decimal import Decimal as d

from erpnext_brasil.contabil.efd_bloco_c import IND_FRT_VALIDOS, RegistroAnalitico, montar_c190
from erpnext_brasil.contabil.efd_bloco_d import (
	EMISSAO_DE_TERCEIROS,
	EMISSAO_PROPRIA,
	IND_FRT_VALIDOS_D100,
	MODELO_BPE,
	MODELO_CTE,
	MODELO_CTE_OS,
	MODELOS_ENCERRADOS_EM_2018,
	OPERACAO_AQUISICAO,
	OPERACAO_PRESTACAO,
	AnaliticoTransporte,
	DocumentoTransporte,
	montar_bloco_d,
	montar_d001,
	montar_d100,
	montar_d190,
	montar_d990,
)
from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido
from erpnext_brasil.contabil.sped_texto import montar_linha
from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave

CHAVE_CTE = montar_chave("35", "2601", "11222333000181", MODELO_CTE, "1", "1", "1", "12345678")
CHAVE_BPE = montar_chave("35", "2601", "11222333000181", MODELO_BPE, "1", "1", "1", "12345678")
EMISSAO = date(2026, 1, 15)


def _documento(**kwargs) -> DocumentoTransporte:
	campos = {
		"operacao": OPERACAO_PRESTACAO,
		"emissao": EMISSAO_PROPRIA,
		"codigo_modelo": MODELO_CTE,
		"codigo_situacao": "00",
		"serie": "001",
		"numero": "1",
		"data_emissao": EMISSAO,
		"chave_acesso": CHAVE_CTE,
		"valor_documento": d("1000.00"),
		"valor_servico": d("1000.00"),
		"valor_bc_icms": d("1000.00"),
		"valor_icms": d("120.00"),
	}
	campos.update(kwargs)
	return DocumentoTransporte(**campos)


def _analitico(**kwargs) -> AnaliticoTransporte:
	campos = {
		"cst_icms": "000",
		"cfop": "5352",
		"valor_operacao": d("1000.00"),
		"valor_bc_icms": d("1000.00"),
		"valor_icms": d("120.00"),
	}
	campos.update(kwargs)
	return AnaliticoTransporte(**campos)


class TestIndicadorDeFrete(unittest.TestCase):
	def test_o_ind_frt_do_d100_nao_aceita_o_dominio_do_c100(self):
		"""O achado: o C100 ganhou '3' e '4' em 2018; o D100 ficou na tabela de 2012."""
		self.assertEqual(IND_FRT_VALIDOS_D100, frozenset({"0", "1", "2", "9"}))
		self.assertIn("3", IND_FRT_VALIDOS)
		self.assertIn("4", IND_FRT_VALIDOS)
		self.assertNotIn("3", IND_FRT_VALIDOS_D100)
		self.assertNotIn("4", IND_FRT_VALIDOS_D100)

	def test_transporte_proprio_e_recusado_no_d100(self):
		"""'3' é transporte próprio no C100 e não existe no D100."""
		with self.assertRaises(EfdInvalido) as erro:
			_documento(indicador_frete="3")

		self.assertIn("C100", str(erro.exception))

	def test_os_codigos_comuns_sao_aceitos(self):
		for codigo in sorted(IND_FRT_VALIDOS_D100):
			with self.subTest(ind_frt=codigo):
				self.assertEqual(montar_d100(_documento(indicador_frete=codigo))["IND_FRT"], codigo)

	def test_sem_frete_informado_o_campo_sai_vazio(self):
		"""'9' (sem cobrança) é afirmação sobre a operação — não se assume por omissão."""
		self.assertEqual(montar_d100(_documento())["IND_FRT"], "")


class TestD190(unittest.TestCase):
	def test_o_analitico_do_transporte_tem_tres_campos_a_menos(self):
		"""D190 tem 9 campos; C190 tem 12 — sem ST nem IPI."""
		do_transporte = montar_d190(_analitico())
		da_mercadoria = montar_c190(
			RegistroAnalitico(cst_icms="000", cfop="5102", valor_operacao=d("1000.00"))
		)

		self.assertEqual(len(do_transporte), 9)
		self.assertEqual(len(da_mercadoria), 12)

		ausentes = {"VL_BC_ICMS_ST", "VL_ICMS_ST", "VL_IPI"}

		self.assertTrue(ausentes.isdisjoint(do_transporte))
		self.assertTrue(ausentes.issubset(da_mercadoria))

	def test_os_nove_campos_na_ordem_oficial(self):
		self.assertEqual(
			list(montar_d190(_analitico())),
			[
				"REG",
				"CST_ICMS",
				"CFOP",
				"ALIQ_ICMS",
				"VL_OPR",
				"VL_BC_ICMS",
				"VL_ICMS",
				"VL_RED_BC",
				"COD_OBS",
			],
		)

	def test_cst_com_origem_diferente_de_zero_e_erro(self):
		"""Não há origem de mercadoria em serviço de transporte."""
		with self.assertRaises(EfdInvalido):
			_analitico(cst_icms="100")

	def test_cfop_de_agrupamento_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_analitico(cfop="5350")

	def test_reducao_de_base_exige_cst_20_ou_70(self):
		with self.assertRaises(EfdInvalido):
			_analitico(valor_reducao_bc=d("100.00"))

	def test_reducao_de_base_com_cst_020_e_valida(self):
		analitico = _analitico(cst_icms="020", valor_reducao_bc=d("100.00"))

		self.assertEqual(montar_d190(analitico)["VL_RED_BC"], d("100.00"))


class TestD100(unittest.TestCase):
	def test_os_vinte_e_cinco_campos_na_ordem_oficial(self):
		campos = montar_d100(_documento())

		self.assertEqual(len(campos), 25)
		self.assertEqual(list(campos)[:6], ["REG", "IND_OPER", "IND_EMIT", "COD_PART", "COD_MOD", "COD_SIT"])
		self.assertEqual(list(campos)[-2:], ["COD_MUN_ORIG", "COD_MUN_DEST"])

	def test_emissao_de_terceiros_so_pode_ser_aquisicao(self):
		with self.assertRaises(EfdInvalido):
			_documento(emissao=EMISSAO_DE_TERCEIROS, operacao=OPERACAO_PRESTACAO)

	def test_emissao_de_terceiros_na_entrada_e_valida(self):
		documento = _documento(
			emissao=EMISSAO_DE_TERCEIROS, operacao=OPERACAO_AQUISICAO, codigo_participante="TRA01"
		)

		self.assertEqual(montar_d100(documento)["IND_EMIT"], EMISSAO_DE_TERCEIROS)

	def test_cte_sem_chave_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_documento(chave_acesso="")

	def test_cte_com_numeracao_inutilizada_dispensa_a_chave(self):
		documento = _documento(codigo_situacao="05", chave_acesso="")

		self.assertEqual(montar_d100(documento)["CHV_CTE"], "")

	def test_chave_invalida_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_documento(chave_acesso="3" * 44)

	def test_serie_do_cte_tem_tres_posicoes(self):
		with self.assertRaises(EfdInvalido) as erro:
			_documento(serie="1")

		self.assertIn("000", str(erro.exception))

	def test_serie_vazia_nao_e_o_mesmo_que_zeros(self):
		with self.assertRaises(EfdInvalido):
			_documento(serie="")

	def test_cte_os_tambem_exige_serie_de_tres_posicoes(self):
		chave = montar_chave("35", "2601", "11222333000181", MODELO_CTE_OS, "1", "1", "1", "12345678")

		with self.assertRaises(EfdInvalido):
			_documento(codigo_modelo=MODELO_CTE_OS, chave_acesso=chave, serie="1")

	def test_modelo_desconhecido_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_documento(codigo_modelo="55")

	def test_numero_zero_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_documento(numero="0")


class TestModelosEncerrados(unittest.TestCase):
	def test_modelo_em_papel_com_data_recente_e_erro(self):
		"""Os modelos 07, 09, 10, 11, 26 e 27 exigem DT_DOC anterior a 01/01/2019."""
		with self.assertRaises(EfdInvalido):
			_documento(codigo_modelo="07", chave_acesso="", serie="1", data_emissao=EMISSAO)

	def test_modelo_em_papel_com_data_antiga_e_valido(self):
		documento = _documento(
			codigo_modelo="07", chave_acesso="", serie="1", data_emissao=date(2018, 12, 31)
		)

		self.assertEqual(montar_d100(documento)["COD_MOD"], "07")

	def test_o_cte_nao_esta_entre_os_encerrados(self):
		self.assertNotIn(MODELO_CTE, MODELOS_ENCERRADOS_EM_2018)
		self.assertNotIn(MODELO_CTE_OS, MODELOS_ENCERRADOS_EM_2018)
		self.assertNotIn(MODELO_BPE, MODELOS_ENCERRADOS_EM_2018)


class TestBpe(unittest.TestCase):
	def _bpe(self, **kwargs) -> DocumentoTransporte:
		campos = {
			"codigo_modelo": MODELO_BPE,
			"chave_acesso": CHAVE_BPE,
			"serie": "1",
			"codigo_participante": "",
		}
		campos.update(kwargs)
		return _documento(**campos)

	def test_bpe_nao_informa_participante(self):
		with self.assertRaises(EfdInvalido):
			self._bpe(codigo_participante="CLI01")

	def test_bpe_nao_informa_subserie(self):
		with self.assertRaises(EfdInvalido):
			self._bpe(subserie="01")

	def test_bpe_nao_informa_frete(self):
		with self.assertRaises(EfdInvalido):
			self._bpe(indicador_frete="0")

	def test_bpe_nao_e_escriturado_nas_entradas(self):
		with self.assertRaises(EfdInvalido):
			self._bpe(operacao=OPERACAO_AQUISICAO)

	def test_bpe_de_saida_e_valido(self):
		self.assertEqual(montar_d100(self._bpe())["COD_MOD"], MODELO_BPE)


class TestBlocoCompleto(unittest.TestCase):
	def test_o_bloco_encadeia_documento_e_analitico(self):
		bloco = montar_bloco_d([(_documento(), [_analitico()])])

		self.assertEqual([linha["REG"] for linha in bloco], ["D001", "D100", "D190", "D990"])
		self.assertEqual(bloco[-1]["QTD_LIN_D"], "4")

	def test_bloco_sem_documentos(self):
		bloco = montar_bloco_d([])

		self.assertEqual([linha["REG"] for linha in bloco], ["D001", "D990"])
		self.assertEqual(bloco[0]["IND_MOV"], "1")

	def test_documento_regular_sem_analitico_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_bloco_d([(_documento(), [])])

	def test_documento_cancelado_nao_tem_analitico(self):
		cancelado = _documento(codigo_situacao="02")
		bloco = montar_bloco_d([(cancelado, [])])

		self.assertEqual([linha["REG"] for linha in bloco], ["D001", "D100", "D990"])

	def test_documento_cancelado_com_analitico_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_bloco_d([(_documento(codigo_situacao="02"), [_analitico()])])

	def test_cfop_de_saida_em_documento_de_entrada_e_erro(self):
		"""IND_OPER '0' exige CFOP começando com 1, 2 ou 3."""
		entrada = _documento(
			operacao=OPERACAO_AQUISICAO,
			emissao=EMISSAO_DE_TERCEIROS,
			codigo_participante="TRA01",
		)

		with self.assertRaises(EfdInvalido) as erro:
			montar_bloco_d([(entrada, [_analitico(cfop="5352")])])

		self.assertIn("CFOP", str(erro.exception))

	def test_cfop_de_entrada_em_documento_de_entrada_e_valido(self):
		entrada = _documento(
			operacao=OPERACAO_AQUISICAO,
			emissao=EMISSAO_DE_TERCEIROS,
			codigo_participante="TRA01",
		)
		bloco = montar_bloco_d([(entrada, [_analitico(cfop="1352")])])

		self.assertEqual(len(bloco), 4)

	def test_base_do_documento_tem_de_bater_com_a_soma_dos_analiticos(self):
		with self.assertRaises(EfdInvalido) as erro:
			montar_bloco_d([(_documento(), [_analitico(valor_bc_icms=d("900.00"))])])

		self.assertIn("VL_BC_ICMS", str(erro.exception))

	def test_dois_analiticos_somam_para_o_documento(self):
		"""Com N analíticos vale a soma — a leitura consistente da tensão documentada."""
		bloco = montar_bloco_d(
			[
				(
					_documento(),
					[
						_analitico(valor_bc_icms=d("600.00"), valor_icms=d("72.00")),
						_analitico(cfop="6352", valor_bc_icms=d("400.00"), valor_icms=d("48.00")),
					],
				)
			]
		)

		self.assertEqual([linha["REG"] for linha in bloco], ["D001", "D100", "D190", "D190", "D990"])

	def test_serializa_em_texto_sped(self):
		bloco = montar_bloco_d([(_documento(), [_analitico()])])
		linhas = [montar_linha(linha) for linha in bloco]

		self.assertTrue(linhas[1].startswith("|D100|1|0||57|00|001||1|"))
		self.assertIn("15012026", linhas[1])
		self.assertIn("1000,00", linhas[1])


class TestAberturaEEncerramento(unittest.TestCase):
	def test_d001_aceita_bloco_vazio(self):
		self.assertEqual(montar_d001(tem_dados=False)["IND_MOV"], "1")
		self.assertEqual(montar_d001(tem_dados=True)["IND_MOV"], "0")

	def test_d990_conta_as_linhas(self):
		self.assertEqual(montar_d990(7)["QTD_LIN_D"], "7")

	def test_d990_com_menos_de_duas_linhas_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_d990(1)


if __name__ == "__main__":
	unittest.main()
