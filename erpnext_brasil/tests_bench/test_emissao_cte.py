# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste real (bench) de `emitir_cte`: o desfecho da SEFAZ vira `Transmissao Fiscal` no banco.

Tarefa 3.2 de `fechar-laco-cte-mdfe`. O transporte é **falso** (nenhum byte sai para a SEFAZ) e o
certificado/assinatura são substituídos: o que se prova aqui é a costura Frappe — o registro
gravado em todo desfecho, a chave/protocolo na fatura — e não o envelope, coberto na suíte pura.

Teste-âncora: `test_a_rejeicao_deixa_o_registro_mesmo_apos_o_rollback`
--------------------------------------------------------------------------
`frappe.throw` desfaz a transação. Sem o `commit` antes dele, o `Transmissao Fiscal` da rejeição
sumiria junto — e o teste só vê isso se der `rollback` e reler por `frappe.get_all`, outro caminho
que não o objeto que a função devolveu.

Como rodar
-----------------
    bench --site v16.localhost run-tests \
        --module erpnext_brasil.tests_bench.test_emissao_cte
"""

from datetime import datetime
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.fiscal.documento.porta import Autorizacao, RespostaTransmissao
from erpnext_brasil.integracao.emissao_cte import emitir_cte
from erpnext_brasil.integracao.situacao_fiscal import situacao_fiscal
from erpnext_brasil.tests_bench.test_cte_documento import CONTADOR, TestCteDocumento

MODULOS_COBERTOS = ("emissao_cte", "guarda_de_relogio")
"""Declarados, não inferidos — ver `scripts/cobertura_de_bench.py`."""

PROTOCOLO = "311260000000001"


class TransporteFalso:
	"""Responde o que o teste mandar e conta as chamadas. Ignora os argumentos de construção."""

	resposta = None
	chamadas = 0

	def __init__(self, *args, **kwargs):
		pass

	def transmitir_cte(self, documento):
		type(self).chamadas += 1
		chave = documento["CTe"]["infCte"]["@Id"].removeprefix("CTe")
		modelo = type(self).resposta

		if modelo == "autorizado":
			return RespostaTransmissao(
				codigo="100",
				mensagem="Autorizado o uso do CT-e",
				autorizacao=Autorizacao(
					protocolo=PROTOCOLO, recebido_em=datetime.now().astimezone(), chave_acesso=chave
				),
				bruto={"cStat": "100", "nProt": PROTOCOLO},
			)

		if modelo == "denegado":
			return RespostaTransmissao(
				codigo="110", mensagem="Uso Denegado", denegado=True, bruto={"cStat": "110"}
			)

		return RespostaTransmissao(codigo="539", mensagem="Rejeição: duplicidade", bruto={"cStat": "539"})


class TestEmissaoCte(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		TestCteDocumento.setUpClass()

	def setUp(self):
		TransporteFalso.chamadas = 0
		self._faturas = []

		for alvo, substituto in (
			("TransporteSefaz", TransporteFalso),
			("carregar_certificado_da_empresa", lambda company: (b"", "")),
			("AssinadorLocal", lambda pfx, senha: None),
			("assinar_cte", lambda arvore, assinador: arvore),
		):
			patcher = mock.patch(f"erpnext_brasil.integracao.emissao_cte.{alvo}", substituto)
			patcher.start()
			self.addCleanup(patcher.stop)

	def tearDown(self):
		# O código sob teste faz `commit`; a limpeza também tem de ser explícita.
		for fatura in self._faturas:
			frappe.db.delete("Transmissao Fiscal", {"documento": fatura})

		frappe.db.commit()

	def _fatura(self):
		fatura = TestCteDocumento._fatura(self)
		self._faturas.append(fatura.name)

		return fatura

	def _registros(self, fatura: str) -> list[dict]:
		return frappe.get_all(
			"Transmissao Fiscal",
			filters={"documento_tipo": "Sales Invoice", "documento": fatura},
			fields=["situacao", "codigo_status", "chave_acesso", "protocolo", "tipo", "xml_retorno"],
		)

	def test_autorizado_grava_registro_e_chave_e_protocolo_na_fatura(self):
		fatura = self._fatura()
		TransporteFalso.resposta = "autorizado"

		resultado = emitir_cte("Sales Invoice", fatura.name)

		registros = self._registros(fatura.name)
		self.assertEqual(len(registros), 1)
		self.assertEqual(registros[0].situacao, "Autorizado")
		self.assertEqual(registros[0].protocolo, PROTOCOLO)
		self.assertEqual(registros[0].tipo, "Autorização")
		self.assertIn("100", registros[0].xml_retorno)

		# Releitura por outro caminho: o `db_set` que não persistiu só aparece aqui.
		chave, protocolo = frappe.db.get_value(
			"Sales Invoice", fatura.name, ["br_chave_acesso", "br_protocolo_autorizacao"]
		)
		self.assertEqual(chave, resultado["chave_acesso"])
		self.assertEqual(chave, registros[0].chave_acesso)
		self.assertEqual(len(chave), 44)
		self.assertEqual(protocolo, PROTOCOLO)

	def test_a_rejeicao_deixa_o_registro_mesmo_apos_o_rollback(self):
		fatura = self._fatura()
		TransporteFalso.resposta = "rejeitado"

		with self.assertRaises(frappe.ValidationError):
			emitir_cte("Sales Invoice", fatura.name)

		frappe.db.rollback()

		registros = self._registros(fatura.name)
		self.assertEqual([r.situacao for r in registros], ["Rejeitado"])
		self.assertEqual(registros[0].codigo_status, "539")
		self.assertFalse(frappe.db.get_value("Sales Invoice", fatura.name, "br_chave_acesso"))

	def test_denegado_e_registrado_como_denegado_e_nao_como_rejeitado(self):
		fatura = self._fatura()
		TransporteFalso.resposta = "denegado"

		with self.assertRaises(frappe.ValidationError):
			emitir_cte("Sales Invoice", fatura.name)

		frappe.db.rollback()

		self.assertEqual([r.situacao for r in self._registros(fatura.name)], ["Denegado"])

	def test_nao_reenvia_o_que_ja_foi_autorizado(self):
		fatura = self._fatura()
		TransporteFalso.resposta = "autorizado"
		emitir_cte("Sales Invoice", fatura.name)

		with self.assertRaises(frappe.ValidationError):
			emitir_cte("Sales Invoice", fatura.name)

		self.assertEqual(TransporteFalso.chamadas, 1)
		self.assertEqual(len(self._registros(fatura.name)), 1)

	def test_dado_ausente_recusa_sem_chamar_a_sefaz_e_sem_registro(self):
		fatura = self._fatura()
		frappe.db.set_value("Sales Invoice", fatura.name, "br_remetente_cte", None)
		TransporteFalso.resposta = "autorizado"

		with self.assertRaises(frappe.ValidationError) as contexto:
			emitir_cte("Sales Invoice", fatura.name)

		self.assertIn("[1206]", str(contexto.exception))
		self.assertEqual(TransporteFalso.chamadas, 0)
		self.assertEqual(self._registros(fatura.name), [])

	def test_a_situacao_do_cte_nao_vaza_para_a_da_nfe(self):
		"""Costura da 3.5: a tela de NF-e e a de CT-e perguntam pela mesma fatura, cada uma pela sua família."""
		fatura = self._fatura()
		TransporteFalso.resposta = "autorizado"
		emitir_cte("Sales Invoice", fatura.name)

		do_cte = situacao_fiscal("Sales Invoice", fatura.name, "cte")
		da_nfe = situacao_fiscal("Sales Invoice", fatura.name)

		self.assertEqual((do_cte["situacao"], do_cte["vale"]), ("Autorizado", True))
		self.assertEqual(do_cte["protocolo"], PROTOCOLO)
		self.assertEqual((da_nfe["situacao"], da_nfe["emitido"]), ("Não emitido", False))


class TestGuardaDeRelogioNaEmissao(FrappeTestCase):
	"""A guarda de relógio (`fonte-de-tempo-ntp-br`, 4.2) no ponto de emissão, com o cache real.

	Teste-âncora: `test_relogio_critico_recusa_sem_consumir_numero_nem_chamar_a_sefaz`. A recusa só
	protege a série se vier antes da alocação do número; o contador relido do banco prova isso.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		TestCteDocumento.setUpClass()

	def setUp(self):
		TransporteFalso.chamadas = 0
		TransporteFalso.resposta = "autorizado"
		self._faturas = []
		self._limpar()
		self.addCleanup(self._limpar)

		emissao = "erpnext_brasil.integracao.emissao_cte"
		for alvo, substituto in (
			(f"{emissao}.TransporteSefaz", TransporteFalso),
			(f"{emissao}.carregar_certificado_da_empresa", lambda company: (b"", "")),
			(f"{emissao}.AssinadorLocal", lambda pfx, senha: None),
			(f"{emissao}.assinar_cte", lambda arvore, assinador: arvore),
		):
			patcher = mock.patch(alvo, substituto)
			patcher.start()
			self.addCleanup(patcher.stop)

	def tearDown(self):
		for fatura in self._faturas:
			frappe.db.delete("Transmissao Fiscal", {"documento": fatura})

		frappe.db.commit()

	def _limpar(self):
		from erpnext_brasil.integracao import medicao_do_relogio as relogio

		relogio._cache().delete_value(relogio.CHAVE_ULTIMA)

	def _medicao(self, desvio_ms: float | None, *, confiavel: bool = True, idade_s: float = 30) -> None:
		import time

		from erpnext_brasil.fiscal.tempo_ntp import Medicao
		from erpnext_brasil.integracao.medicao_do_relogio import guardar
		from erpnext_brasil.integracao.relogio_oficial import Rodada

		medicao = Medicao(desvio_ms, confiavel, 3, 3, 4.0, "" if confiavel else "fontes divergem")
		guardar(Rodada(medicao=medicao, medida_em=time.time() - idade_s))

	def _fatura(self):
		fatura = TestCteDocumento._fatura(self)
		self._faturas.append(fatura.name)

		return fatura

	def _ultimo_numero(self) -> int:
		return frappe.db.get_value("Numeracao Fiscal", CONTADOR, "ultimo_numero") or 0

	def test_relogio_critico_recusa_sem_consumir_numero_nem_chamar_a_sefaz(self):
		fatura = self._fatura()
		antes = self._ultimo_numero()
		self._medicao(90_000.0)

		with self.assertRaises(frappe.ValidationError) as contexto:
			emitir_cte("Sales Invoice", fatura.name)

		self.assertIn("Emissão recusada", str(contexto.exception))
		self.assertIn("90.0 s", str(contexto.exception))
		self.assertEqual(TransporteFalso.chamadas, 0, "a SEFAZ foi chamada com o relógio errado")
		self.assertEqual(self._ultimo_numero(), antes, "a recusa consumiu número da série")
		self.assertFalse(frappe.db.get_value("Sales Invoice", fatura.name, "br_numero_cte"))
		self.assertEqual(frappe.db.count("Transmissao Fiscal", {"documento": fatura.name}), 0)

	def test_a_recusa_vem_antes_ate_de_ler_o_documento(self):
		"""Primeira instrução: um nome que nem existe recusa pelo relógio, não por 'não encontrado'."""
		self._medicao(90_000.0)

		with self.assertRaises(frappe.ValidationError) as contexto:
			emitir_cte("Sales Invoice", "nao-existe-este-documento")

		self.assertIn("Emissão recusada", str(contexto.exception))

	def test_a_nfe_tambem_e_protegida(self):
		from erpnext_brasil.integracao.emissao_nfe import emitir_nfe

		self._medicao(-90_000.0)

		with self.assertRaises(frappe.ValidationError) as contexto:
			emitir_nfe("Sales Invoice", "nao-existe-este-documento")

		self.assertIn("adiantado", str(contexto.exception))

	def test_desvio_entre_os_limites_emite_e_avisa(self):
		fatura = self._fatura()
		self._medicao(2500.0)
		frappe.local.message_log = []

		resultado = emitir_cte("Sales Invoice", fatura.name)

		self.assertEqual(resultado["situacao"], "Autorizado")
		self.assertEqual(TransporteFalso.chamadas, 1)
		self.assertTrue(any("Hora Legal" in str(m) for m in frappe.local.message_log))

	def test_relogio_certo_emite_sem_aviso(self):
		fatura = self._fatura()
		self._medicao(40.0)
		frappe.local.message_log = []

		emitir_cte("Sales Invoice", fatura.name)

		self.assertFalse(any("Hora Legal" in str(m) for m in frappe.local.message_log))

	def test_sem_medicao_nao_bloqueia(self):
		fatura = self._fatura()

		self.assertEqual(emitir_cte("Sales Invoice", fatura.name)["situacao"], "Autorizado")

	def test_medicao_vencida_ou_nao_confiavel_nao_bloqueia_mesmo_com_desvio_enorme(self):
		for nome, argumentos in (
			("vencida", {"idade_s": 10 * 3600}),
			("nao confiavel", {"confiavel": False}),
		):
			with self.subTest(caso=nome):
				fatura = self._fatura()
				self._medicao(999_999.0, **argumentos)
				TransporteFalso.chamadas = 0

				emitir_cte("Sales Invoice", fatura.name)

				self.assertEqual(TransporteFalso.chamadas, 1)

	def test_guarda_desligada_emite_mesmo_com_relogio_critico(self):
		fatura = self._fatura()
		self._medicao(90_000.0)

		with mock.patch.dict(frappe.conf, {"brasil_ntp_guarda": False}):
			resultado = emitir_cte("Sales Invoice", fatura.name)

		self.assertEqual(resultado["situacao"], "Autorizado")

	def test_o_limite_critico_vem_da_configuracao(self):
		fatura = self._fatura()
		self._medicao(5000.0)

		with mock.patch.dict(frappe.conf, {"brasil_ntp_limite_critico_ms": 3000}):
			with self.assertRaises(frappe.ValidationError):
				emitir_cte("Sales Invoice", fatura.name)

	# ---------------------------------------------------------------- correção do instante (5.1 e 5.2)

	def _registro(self, fatura: str) -> dict:
		return frappe.get_all(
			"Transmissao Fiscal",
			filters={"documento": fatura, "tipo": "Autorização"},
			fields=["deslocamento_relogio_ms", "instante_corrigido", "xml_enviado"],
		)[0]

	def _dhemi(self, xml: str):
		import re
		from datetime import datetime as _datetime

		return _datetime.fromisoformat(re.search(r"<dhEmi>([^<]+)</dhEmi>", xml).group(1))

	def test_correcao_desligada_nao_grava_deslocamento_e_usa_o_relogio_do_servidor(self):
		from datetime import datetime as _datetime

		fatura = self._fatura()
		self._medicao(3000.0)
		antes = _datetime.now().astimezone()

		emitir_cte("Sales Invoice", fatura.name)

		registro = self._registro(fatura.name)
		self.assertEqual(registro.instante_corrigido, 0)
		self.assertAlmostEqual((self._dhemi(registro.xml_enviado) - antes).total_seconds(), 0, delta=5)

	def test_correcao_ligada_soma_o_deslocamento_medido_e_o_registra(self):
		from datetime import datetime as _datetime

		fatura = self._fatura()
		self._medicao(3000.0)
		antes = _datetime.now().astimezone()

		with mock.patch.dict(frappe.conf, {"brasil_ntp_corrigir_dhemi": True}):
			emitir_cte("Sales Invoice", fatura.name)

		registro = self._registro(fatura.name)
		self.assertEqual(registro.instante_corrigido, 1)
		self.assertEqual(registro.deslocamento_relogio_ms, 3000.0, "relido do banco por outro caminho")
		self.assertAlmostEqual((self._dhemi(registro.xml_enviado) - antes).total_seconds(), 3, delta=5)
		self.assertGreater(
			(self._dhemi(registro.xml_enviado) - antes).total_seconds(), 1.5, "a correção não entrou"
		)

	def test_correcao_ligada_sem_medicao_cai_no_relogio_do_servidor(self):
		fatura = self._fatura()

		with mock.patch.dict(frappe.conf, {"brasil_ntp_corrigir_dhemi": True}):
			emitir_cte("Sales Invoice", fatura.name)

		self.assertEqual(self._registro(fatura.name).instante_corrigido, 0)
