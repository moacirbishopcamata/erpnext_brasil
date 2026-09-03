# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/documento/transmissao_registro.py` e do schema do DocType.

Duas coisas são verificadas aqui, e a segunda é a que costuma escapar: a regra pura, e a
**coerência entre a regra e o JSON do DocType**. Se o `Select` da tela oferecer uma
situação que a regra recusa (ou vice-versa), o usuário escolhe na interface e leva um
erro que parece um bug do sistema.
"""

import json
import unittest
from pathlib import Path

from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.fiscal.documento.transmissao_registro import (
	AMBIENTES,
	SITUACOES,
	TIPOS,
	RegistroInvalido,
	validar_registro,
)

CHAVE = montar_chave("35", "2601", "11222333000181", "55", "1", "1", "1", "12345678")

SCHEMA = (
	Path(__file__).resolve().parent.parent
	/ "registros_fiscais"
	/ "doctype"
	/ "transmissao_fiscal"
	/ "transmissao_fiscal.json"
)


def _registro(**overrides) -> dict:
	base = {
		"tipo": "Autorização",
		"situacao": "Autorizado",
		"ambiente": "Produção",
		"chave_acesso": CHAVE,
		"protocolo": "135260000123456",
	}
	base.update(overrides)

	return base


def _opcoes_do_campo(fieldname: str) -> list[str]:
	dados = json.loads(SCHEMA.read_text(encoding="utf-8"))
	campo = next(c for c in dados["fields"] if c["fieldname"] == fieldname)

	return [o for o in campo["options"].split("\n") if o]


class TestRegistroValido(unittest.TestCase):
	def test_autorizacao_completa(self):
		validar_registro(_registro())

	def test_pendente_nao_exige_protocolo(self):
		"""Pendente é estado legítimo: o lote foi aceito e ainda não foi julgado."""
		validar_registro(_registro(situacao="Pendente", protocolo=""))

	def test_consulta_sem_protocolo(self):
		validar_registro(_registro(tipo="Consulta", situacao="Pendente", protocolo=""))


class TestInvariantes(unittest.TestCase):
	def test_autorizado_sem_protocolo_e_erro(self):
		"""O protocolo é a prova da autorização."""
		with self.assertRaises(RegistroInvalido):
			validar_registro(_registro(protocolo=""))

	def test_rejeitado_sem_mensagem_e_erro(self):
		with self.assertRaises(RegistroInvalido):
			validar_registro(_registro(situacao="Rejeitado", protocolo="", mensagem=""))

	def test_rejeitado_com_mensagem_e_valido(self):
		validar_registro(_registro(situacao="Rejeitado", protocolo="", mensagem="Rejeição: 539 duplicidade"))

	def test_denegado_sem_mensagem_e_erro(self):
		with self.assertRaises(RegistroInvalido):
			validar_registro(_registro(situacao="Denegado", protocolo="", mensagem=""))

	def test_inutilizacao_com_chave_e_erro(self):
		"""Inutilizar é declarar que a faixa não foi usada — não há documento."""
		with self.assertRaises(RegistroInvalido):
			validar_registro(_registro(tipo="Inutilização", chave_acesso=CHAVE))

	def test_inutilizacao_sem_chave_e_valida(self):
		validar_registro(_registro(tipo="Inutilização", chave_acesso=""))

	def test_chave_invalida_e_erro(self):
		"""Reaproveita a validação da família NF-e: dígito verificador de verdade."""
		with self.assertRaises(RegistroInvalido):
			validar_registro(_registro(chave_acesso="1" * 44))

	def test_tipo_desconhecido_e_erro(self):
		with self.assertRaises(RegistroInvalido):
			validar_registro(_registro(tipo="Sei lá"))

	def test_situacao_desconhecida_e_erro(self):
		with self.assertRaises(RegistroInvalido):
			validar_registro(_registro(situacao="Talvez"))

	def test_ambiente_desconhecido_e_erro(self):
		with self.assertRaises(RegistroInvalido):
			validar_registro(_registro(ambiente="Testes"))


class TestSchemaBateComARegra(unittest.TestCase):
	"""A costura entre a tela e a regra — onde o usuário escolheria uma opção que o
	código recusa, e pareceria bug do sistema."""

	def test_situacoes_do_select_sao_as_da_regra(self):
		self.assertEqual(_opcoes_do_campo("situacao"), list(SITUACOES))

	def test_tipos_do_select_sao_os_da_regra(self):
		self.assertEqual(_opcoes_do_campo("tipo"), list(TIPOS))

	def test_ambientes_do_select_sao_os_da_regra(self):
		self.assertEqual(sorted(_opcoes_do_campo("ambiente")), sorted(AMBIENTES))

	def test_o_doctype_pertence_ao_modulo_de_persistencia(self):
		"""Não pode migrar para `Fiscal`, que é a camada pura sem Frappe."""
		dados = json.loads(SCHEMA.read_text(encoding="utf-8"))

		self.assertEqual(dados["module"], "Registros Fiscais")

	def test_o_modulo_esta_declarado(self):
		modulos = (
			(Path(__file__).resolve().parent.parent / "modules.txt").read_text(encoding="utf-8").split("\n")
		)

		self.assertIn("Registros Fiscais", modulos)


if __name__ == "__main__":
	unittest.main()
