# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

import unittest
from datetime import datetime, timedelta

from laboratorio_sus.puro.rejeicao import (
	CondicaoDeTransporte,
	EstabilidadeDoExame,
	MotivoDeQuarentena,
	MotivoDeRejeicao,
	avaliar_estabilidade,
)
from laboratorio_sus.puro.tempos import Etapa, Prioridade, etapas_atrasadas, tempos_por_etapa

T0 = datetime(2026, 10, 12, 8, 0)


class TestEstabilidade(unittest.TestCase):
	def setUp(self):
		self.exame = EstabilidadeDoExame(timedelta(hours=4), 2.0, 8.0)

	def _cond(self, depois, temperatura=5.0):
		return CondicaoDeTransporte(T0, T0 + depois, temperatura)

	def test_dentro_dos_limites(self):
		self.assertIsNone(avaliar_estabilidade(self.exame, self._cond(timedelta(hours=3))))

	def test_exatamente_no_prazo_ainda_vale(self):
		self.assertIsNone(avaliar_estabilidade(self.exame, self._cond(timedelta(hours=4))))

	def test_um_minuto_depois_vence(self):
		motivo = avaliar_estabilidade(self.exame, self._cond(timedelta(hours=4, minutes=1)))
		self.assertIs(motivo, MotivoDeRejeicao.ESTABILIDADE_VENCIDA)

	def test_temperatura_nos_extremos_vale_e_fora_rejeita(self):
		for t in (2.0, 8.0):
			self.assertIsNone(avaliar_estabilidade(self.exame, self._cond(timedelta(hours=1), t)))

		for t in (1.9, 8.1):
			self.assertIs(
				avaliar_estabilidade(self.exame, self._cond(timedelta(hours=1), t)),
				MotivoDeRejeicao.TEMPERATURA_FORA_DA_FAIXA,
			)

	def test_exame_com_faixa_e_sem_registro_de_temperatura_nao_e_aceito_por_omissao(self):
		self.assertIs(
			avaliar_estabilidade(self.exame, self._cond(timedelta(hours=1), None)),
			MotivoDeRejeicao.TEMPERATURA_FORA_DA_FAIXA,
		)

	def test_exame_sem_faixa_ignora_temperatura(self):
		exame = EstabilidadeDoExame(timedelta(hours=4))
		self.assertIsNone(avaliar_estabilidade(exame, self._cond(timedelta(hours=1), None)))

	def test_prazo_vence_antes_da_temperatura(self):
		motivo = avaliar_estabilidade(self.exame, self._cond(timedelta(hours=9), 50.0))
		self.assertIs(motivo, MotivoDeRejeicao.ESTABILIDADE_VENCIDA)

	def test_recebimento_antes_da_coleta_e_relogio_incoerente(self):
		with self.assertRaises(ValueError):
			avaliar_estabilidade(self.exame, CondicaoDeTransporte(T0, T0 - timedelta(minutes=1), 5.0))

	def test_listas_de_motivos_sao_enumeradas(self):
		self.assertEqual(len(MotivoDeRejeicao), 9)
		self.assertIn("identificador_desconhecido", {m.value for m in MotivoDeQuarentena})


class TestTempos(unittest.TestCase):
	def _carimbos(self, **minutos):
		return {nome: T0 + timedelta(minutes=m) for nome, m in minutos.items()}

	def test_duracao_de_cada_etapa(self):
		tempos = tempos_por_etapa(
			self._carimbos(solicitacao=0, coleta=30, chegada=150, liberacao=210, ciencia=240)
		)
		self.assertEqual(
			[(t.etapa, int(t.duracao.total_seconds() // 60)) for t in tempos],
			[
				(Etapa.SOLICITACAO_ATE_COLETA, 30),
				(Etapa.COLETA_ATE_CHEGADA, 120),
				(Etapa.CHEGADA_ATE_LIBERACAO, 60),
				(Etapa.LIBERACAO_ATE_CIENCIA, 30),
			],
		)

	def test_etapa_com_carimbo_faltando_e_omitida(self):
		tempos = tempos_por_etapa(self._carimbos(solicitacao=0, coleta=10))
		self.assertEqual([t.etapa for t in tempos], [Etapa.SOLICITACAO_ATE_COLETA])

	def test_carimbo_fora_de_ordem_e_erro(self):
		with self.assertRaises(ValueError):
			tempos_por_etapa(self._carimbos(solicitacao=10, coleta=0))

	def test_atraso_so_acima_do_prazo(self):
		prazos = {
			Prioridade.URGENCIA: {Etapa.CHEGADA_ATE_LIBERACAO: timedelta(minutes=60)},
			Prioridade.ROTINA: {Etapa.CHEGADA_ATE_LIBERACAO: timedelta(hours=24)},
		}
		no_limite = tempos_por_etapa(self._carimbos(chegada=0, liberacao=60))
		passou = tempos_por_etapa(self._carimbos(chegada=0, liberacao=61))

		self.assertEqual(etapas_atrasadas(no_limite, Prioridade.URGENCIA, prazos), [])
		self.assertEqual(etapas_atrasadas(passou, Prioridade.URGENCIA, prazos), [Etapa.CHEGADA_ATE_LIBERACAO])
		self.assertEqual(etapas_atrasadas(passou, Prioridade.ROTINA, prazos), [])

	def test_sem_prazo_configurado_nao_ha_atraso(self):
		passou = tempos_por_etapa(self._carimbos(chegada=0, liberacao=9999))
		self.assertEqual(etapas_atrasadas(passou, Prioridade.URGENCIA, {}), [])


if __name__ == "__main__":
	unittest.main()
