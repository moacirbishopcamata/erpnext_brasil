## Why

Dois achados da revisão do Cherry (`docs/revisao-do-cherry.md`) andam juntos e bloqueiam a etapa de executar `bench` de dentro dele:

- **CH-05:** `_testar_conexao` chama `cfg.testar_conexao` na thread da interface (`app.py`), com `timeout=30` por sonda; até ~63 s com a janela sem responder. A Microsoft pede feedback e como parar numa operação longa.
- **CH-06:** a interface não tem teste no CI. O job `cherry` roda com `--include=config.py` e `test_app.py` pula sem display; `app.py` tem 83% de cobertura na máquina com display, e todo o `_testar_conexao` estava sem teste. Executar `bench` (operação ainda mais longa) em cima de uma interface sem rede de segurança no CI é o risco.

## What Changes

- O teste de conexão roda numa thread de trabalho; a interface só consulta o resultado por `after` (tkinter não é seguro entre threads). Enquanto roda, o botão vira "Parar de esperar", a barra de estado diz que está testando e o segundo clique não dispara outro teste. "Parar de esperar" descarta o resultado quando chegar; não mata o processo da sonda, que termina sozinha pelo `timeout`.
- Exceção inesperada da sonda vira mensagem na tela, não thread morta.
- Testes novos de `test_app.py` para `_testar_conexao` (conectou, não conectou, parar de esperar, exceção) e para os ramos de erro de gravar o banco e de copiar o `new-site`.
- O CI passa a rodar `test_app.py` com display virtual (`xvfb`) e a medir a cobertura de `app.py` com um piso próprio, mantendo o piso de 95% do núcleo.

## Capabilities

### New Capabilities

Nenhuma. O Cherry não tem spec em `openspec/specs/`; o change usa `skip_specs: true`.

### Modified Capabilities

Nenhuma.

## Impact

- `scripts/cherry/app.py`, `scripts/cherry/test_app.py`, `scripts/cherry/__init__.py` (`0.2.1`: não muda o que o usuário vê além do botão durante o teste, então `patch`).
- `.github/workflows/ci.yml` (job `cherry`: `apt` de `xvfb` e `python3-tk`, `xvfb-run`, segundo piso).
- Documentação: `docs/cherry.md`, `docs/revisao-do-cherry.md` (marcar CH-05 e CH-06 resolvidos).
- Risco: o passo de `xvfb` só se prova de verdade no primeiro run do CI; se falhar, o ajuste é no PR.
