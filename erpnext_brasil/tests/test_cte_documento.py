# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A costura entre o cadastro e a montagem do CT-e.

`integracao/cte_documento.py` importa `frappe`, então a suíte pura não o executa — a montagem em
si é coberta por `test_cte_montagem.py`. O que **cabe** aqui é a costura, que é onde a classe de
bug mais cara deste projeto se esconde: o código lê um campo e a instalação nunca o criou (31
casos já foram achados assim). Estes testes leem o fonte do mapeador e o cruzam com o que os
Custom Fields realmente declaram.

Também travam as tabelas de tradução rótulo → código: o Select guarda o texto que o usuário vê, o
leiaute espera outro, e uma opção nova sem tradução só apareceria na emissão.
"""

import ast
import pathlib
import re
import unittest

from erpnext_brasil.fiscal.cte import MODAL_RODOVIARIO
from erpnext_brasil.setup import campos_documento, custom_fields

FONTE = pathlib.Path(__file__).resolve().parents[1] / "integracao" / "cte_documento.py"


def _campos_lidos() -> set[str]:
	"""Todo `br_*` que o mapeador menciona, com `{prefixo}` expandido nos dois valores reais."""
	arvore = ast.parse(FONTE.read_text(encoding="utf-8"))
	nomes: set[str] = set()
	# Os pedaços constantes de um f-string não são campos: `f"br_uf_{x}"` já entra inteiro.
	pedacos = {id(p) for no in ast.walk(arvore) if isinstance(no, ast.JoinedStr) for p in no.values}

	for no in ast.walk(arvore):
		if id(no) in pedacos:
			continue

		if isinstance(no, ast.Constant) and isinstance(no.value, str):
			textos = [no.value]
		elif isinstance(no, ast.JoinedStr):
			textos = ["".join(p.value if isinstance(p, ast.Constant) else "{prefixo}" for p in no.values)]
		else:
			continue

		for texto in textos:
			if re.fullmatch(r"br_[a-z_{}]+", texto):
				if "{prefixo}" in texto:
					nomes.update(texto.replace("{prefixo}", p) for p in ("inicio", "fim"))
				else:
					nomes.add(texto)

	return nomes


def _declarados(doctype: str) -> set[str]:
	campos = [*campos_documento.get_custom_fields().get(doctype, [])]
	campos += custom_fields.get_custom_fields().get(doctype, [])

	return {c["fieldname"] for c in campos}


def _opcoes(select: str) -> set[str]:
	return {o for o in select.splitlines() if o}


class TestCamposLidosEstaoDeclarados(unittest.TestCase):
	"""O teste que a primeira versão do mapeador teria reprovado: campo lido e nunca criado."""

	def test_o_mapeador_le_algum_campo(self):
		self.assertGreater(len(_campos_lidos()), 15, "o extrator de campos não achou o que devia")

	def test_todo_campo_lido_esta_declarado_em_algum_doctype_do_cte(self):
		lidos = _campos_lidos()
		declarados = _declarados("Sales Invoice") | _declarados("Company") | _declarados("Customer")
		faltando = sorted(lidos - declarados)

		self.assertEqual(faltando, [], f"campos lidos pelo mapeador e nunca criados: {faltando}")

	def test_os_campos_novos_do_cte_estao_na_fatura_de_venda(self):
		esperados = {
			"br_tomador_cte",
			"br_remetente_cte",
			"br_destinatario_cte",
			"br_produto_predominante",
			"br_valor_carga",
			"br_quantidade_carga",
			"br_unidade_carga",
			"br_tipo_medida_carga",
			"br_cst_icms_cte",
			"br_aliquota_icms_cte",
			"br_reducao_base_icms_cte",
			"br_numero_cte",
			"br_natureza_transporte",
		}

		self.assertEqual(sorted(esperados - _declarados("Sales Invoice")), [])

	def test_os_campos_de_cte_nao_vazam_para_outros_documentos(self):
		for doctype in ("Delivery Note", "Purchase Invoice", "Purchase Receipt", "POS Invoice"):
			with self.subTest(doctype=doctype):
				self.assertNotIn("br_cst_icms_cte", _declarados(doctype))
				self.assertNotIn("br_secao_transporte", _declarados(doctype))

	def test_nao_ha_campo_declarado_duas_vezes_na_fatura(self):
		nomes = [c["fieldname"] for c in campos_documento.get_custom_fields()["Sales Invoice"]]
		repetidos = sorted({n for n in nomes if nomes.count(n) > 1})

		self.assertEqual(repetidos, [])


class TestTraducaoDosRotulos(unittest.TestCase):
	def _confere(self, select: str, tabela: dict):
		self.assertEqual(sorted(_opcoes(select) ^ set(tabela)), [], "opções do Select e tabela divergem")

	def test_modal(self):
		self._confere(campos_documento.OPCOES_MODAL_CTE, campos_documento.MODAL_CTE_POR_ROTULO)

	def test_o_rodoviario_traduz_para_o_codigo_do_leiaute(self):
		self.assertEqual(campos_documento.MODAL_CTE_POR_ROTULO["Rodoviário"], MODAL_RODOVIARIO)

	def test_tipo_de_servico(self):
		self._confere(campos_documento.OPCOES_TIPO_SERVICO_CTE, campos_documento.TIPO_SERVICO_CTE_POR_ROTULO)

	def test_tomador(self):
		self._confere(campos_documento.OPCOES_TOMADOR_CTE, campos_documento.TOMADOR_CTE_POR_ROTULO)

	def test_unidade_da_carga(self):
		self._confere(campos_documento.OPCOES_UNIDADE_CARGA, campos_documento.UNIDADE_CARGA_POR_ROTULO)

	def test_cst_do_icms_so_oferece_o_que_a_montagem_sabe_montar(self):
		from erpnext_brasil.fiscal.cte_montagem import CST_COM_IMPOSTO, CST_ISENCAO, CST_SIMPLES

		suportados = CST_COM_IMPOSTO | CST_ISENCAO | {CST_SIMPLES}

		self.assertEqual(sorted(_opcoes(campos_documento.OPCOES_CST_ICMS_CTE) ^ suportados), [])

	def test_as_traducoes_usam_o_dominio_do_leiaute(self):
		self.assertEqual(set(campos_documento.TOMADOR_CTE_POR_ROTULO.values()), {"0", "3", "4"})
		self.assertEqual(
			set(campos_documento.UNIDADE_CARGA_POR_ROTULO.values()), {"00", "01", "02", "03", "04", "05"}
		)
		self.assertEqual(
			set(campos_documento.TIPO_SERVICO_CTE_POR_ROTULO.values()), {"0", "1", "2", "3", "4"}
		)


if __name__ == "__main__":
	unittest.main()
