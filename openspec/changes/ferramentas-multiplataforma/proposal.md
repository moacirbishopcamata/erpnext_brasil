## Why

Por decisão do dono do projeto (2026-10-11), **o ERP e os seus utilitários (Cherry, Soda e Chantilly) devem funcionar tanto em Windows quanto em Linux**. Hoje o desenho assume um único cenário: a interface no Windows operando um bench que vive no WSL2. Isso cobre quem usa Windows, mas deixa de fora quem tem uma máquina Linux (sem WSL, sem `wsl.exe`, com caminhos `/home/...` nativos e com o bench no mesmo sistema) e não diz o que cada ferramenta faz quando o computador é Windows sem WSL.

Há um limite que precisa ficar explícito, porque muda o que "funcionar em Windows" pode significar: **o Frappe/ERPNext não roda nativamente no Windows** (o próprio projeto registra que o `bench` não funciona nativo no Windows e que os testes de bench só rodam em WSL2/Linux). Para o **ERP**, "Windows" quer dizer **Windows com WSL2**; para os **utilitários**, quer dizer **rodar de verdade no Windows**, e também em Linux, operando o bench local.

## What Changes

- Uma **matriz de plataformas** explícita e testada: Windows 10/11 com o bench no WSL2, e Linux (com o bench local, no mesmo sistema). O Cherry, o Soda e o Chantilly passam a funcionar nos dois, com o **mesmo código**.
- Uma porta de **plataforma** nas três ferramentas, com dois adaptadores: *Windows com WSL* (executa pelo `wsl.exe`, lê o bench pelo caminho `\\wsl.localhost\...`) e *Linux nativo* (executa direto, lê `/home/...`). O núcleo de regra não sabe em que sistema roda.
- Separação rigorosa entre **caminho do computador onde a janela roda** e **caminho do bench** (que é sempre Linux): o segundo usa `PurePosixPath`; o primeiro usa `Path`. Nunca se mistura.
- **Chantilly:** a leitura de `/proc` vale onde o bench roda (Linux ou WSL2). Num Windows, o Chantilly mede também o **próprio computador Windows** (CPU, memória, disco) pela biblioteca padrão (`ctypes`), identificado como tal, separado do que se mede dentro do WSL2.
- **Soda e Cherry:** o controle de processos e de arquivos funciona nos dois sistemas; o que só existe em Linux (sinais, `/proc`, permissão `0600`) tem equivalente declarado ou fica claramente indisponível no Windows, nunca falha em silêncio.
- **Linux sem display (servidor):** as três ferramentas têm modo de **terminal completo** (os comandos já previstos), com mensagem clara quando não há ambiente gráfico; a interface exige `python3-tk` e um display.
- **CI em matriz** (`ubuntu-latest` e `windows-latest`) para a suíte pura e para os testes das ferramentas, de modo que um defeito que só aparece num dos sistemas seja pego antes de chegar ao usuário. (A concorrência da persistência já achou três defeitos que só existiam no Windows.)
- **Documentação** com a tabela "o que funciona onde", sem prometer o que não existe.

Fora desta mudança: fazer o Frappe/ERPNext rodar nativo no Windows (não é suportado pelo upstream), macOS, e contêineres como alvo de primeira classe.

## Capabilities

### New Capabilities

- `ferramentas/multiplataforma`: o contrato de execução do Cherry, do Soda e do Chantilly em Windows (com o bench no WSL2) e em Linux (com o bench local).

### Modified Capabilities

Nenhuma.

## Impact

- Pacote puro `erpnext_brasil/sistema/` ganha a porta `Plataforma` e os dois adaptadores (em `scripts/` para o que toca o sistema), e as três ferramentas passam a usá-la.
- `.github/workflows/ci.yml`: matriz de sistemas operacionais.
- `docs/ferramentas-de-operacao.md`, `docs/cherry.md`, `docs/soda.md`, `docs/chantilly.md`: tabela de compatibilidade.
- O pacote `erpnext_brasil/persistencia` já é multiplataforma e tem correções específicas do Windows com teste.
