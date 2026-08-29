# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da interpretação da resposta de autorização.

O teste-âncora (`TestArmadilhaDosDoisCstat`) é o motivo de este módulo existir: a
resposta tem `cStat` do lote e `cStat` da nota em níveis diferentes, e um lote
processado (104) com nota rejeitada não pode ser lido como sucesso.

Pulados quando `lxml` não está instalado — mas nesta sessão já está.
"""

import unittest

try:
	import lxml  # noqa: F401

	TEM_LXML = True
except ImportError:
	TEM_LXML = False

from erpnext_brasil.fiscal.documento.resposta_sefaz import (
	RespostaSefazInvalida,
	interpretar_autorizacao,
)


def _resposta(cstat_lote="104", motivo_lote="Lote processado", inf_prot=""):
	return (
		'<retEnviNFe xmlns="http://www.portalfiscal.inf.br/nfe">'
		"<tpAmb>2</tpAmb><verAplic>SVRS202601</verAplic>"
		f"<cStat>{cstat_lote}</cStat><xMotivo>{motivo_lote}</xMotivo>"
		"<cUF>11</cUF><dhRecbto>2026-08-24T10:00:00-04:00</dhRecbto>"
		f"{inf_prot}"
		"</retEnviNFe>"
	)


def _prot_nfe(cstat="100", motivo="Autorizado o uso da NF-e"):
	return (
		"<protNFe><infProt>"
		"<tpAmb>2</tpAmb><verAplic>SVRS202601</verAplic>"
		f"<chNFe>{'3' * 44}</chNFe>"
		"<dhRecbto>2026-08-24T10:00:01-04:00</dhRecbto>"
		f"<nProt>135260000123456</nProt><digVal>ZGln</digVal>"
		f"<cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo>"
		"</infProt></protNFe>"
	)


@unittest.skipUnless(TEM_LXML, "requer lxml, disponível no bench")
class TestArmadilhaDosDoisCstat(unittest.TestCase):
	"""Lote processado não é sinônimo de nota autorizada."""

	def test_lote_processado_e_nota_autorizada(self):
		resultado = interpretar_autorizacao(_resposta(inf_prot=_prot_nfe()))

		self.assertEqual(resultado.cstat_lote, "104")
		self.assertTrue(resultado.lote_processado)
		self.assertEqual(resultado.cstat_nfe, "100")
		self.assertTrue(resultado.autorizado)

	def test_lote_processado_e_nota_rejeitada(self):
		"""O caso que um leitor ingênuo do cStat do lote reportaria como sucesso."""
		resultado = interpretar_autorizacao(
			_resposta(inf_prot=_prot_nfe(cstat="225", motivo="Falha no schema XML"))
		)

		self.assertTrue(resultado.lote_processado)
		self.assertFalse(resultado.autorizado)
		self.assertEqual(resultado.motivo_nfe, "Falha no schema XML")

	def test_lote_processado_e_nota_denegada(self):
		resultado = interpretar_autorizacao(
			_resposta(inf_prot=_prot_nfe(cstat="110", motivo="Uso Denegado"))
		)

		self.assertTrue(resultado.denegado)
		self.assertFalse(resultado.autorizado)

	def test_cstat_do_lote_nao_e_confundido_com_o_da_nota(self):
		"""Os dois números aparecem no mesmo documento; a leitura não pode pegar o errado."""
		resultado = interpretar_autorizacao(
			_resposta(cstat_lote="104", inf_prot=_prot_nfe(cstat="100"))
		)

		self.assertNotEqual(resultado.cstat_lote, resultado.cstat_nfe)
		self.assertEqual(resultado.cstat_lote, "104")
		self.assertEqual(resultado.cstat_nfe, "100")


@unittest.skipUnless(TEM_LXML, "requer lxml, disponível no bench")
class TestLoteAindaNaoJulgado(unittest.TestCase):
	"""Sem protNFe é estado válido do fluxo — precisa de nova consulta, não é erro."""

	def test_lote_em_processamento_nao_tem_protocolo(self):
		resposta = (
			'<retEnviNFe xmlns="http://www.portalfiscal.inf.br/nfe">'
			"<cStat>103</cStat><xMotivo>Lote recebido com sucesso</xMotivo>"
			"<nRec>351000000000001</nRec>"
			"</retEnviNFe>"
		)

		resultado = interpretar_autorizacao(resposta)

		self.assertIsNone(resultado.protocolo)
		self.assertIsNone(resultado.cstat_nfe)
		self.assertTrue(resultado.pendente)
		self.assertEqual(resultado.numero_recibo, "351000000000001")

	def test_pendente_e_falso_quando_ha_protocolo(self):
		resultado = interpretar_autorizacao(_resposta(inf_prot=_prot_nfe()))

		self.assertFalse(resultado.pendente)


class TestDadosDoProtocolo(unittest.TestCase):
	@unittest.skipUnless(TEM_LXML, "requer lxml")
	def test_todos_os_campos_extraidos(self):
		resultado = interpretar_autorizacao(_resposta(inf_prot=_prot_nfe()))

		self.assertEqual(resultado.protocolo, "135260000123456")
		self.assertEqual(resultado.chave_conferida, "3" * 44)
		self.assertEqual(resultado.data_recebimento, "2026-08-24T10:00:01-04:00")


@unittest.skipUnless(TEM_LXML, "requer lxml, disponível no bench")
class TestValidacao(unittest.TestCase):
	def test_xml_invalido(self):
		with self.assertRaises(RespostaSefazInvalida):
			interpretar_autorizacao("isto nao e xml")

	def test_documento_sem_cstat_de_lote(self):
		with self.assertRaises(RespostaSefazInvalida):
			interpretar_autorizacao('<outraCoisa xmlns="urn:x"><a>1</a></outraCoisa>')

	def test_aceita_bytes(self):
		resultado = interpretar_autorizacao(_resposta(inf_prot=_prot_nfe()).encode("utf-8"))

		self.assertTrue(resultado.autorizado)


if __name__ == "__main__":
	unittest.main()
