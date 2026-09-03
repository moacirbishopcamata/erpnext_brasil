# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_s1000.py` — evtInfoEmpregador (S-1000)."""

import unittest

from erpnext_brasil.folha.esocial_s1000 import (
	EsocialS1000Invalido,
	IdeEmpregador,
	IdeEvento,
	IdePeriodo,
	InfoCadastro,
	montar_alteracao,
	montar_evento_s1000,
	montar_exclusao,
	montar_inclusao,
)


class TestIdeEvento(unittest.TestCase):
	def test_valido(self):
		IdeEvento(tp_amb=2, proc_emi=1, ver_proc="1.0")

	def test_tp_amb_invalido_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			IdeEvento(tp_amb=7, proc_emi=1, ver_proc="1.0")

	def test_proc_emi_fora_de_faixa_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			IdeEvento(tp_amb=2, proc_emi=10, ver_proc="1.0")

	def test_ver_proc_vazio_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			IdeEvento(tp_amb=2, proc_emi=1, ver_proc="")


class TestIdeEmpregador(unittest.TestCase):
	def test_valido_cnpj(self):
		IdeEmpregador(tp_insc=1, nr_insc="12345678")

	def test_tp_insc_invalido_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			IdeEmpregador(tp_insc=3, nr_insc="12345678")

	def test_nr_insc_vazio_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			IdeEmpregador(tp_insc=1, nr_insc="")


class TestIdePeriodo(unittest.TestCase):
	def test_valido_so_inicio(self):
		IdePeriodo(ini_valid="2026-01")

	def test_valido_com_fim(self):
		IdePeriodo(ini_valid="2026-01", fim_valid="2026-12")

	def test_ini_valid_fora_do_formato_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			IdePeriodo(ini_valid="2026")

	def test_fim_valid_fora_do_formato_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			IdePeriodo(ini_valid="2026-01", fim_valid="2026")


class TestInfoCadastro(unittest.TestCase):
	def _base(self, **overrides) -> dict:
		base = dict(class_trib="03", ind_des_folha=0, ind_opt_reg_eletron=1)
		base.update(overrides)
		return base

	def test_valido_so_com_campos_obrigatorios(self):
		InfoCadastro(**self._base())

	def test_valido_com_opcionais(self):
		InfoCadastro(**self._base(ind_coop=0, ind_constr=0, ind_porte="S", ind_pert_irrf="S"))

	def test_class_trib_fora_do_formato_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			InfoCadastro(**self._base(class_trib="3"))

	def test_ind_des_folha_invalido_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			InfoCadastro(**self._base(ind_des_folha=9))

	def test_ind_opt_reg_eletron_invalido_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			InfoCadastro(**self._base(ind_opt_reg_eletron=2))

	def test_ind_coop_invalido_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			InfoCadastro(**self._base(ind_coop=9))

	def test_ind_constr_invalido_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			InfoCadastro(**self._base(ind_constr=9))

	def test_ind_opc_cp_invalido_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			InfoCadastro(**self._base(ind_opc_cp=9))

	def test_ind_porte_diferente_de_s_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			InfoCadastro(**self._base(ind_porte="N"))

	def test_cnpj_efr_fora_do_formato_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			InfoCadastro(**self._base(cnpj_efr="123"))

	def test_ind_trib_folha_pis_pasep_diferente_de_s_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			InfoCadastro(**self._base(ind_trib_folha_pis_pasep="N"))

	def test_ind_pert_irrf_diferente_de_s_e_erro(self):
		with self.assertRaises(EsocialS1000Invalido):
			InfoCadastro(**self._base(ind_pert_irrf="N"))


class TestMontarOperacoes(unittest.TestCase):
	def test_montar_inclusao_com_info_cadastro(self):
		periodo = IdePeriodo(ini_valid="2026-01")
		info = InfoCadastro(class_trib="03", ind_des_folha=0, ind_opt_reg_eletron=1)

		resultado = montar_inclusao(periodo, info)

		self.assertEqual(resultado["inclusao"]["idePeriodo"]["iniValid"], "2026-01")
		self.assertEqual(resultado["inclusao"]["infoCadastro"]["classTrib"], "03")
		self.assertNotIn("fimValid", resultado["inclusao"]["idePeriodo"])

	def test_montar_inclusao_sem_info_cadastro(self):
		resultado = montar_inclusao(IdePeriodo(ini_valid="2026-01"))

		self.assertNotIn("infoCadastro", resultado["inclusao"])

	def test_montar_alteracao_com_nova_validade(self):
		periodo = IdePeriodo(ini_valid="2026-01")
		nova = IdePeriodo(ini_valid="2026-02")

		resultado = montar_alteracao(periodo, nova_validade=nova)

		self.assertEqual(resultado["alteracao"]["novaValidade"]["iniValid"], "2026-02")

	def test_montar_exclusao_nao_tem_info_cadastro(self):
		resultado = montar_exclusao(IdePeriodo(ini_valid="2026-01", fim_valid="2026-06"))

		self.assertEqual(resultado["exclusao"]["idePeriodo"]["fimValid"], "2026-06")
		self.assertNotIn("infoCadastro", resultado["exclusao"])


class TestMontarEventoS1000(unittest.TestCase):
	def test_estrutura_completa(self):
		ide_evento = IdeEvento(tp_amb=2, proc_emi=1, ver_proc="1.0")
		ide_empregador = IdeEmpregador(tp_insc=1, nr_insc="12345678")
		info_empregador = montar_inclusao(
			IdePeriodo(ini_valid="2026-01"),
			InfoCadastro(class_trib="03", ind_des_folha=0, ind_opt_reg_eletron=1),
		)

		evento = montar_evento_s1000(
			"ID11234567890123456789012345678901", ide_evento, ide_empregador, info_empregador
		)

		raiz = evento["eSocial"]["evtInfoEmpregador"]
		self.assertEqual(raiz["Id"], "ID11234567890123456789012345678901")
		self.assertEqual(raiz["ideEvento"]["tpAmb"], 2)
		self.assertEqual(raiz["ideEmpregador"]["nrInsc"], "12345678")
		self.assertEqual(raiz["infoEmpregador"]["inclusao"]["infoCadastro"]["classTrib"], "03")


if __name__ == "__main__":
	unittest.main()
