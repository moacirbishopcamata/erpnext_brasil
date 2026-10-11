# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes dos perfis de banco: modelo, regras do repositório (nos três formatos), adoção, leitor e uso pelo Soda."""

import dataclasses
import json
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path

from erpnext_brasil.bancos import perfis as leitura
from erpnext_brasil.bancos.modelo import PerfilDeBanco, PerfilInvalido, UltimoTeste, chave_do_nome
from erpnext_brasil.bancos.repositorio import (
	NomeRepetido,
	PerfilEmUso,
	PerfilInexistente,
	PerfisDeBanco,
	PerfisMaisNovos,
	SemPadrao,
	Uso,
	adotar_configuracao_existente,
)
from erpnext_brasil.bancos.uso import usos_pelas_instancias
from erpnext_brasil.persistencia import fabrica
from erpnext_brasil.persistencia.memoria import RepositorioEmMemoria
from erpnext_brasil.soda.leitura import LeitorDeInstancias
from erpnext_brasil.soda.modelo import Estado
from erpnext_brasil.soda.registro import Registro

AGORA = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)
SENHA = "s3nh4-Secreta-do-root"


class TestModelo(unittest.TestCase):
	def test_porta_padrao_por_tipo(self):
		self.assertEqual(PerfilDeBanco("a", "mariadb").porta, 3306)
		self.assertEqual(PerfilDeBanco("b", "postgres").porta, 5432)

	def test_perfil_vai_e_volta_pelo_documento(self):
		perfil = PerfilDeBanco(
			"pg", "postgres", "db.local", 5433, "postgres", True, UltimoTeste("2026", "tcp", True)
		)
		self.assertEqual(PerfilDeBanco.de_documento(perfil.para_documento()), perfil)

	def test_nao_existe_campo_de_senha(self):
		nomes = {campo.name for campo in dataclasses.fields(PerfilDeBanco)}
		self.assertFalse({n for n in nomes if "senha" in n or "password" in n})

	def test_senha_gravada_a_mao_nao_entra_no_objeto(self):
		documento = PerfilDeBanco("a", "mariadb").para_documento() | {"senha": SENHA, "root_password": SENHA}
		perfil = PerfilDeBanco.de_documento(documento)
		self.assertNotIn(SENHA, repr(perfil))
		self.assertNotIn(SENHA, json.dumps(perfil.para_documento()))

	def test_perfil_e_imutavel(self):
		with self.assertRaises(dataclasses.FrozenInstanceError):
			PerfilDeBanco("a", "mariadb").host = "outro"

	def test_entradas_invalidas(self):
		casos = {
			"nome vazio": dict(nome="", tipo="mariadb"),
			"nome com espaço": dict(nome="meu perfil", tipo="mariadb"),
			"nome com acento": dict(nome="padrão", tipo="mariadb"),
			"nome grande": dict(nome="a" * 61, tipo="mariadb"),
			"nome não texto": dict(nome=None, tipo="mariadb"),
			"tipo desconhecido": dict(nome="a", tipo="oracle"),
			"porta zero é o padrão, negativa não": dict(nome="a", tipo="mariadb", porta=-1),
			"porta grande": dict(nome="a", tipo="mariadb", porta=70000),
			"porta texto": dict(nome="a", tipo="mariadb", porta="3306"),
			"porta bool": dict(nome="a", tipo="mariadb", porta=True),
			"host vazio": dict(nome="a", tipo="mariadb", host="  "),
			"host com símbolo": dict(nome="a", tipo="mariadb", host="db;rm -rf"),
			"host não texto": dict(nome="a", tipo="mariadb", host=5),
			"usuário com símbolo": dict(nome="a", tipo="mariadb", usuario_root="root'--"),
			"host enorme": dict(nome="a", tipo="mariadb", host="h" * 300),
		}

		for nome, argumentos in casos.items():
			with self.subTest(caso=nome), self.assertRaises(PerfilInvalido):
				PerfilDeBanco(**argumentos)

	def test_host_e_usuario_sao_aparados_e_usuario_pode_ser_vazio(self):
		perfil = PerfilDeBanco("a", "mariadb", "  db.local ", usuario_root="  root ")
		self.assertEqual((perfil.host, perfil.usuario_root), ("db.local", "root"))
		self.assertEqual(PerfilDeBanco("b", "mariadb").usuario_root, "")

	def test_chave_ignora_caixa(self):
		self.assertEqual(chave_do_nome("Local-PG"), "local-pg")
		self.assertEqual(PerfilDeBanco("MariaDB", "mariadb").chave, "mariadb")

	def test_chaves_do_common_site_config_nunca_levam_senha(self):
		chaves = PerfilDeBanco("a", "postgres", "db.local", 5433, "postgres").chaves_common_config()
		self.assertEqual(
			chaves, {"db_type": "postgres", "db_host": "db.local", "db_port": 5433, "root_login": "postgres"}
		)
		self.assertEqual(PerfilDeBanco("b", "mariadb").chaves_common_config().keys() & {"root_login"}, set())
		self.assertNotIn("root_password", chaves)

	def test_servidor_identifica_tipo_host_e_porta(self):
		self.assertEqual(PerfilDeBanco("a", "mariadb", "h", 1).servidor, ("mariadb", "h", 1))

	def test_documentos_malformados(self):
		ruins = [
			"texto",
			{"nome": "a", "tipo": "mariadb", "host": "h", "porta": "3306"},
			{"nome": "a", "tipo": "mariadb", "host": "h", "porta": True},
			{"nome": "a", "tipo": "oracle", "host": "h", "porta": 1},
			{"nome": "a", "tipo": "mariadb", "host": "h", "porta": 1, "ultimo_teste": "x"},
			{
				"nome": "a",
				"tipo": "mariadb",
				"host": "h",
				"porta": 1,
				"ultimo_teste": {"quando": "", "nivel": "tcp", "ok": True},
			},
			{
				"nome": "a",
				"tipo": "mariadb",
				"host": "h",
				"porta": 1,
				"ultimo_teste": {"quando": "x", "nivel": "tcp", "ok": "sim"},
			},
		]

		for ruim in ruins:
			with self.subTest(ruim=str(ruim)[:60]), self.assertRaises(PerfilInvalido):
				PerfilDeBanco.de_documento(ruim)

	def test_padrao_so_vale_se_for_verdadeiro_de_fato(self):
		base = PerfilDeBanco("a", "mariadb").para_documento()
		self.assertFalse(PerfilDeBanco.de_documento(base | {"padrao": "true"}).padrao)


