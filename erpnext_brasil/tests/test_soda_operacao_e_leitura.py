# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da conciliação, do diário, do executor de planos, da configuração e do leitor de identidade do Soda."""

import dataclasses
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from erpnext_brasil.persistencia.documentos import PersistenciaInvalida
from erpnext_brasil.persistencia.memoria import RepositorioEmMemoria
from erpnext_brasil.soda import configuracao as cfg
from erpnext_brasil.soda import leitura as lei
from erpnext_brasil.soda.conciliacao import FatosDaInstancia, conciliar, encontrar_orfaos
from erpnext_brasil.soda.diario import Diario, EstadoDaOperacao, Operacao
from erpnext_brasil.soda.modelo import Estado, Instancia
from erpnext_brasil.soda.plano import Passo, executar_plano
from erpnext_brasil.soda.portas import FaixaDePortas

UUID_A = "12345678-1234-4234-8234-123456789abc"


def instancia_em(estado: Estado) -> Instancia:
	return Instancia(
		uuid=UUID_A,
		descritivo="Homologação",
		host="homologacao-12345678.localhost",
		porta=8100,
		estado=estado,
		perfil_de_banco="padrao",
		tipo_de_banco="mariadb",
		aplicativos=("erpnext", "erpnext_brasil"),
		criada_em="2026-10-11T12:00:00+00:00",
	)


def fatos(**campos) -> FatosDaInstancia:
	return FatosDaInstancia(**campos)


