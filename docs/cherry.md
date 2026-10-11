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

## Versão 0.2.0 — segredo e escrita (2026-10-11)

Fecha os quatro achados de segurança da revisão (CH-01 a CH-04):

- **A senha de root não vai mais em argumento de processo.** A sonda de conexão a recebe pela variável de ambiente `CHERRY_SENHA_ROOT`; para o `wsl.exe` levá-la ao Linux, o Cherry acrescenta a variável ao `WSLENV` do processo filho (sem perder o que já houver). Medido: a senha chega ao venv do bench, não aparece na linha de comando do `wsl.exe` no Windows e tem zero ocorrências no `ps` do Linux.
- **Toda gravação é atômica.** O texto vai para um arquivo temporário na mesma pasta e só então troca o original com `os.replace`; se qualquer passo falhar, o original fica byte a byte como estava e o temporário é apagado. Vale para `common_site_config.json`, `site_config.json`, `apps.txt` e `~/.cherry.json`.
- **O comando copiado só aceita nomes seguros.** Servidor, usuário, site e apps precisam ter só letras, dígitos e `. _ : @ -`; qualquer outra coisa é recusada (as senhas continuam entre aspas simples). `gravar_apps_txt` usa o mesmo critério.
- **A senha do Administrator não vem mais preenchida.** Vazia, o comando omite `--admin-password` e o `bench` a pergunta no terminal (`frappe/utils/install.py`, `get_admin_password`), então ela não fica no comando nem na área de transferência.
- **A área de transferência é limpa em 60 s**, mas só se ainda tiver o comando copiado; se o usuário copiou outra coisa, não se apaga.

Testes: 69 (eram 55); núcleo `config.py` 100%, interface 83%, total 89%. O CI continua rodando só o núcleo (CH-06 segue aberto).

## Versão 0.2.1 — teste de conexão sem travar, e a interface no CI (2026-10-11)

Fecha CH-05 e CH-06 da revisão:

- **O teste de conexão roda numa thread de trabalho.** Antes, `_testar_conexao` esperava a sonda na thread da interface, com `timeout=30` por tentativa: até ~63 s de janela sem responder. Agora o trabalhador só calcula e devolve o resultado por uma fila; quem mexe na tela é sempre a thread da interface, que consulta a fila a cada 100 ms (o tkinter não é seguro entre threads). Medido com uma sonda simulada de 3 s: o clique volta em 0,03 s e a janela atende eventos em 0,02 s.
- **O botão vira "Parar de esperar"** enquanto o teste roda; um segundo clique (ou Alt+T) descarta o resultado quando chegar. Não mata o processo da sonda: ele termina sozinho pelo `timeout`. Uma exceção inesperada da sonda vira mensagem na tela, não thread morta.
- **Defeito achado ao escrever o teste:** `_gravar_banco` lia o `common_site_config.json` fora do `try`; com o arquivo ilegível, a falha saía como traceback no console e nenhuma mensagem na tela. Agora vira "não pôde ser lido" e nada é gravado.
- **A interface entra no CI.** O job `cherry` instala `xvfb` e `python3-tk`, roda os testes com `xvfb-run` e aplica **dois pisos**: 95% no núcleo (`config.py`) e **87% na interface** (`app.py`, medida em 89%; o piso fica dois pontos abaixo para não quebrar por uma linha). Se o display falhar e `test_app.py` pular, `app.py` cai a 0% e o passo falha, em vez de passar em silêncio.

Testes: 77 (eram 69); núcleo 100%, interface 89%, total 92%.

## Versão 0.4.0 — perfis de banco de dados (2026-10-11)

Por decisão do dono do projeto, **a escolha do banco é do Cherry** (mudança `cherry-perfis-de-banco`). A aba **Banco de dados** ganhou uma lista de **perfis**: configurações nomeadas de servidor (MariaDB ou PostgreSQL; host, porta, usuário administrador).

