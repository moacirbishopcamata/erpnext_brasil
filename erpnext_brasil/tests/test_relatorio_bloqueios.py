# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Classificação pura do relatório "Bloqueios SEFAZ" (`fiscal/relatorio_bloqueios.py`).

Teste-âncora: `test_sem_liberado_em_e_tratado_como_ativo`. Declarar liberado o que o relatório não sabe seria
convidar a nova emissão que custa outra hora de bloqueio.
"""

import unittest
from datetime import datetime, timedelta

from erpnext_brasil.fiscal.relatorio_bloqueios import classificar

AGORA = datetime(2026, 10, 9, 12, 0, 0)


def _b(bloqueado=AGORA - timedelta(minutes=10), liberado=AGORA + timedelta(minutes=50), cnpj="1"):
	return {"cnpj": cnpj, "bloqueado_em": bloqueado, "liberado_em": liberado}


class TestClassificar(unittest.TestCase):
	def test_antes_de_liberado_em_e_ativo_com_minutos_restantes(self):
		linha = classificar([_b()], AGORA)[0]

		self.assertEqual((linha["situacao"], linha["restante_min"]), ("Ativo", 50))

	def test_fracao_de_minuto_arredonda_para_cima(self):
		linha = classificar([_b(liberado=AGORA + timedelta(seconds=61))], AGORA)[0]

		self.assertEqual(linha["restante_min"], 2)

	def test_exatamente_em_liberado_em_ja_esta_liberado(self):
		linha = classificar([_b(liberado=AGORA)], AGORA)[0]

		self.assertEqual((linha["situacao"], linha["restante_min"]), ("Liberado", 0))

	def test_depois_de_liberado_em_nao_devolve_tempo_negativo(self):
		linha = classificar([_b(liberado=AGORA - timedelta(hours=3))], AGORA)[0]

		self.assertEqual((linha["situacao"], linha["restante_min"]), ("Liberado", 0))

	def test_sem_liberado_em_e_tratado_como_ativo(self):
		linha = classificar([_b(liberado=None)], AGORA)[0]

		self.assertEqual((linha["situacao"], linha["restante_min"]), ("Ativo", 0))

	def test_ativos_primeiro_e_depois_o_mais_recente(self):
		antigo_liberado = _b(
			cnpj="a", bloqueado=AGORA - timedelta(days=2), liberado=AGORA - timedelta(days=2)
		)
		recente_liberado = _b(
			cnpj="b", bloqueado=AGORA - timedelta(hours=5), liberado=AGORA - timedelta(hours=4)
		)
		ativo = _b(cnpj="c")

		self.assertEqual(
			[x["cnpj"] for x in classificar([antigo_liberado, ativo, recente_liberado], AGORA)],
			["c", "b", "a"],
		)

	def test_nao_altera_os_campos_de_entrada(self):
		entrada = _b()

		classificar([entrada], AGORA)

		self.assertNotIn("situacao", entrada)


if __name__ == "__main__":
	unittest.main()
