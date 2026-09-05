# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Costura do cancelamento e da carta de correção — o que dá para travar sem bench.

`integracao/eventos_nfe.py` importa `frappe`, então a execução só existe num site real.
O que **pode** ser conferido aqui é justamente o que some em silêncio num site:

- **campo inventado no dicionário de criação** — o Frappe descarta no save, sem erro, e o
  registro nasce incompleto (a família dos 31 campos de `docs/gaps.md`);
- **valor fora do `Select`** — mesmo destino: o registro fica sem tipo ou sem situação, e
  ninguém descobre até procurar um cancelamento que não está lá;
- **ordem entre gravar e falhar** — se o `throw` viesse antes do `_registrar`, a rejeição
  da SEFAZ não deixaria rastro nenhum, que é exatamente o silêncio que `emissao_nfe` foi
  escrito para não repetir.

Teste-âncora: `test_o_registro_e_gravado_antes_do_throw`. Ele não olha valor nenhum —
olha a **ordem**, que é a parte que um teste de retorno jamais pegaria.
"""

import ast
import json
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

_CAMINHO = RAIZ / "integracao" / "eventos_nfe.py"
_FONTE = _CAMINHO.read_text(encoding="utf-8")
_ARVORE = ast.parse(_FONTE)

_DOCTYPE = RAIZ / "registros_fiscais" / "doctype" / "transmissao_fiscal" / "transmissao_fiscal.json"
_DEFINICAO = json.loads(_DOCTYPE.read_text(encoding="utf-8"))

METODOS_EXPOSTOS = ("cancelar_nfe", "enviar_carta_correcao")


def _funcao(nome: str) -> ast.FunctionDef:
	for no in _ARVORE.body:
		if isinstance(no, ast.FunctionDef) and no.name == nome:
			return no

	raise AssertionError(f"{nome} não existe em eventos_nfe.py")


def _opcoes(campo: str) -> set[str]:
	definicao = next(c for c in _DEFINICAO["fields"] if c["fieldname"] == campo)

	return {o for o in definicao["options"].splitlines() if o}


def _campos_declarados() -> set[str]:
	return {c["fieldname"] for c in _DEFINICAO["fields"]}


def _dicionario_gravado() -> ast.Dict:
	"""O literal passado a `frappe.get_doc` dentro de `_registrar`."""
	for no in ast.walk(_funcao("_registrar")):
		if isinstance(no, ast.Call) and isinstance(no.args and no.args[0], ast.Dict):
			return no.args[0]

	raise AssertionError("_registrar não passa um dicionário literal a frappe.get_doc")


def _rotulos_de_ambiente() -> set[str]:
	"""Os valores de `AMBIENTE_POR_CHAVE`, lidos do fonte de `emissao_nfe`."""
	fonte = (RAIZ / "integracao" / "emissao_nfe.py").read_text(encoding="utf-8")

	for no in ast.walk(ast.parse(fonte)):
		if isinstance(no, ast.Assign) and any(
			isinstance(alvo, ast.Name) and alvo.id == "AMBIENTE_POR_CHAVE" for alvo in no.targets
		):
			return {v.value for v in no.value.values if isinstance(v, ast.Constant)}

	raise AssertionError("AMBIENTE_POR_CHAVE não encontrado em emissao_nfe.py")


def _tem_decorador_whitelist(funcao: ast.FunctionDef) -> bool:
	for decorador in funcao.decorator_list:
		alvo = decorador.func if isinstance(decorador, ast.Call) else decorador

		if isinstance(alvo, ast.Attribute) and alvo.attr == "whitelist":
			return True

	return False


class TestCamposGravados(unittest.TestCase):
	"""Campo que o DocType não declara é descartado no save, sem erro."""

	def test_todo_campo_gravado_existe_no_doctype(self):
		declarados = _campos_declarados() | {"doctype"}
		gravados = {
			chave.value
			for chave in _dicionario_gravado().keys
			if isinstance(chave, ast.Constant) and isinstance(chave.value, str)
		}

		self.assertTrue(gravados, "nenhum campo lido — o teste ficaria verde por vazio")
		self.assertEqual(set(), gravados - declarados)

	def test_o_doctype_gravado_e_transmissao_fiscal(self):
		dicionario = _dicionario_gravado()
		valores = dict(
			zip(
				[c.value for c in dicionario.keys if isinstance(c, ast.Constant)],
				dicionario.values,
				strict=False,
			)
		)

		self.assertEqual("Transmissao Fiscal", valores["doctype"].value)

	def test_todo_campo_obrigatorio_do_doctype_e_gravado(self):
		"""Faltar um `reqd` só aparece no primeiro cancelamento real, como erro de save."""
		gravados = {chave.value for chave in _dicionario_gravado().keys if isinstance(chave, ast.Constant)}
		obrigatorios = {
			c["fieldname"]
			for c in _DEFINICAO["fields"]
			if c.get("reqd") and c["fieldname"] != "naming_series"
		}

		self.assertEqual(set(), obrigatorios - gravados)


class TestDominios(unittest.TestCase):
	"""Valor fora do `Select` não levanta erro: some, e o registro fica sem o campo."""

	def test_os_tipos_de_evento_existem_no_doctype(self):
		from erpnext_brasil.fiscal.documento.transmissao_registro import (
			TIPO_CANCELAMENTO,
			TIPO_CARTA_DE_CORRECAO,
		)

		opcoes = _opcoes("tipo")

		self.assertIn(TIPO_CANCELAMENTO, opcoes)
		self.assertIn(TIPO_CARTA_DE_CORRECAO, opcoes)

	def test_as_situacoes_usadas_existem_no_doctype(self):
		from erpnext_brasil.fiscal.documento.transmissao_registro import (
			SITUACAO_AUTORIZADO,
			SITUACAO_CANCELADO,
			SITUACAO_REJEITADO,
		)

		opcoes = _opcoes("situacao")

		for situacao in (SITUACAO_AUTORIZADO, SITUACAO_CANCELADO, SITUACAO_REJEITADO):
			self.assertIn(situacao, opcoes)

	def test_os_rotulos_de_ambiente_existem_no_doctype(self):
		"""`AMBIENTE_POR_CHAVE` traduz a chave interna para o rótulo do `Select`.

		Lido por AST porque `emissao_nfe` importa `frappe`: esta suíte roda sem bench.
		"""
		self.assertEqual(set(), _rotulos_de_ambiente() - _opcoes("ambiente"))


class TestOrdemDosEfeitos(unittest.TestCase):
	"""A parte que um teste de retorno jamais pegaria."""

	def _linhas(self, funcao: ast.FunctionDef, alvo: str) -> list[int]:
		achadas = []

		for no in ast.walk(funcao):
			if isinstance(no, ast.Call):
				chamado = no.func
				nome = chamado.id if isinstance(chamado, ast.Name) else getattr(chamado, "attr", "")

				if nome == alvo:
					achadas.append(no.lineno)

		if not achadas:
			raise AssertionError(f"{funcao.name} não chama {alvo}")

		return sorted(achadas)

	def _posicao(self, funcao: ast.FunctionDef, alvo: str) -> int:
		return self._linhas(funcao, alvo)[0]

	def test_o_registro_e_gravado_antes_do_throw(self):
		"""Rejeição da SEFAZ que não deixa rastro obriga o usuário a adivinhar."""
		for nome in METODOS_EXPOSTOS:
			with self.subTest(metodo=nome):
				funcao = _funcao(nome)

				# O **último** `throw`: o primeiro de `cancelar_nfe` é a recusa por
				# protocolo ausente, que precede a transmissão de propósito — ali ainda
				# não houve resposta da SEFAZ, logo não há o que registrar.
				self.assertLess(
					self._posicao(funcao, "_registrar"),
					self._linhas(funcao, "throw")[-1],
				)

	def test_a_permissao_e_conferida_antes_de_transmitir(self):
		"""Transmitir para a SEFAZ antes de checar permissão é irreversível."""
		for nome in METODOS_EXPOSTOS:
			with self.subTest(metodo=nome):
				funcao = _funcao(nome)

				self.assertLess(
					self._posicao(funcao, "check_permission"),
					self._posicao(funcao, "_transporte"),
				)


class TestSuperficieExposta(unittest.TestCase):
	def test_os_dois_metodos_sao_whitelisted(self):
		"""Sem o decorador o método existe e continua inalcançável — o gap original."""
		for nome in METODOS_EXPOSTOS:
			with self.subTest(metodo=nome):
				self.assertTrue(_tem_decorador_whitelist(_funcao(nome)))

	def test_o_transporte_nao_monta_contexto_sefaz(self):
		"""`contexto_sefaz.py` reserva a construção ao `TransporteSefaz`: montá-lo fora
		duplica o ciclo de vida dos PEM e vaza chave privada em disco quando falha."""
		self.assertNotIn("ContextoSefaz(", _FONTE)

	def test_nao_importa_funcao_privada_de_outro_modulo(self):
		"""UF e CNPJ vêm da chave de acesso; puxar o `_emitente` de `nfe_documento`
		reintroduziria a segunda leitura do cadastro que a chave existe para evitar."""
		for no in ast.walk(_ARVORE):
			if not isinstance(no, ast.ImportFrom) or not (no.module or "").startswith("erpnext_brasil"):
				continue

			for alias in no.names:
				self.assertFalse(
					alias.name.startswith("_"),
					f"importa {alias.name} de {no.module}",
				)

	def test_o_transporte_e_fechado(self):
		"""Sem `with`, os PEM do TLS ficam no disco temporário até o processo morrer."""
		for nome in METODOS_EXPOSTOS:
			with self.subTest(metodo=nome):
				usos = [no for no in ast.walk(_funcao(nome)) if isinstance(no, ast.With)]

				self.assertTrue(usos, f"{nome} não usa o transporte como context manager")


if __name__ == "__main__":
	unittest.main()
