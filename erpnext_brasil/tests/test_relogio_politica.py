# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A política do relógio (`fiscal/relogio_politica.py`): configuração validada e veredito.

Teste-âncora: `test_medicao_que_nao_serve_nunca_bloqueia_nem_alerta`. Rede fora, medição vencida ou
fontes que discordam não são prova de relógio errado — tratar como erro pararia a emissão fiscal
por uma falha da própria medição.
"""

import unittest

from erpnext_brasil.fiscal.relogio_politica import (
	CHAVES,
	INTERVALO_DE_REAVISO_S,
	SERVIDORES_PADRAO,
	ConfiguracaoInvalida,
	ConfiguracaoRelogio,
	UltimaMedicao,
	Veredito,
	avaliar,
	deve_notificar,
	ler_configuracao,
	mensagem_de_alerta,
)
from erpnext_brasil.fiscal.tempo_ntp import Medicao

AGORA = 1_760_000_000.0
CONFIG = ConfiguracaoRelogio()


def _ultima(
	desvio_ms: float | None = 0.0,
	*,
	confiavel: bool = True,
	idade_s: float = 60.0,
	motivo: str = "",
) -> UltimaMedicao:
	medicao = Medicao(desvio_ms, confiavel, 3 if desvio_ms is not None else 0, 3, 5.0, motivo)

	return UltimaMedicao(medicao=medicao, medida_em=AGORA - idade_s)


class TestConfiguracao(unittest.TestCase):
	def test_sem_nenhuma_chave_valem_os_padroes(self):
		config = ler_configuracao({})

		self.assertEqual(config, ConfiguracaoRelogio())
		self.assertEqual(config.servidores, SERVIDORES_PADRAO)
		self.assertTrue(config.guarda_ligada)
		self.assertFalse(config.correcao_ligada, "a correção de dhEmi tem de nascer desligada")

	def test_valores_validos_sao_lidos(self):
		config = ler_configuracao(
			{
				CHAVES["limite_aviso_ms"]: 500,
				CHAVES["limite_critico_ms"]: 30_000,
				CHAVES["ttl_s"]: 3600,
				CHAVES["servidores"]: ["A.ntp.br ", "b.ntp.br"],
				CHAVES["guarda_ligada"]: False,
				CHAVES["correcao_ligada"]: True,
			}
		)

		self.assertEqual(
			(config.limite_aviso_ms, config.limite_critico_ms, config.ttl_s), (500, 30_000, 3600)
		)
		self.assertEqual(config.servidores, ("a.ntp.br", "b.ntp.br"))
		self.assertFalse(config.guarda_ligada)
		self.assertTrue(config.correcao_ligada)

	def test_valor_invalido_nomeia_a_chave(self):
		casos = [
			(CHAVES["limite_aviso_ms"], "rápido"),
			(CHAVES["limite_critico_ms"], -5),
			(CHAVES["ttl_s"], 30),
			(CHAVES["ttl_s"], 12.5),
			(CHAVES["guarda_ligada"], "sim"),
			(CHAVES["correcao_ligada"], 1),
			(CHAVES["servidores"], "a.ntp.br"),
			(CHAVES["dispersao_ms"], True),
		]

		for chave, valor in casos:
			with self.subTest(chave=chave, valor=valor), self.assertRaises(ConfiguracaoInvalida) as contexto:
				ler_configuracao({chave: valor})

			self.assertEqual(contexto.exception.chave, chave)
			self.assertIn(chave, str(contexto.exception))

	def test_critico_precisa_ser_maior_que_aviso(self):
		"""O erro clássico: digitar o crítico em segundos (60) e o aviso em milissegundos (1000)."""
		with self.assertRaises(ConfiguracaoInvalida) as contexto:
			ler_configuracao({CHAVES["limite_aviso_ms"]: 1000, CHAVES["limite_critico_ms"]: 60})

		self.assertEqual(contexto.exception.chave, CHAVES["limite_critico_ms"])

	def test_um_servidor_so_nao_forma_consenso(self):
		with self.assertRaises(ConfiguracaoInvalida):
			ler_configuracao({CHAVES["servidores"]: ["a.ntp.br", "A.NTP.BR"]})

	def test_nulo_vale_o_padrao(self):
		self.assertEqual(ler_configuracao({CHAVES["ttl_s"]: None}), ConfiguracaoRelogio())


class TestVeredito(unittest.TestCase):
	def test_dentro_do_limite_de_aviso_esta_ok(self):
		veredito = avaliar(_ultima(400.0), AGORA, CONFIG)

		self.assertEqual(veredito.nivel, "ok")
		self.assertEqual(veredito.desvio_ms, 400.0)

	def test_a_partir_do_limite_de_aviso_avisa(self):
		self.assertEqual(avaliar(_ultima(1000.0), AGORA, CONFIG).nivel, "aviso")
		self.assertEqual(avaliar(_ultima(30_000.0), AGORA, CONFIG).nivel, "aviso")

	def test_a_partir_do_limite_critico_e_critico(self):
		self.assertEqual(avaliar(_ultima(60_000.0), AGORA, CONFIG).nivel, "critico")
		self.assertEqual(avaliar(_ultima(3_600_000.0), AGORA, CONFIG).nivel, "critico")

	def test_o_sinal_do_desvio_nao_importa(self):
		"""Relógio adiantado é tão errado quanto atrasado."""
		self.assertEqual(avaliar(_ultima(-60_000.0), AGORA, CONFIG).nivel, "critico")
		self.assertEqual(avaliar(_ultima(-1500.0), AGORA, CONFIG).nivel, "aviso")
		self.assertEqual(avaliar(_ultima(-1500.0), AGORA, CONFIG).desvio_ms, -1500.0)

	def test_os_limites_vem_da_configuracao(self):
		config = ConfiguracaoRelogio(limite_aviso_ms=100, limite_critico_ms=200)

		self.assertEqual(avaliar(_ultima(150.0), AGORA, config).nivel, "aviso")
		self.assertEqual(avaliar(_ultima(250.0), AGORA, config).nivel, "critico")

	def test_sem_medicao_nenhuma(self):
		veredito = avaliar(None, AGORA, CONFIG)

		self.assertEqual(veredito.nivel, "sem_medicao")
		self.assertIn("ainda não há medição", veredito.motivo)

	def test_medicao_vencida_nao_vale_mesmo_com_desvio_enorme(self):
		veredito = avaliar(_ultima(999_999.0, idade_s=CONFIG.ttl_s + 1), AGORA, CONFIG)

		self.assertEqual(veredito.nivel, "sem_medicao")
		self.assertIn("vencida", veredito.motivo)

	def test_na_borda_da_validade_ainda_vale(self):
		self.assertEqual(avaliar(_ultima(5.0, idade_s=CONFIG.ttl_s), AGORA, CONFIG).nivel, "ok")

	def test_medicao_que_nao_serve_nunca_bloqueia_nem_alerta(self):
		nao_serve = {
			"nao medido": _ultima(None, confiavel=False, motivo="nenhuma das 3 fontes respondeu"),
			"nao confiavel": _ultima(999_999.0, confiavel=False, motivo="as fontes divergem"),
			"vencida": _ultima(999_999.0, idade_s=10 * CONFIG.ttl_s),
		}

		for rotulo, ultima in nao_serve.items():
			with self.subTest(caso=rotulo):
				veredito = avaliar(ultima, AGORA, CONFIG)

				self.assertEqual(veredito.nivel, "sem_medicao")
				self.assertNotIn(veredito.nivel, ("aviso", "critico"))

	def test_o_motivo_da_falha_da_medicao_chega_ao_veredito(self):
		veredito = avaliar(
			_ultima(None, confiavel=False, motivo="nenhuma das 3 fontes respondeu"), AGORA, CONFIG
		)

		self.assertIn("nenhuma das 3", veredito.motivo)

	def test_a_idade_e_informada(self):
		self.assertEqual(avaliar(_ultima(1.0, idade_s=90), AGORA, CONFIG).idade_s, 90)


class TestNotificacao(unittest.TestCase):
	"""O alerta é horário na medição e diário na notificação: não vira spam."""

	def test_ok_e_sem_medicao_nunca_notificam(self):
		for nivel in ("ok", "sem_medicao"):
			with self.subTest(nivel=nivel):
				self.assertFalse(deve_notificar(Veredito(nivel), None, None, AGORA))

	def test_primeiro_aviso_notifica_na_hora(self):
		self.assertTrue(deve_notificar(Veredito("aviso", 2000.0), None, None, AGORA))

	def test_mesmo_nivel_dentro_do_intervalo_nao_repete(self):
		self.assertFalse(deve_notificar(Veredito("aviso", 2000.0), "aviso", AGORA - 3600, AGORA))

	def test_mesmo_nivel_depois_do_intervalo_repete(self):
		ha_um_dia = AGORA - INTERVALO_DE_REAVISO_S

		self.assertTrue(deve_notificar(Veredito("aviso", 2000.0), "aviso", ha_um_dia, AGORA))

	def test_piorar_de_nivel_notifica_mesmo_dentro_do_intervalo(self):
		self.assertTrue(deve_notificar(Veredito("critico", 90_000.0), "aviso", AGORA - 60, AGORA))

	def test_melhorar_de_nivel_nao_notifica_de_novo_dentro_do_intervalo(self):
		self.assertFalse(deve_notificar(Veredito("aviso", 2000.0), "critico", AGORA - 60, AGORA))

	def test_a_mensagem_diz_o_desvio_o_sentido_e_o_que_fazer(self):
		assunto, texto = mensagem_de_alerta(Veredito("aviso", 2500.0), CONFIG)

		self.assertIn("Hora Legal", assunto)
		self.assertIn("atrasado", texto)
		self.assertIn("2.5 s", texto)
		self.assertIn("NTP.br", texto)
		self.assertIn("NTS", texto)

	def test_relogio_adiantado_diz_adiantado(self):
		self.assertIn("adiantado", mensagem_de_alerta(Veredito("aviso", -2500.0), CONFIG)[1])

	def test_critico_com_guarda_ligada_diz_que_a_emissao_esta_recusada(self):
		texto = mensagem_de_alerta(Veredito("critico", 90_000.0), CONFIG)[1]

		self.assertIn("recusada", texto)

	def test_critico_com_guarda_desligada_nao_promete_recusa(self):
		config = ConfiguracaoRelogio(guarda_ligada=False)

		self.assertNotIn("recusada", mensagem_de_alerta(Veredito("critico", 90_000.0), config)[1])


if __name__ == "__main__":
	unittest.main()
