# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Prova de ponta a ponta: um arquivo EFD-ICMS/IPI mínimo, completo e serializado.

Nenhum teste anterior cruzava os quatro módulos do EFD (`efd_bloco_0`, `efd_bloco_c`,
`efd_icms_ipi`, `efd_bloco_9`) com o serializador (`sped_texto`) — cada um estava
testado sozinho. Este é o teste de **costura**: monta um arquivo de verdade, do `0000`
ao `9999`, e confere que as contagens que o Bloco 9 declara batem com as linhas
efetivamente produzidas.

É exatamente o tipo de erro que cobertura alta de teste unitário não pega: cada
`montar_*` pode estar certo e o arquivo inteiro sair com `QTD_LIN` errado, porque
ninguém contou as linhas de verdade.
"""

import unittest
from collections import Counter
from decimal import Decimal as d

from erpnext_brasil.contabil.apuracao_periodo import ApuracaoPeriodo
from erpnext_brasil.contabil.efd_bloco_0 import (
	ATIVIDADE_INDUSTRIAL,
	Identificacao,
	Item,
	Participante,
	montar_0000,
	montar_0001,
	montar_0150,
	montar_0190,
	montar_0200,
	montar_0990,
)
from erpnext_brasil.contabil.efd_bloco_9 import montar_bloco_9
from erpnext_brasil.contabil.efd_bloco_c import (
	EMISSAO_PROPRIA,
	MODELO_NFE,
	OPERACAO_SAIDA,
	DocumentoFiscal,
	RegistroAnalitico,
	montar_c001,
	montar_c100,
	montar_c190,
	montar_c990,
)
from erpnext_brasil.contabil.efd_icms_ipi import montar_e110
from erpnext_brasil.contabil.sped_texto import montar_linha
from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave

CHAVE = montar_chave("35", "2601", "11222333000181", MODELO_NFE, "1", "1", "1", "12345678")


def _montar_arquivo() -> list[dict]:
	"""Um arquivo mínimo mas real: identificação, um participante, uma unidade, um
	item, uma nota fiscal com seu analítico, e a apuração do ICMS do período."""
	bloco_0 = [
		montar_0000(
			Identificacao(
				codigo_versao="017",
				data_inicial="01012026",
				data_final="31012026",
				nome="Empresa Teste LTDA",
				uf="RO",
				inscricao_estadual="00000000",
				codigo_municipio="1100205",
				perfil="A",
				atividade=ATIVIDADE_INDUSTRIAL,
				cnpj="11222333000181",
			)
		),
		montar_0001(tem_dados=True),
		montar_0150(
			Participante(
				codigo="CLI001",
				nome="Cliente Teste",
				codigo_pais="01058",
				cnpj="11444777000161",
			)
		),
		montar_0190("UN", "Unidade"),
		montar_0200(
			Item(
				codigo="PROD001",
				descricao="Produto de Teste",
				unidade_inventario="UN",
				tipo="04",
				codigo_ncm="84713019",
			)
		),
	]
	bloco_0.append(montar_0990(len(bloco_0) + 1))

	bloco_c = [
		montar_c001(tem_dados=True),
		montar_c100(
			DocumentoFiscal(
				operacao=OPERACAO_SAIDA,
				emissao=EMISSAO_PROPRIA,
				codigo_modelo=MODELO_NFE,
				codigo_situacao="00",
				numero="1",
				data_emissao="15012026",
				valor_documento=d("1000.00"),
				indicador_pagamento="0",
				indicador_frete="0",
				codigo_participante="CLI001",
				chave_acesso=CHAVE,
				valor_mercadorias=d("1000.00"),
				valor_bc_icms=d("1000.00"),
				valor_icms=d("175.00"),
			)
		),
		montar_c190(
			RegistroAnalitico(
				cst_icms="000",
				cfop="5102",
				aliquota_icms=d("17.50"),
				valor_operacao=d("1000.00"),
				valor_bc_icms=d("1000.00"),
				valor_icms=d("175.00"),
			)
		),
	]
	bloco_c.append(montar_c990(len(bloco_c) + 1))

	# O Bloco E ainda não tem abertura/encerramento próprios implementados; a apuração
	# entra sozinha, o que é suficiente para provar a contagem do Bloco 9.
	bloco_e = [montar_e110(ApuracaoPeriodo(tributo="ICMS", debitos=d("175.00"), creditos=d("0.00")))]

	demais_blocos = bloco_0 + bloco_c + bloco_e
	contagem = Counter(linha["REG"] for linha in demais_blocos)

	return demais_blocos + montar_bloco_9(dict(contagem))


class TestArquivoCompleto(unittest.TestCase):
	def setUp(self):
		self.arquivo = _montar_arquivo()

	def test_comeca_no_0000_e_termina_no_9999(self):
		self.assertEqual(self.arquivo[0]["REG"], "0000")
		self.assertEqual(self.arquivo[-1]["REG"], "9999")

	def test_qtd_lin_do_9999_bate_com_as_linhas_reais(self):
		"""A pós-condição que só um teste de arquivo inteiro pega."""
		fim = self.arquivo[-1]

		self.assertEqual(int(fim["QTD_LIN"]), len(self.arquivo))

	def test_cada_9900_bate_com_a_contagem_real_do_arquivo(self):
		"""Confere cada linha `9900` contra a contagem de verdade — o que o PVA faz."""
		real = Counter(linha["REG"] for linha in self.arquivo)

		for linha in self.arquivo:
			if linha["REG"] != "9900":
				continue

			with self.subTest(registro=linha["REG_BLC"]):
				self.assertEqual(int(linha["QTD_REG_BLC"]), real[linha["REG_BLC"]])

	def test_todo_registro_do_arquivo_tem_linha_9900(self):
		registros = {linha["REG"] for linha in self.arquivo}
		totalizados = {linha["REG_BLC"] for linha in self.arquivo if linha["REG"] == "9900"}

		self.assertEqual(registros, totalizados)

	def test_encerramentos_de_bloco_batem_com_as_linhas_do_bloco(self):
		real = Counter(linha["REG"] for linha in self.arquivo)

		fecha_0 = next(l for l in self.arquivo if l["REG"] == "0990")
		linhas_do_bloco_0 = sum(qtd for reg, qtd in real.items() if reg.startswith("0"))

		self.assertEqual(int(fecha_0["QTD_LIN_0"]), linhas_do_bloco_0)

		fecha_c = next(l for l in self.arquivo if l["REG"] == "C990")
		linhas_do_bloco_c = sum(qtd for reg, qtd in real.items() if reg.startswith("C"))

		self.assertEqual(int(fecha_c["QTD_LIN_C"]), linhas_do_bloco_c)

	def test_serializa_em_texto_sped(self):
		texto = "\n".join(montar_linha(linha) for linha in self.arquivo)
		linhas = texto.split("\n")

		self.assertEqual(len(linhas), len(self.arquivo))
		self.assertTrue(linhas[0].startswith("|0000|"))
		self.assertTrue(linhas[-1].startswith("|9999|"))

		for linha in linhas:
			with self.subTest(linha=linha):
				self.assertTrue(linha.startswith("|"))
				self.assertTrue(linha.endswith("|"))

	def test_decimal_sai_com_virgula_no_texto(self):
		"""Confere que o valor monetário atravessa a cadeia inteira no formato do
		SPED, não em notação Python."""
		texto = "\n".join(montar_linha(linha) for linha in self.arquivo)

		self.assertIn("1000,00", texto)


if __name__ == "__main__":
	unittest.main()
