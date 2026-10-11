# Revisão do Cherry — segredo e escrita de arquivo

Cobre as tarefas 2.1 a 2.4 do change `revisao-do-cherry`. Medições feitas em 2026-10-11 com um script em diretório temporário, sem tocar em nenhum bench.

## CH-01 — a senha de root vai como argumento de linha de comando — **Alto**

`testar_conexao` monta `argumentos = [tipo, host, porta, usuario_root, senha_root]` (`config.py:393`) e os passa depois do `-c <sonda>` em `wsl -d <distro> -- <python do bench> -c ... *argumentos` e em `python -c ... *argumentos` (`config.py:395-402`). Argumento de processo é legível por outros processos.

- **Medido (Windows):** com o executor injetável, lancei um processo com os mesmos cinco argumentos e li `Win32_Process.CommandLine` por outro processo: **a senha de teste aparece em texto puro**.
- **Não medido:** o `ps` dentro do WSL (mesmo mecanismo no Linux, onde qualquer usuário local vê a linha de comando).
- Alcance: uma senha de administrador de banco de desenvolvimento, visível por até 30 segundos (o `timeout` da sonda), a qualquer processo da mesma máquina.
- Correção natural: entregar a senha por variável de ambiente do processo filho ou por entrada padrão (`stdin`), nunca por argumento. O executor já é injetável, então o teste prova isso sem `wsl`.

## CH-02 — a gravação de arquivo não é atômica — **Alto**

`_gravar_texto` (`config.py:176-187`) abre o destino com `"w"` (que **trunca na hora**) e depois escreve. Toda gravação do Cherry passa por ela: `common_site_config.json` (banco, Redis, portas), `apps.txt` e `~/.cherry.json`.

- **Medido:** simulei falha de escrita depois de 10 bytes sobre um `common_site_config.json` de 92 bytes. Resultado: o arquivo ficou com **10 bytes e deixou de ser JSON válido**. O conteúdo anterior se perdeu.
- Consequência: um disco cheio, uma queda de energia ou uma queda do compartilhamento `\wsl.localhost\...` no meio da escrita deixa o bench sem configuração de banco e de Redis, e o Cherry só mostra o erro depois do dano.
- Correção natural: gravar num arquivo temporário na mesma pasta e trocar com `os.replace`, preservando o original se algo falhar. O teste de costura (reler os bytes por outro caminho) já existe como método; falta o caso de falha no meio.

### Comportamentos que **estão certos** (medidos)

| Situação | Resultado |
|---|---|
| JSON existente corrompido | `JSONDecodeError`, **arquivo intacto** (não grava por cima) |
| JSON que é lista, não objeto | `CherryInvalido`, arquivo intacto |
| Arquivo somente leitura | `PermissionError` |
| Distro do WSL que não existe | `FileNotFoundError` |

## CH-03 — o `bench new-site` copiado só escapa as senhas — **Médio**

`comando_new_site` (`config.py:310-338`) coloca `_aspas(...)` só em `--db-root-password` e `--admin-password`. `site`, `host`, `usuario_root` e os nomes de app entram **sem aspas**; a validação do site recusa só espaço, e a de app (`gravar_apps_txt`) recusa só espaço e `/`.

- **Medido:** com host `127.0.0.1;touch${IFS}/tmp/h`, usuário `root;id` e app `$(id)`, o comando gerado contém essas strings cruas. Quem cola no terminal executa `touch` e `id`.
- Alcance: valores digitados pelo próprio usuário, ou lidos do `apps.txt` do bench (que `ler_apps_txt` não valida). Risco baixo de exploração, mas o comando é feito para ser colado num shell.
- Correção: aspas do shell em todos os valores, ou recusar caracteres fora de `[A-Za-z0-9._:-]` nos nomes.

## CH-04 — senha de administrador padrão e senhas na área de transferência — **Médio**

- `self.senha_admin = tk.StringVar(value="admin")` (`app.py:210`): o comando copiado sai com `--admin-password 'admin'` se o usuário não trocar. O `docs/cherry.md` promete "padrões seguros", e a diretriz da Microsoft que o doc cita manda escolher o valor mais seguro por padrão.
- `_copiar_new_site` põe o comando, com as duas senhas, no clipboard (`app.py:388-389`) e **nunca o limpa**.

## CH-09 — campo vazio em "Portas e Redis" remove a chave sem dizer qual — **Baixo**

`_gravar_portas` (`app.py:436-459`) transforma campo vazio em `None`, que `atualizar_json` usa para **remover** a chave. O doc declara esse comportamento, mas a mensagem de estado diz só "Portas, Redis e developer_mode gravados" (`app.py:461`): quem esvaziou `redis_cache` sem querer não é avisado de que a chave foi apagada.

## Trilha da senha (tarefa 2.2)

| Ponto | Resultado |
|---|---|
| `Banco.__repr__` | senha fora (`field(repr=False)`, `config.py:269`) |
| `~/.cherry.json` | só `distro`, `caminho_linux`, `raiz_local`, `geometria` (`app.py:621-627`): **nunca senha** |
| `site_config.json` exibido | `db_password`, `root_password`, `encryption_key` mascaradas (`app.py:519`) |
| `common_site_config.json` | recebe `root_password` em texto puro **se o usuário mandar gravar** (`config.py:304-305`); é o formato do Frappe e está declarado no doc |
| Argumento de processo, clipboard | ver CH-01 e CH-04 |
| Mensagens de erro | a mensagem da sonda traz o texto da exceção do driver; `psycopg2` e `pymysql` não ecoam a senha. Não verifiquei driver a driver |
