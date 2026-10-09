# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""`TransporteSefaz.transmitir_cte`: o CT-e passa pela mesma guarda e pelo mesmo registrador da NF-e.

Tarefas 3.1 (o método existe e delega ao módulo do CT-e) e 3.3 (a guarda de consumo indevido
recusa **antes** de qualquer chamada à SEFAZ). O `cStat 656` vale para os três documentos (NF-e,
CT-e, MDF-e) e a porta é uma só — `design.md`, decisão 3 —, então repetir a guarda num caminho
próprio do CT-e seria cinco chances de esquecê-la; ela fica em `_contexto`.

Teste-âncora: `test_a_guarda_recusa_antes_de_chamar_a_sefaz` conta as chamadas à sessão HTTP: zero.
"""

import unittest

from erpnext_brasil.tests.test_autorizacao_sefaz_cte import CHAVE, CTE, SessaoFalsa, _autorizado
from erpnext_brasil.tests.test_resposta_cte import _ret
from erpnext_brasil.tests.test_transporte_sefaz import TEM_DEPENDENCIAS, _gerar_pfx

CNPJ = "11222333000181"


class Bloqueado(Exception):
	pass


@unittest.skipUnless(TEM_DEPENDENCIAS, "requer cryptography, disponível no bench")
class TestTransmitirCte(unittest.TestCase):
	def _transporte(self, sessao, **extras):
		from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

		return TransporteSefaz(
			_gerar_pfx(), "teste123", "RO", CNPJ, ambiente="homologacao", sessao=sessao, **extras
		)

	def test_transmite_em_uma_chamada_e_devolve_a_autorizacao(self):
		sessao = SessaoFalsa(_autorizado())

		with self._transporte(sessao) as transporte:
			resposta = transporte.transmitir_cte(CTE)

		self.assertEqual(len(sessao.chamadas), 1)
		self.assertTrue(resposta.autorizada)
		self.assertEqual(resposta.autorizacao.chave_acesso, CHAVE)

	def test_vai_ao_servico_do_cte_e_nao_ao_da_nfe(self):
		sessao = SessaoFalsa(_autorizado())

		with self._transporte(sessao) as transporte:
			transporte.transmitir_cte(CTE)

		self.assertIn("CTeRecepcaoSincV4", sessao.chamadas[0]["url"])
		self.assertNotIn("NFeAutorizacao", sessao.chamadas[0]["url"])

	def test_a_guarda_recusa_antes_de_chamar_a_sefaz(self):
		"""Teste-âncora da 3.3: bloqueado, a requisição **não sai** — a que sair na janela
		reiniciaria a contagem de uma hora."""
		sessao = SessaoFalsa(_autorizado())
		consultas = []

		def guarda(cnpj, ambiente):
			consultas.append((cnpj, ambiente))
			raise Bloqueado("janela aberta")

		with self.assertRaises(Bloqueado), self._transporte(sessao, guarda=guarda) as transporte:
			transporte.transmitir_cte(CTE)

		self.assertEqual(consultas, [(CNPJ, "homologacao")])
		self.assertEqual(sessao.chamadas, [], "a guarda não impediu a requisição")

	def test_o_registrador_recebe_o_codigo_da_resposta(self):
		"""É assim que o `656` do CT-e abre a janela de bloqueio, igual ao da NF-e."""
		anotado = []
		sessao = SessaoFalsa(_ret("656", "Consumo Indevido"))

		with self._transporte(sessao, registrador=lambda *args: anotado.append(args)) as transporte:
			resposta = transporte.transmitir_cte(CTE)

		self.assertEqual(resposta.codigo, "656")
		self.assertEqual(anotado, [(CNPJ, "homologacao", "656", "Consumo Indevido")])

	def test_o_registrador_tambem_ve_a_autorizacao(self):
		anotado = []

		with self._transporte(
			SessaoFalsa(_autorizado()), registrador=lambda *args: anotado.append(args)
		) as transporte:
			transporte.transmitir_cte(CTE)

		self.assertEqual([a[2] for a in anotado], ["100"])

	def test_sem_guarda_nem_registrador_funciona(self):
		"""`None` é o padrão (adaptador sem banco, em teste) — não é omissão."""
		with self._transporte(SessaoFalsa(_autorizado())) as transporte:
			self.assertTrue(transporte.transmitir_cte(CTE).autorizada)


if __name__ == "__main__":
	unittest.main()
