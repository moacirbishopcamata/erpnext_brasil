# Revisão do Cherry — linha de base

Revisão de **2026-10-11**, commit `861fa11`, Cherry `0.1.0`. Somente leitura: nenhum código do Cherry foi alterado. Síntese em [`../revisao-do-cherry.md`](../revisao-do-cherry.md).

## Números

| Medida | Valor | Como foi obtido |
|---|---|---|
| Linhas em `scripts/cherry/*.py` | 1.664 | `wc -l scripts/cherry/*.py` |
| `config.py` / `app.py` | 443 / 662 linhas | idem |
| Testes | 55 (`test_config` 41 + `test_app` 14) | `python -m unittest scripts.cherry.test_config scripts.cherry.test_app -v` |
| Versão | `0.1.0` | `scripts/cherry/__init__.py` |

## Execuções

| Verificação | Resultado |
|---|---|
| Testes do Cherry | `Ran 55 tests ... OK`, nenhum pulado (esta máquina tem display, então `test_app.py` rodou) |
| Cobertura, como no CI (`coverage run` com `--include scripts/cherry/*.py`) | `config.py` **100%** (176 instruções); `app.py` **83%** (397 instruções, 67 sem cobertura); total 88% |
| `ruff check scripts` e `ruff format --check scripts` | limpo; 11 arquivos já formatados |
| Tela da máquina | 1366×768, fator de escala do Tk 1,33 |

A cobertura medida **bate exatamente** com o que `docs/cherry.md` declarou para a primeira versão (55 testes, 100%, 83%, 88%): o doc está fiel à `0.1.0`, e a `0.1.0` não mudou desde então.

## Linhas de `app.py` sem cobertura

`155-159, 162-166, 170-171, 175-177, 278-281, 296, 322-337, 341, 368-370, 382-384, 436, 448-452, 458-460, 515, 533-534, 547-548, 577, 581-583, 602-603, 611, 614, 618, 630-631, 637, 643-644, 658, 662`. Destaques: **`_testar_conexao` inteiro (322-337)**, o ramo de erro de gravar o banco (368-370) e o de copiar o `bench new-site` (382-384).

## O que esta revisão não fez

- Não rodou o Cherry contra um bench real do usuário: todas as gravações usaram diretório temporário.
- Não mediu a lista de processos **dentro do WSL** (só no Windows).
- Não leu os 41 testes de `test_config.py` um a um.
