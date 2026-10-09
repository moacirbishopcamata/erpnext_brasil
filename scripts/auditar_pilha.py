# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Audita a pilha que sustenta o ERPNext: versões suportadas e vulnerabilidades conhecidas.

Repete, de forma reprodutível, as consultas que foram feitas à mão em 2026-10-09 (`docs/auditoria-da-pilha.md`):

- **Versões**: o que está instalado no bench (Frappe, ERPNext, HRMS, `bench`, Python, Node, MariaDB, Redis) contra
  a última versão da série e o fim de suporte, vindos de `endoflife.date`, das releases do GitHub e do PyPI.
- **Avisos de segurança** dos quatro projetos Frappe (API de advisories do GitHub).
- **Bibliotecas Python** do ambiente do bench, no OSV.

Só biblioteca padrão. Uso::

    python3 scripts/auditar_pilha.py                      # lê ~/frappe-bench-16
    python3 scripts/auditar_pilha.py --bench ~/outro --json

Código de saída: **0** se nada falha; **1** se há componente fora de suporte, vulnerabilidade alta/crítica que afeta
a instalação, ou componente que não pôde ser verificado. Defasagem em relação à última versão é relatada, mas **não**
falha — atrás da última patch não é o mesmo que fora de suporte.

As quatro armadilhas que este script existe para não repetir
-------------------------------------------------------------
1. **A faixa de um advisory do GitHub às vezes é só a versão corrigida** (`'16.7.0'`, sem operador) e, quando ainda
   não há correção, `'tbd'`. Ler "sem operador" como "afeta tudo" marcou como vulneráveis versões já corrigidas.
