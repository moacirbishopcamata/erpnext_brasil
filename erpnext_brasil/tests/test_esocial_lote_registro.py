# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_lote_registro.py` e do schema do DocType `Lote eSocial`.

O teste que mais importa é `test_em_processamento_sem_protocolo_e_erro`: sem protocolo,
um lote pendente fica **inconsultável para sempre** — que é exatamente o problema que
este registro existe para resolver.
"""

import json
import unittest
from pathlib import Path

from erpnext_brasil.folha.esocial_lote_registro import (
	AMBIENTES,
	SITUACAO_EM_PROCESSAMENTO,
	SITUACAO_PROCESSADO,
	SITUACAO_REJEITADO,
	SITUACOES,
	LoteInvalido,
	situacao_para_codigo,
	validar_lote,
)

PROTOCOLO = "1.1.0000000000000000001"

RAIZ = Path(__file__).resolve().parent.parent / "registros_fiscais" / "doctype"
SCHEMA_LOTE = RAIZ / "lote_esocial" / "lote_esocial.json"
SCHEMA_EVENTO = RAIZ / "evento_do_lote_esocial" / "evento_do_lote_esocial.json"


def _lote(**overrides) -> dict:
	base = {
		"situacao": SITUACAO_PROCESSADO,
		"ambiente": "Produção restrita",
		"protocolo_envio": PROTOCOLO,
	}
	base.update(overrides)

	return base


def _campo(schema: Path, fieldname: str) -> dict:
	dados = json.loads(schema.read_text(encoding="utf-8"))

	return next(c for c in dados["fields"] if c["fieldname"] == fieldname)


class TestSituacaoPorCodigo(unittest.TestCase):
	"""Traduz o `cdResposta` do eSocial na situação do registro."""

	def test_201_e_processado(self):
		self.assertEqual(situacao_para_codigo(201), SITUACAO_PROCESSADO)

	def test_202_com_advertencias_tambem_e_processado(self):
		self.assertEqual(situacao_para_codigo(202), SITUACAO_PROCESSADO)

	def test_203_e_em_processamento(self):
		"""O código que motiva o registro existir: ainda não há decisão."""
		self.assertEqual(situacao_para_codigo(203), SITUACAO_EM_PROCESSAMENTO)

	def test_401_e_rejeitado(self):
		self.assertEqual(situacao_para_codigo(401), SITUACAO_REJEITADO)

	def test_codigo_desconhecido_e_rejeitado_nao_sucesso(self):
		"""Nunca assumir código não tabelado como sucesso — mesma disciplina de
		`esocial_retorno.StatusRetorno`."""
		self.assertEqual(situacao_para_codigo(999), SITUACAO_REJEITADO)


class TestValidacao(unittest.TestCase):
	def test_lote_valido(self):
		validar_lote(_lote())

	def test_enviado_sem_protocolo_e_valido(self):
		"""Entre transmitir e ler a resposta, ainda não há protocolo."""
		validar_lote(_lote(situacao="Enviado", protocolo_envio=""))

	def test_em_processamento_sem_protocolo_e_erro(self):
		"""Sem protocolo o lote fica inconsultável — o pior estado possível."""
		with self.assertRaises(LoteInvalido):
			validar_lote(_lote(situacao=SITUACAO_EM_PROCESSAMENTO, protocolo_envio=""))

	def test_em_processamento_com_protocolo_e_valido(self):
		validar_lote(_lote(situacao=SITUACAO_EM_PROCESSAMENTO))

	def test_protocolo_fora_do_formato_e_erro(self):
		"""Reaproveita `protocolo_e_valido` do módulo de consulta."""
		with self.assertRaises(LoteInvalido):
			validar_lote(_lote(protocolo_envio="123"))

	def test_situacao_desconhecida_e_erro(self):
		with self.assertRaises(LoteInvalido):
			validar_lote(_lote(situacao="Talvez"))

	def test_ambiente_da_sefaz_e_recusado(self):
		""" "Homologação" é da SEFAZ; o eSocial usa "Produção restrita"."""
		with self.assertRaises(LoteInvalido):
			validar_lote(_lote(ambiente="Homologação"))


class TestSchemaBateComARegra(unittest.TestCase):
	def test_situacoes_do_select_sao_as_da_regra(self):
		opcoes = [o for o in _campo(SCHEMA_LOTE, "situacao")["options"].split("\n") if o]

		self.assertEqual(opcoes, list(SITUACOES))

	def test_ambientes_do_select_sao_os_do_esocial(self):
		opcoes = [o for o in _campo(SCHEMA_LOTE, "ambiente")["options"].split("\n") if o]

		self.assertEqual(sorted(opcoes), sorted(AMBIENTES))
		self.assertNotIn("Homologação", opcoes)

	def test_a_tabela_filha_e_declarada_como_tabela(self):
		dados = json.loads(SCHEMA_EVENTO.read_text(encoding="utf-8"))

		self.assertEqual(dados["istable"], 1)

	def test_o_lote_aponta_para_a_tabela_filha_certa(self):
		self.assertEqual(_campo(SCHEMA_LOTE, "eventos")["options"], "Evento do Lote eSocial")

	def test_id_do_evento_cabe_nos_36_caracteres_do_esocial(self):
		"""O `Id` do eSocial tem exatamente 36 caracteres (ver esocial_id.py)."""
		self.assertEqual(_campo(SCHEMA_EVENTO, "id_evento")["length"], 36)

	def test_ambos_no_modulo_de_persistencia(self):
		for schema in (SCHEMA_LOTE, SCHEMA_EVENTO):
			with self.subTest(schema=schema.name):
				dados = json.loads(schema.read_text(encoding="utf-8"))

				self.assertEqual(dados["module"], "Registros Fiscais")


if __name__ == "__main__":
	unittest.main()
