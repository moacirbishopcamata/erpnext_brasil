# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/documento/leitura_codigo.py` — leitura de código de barras 1D/2D."""

import unittest

from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.fiscal.documento.leitura_codigo import LeituraInvalida, extrair_chave

CHAVE = montar_chave("35", "2601", "11222333000181", "65", "1", "1", "1", "12345678")
CHAVE_NFE = montar_chave("35", "2601", "11222333000181", "55", "1", "1", "1", "12345678")

URL_BASE = "https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx"


class TestLeitura1D(unittest.TestCase):
	"""O leitor 1D no DANFE/DACTE/DAMDFE entrega os 44 dígitos crus."""

	def test_quarenta_e_quatro_digitos_crus(self):
		self.assertEqual(extrair_chave(CHAVE_NFE), CHAVE_NFE)

	def test_com_espacos_em_volta(self):
		self.assertEqual(extrair_chave(f"  {CHAVE_NFE}  "), CHAVE_NFE)

	def test_formatada_com_espacos_como_impressa_no_danfe(self):
		"""O DANFE imprime a chave por extenso em grupos de quatro."""
		formatada = " ".join(CHAVE_NFE[i : i + 4] for i in range(0, 44, 4))

		self.assertEqual(extrair_chave(formatada), CHAVE_NFE)

	def test_com_pontos_e_hifens(self):
		self.assertEqual(extrair_chave(f"{CHAVE_NFE[:22]}.{CHAVE_NFE[22:]}"), CHAVE_NFE)


class TestLeitura2D(unittest.TestCase):
	"""O leitor 2D no DANFCe entrega a URL inteira, não a chave."""

	def test_url_do_qrcode_online(self):
		url = f"{URL_BASE}?p={CHAVE}|2|1|1|A1B2C3D4E5F6"

		self.assertEqual(extrair_chave(url), CHAVE)

	def test_url_do_qrcode_em_contingencia_offline(self):
		"""A variante off-line tem mais campos depois da chave — a função corta no
		primeiro `|`, então a quantidade de campos não importa."""
		url = f"{URL_BASE}?p={CHAVE}|2|1|15|1000.00|ABCDEF0123|1|A1B2C3D4E5F6"

		self.assertEqual(extrair_chave(url), CHAVE)

	def test_url_com_pipe_percent_encoded(self):
		"""Alguns leitores entregam a URL já codificada."""
		url = f"{URL_BASE}?p={CHAVE}%7C2%7C1%7C1%7CA1B2C3D4E5F6"

		self.assertEqual(extrair_chave(url), CHAVE)

	def test_url_http_sem_s(self):
		url = f"http://www.nfce.sefin.ro.gov.br/consultanfce/consulta.jsp?p={CHAVE}|2|1|1|ABC"

		self.assertEqual(extrair_chave(url), CHAVE)

	def test_apenas_o_conteudo_do_parametro_sem_a_url(self):
		"""Alguns leitores entregam só o conteúdo, sem o prefixo da URL."""
		self.assertEqual(extrair_chave(f"?p={CHAVE}|2|1|1|ABC"), CHAVE)


class TestLeituraInvalida(unittest.TestCase):
	def test_vazio(self):
		with self.assertRaises(LeituraInvalida):
			extrair_chave("")

	def test_so_espacos(self):
		with self.assertRaises(LeituraInvalida):
			extrair_chave("   ")

	def test_codigo_de_barras_de_produto_falha_alto(self):
		"""EAN-13 lido por engano num campo de chave: tem de falhar, não ser
		interpretado como pedaço de chave."""
		with self.assertRaises(LeituraInvalida):
			extrair_chave("7891234567895")

	def test_quarenta_e_quatro_digitos_com_dv_errado(self):
		"""Extrair não é confiar: o dígito verificador é conferido."""
		errada = CHAVE_NFE[:-1] + ("0" if CHAVE_NFE[-1] != "0" else "1")

		with self.assertRaises(LeituraInvalida):
			extrair_chave(errada)

	def test_url_sem_chave_valida(self):
		with self.assertRaises(LeituraInvalida):
			extrair_chave(f"{URL_BASE}?p=123|2|1|1|ABC")

	def test_texto_qualquer(self):
		with self.assertRaises(LeituraInvalida):
			extrair_chave("nota fiscal numero 123")

	def test_url_nao_junta_digitos_de_toda_a_url(self):
		"""A URL tem dígitos fora do parâmetro `p` (portas, versões). Se a função
		removesse separadores antes de isolar o candidato, ela juntaria tudo e
		acharia 44 dígitos onde não há chave nenhuma."""
		with self.assertRaises(LeituraInvalida):
			extrair_chave("https://exemplo.com:8080/v2/consulta/1234567890?p=12345|2|1|1|ABC")


class TestChaveDeQualquerModelo(unittest.TestCase):
	def test_chave_de_nfe_modelo_55(self):
		self.assertEqual(extrair_chave(CHAVE_NFE), CHAVE_NFE)

	def test_chave_de_cte_modelo_57(self):
		chave_cte = montar_chave("35", "2601", "11222333000181", "57", "1", "1", "1", "12345678")

		self.assertEqual(extrair_chave(chave_cte), chave_cte)

	def test_chave_de_mdfe_modelo_58(self):
		chave_mdfe = montar_chave("35", "2601", "11222333000181", "58", "1", "1", "1", "12345678")

		self.assertEqual(extrair_chave(chave_mdfe), chave_mdfe)


if __name__ == "__main__":
	unittest.main()
