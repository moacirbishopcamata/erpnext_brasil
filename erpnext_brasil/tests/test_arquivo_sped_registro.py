# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/arquivo_sped_registro.py` e do schema do DocType `Arquivo SPED`.

O teste que mais importa é `test_substituto_sem_recibo_anterior_e_erro`: declarar-se
retificador sem dizer o que se retifica é entrega que o Fisco não consegue ligar ao
original.
"""

import json
import unittest
from datetime import date
from pathlib import Path

from erpnext_brasil.contabil.arquivo_sped_registro import (
	FINALIDADE_ORIGINAL,
	FINALIDADE_SUBSTITUTO,
	FINALIDADES,
	TIPOS,
	ArquivoInvalido,
	validar_arquivo,
)

SCHEMA = (
	Path(__file__).resolve().parent.parent
	/ "registros_fiscais"
	/ "doctype"
	/ "arquivo_sped"
	/ "arquivo_sped.json"
)


def _arquivo(**overrides) -> dict:
	base = {
		"tipo": "EFD-ICMS/IPI",
		"finalidade": FINALIDADE_ORIGINAL,
		"data_inicial": date(2026, 1, 1),
		"data_final": date(2026, 1, 31),
	}
	base.update(overrides)

	return base


def _campo(fieldname: str) -> dict:
	dados = json.loads(SCHEMA.read_text(encoding="utf-8"))

	return next(c for c in dados["fields"] if c["fieldname"] == fieldname)


class TestArquivoValido(unittest.TestCase):
	def test_efd_original(self):
		validar_arquivo(_arquivo())

	def test_substituto_com_recibo_anterior(self):
		validar_arquivo(_arquivo(finalidade=FINALIDADE_SUBSTITUTO, recibo_anterior="12345678901234567890"))

	def test_periodo_de_um_dia_e_valido(self):
		"""Início e fim iguais: escrituração de um dia é caso raro, não erro."""
		validar_arquivo(_arquivo(data_inicial=date(2026, 1, 15), data_final=date(2026, 1, 15)))

	def test_todos_os_tipos_declarados_sao_aceitos(self):
		for tipo in TIPOS:
			with self.subTest(tipo=tipo):
				validar_arquivo(_arquivo(tipo=tipo))


class TestRetificacao(unittest.TestCase):
	def test_substituto_sem_recibo_anterior_e_erro(self):
		"""Sem o recibo, o Fisco não liga a retificação ao arquivo substituído."""
		with self.assertRaises(ArquivoInvalido):
			validar_arquivo(_arquivo(finalidade=FINALIDADE_SUBSTITUTO))

	def test_original_com_recibo_anterior_e_erro(self):
		"""O inverso também é contraditório: afirma substituir e declara-se original."""
		with self.assertRaises(ArquivoInvalido):
			validar_arquivo(_arquivo(recibo_anterior="12345678901234567890"))


class TestPeriodo(unittest.TestCase):
	def test_periodo_invertido_e_erro(self):
		with self.assertRaises(ArquivoInvalido):
			validar_arquivo(_arquivo(data_inicial=date(2026, 1, 31), data_final=date(2026, 1, 1)))

	def test_sem_data_inicial_e_erro(self):
		with self.assertRaises(ArquivoInvalido):
			validar_arquivo(_arquivo(data_inicial=None))

	def test_sem_data_final_e_erro(self):
		with self.assertRaises(ArquivoInvalido):
			validar_arquivo(_arquivo(data_final=None))


class TestDominios(unittest.TestCase):
	def test_tipo_desconhecido_e_erro(self):
		with self.assertRaises(ArquivoInvalido):
			validar_arquivo(_arquivo(tipo="EFD-Reinf"))

	def test_finalidade_desconhecida_e_erro(self):
		with self.assertRaises(ArquivoInvalido):
			validar_arquivo(_arquivo(finalidade="Retificadora"))


class TestSchemaBateComARegra(unittest.TestCase):
	def test_tipos_do_select_sao_os_da_regra(self):
		opcoes = [o for o in _campo("tipo")["options"].split("\n") if o]

		self.assertEqual(opcoes, list(TIPOS))

	def test_finalidades_do_select_sao_as_da_regra(self):
		opcoes = [o for o in _campo("finalidade")["options"].split("\n") if o]

		self.assertEqual(opcoes, list(FINALIDADES))

	def test_a_tela_ja_exige_o_recibo_no_substituto(self):
		"""A regra recusa depois; a tela avisa antes — as duas dizem o mesmo."""
		campo = _campo("recibo_anterior")

		self.assertIn("Substituto", campo["mandatory_depends_on"])

	def test_o_hash_nao_e_editavel(self):
		"""Hash digitado à mão não prova nada sobre o conteúdo."""
		self.assertEqual(_campo("hash_conteudo")["read_only"], 1)

	def test_o_hash_cabe_num_sha256(self):
		self.assertEqual(_campo("hash_conteudo")["length"], 64)

	def test_no_modulo_de_persistencia(self):
		dados = json.loads(SCHEMA.read_text(encoding="utf-8"))

		self.assertEqual(dados["module"], "Registros Fiscais")


if __name__ == "__main__":
	unittest.main()
