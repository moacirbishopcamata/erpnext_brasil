# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Costura entre `hooks.py`, `setup/custom_fields.py` e o que o código de integração lê.

Por que este teste existe
-------------------------------
A varredura de gaps de 2026-09-04 (ver `docs/gaps.md`) encontrou dois hooks **ligados e
inertes**:

- `chave_acesso_documento.validar_chave_acesso` lia `doc.get("br_chave_acesso")` num
  DocType onde o campo nunca foi criado — `get` devolvia `None` e a função retornava
  cedo, sem erro e sem aviso;
- `cfop_sugestao` escrevia `linha.br_cfop_sugerido` em DocTypes filhos onde o campo não
  existia — atribuir atributo não declarado num `Document` do Frappe não levanta erro, o
  valor simplesmente some no save.

Nenhum teste pegou porque **todo teste puro monta o campo por conta própria**. É o caso
clássico de suíte verde convivendo com bug real: cada peça testada sozinha, a interação
entre duas nunca.

Este teste é a interação. Ele não simula documento nenhum — lê as duas fontes de verdade
(o que o hook promete e o que a instalação cria) e confere que combinam. Roda sem bench,
porque as duas são estruturas de dados puras.

O que ele **não** substitui: teste de bench que grave e releia um documento de verdade.
Isso continua na lista de `docs/gaps.md`.
"""

import ast
import re
import unittest
from pathlib import Path

from erpnext_brasil.setup.campos import todos_os_campos
from erpnext_brasil.setup.custom_fields import (
	DOCUMENTOS_COM_APURACAO,
	DOCUMENTOS_COM_CFOP_SUGERIDO,
	DOCUMENTOS_COM_CHAVE_DE_ACESSO,
)

RAIZ = Path(__file__).resolve().parent.parent

CAMPOS = todos_os_campos()
"""A **mesma** união que a instalação aplica — não uma montada aqui.

