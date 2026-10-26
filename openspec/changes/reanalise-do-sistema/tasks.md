## 1. Linha de base

- [ ] 1.1 Fixar o commit de partida (`c1ef23d`, revisão total) e o de chegada (HEAD da `main` no início da aplicação), `__version__` e data em `docs/reanalise/linha-de-base.md`, com a lista de arquivos de `git diff --stat c1ef23d..<chegada>` sobre `erpnext_brasil/`, `scripts/`, `docker/`, `Dockerfile`, `docker-compose.yml` e `.github/` — verificar conferindo que o comando que gerou cada número está citado no próprio arquivo.
- [ ] 1.2 Rodar a suíte pura, `ruff check erpnext_brasil/ scripts/`, `ruff format --check erpnext_brasil/ scripts/` e os testes do Cherry com cobertura (mesmos comandos do `ci.yml`) e registrar o resultado — verificar pela saída copiada no documento, com a contagem de testes comparada aos 3.490 da revisão total.
- [ ] 1.3 Rodar `python scripts/cobertura_de_bench.py` e comparar com o 13/13 da revisão total — verificar pela lista no documento.

## 2. Situação dos achados anteriores (RT-01 a RT-18)

- [ ] 2.1 Para cada RT, reler o arquivo e a linha citados em `docs/revisao-total.md` contra o código atual e classificar em um dos cinco estados do design (Decisão 3) — verificar com uma tabela em `docs/reanalise/situacao-rt.md` em que cada linha tem evidência (arquivo:linha, commit ou saída de comando).
- [ ] 2.2 Subir o bench `version-16` no WSL2 (script em arquivo + PowerShell + log; `SO_SERVICOS=1 bash scripts/subir.sh`; backup antes conforme `docs/ambiente-dev-bench.md`) — verificar pelo log anexado, ou registrar "não executado" com o erro.
- [ ] 2.3 Se o bench subiu, rodar `bench --site <site> run-tests --app erpnext_brasil --module erpnext_brasil.tests_bench.test_folha` e atualizar o estado de RT-01 — verificar com a saída do teste no anexo; se passar, marcar as tarefas 1.1/1.2 de `corrigir-ano-da-folha` citando a saída.
- [ ] 2.4 Registrar quais testes de bench faltam para RT-02/RT-03 (tarefas 1.1 e 2.1 de `proteger-gerar-efd`), sem escrevê-los — verificar com o apontamento para a change dona em `situacao-rt.md`.
- [ ] 2.5 Reconferir RT-07 (`auditar_pilha.py` e a versão do MariaDB) rodando `python3 scripts/auditar_pilha.py --bench ~/frappe-bench-16` no WSL2, e checar na web CVE de Frappe/ERPNext/bench desde 2026-10-09 — verificar com a saída do script e as URLs consultadas, com data.

## 3. Revisão das superfícies novas

Para cada frente: ler os módulos que escrevem em disco, abrem processo, tocam rede ou guardam segredo; classificar cada achado (Crítico, Alto, Médio, Baixo) com ID `RA-xx` e evidência; escrever `docs/reanalise/<frente>.md`. Verificação de cada item: o anexo existe, todo achado tem evidência e a cobertura (o que foi lido, o que foi só varrido) está declarada.

- [ ] 3.1 Persistência e dados das ferramentas (`persistencia/`, `bancos/`, `soda/registro.py`, `soda/diario.py`): escrita atômica, migração JSON→SQLite, concorrência entre processos, pós-condição de escrita e se `test_persistencia_contrato.py` relê por caminho independente — anexo `persistencia.md`.
- [ ] 3.2 Docker, instalador e segredos (`docker/`, `Dockerfile`, `docker-compose.yml`, `scripts/instalar_app_brasil.sh`): segredo por arquivo, permissões, tag/digest das imagens, `subprocess`/`shell`, e a promessa de `docs/docker.md` contra o que `test_docker.py` prova — anexo `docker-e-instalador.md`.
- [ ] 3.3 Cherry `0.4.0` e Soda (`scripts/cherry/` desde a `0.2.0`, `soda/`, `sistema/rede.py`): perfis de banco, instâncias por UUID, escrita no `common_site_config.json`, segredo e clipboard, identidade da instância, partindo dos achados CH-xx já fechados — anexo `cherry-e-soda.md`.
- [ ] 3.4 Arquitetura, CI e documentação: se `test_arquitetura.py` cobre a arquitetura real (pureza de `contabil/`/`folha/` não imposta), o job do Cherry no `ci.yml`, `docs/README.md` contra os docs novos desde `c1ef23d`, e a divergência `version-15`/`version-16` entre `docs/versoes-frappe-erpnext.md`, `pyproject.toml` e `scripts/subir.sh` — anexo `arquitetura-ci-docs.md`; erro factual simples em doc é corrigido na hora e listado.
- [ ] 3.5 Regressão indireta: cruzar os pontos de entrada novos (`hooks.py`, `scripts/*/__main__.py`, `docker/*.py`, `scripts/*.sh`) com quem os chama, para achar código antigo alcançado de um jeito novo — verificar com a lista de pontos cruzados no anexo de arquitetura, e o que não puder ser descartado em "a verificar".

## 4. Síntese e fila de correções

- [ ] 4.1 Escrever `docs/reanalise.md`: commits de partida e chegada, números comparados à revisão total, quadro de situação dos RT, achados RA por severidade com link ao anexo, o que não foi executado (bench, Docker construído, homologação SEFAZ) — verificar relendo que cada achado da síntese tem link e evidência.
- [ ] 4.2 Acrescentar no topo de `docs/revisao-total.md` uma linha apontando para `docs/reanalise.md` como retrato vigente, indexar `docs/reanalise.md` e `docs/reanalise/` em `docs/README.md` e reconciliar `docs/gaps.md` (itens resolvidos, novos, data e versão no cabeçalho) — verificar abrindo os três arquivos.
- [ ] 4.3 Para cada achado RA Crítico ou Alto, criar a proposta de change de correção (`openspec/changes/<nome>`) ou registrar por que não — verificar com `openspec list` mostrando as propostas novas.
- [ ] 4.4 Confirmar que a reanálise não alterou código: rodar de novo a suíte pura e `ruff`, e `git diff --stat` mostrando só `docs/` e `openspec/` — verificar pela saída anexada à síntese.
