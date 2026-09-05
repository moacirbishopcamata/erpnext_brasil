# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Dados bancários da cobrança: limpeza, limites e o que o site precisa ter declarado.

Duas metades. A primeira é o domínio puro (`contabil/conta_bancaria.py`) — validação que
roda sem bench. A segunda é a costura: todo campo que `integracao/conta_bancaria.py` lê tem
de estar declarado em `setup/custom_fields.py`, senão `frappe.get_all` devolve `None` e a
conta chega vazia sem erro nenhum. É a família dos 31 campos de `docs/gaps.md`.

Teste-âncora: `test_todo_campo_lido_esta_declarado`.
"""

import ast
import unittest
from pathlib import Path

from erpnext_brasil.contabil.conta_bancaria import (
	TAMANHOS,
	DadosBancariosInvalidos,
	montar_conta_bancaria,
	somente_digitos,
)
from erpnext_brasil.setup.custom_fields import get_custom_fields

RAIZ = Path(__file__).resolve().parent.parent


def _campos_lidos() -> set[str]:
	"""`CAMPOS_DA_CONTA`, lido do fonte por AST.

	`integracao/conta_bancaria.py` importa `frappe`, e esta suíte roda sem bench — mesma
	razão de `test_eventos_nfe` ler `AMBIENTE_POR_CHAVE` assim.
	"""
	fonte = (RAIZ / "integracao" / "conta_bancaria.py").read_text(encoding="utf-8")

	for no in ast.walk(ast.parse(fonte)):
		if isinstance(no, ast.Assign) and any(
			isinstance(alvo, ast.Name) and alvo.id == "CAMPOS_DA_CONTA" for alvo in no.targets
		):
			return {e.value for e in no.value.elts if isinstance(e, ast.Constant)}

	raise AssertionError("CAMPOS_DA_CONTA não encontrado")


def _conta(**mudancas):
	base = {
		"codigo_banco": "341",
		"agencia": "1234",
		"conta": "56789",
		"agencia_dv": "5",
		"conta_dv": "0",
		"carteira": "109",
		"convenio": "1234567",
	}
	base.update(mudancas)

	return montar_conta_bancaria(**base)


class TestLimpeza(unittest.TestCase):
	def test_pontuacao_digitada_pelo_usuario_nao_entra_no_arquivo(self):
		conta = _conta(agencia="1.234", conta="56.789")

		self.assertEqual("1234", conta.agencia)
		self.assertEqual("56789", conta.conta)

	def test_o_hifen_do_digito_e_removido(self):
		self.assertEqual("12345", somente_digitos("1234-5"))

	def test_valor_ausente_vira_string_vazia(self):
		self.assertEqual("", somente_digitos(None))

	def test_a_formatacao_para_humano_recoloca_o_hifen(self):
		conta = _conta()

		self.assertEqual("1234-5", conta.agencia_formatada)
		self.assertEqual("56789-0", conta.conta_formatada)

	def test_sem_digito_nao_sobra_hifen_solto(self):
		"""`1234-` num comprovante parece dado truncado."""
		conta = _conta(agencia_dv="", conta_dv="")

		self.assertEqual("1234", conta.agencia_formatada)
		self.assertEqual("56789", conta.conta_formatada)


class TestObrigatorios(unittest.TestCase):
	def test_sem_banco_agencia_ou_conta_nao_ha_cobranca(self):
		for campo in ("codigo_banco", "agencia", "conta"):
			with self.subTest(campo=campo):
				with self.assertRaises(DadosBancariosInvalidos) as erro:
					_conta(**{campo: ""})

				self.assertEqual(campo, erro.exception.campo)

	def test_a_mensagem_diz_qual_campo(self):
		"""Quem vê o erro está numa tela com sete caixas parecidas."""
		with self.assertRaises(DadosBancariosInvalidos) as erro:
			_conta(agencia="")

		self.assertIn("agencia", str(erro.exception))

	def test_digito_e_carteira_podem_faltar(self):
		"""Nem todo banco usa dígito na agência, e carteira depende de contrato."""
		conta = _conta(agencia_dv="", conta_dv="", carteira="", convenio="")

		self.assertEqual("341", conta.codigo_banco)


class TestLimites(unittest.TestCase):
	def test_campo_maior_que_o_teto_e_recusado(self):
		with self.assertRaises(DadosBancariosInvalidos) as erro:
			_conta(agencia="123456")

		self.assertEqual("agencia", erro.exception.campo)

	def test_o_codigo_do_banco_tem_tamanho_exato(self):
		"""Um COMPE de dois dígitos deslocaria o código de barras inteiro."""
		with self.assertRaises(DadosBancariosInvalidos) as erro:
			_conta(codigo_banco="41")

		self.assertEqual("codigo_banco", erro.exception.campo)

	def test_o_codigo_do_banco_aceita_zero_a_esquerda(self):
		"""001 é o Banco do Brasil, e perder o zero o transformaria em outro banco."""
		self.assertEqual("001", _conta(codigo_banco="001").codigo_banco)

	def test_todo_campo_declarado_tem_teto(self):
		"""Campo sem teto é campo que ninguém confere."""
		self.assertEqual(7, len(TAMANHOS))
		self.assertTrue(all(limite > 0 for limite in TAMANHOS.values()))


class TestCosturaComOSite(unittest.TestCase):
	"""Campo lido e não declarado devolve `None` — a conta chega vazia, sem erro."""

	def _declarados(self, doctype: str) -> set[str]:
		return {campo["fieldname"] for campo in get_custom_fields().get(doctype, [])}

	def test_todo_campo_lido_esta_declarado(self):
		# Do ERPNext, não deste app — por isso não estão em `custom_fields`.
		nativos = {"name", "bank", "bank_account_no"}
		nossos = _campos_lidos() - nativos

		self.assertTrue(nossos, "nenhum campo próprio lido — o teste ficaria vazio")
		self.assertEqual(set(), nossos - self._declarados("Bank Account"))

	def test_o_codigo_compe_esta_declarado_no_banco_e_nao_na_conta(self):
		"""É atributo da instituição: repeti-lo por conta deixaria duas contas do mesmo
		banco discordarem sobre qual banco é."""
		self.assertIn("br_codigo_banco", self._declarados("Bank"))
		self.assertNotIn("br_codigo_banco", self._declarados("Bank Account"))

	def test_o_numero_da_conta_nao_foi_duplicado(self):
		"""`bank_account_no` já existe no ERPNext; um `br_conta` produziria duas verdades
		sobre a mesma conta."""
		self.assertNotIn("br_conta", self._declarados("Bank Account"))

	def test_o_ispb_nao_se_confunde_com_o_compe(self):
		"""Oito dígitos para o PIX, três para o boleto — e nenhum se deduz do outro."""
		declarados = self._declarados("Bank")

		self.assertIn("br_ispb", declarados)
		self.assertIn("br_codigo_banco", declarados)


if __name__ == "__main__":
	unittest.main()
