# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Cherry — o núcleo sem interface: os arquivos que se configuram à mão num bench.

Por que existe
--------------
Cada arquivo abaixo já custou uma rodada de diagnóstico neste projeto, e todos são editados
à mão, sem validação nenhuma:

- `sites/common_site_config.json` — banco (`db_type`, `db_host`, `db_port`, `root_login`,
  `root_password`), Redis, portas, `default_site`, `developer_mode`. É daqui que o
  `bench new-site` lê o tipo de banco e as credenciais de root quando não as recebe na
  linha de comando (`frappe/installer.py::install_db` e
  `frappe/database/postgres/setup_db.py::get_root_connection`, lidos na fonte).
- `sites/<site>/site_config.json` — o banco daquele site e `allow_tests`, exigido pelo
  `bench run-tests`.
- `sites/apps.txt` — a lista do que o bench considera instalável. **Sem `\\n` final, o último
  app some** (`docs/banco-do-bench-v16.md`, item 4b) — e isto já aconteceu duas vezes.

Este módulo é a única porta de escrita do Cherry: a interface (`app.py`) só chama o que
está aqui. Sem tkinter, sem Frappe, sem rede — testável com `unittest` puro.

O que ele deliberadamente não faz
---------------------------------
- **Não cria o site.** Devolve o comando `bench new-site` pronto para colar; quem executa é
  o bench, no WSL, onde o erro aparece com o traceback completo.
- **Não guarda senha em disco por conta própria.** As preferências do Cherry
  (`~/.cherry.json`) só levam caminho do bench e distro; a senha de root vai para o
  `common_site_config.json` **apenas quando o usuário manda gravar** — que é onde o Frappe
  a espera.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

__all__ = [
	"MARIADB",
	"PORTA_PADRAO",
	"POSTGRES",
	"Banco",
	"Bench",
	"CherryInvalido",
	"ResultadoConexao",
	"atualizar_json",
	"caminho_wsl",
	"comando_new_site",
	"gravar_apps_txt",
	"gravar_json",
	"ler_apps_txt",
	"ler_json",
	"testar_conexao",
]

MARIADB = "mariadb"
POSTGRES = "postgres"
TIPOS = (MARIADB, POSTGRES)
PORTA_PADRAO = {MARIADB: 3306, POSTGRES: 5432}
"""Portas padrão de cada servidor — o que o Frappe assume quando `db_port` está ausente."""

ROTULO = {MARIADB: "MariaDB", POSTGRES: "PostgreSQL"}


_NOME_SEGURO = re.compile(r"[A-Za-z0-9._:@-]+")
"""O que pode aparecer **sem aspas** num comando de shell: letras, dígitos e `. _ : @ -`.

Host, usuário, site e nomes de app saem crus em `comando_new_site`; qualquer outro caractere
(`;`, `$`, crase, espaço, barra) é recusado em vez de escapado — a recusa é mais simples e não
depende de lembrar de cada caractere especial do shell (CH-03 da revisão do Cherry).
"""


def _exigir_nome_seguro(valor: str, o_que: str) -> str:
	if not _NOME_SEGURO.fullmatch(valor):
		raise CherryInvalido(
			f"{o_que} só pode ter letras, dígitos e os caracteres . _ : @ - — recebido {valor!r}"
		)

	return valor


class CherryInvalido(ValueError):
	"""Pré-condição violada — o Cherry recusa antes de tocar em qualquer arquivo."""


# ---------------------------------------------------------------------------
# JSON no formato do Frappe
# ---------------------------------------------------------------------------


def ler_json(caminho: Path) -> dict:
	"""Lê um JSON de configuração; arquivo ausente é `{}`, não erro.

	Um `common_site_config.json` que ainda não existe é o estado normal de um bench recém
	criado — tratar como erro impediria o Cherry de ser o primeiro a escrevê-lo.
	"""
	if not caminho.exists():
		return {}

	conteudo = caminho.read_text(encoding="utf-8").strip()

	if not conteudo:
		return {}

	dados = json.loads(conteudo)

	if not isinstance(dados, dict):
		raise CherryInvalido(f"{caminho} não contém um objeto JSON")

	return dados


def gravar_json(caminho: Path, dados: dict) -> None:
	"""Grava como o Frappe grava (`indent=1`, chaves ordenadas, `\\n` final).

	`frappe.installer.update_site_config` usa exatamente este formato; reproduzi-lo evita
	que o próximo `bench set-config` reescreva o arquivo inteiro só por estilo.
	"""
	_gravar_texto(caminho, json.dumps(dados, indent=1, sort_keys=True) + "\n")


