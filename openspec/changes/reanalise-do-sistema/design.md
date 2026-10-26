## Context

Ver `proposal.md` (Why). Estado atual que molda o método:

- A régua já existe: `openspec/changes/revisao-total-erpnext-brasil/design.md` define severidade em quatro níveis, evidência obrigatória e "costura primeiro". A reanálise **herda** essa régua sem redefini-la, para que RT-xx e achados novos sejam comparáveis.
- O código novo desde `c1ef23d` é, em sua maioria, **puro e desktop**: `persistencia/`, `soda/`, `bancos/`, `sistema/` não importam `frappe`, `tkinter` nem `integracao/` (imposto por `TestPacotesPurosDasFerramentas` em `tests/test_arquitetura.py`). A costura desses pacotes não é com o Frappe: é com o **disco** (JSON, SQLite, arquivos de configuração do bench) e com o **sistema** (portas, processos, Docker).
- Fora dele, há superfícies com efeito externo: `docker/construir.py` e `docker/preparar.py` (montagem de imagem e de segredos), `docker/compose*.yaml`, `scripts/instalar_app_brasil.sh` e `scripts/cherry/` (escreve `common_site_config.json` e perfis de banco).
- Do lado Frappe, só o commit `b08beb7` mexeu: `folha/periodo.py`, `integracao/{folha,geracao_efd,navegador_estoque,alerta_fiscal,pix}.py`, com guardas por `ast` (`test_whitelist_com_permissao.py`, `test_periodo_folha.py`) mas sem prova em bench.
- Há bench `version-16` no WSL2 (`~/frappe-bench-16`) e o Bash de worktree não chama `wsl` diretamente: execução de bench vai por script em arquivo, disparado via PowerShell, com log.

## Goals / Non-Goals

**Goals:**
- Um quadro de situação dos 18 RT que distinga "corrigido no código" de "provado".
- Cobrir as superfícies novas com a mesma profundidade que a revisão total deu às frentes fiscais.
- Fechar, se o ambiente permitir, a lacuna de prova em bench deixada pelas correções de `0.228.0`.

**Non-Goals:**
- Reler as frentes fiscais, contábeis e de folha que não mudaram desde `c1ef23d`; elas herdam o retrato da revisão total, exceto onde um RT aponta.
- Revisar o laboratório SUS: o núcleo saiu deste repositório (commit `00e0d39`) e tem repositório próprio.
- Revisar a branch `hora-legal-br-como-reserva` antes da mescla.
- Corrigir código (exceto erro factual em doc) ou escrever o teste de bench que falta além do necessário para provar RT-01/02/03 (ver Decisão 4).

## Decisions

1. **Escopo por diferença, não por inventário.** O conjunto revisado é `git diff --stat c1ef23d..<commit da reanálise>` sobre `erpnext_brasil/`, `scripts/`, `docker/`, `Dockerfile`, `docker-compose.yml` e `.github/`, mais os arquivos citados nos RT. *Alternativa*: varredura completa de novo. Rejeitada: repetiria nove frentes onde o código não mudou e diluiria o esforço nas superfícies que nunca foram vistas. O commit de partida e o de chegada ficam fixados na linha de base, para a próxima reanálise partir dele.

2. **Frentes da reanálise.** Quatro frentes novas, mais o quadro dos RT:
   - **Persistência e dados das ferramentas** (`persistencia/`, `bancos/`, `soda/registro.py`, `soda/diario.py`): escrita atômica, migração JSON→SQLite, concorrência entre processos, pós-condição de escrita, e se `test_persistencia_contrato.py` relê por caminho independente ou só confere o retorno.
   - **Docker, instalador e segredos** (`docker/`, `Dockerfile`, `docker-compose.yml`, `scripts/instalar_app_brasil.sh`): segredo por arquivo vs. variável de ambiente, permissões, imagem fixada por digest/tag, `subprocess`/`shell`, e se a promessa de `docs/docker.md` bate com o que `test_docker.py` prova.
   - **Cherry `0.4.0` e Soda** (`scripts/cherry/`, `soda/`, `sistema/rede.py`): o que mudou desde a revisão do Cherry (perfis de banco, instâncias por UUID), escrita em arquivo do bench, segredo e clipboard, identidade da instância.
   - **Arquitetura, CI e documentação**: se `test_arquitetura.py` ainda descreve a arquitetura real (pureza de `contabil/`/`folha/` não imposta), o job do Cherry no CI, `docs/README.md` contra os docs novos e a divergência `version-15`/`version-16`.
   *Alternativa*: encaixar o novo nas nove frentes antigas. Rejeitada: as ferramentas de operação não têm frente correspondente; "integração Frappe" e "setup" não descrevem um núcleo desktop sem Frappe.