class TestConciliacao(unittest.TestCase):
	def conciliar(self, estado, **campos):
		return conciliar(instancia_em(estado), fatos(**campos))

	def test_tabela_de_decisao(self):
		casos = [
			# estado, fatos, esperado, incerto
			(Estado.CRIANDO, dict(operacao_em_andamento=True), Estado.CRIANDO, False),
			(Estado.CRIANDO, dict(operacao_em_andamento=False), Estado.CRIACAO_INTERROMPIDA, False),
			(Estado.CRIANDO, dict(), Estado.CRIANDO, True),
			(Estado.CRIACAO_INTERROMPIDA, dict(processo_existe=True), Estado.CRIACAO_INTERROMPIDA, False),
			(Estado.PARADA, dict(processo_existe=False), Estado.PARADA, False),
			(Estado.PARADA, dict(processo_existe=True, porta_em_escuta=False), Estado.PARADA, False),
			(Estado.PARADA, dict(processo_existe=True, porta_em_escuta=True), Estado.NO_AR, False),
			(Estado.PARADA, dict(), Estado.PARADA, True),
			(Estado.NO_AR, dict(processo_existe=True, porta_em_escuta=True), Estado.NO_AR, False),
			(Estado.NO_AR, dict(processo_existe=True, porta_em_escuta=False), Estado.CAIU, False),
			(Estado.NO_AR, dict(processo_existe=True), Estado.NO_AR, True),
			(Estado.NO_AR, dict(processo_existe=False), Estado.CAIU, False),
			(Estado.NO_AR, dict(), Estado.NO_AR, True),
			(Estado.CAIU, dict(processo_existe=True, porta_em_escuta=True), Estado.NO_AR, False),
			(Estado.CAIU, dict(processo_existe=False), Estado.CAIU, False),
			(Estado.SUBINDO, dict(processo_existe=False), Estado.FALHOU_AO_SUBIR, False),
			(Estado.SUBINDO, dict(processo_existe=True, porta_em_escuta=True), Estado.NO_AR, False),
			(Estado.SUBINDO, dict(processo_existe=True, segundos_desde_o_inicio=10), Estado.SUBINDO, False),
			(
				Estado.SUBINDO,
				dict(processo_existe=True, segundos_desde_o_inicio=500),
				Estado.FALHOU_AO_SUBIR,
				False,
			),
			(Estado.SUBINDO, dict(processo_existe=True), Estado.SUBINDO, True),
			(Estado.FALHOU_AO_SUBIR, dict(processo_existe=True, porta_em_escuta=True), Estado.NO_AR, False),
			(Estado.FALHOU_AO_SUBIR, dict(processo_existe=False), Estado.FALHOU_AO_SUBIR, False),
		]

		for estado, campos, esperado, incerto in casos:
			with self.subTest(estado=estado.value, fatos=campos):
				resultado = self.conciliar(estado, **campos)
				self.assertEqual(resultado.estado, esperado)
				self.assertEqual(resultado.incerto, incerto)
				self.assertTrue(resultado.motivo)

	def test_fato_desconhecido_nunca_declara_queda(self):
		for estado in (Estado.NO_AR, Estado.CAIU, Estado.PARADA, Estado.SUBINDO):
			with self.subTest(estado=estado.value):
				resultado = self.conciliar(estado)
				self.assertEqual(resultado.estado, estado)
				self.assertTrue(resultado.incerto)

	def test_prazo_de_subida_e_configuravel(self):
		instancia = instancia_em(Estado.SUBINDO)
		campos = fatos(processo_existe=True, segundos_desde_o_inicio=30)

		self.assertEqual(conciliar(instancia, campos).estado, Estado.SUBINDO)
		self.assertEqual(conciliar(instancia, campos, prazo_de_subida=10).estado, Estado.FALHOU_AO_SUBIR)

	def test_site_ausente_vira_anomalia_sem_mudar_o_estado(self):
		resultado = self.conciliar(Estado.PARADA, processo_existe=False, site_presente=False)

		self.assertEqual(resultado.estado, Estado.PARADA)
		self.assertEqual(resultado.anomalias, ("o site da instância não está no bench",))

	def test_site_ausente_durante_a_criacao_e_normal(self):
		resultado = self.conciliar(Estado.CRIANDO, operacao_em_andamento=True, site_presente=False)
		self.assertEqual(resultado.anomalias, ())

	def test_toda_constatacao_e_uma_transicao_que_o_registro_aceita(self):
		from erpnext_brasil.soda.modelo import TRANSICOES, TRANSICOES_DA_CONCILIACAO

		for estado in Estado:
			for campos in (
				dict(),
				dict(processo_existe=True, porta_em_escuta=True),
				dict(processo_existe=True, porta_em_escuta=False),
				dict(processo_existe=False),
				dict(operacao_em_andamento=False),
				dict(processo_existe=True, segundos_desde_o_inicio=9999),
			):
				novo = self.conciliar(estado, **campos).estado

				with self.subTest(de=estado.value, para=novo.value, fatos=campos):
					self.assertTrue(
						novo == estado or novo in TRANSICOES[estado] | TRANSICOES_DA_CONCILIACAO[estado]
					)

	def test_orfaos_so_na_faixa_e_fora_do_registro(self):
		faixa = FaixaDePortas(8100, 8199)
		escutando = {
			8100: (111, "gunicorn"),
			8150: (222, "gunicorn"),
			8101: (None, "?"),
			9000: (333, "outro"),
		}

		orfaos = encontrar_orfaos(faixa, escutando, {8100})

		self.assertEqual(
			[(o.porta, o.pid, o.descricao) for o in orfaos], [(8101, None, "?"), (8150, 222, "gunicorn")]
		)

	def test_sem_orfaos(self):
		self.assertEqual(encontrar_orfaos(FaixaDePortas(8100, 8199), {}, set()), [])


def relogio():
	instante = [datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)]

	def agora():
		instante[0] += timedelta(seconds=1)

		return instante[0]

	return agora


def novo_diario(repo=None, dono=4242):
	ids = iter(f"op{n:02d}" for n in range(1000))

	return Diario(repo or RepositorioEmMemoria(), dono=dono, agora=relogio(), gerar_id=lambda: next(ids))


