# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da configuração Docker (`docker/`): estrutura, segurança por padrão e scripts de apoio.

Três camadas, da mais barata à mais fiel:

1. **Estrutura** (sem Docker): os arquivos têm os serviços esperados, a porta é local, nenhum segredo está
   escrito, o `apps.json` é válido, e os arquivos de contêiner usam só `LF`.
2. **Scripts** (sem Docker): `preparar.py` e `construir.py` cumprem seus contratos (não sobrescreve segredo,
   não imprime valor, comando como lista de argumentos, commit fixado, conteúdo do `apps.json` fora do comando).
3. **Resolução real do Compose** (com Docker): `docker compose config` em JSON para cada banco, conferindo
   portas publicadas, rótulos de instância, segredos montados e que o serviço de criação de site só existe com
   o perfil. Pulado, com o motivo escrito, quando não há Docker (por exemplo, no Windows sem Docker).
"""

import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

DOCKER = Path(__file__).resolve().parents[2] / "docker"
COMPOSE = DOCKER / "compose.yaml"
BANCOS = {"mariadb": DOCKER / "compose.mariadb.yaml", "postgres": DOCKER / "compose.postgres.yaml"}
ENV_EXEMPLO = DOCKER / ".env.example"
ARQUIVOS_DO_COMPOSE = (COMPOSE, *BANCOS.values())


def _carregar(nome: str):
	"""Os scripts de `docker/` não são um pacote: carrega-se pelo caminho do arquivo."""
	especificacao = importlib.util.spec_from_file_location(f"docker_{nome}", DOCKER / f"{nome}.py")
	modulo = importlib.util.module_from_spec(especificacao)
	sys.modules[especificacao.name] = modulo
	especificacao.loader.exec_module(modulo)

	return modulo


preparar = _carregar("preparar")
construir = _carregar("construir")


def _texto(caminho: Path) -> str:
	return caminho.read_text(encoding="utf-8")


class TestEstrutura(unittest.TestCase):
	SERVICOS_DA_BASE = (
		"redis-cache",
		"redis-queue",
		"configurator",
		"create-site",
		"backend",
		"frontend",
		"websocket",
		"queue-short",
		"queue-long",
		"scheduler",
	)

	def test_a_base_tem_todos_os_servicos_e_nenhum_banco(self):
		texto = _texto(COMPOSE)

		for servico in self.SERVICOS_DA_BASE:
			self.assertRegex(texto, rf"(?m)^  {re.escape(servico)}:\s*$", f"falta o serviço {servico}")

		self.assertNotRegex(texto, r"(?m)^  db:\s*$", "o banco entra por override, a escolha é do Cherry")

	def test_cada_override_define_o_banco_certo(self):
		maria, postgres = _texto(BANCOS["mariadb"]), _texto(BANCOS["postgres"])

		self.assertRegex(maria, r"(?m)^  db:\s*$")
		self.assertIn("image: mariadb:", maria)
		self.assertIn("utf8mb4", maria)
		self.assertIn("DB_TIPO: mariadb", maria)
		self.assertNotIn("image: postgres", maria)
		self.assertIn("image: postgres:", postgres)
		self.assertIn("DB_TIPO: postgres", postgres)
		self.assertNotIn("image: mariadb", postgres)

	def test_senha_do_banco_vai_por_arquivo(self):
		self.assertIn("MYSQL_ROOT_PASSWORD_FILE: /run/secrets/db_password", _texto(BANCOS["mariadb"]))
		self.assertIn("POSTGRES_PASSWORD_FILE: /run/secrets/db_password", _texto(BANCOS["postgres"]))
		self.assertRegex(_texto(COMPOSE), r"(?s)secrets:\s+db_password:\s+file:")

	def test_nenhuma_senha_em_claro_nos_arquivos_do_compose(self):
		proibidos = re.compile(
			r"(?m)^\s*(MYSQL_ROOT_PASSWORD|MARIADB_ROOT_PASSWORD|POSTGRES_PASSWORD|DB_PASSWORD|ADMIN_PASSWORD)\s*:"
		)

		for arquivo in ARQUIVOS_DO_COMPOSE:
			with self.subTest(arquivo=arquivo.name):
				self.assertIsNone(
					proibidos.search(_texto(arquivo)), "senha em variável de ambiente, e não por arquivo"
				)

	def test_so_o_proxy_publica_porta_e_so_no_computador_local(self):
		self.assertEqual(sum(_texto(a).count("ports:") for a in ARQUIVOS_DO_COMPOSE), 1)
		self.assertIn('"${ENDERECO:-127.0.0.1}:${PORTA_WEB:-8080}:8080"', _texto(COMPOSE))

	def test_sem_novos_privilegios_nos_servicos(self):
		self.assertGreaterEqual(_texto(COMPOSE).count("no-new-privileges:true"), 3)

		for arquivo in BANCOS.values():
			self.assertIn("no-new-privileges:true", _texto(arquivo))

	def test_rotulos_de_instancia_e_nome_do_projeto(self):
		texto = _texto(COMPOSE)
		self.assertIn("br.erpnext-brasil.instancia: ${SODA_INSTANCE_ID:-}", texto)
		self.assertIn("br.erpnext-brasil.descritivo: ${SODA_DESCRITIVO:-}", texto)
		self.assertIn("name: ${COMPOSE_PROJECT_NAME:-erpnext-brasil}", texto)

	def test_a_criacao_de_site_so_roda_sob_perfil_e_le_os_segredos_de_arquivo(self):
		texto = _texto(COMPOSE)
		self.assertIn("profiles: [inicializacao]", texto)
		self.assertIn("/run/secrets/admin_password", texto)
		self.assertIn("/run/secrets/db_password", texto)
		self.assertIn("--install-app erpnext --install-app erpnext_brasil", texto)

	def test_env_exemplo_nao_tem_segredo(self):
		sensivel = re.compile(r"(?i)(pass|senha|token|secret|segredo|key|chave)")

		for linha in _texto(ENV_EXEMPLO).splitlines():
			if not linha.strip() or linha.lstrip().startswith("#") or "=" not in linha:
				continue

			nome, _, valor = linha.partition("=")

			if sensivel.search(nome):
				self.assertEqual(valor.strip(), "", f"{nome} tem valor no exemplo")

	def test_env_exemplo_fixa_o_separador_do_compose_para_os_dois_sistemas(self):
		texto = _texto(ENV_EXEMPLO)
		self.assertIn("COMPOSE_PATH_SEPARATOR=,", texto)
		self.assertIn("COMPOSE_FILE=compose.yaml,compose.mariadb.yaml", texto)

	def test_apps_json_traz_o_erpnext_e_o_erpnext_brasil_sem_credencial(self):
		apps = json.loads(_texto(DOCKER / "apps.json"))
		urls = [a["url"] for a in apps]

		self.assertTrue(any(u.endswith("/erpnext") for u in urls))
		self.assertTrue(any(u.endswith("/erpnext_brasil") for u in urls))
		self.assertFalse(
			[u for u in urls if re.search(r"://[^/]*@", u)], "credencial no apps.json versionado"
		)
		self.assertEqual({a["branch"] for a in apps if a["url"].endswith("/erpnext")}, {"version-16"})

	def test_gitignore_protege_segredos_e_configuracao_local(self):
		texto = _texto(DOCKER / ".gitignore")

		for padrao in ("segredos/", ".env", "apps.local.json"):
			self.assertIn(padrao, texto)

	def test_arquivos_de_conteiner_usam_so_lf(self):
		arquivos = [
			*ARQUIVOS_DO_COMPOSE,
			ENV_EXEMPLO,
			DOCKER / "apps.json",
			DOCKER / "preparar.py",
			DOCKER / "construir.py",
		]

		for arquivo in arquivos:
			with self.subTest(arquivo=arquivo.name):
				self.assertNotIn(b"\r\n", arquivo.read_bytes())

		self.assertIn("eol=lf", _texto(DOCKER / ".gitattributes"))


class TestPreparar(unittest.TestCase):
	def setUp(self):
		self._pasta = tempfile.TemporaryDirectory()
		self.addCleanup(self._pasta.cleanup)
		self.pasta = Path(self._pasta.name) / "segredos"

	def test_cria_os_dois_segredos_aleatorios_e_seguros_para_o_shell(self):
		situacao = preparar.gerar_segredos(self.pasta)

		self.assertEqual(situacao, {"db_password": "criado", "admin_password": "criado"})
		valores = {n: (self.pasta / n).read_text(encoding="utf-8") for n in preparar.NOMES_DOS_SEGREDOS}

		for valor in valores.values():
			self.assertGreaterEqual(len(valor), 30)
			self.assertIsNotNone(
				re.fullmatch(r"[A-Za-z0-9_-]+", valor), "caractere que o shell poderia interpretar"
			)

		self.assertEqual(len(set(valores.values())), 2, "os dois segredos precisam ser diferentes")

	def test_nao_sobrescreve_segredo_existente(self):
		preparar.gerar_segredos(self.pasta)
		antes = {n: (self.pasta / n).read_bytes() for n in preparar.NOMES_DOS_SEGREDOS}

		situacao = preparar.gerar_segredos(self.pasta)

		self.assertEqual(situacao, {"db_password": "mantido", "admin_password": "mantido"})
		self.assertEqual({n: (self.pasta / n).read_bytes() for n in preparar.NOMES_DOS_SEGREDOS}, antes)

	def test_cria_so_o_que_falta(self):
		self.pasta.mkdir(parents=True)
		(self.pasta / "db_password").write_text("ja-existe-e-vale", encoding="utf-8")

		situacao = preparar.gerar_segredos(self.pasta)

		self.assertEqual(situacao, {"db_password": "mantido", "admin_password": "criado"})
		self.assertEqual((self.pasta / "db_password").read_text(encoding="utf-8"), "ja-existe-e-vale")

	def test_segredo_vazio_e_recusado_e_nao_e_alterado(self):
		self.pasta.mkdir(parents=True)
		(self.pasta / "db_password").write_bytes(b"")

		with self.assertRaises(preparar.SegredoInvalido):
			preparar.gerar_segredos(self.pasta)

		self.assertEqual((self.pasta / "db_password").read_bytes(), b"")

	def test_o_gerador_e_injetavel(self):
		preparar.gerar_segredos(self.pasta, gerar=lambda: "fixo-para-teste")
		self.assertEqual((self.pasta / "db_password").read_text(encoding="utf-8"), "fixo-para-teste")

	@unittest.skipUnless(
		os.name == "posix", "permissão 0600 só existe em Linux e no WSL; no Windows vale a ACL da pasta"
	)
	def test_arquivos_nascem_so_do_dono(self):
		preparar.gerar_segredos(self.pasta)

		for nome in preparar.NOMES_DOS_SEGREDOS:
			self.assertEqual((self.pasta / nome).stat().st_mode & 0o777, 0o600)

	def test_a_saida_nunca_traz_o_valor_gerado(self):
		saida, erro = io.StringIO(), io.StringIO()

		with redirect_stdout(saida), redirect_stderr(erro):
			self.assertEqual(preparar.main(["--pasta", str(self.pasta)]), 0)

		visivel = saida.getvalue() + erro.getvalue()

		for nome in preparar.NOMES_DOS_SEGREDOS:
			self.assertIn(nome, visivel)
			self.assertNotIn((self.pasta / nome).read_text(encoding="utf-8"), visivel)

	def test_main_recusa_segredo_vazio_com_codigo_de_erro(self):
		self.pasta.mkdir(parents=True)
		(self.pasta / "admin_password").write_bytes(b"")
		erro = io.StringIO()

		with redirect_stderr(erro), redirect_stdout(io.StringIO()):
			self.assertEqual(preparar.main(["--pasta", str(self.pasta)]), 2)

		self.assertIn("Não foi possível", erro.getvalue())


class TestConstruir(unittest.TestCase):
	def setUp(self):
		self._pasta = tempfile.TemporaryDirectory()
		self.addCleanup(self._pasta.cleanup)
		self.pasta = Path(self._pasta.name)
		self.apps = self.pasta / "apps.local.json"
		self.apps.write_text(
			json.dumps([{"url": "https://ghp_TOKEN_SECRETO@github.com/dono/privado", "branch": "main"}]),
			encoding="utf-8",
		)

	def test_o_commit_padrao_esta_fixado(self):
		self.assertRegex(construir.FRAPPE_DOCKER_COMMIT, r"[0-9a-f]{40}")

	def test_o_comando_e_uma_lista_de_argumentos_com_a_receita_fixada(self):
		comando = construir.comando_de_build(apps=self.apps)

		self.assertIsInstance(comando, list)
		self.assertTrue(all(isinstance(a, str) for a in comando))
		self.assertEqual(comando[:2], ["docker", "build"])
		self.assertIn("FRAPPE_BRANCH=version-16", comando)
		self.assertIn("images/layered/Containerfile", comando)
		self.assertTrue(comando[-1].endswith("#" + construir.FRAPPE_DOCKER_COMMIT))
		self.assertEqual(comando[comando.index("--tag") + 1], "erpnext-brasil:version-16")

	def test_o_conteudo_do_apps_json_nunca_aparece_no_comando(self):
		comando = construir.comando_de_build(apps=self.apps)
		segredo = comando[comando.index("--secret") + 1]

		self.assertEqual(segredo, f"id=apps_json,src={self.apps.resolve()}")
		self.assertFalse([a for a in comando if "TOKEN_SECRETO" in a], "a credencial vazou para o comando")

	def test_o_apps_json_versionado_serve(self):
		self.assertEqual(construir.comando_de_build(apps=construir.APPS_PADRAO)[1], "build")

	def test_entradas_invalidas_sao_recusadas_antes_de_executar(self):
		invalidas = [
			{"tag": "etiqueta com espaço"},
			{"tag": "; rm -rf /"},
			{"imagem": "Imagem/Maiuscula"},
			{"imagem": "img$(id)"},
			{"commit": "main"},
			{"commit": "abc123"},
			{"commit": "G" * 40},
			{"ramo": "ramo com espaço"},
			{"ramo": "$(id)"},
		]

		for opcoes in invalidas:
			with self.subTest(opcoes=opcoes), self.assertRaises(construir.ConstrucaoInvalida):
				construir.comando_de_build(apps=self.apps, **opcoes)

	def test_apps_json_ausente_ilegivel_ou_vazio_e_recusado(self):
		(self.pasta / "ruim.json").write_text("{quebrado", encoding="utf-8")
		(self.pasta / "vazio.json").write_text("[]", encoding="utf-8")
		(self.pasta / "sem_url.json").write_text('[{"branch": "main"}]', encoding="utf-8")
		(self.pasta / "objeto.json").write_text("{}", encoding="utf-8")

		for nome in ("nao_existe.json", "ruim.json", "vazio.json", "sem_url.json", "objeto.json"):
			with self.subTest(arquivo=nome), self.assertRaises(construir.ConstrucaoInvalida):
				construir.comando_de_build(apps=self.pasta / nome)

	def test_a_mensagem_de_erro_nao_repete_o_conteudo_do_apps_json(self):
		(self.pasta / "ruim.json").write_text("{quebrado TOKEN_SECRETO", encoding="utf-8")

		with self.assertRaises(construir.ConstrucaoInvalida) as contexto:
			construir.comando_de_build(apps=self.pasta / "ruim.json")

		self.assertNotIn("TOKEN_SECRETO", str(contexto.exception))

	def test_main_mostrar_nao_executa_nada(self):
		saida = io.StringIO()

		with mock.patch.object(construir.subprocess, "run") as executar, redirect_stdout(saida):
			self.assertEqual(construir.main(["--apps", str(self.apps), "--mostrar"]), 0)

		executar.assert_not_called()
		self.assertIn("docker build", saida.getvalue())
		self.assertNotIn("TOKEN_SECRETO", saida.getvalue())

	def test_main_executa_sem_shell_e_devolve_o_codigo_do_docker(self):
		with (
			mock.patch.object(construir.shutil, "which", return_value="/usr/bin/docker"),
			mock.patch.object(construir.subprocess, "run", return_value=mock.Mock(returncode=7)) as executar,
			redirect_stdout(io.StringIO()),
		):
			codigo = construir.main(["--apps", str(self.apps)])

		self.assertEqual(codigo, 7)
		argumentos, opcoes = executar.call_args
		self.assertIsInstance(argumentos[0], list)
		self.assertNotIn("shell", opcoes)
		self.assertEqual(opcoes["env"]["DOCKER_BUILDKIT"], "1")

	def test_main_sem_docker_orienta_e_nao_executa(self):
		erro = io.StringIO()

		with (
			mock.patch.object(construir.shutil, "which", return_value=None),
			mock.patch.object(construir.subprocess, "run") as executar,
			redirect_stderr(erro),
		):
			self.assertEqual(construir.main(["--apps", str(self.apps)]), 3)

		executar.assert_not_called()
		self.assertIn("Docker", erro.getvalue())

	def test_main_com_entrada_invalida_recusa_com_codigo_de_erro(self):
		erro = io.StringIO()

		with redirect_stderr(erro):
			self.assertEqual(construir.main(["--apps", str(self.apps), "--tag", "x y"]), 2)

		self.assertIn("Não foi possível", erro.getvalue())


def _docker_disponivel() -> bool:
	if shutil.which("docker") is None:
		return False

	try:
		return (
			subprocess.run(
				["docker", "compose", "version"], capture_output=True, timeout=30, check=False
			).returncode
			== 0
		)
	except (OSError, subprocess.TimeoutExpired):
		return False


@unittest.skipUnless(
	_docker_disponivel(),
	"sem Docker com o plugin compose nesta máquina (por exemplo, Windows sem Docker); o CI e o WSL2 o têm",
)
class TestResolucaoReal(unittest.TestCase):
	"""`docker compose config` de verdade, em JSON, para cada banco."""

	def setUp(self):
		self._pasta = tempfile.TemporaryDirectory()
		self.addCleanup(self._pasta.cleanup)
		pasta = Path(self._pasta.name)
		(pasta / "db").write_text("segredo-de-teste-db", encoding="utf-8")
		(pasta / "adm").write_text("segredo-de-teste-admin", encoding="utf-8")
		self.ambiente = {
			**os.environ,
			"DB_PASSWORD_ARQUIVO": str(pasta / "db"),
			"ADMIN_PASSWORD_ARQUIVO": str(pasta / "adm"),
			"SITE_NAME": "erp.localhost",
		}

	def _resolver(self, banco: str, *, perfil: bool = False, extra: dict | None = None) -> dict:
		comando = [
			"docker",
			"compose",
			"--project-directory",
			str(DOCKER),
			"--env-file",
			str(ENV_EXEMPLO),
			"-f",
			str(COMPOSE),
			"-f",
			str(BANCOS[banco]),
		]

		if perfil:
			comando += ["--profile", "inicializacao"]

		resultado = subprocess.run(
			[*comando, "config", "--format", "json"],
			capture_output=True,
			text=True,
			env={**self.ambiente, **(extra or {})},
			timeout=60,
			check=False,
		)
		self.assertEqual(resultado.returncode, 0, resultado.stderr)

		return json.loads(resultado.stdout)

	def test_resolve_com_cada_banco_e_so_um_banco(self):
		for banco, imagem in (("mariadb", "mariadb:"), ("postgres", "postgres:")):
			with self.subTest(banco=banco):
				servicos = self._resolver(banco)["services"]
				self.assertIn("db", servicos)
				self.assertTrue(servicos["db"]["image"].startswith(imagem))
				self.assertEqual(servicos["configurator"]["environment"]["DB_TIPO"], banco)

	def test_so_o_proxy_publica_porta_e_em_127_0_0_1(self):
		for banco in BANCOS:
			with self.subTest(banco=banco):
				servicos = self._resolver(banco)["services"]
				publicam = {nome: s["ports"] for nome, s in servicos.items() if s.get("ports")}

				self.assertEqual(list(publicam), ["frontend"])
				self.assertEqual(publicam["frontend"][0]["host_ip"], "127.0.0.1")
				self.assertEqual(str(publicam["frontend"][0]["target"]), "8080")

	def test_a_criacao_de_site_so_existe_com_o_perfil(self):
		self.assertNotIn("create-site", self._resolver("mariadb")["services"])
		self.assertIn("create-site", self._resolver("mariadb", perfil=True)["services"])

	def test_os_rotulos_de_instancia_chegam_aos_servicos_de_aplicacao(self):
		extra = {
			"SODA_INSTANCE_ID": "1f3c9e2b-aaaa-4bbb-8ccc-0123456789ab",
			"SODA_DESCRITIVO": "NF-e em homologação",
		}
		servicos = self._resolver("mariadb", extra=extra)["services"]

		for nome in (
			"backend",
			"frontend",
			"websocket",
			"queue-short",
			"queue-long",
			"scheduler",
			"configurator",
		):
			with self.subTest(servico=nome):
				self.assertEqual(
					servicos[nome]["labels"]["br.erpnext-brasil.instancia"], extra["SODA_INSTANCE_ID"]
				)
				self.assertEqual(
					servicos[nome]["labels"]["br.erpnext-brasil.descritivo"], extra["SODA_DESCRITIVO"]
				)

	def test_segredos_montados_e_nenhuma_senha_em_claro_no_resultado(self):
		for banco in BANCOS:
			with self.subTest(banco=banco):
				bruto = json.dumps(self._resolver(banco, perfil=True))

				self.assertNotIn("segredo-de-teste-db", bruto)
				self.assertNotIn("segredo-de-teste-admin", bruto)
				self.assertIn("/run/secrets/db_password", bruto)

	def test_a_ordem_de_subida_e_por_saude(self):
		servicos = self._resolver("mariadb")["services"]

		self.assertEqual(servicos["configurator"]["depends_on"]["db"]["condition"], "service_healthy")
		self.assertEqual(
			servicos["backend"]["depends_on"]["configurator"]["condition"], "service_completed_successfully"
		)
		self.assertEqual(servicos["frontend"]["depends_on"]["backend"]["condition"], "service_healthy")

	def test_dois_projetos_nao_colidem_em_nome_nem_em_volume(self):
		a = self._resolver("mariadb", extra={"COMPOSE_PROJECT_NAME": "erp-aaaa1111", "PORTA_WEB": "8101"})
		b = self._resolver("mariadb", extra={"COMPOSE_PROJECT_NAME": "erp-bbbb2222", "PORTA_WEB": "8102"})

		self.assertNotEqual(a["name"], b["name"])
		self.assertTrue(all(v["name"].startswith("erp-aaaa1111") for v in a["volumes"].values()))
		self.assertTrue(all(v["name"].startswith("erp-bbbb2222") for v in b["volumes"].values()))
		self.assertNotEqual(
			a["services"]["frontend"]["ports"][0]["published"],
			b["services"]["frontend"]["ports"][0]["published"],
		)


if __name__ == "__main__":
	unittest.main()
