# Versões de Frappe/ERPNext — Docker/compose vs. bench de teste real

> **Atualização de 2026-10-26: a divergência abaixo foi fechada.** O bench de teste (WSL2,
> `~/frappe-bench-16`) roda em `version-16` — Frappe `16.53.0`, ERPNext `16.52.1`, HRMS
> `16.52.0` —, e o `Dockerfile`/`docker-compose.yml` apontam para a mesma série. O texto
> daqui para baixo é o registro de 2026-09-03, quando o bench ainda estava em `version-15`;
> mantido como histórico. Versões, backup e testes da migração mais recente:
> [`atualizacao-do-bench-2026-10-26.md`](atualizacao-do-bench-2026-10-26.md). O que **continua**
> sem prova é `erpnext_brasil` sobre esse bench: o clone do app lá está atrasado e com trabalho
> local (ver [`reanalise/situacao-rt.md`](reanalise/situacao-rt.md)).

Pedido direto do usuário: manter sempre a versão **estável** mais recente de Frappe
Framework e ERPNext, tanto no `Dockerfile`/`docker-compose.yml` quanto na declaração de
compatibilidade do próprio `erpnext_brasil`.

## Versão estável confirmada em 2026-09-03

Checado direto em `github.com/frappe/frappe/releases` e `github.com/frappe/erpnext/releases`:

| Projeto | Última tag estável | Branch |
|---|---|---|
| Frappe Framework | `v16.33.0` | `version-16` |
| ERPNext | `v16.34.1` | `version-16` |

`version-16` é mais recente que o `version-15` (Frappe `15.119.1`/ERPNext `15.120.0`)
usado até agora no bench WSL2 deste projeto.

## O que foi atualizado

- **`Dockerfile`**: `ARG FRAPPE_VERSION` default trocado de `version-15` para
  `version-16` — a imagem `frappe/erpnext:version-16` já traz Frappe e ERPNext
  `version-16` prontos.
- **`docker-compose.yml`**: serviço `nginx` trocado para `frappe/erpnext:version-16`
  (precisa bater com a versão da imagem construída pelo `Dockerfile`, senão o proxy
  reverso e o backend divergem de versão de assets).
- **`pyproject.toml`**: `[tool.bench.frappe-dependencies]` continua com piso aberto
  (`>=15.0.0`, sem teto) — comentário novo cita a versão estável mais recente e onde
  conferir, sem impor um teto artificial que quebraria a instalação assim que a
  próxima versão sair.

## Achado real, declarado: o bench de teste (WSL2) continua em `version-15`

**Não foi migrado nesta sessão.** O bench WSL2 (`docs/ambiente-dev-bench.md`) é o único
ambiente onde este app foi de fato confirmado funcionando de ponta a ponta (`bench
run-tests`, 1671 testes contra banco/Redis reais) — e ele está em `version-15`, não
`version-16`. Migrar um bench já funcionando para uma versão maior é uma operação de
risco real (schema de banco, dependências, possíveis breaking changes entre majors do
Frappe/ERPNext) que não foi pedida nem tentada aqui.

**Consequência honesta**: `Dockerfile`/`docker-compose.yml` apontam para `version-16`
(a versão estável mais recente, como pedido), mas essa combinação específica
(`erpnext_brasil` + Frappe/ERPNext `version-16`) **não foi testada de ponta a ponta**
em lugar nenhum ainda — só o bench `version-15` tem essa confirmação. Como este app usa
só APIs estáveis do Frappe (custom fields via `create_custom_fields`, `doc_events`,
`frappe.get_doc`/`get_meta`/`db_set`), a expectativa razoável é que funcione sem
mudança — mas "expectativa razoável" não é o mesmo que "verificado", e essa distinção
fica registrada aqui em vez de escondida atrás de uma versão de Docker que parece
testada só porque está escrita no arquivo.

## Quando reconciliar

Migrar o bench WSL2 para `version-16` (ou criar um segundo bench só para isso) é o
próximo passo natural para fechar essa lacuna — não feito aqui porque não foi pedido e
teria risco de quebrar o único ambiente de teste real que este projeto tem hoje.
