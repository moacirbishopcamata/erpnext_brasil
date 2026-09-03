# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_s2200.py` — S-2200 (Admissão de Trabalhador)."""

import unittest
from datetime import date
from decimal import Decimal

from erpnext_brasil.folha.esocial_s2200 import (
	INDICADOR_ADMISSAO_NORMAL,
	TIPO_ADMISSAO_ADMISSAO,
	EsocialS2200Invalido,
	IdeEvento,
	InfoCeletista,
	InfoContrato,
	Trabalhador,
	Vinculo,
)


class TestIdeEvento(unittest.TestCase):
	def _valido(self, **overrides) -> dict:
		base = dict(ind_retif=1, proc_emi=1, ver_proc="ERPNextBrasil-1.0", tp_amb=1)
		base.update(overrides)

		return base

	def test_valido(self):
		IdeEvento(**self._valido())

	def test_proc_emi_8_e_erro_neste_evento(self):
		"""Diferente do S-1200: TS_procEmi_sem_8 exclui explicitamente o valor 8."""
		with self.assertRaises(EsocialS2200Invalido):
			IdeEvento(**self._valido(proc_emi=8))

	def test_proc_emi_outros_digitos_sao_aceitos(self):
		for digito in (0, 1, 2, 7, 9):
			with self.subTest(digito=digito):
				IdeEvento(**self._valido(proc_emi=digito))

	def test_sem_periodicidade_no_construtor(self):
		"""Não deve aceitar per_apur/ind_apuracao — este evento não é periódico."""
		with self.assertRaises(TypeError):
			IdeEvento(**self._valido(), per_apur="2026-01")

	def test_retificacao_sem_recibo_e_erro(self):
		with self.assertRaises(EsocialS2200Invalido):
			IdeEvento(**self._valido(ind_retif=2))

	def test_tp_amb_invalido_e_erro(self):
		with self.assertRaises(EsocialS2200Invalido):
			IdeEvento(**self._valido(tp_amb=3))


class TestTrabalhador(unittest.TestCase):
	def test_valido(self):
		Trabalhador(cpf_trab="12345678901", nm_trab="Maria Silva", sexo=1, raca_cor=1, grau_instr=1)

	def test_cpf_invalido_e_erro(self):
		with self.assertRaises(EsocialS2200Invalido):
			Trabalhador(cpf_trab="123", nm_trab="Maria Silva", sexo=1, raca_cor=1, grau_instr=1)

	def test_nome_vazio_e_erro(self):
		with self.assertRaises(EsocialS2200Invalido):
			Trabalhador(cpf_trab="12345678901", nm_trab="", sexo=1, raca_cor=1, grau_instr=1)


class TestVinculo(unittest.TestCase):
	def test_valido(self):
		Vinculo(matricula="1", tp_reg_trab=1, tp_reg_prev=1, cad_ini="N")

	def test_tp_reg_prev_invalido_e_erro(self):
		with self.assertRaises(EsocialS2200Invalido):
			Vinculo(matricula="1", tp_reg_trab=1, tp_reg_prev=5, cad_ini="N")

	def test_cad_ini_invalido_e_erro(self):
		with self.assertRaises(EsocialS2200Invalido):
			Vinculo(matricula="1", tp_reg_trab=1, tp_reg_prev=1, cad_ini="X")


class TestInfoCeletista(unittest.TestCase):
	def test_valido(self):
		InfoCeletista(
			dt_adm=date(2026, 1, 15),
			tp_admissao=TIPO_ADMISSAO_ADMISSAO,
			ind_admissao=INDICADOR_ADMISSAO_NORMAL,
			cnpj_sind_categ_prof="12345678000199",
		)

	def test_todos_os_tipos_admissao_1_a_7_sao_aceitos(self):
		for tipo in range(1, 8):
			with self.subTest(tipo=tipo):
				InfoCeletista(
					dt_adm=date(2026, 1, 15),
					tp_admissao=tipo,
					ind_admissao=INDICADOR_ADMISSAO_NORMAL,
					cnpj_sind_categ_prof="12345678000199",
				)

	def test_tipo_admissao_fora_da_faixa_e_erro(self):
		with self.assertRaises(EsocialS2200Invalido):
			InfoCeletista(
				dt_adm=date(2026, 1, 15),
				tp_admissao=8,
				ind_admissao=INDICADOR_ADMISSAO_NORMAL,
				cnpj_sind_categ_prof="12345678000199",
			)

	def test_ind_admissao_fora_da_faixa_e_erro(self):
		with self.assertRaises(EsocialS2200Invalido):
			InfoCeletista(
				dt_adm=date(2026, 1, 15),
				tp_admissao=TIPO_ADMISSAO_ADMISSAO,
				ind_admissao=4,
				cnpj_sind_categ_prof="12345678000199",
			)

	def test_cnpj_sind_categ_prof_invalido_e_erro(self):
		with self.assertRaises(EsocialS2200Invalido):
			InfoCeletista(
				dt_adm=date(2026, 1, 15),
				tp_admissao=TIPO_ADMISSAO_ADMISSAO,
				ind_admissao=INDICADOR_ADMISSAO_NORMAL,
				cnpj_sind_categ_prof="123",
			)


class TestInfoContrato(unittest.TestCase):
	def test_valido(self):
		InfoContrato(
			cod_categ=101,
			nm_cargo="Analista",
			valor_salario=Decimal("3000.00"),
			unid_sal_fixo=1,
			tp_salario=1,
		)

	def test_cod_categ_fora_de_3_digitos_e_erro(self):
		with self.assertRaises(EsocialS2200Invalido):
			InfoContrato(
				cod_categ=99,
				nm_cargo="Analista",
				valor_salario=Decimal("3000.00"),
				unid_sal_fixo=1,
				tp_salario=1,
			)

	def test_salario_negativo_e_erro(self):
		with self.assertRaises(EsocialS2200Invalido):
			InfoContrato(
				cod_categ=101,
				nm_cargo="Analista",
				valor_salario=Decimal("-1.00"),
				unid_sal_fixo=1,
				tp_salario=1,
			)


if __name__ == "__main__":
	unittest.main()
