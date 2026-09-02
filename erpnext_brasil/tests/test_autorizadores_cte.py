# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/documento/autorizadores_cte.py`."""

import unittest

from erpnext_brasil.fiscal.documento.autorizadores_cte import (
	AUTORIZADOR_POR_UF,
	AutorizadorDesconhecido,
	endpoint,
)


class TestAutorizadorPorUf(unittest.TestCase):
	def test_cobre_as_27_ufs_mais_an(self):
		pseudo_entradas = {"SVRS", "SVSP"}
		ufs_reais = {sigla for sigla in AUTORIZADOR_POR_UF if sigla not in pseudo_entradas}
		self.assertEqual(len(ufs_reais), 28)
		self.assertIn("AN", ufs_reais)

	def test_ro_esta_no_grupo_svrs(self):
		self.assertEqual(AUTORIZADOR_POR_UF["RO"], "SVRS")

	def test_am_ba_go_divergem_da_nfe_e_caem_no_svrs(self):
		"""Achado real: AM/BA/GO têm webservice próprio na NF-e mas usam o
		autorizador compartilhado no CT-e."""
		self.assertEqual(AUTORIZADOR_POR_UF["AM"], "SVRS")
		self.assertEqual(AUTORIZADOR_POR_UF["BA"], "SVRS")
		self.assertEqual(AUTORIZADOR_POR_UF["GO"], "SVRS")

	def test_pe_diverge_da_nfe_e_cai_no_svsp(self):
		self.assertEqual(AUTORIZADOR_POR_UF["PE"], "SVSP")

	def test_seis_ufs_tem_webservice_proprio(self):
		"""SVRS/SVSP se automapeiam no JSON de origem (alias, não UF real) e AN só
		serve DistribuicaoDFe -- excluídos para isolar as UFs com webservice
		próprio de verdade."""
		nao_uf = {"SVRS", "SVSP", "AN"}
		proprios = {
			uf for uf, grupo in AUTORIZADOR_POR_UF.items() if grupo == uf and uf not in nao_uf
		}
		self.assertEqual(proprios, {"MG", "MS", "MT", "PR", "RS", "SP"})


class TestEndpoint(unittest.TestCase):
	def test_mg_producao(self):
		url = endpoint("MG", "CteRecepcao")
		self.assertEqual(url, "https://cte.fazenda.mg.gov.br/cte/services/CTeRecepcaoSincV4")

	def test_ro_resolve_pelo_grupo_svrs(self):
		url = endpoint("RO", "CteRecepcao")
		self.assertEqual(url, "https://cte.svrs.rs.gov.br/ws/CTeRecepcaoSincV4/CTeRecepcaoSincV4.asmx")

	def test_svrs_e_identico_ao_rs(self):
		self.assertEqual(endpoint("RO", "CteRecepcao"), endpoint("RS", "CteRecepcao"))

	def test_svsp_e_identico_ao_sp(self):
		self.assertEqual(endpoint("PE", "CteRecepcao"), endpoint("SP", "CteRecepcao"))

	def test_homologacao_diferente_de_producao(self):
		self.assertNotEqual(
			endpoint("MG", "CteRecepcao", ambiente="homologacao"), endpoint("MG", "CteRecepcao")
		)

	def test_uf_desconhecida_levanta_erro(self):
		with self.assertRaises(AutorizadorDesconhecido):
			endpoint("XX", "CteRecepcao")

	def test_ambiente_invalido_levanta_erro(self):
		with self.assertRaises(ValueError):
			endpoint("MG", "CteRecepcao", ambiente="teste")

	def test_servico_inexistente_no_grupo_devolve_none(self):
		"""AN só tem CTeDistribuicaoDFe -- não confunde com autorização."""
		self.assertIsNone(endpoint("AN", "CteRecepcao"))
		self.assertIsNotNone(endpoint("AN", "CTeDistribuicaoDFe"))


if __name__ == "__main__":
	unittest.main()
