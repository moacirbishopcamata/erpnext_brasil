# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_s2299.py` — S-2299 (Desligamento de Trabalhador)."""

import unittest
from datetime import date
from decimal import Decimal

from erpnext_brasil.folha.esocial_s1200 import DmDev, IdeEstabLot, InfoPerApur, ItemRemuneracao, RemunPerApur
from erpnext_brasil.folha.esocial_s2299 import EsocialS2299Invalido, IdeEvento, InfoDeslig, VerbasResc


class TestIdeEvento(unittest.TestCase):
	def _valido(self, **overrides) -> dict:
		base = dict(ind_retif=1, proc_emi=1, ver_proc="ERPNextBrasil-1.0", tp_amb=1)
		base.update(overrides)

		return base

	def test_valido(self):
		IdeEvento(**self._valido())

	def test_proc_emi_8_e_aceito_neste_evento(self):
		"""Diferente do S-2200: aqui procEmi é o tipo genérico (livre), não
		TS_procEmi_sem_8 — 8 é um valor válido."""
		IdeEvento(**self._valido(proc_emi=8))

	def test_com_ind_guia(self):
		IdeEvento(**self._valido(ind_guia="1"))

	def test_retificacao_sem_recibo_e_erro(self):
		with self.assertRaises(EsocialS2299Invalido):
			IdeEvento(**self._valido(ind_retif=2))

	def test_tp_amb_invalido_e_erro(self):
		with self.assertRaises(EsocialS2299Invalido):
			IdeEvento(**self._valido(tp_amb=3))


class TestInfoDeslig(unittest.TestCase):
	def test_valido(self):
		InfoDeslig(mtv_deslig="01", dt_deslig=date(2026, 6, 30), ind_pagto_api="S")

	def test_com_dt_proj_fim_api(self):
		InfoDeslig(
			mtv_deslig="01", dt_deslig=date(2026, 6, 30), ind_pagto_api="S", dt_proj_fim_api=date(2026, 7, 10)
		)

	def test_mtv_deslig_fora_do_tamanho_e_erro(self):
		with self.assertRaises(EsocialS2299Invalido):
			InfoDeslig(mtv_deslig="1", dt_deslig=date(2026, 6, 30), ind_pagto_api="S")

	def test_mtv_deslig_nao_numerico_e_erro(self):
		with self.assertRaises(EsocialS2299Invalido):
			InfoDeslig(mtv_deslig="AB", dt_deslig=date(2026, 6, 30), ind_pagto_api="S")

	def test_ind_pagto_api_invalido_e_erro(self):
		with self.assertRaises(EsocialS2299Invalido):
			InfoDeslig(mtv_deslig="01", dt_deslig=date(2026, 6, 30), ind_pagto_api="X")


class TestVerbasResc(unittest.TestCase):
	def _dm_dev(self) -> DmDev:
		item = ItemRemuneracao(cod_rubr="9001", vr_rubr=Decimal("500.00"))
		remun = RemunPerApur(itens_remun=(item,))
		estab_lot = IdeEstabLot(tp_insc=1, nr_insc="12345678000199", cod_lotacao="1", remun_per_apur=(remun,))
		return DmDev(ide_dm_dev="1", cod_categ=101, info_per_apur=InfoPerApur(ide_estab_lot=(estab_lot,)))

	def test_valido_reaproveita_dm_dev_do_s1200(self):
		"""Prova que VerbasResc usa o mesmo DmDev de esocial_s1200.py, não uma
		cópia — instância criada com aquele módulo é aceita direto aqui."""
		VerbasResc(dm_dev=(self._dm_dev(),))

	def test_vazio_e_valido(self):
		"""dmDev tem minOccurs=0 dentro de verbasResc."""
		VerbasResc(dm_dev=())

	def test_mais_de_50_dm_dev_e_erro(self):
		with self.assertRaises(EsocialS2299Invalido):
			VerbasResc(dm_dev=tuple(self._dm_dev() for _ in range(51)))


if __name__ == "__main__":
	unittest.main()