class TestDiario(unittest.TestCase):
	def test_abrir_registra_a_intencao_antes_de_qualquer_passo(self):
		diario = novo_diario()
		operacao = diario.abrir("criar", UUID_A, ("a", "b", "c"))

		self.assertEqual(operacao.estado, EstadoDaOperacao.EM_ANDAMENTO)
		self.assertEqual(operacao.proximo_passo, "a")
		self.assertEqual(diario.obter(operacao.id), operacao)
		self.assertEqual(diario.em_andamento(), [operacao])

	def test_passos_e_encerramento(self):
		diario = novo_diario()
		operacao = diario.abrir("criar", UUID_A, ("a", "b"))

		diario.passo_concluido(operacao.id, "a")
		repetido = diario.passo_concluido(operacao.id, "a")
		self.assertEqual(repetido.concluidos, ("a",), "passo repetido não duplica")
		self.assertEqual(repetido.proximo_passo, "b")

		diario.passo_concluido(operacao.id, "b")
		self.assertIsNone(diario.obter(operacao.id).proximo_passo)

		final = diario.encerrar(operacao.id, EstadoDaOperacao.CONCLUIDA)
		self.assertIsNotNone(final.terminada_em)
		self.assertEqual(diario.em_andamento(), [])

	def test_detalhe_e_limitado(self):
		diario = novo_diario()
		operacao = diario.abrir("criar", UUID_A, ("a",))
		final = diario.encerrar(operacao.id, EstadoDaOperacao.FALHOU, "x" * 5000)
		self.assertEqual(len(final.detalhe), 300)

	def test_relogio_padrao_e_utc_com_fuso(self):
		diario = Diario(RepositorioEmMemoria(), dono=1)
		operacao = diario.abrir("criar", "x", ("a",))
		self.assertIsNotNone(datetime.fromisoformat(operacao.iniciada_em).tzinfo)
		self.assertEqual(len(operacao.id), 16)

	def test_operacao_inexistente(self):
		diario = novo_diario()

		self.assertIsNone(diario.obter("nada"))

		with self.assertRaises(LookupError):
			diario.passo_concluido("nada", "a")

		with self.assertRaises(LookupError):
			diario.encerrar("nada", EstadoDaOperacao.FALHOU)

	def test_documento_vai_e_volta(self):
		operacao = novo_diario().abrir("criar", UUID_A, ("a",))
		self.assertEqual(Operacao.de_documento(operacao.para_documento()), operacao)

	def test_operacao_e_imutavel(self):
		operacao = novo_diario().abrir("criar", UUID_A, ("a",))

		with self.assertRaises(dataclasses.FrozenInstanceError):
			operacao.estado = EstadoDaOperacao.CONCLUIDA

	def test_listar_vem_em_ordem_de_inicio(self):
		diario = novo_diario()
		primeira = diario.abrir("criar", UUID_A, ("a",))
		segunda = diario.abrir("remover", UUID_A, ("a",))
		self.assertEqual([o.id for o in diario.listar()], [primeira.id, segunda.id])

	def test_interrompida_so_quando_o_dono_morreu(self):
		diario = novo_diario(dono=1)
		viva = diario.abrir("criar", "x", ("a", "b"))
		diario.passo_concluido(viva.id, "a")

		self.assertEqual(diario.marcar_interrompidas(lambda pid: True), [])
		self.assertEqual(diario.obter(viva.id).estado, EstadoDaOperacao.EM_ANDAMENTO)

		marcadas = diario.marcar_interrompidas(lambda pid: False)

		self.assertEqual([m.id for m in marcadas], [viva.id])
		self.assertEqual(marcadas[0].estado, EstadoDaOperacao.INTERROMPIDA)
		self.assertIn("último passo concluído: a", marcadas[0].detalhe)

	def test_interrompida_sem_nenhum_passo(self):
		diario = novo_diario()
		operacao = diario.abrir("criar", "x", ("a",))
		marcada = diario.marcar_interrompidas(lambda pid: False)[0]
		self.assertEqual(marcada.id, operacao.id)
		self.assertIn("nenhum", marcada.detalhe)

	def test_limitar_descarta_so_terminadas_antigas(self):
		diario = novo_diario()
		antigas = [diario.abrir("criar", "x", ("a",)) for _ in range(3)]

		for operacao in antigas:
			diario.encerrar(operacao.id, EstadoDaOperacao.CONCLUIDA)

		ativa = diario.abrir("criar", "x", ("a",))

		self.assertEqual(diario.limitar(manter=1), 2)
		self.assertEqual({o.id for o in diario.listar()}, {antigas[2].id, ativa.id})
		self.assertEqual(diario.limitar(manter=10), 0)

	def test_o_que_um_diario_grava_outro_le(self):
		with tempfile.TemporaryDirectory() as pasta:
			caminho = Path(pasta) / "registro.sqlite"
			gravador = novo_diario(cfg.fabrica.abrir(caminho, "sqlite"))
			operacao = gravador.abrir("criar", UUID_A, ("a",))

			leitor = novo_diario(cfg.fabrica.abrir(caminho, "sqlite"))

			self.assertEqual(leitor.obter(operacao.id), operacao)