def atualizar_json(caminho: Path, alteracoes: dict) -> dict:
	"""Mescla `alteracoes` no arquivo, preservando o que não foi tocado.

	Valor `None` **remove** a chave — é como se desliga `developer_mode` ou se tira um
	`default_site` sem apagar o resto do arquivo. Devolve o conteúdo final gravado.
	"""
	dados = ler_json(caminho)

	for chave, valor in alteracoes.items():
		if valor is None:
			dados.pop(chave, None)
		else:
			dados[chave] = valor

	gravar_json(caminho, dados)

	return dados


# ---------------------------------------------------------------------------
# apps.txt
# ---------------------------------------------------------------------------


def ler_apps_txt(caminho: Path) -> list[str]:
	if not caminho.exists():
		return []

	return [linha.strip() for linha in caminho.read_text(encoding="utf-8").splitlines() if linha.strip()]


def gravar_apps_txt(caminho: Path, apps: list[str]) -> str:
	"""Grava um app por linha, **sempre** com `\\n` final, sem vazios nem repetidos.

	`frappe` precisa vir primeiro: é o que o próprio `bench` faz ao criar o arquivo, e a
	ordem de instalação segue esta lista. Devolve o texto gravado, para o teste conferir o
	byte final sem reabrir o arquivo.
	"""
	limpos: list[str] = []

	for app in apps:
		nome = app.strip()

		if not nome:
			continue

		_exigir_nome_seguro(nome, "o nome do app")

		if nome not in limpos:
			limpos.append(nome)

	if not limpos:
		raise CherryInvalido("apps.txt não pode ficar vazio — ao menos `frappe`")

	if limpos[0] != "frappe":
		if "frappe" in limpos:
			limpos.remove("frappe")

		limpos.insert(0, "frappe")

	texto = "\n".join(limpos) + "\n"
	_gravar_texto(caminho, texto)

	return texto


def _gravar_texto(caminho: Path, texto: str) -> None:
	"""Sempre `\n`, nunca `\r\n` — e **atômico**: o destino nunca fica pela metade.

	`Path.write_text` no Windows traduz `\n` para `\r\n`, e um `apps.txt` com CRLF faria o
	Frappe enxergar um app chamado `erpnext\r`. Foi o teste de costura — que relê os bytes,
	não a lista devolvida — que pegou isto antes de qualquer bench ser tocado.

	Abrir o destino com `"w"` o trunca na hora: uma falha no meio da escrita (disco cheio, queda
	do compartilhamento `\\wsl.localhost`) deixava o `common_site_config.json` com poucos bytes e
	JSON inválido (CH-02 da revisão do Cherry, medido). Por isso o texto vai para um arquivo
	temporário **na mesma pasta** e só então troca o original com `os.replace`; se qualquer passo
	falhar, o original continua como estava e o temporário é apagado.
	"""
	caminho.parent.mkdir(parents=True, exist_ok=True)

	descritor, nome_temporario = tempfile.mkstemp(
		dir=caminho.parent, prefix=f".{caminho.name}.", suffix=".tmp"
	)
	temporario = Path(nome_temporario)

	try:
		with os.fdopen(descritor, "w", encoding="utf-8", newline="\n") as arquivo:
			arquivo.write(texto)
			arquivo.flush()
			os.fsync(arquivo.fileno())

		if caminho.exists():
			shutil.copymode(caminho, temporario)

		os.replace(temporario, caminho)
	except BaseException:
		temporario.unlink(missing_ok=True)
		raise


# ---------------------------------------------------------------------------
# O bench, visto do Windows ou do próprio Linux
# ---------------------------------------------------------------------------


def caminho_wsl(distro: str, caminho_linux: str) -> Path:
	"""Traduz `/home/x/frappe-bench` para `\\\\wsl.localhost\\<distro>\\home\\x\\frappe-bench`.

	É o que permite ao Cherry, rodando no Windows, editar os arquivos do bench que vive no
	WSL sem copiar nada — o mesmo caminho que o Explorer usa.
	"""
	if not distro.strip():
		raise CherryInvalido("distro do WSL vazia")

	partes = PurePosixPath(caminho_linux)

	if not partes.is_absolute():
		raise CherryInvalido(f"caminho Linux precisa ser absoluto: {caminho_linux!r}")

	return Path(rf"\\wsl.localhost\{distro.strip()}").joinpath(*partes.parts[1:])


