# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Código de município do IBGE (`fiscal/codigos/municipio.py`) — tarefa 1.1 de `tropicalizar-demais-modulos`.

Os dados dos testes **não são de memória**: as 27 capitais e as 9 exceções foram conferidas, uma a uma, contra
a lista oficial de municípios do IBGE baixada em 2026-10-09. Para repetir a conferência completa (os 5.571
códigos), aponte `IBGE_MUNICIPIOS_JSON` para o JSON da API de localidades; sem a variável o teste é pulado —
a lista não é embutida no repositório.

Teste-âncora: `test_os_nove_municipios_reais_fora_da_regra_sao_aceitos`. A primeira ideia era recusar todo
código com dígito errado; a lista oficial mostrou que isso recusaria 9 municípios que existem.
"""

import ast
import json
import os
import pathlib
import unittest

from erpnext_brasil.fiscal.codigos.municipio import (
	EXCECOES_DO_DIGITO,
	ExcecoesInvalidas,
	MunicipioInvalido,
	digito_verificador,
	ler_excecoes,
	validar_municipio,
)

CAPITAIS = {
	"RO": "1100205", "AC": "1200401", "AM": "1302603", "RR": "1400100", "PA": "1501402",
	"AP": "1600303", "TO": "1721000", "MA": "2111300", "PI": "2211001", "CE": "2304400",
	"RN": "2408102", "PB": "2507507", "PE": "2611606", "AL": "2704302", "SE": "2800308",
	"BA": "2927408", "MG": "3106200", "ES": "3205309", "RJ": "3304557", "SP": "3550308",
	"PR": "4106902", "SC": "4205407", "RS": "4314902", "MS": "5002704", "MT": "5103403",
	"GO": "5208707", "DF": "5300108",
}  # fmt: skip


class TestDigitoVerificador(unittest.TestCase):
	def test_valores_conhecidos(self):
		self.assertEqual(digito_verificador("110020"), 5)  # Porto Velho
		self.assertEqual(digito_verificador("355030"), 8)  # São Paulo
		self.assertEqual(digito_verificador("310620"), 0)  # Belo Horizonte: soma 10, resto 0

	def test_exige_seis_algarismos(self):
		for ruim in ("", "12345", "1234567", "12345a"):
			with self.subTest(ruim=ruim), self.assertRaises(ValueError):
				digito_verificador(ruim)


class TestValidarMunicipio(unittest.TestCase):
	def test_as_27_capitais_passam_com_a_propria_uf(self):
		for uf, codigo in CAPITAIS.items():
			with self.subTest(uf=uf):
				validar_municipio(codigo, uf)

	def test_os_nove_municipios_reais_fora_da_regra_sao_aceitos(self):
		self.assertEqual(len(EXCECOES_DO_DIGITO), 9)

		for codigo, (nome, uf) in EXCECOES_DO_DIGITO.items():
			esperado = digito_verificador(codigo[:6])
			self.assertNotEqual(int(codigo[6]), esperado, f"{nome} deixou de ser exceção — remova da lista")

			with self.subTest(municipio=nome):
				validar_municipio(codigo, uf)

	def test_um_digito_trocado_e_recusado_com_o_digito_esperado(self):
		with self.assertRaises(MunicipioInvalido) as contexto:
			validar_municipio("1100206")

		self.assertEqual(contexto.exception.motivo, "digito")
		self.assertIn("deveria ser 5", str(contexto.exception))

	def test_nenhuma_troca_de_um_digito_entre_os_seis_primeiros_escapa(self):
		"""Com peso 1 a contribuição do algarismo é ele mesmo; com peso 2 é 0,2,4,6,8,1,3,5,7,9 — nos dois casos
		os dez valores são distintos módulo 10, então trocar um algarismo sempre muda o dígito esperado."""
		for base in (*CAPITAIS.values(), "3550308"):
			passaram = []

			for posicao in range(6):
				for novo in "0123456789":
					if novo == base[posicao]:
						continue

					codigo = base[:posicao] + novo + base[posicao + 1 :]

					try:
						validar_municipio(codigo)
						passaram.append(codigo)
					except MunicipioInvalido:
						pass

			self.assertEqual(passaram, [], f"trocas de um dígito em {base} que passaram")

	def test_municipio_de_outra_uf_e_recusado(self):
		with self.assertRaises(MunicipioInvalido) as contexto:
			validar_municipio("1100205", "SP")

		self.assertEqual(contexto.exception.motivo, "uf")
		self.assertIn("é de RO", str(contexto.exception))
		self.assertIn("informa SP", str(contexto.exception))

	def test_uf_por_extenso_e_sem_acento_tambem_vale(self):
		validar_municipio("1100205", "Rondônia")
		validar_municipio("1100205", "rondonia")

		with self.assertRaises(MunicipioInvalido):
			validar_municipio("1100205", "São Paulo")

	def test_uf_nao_reconhecida_nao_trava_mas_o_digito_continua_valendo(self):
		validar_municipio("1100205", "Estado Imaginário")
		validar_municipio("1100205", None)
		validar_municipio("1100205", "")

		with self.assertRaises(MunicipioInvalido) as contexto:
			validar_municipio("1100206", None)

		self.assertEqual(contexto.exception.motivo, "digito")

	def test_prefixo_que_nao_e_de_uf_e_recusado(self):
		with self.assertRaises(MunicipioInvalido) as contexto:
			validar_municipio("9900001")

		self.assertEqual(contexto.exception.motivo, "uf")

	def test_formato_malformado_e_recusado_como_antes(self):
		for ruim in ("", "123456", "12345678", "11002a5", None):
			with self.subTest(ruim=ruim), self.assertRaises(MunicipioInvalido) as contexto:
				validar_municipio(ruim)

			self.assertEqual(contexto.exception.motivo, "formato")

		self.assertIn("deve ter 7 dígitos numéricos", str(contexto.exception))

	def test_excecao_do_administrador_dispensa_so_o_digito(self):
		extras = frozenset({"1100206"})

		validar_municipio("1100206", "RO", extras)

		with self.assertRaises(MunicipioInvalido):
			validar_municipio("1100206", "SP", extras)

	def test_excecao_conhecida_continua_presa_a_sua_uf(self):
		with self.assertRaises(MunicipioInvalido) as contexto:
			validar_municipio("2202251", "SP")

		self.assertEqual(contexto.exception.motivo, "uf")


class TestLerExcecoes(unittest.TestCase):
	def test_vazio_ou_ausente(self):
		self.assertEqual(ler_excecoes(None), frozenset())
		self.assertEqual(ler_excecoes([]), frozenset())

	def test_lista_valida(self):
		self.assertEqual(ler_excecoes(["1100206", " 3550309 "]), frozenset({"1100206", "3550309"}))

	def test_recusa_o_que_nao_e_lista_de_sete_digitos(self):
		for ruim in ("1100206", [1100206], ["110020"], ["1100206x"], {"a": 1}, 7):
			with self.subTest(ruim=ruim), self.assertRaises(ExcecoesInvalidas):
				ler_excecoes(ruim)


@unittest.skipUnless(
	os.environ.get("IBGE_MUNICIPIOS_JSON") and os.path.exists(os.environ.get("IBGE_MUNICIPIOS_JSON", "")),
	"defina IBGE_MUNICIPIOS_JSON com o JSON da API de localidades do IBGE para conferir os 5.571 códigos",
)
class TestContraAListaOficialCompleta(unittest.TestCase):
	"""A conferência que fez a regra virar 'regra + 9 exceções'. Roda só quando a lista está à mão."""

	def test_todo_municipio_real_passa_e_so_as_nove_exceções_violam_a_regra(self):
		with open(os.environ["IBGE_MUNICIPIOS_JSON"], encoding="utf-8") as arquivo:
			municipios = json.load(arquivo)

		violam = []

		for municipio in municipios:
			codigo = str(municipio["id"])
			validar_municipio(codigo)

			if int(codigo[6]) != digito_verificador(codigo[:6]):
				violam.append(codigo)

		self.assertGreaterEqual(len(municipios), 5570)
		self.assertEqual(sorted(violam), sorted(EXCECOES_DO_DIGITO))


class TestCosturaDoHookDeEndereco(unittest.TestCase):
	"""`integracao/party.py` importa `frappe`; o comportamento está em `tests_bench/test_party.py`. Aqui, a costura."""

	def _codigo(self) -> ast.Module:
		return ast.parse(
			(pathlib.Path(__file__).resolve().parents[1] / "integracao" / "party.py").read_text(
				encoding="utf-8"
			)
		)

	def _funcao(self, nome: str) -> ast.FunctionDef:
		return next(n for n in ast.walk(self._codigo()) if isinstance(n, ast.FunctionDef) and n.name == nome)

	def test_o_hook_usa_a_regra_pura_e_o_codigo_de_erro_estavel(self):
		corpo = ast.unparse(self._funcao("validar_codigo_municipio"))

		self.assertIn("validar_municipio(", corpo)
		self.assertIn("MunicipioInvalido", corpo)
		self.assertIn("CADASTRO_CODIGO_DE_MUNICIPIO_INVALIDO", corpo)
		self.assertIn("doc.get('state')", corpo, "a UF do endereço é a segunda barreira")

	def test_configuracao_invalida_degrada_com_registro_e_nao_trava_o_cadastro(self):
		corpo = ast.unparse(self._funcao("_excecoes_do_administrador"))

		self.assertIn("ExcecoesInvalidas", corpo)
		self.assertIn("log_error", corpo)
		self.assertNotIn("throw", corpo)

	def test_a_chave_de_configuracao_tem_o_nome_documentado(self):
		valores = [
			n.value.value
			for n in self._codigo().body
			if isinstance(n, ast.Assign)
			and getattr(n.targets[0], "id", "") == "CHAVE_EXCECOES_DO_DIGITO"
			and isinstance(n.value, ast.Constant)
		]

		self.assertEqual(valores, ["brasil_municipios_excecao_dv"])

	def test_o_hook_continua_ligado_ao_address(self):
		from erpnext_brasil import hooks

		self.assertEqual(
			hooks.doc_events["Address"]["validate"],
			"erpnext_brasil.integracao.party.validar_codigo_municipio",
		)


if __name__ == "__main__":
	unittest.main()
