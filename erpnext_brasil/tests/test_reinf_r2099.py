# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/reinf_r2099.py` — R-2099 (Fechamento dos Eventos Periódicos
do EFD-Reinf), a outra metade do gatilho da DCTFWeb."""

import unittest

from erpnext_brasil.contabil.reinf_r2099 import (
	AMBIENTE_PRODUCAO,
	IdeContri,
	IdeEventoFechamento,
	IdeRespInf,
	InfoFechamentoReinf,
	ReinfInvalido,
	montar_info_fech_reinf,
)


def _ide_evento(**kwargs) -> IdeEventoFechamento:
	base = {"per_apur": "2026-08", "tp_amb": AMBIENTE_PRODUCAO, "proc_emi": 1, "ver_proc": "1.0.0"}
	base.update(kwargs)
	return IdeEventoFechamento(**base)


class TestIdeEventoFechamento(unittest.TestCase):
	def test_nao_tem_ind_retif_nem_nr_recibo(self):
		"""ideEvento do R-2099 não é o mesmo tipo do R-4020 -- sem indRetif/nrRecibo."""
		evento = _ide_evento()

		self.assertFalse(hasattr(evento, "ind_retif"))
		self.assertFalse(hasattr(evento, "nr_recibo"))

	def test_per_apur_valido(self):
		_ide_evento(per_apur="2026-01")
		_ide_evento(per_apur="2026-12")

	def test_per_apur_mes_invalido_levanta_erro(self):
		with self.assertRaises(ReinfInvalido):
			_ide_evento(per_apur="2026-13")

	def test_per_apur_formato_errado_levanta_erro(self):
		with self.assertRaises(ReinfInvalido):
			_ide_evento(per_apur="2026")

	def test_tp_amb_invalido_levanta_erro(self):
		with self.assertRaises(ReinfInvalido):
			_ide_evento(tp_amb=9)


class TestIdeContriReaproveitado(unittest.TestCase):
	def test_e_o_mesmo_tipo_do_r4020(self):
		from erpnext_brasil.contabil.reinf_r4020 import IdeContri as IdeContriOriginal

		self.assertIs(IdeContri, IdeContriOriginal)

	def test_funciona_normalmente(self):
		contri = IdeContri(tp_insc=1, nr_insc="11222333000181")
		self.assertEqual(contri.nr_insc, "11222333000181")


class TestIdeRespInf(unittest.TestCase):
	def test_campos_obrigatorios(self):
		resp = IdeRespInf(nome="Fulano de Tal", cpf="11144477735")
		self.assertEqual(resp.nome, "Fulano de Tal")

	def test_cpf_invalido_levanta_erro(self):
		with self.assertRaises(ReinfInvalido):
			IdeRespInf(nome="Fulano", cpf="123")

	def test_nome_vazio_levanta_erro(self):
		with self.assertRaises(ReinfInvalido):
			IdeRespInf(nome="", cpf="11144477735")


class TestMontarInfoFechReinf(unittest.TestCase):
	def test_sem_transdctfweb(self):
		"""Achado real: o R-2099 não tem campo equivalente a transDCTFWeb do S-1299 --
		o gatilho explícito da DCTFWeb existe só do lado do eSocial."""
		info = InfoFechamentoReinf(
			servicos_tomados=True,
			servicos_prestados=False,
			recebimento_assoc_desportiva=False,
			repasse_assoc_desportiva=False,
			comercializacao_producao_rural=False,
			cprb=False,
			aquisicao_producao_rural=False,
		)

		grupo = montar_info_fech_reinf(info)

		self.assertNotIn("transDCTFWeb", grupo)
		self.assertEqual(len(grupo), 7)

	def test_todos_os_indicadores_sempre_presentes(self):
		"""Diferente do S-1299, nenhum campo de infoFech é opcional aqui -- todos os
		sete aparecem sempre, independente do valor."""
		info = InfoFechamentoReinf(
			servicos_tomados=False,
			servicos_prestados=False,
			recebimento_assoc_desportiva=False,
			repasse_assoc_desportiva=False,
			comercializacao_producao_rural=False,
			cprb=False,
			aquisicao_producao_rural=False,
		)

		grupo = montar_info_fech_reinf(info)

		for campo in (
			"evtServTm", "evtServPr", "evtAssDespRec", "evtAssDespRep",
			"evtComProd", "evtCPRB", "evtAquis",
		):
			self.assertIn(campo, grupo)
			self.assertEqual(grupo[campo], "N")

	def test_valor_true_vira_s(self):
		info = InfoFechamentoReinf(
			servicos_tomados=True,
			servicos_prestados=True,
			recebimento_assoc_desportiva=False,
			repasse_assoc_desportiva=False,
			comercializacao_producao_rural=False,
			cprb=False,
			aquisicao_producao_rural=False,
		)

		grupo = montar_info_fech_reinf(info)

		self.assertEqual(grupo["evtServTm"], "S")
		self.assertEqual(grupo["evtServPr"], "S")


if __name__ == "__main__":
	unittest.main()
