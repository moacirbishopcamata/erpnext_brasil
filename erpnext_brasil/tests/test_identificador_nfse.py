# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Identificadores da DPS e da NFS-e nacional.

Conferidos contra os XSD oficiais v1.01 (09/02/2026), lidos localmente.

Teste-âncora: `test_o_identificador_nao_se_confunde_com_a_chave_da_nfe`. A NF-e tem 44
dígitos com prefixo `NFe` e DV por módulo 11; a NFS-e tem 50 com prefixo `NFS` e um DV cujo
algoritmo o XSD não define. Confundir as duas é a analogia entre documentos irmãos que este
projeto já pagou caro para não repetir.

Módulo puro: roda sem bench.
"""

import unittest

from erpnext_brasil.fiscal.documento.identificador_nfse import (
	PREFIXO_DPS,
	PREFIXO_NFSE,
	TAMANHO_DPS,
	TAMANHO_NFSE,
	IdentificadorInvalido,
	ler_identificador_dps,
	montar_identificador_dps,
	montar_identificador_nfse,
)

MUNICIPIO_PORTO_VELHO = "1100205"


def _dps(**mudancas) -> str:
	base = {
		"codigo_municipio": MUNICIPIO_PORTO_VELHO,
		"tipo_inscricao": "2",
		"inscricao_federal": "12345678000199",
		"serie": "1",
		"numero": "1",
	}
	base.update(mudancas)

	return montar_identificador_dps(**base)


def _nfse(**mudancas) -> str:
	base = {
		"codigo_municipio": MUNICIPIO_PORTO_VELHO,
		"ambiente_gerador": "1",
		"tipo_inscricao": "2",
		"inscricao_federal": "12345678000199",
		"numero": "1",
		"ano_mes": "2609",
		"codigo_numerico": "000000001",
		"digito_verificador": "7",
	}
	base.update(mudancas)

	return montar_identificador_nfse(**base)


class TestTamanhos(unittest.TestCase):
	def test_a_dps_tem_45_posicoes_com_prefixo(self):
		identificador = _dps()

		self.assertTrue(identificador.startswith(PREFIXO_DPS))
		self.assertEqual(45, len(identificador))
		self.assertEqual(TAMANHO_DPS, len(identificador) - len(PREFIXO_DPS))

	def test_a_nfse_tem_53_posicoes_com_prefixo(self):
		identificador = _nfse()

		self.assertTrue(identificador.startswith(PREFIXO_NFSE))
		self.assertEqual(53, len(identificador))
		self.assertEqual(TAMANHO_NFSE, len(identificador) - len(PREFIXO_NFSE))

	def test_o_identificador_nao_se_confunde_com_a_chave_da_nfe(self):
		"""Teste-âncora: 44 dígitos e prefixo `NFe` são de outro documento."""
		self.assertNotEqual(44, TAMANHO_DPS)
		self.assertNotEqual(44, TAMANHO_NFSE)
		self.assertNotEqual("NFe", PREFIXO_NFSE)


class TestPosicoes(unittest.TestCase):
	def test_os_campos_ficam_nas_posicoes_do_leiaute(self):
		lido = ler_identificador_dps(_dps(serie="12", numero="345"))

		self.assertEqual(MUNICIPIO_PORTO_VELHO, lido.codigo_municipio)
		self.assertEqual("2", lido.tipo_inscricao)
		self.assertEqual("12345678000199", lido.inscricao_federal)
		self.assertEqual("00012", lido.serie)
		self.assertEqual("000000000000345", lido.numero)

	def test_ler_aceita_com_e_sem_prefixo(self):
		"""Quem lê XML recebe com prefixo; quem lê relatório, sem."""
		com_prefixo = _dps()
		sem_prefixo = com_prefixo.removeprefix(PREFIXO_DPS)

		self.assertEqual(
			ler_identificador_dps(com_prefixo),
			ler_identificador_dps(sem_prefixo),
		)

	def test_montar_e_ler_fecham_o_ciclo(self):
		original = _dps(serie="99", numero="123456")
		relido = ler_identificador_dps(original)

		self.assertEqual(
			original,
			montar_identificador_dps(
				codigo_municipio=relido.codigo_municipio,
				tipo_inscricao=relido.tipo_inscricao,
				inscricao_federal=relido.inscricao_federal,
				serie=relido.serie,
				numero=relido.numero,
			),
		)


class TestInscricaoFederal(unittest.TestCase):
	"""O XSD manda completar o CPF com 000 à esquerda — 14 posições nos dois casos."""

	def test_cpf_recebe_tres_zeros_a_esquerda(self):
		lido = ler_identificador_dps(_dps(tipo_inscricao="1", inscricao_federal="12345678901"))

		self.assertEqual("00012345678901", lido.inscricao_federal)

	def test_cnpj_ocupa_as_14_posicoes_inteiras(self):
		lido = ler_identificador_dps(_dps(tipo_inscricao="2", inscricao_federal="12345678000199"))

		self.assertEqual("12345678000199", lido.inscricao_federal)

	def test_a_pontuacao_do_documento_e_removida(self):
		lido = ler_identificador_dps(_dps(inscricao_federal="12.345.678/0001-99"))

		self.assertEqual("12345678000199", lido.inscricao_federal)

	def test_cpf_com_tamanho_de_cnpj_e_recusado(self):
		"""A conferência é por tipo, não um `rjust(14)` que aceitaria qualquer coisa."""
		with self.assertRaises(IdentificadorInvalido) as erro:
			_dps(tipo_inscricao="1", inscricao_federal="12345678000199")

		self.assertEqual("inscricao_federal", erro.exception.campo)

	def test_tipo_de_inscricao_desconhecido_e_recusado(self):
		with self.assertRaises(IdentificadorInvalido) as erro:
			_dps(tipo_inscricao="9")

		self.assertEqual("tipo_inscricao", erro.exception.campo)


class TestSerieENumero(unittest.TestCase):
	def test_a_serie_admite_zeros_a_esquerda(self):
		"""`TSSerieDPS` os admite explicitamente — planilha e banco os removem, e o
		identificador é posicional."""
		self.assertEqual("00001", ler_identificador_dps(_dps(serie="00001")).serie)

	def test_serie_maior_que_cinco_digitos_e_recusada(self):
		with self.assertRaises(IdentificadorInvalido) as erro:
			_dps(serie="123456")

		self.assertEqual("serie", erro.exception.campo)

	def test_zeros_a_esquerda_do_numero_sao_enchimento_posicional(self):
		"""Achado de um teste de ciclo, não de leitura de código.

		`TSNumDPS` é `[1-9][0-9]{0,14}`, e a primeira versão deste módulo recusava qualquer
		número começado em zero. Só que `ler_identificador_dps` devolve os campos **como
		estão no identificador** — preenchidos até a largura —, então montar → ler → montar
		não fechava: o segundo `montar` recusava o que o `ler` acabara de produzir.

		A leitura certa é que os zeros à esquerda enchem a **posição**, não fazem parte do
		número. `"0123"` e `"123"` são a mesma DPS.
		"""
		self.assertEqual(_dps(numero="123"), _dps(numero="0000000000000123"[-15:]))

	def test_numero_zerado_e_recusado(self):
		"""Ali não há enchimento a tirar: o documento ficaria sem número."""
		with self.assertRaises(IdentificadorInvalido) as erro:
			_dps(numero="000")

		self.assertEqual("numero", erro.exception.campo)

	def test_numero_maior_que_quinze_digitos_e_recusado(self):
		with self.assertRaises(IdentificadorInvalido) as erro:
			_dps(numero="1234567890123456")

		self.assertEqual("numero", erro.exception.campo)

	def test_a_serie_nao_carrega_os_caracteres_literais_do_xsd(self):
		"""O `pattern` de `TSSerieDPS` traz `^` e `$`, que em XML Schema **não** são
		âncoras — seriam literais. É o único pattern assim em 1843 linhas do arquivo, e
		este módulo aplica a intenção, não a letra. Ver a docstring do módulo."""
		with self.assertRaises(IdentificadorInvalido):
			_dps(serie="^1$")


class TestNfse(unittest.TestCase):
	def test_o_digito_verificador_e_exigido_e_nao_calculado(self):
		"""O XSD declara a posição do DV e **não** o algoritmo. Assumir módulo 11 porque a
		NF-e usa módulo 11 é a analogia proibida."""
		with self.assertRaises(IdentificadorInvalido) as erro:
			_nfse(digito_verificador="")

		self.assertEqual("digito_verificador", erro.exception.campo)

	def test_o_numero_da_nfse_vai_ate_treze_digitos(self):
		"""`TSNNFSe` é mais curto que o `TSNumDPS`, de 15 — dois documentos, dois limites."""
		with self.assertRaises(IdentificadorInvalido) as erro:
			_nfse(numero="12345678901234")

		self.assertEqual("numero", erro.exception.campo)

	def test_ano_mes_tem_quatro_digitos(self):
		with self.assertRaises(IdentificadorInvalido) as erro:
			_nfse(ano_mes="202609")

		self.assertEqual("ano_mes", erro.exception.campo)

	def test_codigo_numerico_tem_nove_digitos(self):
		with self.assertRaises(IdentificadorInvalido) as erro:
			_nfse(codigo_numerico="123")

		self.assertEqual("codigo_numerico", erro.exception.campo)

	def test_o_ambiente_gerador_existe_na_nfse_e_nao_na_dps(self):
		"""Campo presente num leiaute e ausente no outro: são documentos diferentes, não
		duas formas do mesmo."""
		identificador = _nfse().removeprefix(PREFIXO_NFSE)

		self.assertEqual("1", identificador[7:8])


class TestMunicipio(unittest.TestCase):
	def test_o_codigo_do_municipio_tem_sete_digitos(self):
		with self.assertRaises(IdentificadorInvalido) as erro:
			_dps(codigo_municipio="11002")

		self.assertEqual("codigo_municipio", erro.exception.campo)

	def test_porto_velho_e_o_municipio_de_referencia_do_projeto(self):
		"""RO, e o município da jurisdição do usuário — ver a memória do projeto."""
		self.assertTrue(_dps().startswith(f"{PREFIXO_DPS}{MUNICIPIO_PORTO_VELHO}"))


class TestRecusas(unittest.TestCase):
	def test_identificador_curto_e_recusado(self):
		with self.assertRaises(IdentificadorInvalido):
			ler_identificador_dps("DPS123")

	def test_identificador_com_letra_e_recusado(self):
		with self.assertRaises(IdentificadorInvalido):
			ler_identificador_dps(PREFIXO_DPS + "A" * TAMANHO_DPS)


if __name__ == "__main__":
	unittest.main()
