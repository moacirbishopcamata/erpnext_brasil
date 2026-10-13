# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

import json
import unittest
import urllib.error

from erpnext_brasil.fiscal.tempo_ntp import Medicao
from erpnext_brasil.integracao.hora_legal_br import com_reserva, medir_pelo_hora_legal
from erpnext_brasil.integracao.relogio_oficial import Rodada


class _Resposta:
	def __init__(self, corpo, status=200):
		self.status = status
		self._corpo = corpo if isinstance(corpo, bytes) else json.dumps(corpo).encode()

	def read(self):
		return self._corpo

	def __enter__(self):
		return self

	def __exit__(self, *args):
		return False


class _Relogio:
	"""Relógio de teste: cada leitura avança `passo` segundos (a ida e volta)."""

	def __init__(self, inicio=1_700_000_000.0, passo=0.010):
		self.agora = inicio
		self.passo = passo

	def __call__(self):
		valor = self.agora
		self.agora += self.passo

		return valor


def _corpo(utc, **extra):
	return {"utc": utc, "degradado": False, "fonte": "a.ntp.br", **extra}


# 1_700_000_000 = 2023-11-14T22:13:20Z
BASE = "2023-11-14T22:13:20"


class TestMedida(unittest.TestCase):
	def test_relogio_atrasado_da_deslocamento_positivo_como_no_ntp(self):
		# local: 22:13:20.000 e 22:13:20.010 (ponto médio .005); serviço diz 22:13:22.005 → local atrasado 2 s
		medicao = medir_pelo_hora_legal(
			"http://hl",
			abrir=lambda p, timeout: _Resposta(_corpo("2023-11-14T22:13:22.005000000Z")),
			relogio=_Relogio(),
		)
		# 22:13:22.005 - 22:13:20.005 = 2 s
		self.assertTrue(medicao.confiavel and medicao.medido)
		self.assertAlmostEqual(medicao.deslocamento_ms, 2000.0, places=1)
		self.assertEqual((medicao.fontes_responderam, medicao.fontes_concordantes), (1, 1))
		self.assertIn("a.ntp.br", medicao.motivo)

	def test_relogio_adiantado_da_deslocamento_negativo(self):
		medicao = medir_pelo_hora_legal(
			"http://hl",
			abrir=lambda p, timeout: _Resposta(_corpo(f"{BASE}.005000000Z")),
			relogio=_Relogio(inicio=1_700_000_003.0),
		)

		self.assertAlmostEqual(medicao.deslocamento_ms, -3000.0, places=1)

	def test_pede_a_api_versionada_com_o_prazo(self):
		vistos = []

		def abrir(pedido, timeout):
			vistos.append((pedido.full_url, timeout))

			return _Resposta(_corpo(f"{BASE}Z"))

		medir_pelo_hora_legal("http://hl:8080/", abrir=abrir, relogio=_Relogio(), prazo=1.5)

		self.assertEqual(vistos, [("http://hl:8080/api/v1/hora", 1.5)])


class TestNaoMedidoNuncaViraZero(unittest.TestCase):
	def _medir(self, abrir, passo=0.010, url="http://hl"):
		return medir_pelo_hora_legal(url, abrir=abrir, relogio=_Relogio(passo=passo))

	def _confere(self, medicao):
		self.assertFalse(medicao.medido)
		self.assertFalse(medicao.confiavel)
		self.assertIsNone(medicao.deslocamento_ms, "não medido nunca vira zero")
		self.assertTrue(medicao.motivo)

	def test_sem_url_e_estado_normal_e_nao_levanta(self):
		self._confere(self._medir(lambda p, timeout: _Resposta(b"{}"), url="  "))

	def test_servico_degradado_nao_serve_de_referencia(self):
		self._confere(self._medir(lambda p, timeout: _Resposta(_corpo(f"{BASE}Z", degradado=True))))

	def test_atraso_alto_recusa_a_medida(self):
		self._confere(self._medir(lambda p, timeout: _Resposta(_corpo(f"{BASE}Z")), passo=1.0))

	def test_rede_fora_http_erro_e_corpo_estranho(self):
		def sem_rede(pedido, timeout):
			raise urllib.error.URLError("sem rota")

		casos = {
			"rede": sem_rede,
			"503": lambda p, timeout: _Resposta(b"{}", status=503),
			"html": lambda p, timeout: _Resposta(b"<html>erro</html>"),
			"sem campo": lambda p, timeout: _Resposta({"outra": 1}),
			"sem fuso": lambda p, timeout: _Resposta({"utc": BASE}),
		}

		for nome, abrir in casos.items():
			with self.subTest(nome):
				self._confere(self._medir(abrir))

	def test_relogio_local_andando_para_tras_recusa(self):
		class Voltando:
			def __init__(self):
				self.valores = iter([100.0, 99.0])

			def __call__(self):
				return next(self.valores)

		medicao = medir_pelo_hora_legal(
			"http://hl", abrir=lambda p, timeout: _Resposta(_corpo(f"{BASE}Z")), relogio=Voltando()
		)

		self._confere(medicao)


