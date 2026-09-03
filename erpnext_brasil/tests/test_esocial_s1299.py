# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_s1299.py` — S-1299 (Fechamento dos Eventos Periódicos).

O teste que mais importa é `test_ide_evento_fechamento_nao_tem_ind_retif`: confirma
que `IdeEventoFechamento` não é `esocial_s1200.IdeEvento` reaproveitado por engano —
são tipos genuinamente diferentes no XSD (`docs/rh-esocial-s1299.md`).
"""

import unittest

from erpnext_brasil.folha.esocial_s1200 import (
	AMBIENTE_PRODUCAO,
	INDICADOR_APURACAO_DECIMO_TERCEIRO,
	INDICADOR_APURACAO_MENSAL,
	EsocialInvalido,
)
from erpnext_brasil.folha.esocial_s1299 import (
	INDICADOR_GUIA_DAE,
	IdeEventoFechamento,
	InfoFechamento,
	montar_info_fech,
)


def _ide_evento(**kwargs) -> IdeEventoFechamento:
	base = {
		"ind_apuracao": INDICADOR_APURACAO_MENSAL,
		"per_apur": "2026-08",
		"tp_amb": AMBIENTE_PRODUCAO,
		"proc_emi": 1,
		"ver_proc": "1.0.0",
	}
	base.update(kwargs)
	return IdeEventoFechamento(**base)


class TestIdeEventoFechamento(unittest.TestCase):
	def test_ide_evento_fechamento_nao_tem_ind_retif(self):
		"""T_ideEvento_folha_sem_retificacao não tem indRetif/nrRecibo -- diferente de
		esocial_s1200.IdeEvento, que tem os dois."""
		self.assertFalse(hasattr(_ide_evento(), "ind_retif"))
		self.assertFalse(hasattr(_ide_evento(), "nr_recibo"))

	def test_per_apur_mensal_precisa_de_7_caracteres(self):
		with self.assertRaises(EsocialInvalido):
			_ide_evento(per_apur="2026")

	def test_per_apur_decimo_terceiro_precisa_de_4_caracteres(self):
		evento = _ide_evento(ind_apuracao=INDICADOR_APURACAO_DECIMO_TERCEIRO, per_apur="2026")
		self.assertEqual(evento.per_apur, "2026")

		with self.assertRaises(EsocialInvalido):
			_ide_evento(ind_apuracao=INDICADOR_APURACAO_DECIMO_TERCEIRO, per_apur="2026-08")

	def test_ind_guia_aceita_dae(self):
		evento = _ide_evento(ind_guia=INDICADOR_GUIA_DAE)
		self.assertEqual(evento.ind_guia, INDICADOR_GUIA_DAE)

	def test_ind_guia_none_e_valido(self):
		_ide_evento(ind_guia=None)

	def test_ind_guia_com_valor_desconhecido_levanta_erro(self):
		"""Só existe um valor definido no leiaute hoje -- ver docstring do módulo."""
		with self.assertRaises(EsocialInvalido):
			_ide_evento(ind_guia=2)


class TestMontarInfoFech(unittest.TestCase):
	def test_indicadores_obrigatorios(self):
		info = InfoFechamento(
			evt_remun=True,
			evt_pgtos=False,
			evt_com_prod=False,
			evt_contrat_av_np=False,
			evt_info_compl_per=False,
		)

		grupo = montar_info_fech(info)

		self.assertEqual(grupo["evtRemun"], "S")
		self.assertEqual(grupo["evtPgtos"], "N")

	def test_campos_opcionais_ausentes_por_padrao(self):
		info = InfoFechamento(
			evt_remun=True,
			evt_pgtos=False,
			evt_com_prod=False,
			evt_contrat_av_np=False,
			evt_info_compl_per=False,
		)

		grupo = montar_info_fech(info)

		self.assertNotIn("indExcApur1250", grupo)
		self.assertNotIn("transDCTFWeb", grupo)
		self.assertNotIn("naoValid", grupo)

	def test_trans_dctfweb_e_o_gatilho_da_declaracao(self):
		"""O campo que efetivamente dispara a geração da DCTFWeb -- não um arquivo
		separado, ver docstring do módulo."""
		info = InfoFechamento(
			evt_remun=True,
			evt_pgtos=False,
			evt_com_prod=False,
			evt_contrat_av_np=False,
			evt_info_compl_per=False,
			trans_dctfweb=True,
		)

		grupo = montar_info_fech(info)

		self.assertEqual(grupo["transDCTFWeb"], "S")

	def test_nao_valid_false_aparece_explicitamente(self):
		"""None e True têm o mesmo efeito no XSD -- só False (\"N\") precisa aparecer
		de fato para executar a regra de validação."""
		info = InfoFechamento(
			evt_remun=True,
			evt_pgtos=False,
			evt_com_prod=False,
			evt_contrat_av_np=False,
			evt_info_compl_per=False,
			nao_valid=False,
		)

		grupo = montar_info_fech(info)

		self.assertEqual(grupo["naoValid"], "N")

	def test_nao_valid_none_nao_aparece(self):
		info = InfoFechamento(
			evt_remun=True,
			evt_pgtos=False,
			evt_com_prod=False,
			evt_contrat_av_np=False,
			evt_info_compl_per=False,
		)

		self.assertNotIn("naoValid", montar_info_fech(info))


if __name__ == "__main__":
	unittest.main()
