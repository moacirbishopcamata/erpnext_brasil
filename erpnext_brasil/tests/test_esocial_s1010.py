# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_s1010.py` — `ideRubrica`/`dadosRubrica` do S-1010."""

import unittest

from erpnext_brasil.folha.esocial_s1010 import (
	CODIGOS_INCIDENCIA_CP,
	CODIGOS_INCIDENCIA_CPRP,
	CODIGOS_INCIDENCIA_FGTS,
	CODIGOS_INCIDENCIA_PIS_PASEP,
	TIPO_RUBRICA_DESCONTO,
	DadosRubrica,
	EsocialS1010Invalido,
	IdeRubrica,
)


class TestIdeRubrica(unittest.TestCase):
	def test_valido(self):
		IdeRubrica(cod_rubr="9001", ide_tab_rubr="1", ini_valid="2026-01")

	def test_com_fim_valid(self):
		IdeRubrica(cod_rubr="9001", ide_tab_rubr="1", ini_valid="2026-01", fim_valid="2026-12")

	def test_cod_rubr_vazio_e_erro(self):
		with self.assertRaises(EsocialS1010Invalido):
			IdeRubrica(cod_rubr="", ide_tab_rubr="1", ini_valid="2026-01")

	def test_ini_valid_vazio_e_erro(self):
		with self.assertRaises(EsocialS1010Invalido):
			IdeRubrica(cod_rubr="9001", ide_tab_rubr="1", ini_valid="")


class TestDadosRubrica(unittest.TestCase):
	def _base(self, **overrides) -> dict:
		base = dict(
			dsc_rubr="INSS sobre salário",
			nat_rubr="1000",
			tp_rubr=TIPO_RUBRICA_DESCONTO,
			cod_inc_cp="00",
			cod_inc_irrf=1,
			cod_inc_fgts="00",
		)
		base.update(overrides)

		return base

	def test_valido_so_com_campos_obrigatorios(self):
		DadosRubrica(**self._base())

	def test_todos_os_codigos_inc_cp_sao_aceitos(self):
		for codigo in CODIGOS_INCIDENCIA_CP:
			with self.subTest(codigo=codigo):
				DadosRubrica(**self._base(cod_inc_cp=codigo))

	def test_todos_os_codigos_inc_fgts_sao_aceitos(self):
		for codigo in CODIGOS_INCIDENCIA_FGTS:
			with self.subTest(codigo=codigo):
				DadosRubrica(**self._base(cod_inc_fgts=codigo))

	def test_todos_os_codigos_inc_cprp_sao_aceitos(self):
		for codigo in CODIGOS_INCIDENCIA_CPRP:
			with self.subTest(codigo=codigo):
				DadosRubrica(**self._base(cod_inc_cprp=codigo))

	def test_todos_os_codigos_inc_pis_pasep_sao_aceitos(self):
		for codigo in CODIGOS_INCIDENCIA_PIS_PASEP:
			with self.subTest(codigo=codigo):
				DadosRubrica(**self._base(cod_inc_pis_pasep=codigo))

	def test_cod_inc_cp_fora_da_tabela_e_erro(self):
		with self.assertRaises(EsocialS1010Invalido):
			DadosRubrica(**self._base(cod_inc_cp="99"))

	def test_cod_inc_fgts_fora_da_tabela_e_erro(self):
		with self.assertRaises(EsocialS1010Invalido):
			DadosRubrica(**self._base(cod_inc_fgts="99"))

	def test_cod_inc_cprp_fora_da_tabela_e_erro(self):
		with self.assertRaises(EsocialS1010Invalido):
			DadosRubrica(**self._base(cod_inc_cprp="99"))

	def test_cod_inc_pis_pasep_fora_da_tabela_e_erro(self):
		with self.assertRaises(EsocialS1010Invalido):
			DadosRubrica(**self._base(cod_inc_pis_pasep="99"))

	def test_tp_rubr_invalido_e_erro(self):
		with self.assertRaises(EsocialS1010Invalido):
			DadosRubrica(**self._base(tp_rubr=5))

	def test_cod_inc_irrf_negativo_e_erro(self):
		with self.assertRaises(EsocialS1010Invalido):
			DadosRubrica(**self._base(cod_inc_irrf=-1))

	def test_cod_inc_irrf_acima_de_4_digitos_e_erro(self):
		with self.assertRaises(EsocialS1010Invalido):
			DadosRubrica(**self._base(cod_inc_irrf=10000))

	def test_teto_remun_valido(self):
		DadosRubrica(**self._base(teto_remun="S"))

	def test_teto_remun_invalido_e_erro(self):
		with self.assertRaises(EsocialS1010Invalido):
			DadosRubrica(**self._base(teto_remun="X"))

	def test_dsc_rubr_vazio_e_erro(self):
		with self.assertRaises(EsocialS1010Invalido):
			DadosRubrica(**self._base(dsc_rubr=""))

	def test_nat_rubr_vazio_e_erro(self):
		with self.assertRaises(EsocialS1010Invalido):
			DadosRubrica(**self._base(nat_rubr=""))


if __name__ == "__main__":
	unittest.main()
