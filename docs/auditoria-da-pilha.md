# Auditoria da pilha do bench (versões e CVE)

Resultado da primeira execução real de `scripts/auditar_pilha.py` contra o `~/frappe-bench-16`, em **2026-10-09**,
e o que foi feito a partir dela. O script usa só a biblioteca padrão, consulta endoflife.date, as releases e os
*security advisories* do GitHub, o PyPI e o OSV, e sai com código 1 se houver série fora de suporte, vulnerabilidade
alta/crítica que afete a versão instalada, ou componente que não se consiga verificar.

```sh
python3 scripts/auditar_pilha.py --bench ~/frappe-bench-16        # --json para máquina
```

## Antes → depois

| Componente | Antes | Depois | Observação |
|---|---|---|---|
| Frappe | 16.36.1 | **16.51.0** | série 16 é a estável mais nova; sem rótulo LTS |
| ERPNext | 16.37.0 | **16.50.0** | |
| HRMS | 16.20.1 | **16.50.0** | |
| bench (CLI) | 5.31.0 | 5.31.0 | já era a última no PyPI |
| Redis | 7.0.15 (pacote Ubuntu) | **7.2.16** (compilado em espaço de usuário) | sha256 conferido |
| MariaDB | 10.11.9 | **10.11.19** (trocado em 2026-10-09) | desligamento limpo, cópia do datadir (498 MB) em `~/mariadb-data.bak-10.11.9-*`; `mariadb-upgrade` dispensado (mesma série 10.11); testes de bench passam |
| Python (venv) | 3.14.6 | 3.14.6; **3.14.8 pendente** | recriar o venv com cópia do atual |
| Node | 24.21.0 | 24.21.0 | já era a última da série |
| pypdf / Werkzeug / urllib3 | 6.15.0 / 3.1.6 / 2.7.0 | 6.19.0 / 3.1.9 / 2.8.0 | CVEs corrigidos |
| PyJWT | 2.13.0 | **2.15.1** | pin `~=2.15.0` (a `develop` do Frappe já tem) |
| oauthlib | 3.3.1 | **4.0.0** | pin `~=4.0.0` (a `develop` já tem); major |
| WeasyPrint | 68.0 | **70.0** | 69 e 70 foram releases de segurança |
| GitPython | 3.1.61 | **3.1.62** | dentro do pin `~=3.1.45` (a 3.2.0 foi recusada: fora do pin) |
| bleach | — | **6.4.0** | |

Os três sites (`v16.localhost`, `v16pg.localhost`, `fr16pg.localhost`) migraram sem erro.

## O que o Frappe não corrigiu na série 16

O PR de PyJWT/oauthlib foi mesclado só na `develop` e o de WeasyPrint foi fechado sem mesclar. Os pins estão no
branch de patches do bench (`frappe-v16-pg-patches`), com a mesma lógica dos patches de PostgreSQL de `contrib/`:
devolver ao upstream, não esconder.

## Verificação após as trocas

- PDF: `frappe.utils.pdf.get_pdf` gera PDF válido com WeasyPrint 70.0.
- JWT: codificação e decodificação HS256 com PyJWT 2.15.1.
- OAuth: `frappe.oauth` importa, `get_oauth_server()` devolve o servidor, o validador herda de `RequestValidator`.
- ⚠️ **Não rodei** `frappe.tests.test_oauth20` nem `test_pdf`: o `run-tests` do Frappe passou mais de 10 minutos
  criando registros de teste e foi interrompido. O que há é um teste de fumaça, não a suíte do Frappe.

## Pendências declaradas

- **pdfkit 1.0.0 — CVE-2025-26240 (alta), sem versão corrigida.** É dependência do Frappe e não há correção
  publicada. Risco aceito e registrado: o caminho vulnerável é `from_string`, e o app não o chama diretamente.
  Revisar a cada release do pdfkit.
- **Avisos "indeterminados"**: CVE-2026-63654, CVE-2026-62315 e CVE-2026-53569 vêm do GitHub sem faixa de
  versão. Conferidos no OSV: todos têm `last_affected = 16.31.0`, e a instalada é a 16.51.0 — **não afetam**.
  O script ainda os lista como indeterminados porque lê só a faixa do GitHub.
- Trocar o Python (3.14.6 → 3.14.8): recriar o venv do bench com cópia do atual.
- ⚠️ MariaDB: o servidor é compartilhado com outra sessão; a troca só foi feita com autorização explícita do usuário, depois de confirmar zero conexões. O `subir.sh` chamado com `| tail` fica pendurado (o `mariadbd` herda o pipe): redirecione para arquivo.
- O backup do `banking/yarn.lock` do ERPNext foi salvo à parte antes da atualização.

## Reauditoria de 2026-10-26 (depois da atualização do bench)

Frappe `16.53.0`, ERPNext `16.52.1` e HRMS `16.52.0` agora "em dia". Falhas do script: **40 → 5**, críticas **7 → 0**
(Pillow 13.0.0, certifi, brotli, virtualenv e filelock atualizados). As 5 que sobram são pin do Frappe (`pypdf==6.19.0`,
`GitPython~=3.1.45`) ou sem correção (`pdfkit`). Detalhe, backup, patches locais e testes:
[`atualizacao-do-bench-2026-10-26.md`](atualizacao-do-bench-2026-10-26.md). O aviso de MariaDB atrasado continua
**falso** (RT-07): o `10.11.19` existe em `~`, o script lê o `10.11.9`.

## Imagens Docker (registradas em 2026-10-11, ainda não auditadas pelo script)

A configuração `docker/` ([`docker.md`](docker.md)) fixa versões de terceiros que `scripts/auditar_pilha.py` **ainda não verifica**. Registro do que está em uso, para a auditoria passar a conferi-las:

| Componente | Versão no Compose | Origem | Observação |
|---|---|---|---|
| MariaDB | 11.8 | `overrides/compose.mariadb.yaml` do frappe_docker | o desenvolvimento local usa 10.11 |
| PostgreSQL | 15.17 | `overrides/compose.postgres.yaml` do frappe_docker | o desenvolvimento local usa 18 |
| Redis | 8.6-alpine | `overrides/compose.redis.yaml` do frappe_docker | o desenvolvimento local usa 7.2 |
| Receita de imagem | commit `2b26e9ab8d75...` do frappe_docker (2026-10-09) | `docker/construir.py` | atualização manual e consciente |

Pendente: estender `auditar_pilha.py` para ler essas versões (variáveis do `.env.example` e a constante `FRAPPE_DOCKER_COMMIT`) e conferi-las contra o fim de suporte e os avisos de segurança.