- **Regra pura em `erpnext_brasil/bancos/`** (sem `frappe` nem `tkinter`, cobertura 100%): `PerfilDeBanco` imutável **sem campo de senha**; `PerfisDeBanco` (o único escritor) com nome único sem diferença de maiúsculas, **exatamente um padrão**, remoção do padrão recusada enquanto houver outros perfis, e perfil em uso por instância do Soda **sem remover nem trocar tipo, servidor ou porta** (a recusa lista as instâncias por descritivo e UUID abreviado); `LeitorDePerfis` somente leitura para o Soda e o Chantilly (sem método de escrita, sem trava, tolera campo novo e esquema mais novo). Os perfis moram na porta de persistência, nos três formatos, com a mesma bateria de testes.
- **Costura em `scripts/cherry/perfis.py`:** os perfis ficam em `sites/cherry/perfis-de-banco.json`; o **padrão** vai ao `common_site_config.json` (`db_type`, `db_host`, `db_port`, `root_login`), de modo que o `bench new-site` puro continua funcionando — **nunca `root_password`**, que só é gravada quando o usuário a digita e manda gravar, como sempre foi.
- **Um bench existente vira o perfil `padrao`** na primeira abertura, sem alterar o `common_site_config.json` (conferido byte a byte).
- **Teste de conexão por perfil:** a senha é informada na hora, vai à sonda pelo ambiente (nunca por argumento) e o perfil guarda **só data, nível e resultado**. Os testes varrem todos os arquivos do bench em busca da senha e não a encontram.
- **A interface:** lista de perfis com o padrão marcado (✓) e o último teste; formulário com as restrições do nome à vista; Novo, Salvar, Tornar padrão e Remover; estado vazio com instrução; "✓ perfil salvo", "✓ padrão" e "✓ removido" na barra de estado. **Selecionar um perfil preenche o formulário e limpa a senha** (a senha não é do perfil). "Gravar no bench" agora salva o perfil, o torna padrão e grava a senha só se digitada.
- **Aviso de alcance:** trocar o padrão com **instâncias do Soda no ar ou subindo** mostra quais são e avisa que elas continuam no banco em que nasceram; só sites novos usam o novo padrão.
- **`bench new-site` do perfil escolhido:** o comando gerado usa o tipo, o host, a porta e o usuário do perfil selecionado.
- **Achado ao escrever o teste:** digitar o nome de um perfil existente com outra caixa (`PADRAO` para `padrao`) quebrava a seleção da lista; agora edita o perfil existente em vez de duplicar.

Ainda não feito nesta versão: a opção de **SQLite** para os perfis nas preferências (mudança `persistencia-sqlite-opcional`; os adaptadores existem, falta ligá-los ao Cherry), o gate de resiliência e segurança (4.4 da mudança) e a captura de tela da aba.

Testes: 124 (eram 77); `config.py` e `perfis.py` a 100%, interface 91% (piso do CI subiu de 87% para 89%).

## Revisão de 2026-10-11

A primeira revisão do Cherry (`0.1.0`) está em [`revisao-do-cherry.md`](revisao-do-cherry.md). Os números deste documento (55 testes; núcleo 100%, interface 83%, total 88%) **conferem** com o código. Achados que mudam o que está dito aqui: a seção "Padrões seguros" não vale para a senha de administrador, que vem pré-preenchida com `admin` (CH-04); a regra de vocabulário "nunca inválido" tem duas exceções em `config.py` (CH-07); e a senha de root da sonda de conexão trafega como argumento de processo (CH-01). A correção está proposta em `openspec/changes/endurecer-segredo-e-escrita-do-cherry`.

## Evolução planejada (propostas de 2026-10-11)

O Cherry passa a conviver com duas ferramentas irmãs, descritas em [`ferramentas-de-operacao.md`](ferramentas-de-operacao.md):

- **Soda** ([`soda.md`](soda.md)) cria e opera várias instâncias do ERPNext Brasil em portas diferentes, cada uma com **UUID único** e **descritivo único**.
- **Chantilly** ([`chantilly.md`](chantilly.md)) monitora o consumo de RAM, CPU e armazenamento.

Mudanças que tocam o Cherry:

- **`cherry-instancias-por-uuid`:** o Cherry identifica cada instância pelo **UUID com o descritivo único**, lidos do contrato de identidade do Soda (somente leitura). A aba Sites passa a mostrar descritivo, UUID abreviado, porta e estado; as chaves `soda_instance_id` e `soda_descritivo` nunca são alteradas pelo Cherry; as abas de configuração **comum** (banco, portas, Redis, `default_site`, `apps.txt`) avisam que a alteração vale para todas as instâncias; o formulário de portas recusa portas alocadas a instâncias; o `bench new-site` gerado avisa que um site criado fora do Soda não terá identidade. Sem o Soda, o Cherry funciona como hoje. Versão prevista: `0.3.0`.
- **`cherry-perfis-de-banco`** *(implementado na `0.4.0`, ver acima)*: a escolha do banco é do Cherry. Ele passa a manter **perfis de banco** nomeados (MariaDB e/ou PostgreSQL; host, porta, usuário; **nunca senha**), com exatamente um padrão, gravado no `common_site_config.json` para o `bench new-site` puro continuar funcionando. O teste de conexão vale por perfil; os perfis são publicados somente para leitura ao Soda e ao Chantilly; um perfil em uso por instância não é removido. Um bench existente vira o perfil padrão sem perder nada. Versão prevista: `0.4.0`.
- **Docker:** a configuração em `docker/` ([`docker.md`](docker.md)) não substitui o Cherry; ela segue a escolha de banco que o Cherry mantém (o Compose combina o override de MariaDB ou de PostgreSQL). Editar o `docker-compose.yml` continua fora do que o Cherry faz hoje.
- **`persistencia-sqlite-opcional`:** as preferências (`~/.cherry.json`) ganham SQLite como opção de persistência, ao lado do JSON, com migração sem perda e a mesma suíte de contrato nos dois formatos. Senha continua sem ser persistida em nenhum formato.

Os pisos de cobertura continuam valendo (95% no núcleo, 89% na interface desde a `0.4.0`).
