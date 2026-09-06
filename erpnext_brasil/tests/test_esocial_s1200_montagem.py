# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Montagem da árvore do S-1200 — o evento da folha.

O buraco que estes testes cobrem: o S-1000 tinha `montar_evento_s1000` desde o início, e o
S-1200 — o evento **mais transmitido** do eSocial — só tinha as dataclasses. Dava para
validar cada grupo e não dava para produzir o evento.

Teste-âncora: `test_o_ide_evento_do_s1200_e_maior_que_o_do_s1000`. Copiar a montagem do
S-1000 e trocar o nome da raiz produziria um `evtRemun` **sem período** — aceito pelo
serializador, recusado pelo eSocial. É a analogia entre eventos irmãos que este projeto
trata como o erro mais caro.

Módulo puro: roda sem bench.
"""

import unittest
from datetime import date
from decimal import Decimal

from erpnext_brasil.folha.esocial_s1200 import (
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
	montar_evento_s1200,
)

ID_EVENTO = "ID1234567890123456789012345678901234"
CNPJ = "12345678000199"


def _dm_dev(itens=None) -> DmDev:
	itens = itens or (ItemRemuneracao(cod_rubr="1001", vr_rubr=Decimal("3000.00")),)

	return DmDev(
		ide_dm_dev="FOLHA-08",
		cod_categ=101,
		info_per_apur=InfoPerApur(
			ide_estab_lot=(
				IdeEstabLot(
					tp_insc=1,
					nr_insc=CNPJ,
					cod_lotacao="1",
					remun_per_apur=(RemunPerApur(itens_remun=itens),),
				),
			)
		),
	)


def _evento(**mudancas) -> dict:
	base = {
		"id_evento": ID_EVENTO,
		"ide_evento": IdeEvento(
			ind_retif=1, ind_apuracao=1, per_apur="2026-08", tp_amb=2, proc_emi=1, ver_proc="1.0"
		),
		"ide_empregador": IdeEmpregador(tp_insc=1, nr_insc=CNPJ),
		"ide_trabalhador": IdeTrabalhador(cpf_trab="12345678901"),
		"dm_dev": (_dm_dev(),),
	}
	base.update(mudancas)

	return montar_evento_s1200(**base)


def _evt(arvore: dict) -> dict:
	return arvore["eSocial"]["evtRemun"]


class TestRaiz(unittest.TestCase):
	def test_a_raiz_e_evtremun_dentro_de_esocial(self):
		arvore = _evento()

		self.assertEqual(["eSocial"], list(arvore))
		self.assertEqual(["evtRemun"], list(arvore["eSocial"]))

	def test_o_id_vai_como_atributo_do_evento(self):
		self.assertEqual(ID_EVENTO, _evt(_evento())["Id"])

	def test_a_ordem_dos_grupos_e_a_do_leiaute(self):
		"""O XML do eSocial é `xs:sequence`: grupo fora de ordem é rejeição."""
		self.assertEqual(
			["Id", "ideEvento", "ideEmpregador", "ideTrabalhador", "dmDev"],
			list(_evt(_evento())),
		)


class TestIdeEvento(unittest.TestCase):
	def test_o_ide_evento_do_s1200_e_maior_que_o_do_s1000(self):
		"""Teste-âncora: o do S-1000 tem três campos; um evento de folha é **de um
		período** e pode ser retificação, então tem `indRetif`, `indApuracao` e `perApur`
		que o de cadastro do empregador não tem."""
		ide = _evt(_evento())["ideEvento"]

		for campo in ("indRetif", "indApuracao", "perApur", "tpAmb", "procEmi", "verProc"):
			with self.subTest(campo=campo):
				self.assertIn(campo, ide)

	def test_a_ordem_dentro_do_ide_evento(self):
		self.assertEqual(
			["indRetif", "indApuracao", "perApur", "tpAmb", "procEmi", "verProc"],
			list(_evt(_evento())["ideEvento"]),
		)

	def test_o_nr_recibo_nao_aparece_no_evento_original(self):
		"""Ausente é diferente de vazio: um `<nrRecibo/>` vazio é rejeitado."""
		self.assertNotIn("nrRecibo", _evt(_evento())["ideEvento"])

	def test_a_retificacao_carrega_o_recibo_logo_apos_o_indicador(self):
		arvore = _evento(
			ide_evento=IdeEvento(
				ind_retif=2,
				nr_recibo="1.2.3456789012345",
				ind_apuracao=1,
				per_apur="2026-08",
				tp_amb=2,
				proc_emi=1,
				ver_proc="1.0",
			)
		)
		ide = _evt(arvore)["ideEvento"]

		self.assertEqual("1.2.3456789012345", ide["nrRecibo"])
		self.assertEqual(["indRetif", "nrRecibo", "indApuracao"], list(ide)[:3])


class TestTrabalhador(unittest.TestCase):
	def test_campos_opcionais_ausentes_nao_viram_chave_vazia(self):
		trabalhador = _evt(_evento())["ideTrabalhador"]

		self.assertEqual(["cpfTrab"], list(trabalhador))

	def test_info_complem_entra_com_a_data_no_formato_do_esocial(self):
		"""`AAAA-MM-DD`, com hífen — diferente do SPED, que usa `DDMMAAAA` sem separador.
		Dois formatos de data no mesmo projeto, e trocá-los é rejeição que não diz qual
		campo está errado."""
		arvore = _evento(
			ide_trabalhador=IdeTrabalhador(
				cpf_trab="12345678901",
				nis_trab="12345678901",
				info_complem=InfoComplem(
					nm_trab="Fulano de Tal", dt_nascto=date(1990, 3, 7), cod_cbo="252305"
				),
			)
		)
		complem = _evt(arvore)["ideTrabalhador"]["infoComplem"]

		self.assertEqual("1990-03-07", complem["dtNascto"])
		self.assertEqual("Fulano de Tal", complem["nmTrab"])
		self.assertNotIn("natAtividade", complem)


class TestDemonstrativos(unittest.TestCase):
	def test_dm_dev_e_lista_porque_o_leiaute_admite_varios(self):
		arvore = _evento(dm_dev=(_dm_dev(), _dm_dev()))

		self.assertEqual(2, len(_evt(arvore)["dmDev"]))

	def test_evento_sem_demonstrativo_e_recusado(self):
		"""Um `evtRemun` sem `dmDev` não declara remuneração nenhuma."""
		with self.assertRaises(EsocialInvalido):
			_evento(dm_dev=())

	def test_a_remuneracao_chega_ate_as_linhas(self):
		item = _evt(_evento())["dmDev"][0]["infoPerApur"]["ideEstabLot"][0]["remunPerApur"][0]["itensRemun"][
			0
		]

		self.assertEqual("1001", item["codRubr"])
		self.assertEqual(Decimal("3000.00"), item["vrRubr"])

	def test_o_valor_continua_decimal_ate_a_serializacao(self):
		"""Converter para float aqui traria o erro binário para dentro da folha."""
		item = _evt(_evento())["dmDev"][0]["infoPerApur"]["ideEstabLot"][0]["remunPerApur"][0]["itensRemun"][
			0
		]

		self.assertIsInstance(item["vrRubr"], Decimal)

	def test_os_opcionais_da_linha_nao_aparecem_quando_ausentes(self):
		item = _evt(_evento())["dmDev"][0]["infoPerApur"]["ideEstabLot"][0]["remunPerApur"][0]["itensRemun"][
			0
		]

		self.assertEqual(["codRubr", "vrRubr"], list(item))


class TestPonteComOCalculo(unittest.TestCase):
	"""`linhas_de_inss_irrf` já existia e não tinha para onde ir."""

	def test_o_inss_e_o_irrf_viram_linhas_do_evento(self):
		itens = linhas_de_inss_irrf(
			Decimal("330.00"),
			Decimal("120.50"),
			cod_rubrica_inss="9001",
			cod_rubrica_irrf="9002",
		)
		arvore = _evento(dm_dev=(_dm_dev(itens=itens),))
		linhas = _evt(arvore)["dmDev"][0]["infoPerApur"]["ideEstabLot"][0]["remunPerApur"][0]["itensRemun"]

		self.assertEqual(["9001", "9002"], [linha["codRubr"] for linha in linhas])
		self.assertEqual(Decimal("330.00"), linhas[0]["vrRubr"])

	def test_rubrica_zerada_continua_gerando_linha(self):
		"""O eSocial espera o valor apurado do período mesmo quando é zero; omitir a
		linha esconderia o cálculo em vez de mostrar "apurado como zero"."""
		itens = linhas_de_inss_irrf(
			Decimal("0.00"), Decimal("0.00"), cod_rubrica_inss="9001", cod_rubrica_irrf="9002"
		)
		arvore = _evento(dm_dev=(_dm_dev(itens=itens),))
		linhas = _evt(arvore)["dmDev"][0]["infoPerApur"]["ideEstabLot"][0]["remunPerApur"][0]["itensRemun"]

		self.assertEqual(2, len(linhas))


if __name__ == "__main__":
	unittest.main()
