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

import unittest
from dataclasses import FrozenInstanceError

from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.fiscal.documento.estado import JUSTIFICATIVA_MAXIMA, JUSTIFICATIVA_MINIMA
from erpnext_brasil.fiscal.documento.evento import (
	CODIGOS_SUCESSO_CANCELAMENTO,
	CODIGOS_SUCESSO_CORRECAO,
	CORRECAO_MAXIMA,
	CORRECAO_MINIMA,
	TIPO_EVENTO_CANCELAMENTO,
	TIPO_EVENTO_CORRECAO,
	XCONDUSO_CCE,
	EventoInvalido,
	RetornoEvento,
	assinar_evento,
	interpretar_retorno_evento,
	montar_env_evento,
	montar_evento_cancelamento,
	montar_evento_correcao,
)
from erpnext_brasil.fiscal.documento.serializacao import para_xml

CHAVE = montar_chave("11", "2608", "11222333000181", "55", "1", "1", "1", "12345678")
JUSTIFICATIVA = "Erro de digitacao no valor do item"
TEXTO_CORRECAO = "Corrigir o descritivo do item 1 onde se le X leia-se Y, conforme combinado"


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


def correcao(**ajustes):
	valores = {
		"chave_acesso": CHAVE,
		"texto_correcao": TEXTO_CORRECAO,
		"cnpj_autor": "11.222.333/0001-81",
		"data_evento": "2026-08-24T10:00:00-04:00",
	}
	valores.update(ajustes)

	return montar_evento_correcao(**valores)


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


class TestCartaDeCorrecao(unittest.TestCase):
	"""`infEvento` da carta de correção compartilha a mesma ordem do cancelamento — só
	`detEvento` muda (xCorrecao/xCondUso em vez de nProt/xJust) e os limites de tamanho
	do texto livre são diferentes (15 a 1000, não 15 a 256)."""

	def test_tipo_evento_e_fixo(self):
		self.assertEqual(TIPO_EVENTO_CORRECAO, "110110")
		self.assertEqual(correcao()["evento"]["infEvento"]["tpEvento"], "110110")

	def test_ordem_de_detevento(self):
		det = correcao()["evento"]["infEvento"]["detEvento"]

		self.assertEqual(list(det), ["@versao", "descEvento", "xCorrecao", "xCondUso"])

	def test_desc_evento_fixo(self):
		self.assertEqual(correcao()["evento"]["infEvento"]["detEvento"]["descEvento"], "Carta de Correção")

	def test_xconduso_e_sempre_o_texto_fixo(self):
		det = correcao()["evento"]["infEvento"]["detEvento"]

		self.assertEqual(det["xCondUso"], XCONDUSO_CCE)

	def test_id_usa_o_tipo_de_evento_correto(self):
		id_evento = correcao(numero_sequencia=1)["evento"]["infEvento"]["@Id"]

		self.assertEqual(id_evento, f"ID110110{CHAVE}01")

	def test_texto_curto_e_erro(self):
		with self.assertRaises(EventoInvalido) as ctx:
			correcao(texto_correcao="curto demais")

		self.assertEqual(ctx.exception.campo, "texto_correcao")

	def test_texto_longo_e_erro(self):
		with self.assertRaises(EventoInvalido):
			correcao(texto_correcao="x" * (CORRECAO_MAXIMA + 1))

	def test_limites_exatos_passam(self):
		curto = correcao(texto_correcao="x" * CORRECAO_MINIMA)
		longo = correcao(texto_correcao="x" * CORRECAO_MAXIMA)

		self.assertEqual(len(curto["evento"]["infEvento"]["detEvento"]["xCorrecao"]), CORRECAO_MINIMA)
		self.assertEqual(len(longo["evento"]["infEvento"]["detEvento"]["xCorrecao"]), CORRECAO_MAXIMA)

	def test_cnpj_invalido_e_erro(self):
		with self.assertRaises(EventoInvalido) as ctx:
			correcao(cnpj_autor="11222333000182")

		self.assertEqual(ctx.exception.campo, "cnpj_autor")

	def test_sequencia_fora_da_faixa(self):
		with self.assertRaises(EventoInvalido):
			correcao(numero_sequencia=21)

	def test_limite_de_15_e_o_minimo_diferente_da_justificativa_de_cancelamento(self):
		"""Documenta explicitamente que os dois eventos têm o mesmo piso (15) mas tetos
		diferentes (256 para xJust, 1000 para xCorrecao) — não é o mesmo número por
		coincidência de reuso de constante."""
		self.assertEqual(CORRECAO_MINIMA, JUSTIFICATIVA_MINIMA)
		self.assertNotEqual(CORRECAO_MAXIMA, JUSTIFICATIVA_MAXIMA)