3. **Situação de cada RT em cinco estados.** *Resolvido e provado* (teste que falha sem a correção, executado); *resolvido no código, sem prova* (guarda estática ou leitura, sem execução no ambiente que importa); *aberto*; *mudou de severidade* (com motivo); *não reproduz* (achado original errado, com evidência). *Alternativa*: binário aberto/fechado. Rejeitada: esconderia justamente a lacuna atual, em que RT-01/02/03 estão "corrigidos" sem nunca terem rodado contra banco.

4. **Bench: tentar, com limite.** A reanálise sobe o bench (`SO_SERVICOS=1 bash scripts/subir.sh`, depois `bench run-tests --module`) e roda os testes de bench **já escritos** que provam RT-01 (`tests_bench/test_folha.py`). Os testes de permissão de RT-02/RT-03 ainda não existem; escrevê-los é código e pertence às changes `proteger-gerar-efd`/`corrigir-ano-da-folha`, não à reanálise. A reanálise só relata que faltam. Se o ambiente não subir em tempo razoável, registra "não executado" com a saída do erro. *Alternativa*: não rodar bench, como na revisão total. Rejeitada: é exatamente a prova que falta para mudar o estado de três RT.

5. **Achado novo nasce com ID próprio.** `RA-01`, `RA-02`… (reanálise), para não colidir com RT-xx nem sugerir que é continuação de um achado antigo. Um RT que reaparece mantém o ID original.

6. **Saída em dois níveis, ao lado da revisão total.** `docs/reanalise.md` (síntese, quadro dos RT, achados RA por severidade, o que não foi executado) e `docs/reanalise/<frente>.md`. `docs/revisao-total.md` ganha só uma linha no topo apontando para a sucessora, sem reescrita, para continuar servindo de histórico datado. *Alternativa*: sobrescrever `docs/revisao-total.md`. Rejeitada: perderia o retrato da `0.227.0` contra o qual os estados dos RT são medidos.

7. **Revisão em linha, sem subagentes**, como na revisão total: a severidade fica consistente entre frentes quando uma só leitura classifica tudo.

## Risks / Trade-offs

- [Escopo por diferença perde regressão indireta: código que não mudou mas passou a ser chamado de outro jeito] → cruzar os pontos de entrada novos (`hooks.py`, `__main__`, scripts) com quem os chama; o que não puder ser descartado vira "a verificar".
- [Bench compartilhado e WSL2 frágil (Bash da worktree não chama `wsl`)] → script em arquivo + PowerShell + log; backup antes conforme `docs/ambiente-dev-bench.md`; nenhum dado de produção.
- [Testes de bench de RT-02/03 não existem, então esses RT não podem sair como "provado"] → declarado na Decisão 4; ficam "resolvido no código, sem prova", com apontamento para a change dona.
- [Revisar o Cherry de novo pode repetir as revisões anteriores] → partir dos achados CH-xx já fechados e olhar só o diff desde a `0.2.0`.
- [Docker não está construído e só roda no WSL] → a frente avalia configuração e o que `test_docker.py` resolve; construir a imagem não é exigido e, se não for feito, fica declarado.
- [Fonte de versão/CVE muda rápido] → toda versão citada traz URL e data da consulta.

## Migration Plan

Não se aplica: nada é implantado. Ao fim, `revisao-total-erpnext-brasil` (23/23 tarefas) pode ser arquivado, e o change desta reanálise também, depois que as propostas de correção existirem.
