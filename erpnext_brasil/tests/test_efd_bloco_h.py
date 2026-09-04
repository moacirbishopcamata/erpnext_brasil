# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/efd_bloco_h.py` (inventário) e do par `E001`/`E990`.

Dois testes-âncora:

- `test_o_valor_pelo_icms_e_pelo_ir_sao_diferentes` — o mesmo item tem dois valores
  legítimos no mesmo registro, e é a regra de `custo_aquisicao.py` que os separa;
- `test_e001_nao_aceita_bloco_vazio_mas_h001_aceita` — registros de abertura de bloco
  não são intercambiáveis.
"""

import unittest
from datetime import date
from decimal import Decimal as d

from erpnext_brasil.contabil.efd_bloco_h import (
	MOTIVO_FINAL_DO_PERIODO,
	MOTIVO_MUDANCA_DE_TRIBUTACAO,
	MOTIVO_SUBSTITUICAO_TRIBUTARIA,
	MOTIVOS_INVENTARIO,
	MOTIVOS_QUE_EXIGEM_H020,
	PROPRIEDADE_DE_TERCEIRO,
	ItemInventario,
	montar_bloco_h,
	montar_h001,
	montar_h005,
	montar_h010,
	montar_h020,
	montar_h030,
	montar_h990,
)
from erpnext_brasil.contabil.efd_icms_ipi import (
	EfdInvalido,
	montar_e001,
	montar_e100,
	montar_e990,
)
from erpnext_brasil.contabil.sped_texto import montar_linha

DATA = date(2026, 12, 31)


def _item(**kwargs) -> ItemInventario:
	campos = {
		"codigo_item": "PROD001",
		"unidade": "UN",
		"quantidade": d("10.000"),
		"valor_unitario": d("100.000000"),
		"valor_item": d("1000.00"),
	}
	campos.update(kwargs)
	return ItemInventario(**campos)


class TestH010(unittest.TestCase):
	def test_os_onze_campos_na_ordem_oficial(self):
		campos = montar_h010(_item())

		self.assertEqual(
			list(campos),
			[
				"REG",
				"COD_ITEM",
				"UNID",
				"QTD",
				"VL_UNIT",
				"VL_ITEM",
				"IND_PROP",
				"COD_PART",
				"TXT_COMPL",
				"COD_CTA",
				"VL_ITEM_IR",
			],
		)

	def test_o_valor_pelo_icms_e_pelo_ir_sao_diferentes(self):
		"""Campo 11 do guia: o ICMS recuperável sai do valor do estoque para o IR, mas
		não para o ICMS/IPI. Dois números certos para o mesmo item."""
		campos = montar_h010(_item(valor_item=d("1000.00"), valor_item_ir=d("820.00")))

		self.assertEqual(campos["VL_ITEM"], d("1000.00"))
		self.assertEqual(campos["VL_ITEM_IR"], d("820.00"))

	def test_sem_escrituracao_pelo_ir_o_campo_sai_vazio(self):
		"""Quem não escritura pelo IR deixa o campo vazio — não zera, que seria dizer
		que o estoque não vale nada para o imposto de renda."""
		linha = montar_linha(montar_h010(_item()))

		self.assertTrue(linha.endswith("||"))

	def test_item_de_terceiro_exige_participante(self):
		with self.assertRaises(EfdInvalido):
			_item(indicador_propriedade=PROPRIEDADE_DE_TERCEIRO)

	def test_item_de_terceiro_com_participante_e_valido(self):
		item = _item(indicador_propriedade=PROPRIEDADE_DE_TERCEIRO, codigo_participante="FORN01")

		self.assertEqual(montar_h010(item)["COD_PART"], "FORN01")

	def test_indicador_de_propriedade_desconhecido_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_item(indicador_propriedade="3")

	def test_codigo_do_item_vazio_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_item(codigo_item="")

	def test_unidade_vazia_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_item(unidade="")

	def test_float_e_recusado(self):
		with self.assertRaises(EfdInvalido):
			_item(valor_item=1000.0)

	def test_quantidade_negativa_e_erro(self):
		with self.assertRaises(EfdInvalido):
			_item(quantidade=d("-1.000"))


class TestH005(unittest.TestCase):
	def test_os_quatro_campos_na_ordem_oficial(self):
		campos = montar_h005(DATA, d("1000.00"), MOTIVO_FINAL_DO_PERIODO)

		self.assertEqual(list(campos), ["REG", "DT_INV", "VL_INV", "MOT_INV"])

	def test_data_sai_sem_separador(self):
		linha = montar_linha(montar_h005(DATA, d("1000.00"), MOTIVO_FINAL_DO_PERIODO))

		self.assertIn("|31122026|", linha)

	def test_todos_os_motivos_declarados_sao_aceitos(self):
		for motivo in MOTIVOS_INVENTARIO:
			with self.subTest(motivo=motivo):
				montar_h005(DATA, d("1000.00"), motivo)

	def test_motivo_desconhecido_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_h005(DATA, d("1000.00"), "07")

	def test_motivo_sem_zero_a_esquerda_e_erro(self):
		"""MOT_INV tem tamanho 2 fixo: "1" não é "01"."""
		with self.assertRaises(EfdInvalido):
			montar_h005(DATA, d("1000.00"), "1")


class TestBlocoCompleto(unittest.TestCase):
	def test_o_total_bate_com_a_soma_dos_itens(self):
		"""Pós-condição do guia: VL_INV = soma dos VL_ITEM."""
		bloco = montar_bloco_h(DATA, [_item(valor_item=d("600.00")), _item(valor_item=d("400.00"))])

		h005 = next(linha for linha in bloco if linha["REG"] == "H005")

		self.assertEqual(h005["VL_INV"], d("1000.00"))

	def test_a_contagem_de_linhas_inclui_abertura_e_encerramento(self):
		bloco = montar_bloco_h(DATA, [_item(), _item()])

		self.assertEqual(bloco[-1]["QTD_LIN_H"], str(len(bloco)))
		self.assertEqual(len(bloco), 5)

	def test_bloco_sem_inventario_tem_so_abertura_e_encerramento(self):
		bloco = montar_bloco_h(DATA, [])

		self.assertEqual([linha["REG"] for linha in bloco], ["H001", "H990"])
		self.assertEqual(bloco[0]["IND_MOV"], "1")
		self.assertEqual(bloco[-1]["QTD_LIN_H"], "2")

	def test_inventario_zerado_com_itens_e_erro(self):
		"""'Atribuir valor Zero ao inventário significa escriturar sem estoque' — item
		com valor zero contradiz o próprio total."""
		with self.assertRaises(EfdInvalido):
			montar_bloco_h(DATA, [_item(valor_item=d("0.00"))])

	def test_motivo_de_st_recusa_a_montagem_simplificada(self):
		"""MOT_INV 06 exige um H030 por item, que esta função não monta — recusar é
		melhor que devolver um bloco incompleto que parece pronto."""
		with self.assertRaises(EfdInvalido):
			montar_bloco_h(DATA, [_item()], motivo=MOTIVO_SUBSTITUICAO_TRIBUTARIA)


class TestH020eH030(unittest.TestCase):
	def test_h020_tem_quatro_campos(self):
		campos = montar_h020("000", d("100.00"), d("18.00"))

		self.assertEqual(list(campos), ["REG", "CST_ICMS", "BC_ICMS", "VL_ICMS"])

	def test_cst_com_menos_de_tres_digitos_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_h020("00", d("100.00"), d("18.00"))

	def test_h030_tem_cinco_campos(self):
		campos = montar_h030(d("18.000000"), d("130.000000"), d("23.400000"), d("2.600000"))

		self.assertEqual(list(campos), ["REG", "VL_ICMS_OP", "VL_BC_ICMS_ST", "VL_ICMS_ST", "VL_FCP"])

	def test_fcp_maior_que_o_icms_st_e_erro(self):
		"""O campo 04 já contém a parcela do FCP; o 05 a destaca de dentro dele."""
		with self.assertRaises(EfdInvalido):
			montar_h030(d("18.000000"), d("130.000000"), d("2.000000"), d("3.000000"))

	def test_os_motivos_que_exigem_h020_sao_de_02_a_05(self):
		self.assertEqual(MOTIVOS_QUE_EXIGEM_H020, ("02", "03", "04", "05"))
		self.assertIn(MOTIVO_MUDANCA_DE_TRIBUTACAO, MOTIVOS_QUE_EXIGEM_H020)
		self.assertNotIn(MOTIVO_FINAL_DO_PERIODO, MOTIVOS_QUE_EXIGEM_H020)
		self.assertNotIn(MOTIVO_SUBSTITUICAO_TRIBUTARIA, MOTIVOS_QUE_EXIGEM_H020)


class TestAberturaEEncerramentoDoBlocoE(unittest.TestCase):
	def test_e001_nao_aceita_bloco_vazio_mas_h001_aceita(self):
		"""O achado: 'Valor Válido: [0]' no E001 contra '[0,1]' no H001. Copiar a
		validação de um para o outro produz arquivo rejeitado pelo PVA."""
		self.assertEqual(montar_e001()["IND_MOV"], "0")
		self.assertEqual(montar_h001(tem_dados=False)["IND_MOV"], "1")

	def test_e001_nao_recebe_parametro(self):
		"""A assinatura torna o erro impossível em vez de validá-lo depois."""
		with self.assertRaises(TypeError):
			montar_e001(False)

	def test_e990_conta_as_linhas_do_bloco(self):
		self.assertEqual(montar_e990(7)["QTD_LIN_E"], "7")

	def test_bloco_e_com_menos_de_quatro_linhas_e_erro(self):
		"""E001, E100 e E110 são obrigatórios: um bloco E com três linhas não existe."""
		with self.assertRaises(EfdInvalido):
			montar_e990(3)

	def test_e100_tem_tres_campos(self):
		campos = montar_e100("01012026", "31012026")

		self.assertEqual(list(campos), ["REG", "DT_INI", "DT_FIN"])

	def test_periodo_invertido_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_e100("31012026", "01012026")

	def test_a_comparacao_de_datas_nao_se_deixa_enganar_pelo_dia(self):
		"""`ddmmaaaa` comparado como texto daria 31/01 > 01/02 — o dia mandando mais que
		o mês. Um período legítimo que atravessa a virada tem de passar."""
		campos = montar_e100("31012026", "01022026")

		self.assertEqual(campos["DT_FIN"], "01022026")

	def test_data_fora_do_formato_e_erro(self):
		with self.assertRaises(EfdInvalido):
			montar_e100("01/01/2026", "31012026")

	def test_bloco_h_aceita_o_minimo_de_duas_linhas(self):
		"""O mínimo difere do bloco E justamente porque este pode ser vazio."""
		self.assertEqual(montar_h990(2)["QTD_LIN_H"], "2")

		with self.assertRaises(EfdInvalido):
			montar_h990(1)


class TestCosturaComOCustoDeAquisicao(unittest.TestCase):
	"""A diferença entre VL_ITEM e VL_ITEM_IR é exatamente o crédito recuperável."""

	def test_o_custo_de_aquisicao_produz_os_dois_valores_do_h010(self):
		from erpnext_brasil.contabil.custo_aquisicao import (
			TributoDaAquisicao,
			custo_de_aquisicao,
		)

		compra = custo_de_aquisicao(
			valor_mercadoria=d("1000.00"),
			tributos=[
				TributoDaAquisicao("ICMS", d("180.00"), recuperavel=True),
				TributoDaAquisicao("PIS", d("16.50"), recuperavel=True),
				TributoDaAquisicao("COFINS", d("76.00"), recuperavel=True),
			],
		)

		campos = montar_h010(
			_item(
				quantidade=d("1.000"),
				valor_unitario=compra.total_pago,
				valor_item=compra.total_pago,
				valor_item_ir=compra.custo,
			)
		)

		self.assertEqual(campos["VL_ITEM"], d("1000.00"))
		self.assertEqual(campos["VL_ITEM_IR"], d("727.50"))
		self.assertEqual(campos["VL_ITEM"] - campos["VL_ITEM_IR"], compra.creditos)

	def test_sem_credito_os_dois_valores_coincidem(self):
		"""Quem não credita não exclui nada: aí sim os dois números são iguais."""
		from erpnext_brasil.contabil.custo_aquisicao import custo_de_aquisicao

		compra = custo_de_aquisicao(valor_mercadoria=d("1000.00"))

		self.assertEqual(compra.custo, compra.total_pago)


if __name__ == "__main__":
	unittest.main()
