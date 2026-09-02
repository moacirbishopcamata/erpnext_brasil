# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/documento/evento_mdfe.py` — evento de cancelamento do MDF-e."""

import unittest

from erpnext_brasil.fiscal.documento.assinatura import MaterialAssinatura
from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.fiscal.documento.evento_mdfe import (
	INDICADOR_ENCERRAMENTO_POR_TERCEIRO,
	JUSTIFICATIVA_MAXIMA_MDFE,
	JUSTIFICATIVA_MINIMA_MDFE,
	TIPO_EVENTO_CANCELAMENTO_MDFE,
	TIPO_EVENTO_ENCERRAMENTO_MDFE,
	TIPO_EVENTO_INCLUSAO_CONDUTOR_MDFE,
	TIPO_EVENTO_INCLUSAO_DFE_MDFE,
	Condutor,
	DocumentoIncluido,
	EventoInvalido,
	assinar_evento,
	montar_env_evento_mdfe,
	montar_evento_cancelamento_mdfe,
	montar_evento_encerramento_mdfe,
	montar_evento_inclusao_condutor_mdfe,
	montar_evento_inclusao_dfe_mdfe,
)
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.mdfe import NAMESPACE_MDFE

_CNPJ_VALIDO = "11222333000181"


def _chave_mdfe() -> str:
	return montar_chave(
		uf="35", ano_mes="2609", cnpj=_CNPJ_VALIDO, modelo="58", serie="001",
		numero="000000001", tipo_emissao="1", codigo_numerico="12345678",
	)


def _chave_nfe() -> str:
	return montar_chave(
		uf="35", ano_mes="2609", cnpj=_CNPJ_VALIDO, modelo="55", serie="001",
		numero="000000001", tipo_emissao="1", codigo_numerico="12345678",
	)


class AssinadorFalso:
	def __init__(self):
		self.recebido: tuple[bytes, str] | None = None

	def assinar(self, xml: bytes, id_elemento: str):
		self.recebido = (xml, id_elemento)
		return MaterialAssinatura(
			digest="ZGlnZXN0", assinatura="YXNzaW5hdHVyYQ==", certificado="Y2VydA=="
		)


class TestMontarEventoCancelamentoMdfe(unittest.TestCase):
	def setUp(self):
		self.chave = _chave_mdfe()
		self.evento = montar_evento_cancelamento_mdfe(
			chave_acesso=self.chave,
			protocolo="935260000000001",
			justificativa="Erro de digitação no cadastro do veículo tracionado.",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T21:00:00-03:00",
		)

	def test_usa_chmdfe_nao_chnfe_nem_chcte(self):
		inf_evento = self.evento["evento"]["infEvento"]

		self.assertEqual(inf_evento["chMDFe"], self.chave)
		self.assertNotIn("chNFe", inf_evento)
		self.assertNotIn("chCTe", inf_evento)

	def test_versao_fica_no_atributo_versaoevento_nao_em_verevento(self):
		"""Achado real: mesma forma do CT-e -- o MDF-e não tem elemento verEvento, a
		versão é atributo de detEvento."""
		inf_evento = self.evento["evento"]["infEvento"]

		self.assertNotIn("verEvento", inf_evento)
		self.assertEqual(inf_evento["detEvento"]["@versaoEvento"], "3.00")
		self.assertEqual(self.evento["evento"]["@versao"], "3.00")

	def test_id_tem_53_digitos_apos_id(self):
		"""Este módulo sempre grava nSeqEvento com 3 dígitos, mesma convenção do CT-e
		-- embora o schema do MDF-e tolere também 2 (ver docstring do módulo)."""
		id_elemento = self.evento["evento"]["infEvento"]["@Id"]

		self.assertTrue(id_elemento.startswith("ID"))
		self.assertEqual(len(id_elemento), len("ID") + 53)
		self.assertTrue(id_elemento.endswith("001"))

	def test_tp_evento_e_o_mesmo_numero_da_nfe_e_do_cte(self):
		"""Achado real: os três documentos (NF-e/CT-e/MDF-e) reaproveitam o mesmo
		código de cancelamento, 110111."""
		self.assertEqual(self.evento["evento"]["infEvento"]["tpEvento"], TIPO_EVENTO_CANCELAMENTO_MDFE)
		self.assertEqual(TIPO_EVENTO_CANCELAMENTO_MDFE, "110111")

	def test_namespace_e_o_do_mdfe(self):
		self.assertEqual(self.evento["evento"]["@xmlns"], NAMESPACE_MDFE)

	def test_justificativa_com_256_caracteres_e_invalida(self):
		texto_256 = "a" * 256

		with self.assertRaises(EventoInvalido):
			montar_evento_cancelamento_mdfe(
				chave_acesso=self.chave,
				protocolo="935260000000001",
				justificativa=texto_256,
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T21:00:00-03:00",
			)

	def test_justificativa_com_255_caracteres_e_valida(self):
		texto_255 = "a" * 255

		evento = montar_evento_cancelamento_mdfe(
			chave_acesso=self.chave,
			protocolo="935260000000001",
			justificativa=texto_255,
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T21:00:00-03:00",
		)

		self.assertEqual(len(evento["evento"]["infEvento"]["detEvento"]["xJust"]), 255)

	def test_limites_de_justificativa_confirmados(self):
		self.assertEqual(JUSTIFICATIVA_MINIMA_MDFE, 15)
		self.assertEqual(JUSTIFICATIVA_MAXIMA_MDFE, 255)

	def test_sem_protocolo_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_cancelamento_mdfe(
				chave_acesso=self.chave,
				protocolo="",
				justificativa="Justificativa válida com mais de quinze caracteres.",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T21:00:00-03:00",
			)

	def test_documento_assinado_serializa(self):
		assinado = assinar_evento(self.evento, AssinadorFalso())
		xml = para_xml(assinado)

		self.assertIn("<infEvento", xml)
		self.assertIn("<chMDFe>", xml)


