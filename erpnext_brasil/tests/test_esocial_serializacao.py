# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_serializacao.py` — a árvore de dicionário do S-1200
serializada de verdade via `fiscal/documento/serializacao.para_xml`, não só
verificada como dict solto (mesma disciplina de `test_sped_texto.py` testar contra
saída real de `montar_e110`/`montar_i050`, não contra dicionário sintético)."""

import unittest
from datetime import date
from decimal import Decimal

from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.folha.esocial_s1200 import (
	AMBIENTE_PRODUCAO,
	INDICADOR_APURACAO_MENSAL,
	DmDev,
	IdeEmpregador,
	IdeEstabLot,
	IdeEvento,
	IdeTrabalhador,
	InfoComplem,
	InfoPerApur,
	ItemRemuneracao,
	RemunPerApur,
)
from erpnext_brasil.folha.esocial_serializacao import NAMESPACE_EVT_REMUN, montar_evt_remun


def _arvore_minima() -> dict:
	ide_evento = IdeEvento(
		ind_retif=1,
		ind_apuracao=INDICADOR_APURACAO_MENSAL,
		per_apur="2026-01",
		tp_amb=AMBIENTE_PRODUCAO,
		proc_emi=1,
		ver_proc="ERPNextBrasil-1.0",
	)
	ide_empregador = IdeEmpregador(tp_insc=1, nr_insc="12345678000199")
	ide_trabalhador = IdeTrabalhador(cpf_trab="12345678901")
	item = ItemRemuneracao(cod_rubr="9001", vr_rubr=Decimal("155.68"))
	remun = RemunPerApur(itens_remun=(item,))
	estab_lot = IdeEstabLot(tp_insc=1, nr_insc="12345678000199", cod_lotacao="1", remun_per_apur=(remun,))
	dm_dev = DmDev(ide_dm_dev="1", cod_categ=101, info_per_apur=InfoPerApur(ide_estab_lot=(estab_lot,)))

	return montar_evt_remun(
		"ID1234567890123456789012345678901234", ide_evento, ide_empregador, ide_trabalhador, (dm_dev,)
	)


class TestMontarEvtRemun(unittest.TestCase):
	def test_serializa_para_xml_bem_formado(self):
		xml = para_xml(_arvore_minima())

		self.assertTrue(xml.startswith("<eSocial"))
		self.assertIn(f'xmlns="{NAMESPACE_EVT_REMUN}"', xml)
		self.assertIn('Id="ID1234567890123456789012345678901234"', xml)

	def test_lxml_analisa_sem_erro(self):
		"""Prova de bem-formação mais forte que checar substring: um parser XML de
		verdade aceita o resultado sem lançar exceção."""
		try:
			from lxml import etree
		except ImportError:
			self.skipTest("requer lxml, disponível no bench")

		xml = para_xml(_arvore_minima())
		raiz = etree.fromstring(xml.encode("utf-8"))

		self.assertEqual(etree.QName(raiz).localname, "eSocial")

	def test_valores_de_ide_evento_presentes(self):
		xml = para_xml(_arvore_minima())

		self.assertIn("<indRetif>1</indRetif>", xml)
		self.assertIn("<indApuracao>1</indApuracao>", xml)
		self.assertIn("<perApur>2026-01</perApur>", xml)

	def test_nr_recibo_ausente_e_omitido(self):
		"""`nrRecibo` é None quando indRetif=1 — `para_xml` omite valor None, a
		tag não deveria aparecer no XML final."""
		xml = para_xml(_arvore_minima())

		self.assertNotIn("<nrRecibo>", xml)

	def test_valor_da_rubrica_presente(self):
		xml = para_xml(_arvore_minima())

		self.assertIn("<codRubr>9001</codRubr>", xml)
		self.assertIn("<vrRubr>155.68</vrRubr>", xml)

	def test_info_complem_ausente_e_omitido(self):
		xml = para_xml(_arvore_minima())

		self.assertNotIn("<infoComplem>", xml)

	def test_info_complem_presente_quando_informado(self):
		ide_evento = IdeEvento(
			ind_retif=1,
			ind_apuracao=INDICADOR_APURACAO_MENSAL,
			per_apur="2026-01",
			tp_amb=AMBIENTE_PRODUCAO,
			proc_emi=1,
			ver_proc="ERPNextBrasil-1.0",
		)
		ide_empregador = IdeEmpregador(tp_insc=1, nr_insc="12345678000199")
		ide_trabalhador = IdeTrabalhador(
			cpf_trab="12345678901",
			info_complem=InfoComplem(nm_trab="Maria Silva", dt_nascto=date(1990, 5, 1), cod_cbo="252105"),
		)
		item = ItemRemuneracao(cod_rubr="9001", vr_rubr=Decimal("100.00"))
		remun = RemunPerApur(itens_remun=(item,))
		estab_lot = IdeEstabLot(
			tp_insc=1, nr_insc="12345678000199", cod_lotacao="1", remun_per_apur=(remun,)
		)
		dm_dev = DmDev(ide_dm_dev="1", cod_categ=101, info_per_apur=InfoPerApur(ide_estab_lot=(estab_lot,)))

		arvore = montar_evt_remun(
			"ID1", ide_evento, ide_empregador, ide_trabalhador, (dm_dev,)
		)
		xml = para_xml(arvore)

		self.assertIn("<nmTrab>Maria Silva</nmTrab>", xml)
		self.assertIn("<dtNascto>1990-05-01</dtNascto>", xml)

	def test_multiplos_dm_dev_viram_elementos_repetidos(self):
		ide_evento = IdeEvento(
			ind_retif=1,
			ind_apuracao=INDICADOR_APURACAO_MENSAL,
			per_apur="2026-01",
			tp_amb=AMBIENTE_PRODUCAO,
			proc_emi=1,
			ver_proc="ERPNextBrasil-1.0",
		)
		ide_empregador = IdeEmpregador(tp_insc=1, nr_insc="12345678000199")
		ide_trabalhador = IdeTrabalhador(cpf_trab="12345678901")
		item = ItemRemuneracao(cod_rubr="9001", vr_rubr=Decimal("100.00"))
		remun = RemunPerApur(itens_remun=(item,))
		estab_lot = IdeEstabLot(
			tp_insc=1, nr_insc="12345678000199", cod_lotacao="1", remun_per_apur=(remun,)
		)
		info_per_apur = InfoPerApur(ide_estab_lot=(estab_lot,))
		dm_dev_1 = DmDev(ide_dm_dev="1", cod_categ=101, info_per_apur=info_per_apur)
		dm_dev_2 = DmDev(ide_dm_dev="2", cod_categ=101, info_per_apur=info_per_apur)

		arvore = montar_evt_remun("ID1", ide_evento, ide_empregador, ide_trabalhador, (dm_dev_1, dm_dev_2))
		xml = para_xml(arvore)

		self.assertEqual(xml.count("<ideDmDev>"), 2)


if __name__ == "__main__":
	unittest.main()