class ContratoDosPerfis:
	def novo_repositorio(self):
		raise NotImplementedError

	def reabrir_repositorio(self):
		raise NotImplementedError

	def novos_perfis(self, repositorio=None, **opcoes):
		opcoes.setdefault("agora", lambda: AGORA)

		return PerfisDeBanco(repositorio or self.repo, **opcoes)

	def setUp(self):
		self.repo = self.novo_repositorio()
		self.publicados = []
		self.perfis = self.novos_perfis(publicar_padrao=self.publicados.append)

	def test_dois_perfis_no_mesmo_bench(self):
		maria = self.perfis.criar("maria", "mariadb")
		pg = self.perfis.criar("pg", "postgres", "db.local", 5433, "postgres")

		self.assertEqual([p.nome for p in self.perfis.listar()], ["maria", "pg"])
		self.assertEqual((maria.tipo, pg.tipo, pg.host, pg.porta), ("mariadb", "postgres", "db.local", 5433))

	def test_o_que_um_grava_o_outro_le(self):
		criado = self.perfis.criar("pg", "postgres")

		self.assertEqual(self.novos_perfis(self.reabrir_repositorio()).obter("PG"), criado)

	def test_o_primeiro_perfil_e_o_padrao_e_e_publicado(self):
		primeiro = self.perfis.criar("maria", "mariadb")
		segundo = self.perfis.criar("pg", "postgres")

		self.assertTrue(primeiro.padrao)
		self.assertFalse(segundo.padrao)
		self.assertEqual(self.publicados, [primeiro])

	def test_exatamente_um_padrao_depois_de_cada_operacao(self):
		def padroes():
			return [p.nome for p in self.perfis.listar() if p.padrao]

		self.perfis.criar("a", "mariadb")
		self.assertEqual(padroes(), ["a"])
		self.perfis.criar("b", "postgres")
		self.assertEqual(padroes(), ["a"])
		self.perfis.definir_padrao("b")
		self.assertEqual(padroes(), ["b"])
		self.perfis.definir_padrao("B")
		self.assertEqual(padroes(), ["b"])
		self.perfis.remover("a")
		self.assertEqual(padroes(), ["b"])

	def test_troca_do_padrao_publica_o_novo(self):
		self.perfis.criar("maria", "mariadb")
		self.perfis.criar("pg", "postgres", "db.local", 5433, "postgres")
		novo = self.perfis.definir_padrao("pg")

		self.assertEqual(self.publicados[-1], novo)
		self.assertEqual(self.publicados[-1].chaves_common_config()["db_type"], "postgres")
		self.assertEqual(self.perfis.padrao().nome, "pg")

	def test_nome_repetido_so_na_caixa_e_recusado_e_informa_o_existente(self):
		original = self.perfis.criar("Maria", "mariadb")

		with self.assertRaises(NomeRepetido) as contexto:
			self.perfis.criar("MARIA", "postgres")

		self.assertEqual(contexto.exception.existente, original)
		self.assertEqual(len(self.perfis.listar()), 1)

	def test_perfil_inexistente(self):
		for operacao in (
			lambda: self.perfis.definir_padrao("x"),
			lambda: self.perfis.remover("x"),
			lambda: self.perfis.alterar("x", host="h"),
			lambda: self.perfis.registrar_teste("x", ok=True, nivel="tcp"),
		):
			with self.subTest(), self.assertRaises(PerfilInexistente):
				operacao()

		self.assertIsNone(self.perfis.obter("x"))

	def test_remover_o_padrao_com_outros_perfis_e_recusado(self):
		self.perfis.criar("a", "mariadb")
		self.perfis.criar("b", "postgres")

		with self.assertRaises(SemPadrao):
			self.perfis.remover("a")

		self.perfis.remover("b")
		self.perfis.remover("a")  # o único perfil pode sair
		self.assertEqual(self.perfis.listar(), [])
		self.assertIsNone(self.perfis.padrao())

	def test_alterar_muda_so_o_pedido_e_republica_se_for_o_padrao(self):
		self.perfis.criar("a", "mariadb")
		alterado = self.perfis.alterar("a", host="db.local", usuario_root="admin")

		self.assertEqual((alterado.host, alterado.usuario_root, alterado.porta), ("db.local", "admin", 3306))
		self.assertEqual(self.publicados[-1], alterado)

	def test_alterar_perfil_que_nao_e_padrao_nao_publica(self):
		self.perfis.criar("a", "mariadb")
		self.perfis.criar("b", "postgres")
		antes = len(self.publicados)
		self.perfis.alterar("b", host="outro")
		self.assertEqual(len(self.publicados), antes)

	def test_alterar_com_valor_invalido_nao_grava(self):
		original = self.perfis.criar("a", "mariadb")

		with self.assertRaises(PerfilInvalido):
			self.perfis.alterar("a", porta=70000)

		self.assertEqual(self.perfis.obter("a"), original)

	def test_resultado_do_teste_e_guardado_sem_senha(self):
		self.perfis.criar("a", "mariadb")
		testado = self.perfis.registrar_teste("a", ok=True, nivel="autenticacao")

		self.assertEqual(testado.ultimo_teste, UltimoTeste(AGORA.isoformat(), "autenticacao", True))
		self.assertEqual(
			self.novos_perfis(self.reabrir_repositorio()).obter("a").ultimo_teste, testado.ultimo_teste
		)

	def test_trocar_o_servidor_zera_o_teste_antigo(self):
		self.perfis.criar("a", "mariadb")
		self.perfis.registrar_teste("a", ok=True, nivel="tcp")

		self.assertIsNone(self.perfis.alterar("a", host="outro.local").ultimo_teste)
		self.perfis.registrar_teste("a", ok=True, nivel="tcp")
		self.assertIsNotNone(self.perfis.alterar("a", usuario_root="admin").ultimo_teste)

	def test_perfil_em_uso_nao_e_removido_nem_muda_de_servidor(self):
		usos = [Uso("Homologação", "12345678"), Uso("Treino", "87654321")]
		perfis = self.novos_perfis(usos=lambda nome: usos if nome == "a" else ())
		perfis.criar("a", "mariadb")
		perfis.criar("b", "postgres")
		perfis.definir_padrao("b")

		with self.assertRaises(PerfilEmUso) as contexto:
			perfis.remover("a")

		self.assertIn("Homologação (12345678)", str(contexto.exception))
		self.assertIn("Treino (87654321)", str(contexto.exception))
		self.assertEqual(contexto.exception.usos, tuple(usos))

		for mudanca in (dict(tipo="postgres"), dict(host="outro"), dict(porta=3307)):
			with self.subTest(mudanca=mudanca), self.assertRaises(PerfilEmUso):
				perfis.alterar("a", **mudanca)

		self.assertEqual(
			perfis.alterar("a", usuario_root="admin").usuario_root, "admin"
		)  # sem trocar o servidor
		self.assertIsNotNone(perfis.obter("a"))

	def test_perfis_mais_novos_sao_lidos_e_nunca_gravados(self):
		criado = self.perfis.criar("a", "mariadb")
		self.repo.gravar("meta", "esquema", {"versao_esquema": 99})

		self.assertEqual(self.perfis.obter("a"), criado)

		for operacao in (
			lambda: self.perfis.criar("b", "mariadb"),
			lambda: self.perfis.alterar("a", host="x"),
			lambda: self.perfis.definir_padrao("a"),
			lambda: self.perfis.remover("a"),
			lambda: self.perfis.registrar_teste("a", ok=True, nivel="tcp"),
		):
			with self.subTest(), self.assertRaises(PerfisMaisNovos):
				operacao()

	def test_versao_de_esquema_ilegivel_vira_a_conhecida(self):
		self.repo.gravar("meta", "esquema", {"versao_esquema": "dois"})
		self.assertEqual(self.perfis.versao_do_esquema(), 1)

	def test_relogio_padrao_tem_fuso(self):
		perfis = PerfisDeBanco(self.repo)
		perfis.criar("a", "mariadb")
		teste = perfis.registrar_teste("a", ok=False, nivel="tcp").ultimo_teste
		self.assertIsNotNone(datetime.fromisoformat(teste.quando).tzinfo)
		self.assertFalse(teste.ok)

	def test_criacao_concorrente_mantem_um_unico_padrao(self):
		if self.reabrir_repositorio() is self.repo:
			self.skipTest("o adaptador em memória não tem instâncias independentes")

		erros = []

		def trabalhar(numero):
			try:
				perfis = self.novos_perfis(self.reabrir_repositorio())

				for i in range(5):
					perfis.criar(f"p{numero}-{i}", "mariadb")
			except Exception as erro:
				erros.append(repr(erro))

		fios = [threading.Thread(target=trabalhar, args=(n,)) for n in range(4)]

		for fio in fios:
			fio.start()

		for fio in fios:
			fio.join()

		listados = self.novos_perfis(self.reabrir_repositorio()).listar()
		self.assertEqual(erros, [])
		self.assertEqual(len(listados), 20)
		self.assertEqual(sum(p.padrao for p in listados), 1)


