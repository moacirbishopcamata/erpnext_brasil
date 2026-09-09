# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Todo DocType do ERPNext que o app toca está declarado de alguma forma.

O contato tem quatro formas, e três já se declaravam
--------------------------------------------------------------
Campo acrescentado (`setup/campos*.py`), comportamento ligado (`hooks.py`) e DocType próprio
sempre estiveram escritos. **Leitura não estava** — o app lia onze DocTypes do ERPNext sem
nada dizer, e `manufacturing` inteiro existia no projeto só por uma delas.

Teste-âncora: `test_nenhum_doctype_do_erpnext_e_tocado_sem_declaracao`. Ele varre o código,
descobre todo nome que corresponde a um DocType do ERPNext, e exige que cada um esteja em
uma das quatro formas. Uma leitura nova acrescentada sem declarar reprova aqui.

⚠️ Por que isto importa mais que as outras declarações: campo e hook são coisas **nossas**,
que mudam quando nós mudamos. Leitura é dependência de estrutura **alheia** — muda quando o
ERPNext muda, e sem esta lista nada aqui acusaria.

O teste que confere se os campos existem de verdade é o de bench
(`tests_bench/test_leituras_do_erpnext.py`); este confere se estão **declarados**. São
perguntas diferentes: um campo pode estar declarado e não existir, ou existir e não estar
declarado, e só os dois testes juntos fecham.

