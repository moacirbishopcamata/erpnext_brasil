# Revisão do Cherry — núcleo, interface, testes, CI e UX

Cobre as tarefas 3.1 a 3.3 e 4.1 a 4.3 do change `revisao-do-cherry`.

## Cobertura

- **Lido:** `config.py` quase inteiro (JSON, `apps.txt`, `Bench`, `Banco`, `comando_new_site`, `testar_conexao`); em `app.py`, os métodos de teste de conexão, gravação do banco, cópia do `new-site`, portas, preferências e a inicialização; `test_app.py` (cabeçalho e preparação); o job `cherry` do CI.
- **Executado:** introspecção da janela real (oculta) e as medições de [`seguranca-e-escrita.md`](seguranca-e-escrita.md).
- **Não lido:** o corpo das abas Sites e `apps.txt` de `app.py`; os 41 testes de `test_config.py`.
- **Fonte de UX relida na web em 2026-10-11:** [UX checklist for desktop applications (Microsoft)](https://learn.microsoft.com/en-us/windows/win32/uxguide/top-violations). A página continua no ar e traz o aviso de que foi escrita para o Windows 7 e não foi atualizada, mas "boa parte da orientação ainda vale". As demais fontes do `docs/cherry.md` (NN/g e outras) **não** foram relidas.

## Núcleo (`config.py`)

Cobertura de linhas 100%, como o doc promete. Os contratos (`CherryInvalido` no `__post_init__` de `Banco`, em `gravar_apps_txt`, em `caminho_wsl`), a imutabilidade (`dataclass(frozen=True)`) e a injeção do executor estão como o doc descreve. Os achados do núcleo são de segurança e de escrita: CH-01, CH-02 e CH-03.

## Achados

### CH-05 — o teste de conexão trava a janela por até ~63 s — **Médio**

`_testar_conexao` (`app.py:321-337`) chama `cfg.testar_conexao` direto, na thread da interface; só há `update_idletasks()` antes. Cada sonda tem `timeout=30` (`config.py:421`) e o fluxo pode tentar a do WSL, a local e o TCP (3 s): até **63 s** com a janela sem responder ("Não está respondendo" no Windows). A Microsoft pede feedback e progresso para operações longas. **Inferido da leitura, não cronometrado.** Correção: rodar a sonda numa thread e atualizar a tela por `after`, com botão que cancele.

### CH-06 — a interface não tem teste no CI, e 17% de `app.py` não tem teste nenhum — **Médio**

O job `cherry` do CI roda `test_config` e `test_app` com `--include="scripts/cherry/config.py"`: o piso de 95% é só do núcleo, e `test_app.py` **pula** sem display (`TEM_DISPLAY`). Resultado: `app.py` tem 0% no CI e 83% na máquina com display. Sem cobertura local: **todo o `_testar_conexao`** (322-337), o ramo de erro de gravar o banco (368-370) e o de copiar o `new-site` (382-384). A CH-05 mora exatamente nesse trecho sem teste. Opções para o CI: passo com `xvfb-run` (custo: instalar `xvfb` e `python3-tk` no runner) ou manter o piso só no núcleo e declarar que a interface é verificada à mão. Esta revisão não aplicou nada.

### CH-07 — mensagens com "inválido" contrariam a regra do próprio Cherry — **Baixo**

`app.py:15` e `docs/cherry.md` dizem "nunca 'erro', 'inválido', 'falhou'". Mas `CherryInvalido` leva à tela mensagens como "nome de app inválido" (`config.py:157`) e "nome de site inválido" (`config.py:318`), exibidas por `_problema` como "Não foi possível: nome de site inválido". A página da Microsoft recomenda "incorreto" ou "não válido". O teste `test_porta_nao_numerica...` cobre a porta, não estas.

### CH-08 — a geometria salva é restaurada sem checar se cabe na tela — **Baixo**

`app.py:613-614` aplica `prefs["geometria"]` como veio. Trocar de monitor ou resolução pode deixar a janela fora da área visível. Esta máquina é 1366×768 (escala 1,33) e `minsize` é 760×560, dentro do mínimo de 800×600 que a Microsoft pede; **não testei** tela menor nem escala de 150%.

## Doc contra o código (tarefa 3.3)

| Afirmação de `docs/cherry.md` | Situação |
|---|---|
| 55 testes; 100% / 83% / 88% | **Confere** (medido) |
| Abas Bench, Banco de dados, Portas e Redis, Sites, apps.txt | **Confere** (`abas.add`, `app.py:116-559`) |
| Teclas de acesso e Enter | **Confere**: `enable_traversal` (`app.py:79`), `underline=0` e `Alt-u/t/g` ligados |
| Foco inicial no primeiro campo | **Confere** (`app.py:57`) |
| "Padrões seguros" | **Diverge** em parte: senha de admin `admin` pré-preenchida (CH-04) |
| Vocabulário que não culpa, "nunca inválido" | **Diverge** em parte (CH-07) |
| Campo vazio **remove** a chave | **Confere**, mas sem avisar qual (CH-09) |
| Senha "nunca" em `~/.cherry.json` | **Confere** |
| Janela nítida em HiDPI (`SetProcessDpiAwareness`) | Chamada existe (`app.py:642`); **não** verificada visualmente |

## Qualidade dos testes (tarefa 4.1)

Os testes de gravação já miram na costura: `gravar_json` é conferido por `json.loads` do arquivo cru e `gravar_apps_txt` pelos bytes (o doc conta que isso pegou o bug de CRLF antes de tocar num bench). O que falta é o caso de **falha no meio da escrita** (CH-02) e o de **segredo em argumento** (CH-01); ambos cabem no executor injetável e num diretório temporário, sem `wsl`.