class TestPlano(unittest.TestCase):
	def montar(self, falha_em=None, falha_ao_desfazer=()):
		eventos = []

		def passo(nome):
			def executar():
				eventos.append(f"+{nome}")

				if nome == falha_em:
					raise RuntimeError(f"{nome} quebrou")

			def desfazer():
				eventos.append(f"-{nome}")

				if nome in falha_ao_desfazer:
					raise OSError(f"{nome} não desfez")

			return Passo(nome, executar, desfazer)

		return eventos, [passo(n) for n in "abcde"]

	def test_tudo_certo(self):
		eventos, passos = self.montar()
		resultado = executar_plano(passos)

		self.assertTrue(resultado.ok)
		self.assertEqual(resultado.concluidos, tuple("abcde"))
		self.assertEqual(eventos, [f"+{n}" for n in "abcde"])

	def test_falha_no_terceiro_desfaz_em_ordem_inversa_inclusive_o_que_falhou(self):
		eventos, passos = self.montar(falha_em="c")
		resultado = executar_plano(passos)

		self.assertFalse(resultado.ok)
		self.assertEqual(resultado.falhou_em, "c")
		self.assertEqual(resultado.erro, "RuntimeError: c quebrou")
		self.assertEqual(resultado.concluidos, ("a", "b"))
		self.assertEqual(resultado.desfeitos, ("c", "b", "a"))
		self.assertEqual(eventos, ["+a", "+b", "+c", "-c", "-b", "-a"])

	def test_falha_ao_desfazer_nao_interrompe_os_demais_e_e_devolvida(self):
		eventos, passos = self.montar(falha_em="c", falha_ao_desfazer=("b",))
		resultado = executar_plano(passos)

		self.assertEqual(resultado.desfeitos, ("c", "a"))
		self.assertEqual(resultado.falhas_ao_desfazer, (("b", "OSError: b não desfez"),))
		self.assertIn("-a", eventos)

	def test_passo_sem_desfazer_e_pulado(self):
		rodou = []
		passos = [
			Passo("a", lambda: rodou.append("a")),
			Passo("b", lambda: (_ for _ in ()).throw(RuntimeError("x"))),
		]
		resultado = executar_plano(passos)
		self.assertEqual(resultado.desfeitos, ())
		self.assertEqual(resultado.falhou_em, "b")

	def test_cancelamento_desfaz_inclusive_o_passo_em_execucao_e_propaga(self):
		eventos = []

		def cancelar():
			eventos.append("+b")
			raise KeyboardInterrupt

		passos = [
			Passo("a", lambda: eventos.append("+a"), lambda: eventos.append("-a")),
			Passo("b", cancelar, lambda: eventos.append("-b")),
		]

		with self.assertRaises(KeyboardInterrupt):
			executar_plano(passos)

		self.assertEqual(eventos, ["+a", "+b", "-b", "-a"])

	def test_cancelamento_entre_passos_so_desfaz_os_concluidos(self):
		diario = novo_diario()
		eventos = []

		def cancelar_ao_concluir(identificador, passo):
			raise KeyboardInterrupt

		diario.passo_concluido = cancelar_ao_concluir
		passos = [Passo("a", lambda: eventos.append("+a"), lambda: eventos.append("-a"))]

		with self.assertRaises(KeyboardInterrupt):
			executar_plano(passos, diario=diario)

		self.assertEqual(eventos, ["+a", "-a"])
		self.assertEqual(diario.listar()[0].estado, EstadoDaOperacao.FALHOU)

	def test_diario_registra_intencao_passos_e_desfecho(self):
		diario = novo_diario()
		_, passos = self.montar()
		executar_plano(passos, diario=diario, tipo="criar", instancia=UUID_A)

		(operacao,) = diario.listar()
		self.assertEqual(operacao.estado, EstadoDaOperacao.CONCLUIDA)
		self.assertEqual(operacao.concluidos, tuple("abcde"))
		self.assertEqual((operacao.tipo, operacao.instancia), ("criar", UUID_A))

	def test_diario_registra_falha(self):
		diario = novo_diario()
		_, passos = self.montar(falha_em="c")
		executar_plano(passos, diario=diario)

		(operacao,) = diario.listar()
		self.assertEqual(operacao.estado, EstadoDaOperacao.FALHOU)
		self.assertEqual(operacao.concluidos, ("a", "b"))
		self.assertIn("falhou em c", operacao.detalhe)