2. **O OSV lista o mesmo CVE duas vezes** (um registro GHSA e um PYSEC); contar registros infla o número. Conta-se por CVE.
3. **Prefixo `v`** em algumas faixas (`'< v16.5.0'`).
4. **Fonte que não responde é "não verificado", nunca "em dia"**: silêncio não é boa notícia.
"""

import argparse
import datetime
import functools
import glob
import json
import os
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field

__all__ = [
	"Achado",
	"auditar",
	"classificar_advisories",
	"comparar_versoes",
	"faixa_afeta",
	"principal",
]

GRAVES = ("critical", "high")
APPS = ("frappe", "erpnext", "hrms")
PROJETOS_FRAPPE = ("frappe", "erpnext", "hrms", "bench")

BIBLIOTECAS_DE_INTERESSE = None
"""`None` = todas as instaladas no ambiente do bench; ou uma lista de nomes para restringir."""


def comparar_versoes(a: str, b: str) -> int:
	"""-1, 0 ou 1. Tolera prefixo `v` e sufixos não numéricos (`16.0.0-beta` conta como `16.0.0`)."""

	def tupla(v: str) -> tuple[int, ...]:
		partes = v.strip().lstrip("vV").split(".")
		numeros = []

		for parte in partes[:4]:
			digitos = re.match(r"\d+", parte)
			numeros.append(int(digitos.group()) if digitos else 0)

		return tuple(numeros + [0] * (4 - len(numeros)))

	ta, tb = tupla(a), tupla(b)

	return (ta > tb) - (ta < tb)


def faixa_afeta(faixa: str | None, instalada: str) -> str:
	"""`"afeta"`, `"nao_afeta"` ou `"indeterminado"` para uma faixa de advisory e uma versão instalada.

	- vazia ou `tbd` → indeterminado (não há correção declarada);
	- **sem operador** → é a versão corrigida: afeta quem está abaixo dela;
	- com operadores (`>= 16.0.0, < 16.18.0`) → todas as condições precisam valer.
	"""
	texto = (faixa or "").strip()

	if not texto or texto.lower() == "tbd":
		return "indeterminado"

	condicoes = [c.strip() for c in texto.split(",") if c.strip()]

	if not any(c[0] in "<>=" for c in condicoes):
		return "afeta" if comparar_versoes(instalada, condicoes[0]) < 0 else "nao_afeta"

	for condicao in condicoes:
		operador = re.match(r"(>=|<=|>|<|=)\s*(.+)", condicao)

		if not operador:
			return "indeterminado"

		op, alvo = operador.group(1), operador.group(2)
		cmp = comparar_versoes(instalada, alvo)

		if not {">=": cmp >= 0, "<=": cmp <= 0, ">": cmp > 0, "<": cmp < 0, "=": cmp == 0}[op]:
			return "nao_afeta"

	return "afeta"


@dataclass
class Achado:
	projeto: str
	identificador: str
	gravidade: str
	resumo: str = ""
	corrigido_em: str = ""


@dataclass
class Relatorio:
	componentes: list[dict] = field(default_factory=list)
	vulnerabilidades: list[Achado] = field(default_factory=list)
	indeterminados: list[Achado] = field(default_factory=list)
	nao_verificados: list[str] = field(default_factory=list)

	@property
	def falhas(self) -> list[str]:
		motivos = [f"{c['nome']}: {c['situacao']}" for c in self.componentes if c["falha"]]
		motivos += [
			f"{v.projeto}: {v.identificador} ({v.gravidade}) afeta a versão instalada"
			for v in self.vulnerabilidades
			if v.gravidade.lower() in GRAVES
		]
		motivos += [f"não verificado: {n}" for n in self.nao_verificados]

		return motivos

	@property
	def codigo_de_saida(self) -> int:
		return 1 if self.falhas else 0


def classificar_advisories(
	advisories: list[dict], instalada: str, projeto: str
) -> tuple[list[Achado], list[Achado]]:
	"""`(afetam, indeterminados)`. Um advisory afeta se **alguma** das suas entradas diz que afeta; é indeterminado se
	nenhuma afeta e alguma não declara a correção."""
	afetam, indeterminados = [], []

	for aviso in advisories:
		veredictos = [
			(faixa_afeta(v.get("vulnerable_version_range"), instalada), v.get("patched_versions") or "")
			for v in aviso.get("vulnerabilities") or []
		]

		achado = Achado(
			projeto=projeto,
			identificador=aviso.get("cve_id") or aviso.get("ghsa_id") or "?",
			gravidade=aviso.get("severity") or "?",
			resumo=(aviso.get("summary") or "")[:90],
		)

		if any(v == "afeta" for v, _ in veredictos):
			achado.corrigido_em = next(c for v, c in veredictos if v == "afeta")
			afetam.append(achado)
		elif any(v == "indeterminado" for v, _ in veredictos):
			indeterminados.append(achado)

	return afetam, indeterminados


def _por_cve(vulnerabilidades: list[dict]) -> dict[str, dict]:
	"""Um registro por CVE: o OSV traz o mesmo CVE em GHSA e PYSEC."""
	unicas: dict[str, dict] = {}

	for v in vulnerabilidades:
		chave = next((a for a in v.get("aliases", []) if a.startswith("CVE-")), v["id"])
		unicas.setdefault(chave, v)

	return unicas


def _corrigido_em(vulnerabilidade: dict, pacote: str, instalada: str) -> str:
	corrigidos = [
		evento["fixed"]
		for afetado in vulnerabilidade.get("affected", [])
		if afetado.get("package", {}).get("name", "").lower() == pacote.lower()
		for faixa in afetado.get("ranges", [])
		for evento in faixa.get("events", [])
		if "fixed" in evento and comparar_versoes(evento["fixed"], instalada) > 0
	]

	return min(corrigidos, key=functools.cmp_to_key(comparar_versoes), default="")


def _componente(
	nome: str, instalada: str | None, ultima: str | None, fim_de_suporte: str | None, hoje: datetime.date
) -> dict:
	"""Uma linha do relatório. `falha` só quando a série está **fora de suporte** ou não deu para verificar."""
	if not instalada:
		return {"nome": nome, "instalada": None, "ultima": ultima, "fim_de_suporte": fim_de_suporte,
			"situacao": "não encontrado no ambiente", "falha": True}  # fmt: skip

	if (
		fim_de_suporte
		and fim_de_suporte not in ("False", "false")
		and datetime.date.fromisoformat(fim_de_suporte) < hoje
	):
		return {"nome": nome, "instalada": instalada, "ultima": ultima, "fim_de_suporte": fim_de_suporte,
			"situacao": f"série fora de suporte desde {fim_de_suporte}", "falha": True}  # fmt: skip

	if ultima and comparar_versoes(instalada, ultima) < 0:
		situacao = f"atrás da última ({ultima})"
	else:
		situacao = "em dia"

	return {"nome": nome, "instalada": instalada, "ultima": ultima, "fim_de_suporte": fim_de_suporte,
		"situacao": situacao, "falha": False}  # fmt: skip


def auditar(instalados: dict, fontes, hoje: datetime.date | None = None) -> Relatorio:
	"""O relatório, a partir do que está instalado e de `fontes` (injetável, para teste sem rede).

	`instalados`::

	    {"apps": {"frappe": "16.36.1", ...}, "bench": "5.31.0",
	     "runtimes": {"python": "3.14.6", "nodejs": "24.21.0", "mariadb": "10.11.9", "redis": "7.2.16"},
	     "bibliotecas": {"pypdf": "6.15.0", ...}}

	`fontes` expõe: `ultima_tag(projeto, versao)`, `ultima_pypi(pacote)`, `ciclo(produto, versao)` →
	`{"latest", "eol"}`, `advisories(projeto)` e `osv(bibliotecas)` → lista paralela de vulnerabilidades. Qualquer uma
	pode levantar `OSError`/`ValueError`: vira "não verificado".
	"""
	hoje = hoje or datetime.date.today()
	relatorio = Relatorio()

	def tentar(descricao: str, chamada, padrao=None):
		try:
			return chamada()
		except (OSError, ValueError, KeyError) as erro:
			relatorio.nao_verificados.append(f"{descricao} ({type(erro).__name__})")

			return padrao

	for app, versao in instalados.get("apps", {}).items():
		if not versao:
			relatorio.componentes.append(_componente(app, None, None, None, hoje))
			continue

		ultima = tentar(
			f"última versão de {app}", lambda app=app, versao=versao: fontes.ultima_tag(app, versao)
		)
		relatorio.componentes.append(_componente(app, versao, ultima, None, hoje))

	if "bench" in instalados:
		versao_do_bench = instalados["bench"]
		ultima = (
			tentar("última versão do bench", lambda: fontes.ultima_pypi("frappe-bench"))
			if versao_do_bench
			else None
		)
		relatorio.componentes.append(_componente("bench", versao_do_bench, ultima, None, hoje))

	for produto, versao in instalados.get("runtimes", {}).items():
		if not versao:
			relatorio.componentes.append(_componente(produto, None, None, None, hoje))
			continue

		ciclo = tentar(
			f"ciclo de {produto}", lambda produto=produto, versao=versao: fontes.ciclo(produto, versao), {}
		)
		relatorio.componentes.append(
			_componente(
				produto,
				versao,
				ciclo.get("latest"),
				str(ciclo.get("eol")) if ciclo.get("eol") else None,
				hoje,
			)
		)

	for projeto in PROJETOS_FRAPPE:
		versao = instalados.get("apps", {}).get(projeto) or (
			instalados.get("bench") if projeto == "bench" else None
		)

		if not versao:
			continue

		avisos = tentar(f"advisories de {projeto}", lambda projeto=projeto: fontes.advisories(projeto), [])
		afetam, indeterminados = classificar_advisories(avisos, versao, projeto)
		relatorio.vulnerabilidades += afetam
		relatorio.indeterminados += indeterminados

	bibliotecas = instalados.get("bibliotecas", {})

	if bibliotecas:
		nomes = list(bibliotecas)
		resultado = tentar("vulnerabilidades das bibliotecas (OSV)", lambda: fontes.osv(bibliotecas), [])

		for nome, vulnerabilidades in zip(nomes, resultado, strict=False):
			for cve, v in _por_cve(vulnerabilidades).items():
				relatorio.vulnerabilidades.append(
					Achado(
						projeto=f"{nome} {bibliotecas[nome]}",
						identificador=cve,
						gravidade=(v.get("database_specific") or {}).get("severity", "?").lower(),
						resumo=(v.get("summary") or "")[:90],
						corrigido_em=_corrigido_em(v, nome, bibliotecas[nome]),
					)
				)

	return relatorio


# ------------------------------------------------------------------------------------------ fontes reais


def _buscar(url: str, dados: dict | None = None):
	requisicao = urllib.request.Request(
		url,
		data=json.dumps(dados).encode() if dados is not None else None,
		headers={
			"User-Agent": "erpnext-brasil-auditoria",
			"Accept": "application/json",
			"Content-Type": "application/json",
		},
	)

	with urllib.request.urlopen(requisicao, timeout=40) as resposta:
		return json.load(resposta)


class FontesReais:
	"""As consultas de verdade. Cada método levanta `OSError`/`ValueError` se a fonte falhar."""

	def ultima_tag(self, projeto: str, versao: str) -> str:
		serie = versao.split(".")[0]
		lancamentos = _buscar(f"https://api.github.com/repos/frappe/{projeto}/releases?per_page=60")
		candidatas = [
			x["tag_name"].lstrip("v")
			for x in lancamentos
			if x["tag_name"].lstrip("v").startswith(f"{serie}.") and not x["prerelease"]
		]

		if not candidatas:
			raise ValueError(f"nenhuma release da série {serie} em {projeto}")

		return max(candidatas, key=lambda v: [int(x) for x in v.split(".")[:3]])

	def ultima_pypi(self, pacote: str) -> str:
		return _buscar(f"https://pypi.org/pypi/{pacote}/json")["info"]["version"]

	def ciclo(self, produto: str, versao: str) -> dict:
		partes = versao.split(".")
		ciclo = ".".join(partes[:2]) if produto in ("python", "mariadb", "redis") else partes[0]

		return _buscar(f"https://endoflife.date/api/{produto}/{ciclo}.json")

	def advisories(self, projeto: str) -> list[dict]:
		return _buscar(
			f"https://api.github.com/repos/frappe/{projeto}/security-advisories?state=published&per_page=100"
		)

	def osv(self, bibliotecas: dict) -> list[list[dict]]:
		consulta = {
			"queries": [
				{"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v in bibliotecas.items()
			]
		}
		resultado = _buscar("https://api.osv.dev/v1/querybatch", consulta)["results"]

		return [
			[_buscar(f"https://api.osv.dev/v1/vulns/{x['id']}") for x in r.get("vulns", [])]
			for r in resultado
		]


# ------------------------------------------------------------------------------------------ leitura do bench


def _executar(comando: list[str]) -> str:
	try:
		return subprocess.run(comando, capture_output=True, text=True, timeout=30, check=False).stdout.strip()
	except (OSError, subprocess.SubprocessError):
		return ""


def _versao(texto: str) -> str | None:
	achado = re.search(r"(\d+\.\d+(?:\.\d+)?)", texto or "")

	return achado.group(1) if achado else None


def ler_instalados(bench: str) -> dict:
	"""O que está instalado no bench. Componente que não se consegue ler vira ausente (e o relatório o acusa)."""
	bench = os.path.expanduser(bench)
	apps = {}

	for app in APPS:
		try:
			conteudo = open(os.path.join(bench, "apps", app, app, "__init__.py"), encoding="utf-8").read()
			apps[app] = re.search(r"__version__\s*=\s*[\"']([^\"']+)", conteudo).group(1)
		except (OSError, AttributeError):
			apps[app] = None  # ausente aparece no relatório como falha, não some

	python = os.path.join(bench, "env", "bin", "python")
	home = os.path.expanduser("~")
	redis = next(
		(
			c
			for c in (os.path.join(home, "redis-7.2.16", "src", "redis-server"), "redis-server")
			if _executar([c, "--version"])
		),
		"redis-server",
	)
	mariadb = next(
		iter(sorted(glob.glob(os.path.join(home, "mariadb-*", "bin", "mariadbd")), reverse=True)), "mariadbd"
	)
	listagem = _executar([python, "-m", "pip", "list", "--format=json"])

	return {
		"apps": apps,
		"bench": next(
			(
				v
				for c in ("bench", os.path.join(home, ".local", "bin", "bench"))
				if (v := _versao(_executar([c, "--version"])))
			),
			None,
		),
		"runtimes": {
			"python": _versao(_executar([python, "--version"])),
			"nodejs": _versao(_executar(["node", "--version"])),
			"mariadb": _versao(_executar([mariadb, "--version"])),
			"redis": _versao(_executar([redis, "--version"])),
		},
		"bibliotecas": {p["name"]: p["version"] for p in json.loads(listagem)} if listagem else {},
	}


def imprimir(relatorio: Relatorio) -> None:
	print("== Componentes")

	for c in relatorio.componentes:
		marca = "FALHA" if c["falha"] else ("  ok " if c["situacao"] == "em dia" else " aviso")
		print(
			f"  [{marca}] {c['nome']:10} instalada={c['instalada']} última={c['ultima']} fim={c['fim_de_suporte']} — {c['situacao']}"
		)

	print(f"\n== Vulnerabilidades que afetam a versão instalada: {len(relatorio.vulnerabilidades)}")

	for v in sorted(
		relatorio.vulnerabilidades,
		key=lambda x: (x.gravidade != "critical", x.gravidade != "high", x.projeto),
	):
		print(
			f"  [{v.gravidade:8}] {v.projeto:22} {v.identificador:22} corrigido em {v.corrigido_em or '-':9} {v.resumo}"
		)

	if relatorio.indeterminados:
		print(f"\n== Avisos SEM versão corrigida declarada (indeterminados): {len(relatorio.indeterminados)}")

		for v in relatorio.indeterminados:
			print(f"  [{v.gravidade:8}] {v.projeto:10} {v.identificador:22} {v.resumo}")

	if relatorio.nao_verificados:
		print("\n== NÃO VERIFICADOS (fonte indisponível)")

		for n in relatorio.nao_verificados:
			print(f"  - {n}")

	print(f"\n{'FALHAS' if relatorio.falhas else 'Sem falhas'}: {len(relatorio.falhas)}")

	for motivo in relatorio.falhas:
		print(f"  - {motivo}")


def principal(argumentos: list[str] | None = None, fontes=None, instalados: dict | None = None) -> int:
	analisador = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
	analisador.add_argument(
		"--bench", default="~/frappe-bench-16", help="pasta do bench (padrão: ~/frappe-bench-16)"
	)
	analisador.add_argument("--json", action="store_true", help="saída em JSON")
	opcoes = analisador.parse_args(argumentos)

	relatorio = auditar(instalados or ler_instalados(opcoes.bench), fontes or FontesReais())

	if opcoes.json:
		print(json.dumps(
			{"componentes": relatorio.componentes, "vulnerabilidades": [vars(v) for v in relatorio.vulnerabilidades],
			 "indeterminados": [vars(v) for v in relatorio.indeterminados], "nao_verificados": relatorio.nao_verificados,
			 "falhas": relatorio.falhas}, ensure_ascii=False, indent=1))  # fmt: skip
	else:
		imprimir(relatorio)

	return relatorio.codigo_de_saida


if __name__ == "__main__":
	sys.exit(principal())