def _rodada(confiavel, desvio=None):
	medicao = Medicao(
		desvio, confiavel, 3 if confiavel else 0, 3 if confiavel else 0, 4.0, "" if confiavel else "udp"
	)

	return Rodada(medicao=medicao, medida_em=1.0, erros={"a.st1.ntp.br": "TimeoutError"})


RESERVA_BOA = Medicao(120.0, True, 1, 1, None, "hora-legal-br (a.ntp.br)")
RESERVA_RUIM = Medicao(None, False, 0, 0, None, "hora-legal-br não respondeu")


class TestComReserva(unittest.TestCase):
	def test_ntp_direto_confiavel_manda_e_a_reserva_nem_e_consultada(self):
		chamadas = []
		direta = _rodada(True, 5.0)

		rodada = com_reserva(
			direta, "http://hl", lambda: 9.0, lambda url: chamadas.append(url) or RESERVA_BOA
		)

		self.assertIs(rodada, direta)
		self.assertEqual(chamadas, [], "a reserva só entra quando o NTP direto falha")

	def test_sem_url_a_rodada_fica_intacta(self):
		direta = _rodada(False)

		self.assertIs(com_reserva(direta, "", lambda: 9.0, lambda url: RESERVA_BOA), direta)

	def test_ntp_direto_cego_usa_a_reserva_e_registra_o_porque(self):
		rodada = com_reserva(_rodada(False), "http://hl", lambda: 9.0, lambda url: RESERVA_BOA)

		self.assertEqual(rodada.medicao, RESERVA_BOA)
		self.assertEqual(rodada.medida_em, 9.0, "a idade da medição conta da reserva")
		self.assertIn("reserva", rodada.erros["hora-legal-br"])
		self.assertIn("a.st1.ntp.br", rodada.erros, "o erro do NTP direto não se perde")

	def test_reserva_tambem_falha_mantem_a_medicao_direta_e_anota_o_motivo(self):
		direta = _rodada(False)
		rodada = com_reserva(direta, "http://hl", lambda: 9.0, lambda url: RESERVA_RUIM)

		self.assertEqual(rodada.medicao, direta.medicao, "reserva ruim nunca piora a situação")
		self.assertEqual(rodada.erros["hora-legal-br"], "hora-legal-br não respondeu")


class TestIndependencia(unittest.TestCase):
	def test_nao_importa_frappe_nem_o_sus_brasil(self):
		import ast
		from pathlib import Path

		fonte = Path(__file__).resolve().parent.parent / "integracao" / "hora_legal_br.py"
		importados = {
			(n.module or "").split(".")[0] if isinstance(n, ast.ImportFrom) else a.name.split(".")[0]
			for n in ast.walk(ast.parse(fonte.read_text(encoding="utf-8")))
			if isinstance(n, (ast.Import, ast.ImportFrom))
			for a in (getattr(n, "names", None) or [None])
		}

		self.assertNotIn("frappe", importados)
		self.assertNotIn("sus_brasil", importados, "erpnext_brasil não pode depender do núcleo SUS")


if __name__ == "__main__":
	unittest.main()
