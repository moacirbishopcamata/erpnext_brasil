# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_retorno.py` — leitura da resposta de envio e de
processamento de lote do eSocial."""

import unittest

from erpnext_brasil.folha.esocial_retorno import (
	CODIGO_ERRO_PREENCHIMENTO,
	CODIGO_LOTE_JA_RECEBIDO_EM_FILA,
	CODIGO_LOTE_RECEBIDO_COM_ADVERTENCIAS,
	CODIGO_LOTE_RECEBIDO_SUCESSO,
	LIMITE_MAXIMO_EVENTOS_NO_RETORNO,
	TIPO_OCORRENCIA_AVISO,
	TIPO_OCORRENCIA_ERRO,
	DadosRecepcaoLote,
	EsocialRetornoInvalido,
	Ocorrencia,
	RetornoEnvioLote,
	RetornoEvento,
	RetornoProcessamentoLote,
	StatusRetorno,
	eventos_com_erro,
)


class TestOcorrencia(unittest.TestCase):
	def test_erro_valido(self):
		Ocorrencia(codigo=1, descricao="CPF inválido", tipo=TIPO_OCORRENCIA_ERRO)

	def test_aviso_valido(self):
		Ocorrencia(codigo=2, descricao="Campo opcional ausente", tipo=TIPO_OCORRENCIA_AVISO)

	def test_tipo_invalido_e_erro(self):
		with self.assertRaises(EsocialRetornoInvalido):
			Ocorrencia(codigo=1, descricao="x", tipo=3)

	def test_descricao_grande_demais_e_erro(self):
		with self.assertRaises(EsocialRetornoInvalido):
			Ocorrencia(codigo=1, descricao="x" * 2049, tipo=TIPO_OCORRENCIA_ERRO)


class TestStatusRetorno(unittest.TestCase):
	def test_sucesso_puro(self):
		status = StatusRetorno(cd_resposta=CODIGO_LOTE_RECEBIDO_SUCESSO, desc_resposta="Lote recebido com sucesso")

		self.assertTrue(status.sucesso)
		self.assertFalse(status.pendente)
		self.assertFalse(status.tem_erro)

	def test_sucesso_com_advertencias_ainda_e_sucesso(self):
		status = StatusRetorno(
			cd_resposta=CODIGO_LOTE_RECEBIDO_COM_ADVERTENCIAS, desc_resposta="Lote recebido com advertências"
		)

		self.assertTrue(status.sucesso)

	def test_pendente(self):
		status = StatusRetorno(cd_resposta=CODIGO_LOTE_JA_RECEBIDO_EM_FILA, desc_resposta="Em processamento")

		self.assertTrue(status.pendente)
		self.assertFalse(status.sucesso)

	def test_erro_de_preenchimento_nao_e_sucesso_nem_pendente(self):
		status = StatusRetorno(cd_resposta=CODIGO_ERRO_PREENCHIMENTO, desc_resposta="Erro de preenchimento")

		self.assertFalse(status.sucesso)
		self.assertFalse(status.pendente)

	def test_codigo_desconhecido_nao_e_sucesso_nem_pendente(self):
		status = StatusRetorno(cd_resposta=999, desc_resposta="Código nunca visto")

		self.assertFalse(status.sucesso)
		self.assertFalse(status.pendente)

	def test_tem_erro_reflete_as_ocorrencias(self):
		com_erro = StatusRetorno(
			cd_resposta=CODIGO_ERRO_PREENCHIMENTO,
			desc_resposta="Erro",
			ocorrencias=(Ocorrencia(codigo=1, descricao="CPF inválido", tipo=TIPO_OCORRENCIA_ERRO),),
		)
		so_aviso = StatusRetorno(
			cd_resposta=CODIGO_LOTE_RECEBIDO_COM_ADVERTENCIAS,
			desc_resposta="Aviso",
			ocorrencias=(Ocorrencia(codigo=2, descricao="Aviso", tipo=TIPO_OCORRENCIA_AVISO),),
		)

		self.assertTrue(com_erro.tem_erro)
		self.assertFalse(so_aviso.tem_erro)

	def test_desc_resposta_grande_demais_e_erro(self):
		with self.assertRaises(EsocialRetornoInvalido):
			StatusRetorno(cd_resposta=201, desc_resposta="x" * 2049)


class TestDadosRecepcaoLote(unittest.TestCase):
	def test_valido(self):
		DadosRecepcaoLote(protocolo_envio="1.2.202601010000000000001")

	def test_vazio_e_erro(self):
		with self.assertRaises(EsocialRetornoInvalido):
			DadosRecepcaoLote(protocolo_envio="")

	def test_grande_demais_e_erro(self):
		with self.assertRaises(EsocialRetornoInvalido):
			DadosRecepcaoLote(protocolo_envio="1" * 31)


class TestRetornoEnvioLote(unittest.TestCase):
	def test_sucesso_com_protocolo(self):
		retorno = RetornoEnvioLote(
			status=StatusRetorno(cd_resposta=CODIGO_LOTE_RECEBIDO_SUCESSO, desc_resposta="OK"),
			dados_recepcao=DadosRecepcaoLote(protocolo_envio="1.2.202601010000000000001"),
		)

		self.assertTrue(retorno.status.sucesso)
		self.assertIsNotNone(retorno.dados_recepcao)

	def test_erro_sem_protocolo(self):
		retorno = RetornoEnvioLote(
			status=StatusRetorno(cd_resposta=CODIGO_ERRO_PREENCHIMENTO, desc_resposta="Erro de preenchimento")
		)

		self.assertFalse(retorno.status.sucesso)
		self.assertIsNone(retorno.dados_recepcao)


class TestRetornoEvento(unittest.TestCase):
	def test_valido(self):
		RetornoEvento(
			id_evento="ID1",
			status=StatusRetorno(cd_resposta=CODIGO_LOTE_RECEBIDO_SUCESSO, desc_resposta="OK"),
		)

	def test_id_vazio_e_erro(self):
		with self.assertRaises(EsocialRetornoInvalido):
			RetornoEvento(id_evento="", status=StatusRetorno(cd_resposta=201, desc_resposta="OK"))

	def test_evento_duplicado_e_registrado(self):
		evento = RetornoEvento(
			id_evento="ID1",
			status=StatusRetorno(cd_resposta=CODIGO_LOTE_RECEBIDO_SUCESSO, desc_resposta="OK"),
			evento_duplicado=True,
		)

		self.assertTrue(evento.evento_duplicado)


class TestRetornoProcessamentoLote(unittest.TestCase):
	def _evento_ok(self, n=1):
		return RetornoEvento(
			id_evento=f"ID{n}", status=StatusRetorno(cd_resposta=CODIGO_LOTE_RECEBIDO_SUCESSO, desc_resposta="OK")
		)

	def _evento_com_erro(self, n=1):
		return RetornoEvento(
			id_evento=f"ID{n}",
			status=StatusRetorno(
				cd_resposta=CODIGO_ERRO_PREENCHIMENTO,
				desc_resposta="Erro",
				ocorrencias=(Ocorrencia(codigo=1, descricao="CPF inválido", tipo=TIPO_OCORRENCIA_ERRO),),
			),
		)

	def test_valido(self):
		RetornoProcessamentoLote(
			status=StatusRetorno(cd_resposta=CODIGO_LOTE_RECEBIDO_SUCESSO, desc_resposta="OK"),
			eventos=(self._evento_ok(),),
		)

	def test_mais_de_50_eventos_e_erro(self):
		eventos = tuple(self._evento_ok(n) for n in range(LIMITE_MAXIMO_EVENTOS_NO_RETORNO + 1))

		with self.assertRaises(EsocialRetornoInvalido):
			RetornoProcessamentoLote(
				status=StatusRetorno(cd_resposta=CODIGO_LOTE_RECEBIDO_SUCESSO, desc_resposta="OK"), eventos=eventos
			)

	def test_eventos_com_erro_filtra_corretamente(self):
		lote = RetornoProcessamentoLote(
			status=StatusRetorno(cd_resposta=CODIGO_LOTE_RECEBIDO_COM_ADVERTENCIAS, desc_resposta="Parcial"),
			eventos=(self._evento_ok(1), self._evento_com_erro(2), self._evento_ok(3)),
		)

		com_erro = eventos_com_erro(lote)

		self.assertEqual(len(com_erro), 1)
		self.assertEqual(com_erro[0].id_evento, "ID2")

	def test_eventos_com_erro_vazio_quando_tudo_ok(self):
		lote = RetornoProcessamentoLote(
			status=StatusRetorno(cd_resposta=CODIGO_LOTE_RECEBIDO_SUCESSO, desc_resposta="OK"),
			eventos=(self._evento_ok(1), self._evento_ok(2)),
		)

		self.assertEqual(eventos_com_erro(lote), ())


if __name__ == "__main__":
	unittest.main()
