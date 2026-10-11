# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Suíte de contrato da persistência selecionável: a mesma bateria contra os três adaptadores.

O ponto desta suíte é a **paridade**: memória, JSON e SQLite precisam produzir o mesmo estado observável
para as mesmas operações, e o que se grava por uma instância precisa ser lido por outra (teste na costura:
grava por um caminho, relê por outro). Um adaptador que diverge faz um caso nomeado falhar.

Depois do contrato vêm os testes de cada formato (arquivo ilegível, esquema mais novo, escrita que falha
no meio, trava) e os da migração e da troca de formato.
"""

import json
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from datetime import datetime
from pathlib import Path
from unittest import mock

from erpnext_brasil.persistencia import arquivos, fabrica
from erpnext_brasil.persistencia import documentos as doc
from erpnext_brasil.persistencia import json_arquivo as ja
from erpnext_brasil.persistencia import sqlite_arquivo as sa
from erpnext_brasil.persistencia.memoria import RepositorioEmMemoria


class ContratoDeRepositorio:
	"""Mixin com a bateria; cada formato a herda junto com `unittest.TestCase` e diz como criar e reabrir."""

	COMPARTILHA_ENTRE_INSTANCIAS = True

	def novo(self):
		raise NotImplementedError

	def reabrir(self):
		"""Outra instância sobre o mesmo armazenamento (outro processo, na prática)."""
		raise NotImplementedError

	def setUp(self):
		self.repo = self.novo()

	def test_obter_inexistente_e_none(self):
		self.assertIsNone(self.repo.obter("preferencias", "janela"))

	def test_grava_e_obtem(self):
		self.repo.gravar("instancias", "a", {"descritivo": "NF-e em homologação", "porta": 8101})
		self.assertEqual(
			self.repo.obter("instancias", "a"), {"descritivo": "NF-e em homologação", "porta": 8101}
		)

	def test_regravar_substitui_o_documento_inteiro(self):
		self.repo.gravar("c", "a", {"x": 1, "y": 2})
		self.repo.gravar("c", "a", {"x": 3})
		self.assertEqual(self.repo.obter("c", "a"), {"x": 3})

	def test_quem_le_recebe_copia(self):
		self.repo.gravar("c", "a", {"lista": [1, 2], "aninhado": {"k": "v"}})
		lido = self.repo.obter("c", "a")
		lido["lista"].append(99)
		lido["aninhado"]["k"] = "alterado"
		self.assertEqual(self.repo.obter("c", "a"), {"lista": [1, 2], "aninhado": {"k": "v"}})

	def test_quem_grava_nao_segura_referencia(self):
		documento = {"lista": [1]}
		self.repo.gravar("c", "a", documento)
		documento["lista"].append(2)
		self.assertEqual(self.repo.obter("c", "a"), {"lista": [1]})

	def test_listar_vem_ordenado_pela_chave(self):
		for chave in ("c", "a", "b"):
			self.repo.gravar("col", chave, {"n": chave})

		self.assertEqual([c for c, _ in self.repo.listar("col")], ["a", "b", "c"])

	def test_listar_colecao_vazia(self):
		self.assertEqual(self.repo.listar("nada"), [])

	def test_colecoes_so_as_que_tem_documento(self):
		self.repo.gravar("b", "1", {})
		self.repo.gravar("a", "1", {})
		self.repo.gravar("c", "1", {})
		self.repo.remover("c", "1")
		self.assertEqual(self.repo.colecoes(), ["a", "b"])

	def test_remover_diz_se_existia(self):
		self.repo.gravar("c", "a", {})
		self.assertTrue(self.repo.remover("c", "a"))
		self.assertFalse(self.repo.remover("c", "a"))
		self.assertIsNone(self.repo.obter("c", "a"))

	def test_nomes_invalidos_sao_recusados_antes_de_gravar(self):
		for ruim in ("", "a/b", "../x", "a b", "x" * 201, None, 5):
			with self.subTest(ruim=ruim):
				with self.assertRaises(doc.PersistenciaInvalida):
					self.repo.gravar(ruim, "a", {})

				with self.assertRaises(doc.PersistenciaInvalida):
					self.repo.gravar("c", ruim, {})

				with self.assertRaises(doc.PersistenciaInvalida):
					self.repo.obter(ruim, "a")

				with self.assertRaises(doc.PersistenciaInvalida):
					self.repo.listar(ruim)

				with self.assertRaises(doc.PersistenciaInvalida):
					self.repo.remover("c", ruim)

		self.assertEqual(self.repo.colecoes(), [])

	def test_documentos_invalidos_sao_recusados(self):
		invalidos = [
			["lista", "não é dicionário"],
			{"nan": float("nan")},
			{1: "chave que não é texto"},
			{"objeto": object()},
			{"aninhado": {2: "x"}},
		]

		for ruim in invalidos:
			with self.subTest(ruim=str(ruim)[:30]), self.assertRaises(doc.PersistenciaInvalida):
				self.repo.gravar("c", "a", ruim)

	def test_segredo_nunca_e_persistido(self):
		"""Nenhuma ferramenta guarda senha ou token, em nenhum formato, em nenhum nível do documento."""
		segredos = [
			{"senha": "x"},
			{"db_password": "x"},
			{"config": {"root_Password": "x"}},
			{"itens": [{"api_key": "x"}]},
			{"token": "x"},
			{"SEGREDO": "x"},
		]

		for ruim in segredos:
			with self.subTest(ruim=str(ruim)), self.assertRaises(doc.PersistenciaInvalida):
				self.repo.gravar("c", "a", ruim)

		self.assertEqual(self.repo.colecoes(), [])

	def test_transacao_agrupa_e_a_leitura_interna_ja_ve_o_que_foi_gravado(self):
		with self.repo.transacao():
			self.repo.gravar("c", "a", {"v": 1})
			self.repo.gravar("c", "b", {"v": 2})
			self.assertEqual(self.repo.obter("c", "a"), {"v": 1})
			self.assertEqual([c for c, _ in self.repo.listar("c")], ["a", "b"])
			self.assertEqual(self.repo.colecoes(), ["c"])
			self.assertTrue(self.repo.remover("c", "a"))

		self.assertEqual([c for c, _ in self.repo.listar("c")], ["b"])

	def test_transacao_que_falha_nao_aplica_nada(self):
		self.repo.gravar("c", "antes", {"v": 0})

		with self.assertRaises(RuntimeError), self.repo.transacao():
			self.repo.gravar("c", "a", {"v": 1})
			self.repo.gravar("c", "b", {"v": 2})
			self.repo.remover("c", "antes")
			raise RuntimeError("falha no meio")

		self.assertEqual([c for c, _ in self.repo.listar("c")], ["antes"])

	def test_transacao_aninhada_e_recusada_e_a_externa_continua_valida(self):
		with self.repo.transacao():
			with self.assertRaises(doc.PersistenciaInvalida), self.repo.transacao():
				pass

			self.repo.gravar("c", "a", {"v": 1})

		self.assertEqual(self.repo.obter("c", "a"), {"v": 1})

	def test_o_que_uma_instancia_grava_a_outra_le(self):
		"""Teste na costura: grava por um caminho e relê por outro, independente."""
		self.repo.gravar("c", "a", {"v": 1})
		self.repo.gravar("c", "b", {"v": 2})
		self.repo.remover("c", "b")

		outra = self.reabrir()

		self.assertEqual(outra.obter("c", "a"), {"v": 1})
		self.assertIsNone(outra.obter("c", "b"))
		self.assertEqual(outra.colecoes(), ["c"])

	def test_acentos_e_unicode_sobrevivem(self):
		self.repo.gravar("c", "a", {"descritivo": "Homologação — São Paulo ✓"})
		self.assertEqual(self.reabrir().obter("c", "a")["descritivo"], "Homologação — São Paulo ✓")

	def test_a_versao_do_esquema_e_um_inteiro_positivo(self):
		self.repo.gravar("c", "a", {})
		self.assertGreaterEqual(self.repo.versao_do_esquema(), 1)

	def test_gravacoes_concorrentes_de_instancias_diferentes_nao_se_perdem(self):
		if not self.COMPARTILHA_ENTRE_INSTANCIAS:
			self.skipTest("o adaptador em memória não tem instâncias independentes")

		def trabalhar(numero):
			repo = self.reabrir()

			for i in range(15):
				repo.gravar("c", f"t{numero}-{i}", {"n": i})

		fios = [threading.Thread(target=trabalhar, args=(n,)) for n in range(4)]

		for fio in fios:
			fio.start()

		for fio in fios:
			fio.join()

		self.assertEqual(len(self.reabrir().listar("c")), 60)


class TestMemoria(ContratoDeRepositorio, unittest.TestCase):
	COMPARTILHA_ENTRE_INSTANCIAS = False

	def novo(self):
		return RepositorioEmMemoria()

	def reabrir(self):
		return self.repo


class _EmArquivo:
	def setUp(self):
		self._pasta = tempfile.TemporaryDirectory()
		self.addCleanup(self._pasta.cleanup)
		self.pasta = Path(self._pasta.name)
		super().setUp()


class TestJson(_EmArquivo, ContratoDeRepositorio, unittest.TestCase):
	def novo(self):
		return ja.RepositorioJson(self.pasta / "dados.json")

	def reabrir(self):
		return ja.RepositorioJson(self.pasta / "dados.json")


class TestSqlite(_EmArquivo, ContratoDeRepositorio, unittest.TestCase):
	def novo(self):
		return sa.RepositorioSqlite(self.pasta / "dados.sqlite")

	def reabrir(self):
		return sa.RepositorioSqlite(self.pasta / "dados.sqlite")


class TestJsonDoArquivo(unittest.TestCase):
	def setUp(self):
		self._pasta = tempfile.TemporaryDirectory()
		self.addCleanup(self._pasta.cleanup)
		self.caminho = Path(self._pasta.name) / "dados.json"
		self.repo = ja.RepositorioJson(self.caminho)

	def test_ler_nao_cria_o_arquivo(self):
		self.assertEqual(self.repo.colecoes(), [])
		self.assertEqual(self.repo.versao_do_esquema(), ja.ESQUEMA_ATUAL)
		self.assertFalse(self.caminho.exists())

	def test_formato_do_arquivo_e_legivel_e_so_com_lf(self):
		self.repo.gravar("c", "a", {"z": 1, "a": 2})
		bruto = self.caminho.read_bytes()
		self.assertTrue(bruto.endswith(b"\n"))
		self.assertNotIn(b"\r", bruto)
		lido = json.loads(bruto)
		self.assertEqual(lido["versao_esquema"], 1)
		self.assertEqual(lido["colecoes"], {"c": {"a": {"a": 2, "z": 1}}})
		self.assertIn(b'\n "colecoes"', bruto)

	def test_colecao_esvaziada_some_do_arquivo(self):
		self.repo.gravar("c", "a", {})
		self.repo.remover("c", "a")
		self.assertEqual(json.loads(self.caminho.read_text(encoding="utf-8"))["colecoes"], {})

	def test_arquivo_ilegivel_nunca_e_sobrescrito(self):
		casos = ["{quebrado", "[1, 2]", '{"colecoes": {}}', '{"versao_esquema": 1, "colecoes": []}']

		for conteudo in casos:
			with self.subTest(conteudo=conteudo):
				self.caminho.write_text(conteudo, encoding="utf-8")

				with self.assertRaises(doc.ArquivoIlegivel) as contexto:
					self.repo.gravar("c", "a", {"v": 1})

				self.assertEqual(contexto.exception.caminho, self.caminho)
				self.assertEqual(self.caminho.read_text(encoding="utf-8"), conteudo)

				with self.assertRaises(doc.ArquivoIlegivel):
					self.repo.obter("c", "a")

	def test_esquema_mais_novo_recusa_gravar_mas_deixa_ler(self):
		self.caminho.write_text(
			json.dumps({"versao_esquema": 99, "colecoes": {"c": {"a": {"v": 1}}}}), encoding="utf-8"
		)
		self.assertEqual(self.repo.obter("c", "a"), {"v": 1})

		with self.assertRaises(doc.EsquemaMaisNovo):
			self.repo.gravar("c", "b", {})

		self.assertEqual(self.repo.versao_do_esquema(), 99)

	def test_falha_no_meio_da_escrita_preserva_o_original_e_nao_deixa_temporario(self):
		self.repo.gravar("c", "a", {"v": 1})
		antes = self.caminho.read_bytes()
		pasta = sorted(p.name for p in self.caminho.parent.iterdir())

		for onde in ("replace", "fsync"):
			with self.subTest(onde=onde):
				with mock.patch.object(arquivos.os, onde, side_effect=OSError("disco cheio simulado")):
					with self.assertRaises(OSError):
						self.repo.gravar("c", "b", {"v": 2})

				self.assertEqual(self.caminho.read_bytes(), antes)
				self.assertEqual(sorted(p.name for p in self.caminho.parent.iterdir()), pasta)

	def test_transacao_que_falha_libera_a_trava(self):
		with self.assertRaises(RuntimeError), self.repo.transacao():
			raise RuntimeError("falha")

		self.repo.gravar("c", "a", {})
		self.assertFalse(self.caminho.with_name("dados.json.trava").exists())


class TestSqliteDoArquivo(unittest.TestCase):
	def setUp(self):
		self._pasta = tempfile.TemporaryDirectory()
		self.addCleanup(self._pasta.cleanup)
		self.caminho = Path(self._pasta.name) / "dados.sqlite"

	def test_cria_o_esquema_em_wal_e_na_versao_atual(self):
		sa.RepositorioSqlite(self.caminho).gravar("c", "a", {"v": 1})

		with closing(sqlite3.connect(self.caminho, isolation_level=None)) as conexao:
			self.assertEqual(conexao.execute("PRAGMA user_version").fetchone()[0], sa.ESQUEMA_ATUAL)
			self.assertEqual(conexao.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")

	def test_esquema_nao_tem_coluna_de_segredo(self):
		"""O esquema é revisto por teste: nenhuma coluna pode ter nome de senha, token ou segredo."""
		sa.RepositorioSqlite(self.caminho).gravar("c", "a", {})

		with closing(sqlite3.connect(self.caminho, isolation_level=None)) as conexao:
			colunas = [
				linha[1]
				for (tabela,) in conexao.execute("SELECT name FROM sqlite_master WHERE type='table'")
				for linha in conexao.execute(f"PRAGMA table_info({tabela})")
			]

		self.assertEqual(sorted(colunas), ["chave", "colecao", "json"])
		self.assertFalse([c for c in colunas if doc._SEGREDO.search(c)])

	def test_arquivo_que_nao_e_sqlite_nunca_e_sobrescrito(self):
		conteudo = b"isto nao e um banco sqlite " * 20
		self.caminho.write_bytes(conteudo)

		for chamada in (
			lambda r: r.gravar("c", "a", {}),
			lambda r: r.obter("c", "a"),
		):
			with self.assertRaises(doc.ArquivoIlegivel):
				chamada(sa.RepositorioSqlite(self.caminho))

		self.assertEqual(self.caminho.read_bytes(), conteudo)

	def test_esquema_mais_novo_so_abre_para_leitura(self):
		sa.RepositorioSqlite(self.caminho).gravar("c", "a", {"v": 1})

		with closing(sqlite3.connect(self.caminho, isolation_level=None)) as conexao:
			conexao.execute("PRAGMA user_version = 99")

		with self.assertRaises(doc.EsquemaMaisNovo):
			sa.RepositorioSqlite(self.caminho).gravar("c", "b", {})

		leitura = sa.RepositorioSqlite(self.caminho, somente_leitura=True)
		self.assertEqual(leitura.obter("c", "a"), {"v": 1})
		self.assertEqual(leitura.versao_do_esquema(), 99)

	def test_migracao_de_esquema_na_abertura_em_transacao(self):
		sa.RepositorioSqlite(self.caminho).gravar("c", "a", {"v": 1})
		migracoes = {**sa.MIGRACOES, 2: ("CREATE TABLE extra (id INTEGER PRIMARY KEY)",)}

		repo = sa.RepositorioSqlite(self.caminho, migracoes=migracoes)
		self.assertEqual(repo.versao_do_esquema(), 2)
		self.assertEqual(repo.obter("c", "a"), {"v": 1})

		with closing(sqlite3.connect(self.caminho, isolation_level=None)) as conexao:
			self.assertIsNotNone(conexao.execute("SELECT 1 FROM sqlite_master WHERE name='extra'").fetchone())

	def test_migracao_que_falha_deixa_o_arquivo_na_versao_anterior(self):
		sa.RepositorioSqlite(self.caminho).gravar("c", "a", {"v": 1})
		ruim = {**sa.MIGRACOES, 2: ("CREATE TABLE ok (id INTEGER)", "COMANDO QUE NAO EXISTE")}

		with self.assertRaises(sqlite3.Error):
			sa.RepositorioSqlite(self.caminho, migracoes=ruim).obter("c", "a")

		with closing(sqlite3.connect(self.caminho, isolation_level=None)) as conexao:
			self.assertEqual(conexao.execute("PRAGMA user_version").fetchone()[0], 1)
			self.assertIsNone(conexao.execute("SELECT 1 FROM sqlite_master WHERE name='ok'").fetchone())

		self.assertEqual(sa.RepositorioSqlite(self.caminho).obter("c", "a"), {"v": 1})

	def test_somente_leitura_de_arquivo_ausente_e_vazio_e_nao_cria_nada(self):
		leitura = sa.RepositorioSqlite(self.caminho, somente_leitura=True)

		self.assertIsNone(leitura.obter("c", "a"))
		self.assertEqual(leitura.listar("c"), [])
		self.assertEqual(leitura.colecoes(), [])
		self.assertEqual(leitura.versao_do_esquema(), 0)
		self.assertFalse(self.caminho.exists())

	def test_somente_leitura_recusa_escrever(self):
		sa.RepositorioSqlite(self.caminho).gravar("c", "a", {})
		leitura = sa.RepositorioSqlite(self.caminho, somente_leitura=True)

		with self.assertRaises(doc.PersistenciaInvalida):
			leitura.gravar("c", "b", {})

		with self.assertRaises(doc.PersistenciaInvalida):
			leitura.remover("c", "a")

		with self.assertRaises(doc.PersistenciaInvalida), leitura.transacao():
			pass

	def test_leitura_imutavel_le_o_instantaneo(self):
		sa.RepositorioSqlite(self.caminho).gravar("c", "a", {"v": 1})
		leitura = sa.RepositorioSqlite(self.caminho, imutavel=True)

		self.assertEqual(leitura.obter("c", "a"), {"v": 1})
		self.assertEqual(leitura.colecoes(), ["c"])

	def test_somente_leitura_de_arquivo_vazio_sem_tabela(self):
		self.caminho.write_bytes(b"")
		leitura = sa.RepositorioSqlite(self.caminho, somente_leitura=True)

		self.assertIsNone(leitura.obter("c", "a"))
		self.assertEqual(leitura.listar("c"), [])
		self.assertEqual(leitura.colecoes(), [])

	def test_dois_gravadores_sao_serializados_pelo_proprio_banco(self):
		primeiro = sa.RepositorioSqlite(self.caminho, espera=0.2)
		segundo = sa.RepositorioSqlite(self.caminho, espera=0.2)
		primeiro.gravar("c", "inicial", {})

		with primeiro.transacao():
			primeiro.gravar("c", "a", {})

			with self.assertRaises(sqlite3.OperationalError):
				segundo.gravar("c", "b", {})

		segundo.gravar("c", "b", {})
		self.assertEqual([c for c, _ in segundo.listar("c")], ["a", "b", "inicial"])


class TestArquivos(unittest.TestCase):
	def setUp(self):
		self._pasta = tempfile.TemporaryDirectory()
		self.addCleanup(self._pasta.cleanup)
		self.pasta = Path(self._pasta.name)

	def test_escrita_atomica_cria_pasta_e_so_usa_lf(self):
		alvo = self.pasta / "sub" / "a.txt"
		arquivos.escrever_atomico(alvo, "um\ndois\n")
		self.assertEqual(alvo.read_bytes(), b"um\ndois\n")

	def test_escrita_atomica_substitui_e_nao_deixa_temporario(self):
		alvo = self.pasta / "a.txt"
		alvo.write_text("antigo", encoding="utf-8")
		arquivos.escrever_atomico(alvo, "novo")
		self.assertEqual(alvo.read_text(encoding="utf-8"), "novo")
		self.assertEqual([p.name for p in self.pasta.iterdir()], ["a.txt"])

	def test_troca_tenta_de_novo_enquanto_o_windows_segura_o_destino(self):
		"""`os.replace` falha com PermissionError enquanto outro processo lê o destino; a troca insiste."""
		origem, destino = self.pasta / "o.tmp", self.pasta / "d.txt"
		origem.write_text("novo", encoding="utf-8")
		falhas = {"restantes": 3}
		real = arquivos.os.replace
		dormiu = []

		def instavel(de, para):
			if falhas["restantes"]:
				falhas["restantes"] -= 1
				raise PermissionError("em uso")

			real(de, para)

		with mock.patch.object(arquivos.os, "replace", side_effect=instavel):
			arquivos._trocar(origem, destino, dormiu.append)

		self.assertEqual(destino.read_text(encoding="utf-8"), "novo")
		self.assertEqual(len(dormiu), 3)

	def test_troca_desiste_depois_das_tentativas_e_diz_o_motivo(self):
		origem, destino = self.pasta / "o.tmp", self.pasta / "d.txt"
		origem.write_text("novo", encoding="utf-8")

		with mock.patch.object(arquivos.os, "replace", side_effect=PermissionError("sempre em uso")):
			with self.assertRaises(PermissionError):
				arquivos._trocar(origem, destino, lambda _: None, tentativas=3)

	def test_trava_basica_cria_e_remove(self):
		caminho = self.pasta / "x.trava"

		with arquivos.Trava(caminho):
			self.assertTrue(caminho.exists())

		self.assertFalse(caminho.exists())

	def test_trava_ocupada_esgota_a_espera(self):
		caminho = self.pasta / "x.trava"
		relogio = iter(range(100))
		dormiu = []

		with arquivos.Trava(caminho):
			with self.assertRaises(doc.TravaOcupada):
				with arquivos.Trava(
					caminho, espera=3, obsoleta_apos=1000, agora=lambda: next(relogio), dormir=dormiu.append
				):
					pass

		self.assertTrue(dormiu)

	def test_trava_de_processo_morto_e_desfeita(self):
		caminho = self.pasta / "x.trava"
		caminho.write_text("999999\n", encoding="utf-8")

		with arquivos.Trava(caminho, obsoleta_apos=-1):
			self.assertTrue(caminho.exists())

		self.assertFalse(caminho.exists())

	def test_trava_que_some_entre_o_erro_e_a_conferencia_nao_e_obsoleta(self):
		trava = arquivos.Trava(self.pasta / "inexistente.trava")
		self.assertFalse(trava._obsoleta())

	def test_quarentena_move_com_data_no_nome(self):
		alvo = self.pasta / "dados.json"
		alvo.write_text("{quebrado", encoding="utf-8")

		destino = arquivos.quarentena(alvo, agora=lambda: datetime(2026, 10, 11, 12, 30, 5))

		self.assertEqual(destino.name, "dados.json.quarentena-20261011123005")
		self.assertFalse(alvo.exists())
		self.assertEqual(destino.read_text(encoding="utf-8"), "{quebrado")


class _Rebelde(RepositorioEmMemoria):
	"""Um destino que engole as gravações: depois de migrar, não fica igual à origem."""

	def gravar(self, colecao, chave, documento):
		pass


class TestMigracao(unittest.TestCase):
	def setUp(self):
		self._pasta = tempfile.TemporaryDirectory()
		self.addCleanup(self._pasta.cleanup)
		self.pasta = Path(self._pasta.name)
		self.json = ja.RepositorioJson(self.pasta / "a.json")
		self.sqlite = sa.RepositorioSqlite(self.pasta / "a.sqlite")

		with self.json.transacao():
			self.json.gravar("instancias", "u1", {"descritivo": "NF-e", "porta": 8101})
			self.json.gravar("instancias", "u2", {"descritivo": "Folha", "porta": 8102})
			self.json.gravar("aposentados", "u0", {"descritivo": "Antiga"})

	def test_ida_e_volta_preserva_tudo(self):
		self.assertEqual(doc.migrar(self.json, self.sqlite), 3)
		volta = ja.RepositorioJson(self.pasta / "volta.json")
		self.assertEqual(doc.migrar(self.sqlite, volta), 3)
		self.assertTrue(doc.sao_iguais(self.json, volta))
		self.assertEqual(doc.listar_tudo(volta), doc.listar_tudo(self.json))

	def test_migrar_duas_vezes_e_idempotente(self):
		doc.migrar(self.json, self.sqlite)
		antes = doc.listar_tudo(self.sqlite)
		doc.migrar(self.json, self.sqlite)
		self.assertEqual(doc.listar_tudo(self.sqlite), antes)

	def test_destino_com_conteudo_diferente_e_recusado_sem_tocar_em_nada(self):
		self.sqlite.gravar("instancias", "u1", {"descritivo": "OUTRO", "porta": 1})

		with self.assertRaises(doc.PersistenciaInvalida):
			doc.migrar(self.json, self.sqlite)

		self.assertEqual(self.sqlite.obter("instancias", "u1")["descritivo"], "OUTRO")
		self.assertEqual(self.sqlite.colecoes(), ["instancias"])

	def test_destino_com_chave_que_a_origem_nao_tem_e_recusado(self):
		self.sqlite.gravar("sobra", "x", {})

		with self.assertRaises(doc.PersistenciaInvalida):
			doc.migrar(self.json, self.sqlite)

	def test_interrompida_no_meio_nao_deixa_o_destino_pela_metade_e_a_origem_fica_intacta(self):
		antes = doc.listar_tudo(self.json)
		originais = self.sqlite.gravar
		contador = {"n": 0}

		def quebra(colecao, chave, documento):
			contador["n"] += 1

			if contador["n"] == 2:
				raise OSError("queda no meio da migração")

			originais(colecao, chave, documento)

		with mock.patch.object(self.sqlite, "gravar", side_effect=quebra):
			with self.assertRaises(OSError):
				doc.migrar(self.json, self.sqlite)

		self.assertEqual(self.sqlite.colecoes(), [])
		self.assertEqual(doc.listar_tudo(self.json), antes)
		self.assertEqual(doc.migrar(self.json, self.sqlite), 3)

	def test_destino_que_diverge_depois_de_migrar_e_denunciado(self):
		with self.assertRaises(doc.MigracaoDivergente):
			doc.migrar(self.json, _Rebelde())


class TestFabrica(unittest.TestCase):
	def setUp(self):
		self._pasta = tempfile.TemporaryDirectory()
		self.addCleanup(self._pasta.cleanup)
		self.pasta = Path(self._pasta.name)

	def test_abrir_devolve_o_adaptador_do_formato(self):
		self.assertEqual(fabrica.abrir(self.pasta / "a.json", "json").formato, "json")
		self.assertEqual(fabrica.abrir(self.pasta / "a.sqlite", "sqlite").formato, "sqlite")

	def test_formato_desconhecido_e_recusado(self):
		with self.assertRaises(doc.PersistenciaInvalida):
			fabrica.abrir(self.pasta / "a.xml", "xml")

		self.assertEqual(fabrica.extensao_do_formato("sqlite"), ".sqlite")

	def test_trocar_formato_migra_e_deixa_o_anterior_ao_lado(self):
		origem = self.pasta / "registro.json"
		fabrica.abrir(origem, "json").gravar("c", "a", {"v": 1})

		resultado = fabrica.trocar_formato(origem, "json", self.pasta / "registro.sqlite", "sqlite")

		self.assertEqual(resultado.total, 1)
		self.assertEqual(resultado.formato_destino, "sqlite")
		self.assertEqual(fabrica.abrir(resultado.destino, "sqlite").obter("c", "a"), {"v": 1})
		self.assertTrue(origem.exists())

	def test_descartar_o_anterior_move_para_quarentena_sem_apagar(self):
		origem = self.pasta / "registro.json"
		fabrica.abrir(origem, "json").gravar("c", "a", {"v": 1})

		destino = fabrica.descartar_anterior(origem)

		self.assertFalse(origem.exists())
		self.assertIn("quarentena", destino.name)
		self.assertTrue(destino.exists())

	def test_mesmo_arquivo_e_origem_inexistente_sao_recusados(self):
		caminho = self.pasta / "a.json"

		with self.assertRaises(doc.PersistenciaInvalida):
			fabrica.trocar_formato(caminho, "json", caminho, "sqlite")

		with self.assertRaises(doc.PersistenciaInvalida):
			fabrica.trocar_formato(caminho, "json", self.pasta / "b.sqlite", "sqlite")


if __name__ == "__main__":
	unittest.main()
