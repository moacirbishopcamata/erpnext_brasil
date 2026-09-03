# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes do `locale/pt_BR.po` — o arquivo que corrige a tradução do ERPNext.

Sobrescrever a tradução de outro app é poder que se usa com parcimônia: se este arquivo
tiver um `msgid` errado, a correção simplesmente não acontece (e ninguém percebe); se
tiver uma entrada duplicada, o comportamento depende de qual o compilador escolhe. Estes
testes tornam o arquivo verificável sem precisar de bench.

Não testam *se* o Frappe aplica a tradução — isso depende do bench e está registrado em
`docs/traducao.md`, com a leitura do código-fonte que confirma o mecanismo. Testam que o
arquivo está correto naquilo que só depende dele.
"""

import re
import unittest
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent.parent / "locale" / "pt_BR.po"

_ENTRADA = re.compile(r'^msgid "(.*)"\s*\nmsgstr "(.*)"', re.MULTILINE)


def _entradas() -> dict[str, str]:
	texto = ARQUIVO.read_text(encoding="utf-8")

	return {msgid: msgstr for msgid, msgstr in _ENTRADA.findall(texto) if msgid}


class TestArquivoExiste(unittest.TestCase):
	def test_o_arquivo_esta_no_lugar_que_o_frappe_procura(self):
		"""Frappe 15+ lê `<app>/locale/<lang>.po`; nome com underscore, não hífen."""
		self.assertTrue(ARQUIVO.exists(), f"esperado em {ARQUIVO}")

	def test_tem_cabecalho_de_po_valido(self):
		texto = ARQUIVO.read_text(encoding="utf-8")

		self.assertIn('"Language: pt_BR\\n"', texto)
		self.assertIn('"Content-Type: text/plain; charset=UTF-8\\n"', texto)


class TestConteudo(unittest.TestCase):
	def setUp(self):
		self.entradas = _entradas()

	def test_nenhuma_traducao_vazia(self):
		"""`msgstr` vazio não corrige nada — seria uma entrada que só ocupa espaço."""
		vazias = [msgid for msgid, msgstr in self.entradas.items() if not msgstr.strip()]

		self.assertEqual(vazias, [], f"entradas sem tradução: {vazias}")

	def test_nenhum_msgid_repetido(self):
		"""Duplicata torna o resultado dependente do compilador."""
		texto = ARQUIVO.read_text(encoding="utf-8")
		ids = [m for m in re.findall(r'^msgid "(.+)"', texto, re.MULTILINE)]

		self.assertEqual(len(ids), len(set(ids)), "há msgid repetido no arquivo")

	def test_nenhuma_traducao_igual_ao_original(self):
		"""Traduzir para o próprio texto não sobrescreve nada de útil."""
		iguais = [msgid for msgid, msgstr in self.entradas.items() if msgid == msgstr]

		self.assertEqual(iguais, [])


class TestCorrecoesQueMotivamOArquivo(unittest.TestCase):
	"""Cada uma tem fonte objetiva — ver os comentários no próprio `.po`."""

	def setUp(self):
		self.entradas = _entradas()

	def test_siglas_fiscais_em_caixa_alta(self):
		"""O ERPNext traduz `Tax ID` como "Cpf/cnpj"; CPF e CNPJ são siglas."""
		self.assertEqual(self.entradas["Tax ID"], "CPF/CNPJ")

	def test_imobilizado_e_nao_ativo_fixo(self):
		"""Lei 6.404/76, Art. 178, §1º — e é o termo que `plano_de_contas.py` usa."""
		self.assertEqual(self.entradas["Fixed Asset"], "Imobilizado")
		self.assertNotIn("Fixo", self.entradas["Fixed Asset Register"])

	def test_preposicao_minuscula_em_titulo(self):
		"""O ERPNext escreve "Custo Dos Produtos Vendidos"."""
		self.assertEqual(self.entradas["Cost of Goods Sold"], "Custo dos Produtos Vendidos")

	def test_nenhuma_preposicao_maiuscula_nas_traducoes(self):
		"""Regra geral aplicada a todo o arquivo, não só ao caso que a motivou."""
		erradas = [
			f"{msgid} -> {msgstr}"
			for msgid, msgstr in self.entradas.items()
			if re.search(r"[a-zà-ú] (Dos|Das|Do|Da|De|Em|Para|Com|E) [A-ZÀ-Ú]", msgstr)
		]

		self.assertEqual(erradas, [], f"preposição em maiúscula: {erradas}")


class TestAlinhamentoComOPlanoDeContas(unittest.TestCase):
	"""Linguagem ubíqua: o termo na tela tem de ser o mesmo do código."""

	def test_imobilizado_bate_com_o_plano_de_contas(self):
		from erpnext_brasil.contabil.plano_de_contas import listar_nomes

		self.assertIn("Imobilizado", listar_nomes())
		self.assertEqual(_entradas()["Fixed Asset"], "Imobilizado")


if __name__ == "__main__":
	unittest.main()
