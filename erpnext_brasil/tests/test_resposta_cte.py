# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Leitura da resposta da autorização síncrona do CT-e (`fiscal/documento/resposta_cte.py`).

A estrutura (`retCTe`: `tpAmb`, `cUF`, `verAplic`, `cStat`, `xMotivo` e `protCTe` **opcional**,
com `infProt`) foi lida do `cteTiposBasico_v4.00.xsd`, tipos `TRetCTe` e `TProtCTe`. Os `cStat`
de autorizado e denegado vêm do `sped-cte` (`Complements`), fonte secundária — o MOC não foi lido.

Diferente da NF-e, não há lote nem recibo: **um** `cStat` decide. Quando existe `protCTe`, o
`cStat` de `infProt` é o do documento; quando não existe (rejeição antes do processamento), vale
o do `retCTe`.
"""

import unittest

from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.fiscal.documento.resposta_cte import (
	AUTORIZADOS,
	DENEGADOS,
	RetornoCteInvalido,
	interpretar_retorno_cte,
)

NS = "http://www.portalfiscal.inf.br/cte"
CHAVE = montar_chave("11", "2610", "11222333000181", "57", "1", "42", "1", "12345678")


def _prot(cstat="100", motivo="Autorizado o uso do CT-e", chave=CHAVE, protocolo="311260000012345"):
	nprot = f"<nProt>{protocolo}</nProt>" if protocolo else ""

	return (
		"<protCTe><infProt>"
		f"<tpAmb>2</tpAmb><verAplic>RS20260101</verAplic><chCTe>{chave}</chCTe>"
		f"<dhRecbto>2026-10-03T09:30:05-04:00</dhRecbto>{nprot}"
		f"<cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo>"
		"</infProt></protCTe>"
	)


def _ret(cstat="100", motivo="Autorizado o uso do CT-e", prot=None, embrulho=None):
	corpo = (
		f'<retCTe xmlns="{NS}" versao="4.00"><tpAmb>2</tpAmb><cUF>11</cUF>'
		f"<verAplic>RS20260101</verAplic><cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo>"
		f"{prot if prot is not None else ''}</retCTe>"
	)

	return f"<{embrulho}>{corpo}</{embrulho}>" if embrulho else corpo


class TestAutorizacao(unittest.TestCase):
	def test_cstat_100_com_protocolo_e_autorizado(self):
		r = interpretar_retorno_cte(_ret(prot=_prot()))

		self.assertTrue(r.autorizado)
		self.assertFalse(r.denegado)
		self.assertEqual((r.protocolo, r.chave), ("311260000012345", CHAVE))
		self.assertEqual(r.codigo, "100")

	def test_cstat_150_autorizado_fora_do_prazo_tambem_autoriza(self):
		r = interpretar_retorno_cte(
			_ret("150", "Autorizado fora de prazo", _prot("150", "Autorizado fora de prazo"))
		)

		self.assertTrue(r.autorizado)

	def test_o_recebimento_vem_com_fuso(self):
		r = interpretar_retorno_cte(_ret(prot=_prot()))

		self.assertEqual(r.recebido_em.utcoffset().total_seconds(), -4 * 3600)

	def test_autorizado_exige_protocolo(self):
		"""`cStat` 100 sem `nProt` não é prova de autorização — recusar em vez de gravar sem protocolo."""
		with self.assertRaises(RetornoCteInvalido):
			interpretar_retorno_cte(_ret(prot=_prot(protocolo="")))


class TestDenegacao(unittest.TestCase):
	def test_os_cstat_de_denegacao(self):
		for cstat in sorted(DENEGADOS):
			with self.subTest(cstat=cstat):
				r = interpretar_retorno_cte(_ret(cstat, "Uso Denegado", _prot(cstat, "Uso Denegado")))

				self.assertTrue(r.denegado)
				self.assertFalse(r.autorizado)

	def test_os_conjuntos_nao_se_cruzam(self):
		self.assertEqual(AUTORIZADOS & DENEGADOS, set())
		self.assertEqual(AUTORIZADOS, {"100", "150"})
		self.assertEqual(DENEGADOS, {"110", "205", "301"})


class TestRejeicao(unittest.TestCase):
	def test_rejeicao_sem_protcte_vale_o_cstat_do_retorno(self):
		r = interpretar_retorno_cte(_ret("539", "Rejeição: Duplicidade de CT-e"))

		self.assertFalse(r.autorizado)
		self.assertFalse(r.denegado)
		self.assertEqual((r.codigo, r.motivo), ("539", "Rejeição: Duplicidade de CT-e"))
		self.assertEqual(r.protocolo, "")

	def test_com_protcte_decide_o_cstat_do_documento_nao_o_do_retorno(self):
		r = interpretar_retorno_cte(
			_ret("100", "ok", _prot("539", "Rejeição: Duplicidade de CT-e", protocolo=""))
		)

		self.assertFalse(r.autorizado)
		self.assertEqual(r.codigo, "539")

	def test_o_consumo_indevido_aparece_como_codigo(self):
		"""`656` chega como `cStat` do retorno e é o que o registrador do transporte lê."""
		self.assertEqual(interpretar_retorno_cte(_ret("656", "Consumo Indevido")).codigo, "656")


class TestEstruturaDaResposta(unittest.TestCase):
	def test_acha_o_retcte_dentro_de_qualquer_embrulho(self):
		"""O nome do elemento que embrulha o resultado muda por serviço; o `retCTe` não."""
		for embrulho in ("cteRecepcaoResult", "cteResultMsg", "outroNome"):
			with self.subTest(embrulho=embrulho):
				r = interpretar_retorno_cte(_ret(prot=_prot(), embrulho=embrulho))

				self.assertTrue(r.autorizado)

	def test_aceita_bytes(self):
		self.assertTrue(interpretar_retorno_cte(_ret(prot=_prot()).encode("utf-8")).autorizado)

	def test_sem_retcte_recusa(self):
		with self.assertRaises(RetornoCteInvalido):
			interpretar_retorno_cte("<outraCoisa/>")

	def test_xml_malformado_recusa(self):
		with self.assertRaises(RetornoCteInvalido):
			interpretar_retorno_cte("<retCTe")

	def test_retcte_sem_cstat_recusa(self):
		with self.assertRaises(RetornoCteInvalido):
			interpretar_retorno_cte(f'<retCTe xmlns="{NS}"><xMotivo>x</xMotivo></retCTe>')


if __name__ == "__main__":
	unittest.main()
