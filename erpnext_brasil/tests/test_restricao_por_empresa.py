# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""O que faz um site multiempresa não mostrar registro fiscal de outra `Company`.

⚠️ Estes testes existem porque a proteção **não é código deste app** — é do Frappe, e
depende de três condições que o app precisa manter. Se qualquer uma cair, a restrição para
de valer **sem erro nenhum**: as listagens simplesmente passam a mostrar mais.

`frappe/model/db_query.py` aplica User Permission automaticamente a **todo campo Link** do
DocType (`add_user_permissions`, sobre `doctype_meta.get_link_fields()`). O campo `company`
entra nessa varredura como qualquer outro — não é preciso `permission_query_conditions`.

As três condições:

1. **O DocType tem campo `company`.** Sem ele não há por onde restringir.
2. **O campo é obrigatório.** Com `apply_strict_user_permissions` desligado (o padrão), o
   Frappe deixa passar registros com o campo **vazio** — `ifnull(company,'')=''`. Campo
   obrigatório fecha esse buraco sem depender de configuração do site.
3. **O campo não tem `ignore_user_permissions`.** Essa marca desliga a restrição para
   aquele campo, e é justamente o que não se quer aqui.

Teste-âncora: `test_o_campo_company_e_obrigatorio`. É a condição que não depende de
configuração do site — as outras duas alguém teria de desligar de propósito.

Módulo de leitura: roda sem bench.
"""

import ast
import json
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

DOCTYPES = sorted(
	(caminho, json.loads(caminho.read_text(encoding="utf-8")))
	for caminho in (RAIZ / "registros_fiscais" / "doctype").glob("*/*.json")
)

PROPRIOS = [(caminho.stem, definicao) for caminho, definicao in DOCTYPES if not definicao.get("istable")]
"""Os DocTypes de nível superior deste app.

Tabela filha fica de fora: ela herda a permissão do pai, e não tem `company` própria.
"""


def _campo(definicao: dict, fieldname: str) -> dict | None:
	for campo in definicao["fields"]:
		if campo["fieldname"] == fieldname:
			return campo

	return None


class TestAsTresCondicoes(unittest.TestCase):
	def test_todo_doctype_proprio_tem_campo_company(self):
		"""Sem `company` não há por onde a User Permission restringir."""
		self.assertTrue(PROPRIOS, "nenhum DocType lido — o teste ficaria vazio")

		for nome, definicao in PROPRIOS:
			with self.subTest(doctype=nome):
				self.assertIsNotNone(_campo(definicao, "company"))

	def test_o_campo_company_e_obrigatorio(self):
		"""Teste-âncora: com `apply_strict_user_permissions` desligado — que é o padrão —
		o Frappe deixa passar registro com o campo **vazio**. Campo obrigatório fecha isso
		sem depender de configuração do site."""
		for nome, definicao in PROPRIOS:
			with self.subTest(doctype=nome):
				self.assertTrue(_campo(definicao, "company").get("reqd"))

	def test_o_campo_company_nao_ignora_user_permissions(self):
		"""`ignore_user_permissions` desliga a restrição para aquele campo."""
		for nome, definicao in PROPRIOS:
			with self.subTest(doctype=nome):
				self.assertFalse(_campo(definicao, "company").get("ignore_user_permissions"))

	def test_o_company_aponta_para_o_doctype_Company(self):
		"""A User Permission é por DocType de destino: `options` errado restringiria por
		outra coisa, ou por nada."""
		for nome, definicao in PROPRIOS:
			with self.subTest(doctype=nome):
				campo = _campo(definicao, "company")

				self.assertEqual("Link", campo["fieldtype"])
				self.assertEqual("Company", campo["options"])


class TestNenhumaLeituraContornaAPermissao(unittest.TestCase):
	"""`ignore_permissions` numa **leitura** desligaria a restrição inteira."""

	def _chamadas_de_leitura_com_ignore(self) -> list[str]:
		achadas = []

		for arquivo in sorted((RAIZ / "integracao").glob("*.py")):
			arvore = ast.parse(arquivo.read_text(encoding="utf-8"))

			for no in ast.walk(arvore):
				if not isinstance(no, ast.Call):
					continue

				nome = getattr(no.func, "attr", "")

				if nome not in ("get_all", "get_list", "get_value"):
					continue

				if any(kw.arg == "ignore_permissions" for kw in no.keywords):
					achadas.append(f"{arquivo.name}:{no.lineno} {nome}")

		return achadas

	def test_nenhuma_consulta_usa_ignore_permissions(self):
		"""Escrever com `ignore_permissions` é legítimo — gravar o registro de auditoria
		não deve depender de o usuário poder criar `Transmissao Fiscal` à mão. **Ler**, não:
		ali a marca desligaria a separação entre empresas."""
		self.assertEqual([], self._chamadas_de_leitura_com_ignore())

	def test_a_varredura_encontra_o_que_procura(self):
		"""Sem isto o teste acima passaria por vacuidade se o padrão de busca quebrasse."""
		escritas = 0

		for arquivo in sorted((RAIZ / "integracao").glob("*.py")):
			escritas += arquivo.read_text(encoding="utf-8").count("ignore_permissions=True")

		self.assertGreater(escritas, 0, "nenhum `ignore_permissions` encontrado — regex quebrou?")


if __name__ == "__main__":
	unittest.main()
