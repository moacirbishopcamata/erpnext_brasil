# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da tabela de autorizadores da NF-e por UF.

O teste mais importante é o de Rondônia — prioridade de verificação confirmada pelo
usuário. Depois vêm os casos em que o módulo se recusa a inventar dado: `NfeConsultaCadastro`
para as 11 UFs do grupo SVRS que não o têm confirmado, e o mesmo serviço para AM/SVAN em
homologação (confirmado o grupo, não confirmado esse serviço específico dentro dele).
"""

import unittest
from unittest.mock import patch

from erpnext_brasil.fiscal.documento import autorizadores_sefaz
from erpnext_brasil.fiscal.documento.autorizadores_sefaz import (
	AUTORIZADOR_POR_UF,
	ENDPOINTS_HOMOLOGACAO,
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
	"""Confirmada para os três grupos (própria UF × 10, SVAN, SVRS) — os 12 grupos que
	existem em `AUTORIZADOR_POR_UF`, via segunda fonte independente, com PR e SP
	checados por uma terceira (página oficial de cada estado)."""

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

	def test_nao_ha_padrao_de_host_entre_grupos(self):
		"""Cada grupo trocou o nome do host de um jeito diferente — SVRS insere um
		hífen, GO troca a palavra inteira, AM abrevia sem hífen. Prova, com os dados
		reais, que inferir por padrão teria acertado no máximo por coincidência."""
		casos = {
			"RO": ("nfe.svrs.rs.gov.br", "nfe-homologacao.svrs.rs.gov.br"),
			"GO": ("nfe.sefaz.go.gov.br", "homolog.sefaz.go.gov.br"),
			"AM": ("nfe.sefaz.am.gov.br", "homnfe.sefaz.am.gov.br"),
		}

		for uf, (host_producao, host_homologacao) in casos.items():
			with self.subTest(uf=uf):
				self.assertIn(host_producao, endpoint(uf, "NFeAutorizacao"))
				self.assertIn(
					host_homologacao, endpoint(uf, "NFeAutorizacao", ambiente="homologacao")
				)

	def test_todos_os_12_grupos_tem_homologacao_confirmada(self):
		"""Os 10 próprios + SVAN + SVRS — nenhum grupo real ficou sem homologação."""
		self.assertEqual(len(ENDPOINTS_HOMOLOGACAO), 12)

	def test_cadconsultacadastro_de_am_e_svan_fica_de_fora_de_proposito(self):
		"""A mesma fonte lista o elemento do serviço para AM/SVAN, mas sem URL dentro
		— ausência real na fonte, tratada como não confirmada (`None`), não como
		grupo inteiro sem homologação."""
		self.assertIsNone(endpoint("AM", "NfeConsultaCadastro", ambiente="homologacao"))
		self.assertIsNone(endpoint("MA", "NfeConsultaCadastro", ambiente="homologacao"))

	def test_grupo_sem_homologacao_confirmada_levanta_not_implemented(self):
		"""Guarda de código para um grupo hipotético ainda não confirmado — hoje todos
		os 12 grupos reais estão cobertos, então o cenário é forçado via patch, não com
		um UF de verdade (não existe mais nenhum)."""
		tabela_sem_sp = {k: v for k, v in ENDPOINTS_HOMOLOGACAO.items() if k != "SP"}

		with patch.object(autorizadores_sefaz, "ENDPOINTS_HOMOLOGACAO", tabela_sem_sp):
			with self.assertRaises(NotImplementedError) as ctx:
				endpoint("SP", "NFeAutorizacao", ambiente="homologacao")

		self.assertIn("não está confirmada", str(ctx.exception))


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
