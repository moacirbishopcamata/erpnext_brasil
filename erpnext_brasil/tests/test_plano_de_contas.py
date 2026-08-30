# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da estrutura de grupos do plano de contas (`contabil/plano_de_contas.py`).

O teste que mais importa é `test_todo_tributo_conhecido_tem_ao_menos_uma_conta`: a
"amarração aos tributos" só vale alguma coisa se todo tributo que a camada fiscal sabe
calcular tiver, de fato, uma conta para receber o lançamento — não é suficiente a conta
existir, precisa existir *para cada* tributo da allowlist.
"""

import unittest

from erpnext_brasil.contabil.plano_de_contas import (
	ARVORE,
	ROOT_TYPE_ATIVO,
	ROOT_TYPE_DESPESA,
	ROOT_TYPE_PASSIVO,
	ROOT_TYPE_RECEITA,
	TRIBUTOS_CONHECIDOS,
	Conta,
	PlanoDeContasInvalido,
	contas_do_tributo,
	listar_nomes,
	validar_arvore,
)


class TestEstrutura(unittest.TestCase):
	def test_quatro_root_types_representados(self):
		"""Ativo, Passivo (com Patrimônio Líquido dentro), Receita e Despesa — os cinco
		`root_type` do ERPNext, sendo Patrimônio Líquido um grupo dentro de Passivo."""
		tipos = {root_type for root_type, _raiz in ARVORE}

		self.assertEqual(tipos, {ROOT_TYPE_ATIVO, ROOT_TYPE_PASSIVO, ROOT_TYPE_RECEITA, ROOT_TYPE_DESPESA})

	def test_patrimonio_liquido_fica_dentro_do_passivo(self):
		"""Art. 178, § 2º: Patrimônio Líquido é um dos três grupos do lado do passivo,
		não uma raiz própria — `root_type` do ERPNext não distingue os dois."""
		_root_type, passivo = next(item for item in ARVORE if item[0] == ROOT_TYPE_PASSIVO)
		nomes_diretos = [filha.nome for filha in passivo.filhas]

		self.assertIn("Patrimônio Líquido", nomes_diretos)

	def test_nenhum_nome_de_conta_duplicado(self):
		nomes = listar_nomes()

		self.assertEqual(len(nomes), len(set(nomes)))

	def test_validar_arvore_nao_levanta_para_a_arvore_padrao(self):
		validar_arvore()  # não deve levantar

	def test_validar_arvore_rejeita_tributo_desconhecido(self):
		arvore_invalida = (
			(ROOT_TYPE_ATIVO, Conta("Ativo", filhas=(Conta("Conta Fantasma", tributo="ICMS-FANTASMA"),))),
		)

		with self.assertRaises(PlanoDeContasInvalido):
			validar_arvore(arvore_invalida)

	def test_validar_arvore_rejeita_nome_duplicado(self):
		arvore_invalida = (
			(
				ROOT_TYPE_ATIVO,
				Conta("Ativo", filhas=(Conta("Caixa"), Conta("Grupo", filhas=(Conta("Caixa"),)))),
			),
		)

		with self.assertRaises(PlanoDeContasInvalido):
			validar_arvore(arvore_invalida)


class TestAmarracaoAosTributos(unittest.TestCase):
	def test_todo_tributo_conhecido_tem_ao_menos_uma_conta(self):
		sem_conta = [tributo for tributo in TRIBUTOS_CONHECIDOS if not contas_do_tributo(tributo)]

		self.assertEqual(sem_conta, [], f"tributo sem nenhuma conta amarrada: {sem_conta}")

	def test_icms_tem_conta_a_recolher_e_a_recuperar(self):
		nomes = {conta.nome for conta in contas_do_tributo("ICMS")}

		self.assertIn("ICMS a Recolher", nomes)
		self.assertIn("ICMS a Recuperar", nomes)

	def test_ibs_e_cbs_nao_tem_conta_a_recuperar(self):
		"""IBS/CBS são não cumulativos por design da reforma tributária (crédito amplo
		e imediato, sem a lógica de acúmulo que gera saldo credor a recuperar como
		ICMS/PIS/COFINS hoje) — só `a Recolher` e a dedução na receita."""
		nomes_ibs = {conta.nome for conta in contas_do_tributo("IBS")}
		nomes_cbs = {conta.nome for conta in contas_do_tributo("CBS")}

		for nomes in (nomes_ibs, nomes_cbs):
			self.assertFalse(any("Recuperar" in nome for nome in nomes))

	def test_retencoes_tem_lado_ativo_e_passivo(self):
		"""IRRF/CSRF/INSS são retenção na fonte — a mesma sigla aparece como ativo
		(quando o cliente retém da empresa) e como passivo (quando a empresa retém de
		um fornecedor), nunca só um lado."""
		for tributo in ("IRRF", "CSRF", "INSS"):
			with self.subTest(tributo=tributo):
				nomes = {conta.nome for conta in contas_do_tributo(tributo)}

				self.assertTrue(any("Compensar" in nome for nome in nomes))
				self.assertTrue(any("Recolher" in nome for nome in nomes))

	def test_tributo_desconhecido_devolve_lista_vazia_sem_levantar(self):
		self.assertEqual(contas_do_tributo("IPTU"), [])

	def test_simples_nacional_nao_e_amarrado_a_um_tributo_da_allowlist(self):
		"""Substitui os tributos individuais — não é o mesmo tributo que nenhum deles,
		por isso não carrega `tributo=` de nenhum item de TRIBUTOS_CONHECIDOS."""
		_root_type, passivo = next(item for item in ARVORE if item[0] == ROOT_TYPE_PASSIVO)
		circulante = next(f for f in passivo.filhas if f.nome == "Passivo Circulante")
		obrigacoes = next(f for f in circulante.filhas if f.nome == "Obrigações Tributárias")
		simples = next(f for f in obrigacoes.filhas if f.nome == "Simples Nacional a Recolher")

		self.assertEqual(simples.tributo, "")


if __name__ == "__main__":
	unittest.main()
