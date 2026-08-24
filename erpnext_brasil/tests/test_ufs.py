# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da resolução de UF a partir do campo livre `state`."""

import unittest

from erpnext_brasil.fiscal.ufs import SIGLAS, resolver_uf


class TestResolverUF(unittest.TestCase):
	def test_sigla_direta(self):
		self.assertEqual(resolver_uf("SP"), "SP")
		self.assertEqual(resolver_uf("sp"), "SP")
		self.assertEqual(resolver_uf(" rj "), "RJ")

	def test_nome_por_extenso_com_acento(self):
		self.assertEqual(resolver_uf("São Paulo"), "SP")
		self.assertEqual(resolver_uf("Espírito Santo"), "ES")
		self.assertEqual(resolver_uf("Goiás"), "GO")
		self.assertEqual(resolver_uf("Pará"), "PA")

	def test_nome_sem_acento_e_caixa_livre(self):
		self.assertEqual(resolver_uf("sao paulo"), "SP")
		self.assertEqual(resolver_uf("RIO GRANDE DO SUL"), "RS")
		self.assertEqual(resolver_uf("Sao  Paulo"), "SP")

	def test_distingue_mato_grosso_de_mato_grosso_do_sul(self):
		self.assertEqual(resolver_uf("Mato Grosso"), "MT")
		self.assertEqual(resolver_uf("Mato Grosso do Sul"), "MS")

	def test_distingue_rio_grande_do_norte_do_sul(self):
		self.assertEqual(resolver_uf("Rio Grande do Norte"), "RN")
		self.assertEqual(resolver_uf("Rio Grande do Sul"), "RS")

	def test_todas_as_27_siglas_resolvem_para_si_mesmas(self):
		for sigla in SIGLAS:
			with self.subTest(sigla=sigla):
				self.assertEqual(resolver_uf(sigla), sigla)

	def test_todos_os_nomes_por_extenso_resolvem(self):
		# Se um nome do mapa deixasse de resolver, a validação de IE daquela UF
		# silenciosamente pararia de rodar — falha invisível, então é testada.
		resolvidos = {resolver_uf(nome) for nome in _NOMES_POR_EXTENSO}
		self.assertEqual(resolvidos, set(SIGLAS))

	def test_valor_irreconhecivel_devolve_none(self):
		for entrada in (None, "", "   ", "Califórnia", "XX", "Estado Novo"):
			with self.subTest(entrada=entrada):
				self.assertIsNone(resolver_uf(entrada))


_NOMES_POR_EXTENSO = [
	"Acre",
	"Alagoas",
	"Amazonas",
	"Amapá",
	"Bahia",
	"Ceará",
	"Distrito Federal",
	"Espírito Santo",
	"Goiás",
	"Maranhão",
	"Minas Gerais",
	"Mato Grosso do Sul",
	"Mato Grosso",
	"Pará",
	"Paraíba",
	"Pernambuco",
	"Piauí",
	"Paraná",
	"Rio de Janeiro",
	"Rio Grande do Norte",
	"Rondônia",
	"Roraima",
	"Rio Grande do Sul",
	"Santa Catarina",
	"Sergipe",
	"São Paulo",
	"Tocantins",
]


if __name__ == "__main__":
	unittest.main()