class TestPerfisEmMemoria(ContratoDosPerfis, unittest.TestCase):
	def novo_repositorio(self):
		return RepositorioEmMemoria()

	def reabrir_repositorio(self):
		return self.repo


class _EmArquivo:
	FORMATO = ""

	def setUp(self):
		self._t = tempfile.TemporaryDirectory()
		self.addCleanup(self._t.cleanup)
		self.pasta = Path(self._t.name)
		super().setUp()

	def novo_repositorio(self):
		return self.reabrir_repositorio()

	def reabrir_repositorio(self):
		return fabrica.abrir(self.pasta / f"perfis{fabrica.extensao_do_formato(self.FORMATO)}", self.FORMATO)


class TestPerfisEmJson(_EmArquivo, ContratoDosPerfis, unittest.TestCase):
	FORMATO = "json"


class TestPerfisEmSqlite(_EmArquivo, ContratoDosPerfis, unittest.TestCase):
	FORMATO = "sqlite"


class TestAdocao(unittest.TestCase):
	def setUp(self):
		self.perfis = PerfisDeBanco(RepositorioEmMemoria(), agora=lambda: AGORA)

	def test_cria_o_padrao_a_partir_da_configuracao_sem_publicar(self):
		publicados = []
		perfis = PerfisDeBanco(RepositorioEmMemoria(), publicar_padrao=publicados.append)
		configuracao = {"db_type": "mariadb", "db_host": "127.0.0.1", "db_port": 3306, "root_login": "root"}

		adotado = adotar_configuracao_existente(perfis, configuracao)

		self.assertEqual(
			(adotado.nome, adotado.tipo, adotado.host, adotado.porta, adotado.usuario_root),
			("padrao", "mariadb", "127.0.0.1", 3306, "root"),
		)
		self.assertTrue(adotado.padrao)
		self.assertEqual(publicados, [], "o arquivo de configuração não é reescrito")
		self.assertEqual(
			configuracao,
			{"db_type": "mariadb", "db_host": "127.0.0.1", "db_port": 3306, "root_login": "root"},
		)

	def test_so_na_primeira_abertura(self):
		configuracao = {"db_type": "mariadb"}
		self.assertIsNotNone(adotar_configuracao_existente(self.perfis, configuracao))
		self.assertIsNone(adotar_configuracao_existente(self.perfis, configuracao))
		self.assertEqual(len(self.perfis.listar()), 1)

	def test_valores_ausentes_usam_o_padrao_do_tipo(self):
		adotado = adotar_configuracao_existente(self.perfis, {"db_type": "postgres"}, nome="meu-pg")
		self.assertEqual(
			(adotado.nome, adotado.host, adotado.porta, adotado.usuario_root),
			("meu-pg", "127.0.0.1", 5432, ""),
		)

	def test_porta_ruim_vira_a_do_tipo(self):
		adotado = adotar_configuracao_existente(self.perfis, {"db_type": "mariadb", "db_port": "3306"})
		self.assertEqual(adotado.porta, 3306)

	def test_sem_banco_reconhecivel_nao_cria_nada(self):
		for configuracao in ({}, {"db_type": "oracle"}, {"db_type": ["mariadb"]}):
			with self.subTest(configuracao=configuracao):
				self.assertIsNone(adotar_configuracao_existente(self.perfis, configuracao))

		self.assertEqual(self.perfis.listar(), [])

	def test_configuracao_com_valor_invalido_nao_derruba_a_abertura(self):
		self.assertIsNone(
			adotar_configuracao_existente(self.perfis, {"db_type": "mariadb", "db_host": "db;x"})
		)
		self.assertEqual(self.perfis.listar(), [])


