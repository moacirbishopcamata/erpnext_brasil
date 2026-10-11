## 1. Segredo fora do argumento (CH-01)

- [x] 1.1 Escrever o teste que injeta um executor, captura o `argv` e a variável de ambiente e falha se a senha estiver em `argv` — verificar vendo-o falhar antes da correção e passar depois.
- [x] 1.2 Passar a senha à sonda do WSL e à local por variável de ambiente do filho (no WSL, via `WSLENV`) ou `stdin`, e ajustar `_SONDA_PYTHON` para lê-la de lá — verificar com o teste da 1.1 e, se houver `wsl`, medindo a linha de comando do processo como na revisão.

## 2. Escrita atômica (CH-02)

- [x] 2.1 Escrever o teste que força falha de escrita no meio e confere que o arquivo original continua byte a byte igual e que não sobra temporário — verificar vendo-o falhar antes e passar depois.
- [x] 2.2 Reescrever `_gravar_texto` com arquivo temporário na mesma pasta e `os.replace`, mantendo `newline="\n"` — verificar com o teste da 2.1 e com os testes de CRLF e de `\n` final já existentes.

## 3. Comando seguro (CH-03)

- [x] 3.1 Escrever o teste com host, usuário, site e app hostis (`;`, `$(...)`, crase) e esperar recusa ou aspas — verificar vendo-o falhar antes e passar depois.
- [x] 3.2 Aplicar a validação ou as aspas em `comando_new_site` e validar nomes de app também na leitura de `apps.txt` — verificar com o teste da 3.1 e `test_config` verde com 100% de cobertura do núcleo.

## 4. Senha de administrador e clipboard (CH-04)

- [x] 4.1 Remover o valor `admin` pré-preenchido e definir o comportamento do comando sem senha de administrador — verificar com teste em `test_app.py` do campo vazio e do comando gerado.
- [x] 4.2 Limpar o clipboard após o prazo definido, só se ainda contiver o comando, e avisar na barra de estado — verificar com teste que avança o `after` e confere o clipboard.

## 5. Versão e documentação

- [x] 5.1 Subir `__version__` para `0.2.0` e atualizar `docs/cherry.md` (seção de segurança, testes, versionamento) e a revisão — verificar pelo teste que confere a versão no título e relendo os dois documentos.
- [x] 5.2 Rodar `python -m unittest scripts.cherry.test_config scripts.cherry.test_app`, `coverage` como no CI (piso de 95% no núcleo) e `ruff` em `scripts/` — verificar com a saída verde.
