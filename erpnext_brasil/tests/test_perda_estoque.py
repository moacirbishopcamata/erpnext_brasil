# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Costura da apuração de perdas com o estoque do ERPNext.

`contabil/perdas.py` tinha o cálculo completo e **nenhum módulo de integração o
importava** — só uma docstring do Bloco K o citava. Esta suíte trava as duas metades da
correção: que a ponte existe, e que ela recusa o que o ERPNext aceitaria calado.

Teste-âncora: `test_recusa_sobra_de_inventario`. No `Stock Reconciliation` o sinal de
`difference_amount` é a **única** coisa que separa falta de sobra, e sinal não é
classificação fiscal. Apurar perda sobre uma sobra produziria estorno de crédito em cima de
um ganho — passivo fiscal criado do nada, sem que nada levantasse erro.

`integracao/perda_estoque.py` importa `frappe`, então a execução só existe num site: o que
se confere aqui é a forma, por AST e texto. `setup/campos_estoque.py` é puro e se importa
de verdade.

Módulo puro: roda sem bench.
"""

import ast
import unittest
from pathlib import Path

from erpnext_brasil.contabil.perdas import TIPOS_DE_PERDA, TIPOS_QUE_ESTORNAM
from erpnext_brasil.setup.campos import todos_os_campos
from erpnext_brasil.setup.campos_estoque import (
	DOCTYPES_COM_PERDA,
	OPCOES_DE_PERDA,
	get_custom_fields,
)
from erpnext_brasil.tests.ajudantes import sem_docstrings

RAIZ = Path(__file__).resolve().parent.parent

_FONTE = (RAIZ / "integracao" / "perda_estoque.py").read_text(encoding="utf-8")
_SEM_DOC = sem_docstrings(_FONTE)
_ARVORE = ast.parse(_FONTE)

_HOOKS = (RAIZ / "hooks.py").read_text(encoding="utf-8")

CAMPOS_DO_ERPNEXT_LIDOS = {
	"Stock Entry": {"purpose", "total_outgoing_value", "value_difference"},
	"Stock Reconciliation": {"difference_amount"},
}
"""Campos do ERPNext que este app lê ou usa como âncora, por DocType.

Fixados aqui de propósito: os DocTypes de estoque são do ERPNext, que não está no caminho
desta suíte. Cada nome foi lido no JSON do erpnext **v16** ao escrever o módulo —
`stock_entry.json` e `stock_reconciliation.json`. A conferência possível é que o módulo não
leia nada além desta lista.
"""

CAMPOS_ESCRITOS = {
	"br_perda_estorna_credito",
	"br_credito_estornado",
	"br_custo_total_da_perda",
}
"""Os campos que o módulo grava no documento.