def documento_de(uuid=UUID_A, descritivo="Homologação", porta=8100, **extra):
	base = {
		"uuid": uuid,
		"descritivo": descritivo,
		"host": f"h-{uuid[:8]}.localhost",
		"porta": porta,
		"estado": "parada",
		"perfil_de_banco": "padrao",
		"tipo_de_banco": "mariadb",
		"aplicativos": ["erpnext", "erpnext_brasil"],
		"criada_em": "2026-10-11T12:00:00+00:00",
	}
	base.update(extra)

	return base


class TestConfiguracao(unittest.TestCase):
	def setUp(self):
		self._t = tempfile.TemporaryDirectory()
		self.addCleanup(self._t.cleanup)
		self.pasta = Path(self._t.name) / "soda"
		self.pasta.mkdir()

	def test_padrao_sem_nada_e_json(self):
		self.assertEqual(cfg.ler_formato(self.pasta), "json")

	def test_formato_deduzido_do_arquivo_que_existe(self):
		cfg.fabrica.abrir(cfg.caminho_do_registro(self.pasta, "sqlite"), "sqlite").gravar("x", "k", {"a": 1})
		self.assertEqual(cfg.ler_formato(self.pasta), "sqlite")

	def test_dois_arquivos_sem_marcador_e_recusado(self):
		for formato in ("json", "sqlite"):
			cfg.fabrica.abrir(cfg.caminho_do_registro(self.pasta, formato), formato).gravar(
				"x", "k", {"a": 1}
			)

		with self.assertRaises(cfg.ConfiguracaoAmbigua):
			cfg.ler_formato(self.pasta)

	def test_marcador_decide_mesmo_com_os_dois_arquivos(self):
		for formato in ("json", "sqlite"):
			cfg.fabrica.abrir(cfg.caminho_do_registro(self.pasta, formato), formato).gravar(
				"x", "k", {"a": 1}
			)

		cfg.gravar_formato(self.pasta, "sqlite")
		self.assertEqual(cfg.ler_formato(self.pasta), "sqlite")

	def test_marcador_com_formato_desconhecido_e_recusado(self):
		(self.pasta / "formato").write_text("xml\n", encoding="utf-8")

		with self.assertRaises(PersistenciaInvalida):
			cfg.ler_formato(self.pasta)

		with self.assertRaises(PersistenciaInvalida):
			cfg.gravar_formato(self.pasta, "xml")

	def test_pasta_do_soda_fica_em_sites(self):
		self.assertEqual(cfg.pasta_do_soda(Path("/bench/sites")), Path("/bench/sites/soda"))

	def test_trocar_formato_preserva_os_dados_e_so_depois_grava_o_marcador(self):
		registro = cfg.abrir_registro(self.pasta, livre=lambda p: True)
		criada = registro.criar("Homologação", perfil_de_banco="padrao", tipo_de_banco="mariadb")

		resultado = cfg.trocar_formato_do_registro(self.pasta, "sqlite")

		self.assertGreater(resultado.total, 0)
		self.assertEqual(cfg.ler_formato(self.pasta), "sqlite")
		self.assertEqual(cfg.abrir_registro(self.pasta).obter(criada.uuid), criada)
		self.assertTrue(cfg.caminho_do_registro(self.pasta, "json").exists(), "o anterior fica ao lado")

	def test_trocar_para_o_mesmo_formato_e_recusado(self):
		cfg.abrir_registro(self.pasta, livre=lambda p: True).criar(
			"Homologação", perfil_de_banco="padrao", tipo_de_banco="mariadb"
		)

		with self.assertRaises(PersistenciaInvalida):
			cfg.trocar_formato_do_registro(self.pasta, "json")

	def test_trocar_para_formato_desconhecido(self):
		with self.assertRaises(PersistenciaInvalida):
			cfg.trocar_formato_do_registro(self.pasta, "xml")

	def test_falha_na_troca_nao_muda_o_marcador(self):
		# nada a migrar: a origem não existe
		with self.assertRaises(PersistenciaInvalida):
			cfg.trocar_formato_do_registro(self.pasta, "sqlite")

		self.assertEqual(cfg.ler_formato(self.pasta), "json")
		self.assertFalse((self.pasta / "formato").exists())

	def test_repositorio_somente_leitura_em_sqlite(self):
		cfg.abrir_registro(self.pasta, livre=lambda p: True).criar(
			"Homologação", perfil_de_banco="padrao", tipo_de_banco="mariadb"
		)
		cfg.trocar_formato_do_registro(self.pasta, "sqlite")

		repo = cfg.abrir_repositorio(self.pasta, somente_leitura=True)

		self.assertEqual(len(repo.listar("instancias")), 1)


