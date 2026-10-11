# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Todo método `@frappe.whitelist()` de `integracao/` checa permissão — ou está numa lista de exceções com motivo.

Por que existe (RT-02, RT-03 e RT-19 da revisão total): `gerar_efd` era alcançável por qualquer usuário
autenticado e gravava com `ignore_permissions=True`; as consultas do navegador de estoque usavam `get_all` e
SQL cru, que ignoram permissão. Um método novo exposto sem checagem repetiria isso em silêncio. Este teste lê
o código (`ast`), sem `frappe`, e falha quando aparece um.

A checagem é textual e direta: procura no corpo do método uma chamada de permissão conhecida. Quem delega a
checagem a um auxiliar precisa estar em `EXCECOES`, com o motivo, e o teste confere que a exceção ainda é
necessária (se o método passar a checar direto, a entrada fica velha e o teste cobra a remoção).
"""

import ast
import unittest
from pathlib import Path

INTEGRACAO = Path(__file__).resolve().parents[1] / "integracao"

CHECAGENS = (
	"check_permission",
	"has_permission",
	"only_for",
	"_permissao",
	"_exigir_permissao",
	"_exigir_leitura",
)

EXCECOES = {
	"encerrar_mdfe": "`_contexto(name, 'submit')` faz `doc.check_permission(...)` antes de qualquer ação",
	"cancelar_mdfe": "`_contexto(name, 'cancel')` faz `doc.check_permission(...)` antes de qualquer ação",
	"ler_codigo": "delega a `scan_barcode` do ERPNext, que aplica as permissões; o caminho GS1 só lê por GTIN",
	"montar_lote": "`evento_do_holerite` faz `holerite.check_permission('read')` por holerite e o `insert()` do lote respeita o DocType",
}


def _metodos_whitelisted():
	for arquivo in sorted(INTEGRACAO.glob("*.py")):
		for no in ast.parse(arquivo.read_text(encoding="utf-8")).body:
			if isinstance(no, ast.FunctionDef) and any(
				"whitelist" in ast.unparse(d) for d in no.decorator_list
			):
				yield arquivo.name, no


def _checa_direto(no: ast.FunctionDef) -> bool:
	corpo = ast.unparse(no)

	return any(token in corpo for token in CHECAGENS)


class TestWhitelistComPermissao(unittest.TestCase):
	def test_ha_metodos_whitelisted_para_vigiar(self):
		self.assertGreater(len(list(_metodos_whitelisted())), 20)

	def test_todo_metodo_exposto_checa_permissao_ou_tem_excecao_com_motivo(self):
		sem_checagem = [
			f"{arquivo}:{no.lineno} {no.name}"
			for arquivo, no in _metodos_whitelisted()
			if not _checa_direto(no) and no.name not in EXCECOES
		]

		self.assertEqual(
			sem_checagem,
			[],
			"método @frappe.whitelist() sem checagem de permissão: acrescente has_permission/check_permission "
			"ou, se a checagem mora num auxiliar, registre em EXCECOES com o motivo",
		)

	def test_as_excecoes_ainda_sao_necessarias(self):
		por_nome = {no.name: no for _, no in _metodos_whitelisted()}

		for nome in EXCECOES:
			self.assertIn(nome, por_nome, f"{nome} não é mais um método whitelisted: remova de EXCECOES")
			self.assertFalse(_checa_direto(por_nome[nome]), f"{nome} agora checa direto: remova de EXCECOES")


if __name__ == "__main__":
	unittest.main()
