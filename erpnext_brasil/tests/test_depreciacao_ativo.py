# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Costura da depreciação fiscal com o `Asset` do ERPNext.

`integracao/depreciacao_ativo.py` importa `frappe`, então a execução só existe num site. O
que se confere aqui é o que ficaria inerte ou divergente em silêncio:

- **o hook ligado** — sem ele a validação existe e nunca roda, que é o gap que este módulo
  foi escrito para pagar, não para repetir;
- **os números não duplicados** — os coeficientes de turno vêm de `COEFICIENTE_POR_TURNOS`,
  e digitá-los de novo aqui seria como ter duas tabelas de UF divergindo;
- **os campos gravados** — nome errado numa linha de `Asset Finance Book` não levanta erro
  no Frappe: some no save.

Teste-âncora: `test_o_metodo_exigido_e_o_linear`. *Written Down Value* e *Double Declining
Balance* são configurações **válidas** no ERPNext, e a primeira quota que produzem é igual
à correta — a divergência só aparece do segundo período em diante.

Módulo puro de leitura: roda sem bench.
"""

import ast
import unittest
from pathlib import Path

from erpnext_brasil.contabil.depreciacao import COEFICIENTE_POR_TURNOS, TAXAS_ANUAIS

RAIZ = Path(__file__).resolve().parent.parent

_FONTE = (RAIZ / "integracao" / "depreciacao_ativo.py").read_text(encoding="utf-8")
_ARVORE = ast.parse(_FONTE)

_HOOKS = (RAIZ / "hooks.py").read_text(encoding="utf-8")
_INSTALL = (RAIZ / "setup" / "install.py").read_text(encoding="utf-8")

CAMPOS_DO_LIVRO = {
	"depreciation_method",
	"rate_of_depreciation",
	"frequency_of_depreciation",
	"total_number_of_depreciations",
	"depreciation_start_date",
	"daily_prorata_based",
	"finance_book",
}
"""Os campos de `Asset Finance Book` que este app escreve.

