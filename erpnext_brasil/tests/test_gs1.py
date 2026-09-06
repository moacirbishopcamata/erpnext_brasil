# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Leitura de etiqueta GS1, e a costura com o leitor do estoque.

Teste-âncora: `test_ai_fixo_nao_precisa_de_separador_e_variavel_precisa`. É a regra que
decide onde cada elemento termina, e errá-la **não levanta erro** — produz um GTIN com o
lote grudado, ou um lote cortado ao meio. Os dois devolvem string, e nenhum reclama; o dado
errado entra no estoque e depois na nota.

Segundo eixo: `test_gtin14_com_zeros_acha_o_ean13_do_cadastro`. O AI (01) é sempre GTIN-14
com zeros à esquerda e o `Item Barcode` guarda o EAN-13 impresso na caixa — procurar os 14
dígitos crus não acha nada, e o estoquista conclui que o item não está cadastrado quando
está.

`fiscal/gs1.py` é puro e se importa de verdade; `integracao/leitura_gs1.py` importa `frappe`
e é conferido por AST e texto.

Módulo puro: roda sem bench.
"""

import ast
import unittest
from datetime import date
from pathlib import Path

from erpnext_brasil.fiscal.gs1 import (
	AI_DE_TAMANHO_FIXO,
	AI_VARIAVEIS,
	SEPARADOR,
	EtiquetaGs1,
	Gs1Invalido,
	ler_gs1,
	parece_gs1,
)
from erpnext_brasil.tests.ajudantes import sem_comentarios_js, sem_docstrings

RAIZ = Path(__file__).resolve().parent.parent

_FONTE = (RAIZ / "integracao" / "leitura_gs1.py").read_text(encoding="utf-8")
_SEM_DOC = sem_docstrings(_FONTE)
_ARVORE = ast.parse(_FONTE)

_JS = (RAIZ / "public" / "js" / "leitura_gs1.js").read_text(encoding="utf-8")
_JS_SEM_COMENTARIO = sem_comentarios_js(_JS)

_HOOKS = (RAIZ / "hooks.py").read_text(encoding="utf-8")


class TestLeituraGs1(unittest.TestCase):
	def test_ai_fixo_nao_precisa_de_separador_e_variavel_precisa(self):
		"""Teste-âncora. `01` tem 14 posições e o próximo elemento começa logo em seguida;
		`10` vai até o FNC1. Uma etiqueta real mistura os dois na mesma cadeia."""
		etiqueta = ler_gs1("0107891234567895" + "17250630" + "10LOTE42" + SEPARADOR + "21SERIE7")

		self.assertEqual("07891234567895", etiqueta.gtin)
		self.assertEqual(date(2025, 6, 30), etiqueta.validade)
		self.assertEqual("LOTE42", etiqueta.lote)
		self.assertEqual("SERIE7", etiqueta.serie)

	def test_o_ultimo_elemento_variavel_dispensa_separador(self):
		"""Fim da cadeia também termina o elemento."""
		etiqueta = ler_gs1("010789123456789510LOTE42")

		self.assertEqual("LOTE42", etiqueta.lote)

	def test_dia_zero_vira_o_ultimo_dia_do_mes(self):
		"""O linter oficial chama-se `yymmd0`, e o `0` final é isso. Ler como dia 1
		venceria o produto trinta dias antes da hora."""
		etiqueta = ler_gs1("17250600")

		self.assertEqual(date(2025, 6, 30), etiqueta.validade)

	def test_dia_zero_em_fevereiro_respeita_o_ano_bissexto(self):
		self.assertEqual(date(2024, 2, 29), ler_gs1("17240200").validade)
		self.assertEqual(date(2025, 2, 28), ler_gs1("17250200").validade)

	def test_recusa_dia_que_nao_existe(self):
		with self.assertRaises(Gs1Invalido):
			ler_gs1("17250631")

	def test_recusa_mes_invalido(self):
		with self.assertRaises(Gs1Invalido):
			ler_gs1("17251301")

	def test_ignora_o_identificador_de_simbologia(self):
		"""`]C1` é GS1-128; deixá-lo passar faria o primeiro AI ser lido como `]C`."""
		for prefixo in ("]C1", "]d2", "]e0"):
			with self.subTest(prefixo=prefixo):
				self.assertEqual("07891234567895", ler_gs1(prefixo + "0107891234567895").gtin)

	def test_recusa_etiqueta_truncada(self):
		"""Um AI fixo com dado curto é etiqueta cortada — devolver o pedaço seria pior."""
		with self.assertRaises(Gs1Invalido):
			ler_gs1("01078912345")

	def test_recusa_separador_ausente_entre_variaveis(self):
		"""Sem o FNC1, o lote engoliria o resto da etiqueta. O máximo do dicionário é o que
		permite perceber."""
		with self.assertRaises(Gs1Invalido):
			ler_gs1("10" + "L" * 25)

	def test_recusa_ai_repetido(self):
		with self.assertRaises(Gs1Invalido):
			ler_gs1("010789123456789501078912345678957")

	def test_recusa_ai_desconhecido(self):
		"""A etiqueta pode ser válida e trazer um AI que o app não usa — melhor recusar do
		que adivinhar onde o elemento termina."""
		with self.assertRaises(Gs1Invalido):
			ler_gs1("9912345")

	def test_recusa_cadeia_vazia(self):
		for vazio in ("", "   ", None):
			with self.subTest(vazio=vazio), self.assertRaises(Gs1Invalido):
				ler_gs1(vazio)

	def test_quantidade_variavel(self):
		etiqueta = ler_gs1("01078912345678953012" + SEPARADOR)

		self.assertEqual(12, etiqueta.quantidade)

	def test_sscc_de_palete(self):
		"""Palete traz SSCC sem GTIN — exigir combinação recusaria etiqueta válida."""
		etiqueta = ler_gs1("00123456789012345675")

		self.assertEqual("123456789012345675", etiqueta.sscc)
		self.assertIsNone(etiqueta.gtin)

	def test_os_elementos_crus_ficam_disponiveis(self):
		etiqueta = ler_gs1("010789123456789510LOTE42")

		self.assertEqual({"01": "07891234567895", "10": "LOTE42"}, etiqueta.elementos)


class TestGtinComEnchimento(unittest.TestCase):
	def test_gtin14_com_zeros_acha_o_ean13_do_cadastro(self):
		"""Segundo eixo. O AI (01) é GTIN-14; o cadastro guarda o EAN-13 da caixa."""
		etiqueta = EtiquetaGs1(gtin="07891234567895")

		self.assertEqual("7891234567895", etiqueta.gtin_sem_enchimento)

	def test_gtin_sem_zeros_fica_igual(self):
		self.assertEqual("17891234567895", EtiquetaGs1(gtin="17891234567895").gtin_sem_enchimento)

	def test_sem_gtin_devolve_nada(self):
		self.assertIsNone(EtiquetaGs1().gtin_sem_enchimento)


class TestPareceGs1(unittest.TestCase):
	"""Conservador de propósito: na dúvida, deixa o caminho antigo do ERPNext funcionar."""

	def test_ean13_puro_nao_parece_gs1(self):
		"""`78` não é AI, mas `01` seria — um EAN que comece com `01` não pode ser
		confundido, e é por isso que o tamanho entra na decisão."""
		self.assertFalse(parece_gs1("7891234567895"))

	def test_gtin14_puro_nao_parece_gs1(self):
		self.assertFalse(parece_gs1("07891234567895"))

	def test_cadeia_com_separador_parece(self):
		self.assertTrue(parece_gs1("010789123456789510LOTE" + SEPARADOR))

	def test_cadeia_comecando_por_ai_parece(self):
		self.assertTrue(parece_gs1("010789123456789510LOTE42"))

	def test_vazio_nao_parece(self):
		self.assertFalse(parece_gs1(""))
		self.assertFalse(parece_gs1(None))


class TestATabelaVemDoDicionarioOficial(unittest.TestCase):
	def test_os_ai_fixos_tem_os_tamanhos_do_dicionario(self):
		"""Transcrição do GS1 Barcode Syntax Dictionary, conferida linha a linha."""
		self.assertEqual(18, AI_DE_TAMANHO_FIXO["00"])
		self.assertEqual(14, AI_DE_TAMANHO_FIXO["01"])
		self.assertEqual(14, AI_DE_TAMANHO_FIXO["02"])

		for ai_de_data in ("11", "13", "15", "17"):
			with self.subTest(ai=ai_de_data):
				self.assertEqual(6, AI_DE_TAMANHO_FIXO[ai_de_data])

	def test_lote_e_serie_sao_variaveis_de_ate_vinte(self):
		self.assertEqual(20, AI_VARIAVEIS["10"])
		self.assertEqual(20, AI_VARIAVEIS["21"])

	def test_nenhum_ai_esta_nas_duas_tabelas(self):
		"""Um AI nos dois lugares tornaria o desempate silencioso e dependente da ordem."""
		self.assertEqual(set(), set(AI_DE_TAMANHO_FIXO) & set(AI_VARIAVEIS))

	def test_o_separador_e_o_gs(self):
		"""FNC1 chega do leitor como GS, ASCII 29."""
		self.assertEqual(chr(29), SEPARADOR)


class TestACosturaComOLeitor(unittest.TestCase):
	def test_delega_ao_erpnext_em_vez_de_reimplementar(self):
		"""Reimplementar as quatro buscas do ERPNext criaria uma segunda verdade que
		envelheceria calada."""
		self.assertIn("scan_barcode", _SEM_DOC)
		self.assertIn("_delegar", _SEM_DOC)

	def test_o_metodo_e_exposto(self):
		"""Sem `@frappe.whitelist()` o JS chama e recebe erro de permissão."""
		self.assertIn("frappe.whitelist", _SEM_DOC)

	def test_procura_o_gtin_nas_duas_formas(self):
		self.assertIn("gtin_sem_enchimento", _SEM_DOC)

	def test_devolve_as_chaves_que_o_js_do_erpnext_espera(self):
		"""Contrato do `barcode_scanner.js`: nomes diferentes fariam o servidor responder e
		nada acontecer na tela."""
		for chave in ("item_code", "batch_no", "serial_no", "uom"):
			with self.subTest(chave=chave):
				self.assertIn(chave, _SEM_DOC)

	def test_a_assinatura_bate_com_a_do_erpnext(self):
		"""O JS chama pelo nome, com dois argumentos — divergir exigiria trocar o JS do
		ERPNext, e aí não seria decoração."""
		funcao = next(
			no for no in ast.walk(_ARVORE) if isinstance(no, ast.FunctionDef) and no.name == "ler_codigo"
		)

		self.assertEqual(["search_value", "ctx"], [a.arg for a in funcao.args.args])

	def test_o_js_troca_nos_dois_lugares(self):
		"""A instância mora em `frm.barcode_scanner` numa tela e em
		`frm.cscript.barcode_scanner` nas outras — procurar só num faria a leitura
		funcionar em metade delas."""
		self.assertIn("frm.barcode_scanner", _JS_SEM_COMENTARIO)
		self.assertIn("frm.cscript.barcode_scanner", _JS_SEM_COMENTARIO)

	def test_o_js_aponta_para_o_nosso_metodo(self):
		self.assertIn("erpnext_brasil.integracao.leitura_gs1.ler_codigo", _JS_SEM_COMENTARIO)

	def test_o_js_esta_ligado_nas_cinco_telas(self):
		"""JS não declarado em `doctype_js` nunca é carregado."""
		for tela in (
			"Stock Entry",
			"Stock Reconciliation",
			"Delivery Note",
			"Purchase Receipt",
			"Material Request",
		):
			with self.subTest(tela=tela):
				self.assertIn(f'"{tela}"', _HOOKS)

		self.assertIn("public/js/leitura_gs1.js", _HOOKS)


if __name__ == "__main__":
	unittest.main()