@dataclass(frozen=True)
class Bench:
	"""Um bench Frappe: o diretório que contém `sites/` e `apps/`.

	`distro`/`caminho_linux` só existem quando o bench está no WSL — é o que o teste de
	conexão usa para rodar o driver **de dentro** do venv do bench, que é quem de fato
	precisa alcançar o banco.
	"""

	raiz: Path
	distro: str = ""
	caminho_linux: str = ""

	@property
	def sites(self) -> Path:
		return self.raiz / "sites"

	@property
	def common_config(self) -> Path:
		return self.sites / "common_site_config.json"

	@property
	def apps_txt(self) -> Path:
		return self.sites / "apps.txt"

	@property
	def no_wsl(self) -> bool:
		return bool(self.distro and self.caminho_linux)

	def existe(self) -> bool:
		return self.sites.is_dir()

	def nomes_de_sites(self) -> list[str]:
		"""Só diretórios com `site_config.json` — `assets/` e os órfãos ficam de fora."""
		if not self.existe():
			return []

		return sorted(p.name for p in self.sites.iterdir() if (p / "site_config.json").is_file())

	def site_config(self, site: str) -> Path:
		if site not in self.nomes_de_sites():
			raise CherryInvalido(f"site desconhecido neste bench: {site!r}")

		return self.sites / site / "site_config.json"


# ---------------------------------------------------------------------------
# O banco
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Banco:
	tipo: str
	host: str = "127.0.0.1"
	porta: int = 0
	usuario_root: str = ""
	senha_root: str = field(default="", repr=False)

	def __post_init__(self):
		if self.tipo not in TIPOS:
			raise CherryInvalido(
				f"tipo de banco desconhecido: {self.tipo!r} (use {MARIADB!r} ou {POSTGRES!r})"
			)

		if not self.host.strip():
			raise CherryInvalido("host vazio")

		porta = self.porta or PORTA_PADRAO[self.tipo]

		if not 1 <= porta <= 65535:
			raise CherryInvalido(f"porta fora da faixa: {self.porta}")

		object.__setattr__(self, "porta", porta)
		object.__setattr__(self, "host", self.host.strip())

	@property
	def rotulo(self) -> str:
		return ROTULO[self.tipo]

	def chaves_common_config(self) -> dict:
		"""As chaves que o `bench new-site` lê quando não recebe `--db-*` na linha de comando.

		`root_login`/`root_password` são os nomes genéricos que os dois `setup_db.py`
		aceitam; o de Postgres ainda prefere `postgres_root_*`, mas cai nos genéricos.
		Usuário/senha vazios **não** gravam a chave — grava-se só o que se sabe.
		"""
		chaves: dict = {"db_type": self.tipo, "db_host": self.host, "db_port": self.porta}

		if self.usuario_root:
			chaves["root_login"] = self.usuario_root

		if self.senha_root:
			chaves["root_password"] = self.senha_root

		return chaves


def comando_new_site(banco: Banco, site: str, senha_admin: str = "", apps: tuple[str, ...] = ()) -> str:
	"""O `bench new-site` exato para este banco — o que se colaria no terminal do bench.

	Explícito em tudo (`--db-type`, host, porta, root), mesmo que o `common_site_config`
	já tenha os valores: o comando é a documentação do que foi feito, e não depende do
	arquivo estar igual amanhã.

	Host, usuário, site e apps passam por `_exigir_nome_seguro` (saem sem aspas); as senhas vão
	entre aspas simples. **Senha de administrador vazia omite `--admin-password`**: o `bench`
	então a pergunta no terminal (`frappe/utils/install.py: get_admin_password`), e ela não fica
	no comando nem na área de transferência.
	"""
	site = _exigir_nome_seguro(site.strip(), "o nome do site")

	partes = [
		f"bench new-site {site}",
		f"--db-type {banco.tipo}",
		f"--db-host {_exigir_nome_seguro(banco.host, 'o servidor')}",
		f"--db-port {banco.porta}",
	]

	if banco.usuario_root:
		partes.append(f"--db-root-username {_exigir_nome_seguro(banco.usuario_root, 'o usuário')}")

	if banco.senha_root:
		partes.append(f"--db-root-password {_aspas(banco.senha_root)}")

	if senha_admin:
		partes.append(f"--admin-password {_aspas(senha_admin)}")

	partes.extend(f"--install-app {_exigir_nome_seguro(app, 'o nome do app')}" for app in apps)

	return " \\\n    ".join(partes)


def _aspas(valor: str) -> str:
	"""Aspas simples do shell — a única forma que não expande `$`, `!` nem crase."""
	return "'" + valor.replace("'", "'\"'\"'") + "'"


# ---------------------------------------------------------------------------
# Teste de conexão — três níveis, e o resultado diz qual rodou
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultadoConexao:
	ok: bool
	nivel: str
	"""`"autenticacao"` (driver de verdade) ou `"tcp"` (só a porta responde)."""
	mensagem: str


VARIAVEL_DA_SENHA = "CHERRY_SENHA_ROOT"
"""Por onde a senha de root chega à sonda. **Nunca** por argumento: a linha de comando de um
processo é legível por qualquer outro processo da máquina (CH-01 da revisão do Cherry, medido)."""

