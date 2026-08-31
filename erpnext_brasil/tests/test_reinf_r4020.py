# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/reinf_r4020.py` — EFD-Reinf R-4020."""

import unittest
from datetime import date
from decimal import Decimal

from erpnext_brasil.contabil.reinf_r4020 import (
	AMBIENTE_PRODUCAO,
	AMBIENTE_PRODUCAO_RESTRITA,
	IdeContri,
	IdeEstab,
	IdeEvento,
	InfoPgto,
	ReinfInvalido,
	Retencoes,
)


def d(v: str) -> Decimal:
	return Decimal(v)


class TestIdeEvento(unittest.TestCase):
	def _valido(self, **overrides) -> dict:
		base = dict(
			ind_retif=1, per_apur="2026-01", tp_amb=AMBIENTE_PRODUCAO, proc_emi=1, ver_proc="ERPNextBrasil-1.0"
		)
		base.update(overrides)

		return base

	def test_valido(self):
		IdeEvento(**self._valido())

	def test_producao_restrita_e_valida(self):
		IdeEvento(**self._valido(tp_amb=AMBIENTE_PRODUCAO_RESTRITA))

	def test_proc_emi_so_aceita_1_ou_2(self):
		"""Diferente de todo procEmi já visto no bloco eSocial (livre 0-9, ou
		livre-exceto-8) — aqui só 1 ou 2."""
		with self.assertRaises(ReinfInvalido):
			IdeEvento(**self._valido(proc_emi=0))

		with self.assertRaises(ReinfInvalido):
			IdeEvento(**self._valido(proc_emi=3))

	def test_retificacao_sem_recibo_e_erro(self):
		with self.assertRaises(ReinfInvalido):
			IdeEvento(**self._valido(ind_retif=2))

	def test_per_apur_fora_do_tamanho_e_erro(self):
		with self.assertRaises(ReinfInvalido):
			IdeEvento(**self._valido(per_apur="2026"))

	def test_tp_amb_invalido_e_erro(self):
		with self.assertRaises(ReinfInvalido):
			IdeEvento(**self._valido(tp_amb=3))


class TestIdeContri(unittest.TestCase):
	def test_cnpj_valido(self):
		IdeContri(tp_insc=1, nr_insc="12345678000199")

	def test_cpf_valido(self):
		IdeContri(tp_insc=2, nr_insc="12345678901")

	def test_tp_insc_invalido_e_erro(self):
		with self.assertRaises(ReinfInvalido):
			IdeContri(tp_insc=3, nr_insc="12345678000199")

	def test_nr_insc_tamanho_invalido_e_erro(self):
		with self.assertRaises(ReinfInvalido):
			IdeContri(tp_insc=1, nr_insc="123")


class TestIdeEstab(unittest.TestCase):
	def test_valido(self):
		IdeEstab(tp_insc_estab=1, nr_insc_estab="12345678000199")

	def test_terceiro_valor_e_aceito(self):
		"""tpInscEstab=3 é aceito por formato, mesmo com significado não confirmado."""
		IdeEstab(tp_insc_estab=3, nr_insc_estab="12345678000199")

	def test_tp_insc_estab_invalido_e_erro(self):
		with self.assertRaises(ReinfInvalido):
			IdeEstab(tp_insc_estab=4, nr_insc_estab="12345678000199")


class TestRetencoes(unittest.TestCase):
	def test_vazio_e_valido(self):
		"""Todos os campos são opcionais — nem todo pagamento sofre as quatro retenções."""
		Retencoes()

	def test_so_ir_informado_e_valido(self):
		Retencoes(vlr_base_ir=d("1000.00"), vlr_ir=d("15.00"))

	def test_valor_negativo_e_erro(self):
		with self.assertRaises(ReinfInvalido):
			Retencoes(vlr_ir=d("-1.00"))

	def test_todos_os_oito_campos_juntos(self):
		Retencoes(
			vlr_base_ir=d("1"), vlr_ir=d("1"),
			vlr_base_csll=d("1"), vlr_csll=d("1"),
			vlr_base_cofins=d("1"), vlr_cofins=d("1"),
			vlr_base_pp=d("1"), vlr_pp=d("1"),
		)  # fmt: skip


class TestInfoPgto(unittest.TestCase):
	def test_valido_sem_retencoes(self):
		InfoPgto(dt_fg=date(2026, 1, 15), vlr_bruto=d("1000.00"))

	def test_valido_com_retencoes(self):
		InfoPgto(
			dt_fg=date(2026, 1, 15),
			vlr_bruto=d("1000.00"),
			retencoes=Retencoes(vlr_base_ir=d("1000.00"), vlr_ir=d("15.00")),
		)

	def test_valor_bruto_negativo_e_erro(self):
		with self.assertRaises(ReinfInvalido):
			InfoPgto(dt_fg=date(2026, 1, 15), vlr_bruto=d("-1.00"))


if __name__ == "__main__":
	unittest.main()
