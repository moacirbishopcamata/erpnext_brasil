# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/cte.py` — montagem dos grupos `ICMSUFFim` e `infDoc/infNFe` do CT-e."""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.cte import montar_icms_uf_fim, montar_infnfe
from erpnext_brasil.fiscal.documento.chave_acesso import ChaveInvalida, montar_chave
from erpnext_brasil.fiscal.impostos.icms import calcular_difal


def _chave_nfe(numero: str = "000000001") -> str:
	return montar_chave(
		uf="35",
		ano_mes="2608",
		cnpj="11222333000181",
		modelo="55",
		serie="001",
		numero=numero,
		tipo_emissao="1",
		codigo_numerico="12345678",
	)


def _chave_cte(numero: str = "000000001") -> str:
	return montar_chave(
		uf="35",
		ano_mes="2608",
		cnpj="11222333000181",
		modelo="57",
		serie="001",
		numero=numero,
		tipo_emissao="1",
		codigo_numerico="12345678",
	)


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


class TestMontarInfnfe(unittest.TestCase):
	def test_uma_chave(self):
		chave = _chave_nfe()

		grupo = montar_infnfe([chave])

		self.assertEqual(grupo, [{"chave": chave}])

	def test_varias_chaves_preserva_ordem(self):
		chave_1 = _chave_nfe("000000001")
		chave_2 = _chave_nfe("000000002")

		grupo = montar_infnfe([chave_1, chave_2])

		self.assertEqual(grupo, [{"chave": chave_1}, {"chave": chave_2}])

	def test_lista_vazia_devolve_lista_vazia(self):
		self.assertEqual(montar_infnfe([]), [])

	def test_chave_invalida_levanta_erro(self):
		with self.assertRaises(ChaveInvalida):
			montar_infnfe(["0" * 43 + "9"])  # DV errado

	def test_recusa_chave_que_nao_e_de_nfe(self):
		"""infDoc/infNFe só aceita NF-e (modelo 55) — colar por engano a chave de outro
		CT-e (modelo 57) tem que falhar aqui, não só na rejeição da SEFAZ."""
		with self.assertRaises(ChaveInvalida):
			montar_infnfe([_chave_cte()])


if __name__ == "__main__":
	unittest.main()
