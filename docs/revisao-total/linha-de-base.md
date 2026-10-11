# Revisão total — linha de base

Revisão de **2026-10-11**, versão `0.227.0`, commit `16159bb` (merge do PR #13). Somente leitura: nenhum código foi alterado.
Síntese em [`../revisao-total.md`](../revisao-total.md).

## Números

| Medida | Valor | Como foi obtido |
|---|---|---|
| Commits | 308 | `git rev-list --count HEAD` |
| Módulos `.py` em `fiscal/` | 83 (19.206 linhas) | `find erpnext_brasil/fiscal -name '*.py'` e `wc -l` |
| Módulos `.py` em `contabil/` | 40 (7.995 linhas) | idem |
| Módulos `.py` em `folha/` | 20 (3.552 linhas) | idem |
| Módulos `.py` em `integracao/` | 76 (11.785 linhas) | idem |
| Módulos `.py` em `setup/` | 9 (2.543 linhas) | idem |
| Módulos `.py` em `registros_fiscais/` | 23 (486 linhas), 7 DocTypes | idem |
| Módulos de teste da suíte pura | 182 (`test_*.py`), 3.490 testes | `ls erpnext_brasil/tests/test_*.py`; `unittest discover` |
| Módulos de teste de bench | 27 (`test_*.py`), 222 testes | `ls erpnext_brasil/tests_bench/test_*.py`; contagem por `ast` |
| Documentos em `docs/` | 142 (fora o `README.md`) | `ls docs/*.md` |
| Métodos `@frappe.whitelist()` | 36 | `grep -rn "frappe.whitelist" erpnext_brasil` |
| Usos de `ignore_permissions` | 28 | `grep -rn ignore_permissions` |
| Caminhos dotted no `hooks.py` | 20, todos resolvem | verificação por `ast` (ver [`integracao.md`](integracao.md)) |

## Execuções desta revisão

| Verificação | Resultado |
|---|---|
| `python -m unittest discover -s erpnext_brasil/tests -t .` | `Ran 3490 tests ... OK (skipped=3)` |
| `ruff check erpnext_brasil/` e `scripts/` | `All checks passed!` |
| `ruff format --check erpnext_brasil/` e `scripts/` | 471 e 11 arquivos já formatados |
| `python scripts/cobertura_de_bench.py` | `Cobertura de bench: 13/13` |
| `python3 scripts/auditar_pilha.py --bench ~/frappe-bench-16` (WSL2) | ver [`pilha-ci.md`](pilha-ci.md) |
| Testes de bench | **não executados** nesta revisão |

## O que esta revisão não fez

- Não rodou o bench. Tudo que depende de Custom Field, hook ou DocType num site real aparece como "inferido da leitura".
- Não autorizou documento em SEFAZ de homologação (exige certificado A1).
- Não leu linha a linha as ~91 mil linhas. A cobertura por frente está declarada em cada anexo.
