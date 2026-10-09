# Cherry: as configurações que se fazem à mão, numa tela

Pedido do usuário em 2026-09-17, em três mensagens: *"crie um pequeno sistema em Python com
UI desktop para configurar banco de dados (MariaDB ou PostgreSQL), chame-o de Cherry"*;
*"quero colocar nesse pequeno sistema as configurações que fazemos manualmente em
arquivos"*; *"aos poucos iremos refiná-lo para automatizar a configuração do sistema ERPNext
BR"*. Este documento registra a primeira versão (`0.1.0`), as decisões, as fontes de UX e o
que ficou de fora.

Código em `scripts/cherry/`, **licença MIT** própria (`scripts/cherry/LICENSE`), fora do
pacote `erpnext_brasil/` — é ferramenta de quem desenvolve, nunca instalada num site.

## Por que existe

Cada arquivo que o Cherry edita já custou uma rodada de diagnóstico neste projeto:

| Arquivo | O que já mordeu |
|---|---|
| `sites/common_site_config.json` | `default_site` ausente → 404 em toda rota (`docs/como-rodar.md`); Redis compartilhado entre benches → dado errado; `db_type`/`root_login` é de onde o `bench new-site` lê o banco quando não recebe `--db-*` (`docs/postgresql.md`) |
| `sites/<site>/site_config.json` | `allow_tests` esquecido → `bench run-tests` recusa |
| `sites/apps.txt` | **sem `\n` final o último app some** — aconteceu duas vezes (`docs/banco-do-bench-v16.md`, 4b; de novo em 2026-09-17) |

Editar à mão não valida nada. O Cherry valida antes de gravar e mostra o que gravou.

## Como rodar

```sh
python scripts/cherry/cherry.py          # de qualquer diretório
python -m scripts.cherry                 # na raiz do repositório
```

Só a biblioteca padrão (`tkinter`, `json`, `subprocess`). Roda no Windows e edita o bench do
WSL por `\\wsl.localhost\<distro>\...` — o mesmo caminho que o Explorer usa. Também aceita um
bench local (pasta que contém `sites/`).

## As cinco abas

| Aba | O que faz | Onde grava |
|---|---|---|
| **Bench** | escolhe o bench (WSL ou pasta local), mostra sites, apps e o banco padrão | `~/.cherry.json` (só caminho e distro — **nunca senha**) |
| **Banco de dados** | MariaDB ou PostgreSQL, host, porta, usuário e senha de administrador; **testa a conexão**; gera o `bench new-site` completo e copia | `common_site_config.json`: `db_type`, `db_host`, `db_port`, `root_login`, `root_password` |
| **Portas e Redis** | `webserver_port`, `socketio_port`, `redis_cache/queue/socketio`, `file_watcher_port`, `developer_mode` | `common_site_config.json`; campo vazio **remove** a chave |
| **Sites** | mostra o `site_config.json` (senhas mascaradas), liga `allow_tests`, define `default_site` | `site_config.json` e `common_site_config.json` (`default_site` + `serve_default_site`) |
| **apps.txt** | edita a lista; `frappe` sempre primeiro; sem vazios nem repetidos; **sempre com `\n` final** | `sites/apps.txt` |

### O teste de conexão tem três níveis, e diz qual rodou

1. **venv do bench no WSL** (`wsl -d <distro> -- <bench>/env/bin/python -c ...`) — é o
   processo que vai falar com o banco de verdade, com o driver que o Frappe usa. Um driver no
   Windows passaria e o bench falharia (rede espelhada, firewall) — ou o inverso.
2. **driver local**, se `psycopg2`/`MySQLdb`/`pymysql` existirem no Python do Windows.
3. **TCP** — só prova que algo escuta na porta, e o resultado diz isso com todas as letras.

## Arquitetura — os mesmos padrões do app

`config.py` é o núcleo: sem tkinter, sem Frappe, sem rede, testável com `unittest` puro.
`app.py` só coleta o que foi digitado e chama o núcleo. É a mesma fronteira
`fiscal/` × `integracao/` do app, aplicada a uma ferramenta.

- **Design by Contract**: pré-condições em `CherryInvalido` (`Banco` recusa tipo, host vazio
  e porta fora da faixa no `__post_init__`; `gravar_apps_txt` recusa lista vazia e nome com
  espaço ou barra; `caminho_wsl` recusa caminho relativo). Pós-condição gravada como teste:
  o arquivo relido termina em `\n`.
- **Imutabilidade**: `Bench`, `Banco`, `ResultadoConexao` são `dataclass(frozen=True)`;
  `Banco` esconde a senha do `repr`.
- **Inversão de dependência**: `testar_conexao(..., executar=subprocess.run)` — o teste injeta
  um executor e prova os três níveis sem `wsl` nem rede.
- **Teste na costura, não no retorno**: `gravar_json` é conferido por `json.loads` do arquivo
  cru; `gravar_apps_txt` pelos **bytes** relidos. Foi isso que pegou um bug real antes de
  qualquer bench ser tocado: `Path.write_text` no Windows grava `\r\n`, e um `apps.txt` com
  CRLF faria o Frappe enxergar um app chamado `erpnext\r`. A função de retorno estava certa;
  o arquivo, não. Corrigido com `newline="\n"` em toda escrita.
