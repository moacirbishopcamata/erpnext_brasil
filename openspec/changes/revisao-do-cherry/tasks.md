## 1. Linha de base

- [x] 1.1 Registrar versão, commit, data e números do Cherry (linhas por arquivo, testes, funções públicas) em `docs/revisao-do-cherry/linha-de-base.md` — verificar conferindo cada número com o comando que o gerou, citado no arquivo.
- [x] 1.2 Rodar `python -m unittest scripts.cherry.test_config scripts.cherry.test_app`, `coverage` como no job `cherry` do CI, `ruff check` e `ruff format --check` em `scripts/` — verificar pela saída copiada no documento, com a cobertura real do `config.py` e do `app.py`.
- [x] 1.3 Dizer se `test_app.py` rodou ou pulou nesta máquina e por quê (display) — verificar pelo resumo do `unittest` (testes pulados) no documento.

## 2. Segredo e escrita de arquivo (prioridade)

- [x] 2.1 Medir se a senha de root aparece na lista de processos durante `testar_conexao` pelo caminho do WSL, e ler `comando_new_site` para o que vai ao clipboard — verificar com a saída da medição (ou "não medido, motivo") e arquivo e linha de cada ponto.
- [x] 2.2 Rastrear todo caminho que a senha percorre (campo da tela, `Banco`, `repr`, mensagem de erro, `~/.cherry.json`, `common_site_config.json`) e provar com teste ou leitura que `~/.cherry.json` e os logs nunca a recebem — verificar com a lista de caminhos e uma busca por `senha`/`password` em `scripts/cherry/` fora de testes.
- [x] 2.3 Auditar `gravar_json` e `gravar_apps_txt`: atomicidade, queda no meio da escrita, permissão negada, caminho `\\wsl.localhost\` indisponível, arquivo existente com formato inesperado — verificar com teste em diretório temporário que cria cada situação e relê os bytes por caminho independente.
- [x] 2.4 Conferir a decisão de que campo vazio **remove** a chave em "Portas e Redis" contra o risco de apagar uma chave que o usuário não viu — verificar com o caso de teste e a mensagem na tela.

## 3. Núcleo e interface

- [x] 3.1 Ler `config.py` por inteiro: contratos (`CherryInvalido`), imutabilidade, injeção do executor, nomes, métodos estáticos e `sealed`-equivalentes — verificar com a lista de achados e a cobertura de linhas do arquivo, que deve ser 100% como o doc promete.
- [x] 3.2 Ler `app.py` por inteiro: o que está no núcleo e deveria estar fora da interface, estado duplicado, tratamento de exceção, ação longa que trava a janela — verificar com arquivo e linha por achado.
- [x] 3.3 Cruzar a tabela "As cinco abas" e a tabela de UX de `docs/cherry.md` com o que o código faz — verificar com a lista de linhas do doc confirmadas, divergentes e não verificáveis.

## 4. Testes, CI e UX

- [x] 4.1 Avaliar se os testes miram na costura (releitura do arquivo gravado) ou só no retorno, e se `test_app.py` cobre os caminhos de erro — verificar com a lista de funções sem teste de costura.
- [x] 4.2 Avaliar o job `cherry` do CI: o que ele prova e o que não prova, e o custo de um passo com `xvfb` para a interface — verificar com proposta concreta de mudança no `ci.yml`, sem aplicar.
- [x] 4.3 Reler as fontes de UX do doc na web e verificar na tela (se houver display) teclado, foco, Enter, HiDPI, janela redimensionada e tamanho mínimo — verificar com a lista de diretrizes confirmadas e a evidência (captura ou "sem display").

## 5. Documentação e roteiro

- [x] 5.1 Reconciliar `docs/cherry.md` e `scripts/cherry/README.md` com o código (versão, número de testes, cobertura, abas) e corrigir erro factual simples — verificar pela lista de divergências e o `git diff` só em docs.
- [x] 5.2 Escrever os requisitos de segurança e de UX da próxima etapa do roteiro (executar `bench`) — verificar relendo que cada requisito responde a um achado ou a uma decisão da seção 6 do `design.md`.

## 6. Síntese e fila

- [x] 6.1 Escrever `docs/revisao-do-cherry.md` com achados por severidade, cobertura real por frente, o que não foi executado e a fila de correções — verificar relendo que cada achado tem evidência e link para o anexo.
- [x] 6.2 Indexar a síntese em `docs/README.md` e `scripts/cherry/README.md` — verificar abrindo os dois.
- [x] 6.3 Criar a proposta de change de correção de cada achado Crítico e Alto, ou registrar por que não — verificar com `openspec list` mostrando as propostas novas.
- [x] 6.4 Rodar de novo os testes do Cherry e `ruff` para confirmar que a revisão não alterou código — verificar com `git diff --stat` mostrando só `docs/`, `openspec/` e o `README.md` do Cherry.