_SONDA_PYTHON = r"""
import os, sys
tipo, host, porta, usuario = sys.argv[1:5]
senha = os.environ.get("CHERRY_SENHA_ROOT", "")
try:
    if tipo == "postgres":
        import psycopg2
        c = psycopg2.connect(host=host, port=int(porta), user=usuario, password=senha, dbname="postgres", connect_timeout=5)
        cur = c.cursor(); cur.execute("select version()"); print("OK " + cur.fetchone()[0])
    else:
        try:
            import MySQLdb as drv
        except ImportError:
            import pymysql as drv
        c = drv.connect(host=host, port=int(porta), user=usuario, passwd=senha, connect_timeout=5)
        cur = c.cursor(); cur.execute("select version()"); print("OK " + str(cur.fetchone()[0]))
except Exception as e:
    print("FALHA " + type(e).__name__ + ": " + str(e).strip())
"""


def testar_conexao(banco: Banco, bench: Bench | None = None, executar=subprocess.run) -> ResultadoConexao:
	"""Autentica se houver driver ao alcance; senão, ao menos prova que a porta responde.

	Ordem, e por quê:

	1. **venv do bench no WSL** (`wsl -d <distro> -- <bench>/env/bin/python`): é o
	   processo que vai falar com o banco de verdade, com o driver que o Frappe usa. Um
	   driver local no Windows passaria e o bench falharia (rede espelhada, firewall) —
	   ou o inverso.
	2. **driver local**, se `psycopg2`/`MySQLdb`/`pymysql` estiverem instalados aqui.
	3. **TCP** — só diz que algo escuta na porta. É pouco, e o resultado diz isso.

	`executar` é injetável para o teste não precisar de `wsl` nem de rede.
	"""
	argumentos = [banco.tipo, banco.host, str(banco.porta), banco.usuario_root]
	ambiente = _ambiente_da_sonda(banco.senha_root)

	if bench is not None and bench.no_wsl and shutil.which("wsl"):
		python_do_bench = str(PurePosixPath(bench.caminho_linux) / "env" / "bin" / "python")
		comando = ["wsl", "-d", bench.distro, "--", python_do_bench, "-c", _SONDA_PYTHON, *argumentos]
		resultado = _rodar_sonda(comando, executar, f"venv do bench ({bench.distro})", ambiente)

		if resultado is not None:
			return resultado

	resultado = _rodar_sonda(["python", "-c", _SONDA_PYTHON, *argumentos], executar, "driver local", ambiente)

	if resultado is not None:
		return resultado

	try:
		with socket.create_connection((banco.host, banco.porta), timeout=3):
			pass
	except OSError as erro:
		return ResultadoConexao(False, "tcp", f"nada responde em {banco.host}:{banco.porta} ({erro})")

	return ResultadoConexao(
		True,
		"tcp",
		f"a porta {banco.porta} responde em {banco.host}, mas nenhum driver estava ao alcance para "
		"autenticar — instale psycopg2/pymysql ou informe o bench no WSL para uma prova de verdade",
	)


def _ambiente_da_sonda(senha: str) -> dict[str, str]:
	"""O ambiente do processo filho: o do Cherry mais a senha, e `WSLENV` para o `wsl.exe` repassá-la.

	O `wsl.exe` só leva ao Linux as variáveis listadas em `WSLENV`; sem isso a senha ficaria no
	Windows e a sonda do venv do bench receberia senha vazia.
	"""
	ambiente = dict(os.environ)
	ambiente[VARIAVEL_DA_SENHA] = senha
	existentes = [v for v in ambiente.get("WSLENV", "").split(":") if v and v != VARIAVEL_DA_SENHA]
	ambiente["WSLENV"] = ":".join([*existentes, VARIAVEL_DA_SENHA])

	return ambiente


def _rodar_sonda(
	comando: list[str], executar, origem: str, ambiente: dict[str, str]
) -> ResultadoConexao | None:
	"""`None` quando a sonda nem pôde rodar (sem driver, sem wsl) — aí se tenta o próximo nível."""
	try:
		saida = executar(comando, capture_output=True, text=True, timeout=30, env=ambiente)
	except (OSError, subprocess.TimeoutExpired):
		return None

	texto = (saida.stdout or "").strip().splitlines()
	ultima = texto[-1] if texto else ""

	if ultima.startswith("OK "):
		return ResultadoConexao(True, "autenticacao", f"{origem}: {ultima[3:]}")

	if ultima.startswith("FALHA "):
		erro = ultima[6:]

		if "No module named" in erro or "ModuleNotFoundError" in erro:
			return None

		return ResultadoConexao(False, "autenticacao", f"{origem}: {erro}")

	return None
