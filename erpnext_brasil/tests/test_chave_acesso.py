# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da chave de acesso da NF-e.

O teste mais importante é `TestPadraoDoXsd`: ele trava a descoberta de que a chave
**não é mais 44 dígitos**. O tipo `TChNFe` do XSD oficial define
``[0-9]{6}[0-9A-Z]{12}[0-9]{26}``, e qualquer validação escrita como ``^\\d{44}$``
passou a rejeitar chave legítima.

Os dois vetores de `TestExemplosConhecidos` foram conferidos contra exemplos resolvidos
com resultado publicado — um com CNPJ numérico e outro com alfanumérico — e reproduzem o
dígito esperado. É o que separa "meu código é coerente" de "meu código concorda com a
especificação".
"""

import unittest

from erpnext_brasil.fiscal.documento.chave_acesso import (
	ChaveInvalida,
	calcular_dv,
	formatar,
	ler_chave,
	montar_chave,
	validar_chave,
)

# 43 posições, CNPJ numérico. Resultado publicado: DV 0.
BASE_NUMERICA = "3526061122233300018155001000000001100000001"

# 43 posições, CNPJ alfanumérico AB000000000001. Resultado publicado: DV 8.
BASE_ALFANUMERICA = "352607AB000000000001550010000000011" + "00000001"


class TestExemplosConhecidos(unittest.TestCase):
	def test_cnpj_numerico(self):
		self.assertEqual(calcular_dv(BASE_NUMERICA), "0")

	def test_cnpj_alfanumerico(self):
		self.assertEqual(calcular_dv(BASE_ALFANUMERICA), "8")

	def test_chave_completa_tem_44_posicoes(self):
		for base in (BASE_NUMERICA, BASE_ALFANUMERICA):
			with self.subTest(base=base[:10]):
				self.assertEqual(len(base + calcular_dv(base)), 44)


class TestPadraoDoXsd(unittest.TestCase):
	"""A chave deixou de ser 44 dígitos puros — `TChNFe` admite 12 alfanuméricas."""

	def test_chave_alfanumerica_e_valida(self):
		chave = BASE_ALFANUMERICA + calcular_dv(BASE_ALFANUMERICA)

		self.assertEqual(validar_chave(chave), chave)

	def test_regex_antiga_rejeitaria_chave_legitima(self):
		"""Guarda explícita contra o retorno de `^\\d{44}$`."""
		import re

		chave = BASE_ALFANUMERICA + calcular_dv(BASE_ALFANUMERICA)

		self.assertIsNone(re.match(r"^\d{44}$", chave))
		self.assertEqual(validar_chave(chave), chave)

	def test_letra_fora_da_faixa_do_cnpj_e_recusada(self):
		"""Só as 12 posições da raiz do CNPJ aceitam letra."""
		chave = list(BASE_NUMERICA + calcular_dv(BASE_NUMERICA))
		chave[0] = "A"  # cUF não é alfanumérico

		with self.assertRaises(ChaveInvalida) as ctx:
			validar_chave("".join(chave))

		self.assertIn("posições 7 a 18", str(ctx.exception))

	def test_dv_do_cnpj_dentro_da_chave_continua_numerico(self):
		# Posições 19 e 20 (índices 18 e 19) são o DV do CNPJ: não aceitam letra.
		chave = list(BASE_ALFANUMERICA + calcular_dv(BASE_ALFANUMERICA))
		chave[18] = "Z"

		with self.assertRaises(ChaveInvalida):
			validar_chave("".join(chave))


class TestValidacao(unittest.TestCase):
	def setUp(self):
		self.chave = BASE_NUMERICA + calcular_dv(BASE_NUMERICA)

	def test_aceita_com_separadores(self):
		self.assertEqual(validar_chave(formatar(self.chave)), self.chave)

	def test_dv_errado_e_recusado(self):
		errado = self.chave[:-1] + ("1" if self.chave[-1] == "0" else "0")

		with self.assertRaises(ChaveInvalida) as ctx:
			validar_chave(errado)

		self.assertIn("Dígito verificador", str(ctx.exception))

	def test_comprimento_errado(self):
		for chave in ("", "123", self.chave + "0"):
			with self.subTest(chave=chave[:12]):
				with self.assertRaises(ChaveInvalida):
					validar_chave(chave)

	def test_minuscula_e_normalizada(self):
		chave = BASE_ALFANUMERICA + calcular_dv(BASE_ALFANUMERICA)

		self.assertEqual(validar_chave(chave.lower()), chave)

	def test_dv_sobre_comprimento_errado_falha_alto(self):
		"""Calcular sobre base errada devolveria dígito plausível e errado."""
		with self.assertRaises(ChaveInvalida):
			calcular_dv("123")


class TestMontagem(unittest.TestCase):
	def test_monta_e_valida(self):
		chave = montar_chave(
			uf="35",
			ano_mes="2606",
			cnpj="11.222.333/0001-81",
			modelo="55",
			serie="1",
			numero="1",
			tipo_emissao="1",
			codigo_numerico="00000001",
		)

		self.assertEqual(validar_chave(chave), chave)

	def test_zeros_a_esquerda_sao_restaurados(self):
		"""Planilha e banco removem zero à esquerda; é a causa mais comum de chave inválida."""
		chave = montar_chave("35", "2606", "11222333000181", "55", "1", "1", "1", "1")
		lida = ler_chave(chave)

		self.assertEqual(lida.serie, "001")
		self.assertEqual(lida.numero, "000000001")
		self.assertEqual(lida.codigo_numerico, "00000001")

	def test_cnpj_com_mascara_e_limpo(self):
		com = montar_chave("35", "2606", "11.222.333/0001-81", "55", "1", "1", "1", "1")
		sem = montar_chave("35", "2606", "11222333000181", "55", "1", "1", "1", "1")

		self.assertEqual(com, sem)

	def test_campo_longo_demais_e_erro(self):
		with self.assertRaises(ChaveInvalida) as ctx:
			montar_chave("35", "2606", "11222333000181", "55", "1234", "1", "1", "1")

		self.assertIn("série", str(ctx.exception))


class TestLeitura(unittest.TestCase):
	def setUp(self):
		self.chave = montar_chave("35", "2606", "11222333000181", "55", "1", "42", "1", "12345678")
		self.lida = ler_chave(self.chave)

	def test_decompoe_os_campos(self):
		self.assertEqual(self.lida.uf, "35")
		self.assertEqual(self.lida.ano_mes, "2606")
		self.assertEqual(self.lida.cnpj, "11222333000181")
		self.assertEqual(self.lida.modelo, "55")
		self.assertEqual(self.lida.numero, "000000042")

	def test_valor_reconstroi_a_chave(self):
		self.assertEqual(self.lida.valor, self.chave)

	def test_reconhece_o_modelo(self):
		self.assertEqual(self.lida.documento, "NF-e")

		nfce = ler_chave(montar_chave("35", "2606", "11222333000181", "65", "1", "1", "1", "1"))
		self.assertEqual(nfce.documento, "NFC-e")

	def test_detecta_cnpj_alfanumerico(self):
		self.assertFalse(self.lida.cnpj_alfanumerico)

		alfa = ler_chave(BASE_ALFANUMERICA + calcular_dv(BASE_ALFANUMERICA))
		self.assertTrue(alfa.cnpj_alfanumerico)


class TestFormatacao(unittest.TestCase):
	def test_agrupa_de_quatro(self):
		chave = BASE_NUMERICA + calcular_dv(BASE_NUMERICA)
		formatada = formatar(chave)

		self.assertEqual(len(formatada.split(" ")), 11)
		self.assertEqual(formatada.replace(" ", ""), chave)


class TestRetrocompatibilidade(unittest.TestCase):
	def test_chave_numerica_bate_pelo_mesmo_caminho(self):
		"""Não há validador "legado": numérico e alfanumérico usam o mesmo código."""
		chave = BASE_NUMERICA + calcular_dv(BASE_NUMERICA)

		self.assertTrue(chave.isdigit())
		self.assertEqual(validar_chave(chave), chave)


if __name__ == "__main__":
	unittest.main()
