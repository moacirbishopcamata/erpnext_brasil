# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Núcleo puro do cliente SNTP (`fiscal/tempo_ntp.py`) — tarefas 1.1 a 1.3 de `fonte-de-tempo-ntp-br`.

Teste-âncora: `test_resposta_de_outro_pedido_e_recusada`. SNTP sem NTS não autentica nada; o eco do
carimbo de origem é a única barreira contra uma resposta falsificada às cegas, e ele se compara no
inteiro de 64 bits (em `float` dois carimbos diferentes colapsam no mesmo número).
"""

import struct
import unittest

from erpnext_brasil.fiscal.tempo_ntp import (
	Amostra,
	NtpInvalido,
	NtpKissOfDeath,
	calcular_deslocamento_e_atraso,
	consolidar,
	de_ntp,
	ler_resposta,
	melhor_amostra,
	montar_pedido,
	para_ntp,
)

T0 = 1_760_000_000.25


def _resposta(
	carimbo: int,
	*,
	estrato: int = 1,
	versao: int = 4,
	modo: int = 4,
	salto: int = 0,
	recebido: float = T0 + 2.05,
	transmitido: float = T0 + 2.15,
	referencia: bytes = b"GPS\x00",
	origem: int | None = None,
) -> bytes:
	pacote = bytearray(48)
	pacote[0] = (salto << 6) | (versao << 3) | modo
	pacote[1] = estrato
	pacote[12:16] = referencia
	struct.pack_into(
		"!QQQ",
		pacote,
		24,
		carimbo if origem is None else origem,
		para_ntp(recebido) if recebido else 0,
		para_ntp(transmitido) if transmitido else 0,
	)

	return bytes(pacote)


class TestCodec(unittest.TestCase):
	def test_o_pedido_tem_48_bytes_modo_cliente_versao_4(self):
		pacote, _ = montar_pedido(T0)

		self.assertEqual(len(pacote), 48)
		self.assertEqual(pacote[0], 0x23, "esperado LI=0, VN=4, modo=3")

	def test_o_carimbo_de_transmissao_e_o_devolvido(self):
		pacote, carimbo = montar_pedido(T0)

		self.assertEqual(struct.unpack_from("!Q", pacote, 40)[0], carimbo)
		self.assertEqual(carimbo, para_ntp(T0))

	def test_vetor_conhecido_da_epoca_unix(self):
		"""1970-01-01 em NTP: 2.208.988.800 s = 0x83AA7E80."""
		self.assertEqual(para_ntp(0.0), 0x83AA7E80_00000000)
		self.assertEqual(de_ntp(0x83AA7E80_00000000), 0.0)

	def test_ida_e_volta_preserva_o_instante(self):
		self.assertAlmostEqual(de_ntp(para_ntp(T0)), T0, places=6)

	def test_apos_2036_o_pivo_de_era_continua_correto(self):
		depois_de_2036 = 2_200_000_000.5  # 2039-09
		self.assertAlmostEqual(de_ntp(para_ntp(depois_de_2036)), depois_de_2036, places=6)

	def test_resposta_valida_traz_os_carimbos_do_servidor(self):
		_, carimbo = montar_pedido(T0)
		lida = ler_resposta(_resposta(carimbo), carimbo)

		self.assertEqual((lida.estrato, lida.versao), (1, 4))
		self.assertAlmostEqual(lida.t1, T0 + 2.05, places=6)
		self.assertAlmostEqual(lida.t2, T0 + 2.15, places=6)

	def test_resposta_de_outro_pedido_e_recusada(self):
		_, carimbo = montar_pedido(T0)
		_, outro = montar_pedido(T0 + 1e-6)

		self.assertNotEqual(carimbo, outro, "o teste só vale se os carimbos diferem")

		with self.assertRaises(NtpInvalido):
			ler_resposta(_resposta(carimbo, origem=outro), carimbo)

	def test_resposta_curta_e_recusada(self):
		_, carimbo = montar_pedido(T0)

		with self.assertRaises(NtpInvalido):
			ler_resposta(_resposta(carimbo)[:47], carimbo)

	def test_modo_que_nao_e_servidor_e_recusado(self):
		_, carimbo = montar_pedido(T0)

		with self.assertRaises(NtpInvalido):
			ler_resposta(_resposta(carimbo, modo=3), carimbo)

	def test_versao_nao_suportada_e_recusada(self):
		_, carimbo = montar_pedido(T0)

		for versao in (0, 1, 2, 5):
			with self.subTest(versao=versao), self.assertRaises(NtpInvalido):
				ler_resposta(_resposta(carimbo, versao=versao), carimbo)

	def test_estrato_zero_e_kiss_of_death_com_o_codigo(self):
		_, carimbo = montar_pedido(T0)

		with self.assertRaises(NtpKissOfDeath) as contexto:
			ler_resposta(_resposta(carimbo, estrato=0, referencia=b"RATE"), carimbo)

		self.assertEqual(contexto.exception.codigo, "RATE")
		self.assertIsInstance(contexto.exception, NtpInvalido)

	def test_servidor_nao_sincronizado_e_recusado(self):
		_, carimbo = montar_pedido(T0)

		with self.assertRaises(NtpInvalido):
			ler_resposta(_resposta(carimbo, estrato=16), carimbo)

		with self.assertRaises(NtpInvalido):
			ler_resposta(_resposta(carimbo, salto=3), carimbo)

	def test_resposta_sem_carimbo_de_transmissao_e_recusada(self):
		_, carimbo = montar_pedido(T0)

		with self.assertRaises(NtpInvalido):
			ler_resposta(_resposta(carimbo, transmitido=0), carimbo)


class TestDeslocamentoEAtraso(unittest.TestCase):
	"""Casos calculados à mão: o RFC 5905 dá as fórmulas, não um exemplo numérico."""

	def test_relogio_local_atrasado_da_deslocamento_positivo(self):
		# Servidor 2 s à frente; 50 ms de rede em cada sentido e 100 ms de processamento.
		deslocamento, atraso = calcular_deslocamento_e_atraso(100.0, 102.05, 102.15, 100.2)

		self.assertAlmostEqual(deslocamento, 2.0, places=9)
		self.assertAlmostEqual(atraso, 0.1, places=9)

	def test_relogio_local_adiantado_da_deslocamento_negativo(self):
		# Servidor 3 s atrás do relógio local.
		deslocamento, atraso = calcular_deslocamento_e_atraso(100.0, 97.05, 97.15, 100.2)

		self.assertAlmostEqual(deslocamento, -3.0, places=9)
		self.assertAlmostEqual(atraso, 0.1, places=9)

	def test_relogio_certo_da_zero(self):
		deslocamento, _ = calcular_deslocamento_e_atraso(100.0, 100.05, 100.15, 100.2)

		self.assertAlmostEqual(deslocamento, 0.0, places=9)

	def test_rede_assimetrica_erra_no_maximo_metade_da_diferenca(self):
		"""Ida 10 ms, volta 90 ms, relógio certo: o erro de θ é (ida − volta)/2 = −40 ms."""
		deslocamento, atraso = calcular_deslocamento_e_atraso(100.0, 100.01, 100.01, 100.1)

		self.assertAlmostEqual(deslocamento, -0.04, places=9)
		self.assertAlmostEqual(atraso, 0.1, places=9)


def _amostra(servidor: str, deslocamento_ms: float, atraso_ms: float = 20.0) -> Amostra:
	return Amostra(servidor, deslocamento_ms, atraso_ms)


class TestSelecaoEConsenso(unittest.TestCase):
	def test_a_melhor_amostra_e_a_de_menor_atraso(self):
		amostras = [_amostra("a", 5, 80), _amostra("a", 1, 12), _amostra("a", 9, 40)]

		self.assertEqual(melhor_amostra(amostras).deslocamento_ms, 1)

	def test_atraso_negativo_e_descartado(self):
		self.assertIsNone(melhor_amostra([_amostra("a", 1, -5)]))

	def test_sem_amostras_nao_ha_melhor(self):
		self.assertIsNone(melhor_amostra([]))

	def test_fontes_concordam_medicao_confiavel_com_o_consenso(self):
		medicao = consolidar([_amostra("a", 1000), _amostra("b", 1040), _amostra("c", 1010)])

		self.assertTrue(medicao.confiavel)
		self.assertEqual(medicao.fontes_concordantes, 3)
		self.assertAlmostEqual(medicao.deslocamento_ms, 1010)

	def test_um_outlier_e_ignorado_se_as_outras_concordam(self):
		medicao = consolidar([_amostra("a", 1000), _amostra("b", 1020), _amostra("c", 90_000)])

		self.assertTrue(medicao.confiavel)
		self.assertEqual(medicao.fontes_concordantes, 2)
		self.assertAlmostEqual(medicao.deslocamento_ms, 1010, msg="o outlier puxou o consenso")

	def test_fontes_divergem_medicao_nao_confiavel(self):
		medicao = consolidar([_amostra("a", 0), _amostra("b", 5000), _amostra("c", 90_000)])

		self.assertFalse(medicao.confiavel)
		self.assertIn("divergem", medicao.motivo)
		self.assertTrue(medicao.medido, "diverge, mas houve medição: fica para diagnóstico")

	def test_uma_so_fonte_nao_basta(self):
		medicao = consolidar([_amostra("a", 800)], total_consultado=3)

		self.assertFalse(medicao.confiavel)
		self.assertIn("só 1 de 3", medicao.motivo)

	def test_nenhuma_fonte_e_nao_medido_e_nunca_zero(self):
		medicao = consolidar([], total_consultado=3)

		self.assertIsNone(medicao.deslocamento_ms)
		self.assertFalse(medicao.medido)
		self.assertFalse(medicao.confiavel)
		self.assertIn("nenhuma das 3", medicao.motivo)

	def test_a_dispersao_tolerada_e_parametro(self):
		amostras = [_amostra("a", 0), _amostra("b", 800)]

		self.assertFalse(consolidar(amostras, dispersao_maxima_ms=500, minimo_concordantes=2).confiavel)
		self.assertTrue(consolidar(amostras, dispersao_maxima_ms=900, minimo_concordantes=2).confiavel)


if __name__ == "__main__":
	unittest.main()
