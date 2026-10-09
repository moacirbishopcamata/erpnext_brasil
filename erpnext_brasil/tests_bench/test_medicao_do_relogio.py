# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) da medição do relógio: cache do Redis, configuração e aviso.

A sonda e a política têm testes puros (`test_relogio_oficial.py`, `test_relogio_politica.py`); o que
só um site mostra é a costura com o **cache de verdade** e com o `site_config`. Nenhuma rede é usada:
a sonda é substituída por uma função que devolve a rodada que o teste quer.

Teste-âncora: `test_o_que_foi_guardado_e_lido_por_outro_caminho`. `guardar` e `ler_ultima` falam com
o mesmo cache; se uma chave divergir, a guarda lê `None` e nunca bloqueia, sem erro nenhum. O teste
relê o valor cru com a API do cache — não por `ler_ultima`.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_medicao_do_relogio
"""

from typing import ClassVar
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.fiscal.relogio_politica import CHAVES, ConfiguracaoRelogio, avaliar
from erpnext_brasil.fiscal.tempo_ntp import Medicao
from erpnext_brasil.integracao import medicao_do_relogio as modulo
from erpnext_brasil.integracao.medicao_do_relogio import (
	CHAVE_ULTIMA,
	configuracao,
	guardar,
	ler_ultima,
	medir_e_guardar,
	servidores_em_pausa,
)
from erpnext_brasil.integracao.relogio_oficial import Rodada

MODULOS_COBERTOS = ("medicao_do_relogio", "relogio_oficial")
"""Declarados, não inferidos — ver `scripts/cobertura_de_bench.py`."""

AGORA = 1_760_000_000.0


def _rodada(desvio_ms: float | None, *, confiavel: bool = True, rate: tuple = (), erros=None) -> Rodada:
	medicao = Medicao(
		desvio_ms, confiavel, 3 if desvio_ms is not None else 0, 3, 4.0, "" if confiavel else "x"
	)

	return Rodada(medicao=medicao, medida_em=AGORA, servidores_rate=rate, erros=erros or {})


class Notificador:
	chamadas: ClassVar[list] = []

	def __call__(self, company, assunto, texto):
		type(self).chamadas.append((company, assunto, texto))

		return 1


class TestMedicaoDoRelogio(FrappeTestCase):
	def setUp(self):
		Notificador.chamadas = []
		self._limpar()
		self.addCleanup(self._limpar)

	def _limpar(self):
		cache = modulo._cache()

		for chave in (
			CHAVE_ULTIMA,
			modulo.CHAVE_AVISO,
			modulo.CHAVE_FALHA,
			modulo.PREFIXO_PAUSA + "a.st1.ntp.br",
		):
			cache.delete_value(chave)

	def _rodar(self, rodada: Rodada, agora: float = AGORA, **extras) -> dict:
		def medir(servidores, **kwargs):
			self.pausados_recebidos = kwargs.get("pausados")

			return rodada

		return medir_e_guardar(medir=medir, agora=lambda: agora, notificar=Notificador(), **extras)

	def test_o_que_foi_guardado_e_lido_por_outro_caminho(self):
		guardar(_rodada(2500.0, erros={"c.st1.ntp.br": "TimeoutError: x"}))

		bruto = modulo._cache().get_value(CHAVE_ULTIMA)
		self.assertEqual(bruto["deslocamento_ms"], 2500.0)
		self.assertEqual(bruto["medida_em"], AGORA)

		ultima = ler_ultima()
		self.assertEqual(ultima.medicao.deslocamento_ms, 2500.0)
		self.assertTrue(ultima.medicao.confiavel)
		self.assertEqual(ultima.medida_em, AGORA)
		self.assertEqual(ultima.erros, {"c.st1.ntp.br": "TimeoutError: x"})

	def test_sem_nada_guardado_nao_ha_medicao(self):
		self.assertIsNone(ler_ultima())

	def test_nao_medido_nunca_vira_zero_no_cache(self):
		guardar(_rodada(None, confiavel=False))

		ultima = ler_ultima()

		self.assertIsNone(ultima.medicao.deslocamento_ms)
		self.assertEqual(avaliar(ultima, AGORA, ConfiguracaoRelogio()).nivel, "sem_medicao")

	def test_conteudo_ilegivel_no_cache_e_tratado_como_sem_medicao(self):
		modulo._cache().set_value(CHAVE_ULTIMA, {"lixo": 1}, expires_in_sec=60)

		self.assertIsNone(ler_ultima())

	def test_rate_poe_o_servidor_em_pausa_e_a_proxima_rodada_o_pula(self):
		self._rodar(_rodada(10.0, rate=("a.st1.ntp.br",)))

		self.assertEqual(servidores_em_pausa(("a.st1.ntp.br", "b.st1.ntp.br")), {"a.st1.ntp.br"})

		self._rodar(_rodada(10.0))
		self.assertEqual(self.pausados_recebidos, {"a.st1.ntp.br"})

	def test_desvio_acima_do_aviso_notifica_todas_as_empresas_uma_vez(self):
		resumo = self._rodar(_rodada(2500.0))

		self.assertEqual(resumo["nivel"], "aviso")
		self.assertTrue(resumo["notificou"])
		self.assertEqual(
			{c for c, _, _ in Notificador.chamadas}, set(frappe.get_all("Company", pluck="name"))
		)
		self.assertIn("Hora Legal", Notificador.chamadas[0][1])

		Notificador.chamadas = []
		repetido = self._rodar(_rodada(2500.0), agora=AGORA + 3600)

		self.assertFalse(repetido["notificou"], "a medição é horária; o aviso não pode ser")
		self.assertEqual(Notificador.chamadas, [])

	def test_piorar_para_critico_notifica_de_novo(self):
		self._rodar(_rodada(2500.0))
		Notificador.chamadas = []

		resumo = self._rodar(_rodada(90_000.0), agora=AGORA + 3600)

		self.assertEqual(resumo["nivel"], "critico")
		self.assertTrue(resumo["notificou"])

	def test_desvio_pequeno_nao_notifica(self):
		resumo = self._rodar(_rodada(120.0))

		self.assertEqual(resumo["nivel"], "ok")
		self.assertFalse(resumo["notificou"])

	def test_nao_medido_registra_a_causa_no_error_log_e_nao_notifica(self):
		antes = frappe.db.count("Error Log", {"method": ("like", "%relógio não medido%")})
		rodada = _rodada(None, confiavel=False, erros={"a.st1.ntp.br": "OSError: Network is unreachable"})

		with mock.patch.object(modulo.frappe, "log_error") as registrar:
			resumo = self._rodar(rodada)

		self.assertEqual(resumo["nivel"], "sem_medicao")
		self.assertFalse(resumo["notificou"])
		registrar.assert_called_once()
		self.assertIn("unreachable", registrar.call_args.kwargs["message"])
		self.assertEqual(antes, frappe.db.count("Error Log", {"method": ("like", "%relógio não medido%")}))

	def test_a_falha_de_medicao_so_e_registrada_uma_vez_por_dia(self):
		rodada = _rodada(None, confiavel=False, erros={"a.st1.ntp.br": "x"})

		with mock.patch.object(modulo.frappe, "log_error") as registrar:
			self._rodar(rodada)
			self._rodar(rodada, agora=AGORA + 3600)

		self.assertEqual(registrar.call_count, 1)

	def test_configuracao_vem_do_site_config_e_invalida_cai_nos_padroes_com_registro(self):
		with mock.patch.dict(frappe.conf, {CHAVES["limite_aviso_ms"]: 250}):
			self.assertEqual(configuracao().limite_aviso_ms, 250)

		with (
			mock.patch.dict(frappe.conf, {CHAVES["limite_critico_ms"]: "60s"}),
			mock.patch.object(modulo.frappe, "log_error") as registrar,
		):
			config = configuracao()

		self.assertEqual(config, ConfiguracaoRelogio())
		self.assertIn(CHAVES["limite_critico_ms"], registrar.call_args.kwargs["message"])
