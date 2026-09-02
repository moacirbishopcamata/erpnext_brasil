# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/documento/evento_cte.py` — eventos de cancelamento e carta de
correção do CT-e."""

import unittest

from erpnext_brasil.fiscal.cte import NAMESPACE_CTE
from erpnext_brasil.fiscal.documento.assinatura import MaterialAssinatura
from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.fiscal.documento.evento_cte import (
	JUSTIFICATIVA_MAXIMA_CTE,
	JUSTIFICATIVA_MINIMA_CTE,
	TIPO_EVENTO_CANCELAMENTO_CTE,
	TIPO_EVENTO_CORRECAO_CTE,
	CorrecaoCte,
	EventoInvalido,
	assinar_evento,
	montar_env_evento_cte,
	montar_evento_cancelamento_cte,
	montar_evento_correcao_cte,
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


if __name__ == "__main__":
	unittest.main()
