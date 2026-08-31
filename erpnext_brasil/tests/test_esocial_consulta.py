# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `folha/esocial_consulta.py` — formato do `protocoloEnvio` e a árvore de
`consultaLoteEventos`."""

import unittest

from erpnext_brasil.folha.esocial_consulta import (
	AGENTE_CAIXA,
	AGENTE_SERPRO,
	ConsultaLoteInvalida,
	montar_consulta_lote_eventos,
	protocolo_e_valido,
)


class TestProtocoloEValido(unittest.TestCase):
	def test_exemplo_do_serpro(self):
		self.assertTrue(protocolo_e_valido(f"{AGENTE_SERPRO}.1.0000000000000000001"))

	def test_exemplo_da_caixa(self):
		self.assertTrue(protocolo_e_valido(f"{AGENTE_CAIXA}.1.0000000000000000001"))

	def test_sequencial_com_18_digitos_e_invalido(self):
		self.assertFalse(protocolo_e_valido("1.1.000000000000000001"))

	def test_sequencial_com_20_digitos_e_invalido(self):
		self.assertFalse(protocolo_e_valido("1.1.00000000000000000012"))

	def test_sem_pontos_e_invalido(self):
		self.assertFalse(protocolo_e_valido("110000000000000000001"))

	def test_vazio_e_invalido(self):
		self.assertFalse(protocolo_e_valido(""))

	def test_none_e_invalido(self):
		self.assertFalse(protocolo_e_valido(None))


class TestMontarConsultaLoteEventos(unittest.TestCase):
	def test_arvore_valida(self):
		arvore = montar_consulta_lote_eventos("1.1.0000000000000000001")

		self.assertEqual(
			arvore, {"eSocial": {"consultaLoteEventos": {"protocoloEnvio": "1.1.0000000000000000001"}}}
		)

	def test_protocolo_invalido_e_erro(self):
		with self.assertRaises(ConsultaLoteInvalida):
			montar_consulta_lote_eventos("protocolo-qualquer")

	def test_serializa_via_para_xml(self):
		from erpnext_brasil.fiscal.documento.serializacao import para_xml

		xml = para_xml(montar_consulta_lote_eventos("1.1.0000000000000000001"))

		self.assertIn("<protocoloEnvio>1.1.0000000000000000001</protocoloEnvio>", xml)


if __name__ == "__main__":
	unittest.main()
