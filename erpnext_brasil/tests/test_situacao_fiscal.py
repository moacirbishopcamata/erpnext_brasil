# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A situação fiscal de um documento, dado tudo o que se transmitiu por ele.

O teste-âncora é `test_carta_de_correcao_nao_reautoriza_documento_cancelado`. Ele existe
porque a implementação ingênua — "pegue o registro mais recente" — passa em quase todos os
outros casos e erra exatamente neste: uma CC-e homologada é gravada como `Autorizado`
(o **evento** foi autorizado), e lida sem olhar o tipo faria uma correção ressuscitar uma
nota cancelada na tela do usuário.

Módulo puro: roda sem bench.
"""

import unittest

from erpnext_brasil.fiscal.documento.situacao_fiscal import (
	SITUACAO_NAO_EMITIDO,
	SITUACOES_DO_DOCUMENTO,
	RegistroLido,
	SituacaoFiscal,
	situacao_do_documento,
)
from erpnext_brasil.fiscal.documento.transmissao_registro import (
	SITUACAO_AUTORIZADO,
	SITUACAO_CANCELADO,
	SITUACAO_DENEGADO,
	SITUACAO_PENDENTE,
	SITUACAO_REJEITADO,
	TIPO_AUTORIZACAO,
	TIPO_CANCELAMENTO,
	TIPO_CARTA_DE_CORRECAO,
	TIPO_CONSULTA,
	TIPO_INUTILIZACAO,
)


def _autorizacao(
	situacao=SITUACAO_AUTORIZADO,
	chave="35240712345678000199550010000000011000000017",
	protocolo="135240000000001",
	nome="TRF-0001",
):
	return RegistroLido(TIPO_AUTORIZACAO, situacao, chave, protocolo, nome)


class TestSemRegistro(unittest.TestCase):
	def test_documento_sem_transmissao_nao_esta_emitido(self):
		situacao = situacao_do_documento([])

		self.assertEqual(SITUACAO_NAO_EMITIDO, situacao.situacao)
		self.assertFalse(situacao.emitido)
		self.assertFalse(situacao.vale)

	def test_nao_emitido_nao_e_rejeitado(self):
		"""Um nunca foi à SEFAZ; o outro foi e voltou. A tela oferece coisas diferentes."""
		self.assertNotEqual(SITUACAO_NAO_EMITIDO, SITUACAO_REJEITADO)

	def test_o_padrao_do_dataclass_e_nao_emitido(self):
		self.assertEqual(SITUACAO_NAO_EMITIDO, SituacaoFiscal().situacao)


class TestAutorizacao(unittest.TestCase):
	def test_autorizada_vale_e_traz_chave_e_protocolo(self):
		situacao = situacao_do_documento([_autorizacao()])

		self.assertEqual(SITUACAO_AUTORIZADO, situacao.situacao)
		self.assertTrue(situacao.vale)
		self.assertTrue(situacao.emitido)
		self.assertEqual("135240000000001", situacao.protocolo)

	def test_rejeitada_nao_esta_emitida(self):
		"""Rejeitado é 'tente de novo': o número continua disponível."""
		situacao = situacao_do_documento([_autorizacao(SITUACAO_REJEITADO, protocolo="")])

		self.assertEqual(SITUACAO_REJEITADO, situacao.situacao)
		self.assertFalse(situacao.emitido)

	def test_denegada_esta_emitida_mas_nao_vale(self):
		"""O número foi consumido — é o que impede reemitir com ele."""
		situacao = situacao_do_documento([_autorizacao(SITUACAO_DENEGADO)])

		self.assertEqual(SITUACAO_DENEGADO, situacao.situacao)
		self.assertTrue(situacao.emitido)
		self.assertFalse(situacao.vale)

	def test_autorizacao_posterior_supera_rejeicao(self):
		"""A segunda tentativa passou; a primeira não deve continuar mandando."""
		situacao = situacao_do_documento(
			[_autorizacao(SITUACAO_REJEITADO, protocolo="", nome="TRF-0001"), _autorizacao(nome="TRF-0002")]
		)

		self.assertEqual(SITUACAO_AUTORIZADO, situacao.situacao)

	def test_a_ordem_dos_registros_nao_muda_o_resultado(self):
		"""A precedência é por tipo, não por ordem de chegada."""
		registros = [_autorizacao(SITUACAO_REJEITADO, protocolo=""), _autorizacao()]

		self.assertEqual(
			situacao_do_documento(registros).situacao,
			situacao_do_documento(list(reversed(registros))).situacao,
		)


class TestCancelamento(unittest.TestCase):
	def test_cancelamento_homologado_vence_a_autorizacao(self):
		situacao = situacao_do_documento(
			[_autorizacao(), RegistroLido(TIPO_CANCELAMENTO, SITUACAO_CANCELADO, nome="TRF-0002")]
		)

		self.assertEqual(SITUACAO_CANCELADO, situacao.situacao)
		self.assertFalse(situacao.vale)
		self.assertTrue(situacao.emitido)

	def test_cancelamento_rejeitado_nao_cancela(self):
		"""A tentativa falhou: a nota continua valendo, e dizer o contrário na tela faria
		o usuário parar de faturar por engano."""
		situacao = situacao_do_documento(
			[_autorizacao(), RegistroLido(TIPO_CANCELAMENTO, SITUACAO_REJEITADO, nome="TRF-0002")]
		)

		self.assertEqual(SITUACAO_AUTORIZADO, situacao.situacao)
		self.assertTrue(situacao.vale)

	def test_cancelado_mantem_a_chave_e_o_protocolo_da_autorizacao(self):
		"""Sem eles o usuário fica sem o que informar ao contador."""
		situacao = situacao_do_documento(
			[_autorizacao(), RegistroLido(TIPO_CANCELAMENTO, SITUACAO_CANCELADO, protocolo="999")]
		)

		self.assertEqual("135240000000001", situacao.protocolo)
		self.assertTrue(situacao.chave_acesso)


class TestCartaDeCorrecao(unittest.TestCase):
	"""Correção emenda texto; não muda situação nenhuma."""

	def test_carta_de_correcao_nao_reautoriza_documento_cancelado(self):
		"""Teste-âncora: a CC-e é gravada como `Autorizado` porque o **evento** foi
		autorizado. Ler o registro mais recente ressuscitaria a nota cancelada."""
		situacao = situacao_do_documento(
			[
				_autorizacao(),
				RegistroLido(TIPO_CANCELAMENTO, SITUACAO_CANCELADO, nome="TRF-0002"),
				RegistroLido(TIPO_CARTA_DE_CORRECAO, SITUACAO_AUTORIZADO, nome="TRF-0003"),
			]
		)

		self.assertEqual(SITUACAO_CANCELADO, situacao.situacao)

	def test_carta_de_correcao_sozinha_nao_emite_nada(self):
		situacao = situacao_do_documento([RegistroLido(TIPO_CARTA_DE_CORRECAO, SITUACAO_AUTORIZADO)])

		self.assertEqual(SITUACAO_NAO_EMITIDO, situacao.situacao)

	def test_as_cartas_homologadas_sao_contadas(self):
		"""Quantas houve importa: cada nova precisa repetir o texto das anteriores."""
		situacao = situacao_do_documento(
			[
				_autorizacao(),
				RegistroLido(TIPO_CARTA_DE_CORRECAO, SITUACAO_AUTORIZADO),
				RegistroLido(TIPO_CARTA_DE_CORRECAO, SITUACAO_AUTORIZADO),
			]
		)

		self.assertEqual(2, situacao.cartas_de_correcao)
		self.assertEqual(SITUACAO_AUTORIZADO, situacao.situacao)

	def test_carta_rejeitada_nao_e_contada(self):
		situacao = situacao_do_documento(
			[_autorizacao(), RegistroLido(TIPO_CARTA_DE_CORRECAO, SITUACAO_REJEITADO)]
		)

		self.assertEqual(0, situacao.cartas_de_correcao)


class TestTiposQueNaoAfirmamNada(unittest.TestCase):
	def test_consulta_e_inutilizacao_nao_mudam_a_situacao(self):
		"""Inutilização é sobre uma **faixa de numeração**, não sobre este documento."""
		for tipo in (TIPO_CONSULTA, TIPO_INUTILIZACAO):
			with self.subTest(tipo=tipo):
				situacao = situacao_do_documento([_autorizacao(), RegistroLido(tipo, SITUACAO_AUTORIZADO)])

				self.assertEqual(SITUACAO_AUTORIZADO, situacao.situacao)

	def test_pendente_nao_afirma_emissao(self):
		"""Transmitido e sem resposta não é emitido — anunciar que é convidaria a
		reemitir por cima de algo que talvez tenha passado."""
		situacao = situacao_do_documento([_autorizacao(SITUACAO_PENDENTE, protocolo="")])

		self.assertEqual(SITUACAO_NAO_EMITIDO, situacao.situacao)
		self.assertFalse(situacao.emitido)

	def test_todos_os_registros_sao_contados_mesmo_os_ignorados(self):
		"""O usuário precisa saber que há histórico, ainda que ele não decida nada."""
		situacao = situacao_do_documento(
			[
				RegistroLido(TIPO_CONSULTA, SITUACAO_AUTORIZADO),
				RegistroLido(TIPO_CONSULTA, SITUACAO_AUTORIZADO),
			]
		)

		self.assertEqual(2, situacao.registros)


class TestVocabulario(unittest.TestCase):
	def test_a_precedencia_esta_declarada_em_ordem_crescente(self):
		"""A ordem **é** a regra; se ela deixar de ser lida como dado, volta a virar `if`
		espalhado — que foi o que este módulo existe para não ter."""
		self.assertEqual(SITUACAO_NAO_EMITIDO, SITUACOES_DO_DOCUMENTO[0])
		self.assertEqual(SITUACAO_CANCELADO, SITUACOES_DO_DOCUMENTO[-1])

	def test_toda_situacao_produzida_esta_declarada(self):
		"""Situação fora da tupla não teria cor nem rótulo na tela."""
		casos = [
			[],
			[_autorizacao()],
			[_autorizacao(SITUACAO_REJEITADO)],
			[_autorizacao(SITUACAO_DENEGADO)],
			[_autorizacao(), RegistroLido(TIPO_CANCELAMENTO, SITUACAO_CANCELADO)],
		]

		for registros in casos:
			with self.subTest(registros=len(registros)):
				self.assertIn(situacao_do_documento(registros).situacao, SITUACOES_DO_DOCUMENTO)


if __name__ == "__main__":
	unittest.main()
