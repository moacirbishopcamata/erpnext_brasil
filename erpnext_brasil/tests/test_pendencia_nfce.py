# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""O DocType da fila de contingência concorda com o domínio, e o prazo é aritmética pura.

Teste-âncora: `test_as_opcoes_do_select_sao_o_dominio`. O `Select` de situação e o enum
`SituacaoDaPendencia` são duas escritas do mesmo conjunto, e divergir é fácil — basta
alguém redigitar um rótulo mais bonito de um lado.

⚠️ O que torna a divergência perigosa: `frappe.db.set_value` **não valida opções de
Select**. Um valor que o enum não conhece grava sem erro nenhum, e só falha depois, longe
dali. Este teste compara os dois lendo o JSON como dado — não o texto do arquivo, que
casaria com o rótulo dentro de uma descrição.

Módulo puro: roda sem bench.
"""

import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from erpnext_brasil.fiscal.contingencia_nfce import (
	PRAZO_TRANSMISSAO,
	SituacaoDaPendencia,
	exige_tratamento_humano,
	transmitir_ate,
	venceu_o_prazo,
)

JSON_DO_DOCTYPE = (
	Path(__file__).resolve().parent.parent
	/ "registros_fiscais"
	/ "doctype"
	/ "pendencia_nfce"
	/ "pendencia_nfce.json"
)


def _campo(fieldname: str) -> dict:
	definicao = json.loads(JSON_DO_DOCTYPE.read_text(encoding="utf-8"))

	for campo in definicao["fields"]:
		if campo["fieldname"] == fieldname:
			return campo

	raise AssertionError(f"campo {fieldname!r} não existe em pendencia_nfce.json")


class TestOSelectConcordaComODominio(unittest.TestCase):
	def test_as_opcoes_do_select_sao_o_dominio(self):
		"""Teste-âncora. Uma opção a mais ou a menos de qualquer lado é divergência."""
		opcoes = _campo("situacao")["options"].split("\n")

		self.assertEqual([s.value for s in SituacaoDaPendencia], opcoes)

	def test_o_padrao_do_select_e_uma_situacao_valida(self):
		"""Um `default` fora das opções nasce inválido em todo registro novo."""
		self.assertEqual(SituacaoDaPendencia.PENDENTE.value, _campo("situacao")["default"])

	def test_denegada_e_rejeitada_sao_situacoes_distintas(self):
		"""Fundi-las apagaria o fato de que a denegada **fica registrada** no fisco, o que
		muda o que a pessoa precisa fazer depois."""
		self.assertNotEqual(SituacaoDaPendencia.DENEGADA, SituacaoDaPendencia.REJEITADA)


class TestTratamentoHumano(unittest.TestCase):
	def test_rejeitada_e_denegada_exigem_pessoa(self):
		"""Nenhuma das duas se resolve tentando de novo: há cupom entregue e nenhum
		documento válido."""
		for situacao in (SituacaoDaPendencia.REJEITADA, SituacaoDaPendencia.DENEGADA):
			with self.subTest(situacao=situacao):
				self.assertTrue(exige_tratamento_humano(situacao))

	def test_pendente_e_autorizada_nao_exigem(self):
		"""Pendente ainda é trabalho da fila; autorizada acabou."""
		for situacao in (SituacaoDaPendencia.PENDENTE, SituacaoDaPendencia.AUTORIZADA):
			with self.subTest(situacao=situacao):
				self.assertFalse(exige_tratamento_humano(situacao))

	def test_toda_situacao_tem_resposta(self):
		"""Situação nova não fica sem decisão — o padrão silencioso seria 'não precisa de
		ninguém', que é o lado errado para errar."""
		for situacao in SituacaoDaPendencia:
			with self.subTest(situacao=situacao):
				self.assertIn(exige_tratamento_humano(situacao), (True, False))


class TestPrazoDeTransmissao(unittest.TestCase):
	EMISSAO = datetime(2026, 9, 9, 14, 0, 0)

	def test_o_prazo_conta_da_emissao(self):
		self.assertEqual(self.EMISSAO + PRAZO_TRANSMISSAO, transmitir_ate(self.EMISSAO))

	def test_dentro_do_prazo_nao_venceu(self):
		self.assertFalse(venceu_o_prazo(self.EMISSAO, self.EMISSAO + timedelta(hours=23)))

	def test_no_limite_ja_venceu(self):
		"""Exatamente no limite as 24 horas se completaram, e o prazo acabou.

		⚠️ Esta asserção nasceu invertida, por analogia com `Bloqueio.ativo_em`, que usa
		`<`. As duas fronteiras são **complementares**, não iguais: lá o estado termina no
		limite, aqui começa. Fica registrado porque a próxima pessoa vai sentir a mesma
		atração pela simetria.
		"""
		self.assertTrue(venceu_o_prazo(self.EMISSAO, transmitir_ate(self.EMISSAO)))

	def test_um_segundo_antes_do_limite_nao_venceu(self):
		quase = transmitir_ate(self.EMISSAO) - timedelta(seconds=1)

		self.assertFalse(venceu_o_prazo(self.EMISSAO, quase))

	def test_depois_do_limite_venceu(self):
		passou = transmitir_ate(self.EMISSAO) + timedelta(seconds=1)

		self.assertTrue(venceu_o_prazo(self.EMISSAO, passou))

	def test_o_prazo_e_de_vinte_e_quatro_horas(self):
		"""Fixado como afirmação, não derivado da constante: derivar faria o teste
		concordar com o código por construção, e um prazo trocado passaria."""
		self.assertEqual(timedelta(hours=24), PRAZO_TRANSMISSAO)


if __name__ == "__main__":
	unittest.main()
