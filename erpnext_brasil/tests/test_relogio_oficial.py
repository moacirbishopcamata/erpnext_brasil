# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A sonda de relógio (`integracao/relogio_oficial.py`) com rede e relógio simulados — tarefa 2.1.

O "mundo" abaixo responde pelo protocolo de verdade (monta o pacote de resposta a partir do pedido,
ecoando o carimbo de origem), então o teste atravessa o codec, a conta e o consenso. Nada sai para a
rede e nada espera de verdade.

Teste-âncora: `test_um_servidor_forjado_nao_move_o_consenso`. SNTP sem NTS pode ser falsificado no
caminho; o que impede um servidor mentiroso de puxar a medição é haver outras duas fontes que
concordam.
"""

import struct
import unittest
from unittest import mock

from erpnext_brasil.fiscal.tempo_ntp import para_ntp
from erpnext_brasil.integracao import relogio_oficial
from erpnext_brasil.integracao.relogio_oficial import medir_relogio

SERVIDORES = ("a.st1.ntp.br", "b.st1.ntp.br", "c.st1.ntp.br")


class Mundo:
	"""Relógio local que só anda quando a rede anda, e servidores com desvios configuráveis."""

	def __init__(self, desvios: dict[str, float | Exception | str], inicio: float = 1_760_000_000.0):
		self.agora_local = inicio
		self.desvios = desvios
		self.chamadas: list[str] = []
		self.pausas = 0

	def agora(self) -> float:
		return self.agora_local

	def dormir(self, segundos: float) -> None:
		self.pausas += 1
		self.agora_local += segundos

	def transporte(self, servidor: str, porta: int, pacote: bytes, prazo: float) -> bytes:
		self.chamadas.append(servidor)
		comportamento = self.desvios[servidor]

		if isinstance(comportamento, Exception):
			raise comportamento

		carimbo = struct.unpack_from("!Q", pacote, 40)[0]
		self.agora_local += 0.05  # ida
		servidor_recebe = self.agora_local + (comportamento if isinstance(comportamento, float) else 0.0)
		self.agora_local += 0.05  # volta
		resposta = bytearray(48)
		resposta[0] = (0 << 6) | (4 << 3) | 4
		resposta[1] = 0 if comportamento == "RATE" else 1
		resposta[12:16] = b"RATE" if comportamento == "RATE" else b"GPS\x00"
		origem = carimbo + 1 if comportamento == "origem-errada" else carimbo
		struct.pack_into("!QQQ", resposta, 24, origem, para_ntp(servidor_recebe), para_ntp(servidor_recebe))

		return bytes(resposta)


def _medir(mundo: Mundo, **extras):
	return medir_relogio(
		SERVIDORES, transporte=mundo.transporte, agora=mundo.agora, dormir=mundo.dormir, **extras
	)


class TestMedicao(unittest.TestCase):
	def test_tres_servidores_concordando_medem_o_desvio_real(self):
		mundo = Mundo(dict.fromkeys(SERVIDORES, 2.0))

		rodada = _medir(mundo)

		self.assertTrue(rodada.medicao.confiavel)
		self.assertAlmostEqual(rodada.medicao.deslocamento_ms, 2000, delta=1)
		self.assertEqual(rodada.medicao.fontes_responderam, 3)
		self.assertEqual(rodada.erros, {})

	def test_relogio_local_adiantado_da_desvio_negativo(self):
		rodada = _medir(Mundo(dict.fromkeys(SERVIDORES, -3.0)))

		self.assertAlmostEqual(rodada.medicao.deslocamento_ms, -3000, delta=1)

	def test_um_servidor_forjado_nao_move_o_consenso(self):
		mundo = Mundo({"a.st1.ntp.br": 0.0, "b.st1.ntp.br": 0.02, "c.st1.ntp.br": 90.0})

		rodada = _medir(mundo)

		self.assertTrue(rodada.medicao.confiavel)
		self.assertEqual(rodada.medicao.fontes_concordantes, 2)
		self.assertAlmostEqual(rodada.medicao.deslocamento_ms, 10, delta=1)

	def test_um_servidor_fora_do_ar_ainda_deixa_duas_fontes(self):
		mundo = Mundo(
			{"a.st1.ntp.br": 1.0, "b.st1.ntp.br": 1.0, "c.st1.ntp.br": TimeoutError("sem resposta")}
		)

		rodada = _medir(mundo)

		self.assertTrue(rodada.medicao.confiavel)
		self.assertIn("c.st1.ntp.br", rodada.erros)
		self.assertIn("TimeoutError", rodada.erros["c.st1.ntp.br"])

	def test_sem_rede_o_resultado_e_nao_medido_e_a_causa_fica_registrada(self):
		mundo = Mundo(dict.fromkeys(SERVIDORES, OSError("Network is unreachable")))

		rodada = _medir(mundo)

		self.assertIsNone(rodada.medicao.deslocamento_ms)
		self.assertFalse(rodada.medicao.confiavel)
		self.assertEqual(set(rodada.erros), set(SERVIDORES))
		self.assertIn("unreachable", rodada.erros["a.st1.ntp.br"])

	def test_resposta_de_outro_pedido_nao_conta(self):
		mundo = Mundo(dict.fromkeys(SERVIDORES, "origem-errada"))

		rodada = _medir(mundo)

		self.assertIsNone(rodada.medicao.deslocamento_ms)
		self.assertIn("carimbo de origem", rodada.erros["a.st1.ntp.br"])

	def test_o_relogio_local_nao_e_alterado_pela_sonda_alem_do_tempo_de_rede(self):
		"""A sonda mede; não corrige nada. O relógio simulado só andou o que a rede e a pausa custaram."""
		mundo = Mundo(dict.fromkeys(SERVIDORES, 5.0))
		inicio = mundo.agora_local

		_medir(mundo)

		esperado = 3 * 3 * 0.1 + mundo.pausas * 1.0
		# O relógio simulado está em ~1,76e9 s, onde o `float` resolve ~2,4e-7: a soma acumula ruído.
		self.assertAlmostEqual(mundo.agora_local - inicio, esperado, delta=1e-5)


class TestCortesiaComOServicoPublico(unittest.TestCase):
	def test_rate_tira_o_servidor_da_rodada_e_o_devolve_para_pausa(self):
		mundo = Mundo({"a.st1.ntp.br": 1.0, "b.st1.ntp.br": "RATE", "c.st1.ntp.br": 1.0})

		rodada = _medir(mundo)

		self.assertEqual(rodada.servidores_rate, ("b.st1.ntp.br",))
		self.assertEqual(mundo.chamadas.count("b.st1.ntp.br"), 1, "insistiu num servidor que pediu RATE")
		self.assertTrue(rodada.medicao.confiavel)

	def test_servidor_pausado_nao_e_consultado(self):
		mundo = Mundo(dict.fromkeys(SERVIDORES, 1.0))

		rodada = _medir(mundo, pausados={"a.st1.ntp.br"})

		self.assertNotIn("a.st1.ntp.br", mundo.chamadas)
		self.assertIn("pausa", rodada.erros["a.st1.ntp.br"])

	def test_ha_pausa_entre_os_pacotes_do_mesmo_servidor(self):
		mundo = Mundo(dict.fromkeys(SERVIDORES, 1.0))

		_medir(mundo, amostras=3)

		self.assertEqual(mundo.pausas, 3 * 2, "duas pausas por servidor, nenhuma antes do primeiro pacote")

	def test_a_quantidade_de_pacotes_e_a_pedida(self):
		mundo = Mundo(dict.fromkeys(SERVIDORES, 1.0))

		_medir(mundo, amostras=2)

		self.assertEqual(len(mundo.chamadas), 3 * 2)

	def test_padroes_sao_tres_stratum_1_do_ntp_br(self):
		self.assertEqual(len(relogio_oficial.SERVIDORES_PADRAO), 3)
		self.assertTrue(all(s.endswith(".st1.ntp.br") for s in relogio_oficial.SERVIDORES_PADRAO))


class TestTransporteUdp(unittest.TestCase):
	def _com_soquete(self, origem: tuple):
		soquete = mock.MagicMock()
		soquete.__enter__.return_value = soquete
		soquete.recvfrom.return_value = (b"resposta", origem)

		return soquete

	def test_aceita_a_resposta_do_endereco_consultado(self):
		soquete = self._com_soquete(("200.160.0.8", 123))
		info = [(2, 2, 17, "", ("200.160.0.8", 123))]

		with (
			mock.patch.object(relogio_oficial.socket, "getaddrinfo", return_value=info),
			mock.patch.object(relogio_oficial.socket, "socket", return_value=soquete),
		):
			dados = relogio_oficial._udp("a.st1.ntp.br", 123, b"pedido", 2.0)

		self.assertEqual(dados, b"resposta")
		soquete.settimeout.assert_called_once_with(2.0)
		soquete.sendto.assert_called_once_with(b"pedido", ("200.160.0.8", 123))

	def test_descarta_a_resposta_de_outro_endereco(self):
		soquete = self._com_soquete(("203.0.113.9", 123))
		info = [(2, 2, 17, "", ("200.160.0.8", 123))]

		with (
			mock.patch.object(relogio_oficial.socket, "getaddrinfo", return_value=info),
			mock.patch.object(relogio_oficial.socket, "socket", return_value=soquete),
			self.assertRaises(OSError),
		):
			relogio_oficial._udp("a.st1.ntp.br", 123, b"pedido", 2.0)


if __name__ == "__main__":
	unittest.main()
