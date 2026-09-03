# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_s1200.py` — grupos `ideEvento`, `ideEmpregador`,
`ideTrabalhador`, `TItemRemuneracao` e a árvore `DmDev`/`InfoPerApur`/`IdeEstabLot`/
`RemunPerApur` do evento S-1200, e a ponte com INSS/IRRF já calculados."""

import unittest
from datetime import date
from decimal import Decimal

from erpnext_brasil.folha.esocial_s1200 import (
	AMBIENTE_PRODUCAO,
	AMBIENTE_PRODUCAO_RESTRITA,
	INDICADOR_APURACAO_DECIMO_TERCEIRO,
	INDICADOR_APURACAO_MENSAL,
	DmDev,
	EsocialInvalido,
	IdeEmpregador,
	IdeEstabLot,
	IdeEvento,
	IdeTrabalhador,
	InfoComplem,
	InfoPerApur,
	ItemRemuneracao,
	RemunPerApur,
	linhas_de_inss_irrf,
)


def d(v: str) -> Decimal:
	return Decimal(v)


def _ide_evento_valido(**overrides) -> dict:
	base = dict(
		ind_retif=1,
		ind_apuracao=INDICADOR_APURACAO_MENSAL,
		per_apur="2026-01",
		tp_amb=AMBIENTE_PRODUCAO,
		proc_emi=1,
		ver_proc="ERPNextBrasil-1.0",
	)
	base.update(overrides)

	return base


class TestIdeEvento(unittest.TestCase):
	def test_evento_original_valido(self):
		IdeEvento(**_ide_evento_valido())

	def test_producao_restrita_e_valida(self):
		IdeEvento(**_ide_evento_valido(tp_amb=AMBIENTE_PRODUCAO_RESTRITA))

	def test_ind_retif_invalido_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeEvento(**_ide_evento_valido(ind_retif=3))

	def test_retificacao_exige_nr_recibo(self):
		with self.assertRaises(EsocialInvalido):
			IdeEvento(**_ide_evento_valido(ind_retif=2))

	def test_retificacao_com_nr_recibo_e_valida(self):
		IdeEvento(**_ide_evento_valido(ind_retif=2, nr_recibo="1.2.202601.0000000000000"))

	def test_per_apur_fora_do_tamanho_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeEvento(**_ide_evento_valido(per_apur="26"))

	def test_decimo_terceiro_exige_per_apur_so_com_o_ano(self):
		IdeEvento(**_ide_evento_valido(ind_apuracao=INDICADOR_APURACAO_DECIMO_TERCEIRO, per_apur="2026"))

	def test_decimo_terceiro_com_per_apur_mensal_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeEvento(
				**_ide_evento_valido(ind_apuracao=INDICADOR_APURACAO_DECIMO_TERCEIRO, per_apur="2026-01")
			)

	def test_mensal_com_per_apur_so_ano_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeEvento(**_ide_evento_valido(ind_apuracao=INDICADOR_APURACAO_MENSAL, per_apur="2026"))

	def test_ind_apuracao_invalido_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeEvento(**_ide_evento_valido(ind_apuracao=3))

	def test_tp_amb_invalido_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeEvento(**_ide_evento_valido(tp_amb=3))

	def test_proc_emi_fora_do_digito_unico_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeEvento(**_ide_evento_valido(proc_emi=10))

	def test_ver_proc_vazio_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeEvento(**_ide_evento_valido(ver_proc=""))


class TestIdeEmpregador(unittest.TestCase):
	def test_cnpj_valido_por_formato(self):
		IdeEmpregador(tp_insc=1, nr_insc="12345678000199")

	def test_nr_insc_curto_demais_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeEmpregador(tp_insc=1, nr_insc="1234567")

	def test_nr_insc_nao_numerico_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeEmpregador(tp_insc=1, nr_insc="1234567A000199")

	def test_tp_insc_fora_do_digito_unico_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeEmpregador(tp_insc=10, nr_insc="12345678000199")


class TestItemRemuneracao(unittest.TestCase):
	def test_valor_direto_sem_quantidade_e_valido(self):
		ItemRemuneracao(cod_rubr="1001", vr_rubr=d("500.00"))

	def test_quantidade_fator_valor_consistentes(self):
		ItemRemuneracao(
			cod_rubr="1002",
			qtd_rubr=d("10.00"),
			fator_rubr=d("1.00"),
			vr_unit=d("50.00"),
			vr_rubr=d("500.00"),
		)

	def test_quantidade_fator_valor_inconsistentes_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			ItemRemuneracao(
				cod_rubr="1002",
				qtd_rubr=d("10.00"),
				fator_rubr=d("1.00"),
				vr_unit=d("50.00"),
				vr_rubr=d("999.00"),
			)

	def test_cod_rubr_vazio_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			ItemRemuneracao(cod_rubr="", vr_rubr=d("100.00"))

	def test_ide_tab_rubr_grande_demais_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			ItemRemuneracao(cod_rubr="1001", vr_rubr=d("100.00"), ide_tab_rubr="123456789")


class TestLinhasDeInssIrrf(unittest.TestCase):
	def test_gera_duas_linhas_com_os_codigos_informados(self):
		linhas = linhas_de_inss_irrf(d("155.68"), d("0.00"), cod_rubrica_inss="9001", cod_rubrica_irrf="9002")

		self.assertEqual(len(linhas), 2)
		self.assertEqual(linhas[0].cod_rubr, "9001")
		self.assertEqual(linhas[0].vr_rubr, d("155.68"))
		self.assertEqual(linhas[1].cod_rubr, "9002")
		self.assertEqual(linhas[1].vr_rubr, d("0.00"))

	def test_valor_zero_ainda_gera_linha(self):
		linhas = linhas_de_inss_irrf(d("0.00"), d("0.00"), cod_rubrica_inss="9001", cod_rubrica_irrf="9002")

		self.assertEqual(len(linhas), 2)


class TestInfoComplem(unittest.TestCase):
	def test_valido(self):
		InfoComplem(nm_trab="Maria Silva", dt_nascto=date(1990, 5, 1), cod_cbo="252105")

	def test_nome_curto_demais_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			InfoComplem(nm_trab="M", dt_nascto=date(1990, 5, 1), cod_cbo="252105")

	def test_cbo_fora_do_tamanho_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			InfoComplem(nm_trab="Maria Silva", dt_nascto=date(1990, 5, 1), cod_cbo="12")

	def test_cbo_nao_numerico_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			InfoComplem(nm_trab="Maria Silva", dt_nascto=date(1990, 5, 1), cod_cbo="ABCDEF")


class TestIdeTrabalhador(unittest.TestCase):
	def test_so_cpf_e_valido(self):
		IdeTrabalhador(cpf_trab="12345678901")

	def test_com_info_complem(self):
		IdeTrabalhador(
			cpf_trab="12345678901",
			info_complem=InfoComplem(nm_trab="Maria Silva", dt_nascto=date(1990, 5, 1), cod_cbo="252105"),
		)

	def test_cpf_fora_do_tamanho_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeTrabalhador(cpf_trab="123")

	def test_cpf_nao_numerico_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeTrabalhador(cpf_trab="1234567890A")

	def test_nis_trab_fora_do_tamanho_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeTrabalhador(cpf_trab="12345678901", nis_trab="123")


class TestRemunPerApur(unittest.TestCase):
	def _item(self):
		return ItemRemuneracao(cod_rubr="9001", vr_rubr=Decimal("100.00"))

	def test_valido(self):
		RemunPerApur(itens_remun=(self._item(),))

	def test_sem_itens_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			RemunPerApur(itens_remun=())

	def test_mais_de_200_itens_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			RemunPerApur(itens_remun=tuple(self._item() for _ in range(201)))

	def test_matricula_vazia_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			RemunPerApur(itens_remun=(self._item(),), matricula="")


class TestIdeEstabLot(unittest.TestCase):
	def _remun(self):
		return RemunPerApur(itens_remun=(ItemRemuneracao(cod_rubr="9001", vr_rubr=Decimal("100.00")),))

	def test_valido(self):
		IdeEstabLot(tp_insc=1, nr_insc="12345678000199", cod_lotacao="1", remun_per_apur=(self._remun(),))

	def test_sem_remun_per_apur_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeEstabLot(tp_insc=1, nr_insc="12345678000199", cod_lotacao="1", remun_per_apur=())

	def test_mais_de_8_remun_per_apur_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeEstabLot(
				tp_insc=1,
				nr_insc="12345678000199",
				cod_lotacao="1",
				remun_per_apur=tuple(self._remun() for _ in range(9)),
			)

	def test_nr_insc_invalido_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			IdeEstabLot(tp_insc=1, nr_insc="123", cod_lotacao="1", remun_per_apur=(self._remun(),))


class TestInfoPerApur(unittest.TestCase):
	def _estab_lot(self):
		remun = RemunPerApur(itens_remun=(ItemRemuneracao(cod_rubr="9001", vr_rubr=Decimal("100.00")),))
		return IdeEstabLot(tp_insc=1, nr_insc="12345678000199", cod_lotacao="1", remun_per_apur=(remun,))

	def test_valido(self):
		InfoPerApur(ide_estab_lot=(self._estab_lot(),))

	def test_sem_estab_lot_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			InfoPerApur(ide_estab_lot=())

	def test_mais_de_24_estab_lot_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			InfoPerApur(ide_estab_lot=tuple(self._estab_lot() for _ in range(25)))


class TestDmDev(unittest.TestCase):
	def _info_per_apur(self):
		remun = RemunPerApur(itens_remun=(ItemRemuneracao(cod_rubr="9001", vr_rubr=Decimal("100.00")),))
		estab_lot = IdeEstabLot(tp_insc=1, nr_insc="12345678000199", cod_lotacao="1", remun_per_apur=(remun,))
		return InfoPerApur(ide_estab_lot=(estab_lot,))

	def test_valido_sem_info_per_apur(self):
		DmDev(ide_dm_dev="1", cod_categ=101)

	def test_valido_com_arvore_completa(self):
		DmDev(ide_dm_dev="1", cod_categ=101, info_per_apur=self._info_per_apur())

	def test_cod_categ_fora_de_3_digitos_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			DmDev(ide_dm_dev="1", cod_categ=99)

	def test_ide_dm_dev_vazio_e_erro(self):
		with self.assertRaises(EsocialInvalido):
			DmDev(ide_dm_dev="", cod_categ=101)


if __name__ == "__main__":
	unittest.main()
