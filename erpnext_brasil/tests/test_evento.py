# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes do evento de cancelamento.

`TestPegadinhaDoId` é o teste-âncora: guarda a descoberta de que `nSeqEvento` aparece de
duas formas diferentes no mesmo evento — sem zero à esquerda no elemento, com zero à
esquerda (2 dígitos) dentro do `@Id`. É o tipo de detalhe que só aparece decompondo um
exemplo real do XSD, e que uma implementação apressada erraria em silêncio.

Não há teste de conformidade contra `elementos_nfe.json` aqui: aquele manifesto vem do
pacote de leiaute principal da NF-e, e o evento de cancelamento é um pacote de esquema
à parte — rodar a conformidade contra o manifesto errado acusaria falso positivo.
"""

import re
import unittest

from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.fiscal.documento.estado import JUSTIFICATIVA_MAXIMA, JUSTIFICATIVA_MINIMA
from erpnext_brasil.fiscal.documento.evento import (
	TIPO_EVENTO_CANCELAMENTO,
	EventoInvalido,
	montar_env_evento,
	montar_evento_cancelamento,
)

CHAVE = montar_chave("11", "2608", "11222333000181", "55", "1", "1", "1", "12345678")
JUSTIFICATIVA = "Erro de digitacao no valor do item"


def evento(**ajustes):
	valores = {
		"chave_acesso": CHAVE,
		"protocolo": "111260000123456",
		"justificativa": JUSTIFICATIVA,
		"cnpj_autor": "11.222.333/0001-81",
		"data_evento": "2026-08-24T10:00:00-04:00",
	}
	valores.update(ajustes)

	return montar_evento_cancelamento(**valores)


class TestOrdemDeInfEvento(unittest.TestCase):
	"""Ordem confirmada no XSD: cOrgao, tpAmb, CNPJ|CPF, chNFe, dhEvento, tpEvento,
	nSeqEvento, verEvento, detEvento."""

	def test_ordem_dos_campos(self):
		inf_evento = evento()["evento"]["infEvento"]

		esperado = [
			"@Id", "cOrgao", "tpAmb", "CNPJ", "chNFe", "dhEvento",
			"tpEvento", "nSeqEvento", "verEvento", "detEvento",
		]  # fmt: skip

		self.assertEqual(list(inf_evento), esperado)

	def test_ordem_de_detevento(self):
		det = evento()["evento"]["infEvento"]["detEvento"]

		self.assertEqual(list(det), ["@versao", "descEvento", "nProt", "xJust"])


class TestValoresFixos(unittest.TestCase):
	def test_tipo_evento_e_fixo(self):
		self.assertEqual(TIPO_EVENTO_CANCELAMENTO, "110111")
		self.assertEqual(evento()["evento"]["infEvento"]["tpEvento"], "110111")

	def test_ver_evento_fixo_em_1_00(self):
		inf_evento = evento()["evento"]["infEvento"]

		self.assertEqual(inf_evento["verEvento"], "1.00")
		self.assertEqual(evento()["evento"]["@versao"], "1.00")
		self.assertEqual(inf_evento["detEvento"]["@versao"], "1.00")

	def test_desc_evento_fixo(self):
		self.assertEqual(evento()["evento"]["infEvento"]["detEvento"]["descEvento"], "Cancelamento")


class TestPegadinhaDoId(unittest.TestCase):
	"""nSeqEvento aparece de duas formas: sem zero à esquerda no elemento, com dois
	dígitos dentro do @Id. Confundir as duas produz um Id que não bate com o padrão
	ID[0-9]{52} do XSD."""

	def test_id_bate_com_o_padrao_do_xsd(self):
		id_evento = evento()["evento"]["infEvento"]["@Id"]

		self.assertRegex(id_evento, r"^ID\d{52}$")

	def test_id_e_a_concatenacao_exata(self):
		id_evento = evento(numero_sequencia=1)["evento"]["infEvento"]["@Id"]

		self.assertEqual(id_evento, f"ID110111{CHAVE}01")

	def test_elemento_nseqevento_nao_tem_zero_a_esquerda(self):
		inf_evento = evento(numero_sequencia=1)["evento"]["infEvento"]

		self.assertEqual(inf_evento["nSeqEvento"], "1")

	def test_id_tem_zero_a_esquerda_para_o_mesmo_numero(self):
		inf_evento = evento(numero_sequencia=1)["evento"]["infEvento"]

		self.assertIn(f"{CHAVE}01", inf_evento["@Id"])
		self.assertNotIn(f"{CHAVE}1", inf_evento["@Id"].replace(f"{CHAVE}01", ""))

	def test_sequencia_dois_digitos_nao_ganha_zero_extra(self):
		inf_evento = evento(numero_sequencia=15)["evento"]["infEvento"]

		self.assertEqual(inf_evento["nSeqEvento"], "15")
		self.assertTrue(inf_evento["@Id"].endswith("15"))

	def test_id_muda_com_a_chave(self):
		outra_chave = montar_chave("35", "2608", "11222333000181", "55", "2", "1", "1", "12345678")
		id1 = evento()["evento"]["infEvento"]["@Id"]
		id2 = evento(chave_acesso=outra_chave)["evento"]["infEvento"]["@Id"]

		self.assertNotEqual(id1, id2)


class TestValidacao(unittest.TestCase):
	def test_justificativa_curta_e_erro(self):
		with self.assertRaises(EventoInvalido) as ctx:
			evento(justificativa="curta")

		self.assertEqual(ctx.exception.campo, "justificativa")

	def test_justificativa_longa_e_erro(self):
		with self.assertRaises(EventoInvalido):
			evento(justificativa="x" * (JUSTIFICATIVA_MAXIMA + 1))

	def test_limite_minimo_passa(self):
		grupo = evento(justificativa="x" * JUSTIFICATIVA_MINIMA)

		self.assertEqual(len(grupo["evento"]["infEvento"]["detEvento"]["xJust"]), JUSTIFICATIVA_MINIMA)

	def test_protocolo_vazio_e_erro(self):
		with self.assertRaises(EventoInvalido) as ctx:
			evento(protocolo="")

		self.assertEqual(ctx.exception.campo, "protocolo")

	def test_cnpj_invalido_e_erro(self):
		with self.assertRaises(EventoInvalido) as ctx:
			evento(cnpj_autor="11222333000182")

		self.assertEqual(ctx.exception.campo, "cnpj_autor")

	def test_sequencia_fora_da_faixa(self):
		for invalida in (0, 21, -1):
			with self.subTest(numero_sequencia=invalida):
				with self.assertRaises(EventoInvalido):
					evento(numero_sequencia=invalida)

	def test_sequencia_maxima_e_aceita(self):
		grupo = evento(numero_sequencia=20)

		self.assertEqual(grupo["evento"]["infEvento"]["nSeqEvento"], "20")


class TestEnvEvento(unittest.TestCase):
	def test_envelope_de_um_evento(self):
		grupo = montar_env_evento([evento()], id_lote="1")["envEvento"]

		self.assertEqual(grupo["idLote"], "1")
		self.assertEqual(len(grupo["evento"]), 1)

	def test_ate_vinte_eventos(self):
		eventos = [evento(numero_sequencia=n) for n in range(1, 21)]
		grupo = montar_env_evento(eventos, id_lote="1")["envEvento"]

		self.assertEqual(len(grupo["evento"]), 20)

	def test_mais_de_vinte_e_erro(self):
		eventos = [evento(numero_sequencia=1) for _ in range(21)]

		with self.assertRaises(EventoInvalido):
			montar_env_evento(eventos, id_lote="1")

	def test_lista_vazia_e_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_env_evento([], id_lote="1")

	def test_sem_id_lote_e_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_env_evento([evento()], id_lote="")

	def test_namespace_na_raiz(self):
		grupo = montar_env_evento([evento()], id_lote="1")["envEvento"]

		self.assertEqual(grupo["@xmlns"], "http://www.portalfiscal.inf.br/nfe")


if __name__ == "__main__":
	unittest.main()