- **Formato do Frappe**: JSON com `indent=1`, chaves ordenadas e `\n` final — o mesmo de
  `frappe.installer.update_site_config`, para o próximo `bench set-config` não reescrever o
  arquivo só por estilo.

## UX — o que foi pesquisado e o que virou código

Fontes: [UX checklist for desktop applications (Microsoft)](https://learn.microsoft.com/en-us/windows/win32/uxguide/top-violations),
[Dialog boxes — design basics (Microsoft)](https://learn.microsoft.com/en-us/windows/win32/uxguide/win-dialog-box),
[Guidelines for keyboard user interface design (Microsoft)](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/dnacc/guidelines-for-keyboard-user-interface-design),
[as 10 heurísticas de Nielsen](https://shiftasia.com/community/applying-jakob-nielsens-10-usability-heuristics-for-better-ux-design/),
[Confirmation dialogs can prevent user errors (NN/g)](https://www.nngroup.com/articles/confirmation-dialog/),
[Form design best practices](https://uxperience.substack.com/p/form-design-best-practices) — consultadas em 2026-09-17.

| Diretriz | No Cherry |
|---|---|
| Uma **instrução principal** por página, imperativa, sem ponto final; abas com nome específico (nunca "Geral"/"Avançado") | "Escolha o bench…", "Informe o servidor…"; abas Bench / Banco de dados / Portas e Redis / Sites / apps.txt |
| **Modal só para o que exige resposta**; feedback de rotina sem interromper | sucesso vai para a barra de estado e uma marca "✓ gravado" que some em 2,5 s; caixa de diálogo só para problema |
| Vocabulário que **não culpa**: nunca "erro", "inválido", "falhou" | "Não foi possível: …", "Não conectou", "a porta precisa ser um número" — e há teste (`test_porta_nao_numerica_e_problema_sem_gravar`) que reprova "Erro" na barra |
| **Confirmação só com consequência real**, como pergunta sim/não | trocar `db_type` num bench que já tem sites pergunta e explica o efeito; o resto grava direto |
| **Padrões seguros** | senha oculta com "Mostrar senha"; `developer_mode` desligado; MariaDB (o banco de referência) pré-selecionado |
| Sugestão nunca sobrescreve dado confirmado | trocar o servidor sugere porta/usuário padrão **só** se os atuais forem os padrão do outro — `3307` digitado permanece (testado) |
| **Teclado**: foco inicial no primeiro campo, Enter aciona a ação da página, teclas de acesso | foco em "Caminho Linux do bench"; Enter = "Usar este bench"/"Testar conexão"/"Gravar"; Alt+U/T/G; abas navegáveis por Ctrl+Tab |
| Controles restritos onde possível | servidor por botão de opção; sites por lista; `allow_tests`/`developer_mode` por caixa de seleção |
| Divulgação progressiva | o bloco do `bench new-site` só aparece por "Mostrar o comando…" |
| Janela nítida em HiDPI, aparência do sistema, tamanho lembrado | `SetProcessDpiAwareness`, tema `vista` quando existe, geometria em `~/.cherry.json` |
| Senha mascarada em toda exibição | `site_config.json` mostra `***` em `db_password`, `root_password`, `encryption_key` (testado) |

## Testes e cobertura

```sh
python -m unittest scripts.cherry.test_config scripts.cherry.test_app -v
python -m coverage run --include="scripts/cherry/*.py" --omit="scripts/cherry/test_*.py,scripts/cherry/__main__.py,scripts/cherry/cherry.py" \
    -m unittest scripts.cherry.test_config scripts.cherry.test_app && python -m coverage report -m
```

Na primeira versão: **55 testes**, núcleo (`config.py`) **100 %**, interface (`app.py`) 83 %,
total 88 %. O teste da interface (`test_app.py`) cria a janela oculta e grava de verdade num
bench temporário; precisa de display — no Windows roda, na CI (Ubuntu sem X) pula. O da CI
roda só o núcleo, com piso de cobertura (`.github/workflows/ci.yml`, job `cherry`).

## Versionamento

`scripts/cherry/__init__.py::__version__`, semântico, exibido no título da janela e conferido
por teste. Independente do `erpnext_brasil.__version__`: o Cherry evolui em ritmo próprio.
Regra: toda mudança visível ao usuário incrementa o `minor`; correção sem mudança de
comportamento, o `patch`.

## O que deliberadamente **não** faz (ainda)

- **Não executa o `bench new-site`** — gera e copia o comando. Rodar `bench` de dentro do Cherry
  exigiria decidir onde o erro aparece; hoje ele aparece no terminal do bench, com traceback
  completo. Candidato natural para a próxima versão, junto com `install-app`/`migrate`.
- **Não sobe Redis nem banco** (`scripts/subir.sh` faz isso no WSL).
- **Não guarda senha** fora do `common_site_config.json`, e só quando o usuário manda gravar.
- **Não edita `docker-compose.yml`** nem `.wslconfig`.

O roteiro combinado com o usuário: refinar aos poucos até o Cherry automatizar a configuração
do ERPNext BR — cada passo com teste na costura e esta página atualizada.
