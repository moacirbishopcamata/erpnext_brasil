## 1. Teste de conexão fora da thread da interface (CH-05)

- [x] 1.1 Escrever o teste de `test_app.py` com um `cfg.testar_conexao` lento (bloqueia num evento) e provar que `_testar_conexao` volta na hora, o botão vira "Parar de esperar" e a janela continua atendendo `update()` — verificar vendo-o falhar antes (a chamada bloqueia) e passar depois.
- [x] 1.2 Implementar a thread de trabalho com fila e consulta por `after`; segundo clique durante o teste não dispara outro, e "Parar de esperar" descarta o resultado — verificar com o teste da 1.1 e os de conectou, não conectou, parar de esperar e exceção.
- [x] 1.3 Cronometrar o ganho: com uma sonda simulada de 3 s, a janela responde em menos de 0,5 s — verificar com a medição registrada no teste ou em `docs/cherry.md`.

## 2. Interface coberta e no CI (CH-06)

- [x] 2.1 Testar os ramos de erro de `_gravar_banco` (OSError e JSON ilegível) e de `_copiar_new_site` (valor recusado) — verificar com a cobertura de `app.py` subindo e esses trechos fora da lista de linhas sem cobertura.
- [ ] 2.2 (**feito no `ci.yml`; só se prova no primeiro run do CI do PR**) Acrescentar ao job `cherry` do CI `xvfb` e `python3-tk`, `xvfb-run` nos testes e um segundo piso de cobertura para `app.py`, mantendo o de 95% do núcleo — verificar com o job verde no PR (o único lugar onde isso se prova) e o tempo dele.
- [x] 2.3 Definir o piso de `app.py` dois pontos abaixo da cobertura medida, e dizer no `docs/cherry.md` por quê — verificar relendo o doc.

## 3. Versão e documentação

- [x] 3.1 Subir para `0.2.1`, atualizar `docs/cherry.md` (testes, cobertura, CI) e marcar CH-05 e CH-06 resolvidos em `docs/revisao-do-cherry.md` — verificar pelo teste de versão e relendo os documentos.
- [x] 3.2 Rodar `python -m unittest scripts.cherry.test_config scripts.cherry.test_app`, `coverage` e `ruff` em `scripts/` — verificar com a saída verde.