class ContratoDoLeitor:
	FORMATO = ""

	def setUp(self):
		self._t = tempfile.TemporaryDirectory()
		self.addCleanup(self._t.cleanup)
		self.pasta = Path(self._t.name)
		self.repo = fabrica.abrir(
			self.pasta / f"{leitura.NOME_DO_ARQUIVO}{fabrica.extensao_do_formato(self.FORMATO)}", self.FORMATO
		)
		self.perfis = PerfisDeBanco(self.repo, agora=lambda: AGORA)
		self.leitor = leitura.abrir_leitor(self.pasta, self.FORMATO)

	def test_o_cherry_grava_e_o_leitor_le_sem_senha(self):
		self.perfis.criar("maria", "mariadb")
		self.perfis.criar("pg", "postgres", "db.local", 5433, "postgres")
		self.perfis.registrar_teste("pg", ok=True, nivel="autenticacao")

		resultado = self.leitor.ler()

		self.assertEqual([p.nome for p in resultado.perfis], ["maria", "pg"])
		self.assertEqual(resultado.padrao.nome, "maria")
		pg = self.leitor.por_nome("PG")
		self.assertEqual(
			(pg.tipo, pg.host, pg.porta, pg.usuario_root, pg.padrao),
			("postgres", "db.local", 5433, "postgres", False),
		)
		self.assertEqual(
			(pg.ultimo_teste_em, pg.ultimo_teste_nivel, pg.ultimo_teste_ok),
			(AGORA.isoformat(), "autenticacao", True),
		)
		self.assertEqual(self.leitor.padrao().nome, "maria")
		self.assertFalse({c for c in dir(pg) if "senha" in c or "password" in c})
		self.assertEqual(resultado.avisos, ())

	def test_sem_perfis(self):
		resultado = self.leitor.ler()
		self.assertEqual((resultado.perfis, resultado.avisos, resultado.padrao), ((), (), None))
		self.assertIsNone(self.leitor.por_nome("x"))
		self.assertIsNone(self.leitor.por_nome(None))

	def test_leitor_nao_oferece_escrita(self):
		for nome in ("gravar", "remover", "transacao", "criar", "alterar", "definir_padrao"):
			self.assertFalse(hasattr(self.leitor, nome), nome)

	def test_perfil_malformado_e_pulado_com_aviso(self):
		self.perfis.criar("bom", "mariadb")
		self.repo.gravar("perfis", "ruim", {"nome": "ruim", "tipo": "oracle", "host": "h", "porta": 1})

		resultado = self.leitor.ler()

		self.assertEqual([p.nome for p in resultado.perfis], ["bom"])
		self.assertEqual(len(resultado.avisos), 1)

	def test_o_escritor_recusa_perfil_malformado_em_vez_de_sobrescrever(self):
		self.perfis.criar("bom", "mariadb")
		self.repo.gravar("perfis", "ruim", {"nome": "ruim", "tipo": "oracle", "host": "h", "porta": 1})

		with self.assertRaises(PerfilInvalido):
			self.perfis.criar("outro", "mariadb")

	def test_campo_novo_e_esquema_mais_novo(self):
		self.repo.gravar(
			"perfis", "a", PerfilDeBanco("a", "mariadb").para_documento() | {"campo_do_futuro": 1}
		)
		self.repo.gravar("meta", "esquema", {"versao_esquema": 99})

		resultado = self.leitor.ler()

		self.assertTrue(resultado.mais_nova)
		self.assertEqual(resultado.versao_do_esquema, 99)
		self.assertEqual(len(resultado.perfis), 1)
		self.assertTrue(any("99" in a for a in resultado.avisos))

	def test_versao_ilegivel_vira_a_conhecida_com_aviso(self):
		self.repo.gravar("meta", "esquema", {"versao_esquema": "dois"})
		resultado = self.leitor.ler()
		self.assertFalse(resultado.mais_nova)
		self.assertEqual(len(resultado.avisos), 1)

	def test_leitura_durante_escrita_nunca_ve_arquivo_pela_metade(self):
		parar = threading.Event()
		erros = []

		def escrever():
			perfis = PerfisDeBanco(fabrica.abrir(self.repo_caminho(), self.FORMATO))

			for n in range(20):
				try:
					perfis.criar(f"perfil-{n}", "mariadb")
				except Exception as erro:
					erros.append(repr(erro))

			parar.set()

		fio = threading.Thread(target=escrever)
		fio.start()

		while not parar.is_set():
			resultado = self.leitor.ler()

			if resultado.ilegivel or resultado.avisos:
				erros.append(f"leitura inconsistente: {resultado.avisos}")

		fio.join()
		self.assertEqual(erros, [])
		self.assertEqual(len(self.leitor.ler().perfis), 20)

	def repo_caminho(self):
		return self.pasta / f"{leitura.NOME_DO_ARQUIVO}{fabrica.extensao_do_formato(self.FORMATO)}"


