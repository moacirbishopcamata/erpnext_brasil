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
| MariaDB | 10.11.9 | 10.11.19 baixado; **troca pendente** | só com o servidor compartilhado livre |
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
- Trocar o MariaDB (10.11.9 → 10.11.19, com `mariadb-upgrade`) e o Python (3.14.6 → 3.14.8).
- O backup do `banking/yarn.lock` do ERPNext foi salvo à parte antes da atualização.
