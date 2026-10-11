# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes do núcleo do Cherry — cada um grava por um caminho e relê por outro.

`gravar_json` → `json.loads` do arquivo cru (não `ler_json`); `gravar_apps_txt` → bytes do
arquivo (não a lista devolvida). É a disciplina de testar a costura, não o retorno: um
`gravar_apps_txt` que devolvesse o texto certo e gravasse sem o `\\n` final passaria num
teste de retorno e repetiria o bug 4b de `banco-do-bench-v16.md`.

Rodar: `python -m unittest scripts.cherry.test_config -v` na raiz do repositório.
"""

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path, PureWindowsPath
from unittest import mock

from scripts import cherry
from scripts.cherry import config as cfg


class _ComBench(unittest.TestCase):
	"""Um bench de mentira num diretório temporário — só o que o Cherry lê e escreve."""

	def setUp(self):
		self._tmp = tempfile.TemporaryDirectory()
		self.raiz = Path(self._tmp.name)
		(self.raiz / "sites" / "um.localhost").mkdir(parents=True)
		(self.raiz / "sites" / "um.localhost" / "site_config.json").write_text('{"db_name": "_abc"}\n')
		(self.raiz / "sites" / "assets").mkdir()
		(self.raiz / "sites" / "orfao").mkdir()
		self.bench = cfg.Bench(self.raiz)

	def tearDown(self):
		self._tmp.cleanup()


class TestVersao(unittest.TestCase):
	def test_e_semantica(self):
		self.assertRegex(cherry.__version__, r"^\d+\.\d+\.\d+$")


class TestJson(_ComBench):
	def test_ausente_e_dicionario_vazio(self):
		self.assertEqual(cfg.ler_json(self.raiz / "nao-existe.json"), {})

	def test_vazio_e_dicionario_vazio(self):
		caminho = self.raiz / "vazio.json"
		caminho.write_text("  \n")
		self.assertEqual(cfg.ler_json(caminho), {})

	def test_lista_no_lugar_de_objeto_e_erro(self):
		caminho = self.raiz / "lista.json"
		caminho.write_text("[1, 2]")

		with self.assertRaises(cfg.CherryInvalido):
			cfg.ler_json(caminho)

	def test_grava_no_formato_do_frappe(self):
		"""indent=1, chaves ordenadas, `\\n` final — relido cru, byte a byte."""
		caminho = self.raiz / "sites" / "novo" / "common_site_config.json"
		cfg.gravar_json(caminho, {"z": 1, "a": "x"})
		self.assertEqual(caminho.read_text(encoding="utf-8"), '{\n "a": "x",\n "z": 1\n}\n')

	def test_atualizar_preserva_o_resto_e_none_remove(self):
		caminho = self.bench.common_config
		cfg.gravar_json(
			caminho, {"redis_cache": "redis://127.0.0.1:13001", "developer_mode": 1, "db_port": 3306}
		)
		final = cfg.atualizar_json(caminho, {"db_port": 5432, "developer_mode": None, "db_type": "postgres"})
		relido = json.loads(caminho.read_text(encoding="utf-8"))
		self.assertEqual(relido, final)
		self.assertEqual(relido["redis_cache"], "redis://127.0.0.1:13001")
		self.assertEqual(relido["db_port"], 5432)
		self.assertEqual(relido["db_type"], "postgres")
		self.assertNotIn("developer_mode", relido)


class TestEscritaAtomica(_ComBench):
	"""CH-02: falha no meio da escrita não pode deixar o destino truncado nem sobra de temporário."""

	def setUp(self):
		super().setUp()
		self.alvo = self.bench.sites / "common_site_config.json"
		cfg.gravar_json(self.alvo, {"db_type": "mariadb", "root_password": "x"})
		self.antes = self.alvo.read_bytes()

	def _pasta(self):
		return sorted(p.name for p in self.alvo.parent.iterdir())

	def test_falha_ao_gravar_preserva_o_original_byte_a_byte(self):
		for ponto in ("fsync", "replace"):
			with self.subTest(ponto=ponto):
				with mock.patch.object(cfg.os, ponto, side_effect=OSError("disco cheio simulado")):
					with self.assertRaises(OSError):
						cfg.gravar_json(self.alvo, {"db_type": "postgres"})

				self.assertEqual(self.alvo.read_bytes(), self.antes)
				json.loads(self.alvo.read_text(encoding="utf-8"))

	def test_falha_nao_deixa_arquivo_temporario(self):
		antes = self._pasta()

		with mock.patch.object(cfg.os, "replace", side_effect=OSError("queda simulada")):
			with self.assertRaises(OSError):
				cfg.gravar_json(self.alvo, {"db_type": "postgres"})

		self.assertEqual(self._pasta(), antes)

	def test_falha_em_arquivo_novo_nao_cria_nada(self):
		novo = self.bench.sites / "novo.json"
		antes = self._pasta()

		with mock.patch.object(cfg.os, "replace", side_effect=OSError("queda simulada")):
			with self.assertRaises(OSError):
				cfg.gravar_json(novo, {"a": 1})

		self.assertFalse(novo.exists())
		self.assertEqual(self._pasta(), antes)

	def test_sucesso_nao_deixa_temporario_e_troca_o_conteudo(self):
		antes = self._pasta()

		cfg.gravar_json(self.alvo, {"db_type": "postgres"})

		self.assertEqual(json.loads(self.alvo.read_text(encoding="utf-8")), {"db_type": "postgres"})
		self.assertEqual(self._pasta(), antes)
		self.assertFalse([n for n in self._pasta() if n.endswith(".tmp")])


class TestAppsTxt(_ComBench):
	def test_grava_sempre_com_quebra_de_linha_final(self):
		cfg.gravar_apps_txt(self.bench.apps_txt, ["frappe", "erpnext", "erpnext_brasil"])
		conteudo = self.bench.apps_txt.read_bytes()
		self.assertTrue(conteudo.endswith(b"\n"), conteudo)
		self.assertEqual(conteudo, b"frappe\nerpnext\nerpnext_brasil\n")

	def test_limpa_vazios_espacos_e_repetidos(self):
		texto = cfg.gravar_apps_txt(self.bench.apps_txt, ["frappe", "", "  erpnext ", "erpnext", "hrms"])
		self.assertEqual(texto, "frappe\nerpnext\nhrms\n")

	def test_frappe_vai_para_o_inicio(self):
		texto = cfg.gravar_apps_txt(self.bench.apps_txt, ["erpnext", "frappe"])
		self.assertEqual(texto.split(), ["frappe", "erpnext"])

	def test_frappe_ausente_e_acrescentado(self):
		texto = cfg.gravar_apps_txt(self.bench.apps_txt, ["erpnext_brasil"])
		self.assertEqual(texto.split(), ["frappe", "erpnext_brasil"])

	def test_vazio_e_erro(self):
		with self.assertRaises(cfg.CherryInvalido):
			cfg.gravar_apps_txt(self.bench.apps_txt, ["", "  "])

	def test_nome_com_espaco_barra_ou_caractere_de_shell_e_erro(self):
		for ruim in ("erp next", "apps/erpnext", "x;touch${IFS}y", "$(id)", "a`b`"):
			with self.subTest(ruim=ruim), self.assertRaises(cfg.CherryInvalido):
				cfg.gravar_apps_txt(self.bench.apps_txt, ["frappe", ruim])

	def test_ler_ignora_linhas_vazias_e_le_sem_quebra_final(self):
		"""O arquivo sem `\\n` final (o caso real do bench-16) ainda é lido inteiro."""
		self.bench.apps_txt.write_bytes(b"frappe\n\nerpnext\nerpnext_brasil")
		self.assertEqual(cfg.ler_apps_txt(self.bench.apps_txt), ["frappe", "erpnext", "erpnext_brasil"])

	def test_ler_ausente_e_lista_vazia(self):
		self.assertEqual(cfg.ler_apps_txt(self.raiz / "nada.txt"), [])


class TestCaminhoWsl(unittest.TestCase):
	def test_traduz_para_unc(self):
		caminho = cfg.caminho_wsl("Ubuntu", "/home/x/frappe-bench-16")
		self.assertEqual(
			PureWindowsPath(caminho), PureWindowsPath(r"\\wsl.localhost\Ubuntu\home\x\frappe-bench-16")
		)

	def test_relativo_e_erro(self):
		with self.assertRaises(cfg.CherryInvalido):
			cfg.caminho_wsl("Ubuntu", "frappe-bench")

	def test_distro_vazia_e_erro(self):
		with self.assertRaises(cfg.CherryInvalido):
			cfg.caminho_wsl("  ", "/home/x")


class TestBench(_ComBench):
	def test_lista_so_diretorios_com_site_config(self):
		self.assertEqual(self.bench.nomes_de_sites(), ["um.localhost"])

	def test_site_desconhecido_e_erro(self):
		with self.assertRaises(cfg.CherryInvalido):
			self.bench.site_config("orfao")

	def test_site_config_aponta_para_o_arquivo(self):
		self.assertEqual(cfg.ler_json(self.bench.site_config("um.localhost")), {"db_name": "_abc"})

	def test_bench_inexistente(self):
		bench = cfg.Bench(self.raiz / "nao")
		self.assertFalse(bench.existe())
		self.assertEqual(bench.nomes_de_sites(), [])

	def test_no_wsl_exige_distro_e_caminho(self):
		self.assertFalse(cfg.Bench(self.raiz).no_wsl)
		self.assertFalse(cfg.Bench(self.raiz, distro="Ubuntu").no_wsl)
		self.assertTrue(cfg.Bench(self.raiz, "Ubuntu", "/home/x/b").no_wsl)


class TestBanco(unittest.TestCase):
	def test_porta_padrao_por_tipo(self):
		self.assertEqual(cfg.Banco(cfg.MARIADB).porta, 3306)
		self.assertEqual(cfg.Banco(cfg.POSTGRES).porta, 5432)

	def test_porta_informada_vence_a_padrao(self):
		self.assertEqual(cfg.Banco(cfg.MARIADB, porta=3307).porta, 3307)

	def test_tipo_desconhecido_e_erro(self):
		with self.assertRaises(cfg.CherryInvalido):
			cfg.Banco("sqlite")

	def test_host_vazio_e_porta_fora_da_faixa_sao_erro(self):
		with self.assertRaises(cfg.CherryInvalido):
			cfg.Banco(cfg.POSTGRES, host="  ")

		with self.assertRaises(cfg.CherryInvalido):
			cfg.Banco(cfg.POSTGRES, porta=70000)

	def test_senha_nao_aparece_no_repr(self):
		self.assertNotIn("segredo", repr(cfg.Banco(cfg.POSTGRES, senha_root="segredo")))

	def test_chaves_do_common_config_sao_as_que_o_frappe_le(self):
		"""`frappe/installer.py::install_db` e `postgres/setup_db.py::get_root_connection`."""
		banco = cfg.Banco(cfg.POSTGRES, "127.0.0.1", 5432, "postgres", "postgres")
		self.assertEqual(
			banco.chaves_common_config(),
			{
				"db_type": "postgres",
				"db_host": "127.0.0.1",
				"db_port": 5432,
				"root_login": "postgres",
				"root_password": "postgres",
			},
		)

	def test_sem_root_nao_grava_chave_vazia(self):
		chaves = cfg.Banco(cfg.MARIADB).chaves_common_config()
		self.assertNotIn("root_login", chaves)
		self.assertNotIn("root_password", chaves)


class TestComandoNewSite(unittest.TestCase):
	def test_postgres_completo(self):
		banco = cfg.Banco(cfg.POSTGRES, "127.0.0.1", 5432, "postgres", "postgres")
		comando = cfg.comando_new_site(banco, "v16pg.localhost", "admin", ("erpnext", "erpnext_brasil"))
		plano = comando.replace(" \\\n    ", " ")
		self.assertEqual(
			plano,
			"bench new-site v16pg.localhost --db-type postgres --db-host 127.0.0.1 --db-port 5432 "
			"--db-root-username postgres --db-root-password 'postgres' --admin-password 'admin' "
			"--install-app erpnext --install-app erpnext_brasil",
		)

	def test_senha_com_aspas_simples_sobrevive_ao_shell(self):
		banco = cfg.Banco(cfg.MARIADB, senha_root="a'b$c")
		self.assertIn("--db-root-password 'a'\"'\"'b$c'", cfg.comando_new_site(banco, "s.localhost"))

	def test_site_invalido_e_erro(self):
		for ruim in ("", "com espaco"):
			with self.subTest(ruim=ruim), self.assertRaises(cfg.CherryInvalido):
				cfg.comando_new_site(cfg.Banco(cfg.MARIADB), ruim)

	def test_senha_de_administrador_vazia_nao_entra_no_comando(self):
		"""O `bench` pergunta no terminal; a senha não fica no comando nem na área de transferência."""
		comando = cfg.comando_new_site(cfg.Banco(cfg.MARIADB), "s.localhost", "")
		self.assertNotIn("--admin-password", comando)

	def test_valores_que_o_shell_interpretaria_sao_recusados(self):
		"""CH-03: host, usuário, site e app saem sem aspas; `;`, `$(...)` e crase precisam ser barrados."""
		hostis = ("127.0.0.1;touch${IFS}/tmp/h", "root;id", "a.localhost$(id)", "x`id`", "a b", "a/b", "a&b")

		for hostil in hostis:
			with self.subTest(hostil=hostil):
				with self.assertRaises(cfg.CherryInvalido):
					cfg.comando_new_site(cfg.Banco(cfg.MARIADB, hostil), "s.localhost")

				with self.assertRaises(cfg.CherryInvalido):
					cfg.comando_new_site(cfg.Banco(cfg.MARIADB, usuario_root=hostil), "s.localhost")

				with self.assertRaises(cfg.CherryInvalido):
					cfg.comando_new_site(cfg.Banco(cfg.MARIADB), hostil)

				with self.assertRaises(cfg.CherryInvalido):
					cfg.comando_new_site(cfg.Banco(cfg.MARIADB), "s.localhost", apps=(hostil,))

	def test_nomes_comuns_continuam_aceitos(self):
		banco = cfg.Banco(cfg.POSTGRES, "db-1.interno", 5432, "app_user@srv")
		comando = cfg.comando_new_site(banco, "v16-pg.localhost", apps=("erpnext_brasil",))
		self.assertIn("--db-host db-1.interno", comando)
		self.assertIn("--db-root-username app_user@srv", comando)


class _Executor:
	"""Substitui `subprocess.run`: devolve o que cada comando 'imprimiria', e anota o que recebeu."""

	def __init__(self, *respostas):
		self.respostas = list(respostas)
		self.comandos: list[list[str]] = []
		self.ambientes: list[dict] = []

	def __call__(self, comando, **opcoes):
		self.comandos.append(list(comando))
		self.ambientes.append(opcoes.get("env") or {})
		resposta = self.respostas.pop(0)

		if isinstance(resposta, Exception):
			raise resposta

		return subprocess.CompletedProcess(comando, 0, stdout=resposta, stderr="")


class TestTestarConexao(unittest.TestCase):
	def setUp(self):
		self.banco = cfg.Banco(cfg.POSTGRES, "127.0.0.1", 5432, "postgres", "postgres")
		self.bench_wsl = cfg.Bench(Path("."), "Ubuntu", "/home/x/frappe-bench-16")

	def test_venv_do_bench_autentica(self):
		executor = _Executor("OK PostgreSQL 18.6\n")

		with mock.patch.object(cfg.shutil, "which", return_value="wsl"):
			resultado = cfg.testar_conexao(self.banco, self.bench_wsl, executar=executor)

		self.assertTrue(resultado.ok)
		self.assertEqual(resultado.nivel, "autenticacao")
		self.assertIn("PostgreSQL 18.6", resultado.mensagem)
		self.assertEqual(executor.comandos[0][:4], ["wsl", "-d", "Ubuntu", "--"])
		self.assertEqual(executor.comandos[0][4], "/home/x/frappe-bench-16/env/bin/python")
		self.assertEqual(executor.comandos[0][-4:], ["postgres", "127.0.0.1", "5432", "postgres"])

	def test_a_senha_nunca_vai_em_argumento_de_processo(self):
		"""CH-01: a linha de comando de um processo é legível por qualquer outro — a senha vai pelo ambiente."""
		segredo = "segredo-que-nao-pode-vazar"
		banco = cfg.Banco(cfg.POSTGRES, "127.0.0.1", 5432, "postgres", segredo)
		executor = _Executor("OK PostgreSQL 18.6\n")

		with mock.patch.object(cfg.shutil, "which", return_value="wsl"):
			cfg.testar_conexao(banco, self.bench_wsl, executar=executor)

		for comando in executor.comandos:
			self.assertFalse([a for a in comando if segredo in a], f"senha em argv: {comando[:5]}")

		self.assertEqual(executor.ambientes[0][cfg.VARIAVEL_DA_SENHA], segredo)

	def test_o_wslenv_leva_a_senha_ao_linux_sem_perder_o_que_ja_havia(self):
		executor = _Executor("OK PostgreSQL 18.6\n")

		with (
			mock.patch.object(cfg.shutil, "which", return_value="wsl"),
			mock.patch.dict(cfg.os.environ, {"WSLENV": "OUTRA/p:CHERRY_SENHA_ROOT:X"}),
		):
			cfg.testar_conexao(self.banco, self.bench_wsl, executar=executor)

		partes = executor.ambientes[0]["WSLENV"].split(":")
		self.assertEqual(partes.count(cfg.VARIAVEL_DA_SENHA), 1)
		self.assertIn("OUTRA/p", partes)
		self.assertIn("X", partes)

	def test_a_sonda_local_tambem_recebe_a_senha_pelo_ambiente(self):
		banco = cfg.Banco(cfg.POSTGRES, "127.0.0.1", 5432, "postgres", "outro-segredo")
		executor = _Executor("OK PostgreSQL 18.6\n")

		cfg.testar_conexao(banco, None, executar=executor)

		self.assertEqual(executor.comandos[0][-4:], ["postgres", "127.0.0.1", "5432", "postgres"])
		self.assertFalse([a for a in executor.comandos[0] if "outro-segredo" in a])
		self.assertEqual(executor.ambientes[0][cfg.VARIAVEL_DA_SENHA], "outro-segredo")

	def test_falha_de_autenticacao_e_reportada_nao_mascarada_por_tcp(self):
		executor = _Executor("FALHA OperationalError: password authentication failed\n")

		with mock.patch.object(cfg.shutil, "which", return_value="wsl"):
			resultado = cfg.testar_conexao(self.banco, self.bench_wsl, executar=executor)

		self.assertFalse(resultado.ok)
		self.assertEqual(resultado.nivel, "autenticacao")
		self.assertIn("password authentication failed", resultado.mensagem)
		self.assertEqual(
			len(executor.comandos), 1, "não deve cair para o driver local depois de uma falha real"
		)

	def test_sem_driver_no_bench_cai_para_o_driver_local(self):
		executor = _Executor("FALHA ModuleNotFoundError: No module named 'psycopg2'\n", "OK MariaDB 10.11\n")

		with mock.patch.object(cfg.shutil, "which", return_value="wsl"):
			resultado = cfg.testar_conexao(self.banco, self.bench_wsl, executar=executor)

		self.assertTrue(resultado.ok)
		self.assertEqual(executor.comandos[1][0], "python")

	def test_sem_bench_no_wsl_nao_chama_wsl(self):
		executor = _Executor("OK x\n")
		cfg.testar_conexao(self.banco, cfg.Bench(Path(".")), executar=executor)
		self.assertEqual(executor.comandos[0][0], "python")

	def test_sem_driver_nenhum_cai_para_tcp(self):
		executor = _Executor(OSError("sem python"))

		with mock.patch.object(cfg.socket, "create_connection", side_effect=OSError("recusada")):
			resultado = cfg.testar_conexao(self.banco, None, executar=executor)

		self.assertFalse(resultado.ok)
		self.assertEqual(resultado.nivel, "tcp")
		self.assertIn("recusada", resultado.mensagem)

	def test_tcp_aberto_diz_que_nao_autenticou(self):
		executor = _Executor(subprocess.TimeoutExpired("python", 30))
		conexao = mock.MagicMock()
		conexao.__enter__.return_value = conexao

		with mock.patch.object(cfg.socket, "create_connection", return_value=conexao):
			resultado = cfg.testar_conexao(self.banco, None, executar=executor)

		self.assertTrue(resultado.ok)
		self.assertEqual(resultado.nivel, "tcp")
		self.assertIn("nenhum driver", resultado.mensagem)

	def test_saida_inesperada_da_sonda_nao_e_sucesso(self):
		executor = _Executor("lixo qualquer\n")

		with mock.patch.object(cfg.socket, "create_connection", side_effect=OSError("x")):
			resultado = cfg.testar_conexao(self.banco, None, executar=executor)

		self.assertEqual(resultado.nivel, "tcp")


class TestSondaEmbutida(unittest.TestCase):
	"""A sonda é código Python dentro de uma string — pelo menos precisa compilar."""

	def test_compila(self):
		compile(cfg._SONDA_PYTHON, "<sonda>", "exec")

	def test_cobre_os_dois_bancos(self):
		self.assertTrue(re.search(r"psycopg2", cfg._SONDA_PYTHON))
		self.assertTrue(re.search(r"MySQLdb|pymysql", cfg._SONDA_PYTHON))


if __name__ == "__main__":
	unittest.main()
