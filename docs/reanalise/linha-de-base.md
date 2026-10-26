# Reanálise — linha de base

Reanálise de **2026-10-26**, versão `0.228.0`. Executa o change `reanalise-do-sistema`.

| | Commit | Data | Versão |
|---|---|---|---|
| Partida (revisão total) | `c1ef23d` | 2026-10-11 | `0.227.0` |
| Chegada (`origin/main`) | `4e2e93f` | 2026-10-12 | `0.228.0` |

Entre as duas: **37 commits** (`git rev-list --count c1ef23d..origin/main`); 346 no total do repositório. A branch `hora-legal-br-como-reserva` (commit `397cb46`, medição do relógio com hora legal como reserva) não está na `main` e fica fora, como declarado na proposta.

## O que mudou desde a revisão total

`git diff --stat c1ef23d 4e2e93f -- erpnext_brasil scripts docker Dockerfile docker-compose.yml .github`: **62 arquivos, +9.944 / −74**. Agrupado:

| Superfície | Arquivos | Revisada antes? |
|---|---|---|
| `persistencia/` (JSON, SQLite, memória, fábrica) | 7 | não |
| `soda/` (identidade, portas, registro, conciliação, diário, plano, leitura) | 10 | não |
| `bancos/` (perfis de banco) | 5 | não |
| `sistema/rede.py` | 2 | não |
| `docker/` (Compose, `construir.py`, `preparar.py`, `.env.example`) | 10 | não |
| `scripts/instalar_app_brasil.sh` | 1 | não |
| `scripts/cherry/` (`0.2.0` → `0.4.0`: perfis, instâncias) | 10 | só até `0.2.0` |
| `.github/workflows/ci.yml` (job do Cherry, Docker) | 1 | parcialmente (revisão total viu o CI anterior) |
| Correção `b08beb7` (`folha/periodo.py`, 5 módulos de `integracao/`) | 6 | é a correção de RT-01/02/03 |
| Testes novos (contrato de persistência, Soda, bancos, Docker, whitelist, período da folha) | 8 | — |

`Dockerfile` e `docker-compose.yml` da raiz **não mudaram** desde `c1ef23d`; o que mudou foi `docker/`.

## Números

Gerados por `python -I contar.py .` (conta `*.py` fora de `__pycache__` por subpasta de `erpnext_brasil/`; script no diretório temporário da sessão, não versionado):

| Pacote | Módulos | Linhas |
|---|---:|---:|
| `fiscal/` | 83 | 19.206 |
| `integracao/` | 76 | 11.829 |
| `contabil/` | 40 | 7.995 |
| `folha/` | 21 | 3.610 |
| `setup/` | 9 | 2.543 |
| `soda/` | 10 | 1.738 |
| `persistencia/` | 7 | 910 |
| `bancos/` | 5 | 649 |
| `registros_fiscais/` | 23 | 486 |
| `patches/` | 2 | 189 |
| `sistema/` | 2 | 33 |
| `tests/` | 192 | 39.108 |
| `tests_bench/` | 29 | 5.594 |
| **Total** | **502** | **93.890** |

Módulos de teste: 190 em `tests/` (`test_*.py`), 27 em `tests_bench/`. Documentos em `docs/*.md`: 156.

## Execução

Ambiente: Windows 11, Python 3.13.14, `ruff` 0.16.6, Docker 29.8.2 (o CI usa Python 3.12 em Ubuntu).

```text
$ python -m unittest discover -s erpnext_brasil/tests -t .
Ran 3956 tests in 63.918s
FAILED (failures=7, skipped=7)

$ python -X utf8 -m unittest discover -s erpnext_brasil/tests -t .
OK (skipped=7)
```

As 7 falhas são um único teste, `test_docker.TestResolucaoReal.test_os_rotulos_de_instancia_chegam_aos_servicos_de_aplicacao`, uma vez por serviço: `'NF-e em homologação' != 'NF-e em homologa��o'`. Causa: `subprocess.run(..., text=True)` sem `encoding` em `tests/test_docker.py:430`, que no Windows decodifica a saída UTF-8 do `docker compose` como `cp1252` (`locale.getpreferredencoding(False)`). Com `-X utf8` passa. Registrado como **RA-01** em [arquitetura-ci-docs](arquitetura-ci-docs.md).

Os 7 pulados são todos de ambiente e declaram o motivo: três testes de concorrência que não se aplicam ao adaptador em memória (as variantes JSON/SQLite rodam), permissão `0600` (só Linux/WSL), `jinja2` ausente, tabela oficial de compatibilidade e JSON do IBGE não fornecidos.

Comparado à revisão total: **3.490 → 3.956 testes (+466)**.

```text
$ ruff check erpnext_brasil/ scripts/
All checks passed!
$ ruff format --check erpnext_brasil/ scripts/
519 files already formatted
```

Cherry, com os mesmos comandos do `ci.yml`:

```text
$ python -m coverage run ... -m unittest scripts.cherry.test_config scripts.cherry.test_perfis scripts.cherry.test_instancias scripts.cherry.test_app
Ran 157 tests in 13.799s
OK
$ coverage report --include=config.py,perfis.py,instancias.py --fail-under=95   →  TOTAL 319 0 100%
$ coverage report --include=app.py --fail-under=89                            →  TOTAL 710 63 91%
```

Cobertura de bench (`python scripts/cobertura_de_bench.py`): **13/13**, igual à revisão total; nenhum módulo novo foi ligado no `hooks.py` desde `c1ef23d`. Vale a ressalva da revisão total (`docs/revisao-total/testes.md:34`): 13/13 mede os módulos ligados no `hooks.py`, não a integração inteira.
