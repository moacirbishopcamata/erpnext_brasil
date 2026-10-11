## Context

Ver `proposal.md` (Why). O que o repositório estabelece:

- O bench roda **só em WSL2/Linux** (`CLAUDE.md`, `docs/ambiente-dev-bench.md`); o `bench` não funciona nativo no Windows. A suíte pura roda em qualquer máquina e já roda tanto no Windows de desenvolvimento quanto no Ubuntu do CI.
- O Cherry hoje lê o bench por `\\wsl.localhost\<distro>\...` e executa por `wsl -d <distro> -- ...`; bench local (pasta com `sites/`) também é aceito.
- `requires-python = ">=3.10"`: o código das ferramentas usa só recursos de 3.10.
- A persistência nova já teve três defeitos que só apareciam no Windows (`os.replace` contra um leitor, conversão para WAL concorrente, migração repetida); foram achados pela suíte de concorrência rodando no Windows.

## Goals / Non-Goals

**Goals:**
- As três ferramentas rodam em Windows e em Linux com o **mesmo código** e a regra livre de teste de sistema operacional.
- Operar o bench no WSL2 (janela no Windows) e o bench local (janela em Linux).
- Dizer com clareza o que funciona onde.
- CI nos dois sistemas.

**Non-Goals:**
- Rodar o Frappe/ERPNext nativo no Windows (não suportado pelo upstream), macOS, e contêineres de primeira classe.

## Decisions

1. **Porta `Plataforma` com dois adaptadores.** A porta oferece: como executar um comando no ambiente do bench (lista de argumentos), como ler e escrever arquivos do bench, como converter caminho do bench para caminho do computador, como listar processos do bench, e como enviar um pedido de término a um processo. Adaptadores: `WindowsComWsl` (executa por `wsl.exe -d <distro> --`, caminhos UNC, sinais enviados por `wsl kill`) e `LinuxNativo` (executa direto, caminhos nativos, `os.kill`). A escolha é configuração do bench. O núcleo de cada ferramenta recebe a porta, nunca consulta `sys.platform`.
2. **Dois tipos de caminho.** `Path` para o computador onde a janela roda; `PurePosixPath` para o bench. A conversão fica numa função única (`caminho_do_computador(bench, caminho_linux)`), testada com distros de nomes diferentes e caminhos com espaço. O `caminho_wsl` do Cherry vira a implementação dessa função para o adaptador do WSL.
3. **Medição do Windows pela biblioteca padrão.** `ctypes` com `GetSystemTimes` (CPU), `GlobalMemoryStatusEx` (memória) e `shutil.disk_usage` (disco). É estritamente da biblioteca padrão e fica isolada em um adaptador de métricas; as métricas do ambiente do bench continuam vindo de `/proc`, dentro do WSL2 ou do Linux. As duas fontes são identificadas e nunca somadas.
4. **Recursos só de um sistema:** declarados na porta com um indicador `disponivel` e um motivo; o chamador trata a indisponibilidade como estado normal. Nada devolve um valor falso.
5. **Sem display:** o ponto de entrada de cada ferramenta detecta a ausência de display (Linux sem `DISPLAY` ou `WAYLAND_DISPLAY`; ausência de `tkinter`) antes de importar a interface, e imprime a mensagem com os comandos de terminal equivalentes.
6. **CI em matriz.** `ubuntu-latest` e `windows-latest` para: suíte pura, testes do Cherry, do Soda e do Chantilly, `ruff`. No Windows, os testes de interface rodam na sessão do runner (que tem desktop); no Linux, sob `xvfb`. Os testes que dependem de recurso só de um sistema (sinais, `/proc`, `chmod`) usam `skipUnless` com o motivo escrito, e há ao menos um teste equivalente no outro sistema.
7. **Finais de linha, codificação e travas.** UTF-8 explícito em toda leitura e escrita de texto, `\n` sempre, `os.replace` com nova tentativa e trava por arquivo com `O_EXCL` tolerante a `PermissionError` (já feitos na persistência).
8. **Padrões do projeto, resiliência e segurança** valem sem exceção nos dois sistemas.

## Risks / Trade-offs

- **Dois adaptadores para manter:** a suíte de contrato da porta roda contra os dois (com um falso para o sistema que não é o do runner), para impedir divergência.
- **`ctypes` no Windows** é frágil se mal usado: isolado, testado com valores reais e com falha simulada, e indisponível (não falso) se uma chamada falhar.
- **CI mais lento e mais caro** com a matriz: aceito, porque o ganho é pegar defeito de plataforma antes do usuário; os jobs de interface do Windows podem rodar só nas mudanças que tocam `scripts/`.
- **WSL2 por baixo no Windows:** o desempenho de arquivo pelo caminho UNC é lento para operações pesadas; a interface lê o mínimo e em segundo plano.
- **Promessa do ERP no Windows:** a única honesta é "no WSL2". Se a intenção era nativo, a decisão muda de natureza e precisa ser conversada (o upstream não suporta).

## Open Questions

1. **"ERP funcionar em Windows" = WSL2?** Foi o entendido, por ser o único modo suportado. Se a expectativa é Windows nativo sem WSL, é um projeto à parte e de risco alto.
2. Linux de referência para o CI e para a documentação: Ubuntu 22.04 e 24.04? Outras distribuições entram como "melhor esforço"?
3. Nos Windows sem WSL, as ferramentas devem oferecer instalar o WSL2 (apenas orientar o comando) ou só informar?
