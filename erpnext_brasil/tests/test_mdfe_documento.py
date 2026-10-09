# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A costura entre o `Shipment` e a montagem do MDF-e — tarefas 4.1 a 4.4.

`integracao/mdfe_documento.py` importa `frappe`, então a suíte pura não o executa; a montagem em si
é coberta por `test_mdfe_montagem.py`. O que **cabe** aqui é a costura, onde a classe de bug mais
cara deste projeto se esconde: o código lê um campo e a instalação nunca o criou (31 casos já foram
achados assim). Estes testes leem o fonte do mapeador e o cruzam com o que os Custom Fields
realmente declaram. O comportamento contra um `Shipment` salvo está em
`tests_bench/test_mdfe_documento.py`.

Teste-âncora: `test_todo_campo_lido_esta_declarado`. A primeira versão de qualquer mapeador novo
teria reprovado nele.
"""

import ast
import pathlib
import re
import unittest

from erpnext_brasil.setup import campos_documento, custom_fields

FONTE = pathlib.Path(__file__).resolve().parents[1] / "integracao" / "mdfe_documento.py"
EXTRACAO = FONTE.parent / "cte_extracao.py"


def _arvore(caminho: pathlib.Path = FONTE) -> ast.Module:
	return ast.parse(caminho.read_text(encoding="utf-8"))


def _campos_lidos() -> set[str]:
	"""Todo `br_*` que o mapeador menciona, com o `{prefixo}` do veículo expandido nos dois valores."""
	nomes: set[str] = set()
	arvore = _arvore()
	# Os pedaços constantes de um f-string não são campos: `f"br_placa{prefixo}_mdfe"` entra inteiro.
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
					nomes.update(texto.replace("{prefixo}", p) for p in ("", "_reboque"))
				else:
					nomes.add(texto)

	return nomes


def _declarados(doctype: str) -> set[str]:
	campos = [*campos_documento.get_custom_fields().get(doctype, [])]
	campos += custom_fields.get_custom_fields().get(doctype, [])

	return {c["fieldname"] for c in campos}


def _constante(nome: str):
	for no in _arvore().body:
		if isinstance(no, ast.Assign) and any(getattr(a, "id", "") == nome for a in no.targets):
			return ast.literal_eval(no.value)

	raise AssertionError(f"{nome} não encontrado em {FONTE.name}")


class TestCamposLidosEstaoDeclarados(unittest.TestCase):
	def test_o_mapeador_le_algum_campo(self):
		self.assertGreater(len(_campos_lidos()), 8, "o extrator de campos não achou o que devia")

	def test_todo_campo_lido_esta_declarado(self):
		declarados = (
			_declarados("Shipment")
			| _declarados("Company")
			| _declarados("Address")
			| _declarados("Delivery Note")
		)
		faltando = sorted(_campos_lidos() - declarados)

		self.assertEqual(faltando, [], f"campos lidos pelo mapeador e nunca criados: {faltando}")

	def test_os_campos_da_viagem_estao_no_shipment(self):
		esperados = {
			"br_numero_mdfe",
			"br_placa_mdfe",
			"br_tara_mdfe",
			"br_rodado_mdfe",
			"br_condutor_nome_mdfe",
			"br_condutor_cpf_mdfe",
			"br_placa_reboque_mdfe",
			"br_tara_reboque_mdfe",
		}

		self.assertEqual(sorted(esperados - _declarados("Shipment")), [])

	def test_os_campos_do_mdfe_nao_vazam_para_outros_documentos(self):
		for doctype in ("Sales Invoice", "Delivery Note", "Purchase Invoice"):
			with self.subTest(doctype=doctype):
				self.assertNotIn("br_placa_mdfe", _declarados(doctype))
				self.assertNotIn("br_numero_mdfe", _declarados(doctype))

	def test_nao_ha_campo_declarado_duas_vezes_no_shipment(self):
		nomes = [c["fieldname"] for c in campos_documento.get_custom_fields()["Shipment"]]

		self.assertEqual(sorted({n for n in nomes if nomes.count(n) > 1}), [])

	def test_cada_campo_insere_depois_de_algo_que_existe(self):
		"""`insert_after` apontando para o nada manda o campo para o fim, sem erro."""
		campos = campos_documento.get_custom_fields()["Shipment"]
		nomes = {c["fieldname"] for c in campos}
		ancora_do_core = "total_weight"

		for campo in campos:
			with self.subTest(campo=campo["fieldname"]):
				self.assertTrue(
					campo["insert_after"] in nomes or campo["insert_after"] == ancora_do_core,
					f"{campo['fieldname']} insere depois de {campo['insert_after']!r}, que não existe",
				)


class TestSelectDoRodado(unittest.TestCase):
	def test_o_select_oferece_exatamente_os_rotulos_traduziveis(self):
		campo = next(
			c for c in campos_documento.get_custom_fields()["Shipment"] if c["fieldname"] == "br_rodado_mdfe"
		)
		opcoes = {o for o in campo["options"].splitlines() if o}

		self.assertEqual(opcoes, set(campos_documento.RODADO_MDFE_POR_ROTULO))

	def test_os_codigos_sao_os_do_modulo_rodoviario(self):
		from erpnext_brasil.fiscal import mdfe_rodoviario as m

		esperado = {
			m.RODADO_TRUCK,
			m.RODADO_TOCO,
			m.RODADO_CAVALO_MECANICO,
			m.RODADO_VAN,
			m.RODADO_UTILITARIO,
			m.RODADO_OUTROS,
		}

		self.assertEqual(set(campos_documento.RODADO_MDFE_POR_ROTULO.values()), esperado)


class TestNumeracaoDoMdfe(unittest.TestCase):
	def test_o_modelo_58_usa_a_serie_do_mdfe_cadastrada_na_company(self):
		self.assertEqual(custom_fields.SERIE_POR_MODELO["58"], "br_serie_mdfe")
		self.assertIn("br_serie_mdfe", _declarados("Company"))

	def test_o_mapeador_aloca_no_modelo_58_e_grava_em_br_numero_mdfe(self):
		self.assertEqual(_constante("MODELO_MDFE"), "58")
		self.assertEqual(_constante("CAMPO_NUMERO"), "br_numero_mdfe")
		self.assertIn("br_numero_mdfe", _declarados("Shipment"))

	def test_o_mapeador_so_aloca_pela_montagem_que_valida_antes(self):
		"""Chamar `numero_do_documento` solto, antes da montagem, consumiria número numa recusa."""
		codigo = _arvore()
		chamadas = [
			n.func.id for n in ast.walk(codigo) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
		]

		self.assertIn("montar_mdfe_alocando_numero", chamadas)
		self.assertNotIn("montar_mdfe_de_dados", chamadas)

		diretas = [
			n
			for f in codigo.body
			if isinstance(f, ast.FunctionDef)
			for n in f.body
			if isinstance(n, ast.Expr | ast.Assign)
			and isinstance(getattr(n, "value", None), ast.Call)
			and getattr(n.value.func, "id", "") == "numero_do_documento"
		]

		self.assertEqual(diretas, [])

	def test_o_shipment_nao_tem_company_entao_a_empresa_e_passada(self):
		"""O `Shipment` do core não tem o campo `company`: a série sai de `pickup_company`."""
		corpo = ast.unparse(_arvore())

		self.assertIn("company=company", corpo)
		self.assertIn("pickup_company", corpo)


class TestCteExtracaoDeixaDeSerOrfao(unittest.TestCase):
	"""Tarefa 4.1: `referencias_do_shipment` ganha chamador de verdade."""

	def test_o_mapeador_chama_referencias_do_shipment_e_agrupa(self):
		chamadas = {
			n.func.id for n in ast.walk(_arvore()) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
		}

		self.assertIn("referencias_do_shipment", chamadas)
		self.assertIn("agrupar_por_municipio_descarga", chamadas)

	def test_a_recusa_da_extracao_vira_recusa_do_mdfe(self):
		"""`CteExtracaoInvalida` não pode escapar como outro tipo para quem chama o mapeador."""
		tratadores = [
			ast.unparse(n.type) for n in ast.walk(_arvore()) if isinstance(n, ast.ExceptHandler) and n.type
		]

		self.assertIn("CteExtracaoInvalida", tratadores)

	def test_dados_insuficientes_do_endereco_vira_recusa_do_mdfe(self):
		tratadores = [
			ast.unparse(n.type) for n in ast.walk(_arvore()) if isinstance(n, ast.ExceptHandler) and n.type
		]

		self.assertIn("DadosInsuficientes", tratadores)


if __name__ == "__main__":
	unittest.main()