Fixados aqui de propósito: o `Asset Finance Book` é do ERPNext, que não está no caminho
desta suíte, então a conferência possível é que o módulo **não escreva nada além** desta
lista — cada nome dela foi lido no `asset_finance_book.json` ao escrever o módulo.
"""


def _constante(nome: str):
	"""Uma constante de módulo, lida por AST — `depreciacao_ativo` importa `frappe`."""
	for no in _ARVORE.body:
		if isinstance(no, ast.Assign) and any(
			isinstance(alvo, ast.Name) and alvo.id == nome for alvo in no.targets
		):
			return ast.literal_eval(no.value)

	raise AssertionError(f"{nome} não encontrado em depreciacao_ativo.py")


def _corpo_executavel() -> str:
	"""O fonte sem docstrings, para asserções de ausência.

	Sem isto, a docstring que explica por que **não** se usa `purchase_date` reprovaria o
	próprio teste que a defende — armadilha já vivida duas vezes neste projeto.
	"""
	proibidas = set()

	for no in ast.walk(_ARVORE):
		if (
			isinstance(no, ast.Expr)
			and isinstance(no.value, ast.Constant)
			and isinstance(no.value.value, str)
		):
			proibidas.update(range(no.lineno, (no.end_lineno or no.lineno) + 1))

	return "\n".join(
		linha for numero, linha in enumerate(_FONTE.splitlines(), start=1) if numero not in proibidas
	)


def _funcao(nome: str) -> ast.FunctionDef:
	for no in ast.walk(_ARVORE):
		if isinstance(no, ast.FunctionDef) and no.name == nome:
			return no

	raise AssertionError(f"{nome} não existe em depreciacao_ativo.py")


def _atribuicoes_em(nome_funcao: str) -> set[str]:
	"""Os atributos que a função grava, como `linha.<campo> = ...`."""
	gravados = set()

	for no in ast.walk(_funcao(nome_funcao)):
		if isinstance(no, ast.Assign):
			for alvo in no.targets:
				if isinstance(alvo, ast.Attribute):
					gravados.add(alvo.attr)

	return gravados


class TestOHookEstaLigado(unittest.TestCase):
	"""Sem isto a validação existe e nunca roda — o gap que este módulo paga."""

	def test_o_asset_tem_o_hook_de_validacao(self):
		self.assertIn('"Asset"', _HOOKS)
		self.assertIn("depreciacao_ativo.validar_livro_fiscal", _HOOKS)

	def test_a_funcao_do_hook_existe_com_a_assinatura_do_frappe(self):
		"""`doc_events` chama com `(doc, method)`; faltar o segundo quebra no primeiro save."""
		parametros = [a.arg for a in _funcao("validar_livro_fiscal").args.args]

		self.assertEqual(["doc", "method"], parametros)

	def test_a_instalacao_cria_o_livro_e_os_turnos(self):
		"""`Finance Book` e `Asset Shift Factor` não nascem sozinhos: sem criá-los, a
		linha fiscal não tem onde se apoiar."""
		self.assertIn("criar_depreciacao_fiscal", _INSTALL)
		self.assertIn("instalar_livro_fiscal", _INSTALL)
		self.assertIn("instalar_turnos", _INSTALL)

	def test_a_instalacao_roda_no_install_e_no_migrate(self):
		"""Só no `after_install` deixaria de fora todo site já existente."""
		# `count` cru pegaria também a linha do `def`; o que interessa são as chamadas.
		chamadas = [
			linha.strip() for linha in _INSTALL.splitlines() if linha.strip() == "criar_depreciacao_fiscal()"
		]

		self.assertEqual(2, len(chamadas))


class TestNumerosNaoDuplicados(unittest.TestCase):
	def test_os_fatores_de_turno_vem_do_modulo_puro(self):
		"""Digitar 1.5 num segundo lugar é como ter duas tabelas de UF divergindo.

		A conferência é do **import**: o módulo tem de buscar os coeficientes em
		`contabil.depreciacao`, não redefini-los.
		"""
		importados = {
			alias.name
			for no in ast.walk(_ARVORE)
			if isinstance(no, ast.ImportFrom) and no.module == "erpnext_brasil.contabil.depreciacao"
			for alias in no.names
		}

		self.assertIn("COEFICIENTE_POR_TURNOS", importados)
		self.assertIn("TAXAS_ANUAIS", importados)

	def test_os_turnos_instalados_sao_os_tres_da_lei(self):
		self.assertEqual(set(COEFICIENTE_POR_TURNOS), set(_constante("TURNOS_POR_NOME").values()))

	def test_nenhum_coeficiente_foi_reescrito_no_fonte(self):
		"""Uma busca literal: `1.5` aparecendo aqui seria a duplicação voltando."""
		corpo = _corpo_executavel()

		for numero in ("1.5", "2.0"):
			with self.subTest(numero=numero):
				self.assertNotIn(numero, corpo)


class TestConfiguracaoExigida(unittest.TestCase):
	def test_o_metodo_exigido_e_o_linear(self):
		"""Teste-âncora: `Written Down Value` aplica a taxa sobre o saldo residual, e o
		art. 319 manda aplicá-la sobre o custo de aquisição. A primeira quota é igual nos
		dois — a divergência só aparece do segundo período em diante."""
		self.assertEqual("Straight Line", _constante("METODO_EXIGIDO"))

	def test_o_rateio_diario_e_sempre_desligado(self):
		"""Art. 319, § 2º dispensa o ajuste no curso do mês; ratear por dias deduz a
		menos, e a diferença atravessa a vida inteira do bem."""
		self.assertIn("linha.daily_prorata_based = 0", _FONTE)

	def test_a_validacao_recusa_os_dois_desvios(self):
		fonte_da_validacao = ast.get_source_segment(_FONTE, _funcao("validar_livro_fiscal"))

		self.assertIn("depreciation_method", fonte_da_validacao)
		self.assertIn("daily_prorata_based", fonte_da_validacao)

	def test_a_validacao_falha_alto_e_nao_avisa(self):
		"""Um aviso amarelo sobre método de depreciação seria clicado sem ler."""
		fonte_da_validacao = ast.get_source_segment(_FONTE, _funcao("validar_livro_fiscal"))

		self.assertIn("frappe.throw", fonte_da_validacao)
		self.assertNotIn("msgprint", fonte_da_validacao)

	def test_a_validacao_ignora_os_demais_livros(self):
		"""O método contábil pode legitimamente ser outro — o livro do contador não é
		deste app."""
		fonte_da_validacao = ast.get_source_segment(_FONTE, _funcao("validar_livro_fiscal"))

		self.assertIn("!= LIVRO_FISCAL", fonte_da_validacao)


class TestCamposEscritos(unittest.TestCase):
	def test_nao_escreve_campo_fora_do_asset_finance_book(self):
		"""Nome errado numa linha filha não levanta erro no Frappe: some no save."""
		gravados = _atribuicoes_em("aplicar_taxa_fiscal")

		self.assertTrue(gravados, "nenhuma atribuição lida — o teste ficaria vazio")
		self.assertEqual(set(), gravados - CAMPOS_DO_LIVRO)

	def test_a_data_de_inicio_vem_de_disponibilidade_e_nao_de_compra(self):
		"""Art. 317, § 2º: deprecia-se a partir de quando o bem é posto em serviço.
		Comprar não é usar, e a diferença é dedução tomada antes da hora."""
		corpo = _corpo_executavel()

		self.assertIn("available_for_use_date", corpo)
		self.assertNotIn("purchase_date", corpo)

	def test_a_permissao_e_conferida_antes_de_gravar(self):
		fonte = ast.get_source_segment(_FONTE, _funcao("aplicar_taxa_fiscal"))

		self.assertLess(fonte.index("check_permission"), fonte.index("doc.save()"))


class TestEspecies(unittest.TestCase):
	def test_a_especie_desconhecida_falha_alto_e_lista_as_conhecidas(self):
		"""Uma mensagem que só diz "espécie inválida" manda o usuário adivinhar."""
		fonte = ast.get_source_segment(_FONTE, _funcao("aplicar_taxa_fiscal"))

		self.assertIn("frappe.throw", fonte)
		self.assertIn("sorted(TAXAS_ANUAIS)", fonte)

	def test_a_taxa_e_o_prazo_saem_da_mesma_tupla(self):
		"""Ler taxa de um lugar e vida útil de outro os deixaria divergir."""
		self.assertIn("taxa, vida_util_anos = taxa_e_vida", _FONTE)

	def test_o_nucleo_de_especies_nao_esta_vazio(self):
		self.assertGreater(len(TAXAS_ANUAIS), 5)


class TestIdempotencia(unittest.TestCase):
	"""`after_migrate` roda a cada atualização: criar de novo, ou sobrescrever ajuste de
	quem administra o site, seriam os dois erros possíveis."""

	def test_a_criacao_confere_a_existencia_antes(self):
		for nome in ("instalar_turnos", "instalar_livro_fiscal"):
			with self.subTest(funcao=nome):
				fonte = ast.get_source_segment(_FONTE, _funcao(nome))

				self.assertIn("frappe.db.exists", fonte)

	def test_a_instalacao_nao_sobrescreve_o_que_ja_existe(self):
		"""Reescrever um fator ajustado a cada `migrate` é silêncio, não correção."""
		fonte = ast.get_source_segment(_FONTE, _funcao("instalar_turnos"))

		self.assertIn("continue", fonte)
		self.assertNotIn("save()", fonte)


if __name__ == "__main__":
	unittest.main()
