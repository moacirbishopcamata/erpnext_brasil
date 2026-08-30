# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da inutilização de faixa de numeração (`NfeInutilizacao4`).

Não há teste de conformidade contra `elementos_nfe.json` aqui pelo mesmo motivo de
`test_evento.py`: `inutNFe` não é do pacote de leiaute principal, é schema próprio.
"""

import unittest

from erpnext_brasil.fiscal.documento.inutilizacao import (
	CODIGO_SUCESSO_INUTILIZACAO,
	CODIGO_UF_POR_SIGLA,
	CODIGOS_UF_IBGE,
	JUSTIFICATIVA_MAXIMA,
	JUSTIFICATIVA_MINIMA,
	VERSAO_INUTILIZACAO,
	InutilizacaoInvalida,
	RetornoInutilizacao,
	assinar_inutilizacao,
	interpretar_retorno_inutilizacao,
	montar_inutilizacao,
)

CNPJ = "11222333000181"
JUSTIFICATIVA = "Faixa pulada por erro de configuracao do emissor fiscal"


def inutilizacao(**ajustes):
	valores = {
		"cuf": "11",
		"ano": "26",
		"cnpj": CNPJ,
		"modelo": "55",
		"serie": "1",
		"numero_inicial": "100",
		"numero_final": "105",
		"justificativa": JUSTIFICATIVA,
	}
	valores.update(ajustes)

	return montar_inutilizacao(**valores)


class TestOrdemDeInfInut(unittest.TestCase):
	"""Ordem confirmada no XSD: tpAmb, xServ, cUF, ano, CNPJ, mod, serie, nNFIni,
	nNFFin, xJust."""

	def test_ordem_dos_campos(self):
		inf_inut = inutilizacao()["inutNFe"]["infInut"]

		esperado = [
			"@Id", "tpAmb", "xServ", "cUF", "ano", "CNPJ", "mod", "serie",
			"nNFIni", "nNFFin", "xJust",
		]  # fmt: skip

		self.assertEqual(list(inf_inut), esperado)

	def test_raiz_e_inutnfe_com_versao_e_namespace(self):
		raiz = inutilizacao()["inutNFe"]

		self.assertEqual(raiz["@versao"], VERSAO_INUTILIZACAO)
		self.assertEqual(raiz["@xmlns"], "http://www.portalfiscal.inf.br/nfe")

	def test_xserv_e_sempre_inutilizar(self):
		self.assertEqual(inutilizacao()["inutNFe"]["infInut"]["xServ"], "INUTILIZAR")

	def test_campos_nao_levam_zero_a_esquerda_no_corpo(self):
		inf_inut = inutilizacao(serie="1", numero_inicial="7", numero_final="9")["inutNFe"]["infInut"]

		self.assertEqual(inf_inut["serie"], "1")
		self.assertEqual(inf_inut["nNFIni"], "7")
		self.assertEqual(inf_inut["nNFFin"], "9")


class TestPegadinhaDoId(unittest.TestCase):
	"""`@Id` leva zero à esquerda em serie/nNFIni/nNFFin até largura fixa — o elemento no
	corpo do documento não leva. Confirmado decompondo um `Id` real de exemplo."""

	def test_id_bate_com_o_padrao_do_xsd(self):
		id_inut = inutilizacao()["inutNFe"]["infInut"]["@Id"]

		self.assertRegex(id_inut, r"^ID\d{41}$")

	def test_id_e_a_concatenacao_com_zero_a_esquerda(self):
		id_inut = inutilizacao(
			cuf="11", ano="26", cnpj=CNPJ, modelo="55", serie="1",
			numero_inicial="100", numero_final="105",
		)["inutNFe"]["infInut"]["@Id"]  # fmt: skip

		self.assertEqual(id_inut, f"ID1126{CNPJ}55001000000100000000105")

	def test_elemento_nao_leva_zero_mas_id_leva(self):
		inf_inut = inutilizacao(serie="1", numero_inicial="100", numero_final="105")["inutNFe"]["infInut"]

		self.assertEqual(inf_inut["serie"], "1")
		self.assertIn("001", inf_inut["@Id"])

	def test_id_muda_com_a_faixa(self):
		id1 = inutilizacao(numero_inicial="100", numero_final="105")["inutNFe"]["infInut"]["@Id"]
		id2 = inutilizacao(numero_inicial="200", numero_final="205")["inutNFe"]["infInut"]["@Id"]

		self.assertNotEqual(id1, id2)


class TestValidacao(unittest.TestCase):
	def test_uf_invalida_e_erro(self):
		with self.assertRaises(InutilizacaoInvalida) as ctx:
			inutilizacao(cuf="99")

		self.assertEqual(ctx.exception.campo, "cuf")

	def test_ano_com_um_digito_e_erro(self):
		with self.assertRaises(InutilizacaoInvalida) as ctx:
			inutilizacao(ano="6")

		self.assertEqual(ctx.exception.campo, "ano")

	def test_cnpj_invalido_e_erro(self):
		with self.assertRaises(InutilizacaoInvalida) as ctx:
			inutilizacao(cnpj="11222333000182")

		self.assertEqual(ctx.exception.campo, "cnpj")

	def test_cnpj_alfanumerico_e_aceito(self):
		"""Confirmado em 2026-08-29 (`leiauteInutNFe_v4.00.xsd` do pacote PL_010_V1.30,
		NT 2026.004) — mesmo CNPJ de exemplo já usado em `test_nfe.py`."""
		doc = inutilizacao(cnpj="12ABC34501DE35")["inutNFe"]["infInut"]

		self.assertEqual(doc["CNPJ"], "12ABC34501DE35")
		self.assertIn("12ABC34501DE35", doc["@Id"])

	def test_modelo_invalido_e_erro(self):
		with self.assertRaises(InutilizacaoInvalida) as ctx:
			inutilizacao(modelo="01")

		self.assertEqual(ctx.exception.campo, "modelo")

	def test_numero_inicial_maior_que_final_e_erro(self):
		with self.assertRaises(InutilizacaoInvalida) as ctx:
			inutilizacao(numero_inicial="200", numero_final="100")

		self.assertEqual(ctx.exception.campo, "numero_final")

	def test_numero_com_zero_a_esquerda_e_erro(self):
		with self.assertRaises(InutilizacaoInvalida):
			inutilizacao(numero_inicial="007", numero_final="009")

	def test_justificativa_curta_e_erro(self):
		with self.assertRaises(InutilizacaoInvalida) as ctx:
			inutilizacao(justificativa="curta demais")

		self.assertEqual(ctx.exception.campo, "justificativa")

	def test_justificativa_longa_e_erro(self):
		with self.assertRaises(InutilizacaoInvalida):
			inutilizacao(justificativa="x" * (JUSTIFICATIVA_MAXIMA + 1))

	def test_limites_exatos_da_justificativa_passam(self):
		curta = inutilizacao(justificativa="x" * JUSTIFICATIVA_MINIMA)
		longa = inutilizacao(justificativa="x" * JUSTIFICATIVA_MAXIMA)

		self.assertEqual(len(curta["inutNFe"]["infInut"]["xJust"]), JUSTIFICATIVA_MINIMA)
		self.assertEqual(len(longa["inutNFe"]["infInut"]["xJust"]), JUSTIFICATIVA_MAXIMA)

	def test_serie_zero_e_aceita(self):
		"""TSerie aceita "0" (série única de contribuinte que não usa série) — caso
		especial que não passa pela mesma checagem de 'sem zero à esquerda'."""
		grupo = inutilizacao(serie="0")

		self.assertEqual(grupo["inutNFe"]["infInut"]["serie"], "0")


class AssinadorFalso:
	def __init__(self):
		self.recebido = None

	def assinar(self, xml: bytes, id_elemento: str):
		from erpnext_brasil.fiscal.documento.assinatura import MaterialAssinatura

		self.recebido = (xml, id_elemento)

		return MaterialAssinatura(
			digest="ZGlnZXN0", assinatura="YXNzaW5hdHVyYQ==", certificado="Y2VydA=="
		)


class TestAssinarInutilizacao(unittest.TestCase):
	def setUp(self):
		self.grupo = inutilizacao()
		self.assinador = AssinadorFalso()
		self.assinado = assinar_inutilizacao(self.grupo, self.assinador)

	def test_assina_o_id_do_infinut(self):
		self.assertEqual(self.assinador.recebido[1], self.grupo["inutNFe"]["infInut"]["@Id"])

	def test_signature_e_irma_de_infinut(self):
		self.assertIn("infInut", self.assinado["inutNFe"])
		self.assertIn("Signature", self.assinado["inutNFe"])
		self.assertNotIn("Signature", self.assinado["inutNFe"]["infInut"])

	def test_documento_assinado_serializa(self):
		from erpnext_brasil.fiscal.documento.serializacao import para_xml

		xml = para_xml(self.assinado)

		self.assertIn("<Signature ", xml)
		self.assertIn(f'Id="{self.grupo["inutNFe"]["infInut"]["@Id"]}"', xml)


def _xml_ret_inut(cstat="102", motivo="Inutilizacao de numero homologado", protocolo="111260000012345"):
	return (
		'<retInutNFe xmlns="http://www.portalfiscal.inf.br/nfe">'
		f"<infInut><cStat>{cstat}</cStat><xMotivo>{motivo}</xMotivo>"
		f"<nProt>{protocolo}</nProt><dhRecbto>2026-08-28T10:00:00-04:00</dhRecbto>"
		"</infInut></retInutNFe>"
	)


class TestInterpretarRetornoInutilizacao(unittest.TestCase):
	def test_102_e_homologada(self):
		retorno = interpretar_retorno_inutilizacao(_xml_ret_inut(cstat=CODIGO_SUCESSO_INUTILIZACAO))

		self.assertTrue(retorno.homologada)
		self.assertEqual(retorno.protocolo, "111260000012345")

	def test_outro_cstat_nao_e_homologada(self):
		retorno = interpretar_retorno_inutilizacao(_xml_ret_inut(cstat="563", motivo="Rejeicao"))

		self.assertFalse(retorno.homologada)
		self.assertEqual(retorno.motivo, "Rejeicao")

	def test_sem_cstat_levanta_erro(self):
		from erpnext_brasil.fiscal.documento.resposta_sefaz import RespostaSefazInvalida

		with self.assertRaises(RespostaSefazInvalida):
			interpretar_retorno_inutilizacao("<retInutNFe></retInutNFe>")

	def test_retorno_e_congelado(self):
		retorno = RetornoInutilizacao(cstat="102", motivo="x")

		with self.assertRaises(Exception):
			retorno.cstat = "999"


class TestCodigoUfPorSigla(unittest.TestCase):
	"""Guarda a consistência entre as duas tabelas de UF: toda sigla mapeia para um
	código presente em `CODIGOS_UF_IBGE`, e as 27 UFs estão cobertas — divergência aqui
	seria um `cUF` errado indo pro XML sem nenhum erro aparente."""

	def test_todas_as_27_ufs_estao_presentes(self):
		self.assertEqual(len(CODIGO_UF_POR_SIGLA), 27)

	def test_todo_codigo_e_valido(self):
		for sigla, codigo in CODIGO_UF_POR_SIGLA.items():
			with self.subTest(sigla=sigla):
				self.assertIn(codigo, CODIGOS_UF_IBGE)

	def test_nao_ha_codigo_duplicado(self):
		self.assertEqual(len(set(CODIGO_UF_POR_SIGLA.values())), 27)

	def test_ro_e_11(self):
		"""RO é onde este app está localizado (norte do país) — o valor mais visado por
		um erro de digitação silencioso."""
		self.assertEqual(CODIGO_UF_POR_SIGLA["RO"], "11")


if __name__ == "__main__":
	unittest.main()
