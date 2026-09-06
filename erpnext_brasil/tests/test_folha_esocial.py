# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Costura entre o `Salary Slip` e o S-1200.

`integracao/folha_esocial.py` importa `frappe`, então a execução só existe num site. Aqui se
confere o que sumiria em silêncio: campo lido e não declarado, dado nativo duplicado, e as
recusas que impedem um evento incompleto de ser aceito como completo.

Teste-âncora: `test_componente_sem_rubrica_recusa_a_montagem`. Pular a linha produziria um
evento com remuneração **a menos** — aceito pelo eSocial, e errado. A divergência entre a
folha e o que foi declarado só apareceria meses depois.

Módulo de leitura: roda sem bench.
"""

import ast
import unittest
from pathlib import Path

from erpnext_brasil.setup.campos_folha import get_custom_fields
from erpnext_brasil.tests.ajudantes import sem_docstrings

RAIZ = Path(__file__).resolve().parent.parent

_FONTE = (RAIZ / "integracao" / "folha_esocial.py").read_text(encoding="utf-8")
_ARVORE = ast.parse(_FONTE)
_INSTALL = (RAIZ / "setup" / "install.py").read_text(encoding="utf-8")


def _funcao(nome: str) -> ast.FunctionDef:
	for no in ast.walk(_ARVORE):
		if isinstance(no, ast.FunctionDef) and no.name == nome:
			return no

	raise AssertionError(f"{nome} não existe em folha_esocial.py")


def _constante(nome: str):
	for no in _ARVORE.body:
		if isinstance(no, ast.Assign) and any(
			isinstance(alvo, ast.Name) and alvo.id == nome for alvo in no.targets
		):
			return ast.literal_eval(no.value)

	raise AssertionError(f"{nome} não encontrado")


def _declarados(doctype: str) -> set[str]:
	return {campo["fieldname"] for campo in get_custom_fields().get(doctype, [])}


class TestCamposLidos(unittest.TestCase):
	"""Campo lido e não declarado devolve `None` — e o evento sai incompleto, sem erro."""

	def test_todo_campo_br_lido_do_empregado_esta_declarado(self):
		lidos = {campo for campo in _constante("CAMPOS_DO_EMPREGADO") if campo.startswith("br_")}

		self.assertTrue(lidos, "nenhum campo br_ lido — o teste ficaria vazio")
		self.assertEqual(set(), lidos - _declarados("Employee"))

	def test_os_campos_de_rubrica_estao_declarados(self):
		corpo = sem_docstrings(_FONTE)
		declarados = _declarados("Salary Component")

		for campo in ("br_cod_rubrica", "br_ide_tab_rubr"):
			with self.subTest(campo=campo):
				self.assertIn(campo, corpo)
				self.assertIn(campo, declarados)

	def test_os_campos_nativos_sao_lidos_e_nao_recriados(self):
		"""Um `br_data_nascimento` ao lado de `date_of_birth` produziria duas datas, e a
		divergência apareceria quando alguém corrigisse uma e não a outra."""
		lidos = set(_constante("CAMPOS_DO_EMPREGADO"))
		declarados = _declarados("Employee")

		for nativo in ("employee_name", "employee_number", "date_of_birth"):
			with self.subTest(campo=nativo):
				self.assertIn(nativo, lidos)
				self.assertNotIn(nativo, declarados)


class TestRecusas(unittest.TestCase):
	def test_componente_sem_rubrica_recusa_a_montagem(self):
		"""Teste-âncora: pular a linha produziria um evento com remuneração a menos —
		aceito pelo eSocial, e errado."""
		fonte = ast.get_source_segment(_FONTE, _funcao("itens_do_holerite"))

		self.assertIn("if not codigo:", fonte)
		self.assertIn("frappe.throw", fonte)

	def test_a_mensagem_diz_qual_componente_falta(self):
		""" "Falta código de rubrica" mandaria o usuário procurar entre dezenas."""
		fonte = ast.get_source_segment(_FONTE, _funcao("itens_do_holerite"))

		self.assertIn(".format(componente)", fonte)

	def test_holerite_sem_verba_declaravel_e_recusado(self):
		fonte = ast.get_source_segment(_FONTE, _funcao("itens_do_holerite"))

		self.assertIn("if not itens:", fonte)

	def test_cada_dado_obrigatorio_tem_recusa_propria(self):
		"""CPF, categoria e lotação são exigidos pelo evento; uma recusa genérica faria o
		usuário descobrir os três problemas um a um."""
		fonte = ast.get_source_segment(_FONTE, _funcao("evento_do_holerite"))

		for termo in ("não tem CPF", "codCateg", "lotação tributária"):
			with self.subTest(termo=termo):
				self.assertIn(termo, fonte)


class TestOQueNaoEntraNoEvento(unittest.TestCase):
	def test_componente_estatistico_e_ignorado(self):
		"""Existe só para cálculo interno do ERPNext: não representa verba paga."""
		fonte = ast.get_source_segment(_FONTE, _funcao("itens_do_holerite"))

		self.assertIn("statistical_component", fonte)
		self.assertIn("do_not_include_in_total", fonte)

	def test_ganhos_e_descontos_viram_uma_lista_so(self):
		"""`itensRemun` não separa provento de desconto — o código da rubrica é que diz o
		que cada linha é. Separá-los inventaria estrutura que o leiaute não tem."""
		fonte = ast.get_source_segment(_FONTE, _funcao("itens_do_holerite"))

		self.assertIn('holerite.get("earnings")', fonte)
		self.assertIn('holerite.get("deductions")', fonte)
		self.assertIn("+", fonte)


class TestConversaoDeValor(unittest.TestCase):
	def test_o_valor_passa_por_str_antes_do_decimal(self):
		"""`Decimal(float)` traria o erro de representação binária junto; `Decimal(str(...))`
		preserva o número que o usuário vê na tela."""
		fonte = ast.get_source_segment(_FONTE, _funcao("itens_do_holerite"))

		self.assertIn("Decimal(str(", fonte)


class TestPeriodoDeApuracao(unittest.TestCase):
	def test_o_periodo_vem_da_data_inicial(self):
		"""Um holerite que atravessa o mês pertence à competência em que **começou**; usar
		`end_date` deslocaria a folha de um mês num período que feche no dia 1º."""
		fonte = sem_docstrings(ast.get_source_segment(_FONTE, _funcao("_periodo_de_apuracao")))

		self.assertIn("start_date", fonte)
		self.assertNotIn("end_date", fonte)

	def test_o_formato_e_o_do_leiaute_mensal(self):
		"""`indApuracao=1` exige `AAAA-MM`, sete caracteres."""
		fonte = ast.get_source_segment(_FONTE, _funcao("_periodo_de_apuracao"))

		self.assertIn("[:7]", fonte)


class TestInstalacao(unittest.TestCase):
	def test_os_campos_de_folha_entram_na_uniao_que_a_instalacao_aplica(self):
		"""A união vive em `setup/campos.py`, não no `install.py`: é dado, e a suíte de
		costura precisa dele sem bench."""
		from erpnext_brasil.setup.campos import todos_os_campos

		declarados = todos_os_campos()

		self.assertIn("Employee", declarados)
		self.assertIn("Salary Component", declarados)

	def test_doctype_ausente_nao_quebra_a_instalacao(self):
		"""`Salary Component` vem do `hrms`, opcional — o bloco fiscal roda sem RH nenhum,
		e `create_custom_fields` não tolera DocType inexistente."""
		self.assertIn('frappe.db.exists("DocType", doctype)', _INSTALL)


class TestSuposicoesDeclaradas(unittest.TestCase):
	def test_o_tipo_de_inscricao_do_empregador_e_constante_nomeada(self):
		"""O leiaute admite 4 (CPF) para empregador doméstico. Assumir CNPJ é decisão, e
		decisão fica em constante com nome, não em literal no meio do código."""
		self.assertEqual(1, _constante("TIPO_INSCRICAO_CNPJ"))

	def test_o_identificador_do_demonstrativo_rastreia_o_holerite(self):
		"""É o que alguém precisa quando o eSocial rejeita: voltar do evento ao documento."""
		fonte = ast.get_source_segment(_FONTE, _funcao("evento_do_holerite"))

		self.assertIn("ide_dm_dev=holerite.name", fonte)


if __name__ == "__main__":
	unittest.main()