class TestLeituraTolerante(unittest.TestCase):
	def test_documento_que_nao_e_objeto_e_pulado(self):
		instancia, aviso = lei._ler_instancia("k", "texto")
		self.assertIsNone(instancia)
		self.assertIn("não é um objeto", aviso)

	def test_busca_por_descritivo_ignora_gravado_invalido_e_acha_o_valido(self):
		repo = RepositorioEmMemoria()
		repo.gravar(
			"instancias", "curta", documento_de(uuid="87654321-4321-4321-8321-cba987654321", descritivo="ab")
		)
		repo.gravar("instancias", UUID_A, documento_de())
		leitor = lei.LeitorDeInstancias(repo)

		self.assertEqual(leitor.por_descritivo("Homologação").uuid, UUID_A)
		self.assertIsNone(leitor.por_descritivo("Outra coisa"))


class TestIdentidadeDoSite(unittest.TestCase):
	def test_chaves_vao_e_voltam(self):
		chaves = lei.chaves_para_site_config(UUID_A.upper(), "Homologação")

		self.assertEqual(set(chaves), set(lei.CHAVES_PROTEGIDAS))
		identidade = lei.identidade_do_site(chaves)
		self.assertEqual((identidade.uuid, identidade.descritivo), (UUID_A, "Homologação"))

	def test_site_que_nao_e_de_instancia(self):
		self.assertIsNone(lei.identidade_do_site({}))
		self.assertIsNone(lei.identidade_do_site({lei.CHAVE_UUID: "lixo"}))

	def test_descritivo_ausente_ou_estranho_vira_vazio(self):
		self.assertEqual(lei.identidade_do_site({lei.CHAVE_UUID: UUID_A}).descritivo, "")
		self.assertEqual(
			lei.identidade_do_site({lei.CHAVE_UUID: UUID_A, lei.CHAVE_DESCRITIVO: 5}).descritivo, ""
		)