class TestMontarEnvEventoMdfe(unittest.TestCase):
	def test_um_evento(self):
		chave = _chave_mdfe()
		evento = montar_evento_cancelamento_mdfe(
			chave_acesso=chave,
			protocolo="935260000000001",
			justificativa="Justificativa válida com mais de quinze caracteres.",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T21:00:00-03:00",
		)

		lote = montar_env_evento_mdfe([evento], "1")

		self.assertEqual(lote["envEvento"]["@xmlns"], NAMESPACE_MDFE)
		self.assertEqual(len(lote["envEvento"]["evento"]), 1)

	def test_lista_vazia_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_env_evento_mdfe([], "1")

	def test_mais_de_20_eventos_levanta_erro(self):
		chave = _chave_mdfe()
		evento = montar_evento_cancelamento_mdfe(
			chave_acesso=chave,
			protocolo="935260000000001",
			justificativa="Justificativa válida com mais de quinze caracteres.",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T21:00:00-03:00",
		)

		with self.assertRaises(EventoInvalido):
			montar_env_evento_mdfe([evento] * 21, "1")


class TestMontarEventoEncerramentoMdfe(unittest.TestCase):
	def setUp(self):
		self.chave = _chave_mdfe()
		self.evento = montar_evento_encerramento_mdfe(
			chave_acesso=self.chave,
			protocolo="935260000000001",
			data_encerramento="2026-09-02",
			codigo_uf="35",
			codigo_municipio="3550308",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T22:00:00-03:00",
		)

	def test_tp_evento_e_110112(self):
		self.assertEqual(self.evento["evento"]["infEvento"]["tpEvento"], TIPO_EVENTO_ENCERRAMENTO_MDFE)
		self.assertEqual(TIPO_EVENTO_ENCERRAMENTO_MDFE, "110112")

	def test_campos_basicos(self):
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]

		self.assertEqual(det_evento["descEvento"], "Encerramento")
		self.assertEqual(det_evento["dtEnc"], "2026-09-02")
		self.assertEqual(det_evento["cUF"], "35")
		self.assertEqual(det_evento["cMun"], "3550308")
		self.assertNotIn("indEncPorTerceiro", det_evento)

	def test_uf_99_exterior_e_aceita(self):
		"""Achado real: cUF usa TCodUfIBGE_EX, que aceita '99' para Exterior -- não a
		tabela normal de 27 UFs."""
		evento = montar_evento_encerramento_mdfe(
			chave_acesso=self.chave,
			protocolo="935260000000001",
			data_encerramento="2026-09-02",
			codigo_uf="99",
			codigo_municipio="3550308",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T22:00:00-03:00",
		)
		self.assertEqual(evento["evento"]["infEvento"]["detEvento"]["cUF"], "99")

	def test_uf_invalida_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_encerramento_mdfe(
				chave_acesso=self.chave,
				protocolo="935260000000001",
				data_encerramento="2026-09-02",
				codigo_uf="00",
				codigo_municipio="3550308",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T22:00:00-03:00",
			)

	def test_municipio_com_menos_de_7_digitos_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_encerramento_mdfe(
				chave_acesso=self.chave,
				protocolo="935260000000001",
				data_encerramento="2026-09-02",
				codigo_uf="35",
				codigo_municipio="12345",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T22:00:00-03:00",
			)

	def test_encerrado_por_terceiro_grava_indicador(self):
		evento = montar_evento_encerramento_mdfe(
			chave_acesso=self.chave,
			protocolo="935260000000001",
			data_encerramento="2026-09-02",
			codigo_uf="35",
			codigo_municipio="3550308",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T22:00:00-03:00",
			encerrado_por_terceiro=True,
		)
		self.assertEqual(
			evento["evento"]["infEvento"]["detEvento"]["indEncPorTerceiro"],
			INDICADOR_ENCERRAMENTO_POR_TERCEIRO,
		)

	def test_sem_protocolo_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_encerramento_mdfe(
				chave_acesso=self.chave,
				protocolo="",
				data_encerramento="2026-09-02",
				codigo_uf="35",
				codigo_municipio="3550308",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T22:00:00-03:00",
			)

	def test_documento_assinado_serializa(self):
		assinado = assinar_evento(self.evento, AssinadorFalso())
		xml = para_xml(assinado)

		self.assertIn("<dtEnc>", xml)
		self.assertIn("<chMDFe>", xml)


