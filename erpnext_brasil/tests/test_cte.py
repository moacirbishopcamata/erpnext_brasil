# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/cte.py` — montagem do grupo `ICMSUFFim` do CT-e."""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.cte import montar_icms_uf_fim
from erpnext_brasil.fiscal.impostos.icms import calcular_difal


class TestMontarIcmsUfFim(unittest.TestCase):
	def test_delega_para_calcular_difal(self):
		"""O grupo não reimplementa a partilha — os valores batem exatamente com uma
		chamada direta a `calcular_difal` com os mesmos parâmetros."""
		esperado = calcular_difal(
			valor_operacao=Decimal("1000.00"),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			aliquota_fcp=Decimal("0.02"),
		)

		grupo = montar_icms_uf_fim(
			valor_prestacao=Decimal("1000.00"),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			aliquota_fcp=Decimal("0.02"),
		)

		self.assertEqual(grupo["vBCUFFim"], str(esperado["base_destino"]))
		self.assertEqual(grupo["vICMSUFFim"], str(esperado["difal"]))
		self.assertEqual(grupo["vICMSUFIni"], str(esperado["icms_origem"]))
		self.assertEqual(grupo["vFCPUFFim"], str(esperado["fcp"]))

	def test_nomes_de_campo_sao_os_do_xsd_do_cte_nao_os_da_nfe(self):
		"""ICMSUFFim usa vBCUFFim/pICMSUFFim/vICMSUFFim — não vBCUFDest/pICMSUFDest/
		vICMSUFDest, que são os nomes do grupo homônimo da NF-e. Confirmado por leitura
		direta do XSD (docs/cte-estado.md), não por analogia."""
		grupo = montar_icms_uf_fim(
			valor_prestacao=Decimal("500.00"),
			aliquota_interestadual=Decimal("0.07"),
			aliquota_interna_destino=Decimal("0.19"),
		)

		for campo in ("vBCUFFim", "pFCPUFFim", "pICMSUFFim", "pICMSInter", "vFCPUFFim", "vICMSUFFim", "vICMSUFIni"):
			self.assertIn(campo, grupo)

		for campo_nfe in ("vBCUFDest", "pICMSUFDest", "vICMSUFDest"):
			self.assertNotIn(campo_nfe, grupo)

	def test_sem_fcp_devolve_zero(self):
		grupo = montar_icms_uf_fim(
			valor_prestacao=Decimal("200.00"),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
		)

		self.assertEqual(grupo["vFCPUFFim"], "0.00")

	def test_base_unica_e_repassada(self):
		"""base_dupla=False muda o resultado de calcular_difal, e a mudança se propaga
		até o grupo montado — prova que o parâmetro não é ignorado silenciosamente."""
		com_base_dupla = montar_icms_uf_fim(
			valor_prestacao=Decimal("1000.00"),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			base_dupla=True,
		)
		com_base_unica = montar_icms_uf_fim(
			valor_prestacao=Decimal("1000.00"),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			base_dupla=False,
		)

		self.assertNotEqual(com_base_dupla["vBCUFFim"], com_base_unica["vBCUFFim"])


if __name__ == "__main__":
	unittest.main()