class ContratoDoLeitor:
	"""Paridade: o leitor devolve o mesmo para JSON e SQLite."""

	FORMATO = ""

	def setUp(self):
		self._t = tempfile.TemporaryDirectory()
		self.addCleanup(self._t.cleanup)
		self.pasta = Path(self._t.name)
		(self.pasta / "formato").write_text(self.FORMATO + "\n", encoding="utf-8")
		self.repo = cfg.abrir_repositorio(self.pasta)
		self.leitor = lei.LeitorDeInstancias.abrir(self.pasta)

	def gravar(self, colecao, chave, documento):
		self.repo.gravar(colecao, chave, documento)

	def test_o_que_o_registro_grava_o_leitor_le(self):
		registro = cfg.abrir_registro(self.pasta, livre=lambda p: True)
		criada = registro.criar("Homologação", perfil_de_banco="padrao", tipo_de_banco="postgres")

		leitura = self.leitor.ler()

		(lida,) = leitura.instancias
		self.assertEqual(
			(lida.uuid, lida.descritivo, lida.host, lida.porta, lida.estado, lida.tipo_de_banco),
			(criada.uuid, "Homologação", criada.host, criada.porta, "criando", "postgres"),
		)
		self.assertEqual(lida.abreviado, criada.abreviado)
		self.assertFalse(leitura.mais_nova)
		self.assertFalse(leitura.ilegivel)
		self.assertEqual(leitura.avisos, ())
		self.assertEqual(self.leitor.por_uuid(criada.uuid.upper()), lida)
		self.assertEqual(self.leitor.por_descritivo("HOMOLOGACAO"), lida)
		self.assertEqual(self.leitor.por_site(criada.host), lida)

	def test_aposentadas_aparecem(self):
		registro = cfg.abrir_registro(self.pasta, livre=lambda p: True)
		criada = registro.criar("Antiga", perfil_de_banco="padrao", tipo_de_banco="mariadb")
		registro.mudar_estado(criada.uuid, Estado.PARADA)
		registro.aposentar(criada.uuid)

		leitura = self.leitor.ler()

		self.assertEqual(leitura.instancias, ())
		self.assertEqual([a.uuid for a in leitura.aposentadas], [criada.uuid])

	def test_registro_vazio(self):
		leitura = self.leitor.ler()
		self.assertEqual((leitura.instancias, leitura.aposentadas, leitura.avisos), ((), (), ()))
		self.assertIsNone(self.leitor.por_uuid(UUID_A))
		self.assertIsNone(self.leitor.por_uuid("lixo"))
		self.assertIsNone(self.leitor.por_descritivo("ab"))
		self.assertIsNone(self.leitor.por_descritivo("Qualquer"))
		self.assertIsNone(self.leitor.por_site("x.localhost"))

	def test_campo_novo_e_estado_novo_nao_quebram_o_leitor(self):
		self.gravar("instancias", UUID_A, documento_de(estado="hibernando", campo_do_futuro={"a": 1}))

		(lida,) = self.leitor.ler().instancias

		self.assertEqual(lida.estado, "hibernando")

	def test_instancia_ruim_e_pulada_com_aviso_e_as_boas_continuam(self):
		self.gravar("instancias", "ruim1", {"uuid": "lixo"})
		self.gravar("instancias", "ruim2", documento_de(porta="8100"))
		self.gravar("instancias", "ruim3", documento_de(descritivo=""))
		self.gravar("instancias", "ruim4", documento_de(porta=True))
		self.gravar("instancias", UUID_A, documento_de())

		leitura = self.leitor.ler()

		self.assertEqual([i.uuid for i in leitura.instancias], [UUID_A])
		self.assertEqual(len(leitura.avisos), 4)

	def test_instancia_que_nao_e_objeto_e_pulada(self):
		self.gravar("instancias", "x", {"uuid": None})
		self.assertEqual(len(self.leitor.ler().avisos), 1)

	def test_aposentada_malformada_e_pulada(self):
		self.gravar("aposentadas", "ruim", {"uuid": "lixo"})
		self.gravar(
			"aposentadas", "boa", {"uuid": UUID_A, "ultimo_descritivo": "Velha", "aposentada_em": "2026"}
		)

		leitura = self.leitor.ler()

		self.assertEqual([a.ultimo_descritivo for a in leitura.aposentadas], ["Velha"])
		self.assertEqual(len(leitura.avisos), 1)

	def test_esquema_mais_novo_le_o_que_da_e_avisa(self):
		self.gravar("instancias", UUID_A, documento_de())
		self.gravar("meta", "esquema", {"versao_esquema": 99})

		leitura = self.leitor.ler()

		self.assertTrue(leitura.mais_nova)
		self.assertEqual(leitura.versao_do_esquema, 99)
		self.assertEqual(len(leitura.instancias), 1)
		self.assertTrue(any("99" in a for a in leitura.avisos))

	def test_versao_de_esquema_ilegivel_vira_a_conhecida_com_aviso(self):
		self.gravar("meta", "esquema", {"versao_esquema": "dois"})

		leitura = self.leitor.ler()

		self.assertFalse(leitura.mais_nova)
		self.assertEqual(len(leitura.avisos), 1)

	def test_leitor_nao_tem_operacao_de_escrita(self):
		for nome in ("gravar", "remover", "transacao", "criar", "mudar_estado"):
			self.assertFalse(hasattr(self.leitor, nome), nome)

	def test_leitura_durante_escrita_nunca_ve_arquivo_pela_metade(self):
		import threading

		parar = threading.Event()
		erros = []

		def escrever():
			registro = cfg.abrir_registro(self.pasta, livre=lambda p: True)

			for n in range(25):
				try:
					registro.criar(f"Instância {n}", perfil_de_banco="padrao", tipo_de_banco="mariadb")
				except Exception as erro:
					erros.append(repr(erro))

			parar.set()

		fio = threading.Thread(target=escrever)
		fio.start()
		leituras = 0

		while not parar.is_set():
			leitura = self.leitor.ler()
			leituras += 1

			if leitura.ilegivel or leitura.avisos:
				erros.append(f"leitura inconsistente: {leitura.avisos}")

		fio.join()

		self.assertEqual(erros, [])
		self.assertGreater(leituras, 0)
		self.assertEqual(len(self.leitor.ler().instancias), 25)


class TestLeitorEmJson(ContratoDoLeitor, unittest.TestCase):
	FORMATO = "json"

	def test_arquivo_corrompido_devolve_leitura_ilegivel(self):
		self.gravar("instancias", UUID_A, documento_de())
		cfg.caminho_do_registro(self.pasta, "json").write_text("{ isto não é json", encoding="utf-8")

		leitura = lei.LeitorDeInstancias.abrir(self.pasta).ler()

		self.assertTrue(leitura.ilegivel)
		self.assertEqual(leitura.instancias, ())
		self.assertEqual(len(leitura.avisos), 1)


class TestLeitorEmSqlite(ContratoDoLeitor, unittest.TestCase):
	FORMATO = "sqlite"


if __name__ == "__main__":
	unittest.main()
