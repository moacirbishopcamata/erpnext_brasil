# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/efd_arquivo.py` — as regras do arquivo, não de nenhum bloco.

`test_efd_arquivo_completo.py` prova que um arquivo real fecha; este prova as recusas —
o que acontece quando a montagem está errada. São complementares: um exercita o caminho
feliz de ponta a ponta, o outro os contratos.

Teste-âncora: `test_registro_no_bloco_errado_e_recusado`. Um `C100` declarado dentro do
bloco `"D"` produz arquivo que só o PVA reclama, e a mensagem dele não diz onde está o
erro de montagem.
"""

import unittest

from erpnext_brasil.contabil.efd_arquivo import (
	ORDEM_DOS_BLOCOS,
	montar_arquivo_efd,
	serializar_arquivo_efd,
)
from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido


def _bloco_zero() -> list[dict]:
	"""O mínimo que faz um arquivo: abertura, indicação de movimento e encerramento."""
	return [
		{"REG": "0000", "COD_VER": "017", "COD_FIN": "0"},
		{"REG": "0001", "IND_MOV": "0"},
		{"REG": "0990", "QTD_LIN_0": "3"},
	]


class TestOrdemEEstrutura(unittest.TestCase):
	def test_a_ordem_dos_blocos_e_a_do_leiaute(self):
		self.assertEqual(ORDEM_DOS_BLOCOS, ("0", "C", "D", "E", "G", "H", "K", "1"))

	def test_o_nove_nao_esta_na_ordem_porque_e_calculado(self):
		self.assertNotIn("9", ORDEM_DOS_BLOCOS)

	def test_comeca_no_0000_e_termina_no_9999(self):
		arquivo = montar_arquivo_efd({"0": _bloco_zero()})

		self.assertEqual(arquivo[0]["REG"], "0000")
		self.assertEqual(arquivo[-1]["REG"], "9999")

	def test_os_blocos_saem_na_ordem_declarada_mesmo_fora_de_ordem_na_entrada(self):
		"""A ordem do `dict` de entrada não importa — a do arquivo é a do leiaute."""
		bloco_h = [{"REG": "H001", "IND_MOV": "1"}, {"REG": "H990", "QTD_LIN_H": "2"}]
		bloco_c = [{"REG": "C001", "IND_MOV": "1"}, {"REG": "C990", "QTD_LIN_C": "2"}]

		arquivo = montar_arquivo_efd({"H": bloco_h, "0": _bloco_zero(), "C": bloco_c})
		blocos = [linha["REG"][0] for linha in arquivo]

		self.assertLess(blocos.index("C"), blocos.index("H"))

	def test_bloco_ausente_simplesmente_nao_entra(self):
		"""Bloco sem movimento é bloco ausente — diferente de bloco vazio, que exigiria
		o par de abertura e encerramento."""
		arquivo = montar_arquivo_efd({"0": _bloco_zero()})

		self.assertEqual({linha["REG"][0] for linha in arquivo}, {"0", "9"})


class TestRecusas(unittest.TestCase):
	def test_registro_no_bloco_errado_e_recusado(self):
		"""O teste-âncora: só o PVA reclamaria, e sem dizer onde."""
		with self.assertRaises(EfdInvalido) as erro:
			montar_arquivo_efd({"0": _bloco_zero(), "D": [{"REG": "C100"}]})

		self.assertIn("C100", str(erro.exception))
		self.assertIn("'D'", str(erro.exception))

	def test_bloco_zero_e_obrigatorio(self):
		"""É ele que traz os cadastros que os demais citam."""
		with self.assertRaises(EfdInvalido):
			montar_arquivo_efd({"C": [{"REG": "C001", "IND_MOV": "1"}]})

	def test_bloco_desconhecido_e_recusado(self):
		with self.assertRaises(EfdInvalido) as erro:
			montar_arquivo_efd({"0": _bloco_zero(), "Z": []})

		self.assertIn("Z", str(erro.exception))

	def test_o_bloco_nove_nao_pode_ser_informado(self):
		"""A contagem dele é o que a montagem calcula — informá-la seria duas fontes."""
		with self.assertRaises(EfdInvalido):
			montar_arquivo_efd({"0": _bloco_zero(), "9": [{"REG": "9001", "IND_MOV": "0"}]})

	def test_arquivo_que_nao_comeca_no_0000_e_recusado(self):
		with self.assertRaises(EfdInvalido):
			montar_arquivo_efd({"0": [{"REG": "0001", "IND_MOV": "0"}]})


class TestContagem(unittest.TestCase):
	def test_a_contagem_do_9999_bate_com_as_linhas(self):
		arquivo = montar_arquivo_efd({"0": _bloco_zero()})

		self.assertEqual(int(arquivo[-1]["QTD_LIN"]), len(arquivo))

	def test_a_contagem_e_derivada_e_nao_informada(self):
		"""Acrescentar uma linha muda o total sem ninguém recontar à mão."""
		curto = montar_arquivo_efd({"0": _bloco_zero()})
		longo = montar_arquivo_efd(
			{"0": _bloco_zero(), "C": [{"REG": "C001", "IND_MOV": "1"}, {"REG": "C990", "QTD_LIN_C": "2"}]}
		)

		self.assertGreater(int(longo[-1]["QTD_LIN"]), int(curto[-1]["QTD_LIN"]))


class TestSerializacao(unittest.TestCase):
	def test_uma_linha_por_registro(self):
		arquivo = montar_arquivo_efd({"0": _bloco_zero()})
		texto = serializar_arquivo_efd(arquivo)

		self.assertEqual(len(texto.split("\n")), len(arquivo))

	def test_sem_quebra_no_fim(self):
		"""Linha vazia depois do 9999 é linha a mais para o contador que já foi fechado."""
		texto = serializar_arquivo_efd(montar_arquivo_efd({"0": _bloco_zero()}))

		self.assertFalse(texto.endswith("\n"))
		self.assertTrue(texto.split("\n")[-1].startswith("|9999|"))

	def test_toda_linha_e_delimitada_por_pipe(self):
		texto = serializar_arquivo_efd(montar_arquivo_efd({"0": _bloco_zero()}))

		for linha in texto.split("\n"):
			with self.subTest(linha=linha):
				self.assertTrue(linha.startswith("|"))
				self.assertTrue(linha.endswith("|"))


if __name__ == "__main__":
	unittest.main()
