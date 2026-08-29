# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da tabela de autorizadores da NF-e por UF.

O teste mais importante é o de Rondônia — prioridade de verificação confirmada pelo
usuário — seguido pelos dois casos em que o módulo se recusa a inventar dado: ambiente
de homologação e `NfeConsultaCadastro` para as 11 UFs do grupo SVRS que não o têm
confirmado.
"""

import unittest

from erpnext_brasil.fiscal.documento.autorizadores_sefaz import (
	AUTORIZADOR_POR_UF,
	UFS_COM_CONSULTA_CADASTRO_NO_SVRS,
	AutorizadorDesconhecido,
	endpoint,
)


class TestCoberturaDas27UFs(unittest.TestCase):
	def test_todas_as_27_estao_mapeadas(self):
		"""26 estados + DF."""
		self.assertEqual(len(AUTORIZADOR_POR_UF), 27)

	def test_dez_ufs_com_webservice_proprio(self):
		proprias = [uf for uf, grupo in AUTORIZADOR_POR_UF.items() if grupo == "PROPRIO"]

		self.assertEqual(
			sorted(proprias), ["AM", "BA", "GO", "MG", "MS", "MT", "PE", "PR", "RS", "SP"]
		)

	def test_apenas_ma_no_svan(self):
		svan = [uf for uf, grupo in AUTORIZADOR_POR_UF.items() if grupo == "SVAN"]

		self.assertEqual(svan, ["MA"])

	def test_dezesseis_ufs_no_svrs(self):
		svrs = [uf for uf, grupo in AUTORIZADOR_POR_UF.items() if grupo == "SVRS"]

		self.assertEqual(len(svrs), 16)


class TestRondonia(unittest.TestCase):
	"""RO é a UF de prioridade de verificação do usuário — não um caso qualquer."""

	def test_ro_esta_no_grupo_svrs(self):
		self.assertEqual(AUTORIZADOR_POR_UF["RO"], "SVRS")

	def test_ro_resolve_autorizacao(self):
		url = endpoint("RO", "NFeAutorizacao")

		self.assertEqual(url, "https://nfe.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx")

	def test_ro_resolve_todos_os_seis_servicos_confirmados(self):
		for servico in (
			"NFeAutorizacao",
			"NFeRetAutorizacao",
			"NfeConsultaProtocolo",
			"NfeStatusServico",
			"NfeInutilizacao",
			"RecepcaoEvento",
		):
			with self.subTest(servico=servico):
				self.assertIsNotNone(endpoint("RO", servico))

	def test_ro_nao_tem_consulta_cadastro_confirmada(self):
		"""A fonte só confirma CadConsultaCadastro do SVRS para AC/ES/RN/PB/SC."""
		self.assertIsNone(endpoint("RO", "NfeConsultaCadastro"))

	def test_ro_nao_esta_na_lista_de_excecao(self):
		self.assertNotIn("RO", UFS_COM_CONSULTA_CADASTRO_NO_SVRS)


class TestWebserviceProprio(unittest.TestCase):
	def test_sp(self):
		self.assertEqual(
			endpoint("SP", "NFeAutorizacao"), "https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx"
		)

	def test_todas_as_dez_tem_os_sete_servicos(self):
		proprias = [uf for uf, grupo in AUTORIZADOR_POR_UF.items() if grupo == "PROPRIO"]
		servicos = (
			"NFeAutorizacao", "NFeRetAutorizacao", "NfeConsultaProtocolo",
			"NfeStatusServico", "NfeConsultaCadastro", "NfeInutilizacao", "RecepcaoEvento",
		)  # fmt: skip

		for uf in proprias:
			for servico in servicos:
				with self.subTest(uf=uf, servico=servico):
					self.assertIsNotNone(endpoint(uf, servico))


class TestSVAN(unittest.TestCase):
	def test_ma_resolve_pelo_svan(self):
		self.assertEqual(
			endpoint("MA", "NFeAutorizacao"),
			"https://www.sefazvirtual.fazenda.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx",
		)

	def test_svan_nao_tem_consulta_cadastro(self):
		self.assertIsNone(endpoint("MA", "NfeConsultaCadastro"))


class TestExcecaoDeConsultaCadastro(unittest.TestCase):
	def test_as_cinco_ufs_resolvem(self):
		for uf in ("AC", "ES", "RN", "PB", "SC"):
			with self.subTest(uf=uf):
				self.assertIsNotNone(endpoint(uf, "NfeConsultaCadastro"))

	def test_as_onze_restantes_nao_resolvem(self):
		restantes = set(
			uf for uf, grupo in AUTORIZADOR_POR_UF.items() if grupo == "SVRS"
		) - UFS_COM_CONSULTA_CADASTRO_NO_SVRS

		self.assertEqual(len(restantes), 11)

		for uf in restantes:
			with self.subTest(uf=uf):
				self.assertIsNone(endpoint(uf, "NfeConsultaCadastro"))


class TestHomologacao(unittest.TestCase):
	"""Confirmada só para SVRS (que cobre RO), via segunda fonte independente."""

	def test_ro_resolve_homologacao(self):
		url = endpoint("RO", "NFeAutorizacao", ambiente="homologacao")

		self.assertEqual(
			url, "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx"
		)

	def test_homologacao_do_svrs_troca_o_host_mas_preserva_o_caminho(self):
		producao = endpoint("RO", "NfeStatusServico")
		homologacao = endpoint("RO", "NfeStatusServico", ambiente="homologacao")

		self.assertEqual(producao.split("/", 3)[-1], homologacao.split("/", 3)[-1])
		self.assertNotEqual(producao, homologacao)

	def test_grupo_sem_homologacao_confirmada_levanta_not_implemented(self):
		"""Não existe padrão de host confiável entre grupos — SP não pode herdar do SVRS."""
		with self.assertRaises(NotImplementedError) as ctx:
			endpoint("SP", "NFeAutorizacao", ambiente="homologacao")

		self.assertIn("não está confirmada", str(ctx.exception))

	def test_ma_svan_tambem_sem_homologacao_confirmada(self):
		with self.assertRaises(NotImplementedError):
			endpoint("MA", "NFeAutorizacao", ambiente="homologacao")


class TestValidacao(unittest.TestCase):
	def test_uf_desconhecida(self):
		with self.assertRaises(AutorizadorDesconhecido):
			endpoint("XX", "NFeAutorizacao")

	def test_ambiente_invalido(self):
		with self.assertRaises(ValueError):
			endpoint("SP", "NFeAutorizacao", ambiente="teste")

	def test_servico_desconhecido_devolve_none_em_vez_de_erro(self):
		"""Serviço que não existe na tabela é tratado como não confirmado, não crash."""
		self.assertIsNone(endpoint("SP", "ServicoQueNaoExiste"))

	def test_uf_minuscula_e_normalizada(self):
		self.assertEqual(endpoint("sp", "NFeAutorizacao"), endpoint("SP", "NFeAutorizacao"))


if __name__ == "__main__":
	unittest.main()
