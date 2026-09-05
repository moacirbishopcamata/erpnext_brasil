# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/efd_bloco_k.py` — controle da produção e do estoque.

Três testes-âncora, um por achado do leiaute:

- `test_saldo_e_movimentacao_tem_precisao_diferente` — o mesmo conceito com casas
  decimais diferentes dentro do mesmo bloco;
- `test_produto_intermediario_tem_saldo_mas_nao_tem_consumo` — cada registro aceita um
  conjunto próprio de tipos de item;
- `test_o_insumo_substituido_sai_sempre_vazio` — campo que existe no leiaute e não deve
  ser preenchido.
"""

import unittest
from datetime import date
from decimal import Decimal as d

from erpnext_brasil.contabil.efd_bloco_k import (
	DECIMAIS_MOVIMENTACAO,
	DECIMAIS_SALDO,
	ESTOQUE_DE_TERCEIRO,
	LEIAUTE_COMPLETO,
	LEIAUTE_SIMPLIFICADO,
	LEIAUTE_SO_SALDOS,
	REGISTROS_DISPENSADOS_NO_SIMPLIFICADO,
	TIPO_PRODUTO_INTERMEDIARIO,
	TIPOS_DE_LEIAUTE,
	TIPOS_EM_K200,
	TIPOS_EM_K220,
	TIPOS_EM_K230,
	TIPOS_EM_K235,
	EstoqueEscriturado,
	InsumoConsumido,
	ItemProduzido,
	MovimentacaoInterna,
	arredondar_quantidade,
	montar_bloco_k,
	montar_k001,
	montar_k010,
	montar_k100,
	montar_k200,
	montar_k220,
	montar_k230,
	montar_k235,
	montar_k990,
	validar_tipo_do_item,
)
from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido

INICIO = date(2026, 1, 1)
FIM = date(2026, 1, 31)


def _saldo(**kwargs) -> EstoqueEscriturado:
	campos = {"data_estoque": FIM, "codigo_item": "PROD001", "quantidade": d("100.000")}
	campos.update(kwargs)
	return EstoqueEscriturado(**campos)


class TestPrecisaoDasQuantidades(unittest.TestCase):
	def test_saldo_e_movimentacao_tem_precisao_diferente(self):
		"""K200 usa 3 casas; K220, K230 e K235 usam 6 — no mesmo bloco."""
		self.assertEqual(DECIMAIS_SALDO, 3)
		self.assertEqual(DECIMAIS_MOVIMENTACAO, 6)

		saldo = montar_k200(_saldo(quantidade=d("100.1234567")))
		consumo = montar_k235(
			InsumoConsumido(data_saida=FIM, codigo_item="INS001", quantidade=d("100.1234567"))
		)

		self.assertEqual(saldo["QTD"], d("100.123"))
		self.assertEqual(consumo["QTD"], d("100.123457"))

	def test_a_conversao_arredonda_e_nao_trunca(self):
		"""Truncar faria o saldo divergir da movimentação que o produziu."""
		self.assertEqual(arredondar_quantidade(d("1.9999"), DECIMAIS_SALDO), d("2.000"))
		self.assertEqual(arredondar_quantidade(d("1.0005"), DECIMAIS_SALDO), d("1.001"))

	def test_arredondar_recusa_float(self):
		with self.assertRaises(EfdInvalido):
			arredondar_quantidade(1.5, DECIMAIS_SALDO)

	def test_producao_e_movimentacao_usam_a_mesma_precisao(self):
		producao = montar_k230(ItemProduzido(codigo_item="PROD001", quantidade=d("10.1234567")))
		movimentacao = montar_k220(
			MovimentacaoInterna(
				data_movimentacao=FIM,
				codigo_item_origem="A",
				codigo_item_destino="B",
				quantidade_origem=d("10.1234567"),
				quantidade_destino=d("10.1234567"),
			)
		)

		self.assertEqual(producao["QTD_ENC"], movimentacao["QTD_ORI"])


class TestTiposDeItemPorRegistro(unittest.TestCase):
	def test_produto_intermediario_tem_saldo_mas_nao_tem_consumo(self):
		"""O achado: tipo 06 entra no K200 e não entra no K235 — o Fisco deduz o consumo
		por diferença."""
		self.assertIn(TIPO_PRODUTO_INTERMEDIARIO, TIPOS_EM_K200)
		self.assertNotIn(TIPO_PRODUTO_INTERMEDIARIO, TIPOS_EM_K235)
		self.assertNotIn(TIPO_PRODUTO_INTERMEDIARIO, TIPOS_EM_K220)

	def test_k230_so_aceita_produto_em_processo_e_acabado(self):
		self.assertEqual(TIPOS_EM_K230, frozenset({"03", "04"}))

	def test_nenhum_registro_aceita_todos_os_tipos(self):
		"""Se dois conjuntos fossem iguais, a distinção não precisaria existir."""
		conjuntos = [TIPOS_EM_K200, TIPOS_EM_K220, TIPOS_EM_K230]

		self.assertEqual(len({frozenset(c) for c in conjuntos}), len(conjuntos))

	def test_tipo_recusado_explica_o_caso_do_intermediario(self):
		with self.assertRaises(EfdInvalido) as erro:
			validar_tipo_do_item(TIPO_PRODUTO_INTERMEDIARIO, TIPOS_EM_K235, "K235")

		self.assertIn("por diferença", str(erro.exception))

	def test_tipo_aceito_passa(self):
		validar_tipo_do_item("01", TIPOS_EM_K235, "K235")

	def test_tipo_desconhecido_e_erro(self):
		with self.assertRaises(EfdInvalido):
			validar_tipo_do_item("99", TIPOS_EM_K200, "K200")


class TestK200(unittest.TestCase):
	def test_os_seis_campos_na_ordem_oficial(self):
		campos = montar_k200(_saldo())

		self.assertEqual(list(campos), ["REG", "DT_EST", "COD_ITEM", "QTD", "IND_EST", "COD_PART"])

	def test_saldo_zero_e_valido(self):
		"""O guia diz que informar estoque zero é desnecessário, não proibido."""
		self.assertEqual(montar_k200(_saldo(quantidade=d("0.000")))["QTD"], d("0.000"))

	def test_estoque_de_terceiro_exige_participante(self):
		with self.assertRaises(EfdInvalido):
			_saldo(indicador_estoque=ESTOQUE_DE_TERCEIRO)

	def test_estoque_de_terceiro_com_participante_e_valido(self):
		saldo = _saldo(indicador_estoque=ESTOQUE_DE_TERCEIRO, codigo_participante="IND01")

		self.assertEqual(montar_k200(saldo)["COD_PART"], "IND01")

	def test_indicador_desconhecido_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_saldo(indicador_estoque="3")

	def test_quantidade_negativa_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_saldo(quantidade=d("-1.000"))


class TestK220(unittest.TestCase):
	def _movimentacao(self, **kwargs) -> MovimentacaoInterna:
		campos = {
			"data_movimentacao": FIM,
			"codigo_item_origem": "A",
			"codigo_item_destino": "B",
			"quantidade_origem": d("100.000000"),
			"quantidade_destino": d("100.000000"),
		}
		campos.update(kwargs)
		return MovimentacaoInterna(**campos)

	def test_os_seis_campos_na_ordem_oficial(self):
		campos = montar_k220(self._movimentacao())

		self.assertEqual(
			list(campos),
			["REG", "DT_MOV", "COD_ITEM_ORI", "COD_ITEM_DEST", "QTD_ORI", "QTD_DEST"],
		)

	def test_origem_igual_ao_destino_e_erro(self):
		"""Se o código não muda, o registro é o K260, não o K220."""
		with self.assertRaises(EfdInvalido) as erro:
			self._movimentacao(codigo_item_destino="A")

		self.assertIn("K260", str(erro.exception))

	def test_as_quantidades_podem_diferir(self):
		"""Reclassificar 100 kg em 98 kg é movimentação legítima."""
		campos = montar_k220(self._movimentacao(quantidade_destino=d("98.000000")))

		self.assertNotEqual(campos["QTD_ORI"], campos["QTD_DEST"])

	def test_quantidade_zero_e_erro(self):
		with self.assertRaises(EfdInvalido):
			self._movimentacao(quantidade_origem=d("0.000000"))


class TestK230(unittest.TestCase):
	def test_os_seis_campos_na_ordem_oficial(self):
		campos = montar_k230(ItemProduzido(codigo_item="PROD001", quantidade=d("10.000000")))

		self.assertEqual(
			list(campos),
			["REG", "DT_INI_OP", "DT_FIN_OP", "COD_DOC_OP", "COD_ITEM", "QTD_ENC"],
		)

	def test_sem_ordem_de_producao_a_quantidade_tem_de_ser_positiva(self):
		with self.assertRaises(EfdInvalido):
			ItemProduzido(codigo_item="PROD001", quantidade=d("0.000000"))

	def test_ordem_em_elaboracao_admite_producao_zero(self):
		"""DT_FIN_OP em branco é informação: a OP não fechou no período."""
		item = ItemProduzido(
			codigo_item="PROD001",
			quantidade=d("0.000000"),
			data_inicio_op=INICIO,
			codigo_ordem_producao="OP-001",
		)

		self.assertIsNone(montar_k230(item)["DT_FIN_OP"])

	def test_ordem_sem_data_de_inicio_e_erro(self):
		with self.assertRaises(EfdInvalido):
			ItemProduzido(codigo_item="PROD001", quantidade=d("1.000000"), codigo_ordem_producao="OP-001")

	def test_data_de_inicio_sem_codigo_de_ordem_e_erro(self):
		with self.assertRaises(EfdInvalido):
			ItemProduzido(codigo_item="PROD001", quantidade=d("1.000000"), data_inicio_op=INICIO)

	def test_ordem_que_termina_antes_de_comecar_e_erro(self):
		with self.assertRaises(EfdInvalido):
			ItemProduzido(
				codigo_item="PROD001",
				quantidade=d("1.000000"),
				data_inicio_op=FIM,
				data_fim_op=INICIO,
				codigo_ordem_producao="OP-001",
			)


class TestK235(unittest.TestCase):
	def test_os_cinco_campos_na_ordem_oficial(self):
		campos = montar_k235(InsumoConsumido(data_saida=FIM, codigo_item="INS001", quantidade=d("5.000000")))

		self.assertEqual(list(campos), ["REG", "DT_SAIDA", "COD_ITEM", "QTD", "COD_INS_SUBST"])

	def test_o_insumo_substituido_sai_sempre_vazio(self):
		"""'A partir de 01/01/2022 não preencher' — o campo permanece, a regra acabou."""
		campos = montar_k235(InsumoConsumido(data_saida=FIM, codigo_item="INS001", quantidade=d("5.000000")))

		self.assertEqual(campos["COD_INS_SUBST"], "")

	def test_nao_ha_como_preencher_o_insumo_substituido(self):
		"""A classe não expõe o campo: o erro fica impossível, não apenas validado."""
		with self.assertRaises(TypeError):
			InsumoConsumido(
				data_saida=FIM,
				codigo_item="INS001",
				quantidade=d("5.000000"),
				codigo_insumo_substituido="ANTIGO",
			)


class TestK010(unittest.TestCase):
	def test_todos_os_leiautes_declarados_sao_aceitos(self):
		for tipo in TIPOS_DE_LEIAUTE:
			with self.subTest(leiaute=tipo):
				montar_k010(tipo)

	def test_leiaute_desconhecido_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_k010("3")

	def test_o_simplificado_dispensa_o_registro_de_maior_volume(self):
		"""K235 (insumos consumidos) é a diferença mais cara entre os dois leiautes."""
		self.assertIn("K235", REGISTROS_DISPENSADOS_NO_SIMPLIFICADO)
		self.assertNotIn("K200", REGISTROS_DISPENSADOS_NO_SIMPLIFICADO)
		self.assertNotIn("K230", REGISTROS_DISPENSADOS_NO_SIMPLIFICADO)


class TestBlocoCompleto(unittest.TestCase):
	def test_a_contagem_de_linhas_inclui_abertura_e_encerramento(self):
		bloco = montar_bloco_k(INICIO, FIM, [_saldo(), _saldo(codigo_item="PROD002")])

		self.assertEqual([linha["REG"] for linha in bloco][:3], ["K001", "K010", "K100"])
		self.assertEqual(bloco[-1]["QTD_LIN_K"], str(len(bloco)))
		self.assertEqual(len(bloco), 6)

	def test_bloco_sem_dados_tem_so_abertura_e_encerramento(self):
		bloco = montar_bloco_k(INICIO, FIM, [])

		self.assertEqual([linha["REG"] for linha in bloco], ["K001", "K990"])
		self.assertEqual(bloco[0]["IND_MOV"], "1")

	def test_saldo_com_data_diferente_do_periodo_e_erro(self):
		"""DT_EST tem de ser igual a DT_FIN do K100: saldo com outra data não é saldo
		daquele período."""
		with self.assertRaises(EfdInvalido):
			montar_bloco_k(INICIO, FIM, [_saldo(data_estoque=INICIO)])

	def test_o_leiaute_restrito_a_saldos_produz_o_bloco_inteiro(self):
		bloco = montar_bloco_k(INICIO, FIM, [_saldo()], tipo_de_leiaute=LEIAUTE_SO_SALDOS)

		self.assertEqual(bloco[1]["IND_TP_LEIAUTE"], LEIAUTE_SO_SALDOS)

	def test_o_leiaute_e_declarado_no_bloco(self):
		bloco = montar_bloco_k(INICIO, FIM, [_saldo()], tipo_de_leiaute=LEIAUTE_SIMPLIFICADO)

		self.assertEqual(bloco[1]["IND_TP_LEIAUTE"], LEIAUTE_SIMPLIFICADO)

	def test_o_padrao_e_o_leiaute_completo(self):
		bloco = montar_bloco_k(INICIO, FIM, [_saldo()])

		self.assertEqual(bloco[1]["IND_TP_LEIAUTE"], LEIAUTE_COMPLETO)


class TestAberturaEEncerramento(unittest.TestCase):
	def test_k001_aceita_bloco_vazio(self):
		"""Ao contrário do E001, que só aceita '0'."""
		self.assertEqual(montar_k001(tem_dados=False)["IND_MOV"], "1")
		self.assertEqual(montar_k001(tem_dados=True)["IND_MOV"], "0")

	def test_k990_conta_as_linhas(self):
		self.assertEqual(montar_k990(9)["QTD_LIN_K"], "9")

	def test_k990_com_menos_de_duas_linhas_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_k990(1)

	def test_periodo_invertido_no_k100_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_k100(FIM, INICIO)

	def test_k100_recusa_data_em_texto(self):
		"""Este módulo usa `date`, não `ddmmaaaa` — comparação de texto erra na virada."""
		with self.assertRaises(EfdInvalido):
			montar_k100("01012026", "31012026")


if __name__ == "__main__":
	unittest.main()