class TestLeitorEmJson(ContratoDoLeitor, unittest.TestCase):
	FORMATO = "json"

	def test_arquivo_corrompido_devolve_leitura_ilegivel(self):
		self.perfis.criar("a", "mariadb")
		self.repo_caminho().write_text("{ não é json", encoding="utf-8")

		resultado = leitura.abrir_leitor(self.pasta, "json").ler()

		self.assertTrue(resultado.ilegivel)
		self.assertEqual(resultado.perfis, ())


class TestLeitorEmSqlite(ContratoDoLeitor, unittest.TestCase):
	FORMATO = "sqlite"


class TestUsoPeloSoda(unittest.TestCase):
	def setUp(self):
		self.repo_soda = RepositorioEmMemoria()
		self.registro = Registro(self.repo_soda, livre=lambda porta: True)
		self.usos = usos_pelas_instancias(LeitorDeInstancias(self.repo_soda))

	def test_lista_as_instancias_que_usam_o_perfil_pelo_descritivo_e_uuid_abreviado(self):
		a = self.registro.criar("Homologação", perfil_de_banco="maria", tipo_de_banco="mariadb")
		b = self.registro.criar("Treino", perfil_de_banco="MARIA", tipo_de_banco="mariadb")
		self.registro.criar("Outro", perfil_de_banco="pg", tipo_de_banco="postgres")

		self.assertEqual(
			set(self.usos("Maria")), {Uso(a.descritivo, a.abreviado), Uso(b.descritivo, b.abreviado)}
		)
		self.assertEqual(self.usos("sem-uso"), ())

	def test_integrado_ao_repositorio_de_perfis(self):
		perfis = PerfisDeBanco(RepositorioEmMemoria(), usos=self.usos)
		perfis.criar("maria", "mariadb")
		perfis.criar("pg", "postgres")
		perfis.definir_padrao("pg")
		instancia = self.registro.criar("Homologação", perfil_de_banco="maria", tipo_de_banco="mariadb")

		with self.assertRaises(PerfilEmUso) as contexto:
			perfis.remover("maria")

		self.assertIn(f"Homologação ({instancia.abreviado})", str(contexto.exception))

		self.registro.mudar_estado(instancia.uuid, Estado.PARADA)
		self.registro.aposentar(instancia.uuid)
		perfis.remover("maria")  # sem instância usando, sai
		self.assertIsNone(perfis.obter("maria"))


