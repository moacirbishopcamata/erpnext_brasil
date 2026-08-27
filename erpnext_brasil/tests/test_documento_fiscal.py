# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes do ciclo de vida do documento fiscal e da porta de transmissão.

Os testes que mais importam aqui não são os do caminho feliz: são os que provam que o
agregado **recusa** a transição impossível. Nota cancelada sem nunca ter sido autorizada,
ou autorizada sem protocolo, é o tipo de estado que passa despercebido por meses e só
aparece na fiscalização.

O teste de ida e volta (`TestCosturaComPersistencia`) exercita a costura de que a própria
suíte fala: mutar, projetar, reconstituir e comparar — não só verificar o retorno.
"""

import unittest
from datetime import datetime, timedelta

from erpnext_brasil.fiscal.documento.estado import (
	JUSTIFICATIVA_MAXIMA,
	JUSTIFICATIVA_MINIMA,
	PRAZO_CANCELAMENTO,
	DocumentoFiscal,
	Estado,
	Protocolo,
	TransicaoInvalida,
)
from erpnext_brasil.fiscal.documento.porta import (
	Autorizacao,
	RespostaTransmissao,
	TransporteFiscal,
	aplicar_resposta,
)

AGORA = datetime(2026, 8, 24, 10, 0, 0)
JUSTIFICATIVA = "Erro de digitacao no valor do item"


def novo() -> DocumentoFiscal:
	return DocumentoFiscal(numero="123", serie="1")


def autorizado(em: datetime = AGORA) -> DocumentoFiscal:
	doc = novo()
	doc.transmitir()
	doc.autorizar(Protocolo(numero="135260000123456", recebido_em=em, chave_acesso="35" + "0" * 42))

	return doc


class TestFluxoFeliz(unittest.TestCase):
	def test_nasce_rascunho(self):
		self.assertIs(novo().estado, Estado.RASCUNHO)

	def test_transmitir_leva_a_aguardando(self):
		doc = novo()
		doc.transmitir()

		self.assertIs(doc.estado, Estado.AGUARDANDO)

	def test_autorizar_guarda_o_protocolo(self):
		doc = autorizado()

		self.assertIs(doc.estado, Estado.AUTORIZADO)
		self.assertTrue(doc.autorizado)
		self.assertEqual(doc.protocolo.numero, "135260000123456")

	def test_cancelar_dentro_do_prazo(self):
		doc = autorizado()
		doc.cancelar(JUSTIFICATIVA, AGORA + timedelta(hours=2))

		self.assertIs(doc.estado, Estado.CANCELADO)
		self.assertEqual(doc.justificativa, JUSTIFICATIVA)


class TestAutorizacaoExigeProtocolo(unittest.TestCase):
	"""A costura crítica: sem protocolo não há autorização."""

	def test_protocolo_vazio_e_erro(self):
		for numero in ("", "   ", None):
			with self.subTest(numero=numero):
				with self.assertRaises(ValueError):
					Protocolo(numero=numero, recebido_em=AGORA)

	def test_autorizar_sem_protocolo_e_erro(self):
		doc = novo()
		doc.transmitir()

		with self.assertRaises(ValueError):
			doc.autorizar(None)

	def test_autorizar_rascunho_e_erro(self):
		"""Autorizar sem transmitir seria afirmar um fato que não aconteceu."""
		with self.assertRaises(TransicaoInvalida):
			novo().autorizar(Protocolo(numero="1", recebido_em=AGORA))


class TestTransicoesRecusadas(unittest.TestCase):
	def test_nao_cancela_rascunho(self):
		with self.assertRaises(TransicaoInvalida) as ctx:
			novo().cancelar(JUSTIFICATIVA, AGORA)

		self.assertIn("autorizado", str(ctx.exception))

	def test_nao_cancela_duas_vezes(self):
		doc = autorizado()
		doc.cancelar(JUSTIFICATIVA, AGORA)

		with self.assertRaises(TransicaoInvalida):
			doc.cancelar(JUSTIFICATIVA, AGORA)

	def test_denegado_e_final(self):
		doc = novo()
		doc.transmitir()
		doc.denegar("Destinatario com irregularidade fiscal")

		self.assertTrue(doc.estado.final)

		for acao in (
			lambda: doc.transmitir(),
			lambda: doc.cancelar(JUSTIFICATIVA, AGORA),
			lambda: doc.autorizar(Protocolo(numero="1", recebido_em=AGORA)),
		):
			with self.assertRaises(TransicaoInvalida):
				acao()

	def test_rejeitado_volta_ao_fluxo(self):
		"""Rejeitado se corrige e reenvia; é o único retorno permitido."""
		doc = novo()
		doc.transmitir()
		doc.rejeitar("Rejeicao 225: falha no schema do XML")

		self.assertIs(doc.estado, Estado.REJEITADO)
		self.assertTrue(doc.estado.permite_reenvio)

		doc.transmitir()
		self.assertIs(doc.estado, Estado.AGUARDANDO)

	def test_reenvio_limpa_o_motivo_anterior(self):
		doc = novo()
		doc.transmitir()
		doc.rejeitar("Rejeicao 225")
		doc.transmitir()

		self.assertEqual(doc.motivo, "")

	def test_rejeicao_e_denegacao_exigem_motivo(self):
		for acao in ("rejeitar", "denegar"):
			with self.subTest(acao=acao):
				doc = novo()
				doc.transmitir()

				with self.assertRaises(ValueError):
					getattr(doc, acao)("   ")


class TestPrazoDeCancelamento(unittest.TestCase):
	def test_prazo_padrao_e_24_horas(self):
		self.assertEqual(PRAZO_CANCELAMENTO, timedelta(hours=24))

	def test_no_limite_ainda_cancela(self):
		doc = autorizado()
		doc.cancelar(JUSTIFICATIVA, AGORA + PRAZO_CANCELAMENTO)

		self.assertIs(doc.estado, Estado.CANCELADO)

	def test_depois_do_prazo_recusa_e_orienta(self):
		doc = autorizado()

		with self.assertRaises(TransicaoInvalida) as ctx:
			doc.cancelar(JUSTIFICATIVA, AGORA + timedelta(hours=25))

		self.assertIn("estorno", str(ctx.exception))

	def test_extemporaneo_exige_pedido_explicito(self):
		"""Até 480h é faculdade de cada UF: não pode acontecer sozinho."""
		doc = autorizado()
		quando = AGORA + timedelta(hours=100)

		with self.assertRaises(TransicaoInvalida):
			doc.cancelar(JUSTIFICATIVA, quando)

		doc.cancelar(JUSTIFICATIVA, quando, permitir_extemporaneo=True)
		self.assertIs(doc.estado, Estado.CANCELADO)

	def test_extemporaneo_tambem_tem_limite(self):
		doc = autorizado()

		with self.assertRaises(TransicaoInvalida):
			doc.cancelar(JUSTIFICATIVA, AGORA + timedelta(hours=481), permitir_extemporaneo=True)


class TestJustificativa(unittest.TestCase):
	"""Limites confirmados no XSD oficial: xJust tem minLength 15 e maxLength 256."""

	def test_limites(self):
		self.assertEqual(JUSTIFICATIVA_MINIMA, 15)
		self.assertEqual(JUSTIFICATIVA_MAXIMA, 256)

	def test_curta_demais_e_erro(self):
		with self.assertRaises(ValueError):
			autorizado().cancelar("Erro", AGORA)

	def test_longa_demais_e_erro(self):
		with self.assertRaises(ValueError):
			autorizado().cancelar("x" * (JUSTIFICATIVA_MAXIMA + 1), AGORA)

	def test_no_limite_minimo_passa(self):
		doc = autorizado()
		doc.cancelar("x" * JUSTIFICATIVA_MINIMA, AGORA)

		self.assertIs(doc.estado, Estado.CANCELADO)

	def test_espaco_nao_conta_para_o_minimo(self):
		with self.assertRaises(ValueError):
			autorizado().cancelar("   Erro   ", AGORA)


class TestReconstituicao(unittest.TestCase):
	def test_recria_do_persistido(self):
		doc = DocumentoFiscal.reconstituir(
			numero="123",
			serie="1",
			estado=Estado.AUTORIZADO,
			protocolo=Protocolo(numero="135", recebido_em=AGORA),
		)

		self.assertTrue(doc.autorizado)

	def test_autorizado_sem_protocolo_e_dado_corrompido(self):
		"""Falhar alto na leitura é melhor que propagar a mentira."""
		for estado in (Estado.AUTORIZADO, Estado.CANCELADO):
			with self.subTest(estado=estado):
				with self.assertRaises(ValueError) as ctx:
					DocumentoFiscal.reconstituir("123", "1", estado)

				self.assertIn("inconsistente", str(ctx.exception))

	def test_rascunho_sem_protocolo_e_normal(self):
		doc = DocumentoFiscal.reconstituir("123", "1", Estado.RASCUNHO)

		self.assertIs(doc.estado, Estado.RASCUNHO)


class TestCosturaComPersistencia(unittest.TestCase):
	"""Muta, projeta, reconstitui e compara — não só verifica o retorno."""

	def test_ida_e_volta_preserva_o_estado(self):
		original = autorizado()
		original.cancelar(JUSTIFICATIVA, AGORA + timedelta(hours=1))

		gravado = original.instantaneo()

		voltou = DocumentoFiscal.reconstituir(
			numero=gravado["numero"],
			serie=gravado["serie"],
			estado=Estado(gravado["estado"]),
			protocolo=Protocolo(
				numero=gravado["protocolo"],
				recebido_em=gravado["protocolo_em"],
				chave_acesso=gravado["chave_acesso"],
			),
			motivo=gravado["motivo"],
			justificativa=gravado["justificativa"],
		)

		self.assertEqual(voltou.instantaneo(), gravado)
		self.assertIs(voltou.estado, Estado.CANCELADO)
		self.assertEqual(voltou.justificativa, JUSTIFICATIVA)

	def test_instantaneo_nao_expoe_o_estado_interno(self):
		doc = autorizado()
		projecao = doc.instantaneo()
		projecao["estado"] = "cancelado"

		self.assertIs(doc.estado, Estado.AUTORIZADO)


class TransporteFalso:
	"""Transporte de teste — devolve o que lhe mandarem devolver."""

	def __init__(self, resposta: RespostaTransmissao):
		self.resposta = resposta
		self.enviados: list[dict] = []

	def transmitir(self, documento: dict) -> RespostaTransmissao:
		self.enviados.append(documento)

		return self.resposta

	def consultar(self, chave_acesso: str):
		raise NotImplementedError

	def cancelar(self, chave_acesso: str, justificativa: str) -> RespostaTransmissao:
		return self.resposta


class TestPorta(unittest.TestCase):
	def test_transporte_falso_satisfaz_o_contrato(self):
		transporte = TransporteFalso(RespostaTransmissao(codigo="100", mensagem="Autorizado"))

		self.assertIsInstance(transporte, TransporteFiscal)

	def test_resposta_autorizada_autoriza_o_documento(self):
		doc = novo()
		doc.transmitir()

		aplicar_resposta(
			doc,
			RespostaTransmissao(
				codigo="100",
				mensagem="Autorizado o uso da NF-e",
				autorizacao=Autorizacao(protocolo="135260000123456", recebido_em=AGORA),
			),
		)

		self.assertTrue(doc.autorizado)
		self.assertEqual(doc.protocolo.numero, "135260000123456")

	def test_resposta_rejeitada_rejeita(self):
		doc = novo()
		doc.transmitir()

		aplicar_resposta(doc, RespostaTransmissao(codigo="225", mensagem="Falha no schema"))

		self.assertIs(doc.estado, Estado.REJEITADO)
		self.assertEqual(doc.motivo, "Falha no schema")

	def test_denegacao_tem_precedencia_sobre_autorizacao(self):
		"""Denegado é final; confundi-lo com rejeição permitiria reenvio indevido."""
		doc = novo()
		doc.transmitir()

		aplicar_resposta(
			doc,
			RespostaTransmissao(
				codigo="302",
				mensagem="Uso denegado por irregularidade do destinatario",
				denegado=True,
				autorizacao=Autorizacao(protocolo="999", recebido_em=AGORA),
			),
		)

		self.assertIs(doc.estado, Estado.DENEGADO)
		self.assertTrue(doc.estado.final)

	def test_resposta_sem_mensagem_usa_o_codigo(self):
		doc = novo()
		doc.transmitir()

		aplicar_resposta(doc, RespostaTransmissao(codigo="999", mensagem=""))

		self.assertIn("999", doc.motivo)


if __name__ == "__main__":
	unittest.main()
