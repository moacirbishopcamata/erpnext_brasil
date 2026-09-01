# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/mdfe.py` — montagem de `infDoc` do MDF-e."""

import unittest

from erpnext_brasil.fiscal.documento.chave_acesso import ChaveInvalida, montar_chave
from erpnext_brasil.fiscal.mdfe import MunicipioDescarga, montar_infdoc


def _chave(modelo: str, numero: str = "000000001") -> str:
	return montar_chave(
		uf="35",
		ano_mes="2608",
		cnpj="11222333000181",
		modelo=modelo,
		serie="001",
		numero=numero,
		tipo_emissao="1",
		codigo_numerico="12345678",
	)


class TestMontarInfdoc(unittest.TestCase):
	def test_um_municipio_com_cte_e_nfe(self):
		chave_cte = _chave("57")
		chave_nfe = _chave("55")
		municipio = MunicipioDescarga(
			codigo="3550308", nome="São Paulo", chaves_cte=[chave_cte], chaves_nfe=[chave_nfe]
		)

		grupo = montar_infdoc([municipio])

		infmun = grupo["infDoc"]["infMunDescarga"][0]
		self.assertEqual(infmun["cMunDescarga"], "3550308")
		self.assertEqual(infmun["xMunDescarga"], "São Paulo")
		self.assertEqual(infmun["infCTe"], [{"chCTe": chave_cte}])
		self.assertEqual(infmun["infNFe"], [{"chNFe": chave_nfe}])

	def test_grupo_ausente_quando_sem_chaves_daquele_tipo(self):
		municipio = MunicipioDescarga(codigo="3550308", nome="São Paulo", chaves_cte=[_chave("57")])

		infmun = montar_infdoc([municipio])["infDoc"]["infMunDescarga"][0]

		self.assertIn("infCTe", infmun)
		self.assertNotIn("infNFe", infmun)

	def test_varios_municipios_preserva_ordem(self):
		m1 = MunicipioDescarga(codigo="3550308", nome="São Paulo", chaves_nfe=[_chave("55", "000000001")])
		m2 = MunicipioDescarga(codigo="3304557", nome="Rio de Janeiro", chaves_nfe=[_chave("55", "000000002")])

		infmun = montar_infdoc([m1, m2])["infDoc"]["infMunDescarga"]

		self.assertEqual(infmun[0]["cMunDescarga"], "3550308")
		self.assertEqual(infmun[1]["cMunDescarga"], "3304557")

	def test_lista_vazia_de_municipios_levanta_erro(self):
		"""infMunDescarga não tem minOccurs=0 no XSD — pelo menos um é obrigatório."""
		with self.assertRaises(ValueError):
			montar_infdoc([])

	def test_recusa_chave_de_nfe_no_grupo_de_cte(self):
		municipio = MunicipioDescarga(codigo="3550308", nome="São Paulo", chaves_cte=[_chave("55")])

		with self.assertRaises(ChaveInvalida):
			montar_infdoc([municipio])

	def test_recusa_chave_de_cte_no_grupo_de_nfe(self):
		municipio = MunicipioDescarga(codigo="3550308", nome="São Paulo", chaves_nfe=[_chave("57")])

		with self.assertRaises(ChaveInvalida):
			montar_infdoc([municipio])


if __name__ == "__main__":
	unittest.main()
