# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes das partes puras que a emissão da NF-e usa.

`integracao/nfe_documento.py` importa `frappe`, então a suíte pura não o alcança — a
montagem completa só pode ser exercitada num site real (lacuna em `docs/gaps.md`).

Por isso as partes **puras** que ele usa não moram lá: as tabelas de tradução ficam em
`setup/custom_fields.py`, ao lado dos Selects que as originam, e o sorteio do `cNF` em
`fiscal/documento/nfe.py`, que é onde a regra do leiaute vive. Mesmo precedente do
`SERIE_POR_MODELO`. Assim a suíte pura consegue travar exatamente o que diverge em
silêncio.

Teste-âncora: `test_todo_rotulo_da_tela_tem_traducao` — se alguém acrescentar uma opção no
Select sem mapeá-la, o teste falha aqui em vez de a emissão quebrar no cliente.
"""

import unittest

from erpnext_brasil.fiscal.codigos.uf import (
	CODIGO_UF_POR_SIGLA,
	UfDesconhecida,
	codigo_da_uf,
	sigla_da_uf,
)
from erpnext_brasil.fiscal.documento.nfe import sortear_codigo_numerico
from erpnext_brasil.setup.custom_fields import (
	CRT_POR_REGIME,
	INDICADOR_IE_POR_ROTULO,
	INDICADORES_IE,
	REGIMES_TRIBUTARIOS,
)


def _opcoes(select: str) -> set[str]:
	return {o for o in select.splitlines() if o}


class TestTraducaoDosRotulos(unittest.TestCase):
	"""As duas tabelas que ligam rótulo de tela a código de leiaute."""

	def test_todo_rotulo_da_tela_tem_traducao(self):
		sem_traducao = sorted(_opcoes(INDICADORES_IE) - set(INDICADOR_IE_POR_ROTULO))

		self.assertEqual(sem_traducao, [], f"opções de br_indicador_ie sem indIEDest: {sem_traducao}")

	def test_nao_ha_traducao_para_rotulo_que_a_tela_nao_oferece(self):
		"""O outro lado: entrada morta na tabela é sujeira que ninguém percebe."""
		orfas = sorted(set(INDICADOR_IE_POR_ROTULO) - _opcoes(INDICADORES_IE))

		self.assertEqual(orfas, [], f"traduções para rótulos inexistentes: {orfas}")

	def test_o_indicador_usa_o_dominio_do_leiaute(self):
		self.assertEqual(set(INDICADOR_IE_POR_ROTULO.values()), {"1", "2", "9"})

	def test_todo_regime_tributario_tem_crt(self):
		sem_crt = sorted(_opcoes(REGIMES_TRIBUTARIOS) - set(CRT_POR_REGIME))

		self.assertEqual(sem_crt, [], f"regimes sem CRT correspondente: {sem_crt}")

	def test_o_crt_usa_o_dominio_do_leiaute(self):
		"""1 = Simples, 2 = Simples com excesso de sublimite, 3 = Regime Normal."""
		self.assertEqual(set(CRT_POR_REGIME.values()), {"1", "2", "3"})

	def test_o_mei_e_simples_nacional(self):
		"""MEI não tem CRT próprio no leiaute — é Simples Nacional."""
		self.assertEqual(CRT_POR_REGIME["Simples Nacional - MEI"], "1")


class TestCodigoNumerico(unittest.TestCase):
	def test_tem_oito_digitos(self):
		for _ in range(50):
			codigo = sortear_codigo_numerico("123")

			self.assertEqual(len(codigo), 8)
			self.assertTrue(codigo.isdigit())

	def test_nunca_repete_o_numero_da_nota(self):
		"""Rejeição 897, regra B03-10: cNF não pode ser igual a nNF."""
		for _ in range(200):
			self.assertNotEqual(sortear_codigo_numerico("7").lstrip("0"), "7")

	def test_nunca_tem_todos_os_digitos_iguais(self):
		for _ in range(200):
			self.assertGreater(len(set(sortear_codigo_numerico("123"))), 1)

	def test_o_resultado_passa_na_validacao_da_identificacao(self):
		"""Costura: o gerador não pode produzir o que `Identificacao.validar` recusa."""
		from datetime import datetime

		from erpnext_brasil.fiscal.documento.nfe import Identificacao

		for numero in ("1", "7", "123", "99999999"):
			with self.subTest(numero=numero):
				Identificacao(
					uf="35",
					municipio_fato_gerador="3550308",
					natureza_operacao="Venda de mercadoria",
					serie="1",
					numero=numero,
					codigo_numerico=sortear_codigo_numerico(numero),
					emissao=datetime(2026, 1, 15, 10, 0, 0),
				).validar()


class TestCodigosDeUf(unittest.TestCase):
	def test_as_vinte_e_sete_unidades(self):
		self.assertEqual(len(CODIGO_UF_POR_SIGLA), 27)

	def test_rondonia_e_onze(self):
		"""A UF do usuário — vale ter o caso explícito."""
		self.assertEqual(codigo_da_uf("RO"), "11")
		self.assertEqual(sigla_da_uf("11"), "RO")

	def test_a_ida_e_a_volta_fecham(self):
		for sigla in CODIGO_UF_POR_SIGLA:
			with self.subTest(uf=sigla):
				self.assertEqual(sigla_da_uf(codigo_da_uf(sigla)), sigla)

	def test_aceita_minuscula_e_espaco(self):
		self.assertEqual(codigo_da_uf(" sp "), "35")

	def test_uf_desconhecida_falha_alto(self):
		"""Devolver vazio produziria um cUF vazio e rejeição sem contexto."""
		with self.assertRaises(UfDesconhecida):
			codigo_da_uf("XX")

		with self.assertRaises(UfDesconhecida):
			sigla_da_uf("99")

	def test_a_inutilizacao_usa_a_mesma_tabela(self):
		"""A tabela morava em `inutilizacao.py` e foi extraída para cá.

		`assertIs`, não `assertEqual`: duas cópias iguais hoje passariam num teste de
		igualdade e divergiriam na primeira alteração. O que se quer garantir é que existe
		**um** objeto, não dois que por ora coincidem.
		"""
		from erpnext_brasil.fiscal.documento.inutilizacao import CODIGO_UF_POR_SIGLA as DA_INUTILIZACAO

		self.assertIs(DA_INUTILIZACAO, CODIGO_UF_POR_SIGLA)


if __name__ == "__main__":
	unittest.main()
