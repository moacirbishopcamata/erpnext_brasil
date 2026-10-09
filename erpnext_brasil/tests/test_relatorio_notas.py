# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Consulta pura do relatório "Notas por Situacao" (`fiscal/relatorio_notas.py`).

Teste-âncora: `test_nada_e_descartado_em_silencio`. Um relatório fiscal que some com linha de situação desconhecida
mostra um total menor que o real, sem avisar.
"""

import unittest

from erpnext_brasil.fiscal.relatorio_notas import SITUACOES, autorizadas_sem_chave, resumir


def _l(tipo="Autorização", situacao="Autorizado", codigo="100", creation="2026-10-01 10:00:00", **extra):
	return {"tipo": tipo, "situacao": situacao, "codigo_status": codigo, "creation": creation, **extra}


class TestResumir(unittest.TestCase):
	def test_agrupa_por_tipo_situacao_e_cstat(self):
		resumo = resumir(
			[_l(), _l(), _l(situacao="Rejeitado", codigo="539"), _l(tipo="Cancelamento", codigo="135")]
		)

		contagem = {(r["tipo"], r["situacao"], r["codigo_status"]): r["quantidade"] for r in resumo}

		self.assertEqual(
			contagem,
			{
				("Autorização", "Autorizado", "100"): 2,
				("Autorização", "Rejeitado", "539"): 1,
				("Cancelamento", "Autorizado", "135"): 1,
			},
		)

	def test_nada_e_descartado_em_silencio(self):
		linhas = [_l(), _l(situacao="Situação Nova"), _l(situacao=None, codigo=None), _l(tipo=None)]

		self.assertEqual(sum(r["quantidade"] for r in resumir(linhas)), len(linhas))

	def test_ordem_segue_a_das_situacoes_e_desconhecida_vai_por_ultimo(self):
		resumo = resumir(
			[_l(situacao="Cancelado"), _l(situacao="Situação Nova"), _l(situacao="Pendente"), _l()]
		)

		self.assertEqual(
			[r["situacao"] for r in resumo],
			["Pendente", "Autorizado", "Cancelado", "Situação Nova"],
		)
		self.assertEqual(SITUACOES[0], "Pendente")

	def test_dentro_da_situacao_o_mais_frequente_vem_primeiro(self):
		resumo = resumir(
			[_l(situacao="Rejeitado", codigo="539")] + [_l(situacao="Rejeitado", codigo="204")] * 3
		)

		self.assertEqual([r["codigo_status"] for r in resumo], ["204", "539"])

	def test_primeira_ultima_e_mensagem_mais_recente(self):
		resumo = resumir(
			[
				_l(creation="2026-10-02 09:00:00", mensagem="segunda"),
				_l(creation="2026-10-01 09:00:00", mensagem="primeira"),
			]
		)

		self.assertEqual(resumo[0]["primeira"], "2026-10-01 09:00:00")
		self.assertEqual(resumo[0]["ultima"], "2026-10-02 09:00:00")
		self.assertEqual(resumo[0]["mensagem"], "segunda")

	def test_mesma_entrada_mesma_saida(self):
		linhas = [_l(situacao="Rejeitado", codigo=c) for c in ("539", "204", "539")]

		self.assertEqual(resumir(linhas), resumir(list(reversed(linhas))))

	def test_sem_linhas_devolve_vazio(self):
		self.assertEqual(resumir([]), [])


class TestAutorizadasSemChave(unittest.TestCase):
	def test_conta_so_autorizacao_autorizada_sem_chave(self):
		linhas = [
			_l(chave_acesso="35" + "1" * 42),
			_l(chave_acesso=""),
			_l(chave_acesso=None),
			_l(chave_acesso="   "),
			_l(situacao="Rejeitado", chave_acesso=""),
			_l(tipo="Cancelamento", chave_acesso=""),
		]

		self.assertEqual(autorizadas_sem_chave(linhas), 3)


if __name__ == "__main__":
	unittest.main()
