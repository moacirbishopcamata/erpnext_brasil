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
	ENDPOINTS_NFCE,
	ENDPOINTS_NFCE_HOMOLOGACAO,
	UF_CONTINGENCIA_SVC,
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

	def test_todos_os_14_grupos_tem_homologacao_confirmada(self):
		"""Os 10 próprios + SVAN + SVRS (autorizadores normais) + SVC-AN + SVC-RS
		(contingência nacional) — nenhum grupo real ficou sem homologação."""
		self.assertEqual(len(ENDPOINTS_HOMOLOGACAO), 14)

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

	def test_modelo_invalido(self):
		with self.assertRaises(ValueError):
			endpoint("SP", "NFeAutorizacao", modelo="99")


class TestModeloNFCe(unittest.TestCase):
	"""Descoberto ao verificar o QR Code da NFC-e: a maioria dos grupos com webservice
	próprio, e o próprio SVRS (grupo de RO), rodam a NFC-e em host separado da NF-e."""

	def test_modelo_padrao_e_55(self):
		self.assertEqual(endpoint("SP", "NFeAutorizacao"), endpoint("SP", "NFeAutorizacao", modelo="55"))

	def test_ro_svrs_usa_host_nfce_diferente_de_nfe(self):
		nfe = endpoint("RO", "NFeAutorizacao", modelo="55")
		nfce = endpoint("RO", "NFeAutorizacao", modelo="65")

		self.assertIn("nfe.svrs.rs.gov.br", nfe)
		self.assertIn("nfce.svrs.rs.gov.br", nfce)
		self.assertNotEqual(nfe, nfce)

	def test_sp_usa_host_nfce_diferente_de_nfe(self):
		nfe = endpoint("SP", "NFeAutorizacao", modelo="55")
		nfce = endpoint("SP", "NFeAutorizacao", modelo="65")

		self.assertNotEqual(nfe, nfce)
		self.assertIn("nfce.", nfce)

	def test_go_bloco_proprio_com_mesmo_host_e_caminho_da_nfe(self):
		"""GO tem bloco próprio na fonte de NFC-e (não é ausência de dado), mas não
		separou infraestrutura por modelo — mesmo host/caminho da NF-e, só sem o sufixo
		'?wsdl' que a tabela de NF-e tem (confirmado byte a byte na fonte)."""
		self.assertIn("GO", ENDPOINTS_NFCE)
		nfe = endpoint("GO", "NFeAutorizacao", modelo="55")
		nfce = endpoint("GO", "NFeAutorizacao", modelo="65")

		self.assertEqual(nfce, "https://nfe.sefaz.go.gov.br/nfe/services/NFeAutorizacao4")
		self.assertEqual(nfe.split("?")[0], nfce)

	def test_ba_pe_svan_sem_bloco_proprio_caem_para_nfe(self):
		"""BA, PE e SVAN (MA) não têm bloco próprio na fonte de NFC-e — devolve o mesmo
		endpoint de NF-e, não None nem erro."""
		for uf in ("BA", "PE", "MA"):
			with self.subTest(uf=uf):
				nfe = endpoint(uf, "NFeAutorizacao", modelo="55")
				nfce = endpoint(uf, "NFeAutorizacao", modelo="65")

				self.assertEqual(nfe, nfce)
				self.assertIsNotNone(nfce)

	def test_nfeconsultacadastro_nunca_usa_tabela_de_nfce(self):
		"""Serviço agnóstico a modelo — sempre resolvido pela tabela de NF-e, mesmo que
		o grupo tenha tabela própria de NFC-e para os outros serviços."""
		self.assertEqual(
			endpoint("SP", "NfeConsultaCadastro", modelo="55"),
			endpoint("SP", "NfeConsultaCadastro", modelo="65"),
		)

	def test_homologacao_de_nfce_tambem_troca_o_host(self):
		producao = endpoint("RO", "NFeAutorizacao", ambiente="producao", modelo="65")
		homologacao = endpoint("RO", "NFeAutorizacao", ambiente="homologacao", modelo="65")

		self.assertIn("nfce.svrs.rs.gov.br", producao)
		self.assertIn("nfce-homologacao.svrs.rs.gov.br", homologacao)

	def test_todos_os_grupos_com_tabela_propria_tem_producao_e_homologacao(self):
		self.assertEqual(set(ENDPOINTS_NFCE), set(ENDPOINTS_NFCE_HOMOLOGACAO))

	def test_nove_grupos_tem_infraestrutura_propria_de_nfce(self):
		"""8 próprios (AM, GO, MG, MS, MT, PR, RS, SP) + SVRS — BA, PE e SVAN ficam de
		fora de propósito (sem bloco próprio na fonte)."""
		self.assertEqual(len(ENDPOINTS_NFCE), 9)