def _xml_ret_env_evento(cstat_lote="128", inf_evento=""):
	return (
		'<retEnvEvento xmlns="http://www.portalfiscal.inf.br/nfe">'
		f"<cStat>{cstat_lote}</cStat><xMotivo>Lote processado</xMotivo>{inf_evento}"
		"</retEnvEvento>"
	)


def _xml_inf_evento(cstat, tipo_evento=None, nprot="135260000123456"):
	tp = f"<tpEvento>{tipo_evento}</tpEvento>" if tipo_evento else ""

	return (
		f"<retEvento><infEvento><cStat>{cstat}</cStat><xMotivo>x</xMotivo>"
		f"<chNFe>{CHAVE}</chNFe>{tp}<nProt>{nprot}</nProt>"
		"<dhRegEvento>2026-08-24T10:05:00-04:00</dhRegEvento>"
		"</infEvento></retEvento>"
	)


class TestInterpretarRetornoEvento(unittest.TestCase):
	"""`interpretar_retorno_evento` lê `retEnvEvento`; `RetornoEvento.homologado` decide
	sucesso a partir do `tpEvento` que a própria resposta traz — não de um único conjunto
	de códigos para todo evento (ver a nota no topo de `evento.py`)."""

	def test_le_cstat_e_motivo_do_lote(self):
		retorno = interpretar_retorno_evento(_xml_ret_env_evento())

		self.assertEqual(retorno.cstat_lote, "128")
		self.assertEqual(retorno.motivo_lote, "Lote processado")

	def test_sem_infevento_nao_e_homologado(self):
		retorno = interpretar_retorno_evento(_xml_ret_env_evento())

		self.assertIsNone(retorno.cstat_evento)
		self.assertFalse(retorno.homologado)

	def test_cancelamento_homologa_com_seus_tres_codigos(self):
		for codigo in CODIGOS_SUCESSO_CANCELAMENTO:
			with self.subTest(codigo=codigo):
				xml = _xml_ret_env_evento(
					inf_evento=_xml_inf_evento(codigo, tipo_evento=TIPO_EVENTO_CANCELAMENTO)
				)
				retorno = interpretar_retorno_evento(xml)

				self.assertTrue(retorno.homologado)

	def test_correcao_so_homologa_com_135(self):
		xml_ok = _xml_ret_env_evento(inf_evento=_xml_inf_evento("135", tipo_evento=TIPO_EVENTO_CORRECAO))
		self.assertTrue(interpretar_retorno_evento(xml_ok).homologado)

		# 101 e 155 são específicos de cancelamento — não valem para homologar uma CC-e,
		# mesmo sendo "códigos de sucesso" em outro contexto.
		for codigo in CODIGOS_SUCESSO_CANCELAMENTO - CODIGOS_SUCESSO_CORRECAO:
			with self.subTest(codigo=codigo):
				xml = _xml_ret_env_evento(
					inf_evento=_xml_inf_evento(codigo, tipo_evento=TIPO_EVENTO_CORRECAO)
				)
				self.assertFalse(interpretar_retorno_evento(xml).homologado)

	def test_tipo_evento_ausente_usa_fallback_generico(self):
		"""Resposta sem `tpEvento` (fixture incompleta, não uma resposta real da SEFAZ —
		o schema real sempre o inclui) cai no conjunto genérico: só 135 homologa."""
		xml_generico = _xml_ret_env_evento(inf_evento=_xml_inf_evento("135"))
		xml_especifico = _xml_ret_env_evento(inf_evento=_xml_inf_evento("101"))

		self.assertTrue(interpretar_retorno_evento(xml_generico).homologado)
		self.assertFalse(interpretar_retorno_evento(xml_especifico).homologado)

	def test_extrai_protocolo_e_chave_e_tipo_evento(self):
		xml = _xml_ret_env_evento(inf_evento=_xml_inf_evento("135", tipo_evento=TIPO_EVENTO_CORRECAO))
		retorno = interpretar_retorno_evento(xml)

		self.assertEqual(retorno.tipo_evento, TIPO_EVENTO_CORRECAO)
		self.assertEqual(retorno.chave_conferida, CHAVE)
		self.assertEqual(retorno.protocolo, "135260000123456")

	def test_retornoevento_e_congelado(self):
		retorno = RetornoEvento(cstat_lote="128", motivo_lote="x")

		with self.assertRaises(FrozenInstanceError):
			retorno.cstat_lote = "999"