Enquanto este arquivo montava a sua, conhecia só um dos três mapas, e reprovou os campos de
folha assim que nasceram. Um teste que constrói o seu próprio universo mede o universo dele.
"""


def _fieldnames(doctype: str) -> set[str]:
	return {campo["fieldname"] for campo in CAMPOS.get(doctype, [])}


class TestChaveDeAcesso(unittest.TestCase):
	def test_todo_doctype_validado_tem_o_campo(self):
		"""O gap 1.1: o hook rodava e não fazia nada."""
		for doctype in DOCUMENTOS_COM_CHAVE_DE_ACESSO:
			with self.subTest(doctype=doctype):
				self.assertIn("br_chave_acesso", _fieldnames(doctype))

	def test_o_hook_esta_ligado_nos_mesmos_doctypes(self):
		"""A lista de campos e a de hooks têm de descrever o mesmo conjunto."""
		hooks = (RAIZ / "hooks.py").read_text(encoding="utf-8")

		self.assertIn("chave_acesso_documento.validar_chave_acesso", hooks)

		for doctype in DOCUMENTOS_COM_CHAVE_DE_ACESSO:
			with self.subTest(doctype=doctype):
				self.assertIn(f'"{doctype}"', hooks)

	def test_a_chave_tem_quarenta_e_quatro_posicoes(self):
		campo = next(c for c in CAMPOS["Sales Invoice"] if c["fieldname"] == "br_chave_acesso")

		self.assertEqual(campo["length"], 44)


class TestCfopSugerido(unittest.TestCase):
	def test_todo_doctype_filho_escrito_tem_o_campo(self):
		"""O gap 1.2: a sugestão era calculada e descartada."""
		for doctype in DOCUMENTOS_COM_CFOP_SUGERIDO:
			with self.subTest(doctype=doctype):
				self.assertIn("br_cfop_sugerido", _fieldnames(doctype))

	def test_a_lista_cobre_os_documentos_que_o_hook_atende(self):
		"""Todo DocType pai tratado por `cfop_sugestao` tem seu filho na lista.

		Lê o mapa do próprio módulo em vez de repetir a lista aqui — repetir é como as
		duas se separam de novo.
		"""
		fonte = (RAIZ / "integracao" / "cfop_sugestao.py").read_text(encoding="utf-8")
		arvore = ast.parse(fonte)

		mapa = next(
			no
			for no in ast.walk(arvore)
			if isinstance(no, ast.Assign)
			and any(getattr(a, "id", "") == "_DOCUMENTOS_COMPRA_VENDA" for a in no.targets)
		)
		pais = {chave.value for chave in mapa.value.keys}
		pais |= {"Subcontracting Order", "Subcontracting Receipt"}

		for pai in sorted(pais):
			with self.subTest(pai=pai):
				self.assertIn(f"{pai} Item", DOCUMENTOS_COM_CFOP_SUGERIDO)

	def test_o_campo_e_somente_leitura(self):
		"""É sugestão derivada, não escolha do usuário."""
		campo = next(c for c in CAMPOS["Sales Invoice Item"] if c["fieldname"] == "br_cfop_sugerido")

		self.assertEqual(campo["read_only"], 1)
		self.assertEqual(campo["length"], 4)


class TestTodoCampoLidoExiste(unittest.TestCase):
	"""A varredura genérica: todo `br_*` lido ou escrito na integração é declarado."""

	def _declarados(self) -> set[str]:
		return {campo["fieldname"] for campos in CAMPOS.values() for campo in campos}

	def test_todo_br_lido_com_get_e_declarado(self):
		declarados = self._declarados()
		lidos: set[str] = set()

		for arquivo in (RAIZ / "integracao").glob("*.py"):
			fonte = arquivo.read_text(encoding="utf-8")
			lidos |= set(re.findall(r'\.get\(\s*"(br_[a-z_]+)"', fonte))

		self.assertTrue(lidos, "a varredura não encontrou nenhuma leitura — regex quebrou?")

		nao_declarados = sorted(lidos - declarados)

		self.assertEqual(
			nao_declarados,
			[],
			f"campos lidos pela integração e nunca criados na instalação: {nao_declarados}",
		)

	def test_todo_br_escrito_em_atributo_e_declarado(self):
		"""Atribuir atributo inexistente num `Document` não levanta erro — some no save."""
		declarados = self._declarados()
		escritos: set[str] = set()

		for arquivo in (RAIZ / "integracao").glob("*.py"):
			fonte = arquivo.read_text(encoding="utf-8")
			escritos |= set(re.findall(r"^\s*\w+\.(br_[a-z_]+)\s*=", fonte, re.M))

		self.assertTrue(escritos, "a varredura não encontrou nenhuma escrita — regex quebrou?")

		nao_declarados = sorted(escritos - declarados)

		self.assertEqual(
			nao_declarados,
			[],
			f"campos escritos pela integração e nunca criados na instalação: {nao_declarados}",
		)


class TestCamposDeApuracao(unittest.TestCase):
	"""O maior gap da varredura: 29 campos que a apuração usava e ninguém criava."""

	def test_todo_campo_de_resultado_e_declarado(self):
		"""Os campos de saída escaparam da varredura por regex — são chaves de dict,
		gravadas por `linha.set(campo, valor)`, não atribuições de atributo.

		Por isso esta checagem lê a constante do próprio módulo em vez de procurar
		padrão no texto: a lista existe, basta compará-la.
		"""
		from erpnext_brasil.integracao.mapeamento import CAMPOS_RESULTADO

		declarados = _fieldnames("Sales Invoice Item")
		faltando = sorted(set(CAMPOS_RESULTADO) - declarados)

		self.assertEqual(faltando, [], f"campos de resultado nunca criados: {faltando}")

	def test_o_cabecalho_tem_os_campos_que_a_operacao_le(self):
		esperados = {
			"br_apurar_impostos",
			"br_indicador_ie",
			"br_destinado_a_revenda",
			"br_regime_pis_cofins",
			"br_ano_competencia",
			"br_excluir_icms_pis_cofins",
		}

		for doctype in DOCUMENTOS_COM_APURACAO:
			with self.subTest(doctype=doctype):
				self.assertTrue(esperados.issubset(_fieldnames(doctype)))

	def test_o_regime_grava_o_valor_que_o_calculo_le(self):
		"""Um Select com rótulo bonito gravaria chave que o cálculo não conhece."""
		from erpnext_brasil.fiscal.impostos.pis_cofins import REGIMES_VALIDOS

		campo = next(c for c in CAMPOS["Sales Invoice"] if c["fieldname"] == "br_regime_pis_cofins")
		opcoes = {o for o in campo["options"].splitlines() if o}

		self.assertEqual(opcoes, set(REGIMES_VALIDOS))
		self.assertIn(campo["default"], REGIMES_VALIDOS)

	def test_os_campos_de_resultado_sao_somente_leitura(self):
		"""Editáveis, convidariam a corrigir o número em vez da alíquota que o produziu."""
		from erpnext_brasil.integracao.mapeamento import CAMPOS_RESULTADO

		for campo in CAMPOS["Sales Invoice Item"]:
			if campo["fieldname"] in CAMPOS_RESULTADO:
				with self.subTest(campo=campo["fieldname"]):
					self.assertEqual(campo.get("read_only"), 1)


if __name__ == "__main__":
	unittest.main()