class TestContingenciaSVC(unittest.TestCase):
	"""SVC-AN/SVC-RS: contingência nacional exclusiva de NF-e (modelo 55) — nunca existe
	para NFC-e, que usa contingência offline (`tpEmis=9`) em vez disso."""

	def test_todas_as_27_ufs_estao_mapeadas_para_um_svc(self):
		self.assertEqual(len(UF_CONTINGENCIA_SVC), 27)

	def test_nenhuma_uf_cai_nos_dois_grupos(self):
		svcan = {uf for uf, grupo in UF_CONTINGENCIA_SVC.items() if grupo == "SVCAN"}
		svcrs = {uf for uf, grupo in UF_CONTINGENCIA_SVC.items() if grupo == "SVCRS"}

		self.assertEqual(svcan & svcrs, set())
		self.assertEqual(len(svcan), 19)
		self.assertEqual(len(svcrs), 8)

	def test_ro_usa_svcan(self):
		"""RO está no grupo SVRS (autorizador normal) — em contingência cai no SVC-AN,
		nunca no próprio SVC-RS (seria cair de volta na mesma infraestrutura)."""
		self.assertEqual(UF_CONTINGENCIA_SVC["RO"], "SVCAN")
		url = endpoint("RO", "NFeAutorizacao", modelo="55", contingencia=True)

		self.assertIn("sefazvirtual.fazenda.gov.br", url)

	def test_am_usa_svcrs_mesma_infraestrutura_do_svrs(self):
		"""AM tem webservice próprio como autorizador normal — em contingência cai no
		SVC-RS, que é byte a byte a infraestrutura do SVRS (RS), não a de AM."""
		self.assertEqual(UF_CONTINGENCIA_SVC["AM"], "SVCRS")
		normal = endpoint("AM", "NFeAutorizacao", modelo="55")
		contingencia = endpoint("AM", "NFeAutorizacao", modelo="55", contingencia=True)

		self.assertIn("nfe.svrs.rs.gov.br", contingencia)
		self.assertNotEqual(normal, contingencia)

	def test_svcrs_e_o_mesmo_dict_do_svrs(self):
		"""Não é coincidência de valor — é o mesmo objeto, confirmado byte a byte na
		fonte: se a URL do SVRS mudar, o SVC-RS muda junto."""
		self.assertIs(autorizadores_sefaz.ENDPOINTS["SVCRS"], autorizadores_sefaz.ENDPOINTS["SVRS"])
		self.assertIs(
			autorizadores_sefaz.ENDPOINTS_HOMOLOGACAO["SVCRS"], autorizadores_sefaz.ENDPOINTS_HOMOLOGACAO["SVRS"]
		)

	def test_contingencia_com_modelo_65_levanta_erro(self):
		"""NFC-e nunca usa SVC — pré-condição de DbC, não um caso silencioso."""
		with self.assertRaises(ValueError):
			endpoint("SP", "NFeAutorizacao", modelo="65", contingencia=True)

	def test_homologacao_em_contingencia(self):
		producao = endpoint("SP", "NFeAutorizacao", modelo="55", contingencia=True)
		homologacao = endpoint(
			"SP", "NFeAutorizacao", ambiente="homologacao", modelo="55", contingencia=True
		)

		self.assertIn("sefazvirtual.fazenda.gov.br", producao)
		self.assertIn("hom.sefazvirtual.fazenda.gov.br", homologacao)
		self.assertNotEqual(producao, homologacao)

	def test_uf_desconhecida_em_contingencia_levanta_autorizador_desconhecido(self):
		with self.assertRaises(AutorizadorDesconhecido):
			endpoint("XX", "NFeAutorizacao", modelo="55", contingencia=True)


if __name__ == "__main__":
	unittest.main()
