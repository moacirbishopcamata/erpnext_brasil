## Why

A revisão total (`revisao-total-erpnext-brasil`, 2026-10-11, versão `0.227.0`, commit `c1ef23d`) é o último retrato do app inteiro. Desde então entraram 38 commits na `main` e cerca de 9,9 mil linhas em 62 arquivos de código, quase todas em superfícies que **nenhuma revisão viu**: os pacotes puros das ferramentas de operação (`persistencia/`, `soda/`, `bancos/`, `sistema/`), a configuração Docker (`docker/`, `Dockerfile`, `docker-compose.yml`), `scripts/instalar_app_brasil.sh`, o Cherry de `0.2.0` a `0.4.0` (as duas revisões do Cherry pararam na `0.1.0`/`0.2.0`) e o job do Cherry no CI. Ao mesmo tempo, as correções dos achados RT-01, RT-02 e RT-03 (commit `b08beb7`, `0.228.0`) estão no código, mas as changes `corrigir-ano-da-folha` e `proteger-gerar-efd` seguem com 3 e 4 tarefas abertas: todas são **prova em bench que nunca rodou**. A síntese de `docs/revisao-total.md` já não descreve o sistema que existe.

## What Changes

- Executar uma **reanálise incremental, somente leitura**, com a mesma régua da revisão total (quatro níveis de severidade, evidência obrigatória, "a verificar" separado de achado).
- **Revisar as superfícies novas** desde `c1ef23d`: persistência selecionável (JSON, SQLite, memória), núcleo do Soda, perfis de banco, rede, Docker/Compose e segredos por arquivo, instalador do app, Cherry `0.4.0` e o CI.
- **Reconferir os 19 achados RT-01 a RT-19** contra o código atual: cada um sai como *resolvido (provado)*, *resolvido no código, sem prova em bench*, *aberto*, *mudou de severidade* ou *não reproduz*.
- **Tentar fechar a prova em bench** das correções de RT-01/02/03 (testes de `tests_bench/test_folha.py` e os de permissão ainda não escritos), no bench `version-16` do WSL2. Se o ambiente não subir, a síntese registra "não executado" em vez de presumir.
- Registrar como candidatos "a verificar" os pontos já observados fora da revisão: `contabil/` e `folha/` são puros só por convenção (`tests/test_arquitetura.py` não os checa); `docs/versoes-frappe-erpnext.md` e o comentário do `pyproject.toml` dizem que o bench de teste está em `version-15`, enquanto `scripts/subir.sh` usa `~/frappe-bench-16` como padrão.
- Produzir `docs/reanalise.md` (síntese datada, com o quadro de situação dos RT) e anexos em `docs/reanalise/`; atualizar `docs/revisao-total.md` só com um aviso de que foi sucedido, e reconciliar `docs/gaps.md`.
- Para cada achado novo Crítico ou Alto, **propor** (não implementar) a change de correção. Erro factual simples em documentação é corrigido na própria reanálise.
- **Não** altera código, Custom Fields, hooks, DocTypes nem dependências.

**Premissa registrada**: o pedido foi "reanálise do projeto/sistema", sem escopo explícito. Interpretado como reanálise incremental (o que mudou desde a revisão total, mais o estado dos achados anteriores), não uma terceira varredura do zero das ~100 mil linhas, porque o código fiscal, contábil e de integração só mudou no commit de correção `b08beb7`. A branch `hora-legal-br-como-reserva` (fonte de tempo), ainda não mesclada na `main`, fica fora; entra na próxima revisão depois da mescla.

## Capabilities

### New Capabilities

Nenhuma. A reanálise não muda comportamento do sistema; o change usa `skip_specs: true`.

### Modified Capabilities

Nenhuma.

## Impact

- Escreve apenas em `docs/` e em `openspec/changes/` (novas propostas de correção e marcação das tarefas de bench de `corrigir-ano-da-folha`/`proteger-gerar-efd`, se a prova rodar).
- Execução de bench, se houver, usa o banco compartilhado do WSL2: segue `docs/ambiente-dev-bench.md`, com backup antes.
- Sucede `docs/revisao-total.md` como retrato vigente; a revisão total fica como histórico e o change `revisao-total-erpnext-brasil` pode ser arquivado ao fim.