⚠️ Escrever num campo não declarado **não levanta erro no Frappe**: o valor some no save.
Por isso a lista existe e é comparada com a declaração.
"""


class TestOsCamposDaPerda(unittest.TestCase):
	"""`setup/campos_estoque.py` é puro — dá para importar e medir de verdade."""

	def test_as_opcoes_vem_do_dominio(self):
		"""Digitar os tipos de novo faria a tela e o domínio divergirem no dia em que um
		tipo fosse acrescentado — e o sintoma seria um valor válido que o formulário
		recusa."""
		self.assertEqual(list(("", *TIPOS_DE_PERDA)), OPCOES_DE_PERDA.split("\n"))

	def test_a_primeira_opcao_e_vazia(self):
		"""Uma `Material Issue` costuma ser consumo. Obrigar a escolher um motivo
		transformaria toda requisição de material em declaração de sinistro."""
		self.assertEqual("", OPCOES_DE_PERDA.split("\n")[0])

	def test_os_dois_doctypes_recebem_o_mesmo_conjunto(self):
		"""Falta e baixa deliberada são documentos diferentes com a mesma consequência
		fiscal."""
		campos = get_custom_fields()

		self.assertEqual(set(DOCTYPES_COM_PERDA), set(campos))

		nomes = [{c["fieldname"] for c in campos[d]} for d in DOCTYPES_COM_PERDA]

		self.assertEqual(nomes[0], nomes[1])

	def test_todo_campo_tem_o_prefixo(self):
		for doctype, definicoes in get_custom_fields().items():
			for definicao in definicoes:
				with self.subTest(doctype=doctype, campo=definicao["fieldname"]):
					self.assertTrue(definicao["fieldname"].startswith("br_"))

	def test_a_ancora_de_cada_doctype_existe_no_erpnext(self):
		"""Âncora inexistente não levanta erro: só põe a seção no lugar errado da tela."""
		for doctype, definicoes in get_custom_fields().items():
			ancora = definicoes[0]["insert_after"]

			with self.subTest(doctype=doctype):
				self.assertIn(ancora, CAMPOS_DO_ERPNEXT_LIDOS[doctype])

	def test_os_resultados_sao_somente_leitura(self):
		"""Quem edita à mão o crédito a estornar apaga a apuração e ninguém percebe."""
		for doctype, definicoes in get_custom_fields().items():
			por_nome = {c["fieldname"]: c for c in definicoes}

			for campo in CAMPOS_ESCRITOS:
				with self.subTest(doctype=doctype, campo=campo):
					self.assertEqual(1, por_nome[campo].get("read_only"))

	def test_nao_ha_campo_para_o_valor_da_perda(self):
		"""O valor é `total_outgoing_value`/`difference_amount`. Um segundo campo criaria
		duas verdades sobre a mesma baixa — o erro já evitado no `Bank Account`."""
		nomes = {c["fieldname"] for d in get_custom_fields().values() for c in d}

		for proibido in ("br_valor_da_perda", "br_valor_baixado", "br_total_da_baixa"):
			self.assertNotIn(proibido, nomes)

	def test_os_campos_entram_na_uniao(self):
		"""Mapa fora de `MAPAS` nunca é instalado — o campo existe no código e não no site."""
		uniao = todos_os_campos()

		for doctype in DOCTYPES_COM_PERDA:
			with self.subTest(doctype=doctype):
				self.assertIn(doctype, uniao)
				self.assertIn("br_tipo_de_perda", {c["fieldname"] for c in uniao[doctype]})


class TestACosturaComOEstoque(unittest.TestCase):
	"""`integracao/perda_estoque.py` importa `frappe`: conferência por forma."""

	def test_recusa_sobra_de_inventario(self):
		"""Teste-âncora. Sobra não é perda: a mercadoria não deixou de existir, ela
		apareceu. Sem esta recusa, o estorno seria calculado sobre um ganho."""
		self.assertIn("difference_amount", _SEM_DOC)
		self.assertIn("diferenca >= ZERO", _SEM_DOC)
		self.assertIn("sobra", _FONTE.lower())

	def test_a_falta_vira_valor_positivo(self):
		"""`difference_amount` vem negativo na falta, e `apurar_perda` exige positivo."""
		self.assertIn("return -diferenca", _SEM_DOC)

	def test_recusa_finalidade_que_nao_e_baixa(self):
		"""Transferência não é perda: estornar o crédito dela criaria passivo sobre
		mercadoria que continua na empresa."""
		self.assertIn("PROPOSITO_DE_BAIXA", _SEM_DOC)
		self.assertIn('doc.get("purpose") != PROPOSITO_DE_BAIXA', _SEM_DOC)

	def test_o_proposito_e_o_do_erpnext(self):
		self.assertIn("Material Issue", _FONTE)

	def test_importa_o_modulo_de_perdas(self):
		"""A metade que faltava: sem este import, `contabil/perdas.py` continua sendo
		código correto e inalcançável."""
		importados = {
			alias.name
			for no in ast.walk(_ARVORE)
			if isinstance(no, ast.ImportFrom) and no.module == "erpnext_brasil.contabil.perdas"
			for alias in no.names
		}

		self.assertEqual({"TipoDePerda", "apurar_perda"}, importados)

	def test_o_hook_esta_ligado_nos_dois_doctypes(self):
		"""Hook ausente = validação escrita que nunca roda — o gap que este módulo paga,
		não o que ele repete."""
		for doctype in DOCTYPES_COM_PERDA:
			with self.subTest(doctype=doctype):
				self.assertIn(f'"{doctype}"', _HOOKS)

		self.assertIn(
			"erpnext_brasil.integracao.perda_estoque.apurar_perda_do_documento",
			_HOOKS,
		)

	def test_so_grava_campos_declarados(self):
		"""Gravar em campo não declarado some no save, sem erro."""
		declarados = {c["fieldname"] for d in get_custom_fields().values() for c in d}
		gravados = {
			no.attr
			for no in ast.walk(_ARVORE)
			if isinstance(no, ast.Attribute) and isinstance(no.ctx, ast.Store) and no.attr.startswith("br_")
		}

		self.assertEqual(CAMPOS_ESCRITOS, gravados)
		self.assertTrue(gravados <= declarados)

	def test_limpa_o_resultado_quando_o_tipo_sai(self):
		"""Apagar o tipo sem limpar deixaria um crédito a estornar de uma classificação que
		não existe mais — número órfão na tela."""
		self.assertIn("_limpar(doc)", _SEM_DOC)

	def test_so_le_campos_conhecidos_do_erpnext(self):
		"""Ler campo inexistente devolve `None` em silêncio — o gap de costura clássico."""
		lidos = {
			no.args[0].value
			for no in ast.walk(_ARVORE)
			if isinstance(no, ast.Call)
			and isinstance(no.func, ast.Attribute)
			and no.func.attr == "get"
			and no.args
			and isinstance(no.args[0], ast.Constant)
			and isinstance(no.args[0].value, str)
			and not no.args[0].value.startswith("br_")
		}
		conhecidos = set().union(*CAMPOS_DO_ERPNEXT_LIDOS.values())

		self.assertTrue(lidos <= conhecidos, f"campos do ERPNext não conferidos: {lidos - conhecidos}")

	def test_nao_redigita_os_tipos_de_perda(self):
		"""Uma segunda lista de tipos divergiria da do domínio."""
		for tipo in TIPOS_QUE_ESTORNAM:
			self.assertNotIn(f'"{tipo}"', _SEM_DOC)

	def test_converte_para_decimal_pela_string(self):
		"""`Decimal(0.1)` carrega o ruído binário do float; `Decimal("0.1")` não."""
		self.assertIn("Decimal(str(", _SEM_DOC)


if __name__ == "__main__":
	unittest.main()
