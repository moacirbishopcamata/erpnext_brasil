## 1. A porta de plataforma

- [ ] 1.1 Pacote puro `erpnext_brasil/sistema/plataforma.py` com a porta `Plataforma` (executar, ler, escrever, converter caminho, listar processos, pedir término) e o indicador `disponivel` com motivo — verificar com um adaptador falso e testes de contrato da porta.
- [ ] 1.2 Tipos distintos para caminho do computador (`Path`) e caminho do bench (`PurePosixPath`), com a conversão única `caminho_do_computador` — verificar com testes de distros de nomes diferentes, caminhos com espaço e acento, e caminho relativo recusado.
- [ ] 1.3 Adaptador `WindowsComWsl` (executa por `wsl.exe -d <distro> --`, caminhos UNC) a partir do que o Cherry já faz — verificar com executor injetado e com `wsl.exe` ausente produzindo a mensagem orientadora.
- [ ] 1.4 Adaptador `LinuxNativo` (executa direto, caminhos nativos, `os.kill`) — verificar com um processo de teste real em Linux/WSL e com executor injetado nos demais sistemas.
- [ ] 1.5 Teste de que a regra pura não consulta `sys.platform` nem `os.name` — verificar com varredura por `ast` e uma violação injetada.

## 2. Métricas do computador Windows

- [ ] 2.1 Adaptador de métricas do Windows por `ctypes` (CPU, memória, disco) isolado, com indisponibilidade em vez de valor falso em caso de falha — verificar no Windows contra o Gerenciador de Tarefas (diferença registrada) e com falha simulada de cada chamada.
- [ ] 2.2 Apresentar as duas fontes separadas na visão geral do Chantilly — verificar com um teste de interface com as duas fontes presentes e com só uma.

## 3. Modo de terminal e ausência de display

- [ ] 3.1 Detecção de ausência de display e de `tkinter` antes de importar a interface, com mensagem e lista de comandos equivalentes — verificar simulando `DISPLAY` vazio e `ImportError` de `tkinter`.
- [ ] 3.2 Todos os comandos de terminal de cada ferramenta funcionam sem importar `tkinter` — verificar com um teste que importa o ponto de entrada de terminal com `tkinter` bloqueado.

## 4. CI e documentação

- [ ] 4.1 Matriz `ubuntu-latest` e `windows-latest` nos jobs da suíte pura e das ferramentas, com `xvfb` só no Linux — verificar com os dois conjuntos de jobs verdes no PR e o log mostrando a interface rodada nos dois.
- [ ] 4.2 Testes que dependem de recurso de um só sistema com `skipUnless` e motivo escrito, e equivalente no outro — verificar listando os testes pulados em cada sistema e o motivo.
- [ ] 4.3 Tabela "o que funciona onde" (ERP e as três ferramentas, em Windows com WSL2, Windows sem WSL e Linux) em `docs/ferramentas-de-operacao.md` e nos documentos de cada ferramenta — verificar relendo contra o código e o CI.
- [ ] 4.4 Gate de padrões e de resiliência e segurança, nos dois sistemas — verificar com a saída dos comandos nos dois jobs do CI.