class AssinadorFalso:
	"""Duplo que satisfaz a porta `Assinador` sem certificado — registra o que recebeu.
	Mesmo duplo usado em `test_nfe.TestAssinarNFe`."""

	def __init__(self):
		self.recebido: tuple[bytes, str] | None = None

	def assinar(self, xml: bytes, id_elemento: str):
		from erpnext_brasil.fiscal.documento.assinatura import MaterialAssinatura

		self.recebido = (xml, id_elemento)

		return MaterialAssinatura(digest="ZGlnZXN0", assinatura="YXNzaW5hdHVyYQ==", certificado="Y2VydA==")


class TestAssinarEvento(unittest.TestCase):
	"""Cobre a lacuna encontrada ao ligar `corrigir`/`cancelar` no adaptador real: um
	`evento` sem `Signature` é rejeitado pela SEFAZ (cardinalidade 1-1 em `TEvento`), e
	os testes de `transporte_sefaz.py` nunca pegariam isso — eles simulam a resposta,
	nunca inspecionam o XML de saída."""

	def setUp(self):
		self.grupo = evento()
		self.assinador = AssinadorFalso()
		self.assinado = assinar_evento(self.grupo, self.assinador)

	def test_assina_o_id_do_infevento(self):
		self.assertEqual(self.assinador.recebido[1], self.grupo["evento"]["infEvento"]["@Id"])

	def test_signature_e_irma_de_infevento(self):
		self.assertIn("infEvento", self.assinado["evento"])
		self.assertIn("Signature", self.assinado["evento"])
		self.assertNotIn("Signature", self.assinado["evento"]["infEvento"])

	def test_infevento_nao_muda_ao_assinar(self):
		self.assertEqual(self.assinado["evento"]["infEvento"], self.grupo["evento"]["infEvento"])

	def test_assina_com_o_xmlns_ja_aplicado(self):
		"""O XML passado ao assinador precisa já ter `xmlns` — assinar antes produziria
		um digest que não bate com o XML final enviado à SEFAZ."""
		xml_assinado = self.assinador.recebido[0].decode("utf-8")

		self.assertIn('xmlns="http://www.portalfiscal.inf.br/nfe"', xml_assinado)

	def test_documento_assinado_serializa(self):
		xml = para_xml(self.assinado)

		self.assertIn("<Signature ", xml)
		self.assertIn(f'Id="{self.grupo["evento"]["infEvento"]["@Id"]}"', xml)

	def test_funciona_para_correcao_tambem(self):
		"""A mesma função assina qualquer evento — cancelamento e CC-e têm o mesmo
		formato de `evento`, só `detEvento` muda, e `assinar_evento` não olha para
		dentro de `detEvento`."""
		grupo_cce = correcao()
		assinado = assinar_evento(grupo_cce, AssinadorFalso())

		self.assertIn("Signature", assinado["evento"])
		self.assertEqual(assinado["evento"]["infEvento"]["tpEvento"], TIPO_EVENTO_CORRECAO)


if __name__ == "__main__":
	unittest.main()
