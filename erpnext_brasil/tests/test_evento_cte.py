# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/documento/evento_cte.py` — eventos de cancelamento, carta de
correção e comprovante de entrega do CT-e."""

import base64
import hashlib
import unittest

from erpnext_brasil.fiscal.cte import MODAL_AEREO, MODAL_RODOVIARIO, NAMESPACE_CTE
from erpnext_brasil.fiscal.documento.assinatura import MaterialAssinatura
from erpnext_brasil.fiscal.documento.chave_acesso import ChaveInvalida, montar_chave
from erpnext_brasil.fiscal.documento.evento_cte import (
	JUSTIFICATIVA_MAXIMA_CTE,
	JUSTIFICATIVA_MINIMA_CTE,
	DESC_EVENTO_GTV,
	ESPECIE_GTV_CHEQUE,
	ESPECIE_GTV_NUMERARIO,
	INDICADOR_DESACORDO_OPERACAO,
	MOTIVO_INSUCESSO_ENDERECO_INEXISTENTE,
	MOTIVO_INSUCESSO_OUTROS,
	MOTIVO_INSUCESSO_RECEBEDOR_NAO_ENCONTRADO,
	TIPO_EVENTO_CANCELAMENTO_COMPROVANTE_ENTREGA_CTE,
	TIPO_EVENTO_CANCELAMENTO_CTE,
	TIPO_EVENTO_CANCELAMENTO_INSUCESSO_ENTREGA_CTE,
	TIPO_EVENTO_CANCELAMENTO_PRESTACAO_DESACORDO_CTE,
	TIPO_EVENTO_COMPROVANTE_ENTREGA_CTE,
	TIPO_EVENTO_CORRECAO_CTE,
	TIPO_EVENTO_EPEC_CTE,
	TIPO_EVENTO_GTV_CTE,
	TIPO_EVENTO_INSUCESSO_ENTREGA_CTE,
	TIPO_EVENTO_PRESTACAO_DESACORDO_CTE,
	TOMADOR_EPEC_DESTINATARIO,
	TOMADOR_EPEC_OUTROS,
	TOMADOR_EPEC_REMETENTE,
	CorrecaoCte,
	EspecieGtv,
	EventoInvalido,
	InfGtv,
	ParteGtv,
	TomadorEpec,
	assinar_evento,
	calcular_hash_entrega,
	montar_env_evento_cte,
	montar_evento_cancelamento_comprovante_entrega_cte,
	montar_evento_cancelamento_insucesso_entrega_cte,
	montar_evento_cancelamento_prestacao_desacordo_cte,
	montar_evento_comprovante_entrega_cte,
	montar_evento_cancelamento_cte,
	montar_evento_correcao_cte,
	montar_evento_epec_cte,
	montar_evento_gtv_cte,
	montar_evento_insucesso_entrega_cte,
	montar_evento_prestacao_desacordo_cte,
	montar_parte_gtv,
	montar_tomador_epec,
)
from erpnext_brasil.fiscal.documento.serializacao import para_xml

_CNPJ_VALIDO = "11222333000181"


def _chave_cte() -> str:
	return montar_chave(
		uf="35", ano_mes="2608", cnpj=_CNPJ_VALIDO, modelo="57", serie="001",
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


class TestMontarEventoCancelamentoCte(unittest.TestCase):
	def setUp(self):
		self.chave = _chave_cte()
		self.evento = montar_evento_cancelamento_cte(
			chave_acesso=self.chave,
			protocolo="135260000000001",
			justificativa="Erro de digitação no valor da prestação de serviço.",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-08-31T10:00:00-03:00",
		)

	def test_usa_chcte_nao_chnfe(self):
		"""Achado real: o campo é chCTe, não chNFe (diferente da NF-e)."""
		inf_evento = self.evento["evento"]["infEvento"]

		self.assertEqual(inf_evento["chCTe"], self.chave)
		self.assertNotIn("chNFe", inf_evento)

	def test_versao_fica_no_atributo_versaoevento_nao_em_verevento(self):
		"""Achado real: o CT-e não tem elemento verEvento -- a versão é um atributo
		de detEvento, diferente da NF-e."""
		inf_evento = self.evento["evento"]["infEvento"]

		self.assertNotIn("verEvento", inf_evento)
		self.assertEqual(inf_evento["detEvento"]["@versaoEvento"], "4.00")

	def test_id_tem_53_digitos_apos_id(self):
		"""Achado real: nSeqEvento entra com 3 dígitos no @Id do CT-e, não 2 como na
		NF-e -- o padrão é ID[0-9]{53}, não ID[0-9]{52}."""
		id_elemento = self.evento["evento"]["infEvento"]["@Id"]

		self.assertTrue(id_elemento.startswith("ID"))
		self.assertEqual(len(id_elemento), len("ID") + 53)
		self.assertTrue(id_elemento.endswith("001"))

	def test_tp_evento_e_o_mesmo_da_nfe(self):
		self.assertEqual(
			self.evento["evento"]["infEvento"]["tpEvento"], TIPO_EVENTO_CANCELAMENTO_CTE
		)
		self.assertEqual(TIPO_EVENTO_CANCELAMENTO_CTE, "110111")

	def test_namespace_e_o_do_cte(self):
		self.assertEqual(self.evento["evento"]["@xmlns"], NAMESPACE_CTE)

	def test_justificativa_com_256_caracteres_e_invalida(self):
		"""Achado real: o limite do CT-e é 255, não 256 como a NF-e -- reaproveitar a
		constante da NF-e teria deixado passar um texto que a SEFAZ rejeitaria."""
		texto_256 = "a" * 256

		with self.assertRaises(EventoInvalido):
			montar_evento_cancelamento_cte(
				chave_acesso=self.chave,
				protocolo="135260000000001",
				justificativa=texto_256,
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-08-31T10:00:00-03:00",
			)

	def test_justificativa_com_255_caracteres_e_valida(self):
		texto_255 = "a" * 255

		evento = montar_evento_cancelamento_cte(
			chave_acesso=self.chave,
			protocolo="135260000000001",
			justificativa=texto_255,
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-08-31T10:00:00-03:00",
		)

		self.assertEqual(len(evento["evento"]["infEvento"]["detEvento"]["xJust"]), 255)

	def test_limites_de_justificativa_confirmados(self):
		self.assertEqual(JUSTIFICATIVA_MINIMA_CTE, 15)
		self.assertEqual(JUSTIFICATIVA_MAXIMA_CTE, 255)

	def test_sem_protocolo_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_cancelamento_cte(
				chave_acesso=self.chave,
				protocolo="",
				justificativa="Justificativa válida com mais de quinze caracteres.",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-08-31T10:00:00-03:00",
			)


class TestAssinarEventoReaproveitado(unittest.TestCase):
	def test_assina_o_id_do_evento_cte(self):
		chave = _chave_cte()
		evento = montar_evento_cancelamento_cte(
			chave_acesso=chave,
			protocolo="135260000000001",
			justificativa="Justificativa válida com mais de quinze caracteres.",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-08-31T10:00:00-03:00",
		)
		assinador = AssinadorFalso()

		assinado = assinar_evento(evento, assinador)

		self.assertEqual(assinador.recebido[1], evento["evento"]["infEvento"]["@Id"])
		self.assertIn("Signature", assinado["evento"])
		self.assertNotIn("Signature", assinado["evento"]["infEvento"])

	def test_documento_assinado_serializa(self):
		chave = _chave_cte()
		evento = montar_evento_cancelamento_cte(
			chave_acesso=chave,
			protocolo="135260000000001",
			justificativa="Justificativa válida com mais de quinze caracteres.",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-08-31T10:00:00-03:00",
		)

		assinado = assinar_evento(evento, AssinadorFalso())
		xml = para_xml(assinado)

		self.assertIn("<infEvento", xml)
		self.assertIn("<chCTe>", xml)


class TestMontarEnvEventoCte(unittest.TestCase):
	def test_um_evento(self):
		chave = _chave_cte()
		evento = montar_evento_cancelamento_cte(
			chave_acesso=chave,
			protocolo="135260000000001",
			justificativa="Justificativa válida com mais de quinze caracteres.",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-08-31T10:00:00-03:00",
		)

		lote = montar_env_evento_cte([evento], "1")

		self.assertEqual(lote["envEvento"]["@xmlns"], NAMESPACE_CTE)
		self.assertEqual(len(lote["envEvento"]["evento"]), 1)

	def test_lista_vazia_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_env_evento_cte([], "1")

	def test_mais_de_20_eventos_levanta_erro(self):
		chave = _chave_cte()
		evento = montar_evento_cancelamento_cte(
			chave_acesso=chave,
			protocolo="135260000000001",
			justificativa="Justificativa válida com mais de quinze caracteres.",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-08-31T10:00:00-03:00",
		)

		with self.assertRaises(EventoInvalido):
			montar_env_evento_cte([evento] * 21, "1")


class TestMontarEventoCorrecaoCte(unittest.TestCase):
	def setUp(self):
		self.chave = _chave_cte()
		self.correcao = CorrecaoCte(
			grupo_alterado="ide", campo_alterado="natOp", valor_alterado="Prestação de serviço"
		)
		self.evento = montar_evento_correcao_cte(
			chave_acesso=self.chave,
			correcoes=[self.correcao],
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-08-31T10:00:00-03:00",
		)

	def test_e_estruturado_nao_texto_livre(self):
		"""Achado real: a CC-e do CT-e não tem xCorrecao (texto livre) -- tem
		infCorrecao, uma lista estruturada de alterações campo a campo."""
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]

		self.assertNotIn("xCorrecao", det_evento)
		self.assertEqual(
			det_evento["infCorrecao"],
			[{"grupoAlterado": "ide", "campoAlterado": "natOp", "valorAlterado": "Prestação de serviço"}],
		)

	def test_multiplas_correcoes_preservam_ordem(self):
		correcoes = [
			CorrecaoCte(grupo_alterado="ide", campo_alterado="natOp", valor_alterado="A"),
			CorrecaoCte(grupo_alterado="emit", campo_alterado="xNome", valor_alterado="B"),
		]

		evento = montar_evento_correcao_cte(
			chave_acesso=self.chave,
			correcoes=correcoes,
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-08-31T10:00:00-03:00",
		)

		inf_correcao = evento["evento"]["infEvento"]["detEvento"]["infCorrecao"]
		self.assertEqual(len(inf_correcao), 2)
		self.assertEqual(inf_correcao[0]["campoAlterado"], "natOp")
		self.assertEqual(inf_correcao[1]["campoAlterado"], "xNome")

	def test_numero_item_alterado_opcional(self):
		sem_indice = CorrecaoCte(grupo_alterado="det", campo_alterado="xProd", valor_alterado="X")
		com_indice = CorrecaoCte(
			grupo_alterado="det", campo_alterado="xProd", valor_alterado="X", numero_item_alterado=2
		)

		self.assertNotIn("nroItemAlterado", _montar_inf_correcao_publica(sem_indice))
		self.assertEqual(_montar_inf_correcao_publica(com_indice)["nroItemAlterado"], "2")

	def test_xconduso_cita_convenio_sinief_06_89_nao_o_da_nfe(self):
		"""Achado real: base legal diferente da NF-e (Art. 58-B do Convênio SINIEF
		06/89, não o Art. 7º do Convênio S/N de 1970)."""
		xconduso = self.evento["evento"]["infEvento"]["detEvento"]["xCondUso"]

		self.assertIn("CONVÊNIO/SINIEF 06/89", xconduso.upper())
		self.assertIn("Art. 58-B", xconduso)
		self.assertNotIn("Art. 7º", xconduso)

	def test_tp_evento_e_o_mesmo_numero_da_nfe(self):
		self.assertEqual(self.evento["evento"]["infEvento"]["tpEvento"], TIPO_EVENTO_CORRECAO_CTE)
		self.assertEqual(TIPO_EVENTO_CORRECAO_CTE, "110110")

	def test_sem_correcoes_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_correcao_cte(
				chave_acesso=self.chave,
				correcoes=[],
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-08-31T10:00:00-03:00",
			)

	def test_grupo_alterado_vazio_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			CorrecaoCte(grupo_alterado="", campo_alterado="natOp", valor_alterado="X")

	def test_numero_item_alterado_fora_do_intervalo_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			CorrecaoCte(
				grupo_alterado="det", campo_alterado="xProd", valor_alterado="X",
				numero_item_alterado=0,
			)

	def test_documento_assinado_serializa(self):
		assinado = assinar_evento(self.evento, AssinadorFalso())
		xml = para_xml(assinado)

		self.assertIn("<infCorrecao", xml)
		self.assertIn("<chCTe>", xml)


def _montar_inf_correcao_publica(correcao: CorrecaoCte) -> dict:
	"""Atalho de teste: monta uma única correção via a função pública, evitando
	depender do nome privado `_montar_inf_correcao` do módulo."""
	evento = montar_evento_correcao_cte(
		chave_acesso=_chave_cte(),
		correcoes=[correcao],
		cnpj_autor=_CNPJ_VALIDO,
		data_evento="2026-08-31T10:00:00-03:00",
	)
	return evento["evento"]["infEvento"]["detEvento"]["infCorrecao"][0]


def _chave_nfe() -> str:
	return montar_chave(
		uf="35", ano_mes="2608", cnpj=_CNPJ_VALIDO, modelo="55", serie="001",
		numero="000000001", tipo_emissao="1", codigo_numerico="12345678",
	)


class TestCalcularHashEntrega(unittest.TestCase):
	def test_bate_com_calculo_de_referencia(self):
		"""Prova o cálculo real: SHA-1 de chave+imagem, recodificado em Base64 -- não
		um valor arbitrário."""
		chave = _chave_cte()
		imagem = "aW1hZ2VtLWZha2U="

		esperado = base64.b64encode(hashlib.sha1((chave + imagem).encode("utf-8")).digest()).decode(
			"ascii"
		)

		self.assertEqual(calcular_hash_entrega(chave, imagem), esperado)

	def test_digest_sha1_tem_20_bytes_decodificados(self):
		"""Confirmado no XSD: base64Binary de comprimento 20 -- o tamanho exato de um
		digest SHA-1."""
		hash_calculado = calcular_hash_entrega(_chave_cte(), "qualquer-imagem")

		self.assertEqual(len(base64.b64decode(hash_calculado)), 20)

	def test_chave_invalida_levanta_erro(self):
		with self.assertRaises(ChaveInvalida):
			calcular_hash_entrega("chave-invalida", "imagem")


class TestMontarEventoComprovanteEntregaCte(unittest.TestCase):
	def setUp(self):
		self.chave = _chave_cte()
		self.evento = montar_evento_comprovante_entrega_cte(
			chave_acesso=self.chave,
			protocolo="135260000000001",
			data_entrega="2026-08-31T15:00:00-03:00",
			numero_documento_recebedor="123456789",
			nome_recebedor="João da Silva",
			imagem_base64="aW1hZ2VtLWZha2U=",
			data_hash="2026-08-31T15:00:01-03:00",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-08-31T15:00:02-03:00",
		)

	def test_tp_evento_e_codigo_proprio_sem_equivalente_na_nfe(self):
		self.assertEqual(
			self.evento["evento"]["infEvento"]["tpEvento"], TIPO_EVENTO_COMPROVANTE_ENTREGA_CTE
		)
		self.assertEqual(TIPO_EVENTO_COMPROVANTE_ENTREGA_CTE, "110180")

	def test_campos_basicos(self):
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]

		self.assertEqual(det_evento["descEvento"], "Comprovante de Entrega do CT-e")
		self.assertEqual(det_evento["nDoc"], "123456789")
		self.assertEqual(det_evento["xNome"], "João da Silva")
		self.assertIn("hashEntrega", det_evento)
		self.assertNotIn("latitude", det_evento)
		self.assertNotIn("infEntrega", det_evento)

	def test_coordenadas_opcionais_formatadas_com_6_casas(self):
		evento = montar_evento_comprovante_entrega_cte(
			chave_acesso=self.chave,
			protocolo="135260000000001",
			data_entrega="2026-08-31T15:00:00-03:00",
			numero_documento_recebedor="123456789",
			nome_recebedor="João da Silva",
			imagem_base64="aW1hZ2VtLWZha2U=",
			data_hash="2026-08-31T15:00:01-03:00",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-08-31T15:00:02-03:00",
			latitude=-23.5,
			longitude=-46.63,
		)

		det_evento = evento["evento"]["infEvento"]["detEvento"]
		self.assertEqual(det_evento["latitude"], "-23.500000")
		self.assertEqual(det_evento["longitude"], "-46.630000")

	def test_latitude_fora_do_intervalo_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_comprovante_entrega_cte(
				chave_acesso=self.chave,
				protocolo="135260000000001",
				data_entrega="2026-08-31T15:00:00-03:00",
				numero_documento_recebedor="123456789",
				nome_recebedor="João da Silva",
				imagem_base64="aW1hZ2VtLWZha2U=",
				data_hash="2026-08-31T15:00:01-03:00",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-08-31T15:00:02-03:00",
				latitude=95.0,
			)

	def test_infentrega_com_chaves_de_nfe(self):
		chave_nfe = _chave_nfe()

		evento = montar_evento_comprovante_entrega_cte(
			chave_acesso=self.chave,
			protocolo="135260000000001",
			data_entrega="2026-08-31T15:00:00-03:00",
			numero_documento_recebedor="123456789",
			nome_recebedor="João da Silva",
			imagem_base64="aW1hZ2VtLWZha2U=",
			data_hash="2026-08-31T15:00:01-03:00",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-08-31T15:00:02-03:00",
			chaves_nfe_entregues=[chave_nfe],
		)

		self.assertEqual(
			evento["evento"]["infEvento"]["detEvento"]["infEntrega"], [{"chNFe": chave_nfe}]
		)

	def test_infentrega_recusa_chave_que_nao_e_de_nfe(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_comprovante_entrega_cte(
				chave_acesso=self.chave,
				protocolo="135260000000001",
				data_entrega="2026-08-31T15:00:00-03:00",
				numero_documento_recebedor="123456789",
				nome_recebedor="João da Silva",
				imagem_base64="aW1hZ2VtLWZha2U=",
				data_hash="2026-08-31T15:00:01-03:00",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-08-31T15:00:02-03:00",
				chaves_nfe_entregues=[self.chave],
			)

	def test_nome_recebedor_curto_demais_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_comprovante_entrega_cte(
				chave_acesso=self.chave,
				protocolo="135260000000001",
				data_entrega="2026-08-31T15:00:00-03:00",
				numero_documento_recebedor="123456789",
				nome_recebedor="J",
				imagem_base64="aW1hZ2VtLWZha2U=",
				data_hash="2026-08-31T15:00:01-03:00",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-08-31T15:00:02-03:00",
			)

	def test_documento_assinado_serializa(self):
		assinado = assinar_evento(self.evento, AssinadorFalso())
		xml = para_xml(assinado)

		self.assertIn("<hashEntrega", xml)
		self.assertIn("<chCTe>", xml)


class TestTomadorEpec(unittest.TestCase):
	def test_aceita_qualquer_um_dos_5_papeis(self):
		"""Achado real: diferente do toma4 real da ide (fixo em '4'), o toma4 do EPEC
		aceita qualquer papel."""
		for papel in (TOMADOR_EPEC_REMETENTE, TOMADOR_EPEC_DESTINATARIO, TOMADOR_EPEC_OUTROS):
			tomador = TomadorEpec(papel=papel, uf="SP", cnpj_cpf=_CNPJ_VALIDO)
			self.assertEqual(tomador.papel, papel)

	def test_papel_invalido_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			TomadorEpec(papel="9", uf="SP", cnpj_cpf=_CNPJ_VALIDO)


class TestMontarTomadorEpec(unittest.TestCase):
	def test_cnpj_valido_monta_grupo_cnpj(self):
		grupo = montar_tomador_epec(
			TomadorEpec(papel=TOMADOR_EPEC_OUTROS, uf="SP", cnpj_cpf=_CNPJ_VALIDO)
		)["toma4"]

		self.assertEqual(grupo["toma"], TOMADOR_EPEC_OUTROS)
		self.assertEqual(grupo["CNPJ"], _CNPJ_VALIDO)
		self.assertNotIn("CPF", grupo)
		self.assertNotIn("IE", grupo)
		self.assertNotIn("xNome", grupo)

	def test_cpf_valido_monta_grupo_cpf(self):
		grupo = montar_tomador_epec(
			TomadorEpec(papel=TOMADOR_EPEC_REMETENTE, uf="SP", cnpj_cpf="11144477735")
		)["toma4"]

		self.assertEqual(grupo["CPF"], "11144477735")
		self.assertNotIn("CNPJ", grupo)

	def test_ie_opcional(self):
		grupo = montar_tomador_epec(
			TomadorEpec(
				papel=TOMADOR_EPEC_OUTROS, uf="SP", cnpj_cpf=_CNPJ_VALIDO,
				inscricao_estadual="123456789",
			)
		)["toma4"]

		self.assertEqual(grupo["IE"], "123456789")

	def test_documento_invalido_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_tomador_epec(TomadorEpec(papel=TOMADOR_EPEC_OUTROS, uf="SP", cnpj_cpf="0"))


class TestMontarEventoEpecCte(unittest.TestCase):
	def setUp(self):
		self.chave = _chave_cte()
		self.tomador = TomadorEpec(papel=TOMADOR_EPEC_OUTROS, uf="SP", cnpj_cpf=_CNPJ_VALIDO)
		self.evento = montar_evento_epec_cte(
			chave_acesso=self.chave,
			justificativa="Contingência por indisponibilidade do sistema da SEFAZ.",
			valor_icms="100.00",
			valor_total_prestacao="1000.00",
			valor_carga="5000.00",
			tomador=self.tomador,
			modal=MODAL_RODOVIARIO,
			uf_inicio="SP",
			uf_fim="RJ",
			data_emissao_cte="2026-08-31T10:00:00-03:00",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-08-31T10:00:01-03:00",
		)

	def test_tp_evento_e_codigo_proprio(self):
		self.assertEqual(self.evento["evento"]["infEvento"]["tpEvento"], TIPO_EVENTO_EPEC_CTE)
		self.assertEqual(TIPO_EVENTO_EPEC_CTE, "110113")

	def test_id_tem_53_digitos_apos_id(self):
		id_elemento = self.evento["evento"]["infEvento"]["@Id"]
		self.assertEqual(len(id_elemento), len("ID") + 53)

	def test_tpcte_fixo_em_0_mesmo_nao_sendo_parametro(self):
		"""Achado real: o tpCTe do EPEC só aceita '0' (CT-e Normal) -- diferente do
		tpCTe da ide, que aceita 0/1/3. Não é parâmetro da função."""
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]
		self.assertEqual(det_evento["tpCTe"], "0")

	def test_campos_basicos(self):
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]

		self.assertEqual(det_evento["descEvento"], "EPEC")
		self.assertEqual(det_evento["vICMS"], "100.00")
		self.assertEqual(det_evento["vTPrest"], "1000.00")
		self.assertEqual(det_evento["vCarga"], "5000.00")
		self.assertEqual(det_evento["modal"], MODAL_RODOVIARIO)
		self.assertEqual(det_evento["UFIni"], "SP")
		self.assertEqual(det_evento["UFFim"], "RJ")
		self.assertEqual(det_evento["dhEmi"], "2026-08-31T10:00:00-03:00")
		self.assertNotIn("vICMSST", det_evento)

	def test_toma4_esta_embutido_no_det_evento(self):
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]
		self.assertEqual(det_evento["toma4"]["toma"], TOMADOR_EPEC_OUTROS)
		self.assertEqual(det_evento["toma4"]["CNPJ"], _CNPJ_VALIDO)

	def test_vicmsst_opcional_quando_informado(self):
		evento = montar_evento_epec_cte(
			chave_acesso=self.chave,
			justificativa="Contingência por indisponibilidade do sistema da SEFAZ.",
			valor_icms="100.00",
			valor_total_prestacao="1000.00",
			valor_carga="5000.00",
			tomador=self.tomador,
			modal=MODAL_RODOVIARIO,
			uf_inicio="SP",
			uf_fim="RJ",
			data_emissao_cte="2026-08-31T10:00:00-03:00",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-08-31T10:00:01-03:00",
			valor_icms_st="10.00",
		)

		self.assertEqual(evento["evento"]["infEvento"]["detEvento"]["vICMSST"], "10.00")

	def test_vtprest_pode_ser_zero_para_cte_complementar(self):
		"""O XSD permite vTPrest zero para CT-e de complemento de valores."""
		evento = montar_evento_epec_cte(
			chave_acesso=self.chave,
			justificativa="Contingência por indisponibilidade do sistema da SEFAZ.",
			valor_icms="0.00",
			valor_total_prestacao="0.00",
			valor_carga="0.00",
			tomador=self.tomador,
			modal=MODAL_RODOVIARIO,
			uf_inicio="SP",
			uf_fim="RJ",
			data_emissao_cte="2026-08-31T10:00:00-03:00",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-08-31T10:00:01-03:00",
		)

		self.assertEqual(evento["evento"]["infEvento"]["detEvento"]["vTPrest"], "0.00")

	def test_modal_invalido_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_epec_cte(
				chave_acesso=self.chave,
				justificativa="Contingência por indisponibilidade do sistema da SEFAZ.",
				valor_icms="100.00",
				valor_total_prestacao="1000.00",
				valor_carga="5000.00",
				tomador=self.tomador,
				modal="9",
				uf_inicio="SP",
				uf_fim="RJ",
				data_emissao_cte="2026-08-31T10:00:00-03:00",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-08-31T10:00:01-03:00",
			)

	def test_modal_aereo_tambem_aceito(self):
		evento = montar_evento_epec_cte(
			chave_acesso=self.chave,
			justificativa="Contingência por indisponibilidade do sistema da SEFAZ.",
			valor_icms="100.00",
			valor_total_prestacao="1000.00",
			valor_carga="5000.00",
			tomador=self.tomador,
			modal=MODAL_AEREO,
			uf_inicio="SP",
			uf_fim="RJ",
			data_emissao_cte="2026-08-31T10:00:00-03:00",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-08-31T10:00:01-03:00",
		)

		self.assertEqual(evento["evento"]["infEvento"]["detEvento"]["modal"], MODAL_AEREO)

	def test_justificativa_com_256_caracteres_e_invalida(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_epec_cte(
				chave_acesso=self.chave,
				justificativa="a" * 256,
				valor_icms="100.00",
				valor_total_prestacao="1000.00",
				valor_carga="5000.00",
				tomador=self.tomador,
				modal=MODAL_RODOVIARIO,
				uf_inicio="SP",
				uf_fim="RJ",
				data_emissao_cte="2026-08-31T10:00:00-03:00",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-08-31T10:00:01-03:00",
			)

	def test_documento_assinado_serializa(self):
		assinado = assinar_evento(self.evento, AssinadorFalso())
		xml = para_xml(assinado)

		self.assertIn("<toma4>", xml)
		self.assertIn("<chCTe>", xml)
		self.assertIn("<tpCTe>0</tpCTe>", xml)


class TestMontarEventoCancelamentoComprovanteEntregaCte(unittest.TestCase):
	def setUp(self):
		self.chave = _chave_cte()
		self.evento = montar_evento_cancelamento_comprovante_entrega_cte(
			chave_acesso=self.chave,
			protocolo="135260000000001",
			protocolo_comprovante_entrega="135260000000002",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T10:00:00-03:00",
		)

	def test_tp_evento_e_110181_nao_o_da_carta_de_correcao(self):
		"""Achado real: 'CE' aqui é Comprovante de Entrega, não Carta de Correção --
		tpEvento 110181, diferente de 110110 (CC-e) e 110180 (comprovante de entrega)."""
		self.assertEqual(
			self.evento["evento"]["infEvento"]["tpEvento"],
			TIPO_EVENTO_CANCELAMENTO_COMPROVANTE_ENTREGA_CTE,
		)
		self.assertEqual(TIPO_EVENTO_CANCELAMENTO_COMPROVANTE_ENTREGA_CTE, "110181")

	def test_dois_protocolos_distintos_nao_o_mesmo_repetido(self):
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]

		self.assertEqual(det_evento["nProt"], "135260000000001")
		self.assertEqual(det_evento["nProtCE"], "135260000000002")
		self.assertNotEqual(det_evento["nProt"], det_evento["nProtCE"])

	def test_desc_evento_fixo(self):
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]
		self.assertEqual(det_evento["descEvento"], "Cancelamento do Comprovante de Entrega do CT-e")

	def test_sem_protocolo_do_cte_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_cancelamento_comprovante_entrega_cte(
				chave_acesso=self.chave,
				protocolo="",
				protocolo_comprovante_entrega="135260000000002",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T10:00:00-03:00",
			)

	def test_sem_protocolo_do_comprovante_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_cancelamento_comprovante_entrega_cte(
				chave_acesso=self.chave,
				protocolo="135260000000001",
				protocolo_comprovante_entrega="",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T10:00:00-03:00",
			)

	def test_documento_assinado_serializa(self):
		assinado = assinar_evento(self.evento, AssinadorFalso())
		xml = para_xml(assinado)

		self.assertIn("<nProtCE>", xml)
		self.assertIn("<chCTe>", xml)


class TestMontarEventoInsucessoEntregaCte(unittest.TestCase):
	def setUp(self):
		self.chave = _chave_cte()
		self.evento = montar_evento_insucesso_entrega_cte(
			chave_acesso=self.chave,
			protocolo="135260000000001",
			data_tentativa_entrega="2026-09-02T15:00:00-03:00",
			tipo_motivo=MOTIVO_INSUCESSO_RECEBEDOR_NAO_ENCONTRADO,
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T15:00:01-03:00",
		)

	def test_tp_evento_e_110190(self):
		self.assertEqual(
			self.evento["evento"]["infEvento"]["tpEvento"], TIPO_EVENTO_INSUCESSO_ENTREGA_CTE
		)
		self.assertEqual(TIPO_EVENTO_INSUCESSO_ENTREGA_CTE, "110190")

	def test_desc_evento_e_campos_basicos(self):
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]

		self.assertEqual(det_evento["descEvento"], "Insucesso na Entrega do CT-e")
		self.assertEqual(det_evento["tpMotivo"], MOTIVO_INSUCESSO_RECEBEDOR_NAO_ENCONTRADO)
		self.assertNotIn("xJustMotivo", det_evento)
		self.assertNotIn("hashTentativaEntrega", det_evento)
		self.assertNotIn("nTentativa", det_evento)

	def test_motivo_outros_exige_justificativa(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_insucesso_entrega_cte(
				chave_acesso=self.chave,
				protocolo="135260000000001",
				data_tentativa_entrega="2026-09-02T15:00:00-03:00",
				tipo_motivo=MOTIVO_INSUCESSO_OUTROS,
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T15:00:01-03:00",
			)

	def test_motivo_outros_com_justificativa_valida(self):
		evento = montar_evento_insucesso_entrega_cte(
			chave_acesso=self.chave,
			protocolo="135260000000001",
			data_tentativa_entrega="2026-09-02T15:00:00-03:00",
			tipo_motivo=MOTIVO_INSUCESSO_OUTROS,
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T15:00:01-03:00",
			justificativa_motivo="a" * 256,
		)

		self.assertEqual(len(evento["evento"]["infEvento"]["detEvento"]["xJustMotivo"]), 256)

	def test_xjustmotivo_aceita_256_diferente_de_tjust_255(self):
		"""Achado real: xJustMotivo usa TString (15-256), não TJust (15-255) -- 256
		caracteres é válido aqui, diferente do cancelamento/EPEC."""
		evento = montar_evento_insucesso_entrega_cte(
			chave_acesso=self.chave,
			protocolo="135260000000001",
			data_tentativa_entrega="2026-09-02T15:00:00-03:00",
			tipo_motivo=MOTIVO_INSUCESSO_OUTROS,
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T15:00:01-03:00",
			justificativa_motivo="a" * 256,
		)
		self.assertEqual(len(evento["evento"]["infEvento"]["detEvento"]["xJustMotivo"]), 256)

	def test_justificativa_com_257_caracteres_e_invalida(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_insucesso_entrega_cte(
				chave_acesso=self.chave,
				protocolo="135260000000001",
				data_tentativa_entrega="2026-09-02T15:00:00-03:00",
				tipo_motivo=MOTIVO_INSUCESSO_OUTROS,
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T15:00:01-03:00",
				justificativa_motivo="a" * 257,
			)

	def test_justificativa_proibida_fora_do_motivo_outros(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_insucesso_entrega_cte(
				chave_acesso=self.chave,
				protocolo="135260000000001",
				data_tentativa_entrega="2026-09-02T15:00:00-03:00",
				tipo_motivo=MOTIVO_INSUCESSO_ENDERECO_INEXISTENTE,
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T15:00:01-03:00",
				justificativa_motivo="Justificativa válida com mais de quinze caracteres.",
			)

	def test_motivo_invalido_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_insucesso_entrega_cte(
				chave_acesso=self.chave,
				protocolo="135260000000001",
				data_tentativa_entrega="2026-09-02T15:00:00-03:00",
				tipo_motivo="9",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T15:00:01-03:00",
			)

	def test_hash_opcional_quando_imagem_informada(self):
		"""Achado real: diferente do comprovante de entrega, o hash aqui é opcional --
		calculado só quando a imagem é informada."""
		evento = montar_evento_insucesso_entrega_cte(
			chave_acesso=self.chave,
			protocolo="135260000000001",
			data_tentativa_entrega="2026-09-02T15:00:00-03:00",
			tipo_motivo=MOTIVO_INSUCESSO_RECEBEDOR_NAO_ENCONTRADO,
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T15:00:01-03:00",
			imagem_base64="aW1hZ2VtLWZha2U=",
			data_hash="2026-09-02T15:00:02-03:00",
		)

		esperado = calcular_hash_entrega(self.chave, "aW1hZ2VtLWZha2U=")
		self.assertEqual(evento["evento"]["infEvento"]["detEvento"]["hashTentativaEntrega"], esperado)

	def test_numero_tentativa_formatado_com_3_digitos(self):
		evento = montar_evento_insucesso_entrega_cte(
			chave_acesso=self.chave,
			protocolo="135260000000001",
			data_tentativa_entrega="2026-09-02T15:00:00-03:00",
			tipo_motivo=MOTIVO_INSUCESSO_RECEBEDOR_NAO_ENCONTRADO,
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T15:00:01-03:00",
			numero_tentativa=2,
		)

		self.assertEqual(evento["evento"]["infEvento"]["detEvento"]["nTentativa"], "002")

	def test_infentrega_reusa_mesma_validacao_do_comprovante(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_insucesso_entrega_cte(
				chave_acesso=self.chave,
				protocolo="135260000000001",
				data_tentativa_entrega="2026-09-02T15:00:00-03:00",
				tipo_motivo=MOTIVO_INSUCESSO_RECEBEDOR_NAO_ENCONTRADO,
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T15:00:01-03:00",
				chaves_nfe_nao_entregues=[self.chave],
			)

	def test_documento_assinado_serializa(self):
		assinado = assinar_evento(self.evento, AssinadorFalso())
		xml = para_xml(assinado)

		self.assertIn("<dhTentativaEntrega>", xml)
		self.assertIn("<chCTe>", xml)


class TestMontarEventoCancelamentoInsucessoEntregaCte(unittest.TestCase):
	def setUp(self):
		self.chave = _chave_cte()
		self.evento = montar_evento_cancelamento_insucesso_entrega_cte(
			chave_acesso=self.chave,
			protocolo="135260000000001",
			protocolo_insucesso_entrega="135260000000003",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T16:00:00-03:00",
		)

	def test_tp_evento_e_110191(self):
		self.assertEqual(
			self.evento["evento"]["infEvento"]["tpEvento"],
			TIPO_EVENTO_CANCELAMENTO_INSUCESSO_ENTREGA_CTE,
		)
		self.assertEqual(TIPO_EVENTO_CANCELAMENTO_INSUCESSO_ENTREGA_CTE, "110191")

	def test_usa_nprotie_nao_nprotce(self):
		"""Achado real: mesma forma do evCancCECTe, mas o campo do segundo protocolo
		é nProtIE, não nProtCE -- confirmado idêntico caso contrário."""
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]

		self.assertEqual(det_evento["nProtIE"], "135260000000003")
		self.assertNotIn("nProtCE", det_evento)

	def test_desc_evento_fixo(self):
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]
		self.assertEqual(det_evento["descEvento"], "Cancelamento do Insucesso de Entrega do CT-e")

	def test_sem_protocolo_do_insucesso_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_cancelamento_insucesso_entrega_cte(
				chave_acesso=self.chave,
				protocolo="135260000000001",
				protocolo_insucesso_entrega="",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T16:00:00-03:00",
			)

	def test_documento_assinado_serializa(self):
		assinado = assinar_evento(self.evento, AssinadorFalso())
		xml = para_xml(assinado)

		self.assertIn("<nProtIE>", xml)
		self.assertIn("<chCTe>", xml)


def _parte_gtv_padrao(nome: str = "Empresa de Valores Ltda") -> ParteGtv:
	return ParteGtv(cnpj_cpf=_CNPJ_VALIDO, uf="SP", nome=nome)


def _inf_gtv_padrao() -> InfGtv:
	return InfGtv(
		numero_documento="12345",
		identificador="AIDF-001",
		data_emissao="2026-09-02",
		digito_verificador="7",
		quantidade_carga="10",
		especies=[EspecieGtv(tipo_especie=ESPECIE_GTV_NUMERARIO, valor_especie="50000.00")],
		remetente=_parte_gtv_padrao("Remetente de Valores Ltda"),
		destinatario=_parte_gtv_padrao("Destinatário de Valores Ltda"),
	)


class TestEspecieGtv(unittest.TestCase):
	def test_tipo_valido(self):
		especie = EspecieGtv(tipo_especie=ESPECIE_GTV_NUMERARIO)
		self.assertEqual(especie.tipo_especie, ESPECIE_GTV_NUMERARIO)

	def test_tipo_invalido_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			EspecieGtv(tipo_especie="9")


class TestMontarParteGtv(unittest.TestCase):
	def test_cnpj_valido(self):
		grupo = montar_parte_gtv(_parte_gtv_padrao())

		self.assertEqual(grupo["CNPJ"], _CNPJ_VALIDO)
		self.assertNotIn("CPF", grupo)
		self.assertEqual(grupo["UF"], "SP")
		self.assertEqual(grupo["xNome"], "Empresa de Valores Ltda")

	def test_cpf_valido(self):
		grupo = montar_parte_gtv(ParteGtv(cnpj_cpf="11144477735", uf="SP", nome="Fulano de Tal"))

		self.assertEqual(grupo["CPF"], "11144477735")
		self.assertNotIn("CNPJ", grupo)

	def test_ie_opcional(self):
		grupo = montar_parte_gtv(
			ParteGtv(cnpj_cpf=_CNPJ_VALIDO, uf="SP", nome="Empresa Ltda", inscricao_estadual="123")
		)
		self.assertEqual(grupo["IE"], "123")

	def test_nome_curto_demais_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_parte_gtv(ParteGtv(cnpj_cpf=_CNPJ_VALIDO, uf="SP", nome="A"))

	def test_documento_invalido_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_parte_gtv(ParteGtv(cnpj_cpf="0", uf="SP", nome="Empresa Ltda"))


class TestInfGtv(unittest.TestCase):
	def test_sem_especie_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			InfGtv(
				numero_documento="12345",
				identificador="AIDF-001",
				data_emissao="2026-09-02",
				digito_verificador="7",
				quantidade_carga="10",
				especies=[],
				remetente=_parte_gtv_padrao(),
				destinatario=_parte_gtv_padrao(),
			)

	def test_ndv_com_mais_de_1_caractere_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			InfGtv(
				numero_documento="12345",
				identificador="AIDF-001",
				data_emissao="2026-09-02",
				digito_verificador="77",
				quantidade_carga="10",
				especies=[EspecieGtv(tipo_especie=ESPECIE_GTV_NUMERARIO)],
				remetente=_parte_gtv_padrao(),
				destinatario=_parte_gtv_padrao(),
			)


class TestMontarEventoGtvCte(unittest.TestCase):
	def setUp(self):
		self.chave = _chave_cte()
		self.evento = montar_evento_gtv_cte(
			chave_acesso=self.chave,
			guias=[_inf_gtv_padrao()],
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T17:00:00-03:00",
		)

	def test_tp_evento_e_110170(self):
		self.assertEqual(self.evento["evento"]["infEvento"]["tpEvento"], TIPO_EVENTO_GTV_CTE)
		self.assertEqual(TIPO_EVENTO_GTV_CTE, "110170")

	def test_desc_evento_usa_forma_acentuada(self):
		"""Achado real: o XSD aceita as duas grafias ('Informações'/'Informacoes') --
		este projeto sempre grava a acentuada."""
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]
		self.assertEqual(det_evento["descEvento"], "Informações da GTV")
		self.assertEqual(DESC_EVENTO_GTV, "Informações da GTV")

	def test_infgtv_e_uma_lista(self):
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]
		self.assertEqual(len(det_evento["infGTV"]), 1)

		inf_gtv = det_evento["infGTV"][0]
		self.assertEqual(inf_gtv["nDoc"], "12345")
		self.assertEqual(inf_gtv["id"], "AIDF-001")
		self.assertEqual(inf_gtv["nDV"], "7")
		self.assertNotIn("serie", inf_gtv)

	def test_multiplas_guias_no_mesmo_evento(self):
		outra = InfGtv(
			numero_documento="99999",
			identificador="AIDF-002",
			data_emissao="2026-09-02",
			digito_verificador="3",
			quantidade_carga="5",
			especies=[EspecieGtv(tipo_especie=ESPECIE_GTV_CHEQUE, valor_especie="1000.00")],
			remetente=_parte_gtv_padrao(),
			destinatario=_parte_gtv_padrao(),
			serie="1",
			placa="ABC1234",
			rntrc="12345678",
		)

		evento = montar_evento_gtv_cte(
			chave_acesso=self.chave,
			guias=[_inf_gtv_padrao(), outra],
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T17:00:00-03:00",
		)

		inf_gtv_list = evento["evento"]["infEvento"]["detEvento"]["infGTV"]
		self.assertEqual(len(inf_gtv_list), 2)
		self.assertEqual(inf_gtv_list[1]["serie"], "1")
		self.assertEqual(inf_gtv_list[1]["placa"], "ABC1234")
		self.assertEqual(inf_gtv_list[1]["RNTRC"], "12345678")

	def test_rntrc_reaproveita_validar_rntrc(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_gtv_cte(
				chave_acesso=self.chave,
				guias=[
					InfGtv(
						numero_documento="12345",
						identificador="AIDF-001",
						data_emissao="2026-09-02",
						digito_verificador="7",
						quantidade_carga="10",
						especies=[EspecieGtv(tipo_especie=ESPECIE_GTV_NUMERARIO)],
						remetente=_parte_gtv_padrao(),
						destinatario=_parte_gtv_padrao(),
						rntrc="123",
					)
				],
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T17:00:00-03:00",
			)

	def test_sem_guias_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_gtv_cte(
				chave_acesso=self.chave,
				guias=[],
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T17:00:00-03:00",
			)

	def test_documento_assinado_serializa(self):
		assinado = assinar_evento(self.evento, AssinadorFalso())
		xml = para_xml(assinado)

		self.assertIn("<infGTV>", xml)
		self.assertIn("<chCTe>", xml)


class TestMontarEventoPrestacaoDesacordoCte(unittest.TestCase):
	def setUp(self):
		self.chave = _chave_cte()
		self.evento = montar_evento_prestacao_desacordo_cte(
			chave_acesso=self.chave,
			observacao="Mercadoria entregue fora do prazo combinado com o tomador.",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T18:00:00-03:00",
		)

	def test_tp_evento_e_610110_fora_da_familia_110xxx(self):
		"""Achado real: primeiro tpEvento fora do padrão 110xxx desta frente."""
		self.assertEqual(
			self.evento["evento"]["infEvento"]["tpEvento"], TIPO_EVENTO_PRESTACAO_DESACORDO_CTE
		)
		self.assertEqual(TIPO_EVENTO_PRESTACAO_DESACORDO_CTE, "610110")
		self.assertFalse(TIPO_EVENTO_PRESTACAO_DESACORDO_CTE.startswith("110"))

	def test_ind_desacordo_oper_sempre_1(self):
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]
		self.assertEqual(det_evento["indDesacordoOper"], INDICADOR_DESACORDO_OPERACAO)
		self.assertEqual(INDICADOR_DESACORDO_OPERACAO, "1")

	def test_desc_evento_usa_forma_acentuada(self):
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]
		self.assertEqual(det_evento["descEvento"], "Prestação do Serviço em Desacordo")

	def test_observacao_curta_demais_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_prestacao_desacordo_cte(
				chave_acesso=self.chave,
				observacao="curta",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T18:00:00-03:00",
			)

	def test_observacao_longa_demais_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_prestacao_desacordo_cte(
				chave_acesso=self.chave,
				observacao="a" * 256,
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T18:00:00-03:00",
			)

	def test_documento_assinado_serializa(self):
		assinado = assinar_evento(self.evento, AssinadorFalso())
		xml = para_xml(assinado)

		self.assertIn("<indDesacordoOper>", xml)
		self.assertIn("<chCTe>", xml)


class TestMontarEventoCancelamentoPrestacaoDesacordoCte(unittest.TestCase):
	def setUp(self):
		self.chave = _chave_cte()
		self.evento = montar_evento_cancelamento_prestacao_desacordo_cte(
			chave_acesso=self.chave,
			protocolo_prestacao_desacordo="135260000000004",
			cnpj_autor=_CNPJ_VALIDO,
			data_evento="2026-09-02T19:00:00-03:00",
		)

	def test_tp_evento_e_610111(self):
		self.assertEqual(
			self.evento["evento"]["infEvento"]["tpEvento"],
			TIPO_EVENTO_CANCELAMENTO_PRESTACAO_DESACORDO_CTE,
		)
		self.assertEqual(TIPO_EVENTO_CANCELAMENTO_PRESTACAO_DESACORDO_CTE, "610111")

	def test_so_tem_nprotevprestdes_sem_nprot_do_cte(self):
		"""Achado real: diferente de evCancCECTe/evCancIECTe, este cancelamento não
		carrega nProt do CT-e -- só o protocolo do evento cancelado."""
		det_evento = self.evento["evento"]["infEvento"]["detEvento"]

		self.assertEqual(det_evento["nProtEvPrestDes"], "135260000000004")
		self.assertNotIn("nProt", det_evento)

	def test_sem_protocolo_levanta_erro(self):
		with self.assertRaises(EventoInvalido):
			montar_evento_cancelamento_prestacao_desacordo_cte(
				chave_acesso=self.chave,
				protocolo_prestacao_desacordo="",
				cnpj_autor=_CNPJ_VALIDO,
				data_evento="2026-09-02T19:00:00-03:00",
			)

	def test_documento_assinado_serializa(self):
		assinado = assinar_evento(self.evento, AssinadorFalso())
		xml = para_xml(assinado)

		self.assertIn("<nProtEvPrestDes>", xml)
		self.assertIn("<chCTe>", xml)


if __name__ == "__main__":
	unittest.main()