Módulo puro: roda sem bench.
"""

import ast
import unittest
from pathlib import Path

from erpnext_brasil.setup.campos import todos_os_campos
from erpnext_brasil.setup.leituras_do_erpnext import (
	LEITURAS,
	NOMES_USADOS_COMO_CHAVE,
	todos_os_doctypes_lidos,
)

RAIZ = Path(__file__).resolve().parent.parent

DOCTYPES_PROPRIOS = frozenset(
	p.name.replace("_", " ").title().replace("Sefaz", "Sefaz").replace("Sped", "SPED")
	for p in (RAIZ / "registros_fiscais" / "doctype").iterdir()
	if p.is_dir() and not p.name.startswith("__")
)
"""Os DocTypes que este app cria. Derivados da pasta, e não listados: uma lista à parte
divergiria no dia em que alguém criasse o sétimo."""

FRAPPE_E_HRMS = frozenset(
	{
		"Address",
		"Company",
		"Customer",
		"Supplier",
		"Item",
		"Employee",
		"Salary Component",
		"Salary Slip",
		"File",
		"User",
		"Error Log",
		"Version",
		"Custom Field",
		"DocType",
		"Account",
		"Bank",
		"Bank Account",
		"Mode of Payment",
	}
)
"""Nomes que aparecem no código e **não** são exclusivos do ERPNext, ou já são declarados
por campo/hook. Fixados aqui para que a varredura não os cobre duas vezes."""


def _nomes_citados() -> set[str]:
	"""Todo literal em maiúscula-inicial que possa ser nome de DocType, no código do app.

	Varre por AST e por SQL cru: `frappe.get_all("X")` e ``` `tabX` ``` são as duas formas
	de tocar um DocType, e conferir só uma deixaria a outra passar.
	"""
	import re

	citados: set[str] = set()
	padrao_sql = re.compile(r"`tab([A-Z][A-Za-z ]+)`")

	for caminho in sorted(RAIZ.rglob("*.py")):
		# ⚠️ `tests_bench/` fica de fora, e a distinção é o ponto.
		#
		# Os fixtures de bench criam `Fiscal Year`, `UOM`, `Price List`, `Warehouse Type` e
		# outros — dependência do **teste**, não do app. Misturá-los aqui faria o contrato
		# mentir sobre o que a produção precisa, e ainda esconderia a diferença que importa:
		# se o ERPNext renomear algo que só o fixture usa, o teste falha e avisa; se
		# renomear algo que o app lê, nada avisa. É essa segunda que esta lista existe para
		# tornar visível.
		if "__pycache__" in str(caminho) or {"tests", "tests_bench"} & set(caminho.parts):
			continue

		texto = caminho.read_text(encoding="utf-8")
		citados |= set(padrao_sql.findall(texto))

		try:
			arvore = ast.parse(texto)
		except SyntaxError:
			continue

		for no in ast.walk(arvore):
			chamada = (
				isinstance(no, ast.Call)
				and isinstance(no.func, ast.Attribute)
				and no.func.attr
				in (
					"get_all",
					"get_list",
					"get_value",
					"get_cached_value",
					"get_doc",
					"get_cached_doc",
					"exists",
				)
				and no.args
				and isinstance(no.args[0], ast.Constant)
				and isinstance(no.args[0].value, str)
			)

			if chamada:
				citados.add(no.args[0].value)

	return citados


class TestAsQuatroFormasDeContato(unittest.TestCase):
	def test_nenhum_doctype_do_erpnext_e_tocado_sem_declaracao(self):
		"""Teste-âncora. Leitura nova sem declarar reprova aqui."""
		declarados = (
			set(todos_os_campos()) | set(todos_os_doctypes_lidos()) | DOCTYPES_PROPRIOS | FRAPPE_E_HRMS
		)
		hooks = (RAIZ / "hooks.py").read_text(encoding="utf-8")

		nao_declarados = sorted(
			nome
			for nome in _nomes_citados()
			if " " in nome or nome[0].isupper()
			if nome not in declarados and f'"{nome}"' not in hooks
		)

		self.assertEqual(
			[],
			nao_declarados,
			f"DocTypes tocados sem declaração: {nao_declarados}. "
			"Acrescente em `setup/leituras_do_erpnext.py` se for leitura.",
		)

	def test_a_varredura_encontra_alguma_coisa(self):
		"""Se `_nomes_citados` parasse de casar, o teste acima passaria sem conferir nada —
		varrer zero nomes nunca encontra pendência.

		Não é hipótese: a varredura escrita à mão que precedeu este teste achou onze
		DocTypes lidos, e este achou treze."""
		self.assertGreater(len(_nomes_citados()), 20)


class TestORegistroDeLeituras(unittest.TestCase):
	def test_os_dois_conjuntos_nao_se_sobrepoem(self):
		"""`LEITURAS` e `NOMES_USADOS_COMO_CHAVE` respondem perguntas diferentes; um nome nos
		dois faria a conferência de campos rodar sobre um DocType do qual nada se lê."""
		self.assertEqual(frozenset(), frozenset(LEITURAS) & NOMES_USADOS_COMO_CHAVE)

	def test_nenhum_lido_tem_campo_ou_hook_nosso(self):
		"""Por definição, `LEITURAS` é o que **não** se declara de outra forma. Um DocType
		que ganhasse campo nosso deveria sair daqui — senão a lista mente sobre o motivo de
		ele estar no app."""
		hooks = (RAIZ / "hooks.py").read_text(encoding="utf-8")
		com_campo = set(todos_os_campos())

		for doctype in todos_os_doctypes_lidos():
			with self.subTest(doctype=doctype):
				self.assertNotIn(doctype, com_campo)
				self.assertNotIn(f'"{doctype}"', hooks)

	def test_o_alias_nao_entra_no_lugar_do_campo(self):
		"""`Item Barcode` é lido com `parent as item_code`. O campo real é `parent`;
		declarar o alias esconderia a dependência verdadeira."""
		self.assertIn("parent", LEITURAS["Item Barcode"])
		self.assertNotIn("item_code", LEITURAS["Item Barcode"])

	def test_os_dois_que_a_varredura_manual_perdeu_estao_declarados(self):
		"""`Dynamic Link` e `Has Role` escaparam da varredura ad-hoc porque ela procurava
		numa lista de nomes que ela mesma montou. São leituras de verdade: a primeira liga
		`Address` à parte (e a UF decide CFOP e alíquota), a segunda diz a quem enviar o
		alerta de certificado."""
		self.assertIn("Dynamic Link", LEITURAS)
		self.assertIn("Has Role", LEITURAS)

	def test_os_dois_doctypes_da_efd_estao_declarados(self):
		"""São os que alimentam arquivo entregue ao Fisco — a maior consequência de um
		renome silencioso do ERPNext."""
		self.assertIn("Work Order", LEITURAS)
		self.assertIn("Stock Ledger Entry", LEITURAS)


if __name__ == "__main__":
	unittest.main()
