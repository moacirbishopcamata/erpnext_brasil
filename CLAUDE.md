# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Localização fiscal brasileira para o ERPNext, distribuída como **app Frappe separado** (`erpnext_brasil`) — o ERPNext/Frappe nunca é forkado nem editado. Prosa, docstrings, commits e artefatos OpenSpec são em **pt-BR**, com acentuação correta.

## Comandos

A suíte pura roda em qualquer máquina, sem bench, site ou banco (é o que o CI executa):

```sh
pip install lxml                                                          # única dependência da suíte pura; sem ela ~80 testes dão ModuleNotFoundError
python -m unittest discover -s erpnext_brasil/tests -t .                 # tudo
python -m unittest erpnext_brasil.tests.test_cfop                         # um módulo
python -m unittest erpnext_brasil.tests.test_cfop.NomeDaClasse.test_x     # um teste

pip install ruff
ruff check erpnext_brasil/
ruff format --check erpnext_brasil/       # `ruff format` para aplicar
```

Estilo (em `pyproject.toml`): linha de 110, **tabulação**, aspas duplas — o mesmo do erpnext. Cabeçalho de arquivo: `# Copyright (c) 2026, ERPNext Brasil contributors` / `# License: MIT. See license.txt`.

Testes de bench (`erpnext_brasil/tests_bench/`) exigem site real e **só rodam em WSL2/Linux** (o `bench` não funciona nativo no Windows):

```sh
bash scripts/subir.sh                     # MariaDB + Redis + servidor, sem sudo/Docker; BENCH=~/frappe-bench-16 é o padrão
SO_SERVICOS=1 bash scripts/subir.sh       # só serviços — use antes de `bench migrate`/`bench execute`
bench --site <site> run-tests --app erpnext_brasil [--module <dotted.path>]
python scripts/cobertura_de_bench.py      # quais módulos ligados no hooks.py ainda não têm teste de bench
```

Cada arquivo de `tests_bench/` declara `MODULOS_COBERTOS`; o script de cobertura lê essa declaração (não infere por nome nem por import). Ao criar um teste de bench, declare-a. Ambiente e armadilhas: `docs/ambiente-dev-bench.md`, `docs/como-rodar.md`, `docs/banco-do-bench-v16.md`.

## Arquitetura

Duas camadas, dependência em **uma direção só** (`integracao/` → `fiscal/`):

- `fiscal/`, `contabil/`, `folha/` — regra pura (funções + `dataclass`, `Decimal`), **nunca importam `frappe`**. Cobrem NF-e/NFC-e, CT-e, MDF-e, impostos (ICMS/IPI/PIS/COFINS/IBS-CBS), SPED/EFD/ECD/ECF/Reinf, eSocial, folha.
- `integracao/` — camada fina que conhece `frappe`, monta o contexto e chama a regra pura; não contém regra fiscal. Há um `repositorio_frappe.py` implementando `Protocol`s da camada pura (inversão de dependência: a regra depende de `RepositorioClassificacao`/`TransporteFiscal`, não do Frappe).
- `setup/` — Custom Fields (`campos.py`, `campos_documento.py`) e instalação (`after_install`/`after_migrate`). `registros_fiscais/doctype/` — DocTypes do app. `hooks.py` liga tudo (doc_events, `doctype_js`, `regional_overrides` para o `hrms`).

`tests/test_arquitetura.py` faz a regra valer com `ast`: falha se `fiscal/` importar `frappe` ou `integracao/`, se um teste importar `frappe`, ou se um módulo de integração crescer demais (regra migrando para o lugar errado). Ao criar código, respeite isso em vez de contornar.

Fluxo típico: documento do ERPNext (ex.: `Sales Invoice`) → hook/ação em `integracao/` → montagem do XML e regra em `fiscal/documento/` → assinatura A1 → transmissão SOAP à SEFAZ (autorizador por UF em `autorizadores_*`) → estado/eventos gravados de volta. Falha alto onde o silêncio daria dado errado; degrada onde a ausência é estado normal (ver `docs/arquitetura.md`).

## Convenções do projeto

- **Fonte normativa citada**: docstrings registram de onde veio cada regra fiscal e o nível de confiança. Não afirme regra fiscal sem fonte; o que está incompleto vai em `docs/gaps.md`. Cada incremento tem doc próprio indexado em `docs/README.md`.
- **Bench alvo é `version-16`** (Frappe 16 / ERPNext 16); o piso declarado é `>=15`.
- **Custom Field tem que ser declarado em `setup/`** — já houve 31 campos que a integração lia e a instalação nunca criava. Use a skill `frappe-bench` ao mexer em Custom Field, DocType, hooks, patches.
- **Mudanças de planejamento** vão por OpenSpec (`openspec/changes/*`, specs em `openspec/specs/fiscal`; comandos em `.claude/commands/opsx` e skills `openspec-*`). Artefatos em pt-BR; cabeçalhos estruturais e `SHALL/MUST` em inglês.
- Bugs encontrados em frappe/erpnext/hrms viram patches em `contrib/` para devolver ao upstream; faça `git pull` desses repositórios no bench antes de corrigir.
- O CI (`.github/workflows/ci.yml`) roda só a suíte pura + `ruff`; **não há job de bench** (lacuna declarada em `docs/gaps.md`, seção 2). Um teste verde no CI não prova nada sobre Custom Field, hook ou DocType — isso só os testes de `tests_bench/` cobrem.
- O diretório `.claude/worktrees/` é de worktrees de sessões paralelas — não edite fora do seu.