class TestMontarEventoInclusaoCondutorMdfe(unittest.TestCase):
	def setUp(self):
		self.chave = _chave_mdfe()
		self.evento = montar_evento_inclusao_condutor_mdfe(
			chave_acesso=self.chave,
			condutor=Condutor(nome="José da Silva", cpf="11144477735"),
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T23:00:00-03:00",
		)

	def test_tp_evento_e_110114(self):
		self.assertEqual(
			self.evento["evento"]["infEvento"]["tpEvento"], TIPO_EVENTO_INCLUSAO_CONDUTOR_MDFE
		)
		self.assertEqual(TIPO_EVENTO_INCLUSAO_CONDUTOR_MDFE, "110114")

	def test_desc_evento_sem_acento(self):
		"""Achado real: única grafia possível, sem acento -- diferente de outros
		eventos desta frente que oferecem variante acentuada."""
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]
		self.assertEqual(det_evento["descEvento"], "Inclusao Condutor")

	def test_condutor_reaproveita_forma_do_veictracao(self):
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]

		self.assertEqual(det_evento["condutor"]["xNome"], "José da Silva")
		self.assertEqual(det_evento["condutor"]["CPF"], "11144477735")

	def test_cpf_invalido_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_inclusao_condutor_mdfe(
				chave_acesso=self.chave,
				condutor=Condutor(nome="José da Silva", cpf="00000000000"),
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T23:00:00-03:00",
			)

	def test_documento_assinado_serializa(self):
		assinado = assinar_evento(self.evento, AssinadorFalso())
		xml = para_xml(assinado)

		self.assertIn("<condutor>", xml)
		self.assertIn("<chMDFe>", xml)


class TestMontarEventoInclusaoDfeMdfe(unittest.TestCase):
	def setUp(self):
		self.chave = _chave_mdfe()
		self.chave_nfe = _chave_nfe()
		self.evento = montar_evento_inclusao_dfe_mdfe(
			chave_acesso=self.chave,
			protocolo="935260000000001",
			codigo_municipio_carrega="3550308",
			nome_municipio_carrega="São Paulo",
			documentos=[
				DocumentoIncluido(
					codigo_municipio_descarga="3304557",
					nome_municipio_descarga="Rio de Janeiro",
					chave_nfe=self.chave_nfe,
				)
			],
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-03T09:00:00-03:00",
		)

	def test_tp_evento_e_110115(self):
		self.assertEqual(
			self.evento["evento"]["infEvento"]["tpEvento"], TIPO_EVENTO_INCLUSAO_DFE_MDFE
		)
		self.assertEqual(TIPO_EVENTO_INCLUSAO_DFE_MDFE, "110115")

	def test_campos_de_carregamento(self):
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]

		self.assertEqual(det_evento["descEvento"], "Inclusão DF-e")
		self.assertEqual(det_evento["cMunCarrega"], "3550308")
		self.assertEqual(det_evento["xMunCarrega"], "São Paulo")

	def test_infdoc_com_uma_nfe(self):
		inf_doc = self.evento["evento"]["infEvento"]["detEvento"]["infDoc"]

		self.assertEqual(len(inf_doc), 1)
		self.assertEqual(inf_doc[0]["cMunDescarga"], "3304557")
		self.assertEqual(inf_doc[0]["xMunDescarga"], "Rio de Janeiro")
		self.assertEqual(inf_doc[0]["chNFe"], self.chave_nfe)

	def test_infdoc_recusa_chave_que_nao_e_nfe(self):
		"""Achado real: este evento só aceita NF-e, nunca CT-e -- diferente do infDoc
		da orquestração principal do MDF-e, que aceita os dois."""
		with self.assertRaises(EventoInvalido):
			montar_evento_inclusao_dfe_mdfe(
				chave_acesso=self.chave,
				protocolo="935260000000001",
				codigo_municipio_carrega="3550308",
				nome_municipio_carrega="São Paulo",
				documentos=[
					DocumentoIncluido(
						codigo_municipio_descarga="3304557",
						nome_municipio_descarga="Rio de Janeiro",
						chave_nfe=self.chave,
					)
				],
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-03T09:00:00-03:00",
			)

	def test_sem_documentos_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_inclusao_dfe_mdfe(
				chave_acesso=self.chave,
				protocolo="935260000000001",
				codigo_municipio_carrega="3550308",
				nome_municipio_carrega="São Paulo",
				documentos=[],
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-03T09:00:00-03:00",
			)

	def test_nome_municipio_descarga_curto_demais_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			DocumentoIncluido(
				codigo_municipio_descarga="3304557", nome_municipio_descarga="R", chave_nfe=self.chave_nfe
			)

	def test_documento_assinado_serializa(self):
		assinado = assinar_evento(self.evento, AssinadorFalso())
		xml = para_xml(assinado)

		self.assertIn("<infDoc>", xml)
		self.assertIn("<chMDFe>", xml)


if __name__ == "__main__":
	unittest.main()
