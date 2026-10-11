## Why

A revisão do Cherry (`docs/revisao-do-cherry.md`) mediu dois problemas Altos e dois Médios que impedem dar ao Cherry o poder de executar `bench`:

- **CH-01:** a senha de root do banco vai como argumento de linha de comando da sonda de conexão (`config.py:393-402`); medido no Windows, ela aparece em texto puro na linha de comando do processo.
- **CH-02:** `_gravar_texto` (`config.py:176-187`) trunca o destino antes de escrever; uma falha no meio deixou um `common_site_config.json` de 92 bytes com 10 bytes e JSON inválido.
- **CH-03:** o `bench new-site` copiado escapa só as senhas; host, usuário, site e nomes de app entram sem aspas (`config.py:310-338`).
- **CH-04:** a senha de administrador vem pré-preenchida com `admin` (`app.py:210`) e o comando com as senhas fica no clipboard sem limpeza (`app.py:388-389`).

## What Changes

- A sonda de conexão recebe a senha por variável de ambiente do processo filho (ou `stdin`), nunca por argumento, nos três níveis (WSL, local; o TCP não usa senha).
- `_gravar_texto` grava em arquivo temporário na mesma pasta e troca com `os.replace`; se algo falhar, o original fica intacto e o temporário é removido.
- `comando_new_site` aplica aspas de shell a todos os valores, ou recusa caracteres fora de `[A-Za-z0-9._:-]` em host, usuário, site e nomes de app (decidir na aplicação; a recusa é mais simples e mais segura).
- A senha de administrador deixa de vir com valor pronto: campo vazio e o comando omite `--admin-password` (o `bench` pergunta), ou gera uma senha aleatória mostrada uma vez. Decidir na aplicação.
- O clipboard é limpo depois de um tempo (por exemplo 60 s) se ainda contiver o comando copiado; o aviso diz isso.
- Versão do Cherry sobe para `0.2.0` (mudança visível: a senha deixa de trafegar por argumento e o campo da senha de administrador muda); `docs/cherry.md` atualizado.

## Capabilities

### New Capabilities

Nenhuma. O Cherry não tem spec em `openspec/specs/`; o change usa `skip_specs: true`.

### Modified Capabilities

Nenhuma.

## Impact

- `scripts/cherry/config.py`, `scripts/cherry/app.py`, `scripts/cherry/__init__.py`.
- Testes: `scripts/cherry/test_config.py` (executor injetado que prova a ausência da senha em `argv`, escrita que falha no meio, comando com valores hostis) e `test_app.py` (campo de administrador, limpeza do clipboard).
- Documentação: `docs/cherry.md`, `docs/revisao-do-cherry.md` (marcar CH-01 a CH-04 resolvidos).
- Comportamento visível: o comando copiado muda quando a senha de administrador fica vazia; a janela avisa que o clipboard será limpo.