class TestNenhumaSenhaEmDisco(unittest.TestCase):
	def test_nenhuma_operacao_do_repositorio_aceita_senha(self):
		import inspect

		for nome in ("criar", "alterar", "registrar_teste", "definir_padrao", "remover"):
			parametros = inspect.signature(getattr(PerfisDeBanco, nome)).parameters
			self.assertFalse({p for p in parametros if "senha" in p or "password" in p}, nome)

	def test_o_que_vai_a_disco_so_tem_os_campos_conhecidos(self):
		for formato in fabrica.FORMATOS:
			with self.subTest(formato=formato), tempfile.TemporaryDirectory() as pasta:
				repo = fabrica.abrir(Path(pasta) / f"perfis{fabrica.extensao_do_formato(formato)}", formato)
				perfis = PerfisDeBanco(repo)
				perfis.criar("a", "mariadb", usuario_root="root")
				perfis.registrar_teste("a", ok=True, nivel="tcp")

				((_, documento),) = repo.listar("perfis")
				self.assertEqual(
					set(documento),
					{"nome", "tipo", "host", "porta", "usuario_root", "padrao", "ultimo_teste"},
				)
				self.assertEqual(set(documento["ultimo_teste"]), {"quando", "nivel", "ok"})


if __name__ == "__main__":
	unittest.main()
