# Revisão total — pilha, CVE e CI

Versão `0.227.0`, 2026-10-11. Cobre as tarefas 4.1 e 4.2 do change `revisao-total-erpnext-brasil`. A revisão só relata: nenhuma versão foi alterada e nenhum backup foi necessário.

## Auditoria da pilha (4.1)

Executada em WSL2 contra `~/frappe-bench-16`:

```sh
python3 scripts/auditar_pilha.py --bench ~/frappe-bench-16
```

O script consulta endoflife.date, as releases e os *security advisories* do GitHub, o PyPI e o OSV no momento da execução (2026-10-11); essas são as fontes web desta tarefa. Saída:

| Componente | Instalada | Última | Fim do suporte | Situação |
|---|---|---|---|---|
| frappe | 16.51.0 | 16.51.1 | — | aviso: atrás da última |
| erpnext | 16.50.0 | 16.50.0 | — | em dia |
| hrms | 16.50.0 | 16.50.0 | — | em dia |
| bench | 5.31.0 | 5.31.0 | — | em dia |
| python | 3.14.8 | 3.14.8 | 2030-10-31 | em dia |
| nodejs | 24.21.0 | 24.21.0 | 2028-04-30 | em dia |
| mariadb | 10.11.9 | 10.11.19 | 2028-02-16 | aviso: atrás da última (**falso, ver RT-07**) |
| redis | 7.2.16 | 7.2.16 | 2029-12-01 | em dia |

Vulnerabilidade que afeta a versão instalada: **1**, `pdfkit 1.0.0`, CVE-2025-26240 (alta), sem versão corrigida. O script saiu com código 1 por causa dela.

- O `pdfkit` já está no **risco aceito** de `docs/auditoria-da-pilha.md:49-51` (dependência do Frappe, o caminho vulnerável é `from_string`, que o app não chama). Nada novo; reconferi: `grep -rn pdfkit erpnext_brasil/` não acha nenhuma referência no app, então o app não chama `pdfkit` nem `from_string` (o uso é do Frappe).
- `frappe 16.51.1` existe e a instalada é a 16.51.0. Atualizar é decisão de operação, com backup antes (regra "sempre LTS").

### RT-07 — `auditar_pilha.py` escolhe o MariaDB pela ordem alfabética do diretório — **Médio**

`scripts/auditar_pilha.py:463-465` pega `sorted(glob("mariadb-*/bin/mariadbd"), reverse=True)[0]`. Na máquina existem `mariadb-10.11.9-...` e `mariadb-10.11.19-...`; em ordem de texto, `10.11.9` vem **depois** de `10.11.19` (compara `9` com `1`), então o script sempre lê o binário **mais antigo** e reporta `instalada=10.11.9`. O `docs/auditoria-da-pilha.md` e o commit `38551eb` dizem que o MariaDB em uso é o **10.11.19** (trocado em 2026-10-09). O aviso de hoje é falso, e o contrário seria pior: um downgrade real ficaria mascarado. Correção: ordenar por tupla numérica da versão. No mesmo bloco, o Redis é procurado por um caminho com a versão escrita (`redis-7.2.16`, linha 457): quando o Redis for atualizado, o script continuará lendo o binário antigo enquanto a pasta existir. Mesma família de problema: a versão "instalada" é a do binário que o script escolhe, não a do que está rodando.

## CI (4.2)

`.github/workflows/ci.yml` tem **três** jobs: suíte pura (Python 3.12 + `lxml`), padrões de código (`ruff check` e `ruff format --check` em `erpnext_brasil/` e `scripts/`) e Cherry (núcleo com cobertura mínima de 95%). O `CLAUDE.md` descrevia só os dois primeiros (corrigido nesta revisão, ver [`documentacao.md`](documentacao.md)).

### RT-16 — não há job de bench — **Médio (declarado)**

Segue a lacuna de `docs/gaps.md`, seção 2. O que um job de bench exigiria, a partir do que `scripts/subir.sh` e `docs/ambiente-dev-bench.md` já fazem:

1. Runner Linux com MariaDB 10.11 e Redis 7.2 como serviços (o app já roda assim no WSL2, sem Docker nem sudo).
2. `bench init` com Frappe 16, `get-app erpnext` e `hrms`, mais `get-app` do próprio repositório; `new-site` e `install-app erpnext_brasil`.
3. `bench --site <site> run-tests --app erpnext_brasil`.
4. `python scripts/cobertura_de_bench.py` como degrau de aprovação.

Custo: dezenas de minutos por execução e cache do bench. Alternativa barata para o primeiro passo: rodar o job só em `push` na `main` e na abertura de PR com rótulo, não em todo PR. Esta revisão **não testou** esse desenho.

### Outras observações de CI

- O comentário de `ci.yml:3` cita "2.292 testes"; hoje são 3.490.
- A suíte pura roda em Python 3.12 no CI e em 3.14 no bench; o piso do app é `>=15` de Frappe. Não há matriz de versões de Python. **Aviso**, sem evidência de falha.
