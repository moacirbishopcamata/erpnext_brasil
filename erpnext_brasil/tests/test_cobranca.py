# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/documento/cobranca.py` — fatura e duplicatas da NF-e.

O teste que mais importa é `test_soma_das_duplicatas_deve_fechar_com_a_fatura`: parcelar
um valor diferente do faturado é erro que o XSD aceitaria em silêncio e que só apareceria
na conciliação do contas a receber, muito depois.
"""

import unittest
from datetime import date
from decimal import Decimal as d

from erpnext_brasil.fiscal.documento.cobranca import (
	LIMITE_DE_DUPLICATAS,
	CobrancaInvalida,
	Duplicata,
	Fatura,
	montar_cobr,
)


class TestFatura(unittest.TestCase):
	def test_liquido_e_derivado(self):
		"""Aceitar o líquido por fora permitiria informar um que não fecha."""
		fatura = Fatura(original=d("1000.00"), desconto=d("100.00"))

		self.assertEqual(fatura.liquido, d("900.00"))

	def test_sem_desconto_o_liquido_e_o_original(self):
		self.assertEqual(Fatura(original=d("1000.00")).liquido, d("1000.00"))

	def test_valor_original_zero_e_erro(self):
		with self.assertRaises(CobrancaInvalida):
			Fatura(original=d("0.00"))

	def test_desconto_negativo_e_erro(self):
		with self.assertRaises(CobrancaInvalida):
			Fatura(original=d("100.00"), desconto=d("-1.00"))

	def test_desconto_maior_que_o_original_e_erro(self):
		with self.assertRaises(CobrancaInvalida):
			Fatura(original=d("100.00"), desconto=d("101.00"))

	def test_numero_longo_demais_e_erro(self):
		with self.assertRaises(CobrancaInvalida):
			Fatura(original=d("100.00"), numero="X" * 61)


class TestDuplicata(unittest.TestCase):
	def test_valida(self):
		Duplicata(vencimento=date(2026, 10, 15), valor=d("300.00"), numero="001")

	def test_valor_zero_e_erro(self):
		"""O XSD aceitaria; aqui não — parcela sem valor não cobra nada."""
		with self.assertRaises(CobrancaInvalida):
			Duplicata(vencimento=date(2026, 10, 15), valor=d("0.00"))

	def test_valor_negativo_e_erro(self):
		with self.assertRaises(CobrancaInvalida):
			Duplicata(vencimento=date(2026, 10, 15), valor=d("-10.00"))

	def test_numero_e_opcional(self):
		Duplicata(vencimento=date(2026, 10, 15), valor=d("300.00"))


class TestMontarCobr(unittest.TestCase):
	def _tres_parcelas(self) -> list[Duplicata]:
		return [
			Duplicata(vencimento=date(2026, 10, 15), valor=d("300.00"), numero="001"),
			Duplicata(vencimento=date(2026, 11, 15), valor=d("300.00"), numero="002"),
			Duplicata(vencimento=date(2026, 12, 15), valor=d("300.00"), numero="003"),
		]

	def test_venda_em_tres_vezes(self):
		grupo = montar_cobr(Fatura(original=d("900.00"), numero="FAT-1"), self._tres_parcelas())

		self.assertEqual(grupo["cobr"]["fat"]["vLiq"], d("900.00"))
		self.assertEqual(len(grupo["cobr"]["dup"]), 3)

	def test_ordem_dos_campos_da_fatura(self):
		"""`fat` antes de `dup`, e dentro de `fat` a ordem do XSD."""
		grupo = montar_cobr(
			Fatura(original=d("1000.00"), desconto=d("100.00"), numero="FAT-1"), self._tres_parcelas()
		)

		self.assertEqual(list(grupo["cobr"]), ["fat", "dup"])
		self.assertEqual(list(grupo["cobr"]["fat"]), ["nFat", "vOrig", "vDesc", "vLiq"])

	def test_desconto_omitido_quando_zero(self):
		"""Tag vazia é rejeição, não omissão — mesma regra da serialização."""
		grupo = montar_cobr(Fatura(original=d("900.00")), self._tres_parcelas())

		self.assertNotIn("vDesc", grupo["cobr"]["fat"])

	def test_campos_da_duplicata(self):
		grupo = montar_cobr(duplicatas=self._tres_parcelas())
		primeira = grupo["cobr"]["dup"][0]

		self.assertEqual(list(primeira), ["nDup", "dVenc", "vDup"])
		self.assertEqual(primeira["dVenc"], "2026-10-15")
		self.assertEqual(primeira["vDup"], d("300.00"))

	def test_vencimento_sai_no_formato_do_xsd(self):
		"""`TData` é AAAA-MM-DD, não o formato brasileiro."""
		grupo = montar_cobr(duplicatas=[Duplicata(vencimento=date(2026, 3, 7), valor=d("10.00"))])

		self.assertEqual(grupo["cobr"]["dup"][0]["dVenc"], "2026-03-07")

	def test_soma_das_duplicatas_deve_fechar_com_a_fatura(self):
		"""Parcelar R$ 1.000 em três de R$ 300 — o XSD aceitaria em silêncio."""
		with self.assertRaises(CobrancaInvalida):
			montar_cobr(Fatura(original=d("1000.00")), self._tres_parcelas())

	def test_soma_fecha_considerando_o_desconto(self):
		"""O que as parcelas somam é o líquido, não o original."""
		montar_cobr(Fatura(original=d("1000.00"), desconto=d("100.00")), self._tres_parcelas())

	def test_so_duplicatas_sem_fatura_e_valido(self):
		"""`fat` é opcional no XSD, e há emissor que só declara as parcelas."""
		montar_cobr(duplicatas=self._tres_parcelas())

	def test_so_fatura_sem_duplicatas_e_valido(self):
		"""Venda faturada à vista: há fatura, não há parcelamento."""
		grupo = montar_cobr(Fatura(original=d("900.00")))

		self.assertNotIn("dup", grupo["cobr"])

	def test_cobranca_vazia_e_erro(self):
		with self.assertRaises(CobrancaInvalida):
			montar_cobr()

	def test_limite_de_120_duplicatas(self):
		"""`maxOccurs="120"` no XSD — não é invenção deste módulo."""
		muitas = [
			Duplicata(vencimento=date(2026, 10, 15), valor=d("1.00")) for _ in range(LIMITE_DE_DUPLICATAS + 1)
		]

		with self.assertRaises(CobrancaInvalida):
			montar_cobr(duplicatas=muitas)

	def test_exatamente_120_duplicatas_e_valido(self):
		montar_cobr(
			duplicatas=[
				Duplicata(vencimento=date(2026, 10, 15), valor=d("1.00")) for _ in range(LIMITE_DE_DUPLICATAS)
			]
		)


if __name__ == "__main__":
	unittest.main()
