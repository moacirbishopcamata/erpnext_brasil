## 1. Blocos comuns (pacote puro `erpnext_brasil/sistema/`)

- [ ] 1.1 `execucao`: executor de comando como lista, com prazo, limite de saída, indicador de truncamento e resultado imutável, sem shell — verificar com testes de prazo estourado, saída acima do limite e comando inexistente, usando um processo de teste do próprio Python.
- [ ] 1.2 `redator`: mascara valores de segredo registrados em qualquer texto — verificar com mensagens de erro que contêm a senha, inclusive com a senha repetida e com caracteres especiais.
- [ ] 1.3 `caminhos`: resolve e confina caminhos, recusando `..` e link simbólico para fora — verificar com um link simbólico real em diretório temporário (pulando no Windows sem privilégio, e dizendo isso).
- [ ] 1.4 `limites`: rotação de log com teto e descarte do mais antigo — verificar gravando além do teto e conferindo o tamanho e o conteúdo mais recente.
- [ ] 1.5 Estender `tests/test_arquitetura.py` para o pacote `sistema` (sem `frappe`, sem tkinter) — verificar acrescentando um import proibido e vendo o teste falhar.

## 2. Diário de operação e tratamento de exceção

- [ ] 2.1 Diário de operação sobre a porta de persistência: intenção e último passo concluído, estados concluída, falhou e interrompida — verificar matando o processo de teste no meio e relendo o diário em outro processo.
- [ ] 2.2 Desfazer só o que foi feito: o executor de planos recebe passos com seu desfazer e, na falha, desfaz os executados em ordem inversa — verificar com falha injetada em cada passo de um plano de cinco.
- [ ] 2.3 Tratamento único de exceção na interface (`report_callback_exception` e decorador) — verificar com um callback que levanta e a janela continuando a responder.

## 3. Trava de padrões proibidos

- [ ] 3.1 `tests/test_seguranca_das_ferramentas.py`: varredura por `ast` de `shell=True`, `os.system`, `eval`, `exec`, `pickle`, `except:` sem tipo, `subprocess` fora do executor e `open(..., "w")` fora da escrita atômica, com lista de exceções justificadas — verificar introduzindo cada padrão num arquivo temporário e vendo o teste falhar.
- [ ] 3.2 O teste cobra que cada exceção da lista ainda seja necessária — verificar removendo o motivo de uma exceção e vendo o teste falhar.

## 4. Entrada aleatória e malformada

- [ ] 4.1 Utilitário de teste de entrada aleatória com semente fixa (truncada, vazia, bytes inválidos, mil aleatórias) — verificar com um leitor de exemplo que falha de propósito.
- [ ] 4.2 Aplicar a cada leitor de texto externo das três ferramentas, à medida que existirem (`/proc`, saída do `bench`, JSON de terceiros, registro do Soda, perfis do Cherry) — verificar com o teste de cada leitor exigindo "indisponível com motivo" e nenhuma exceção.

## 5. Permissões e recursos

- [ ] 5.1 Permissão restrita ao dono nos arquivos de estado (persistência, registro, trava), com `chmod 0600` do SQLite — verificar em WSL lendo o modo dos arquivos criados, e dizendo que no Windows vale a ACL.
- [ ] 5.2 Aviso quando um arquivo de estado é legível por outros — verificar com um arquivo `0644` criado de propósito.
- [ ] 5.3 Teto de saída capturada e de log nas três ferramentas — verificar com comando de saída enorme e log além do teto.

## 6. Aplicação nas três ferramentas

- [ ] 6.1 Cherry: executor, redator, confinamento de caminhos e tratamento único de exceção; revisar `config.py` e `app.py` contra cada requisito — verificar com os testes novos e a lista de requisitos atendidos em `docs/cherry.md`.
- [ ] 6.2 Soda: o mesmo, mais diário de operação em criação, remoção e troca de formato — verificar com interrupção simulada em cada operação.
- [ ] 6.3 Chantilly: o mesmo, mais leitor de `/proc` à prova de entrada malformada e parada do ERP que falha fechada — verificar com os trechos malformados e com um processo não identificado que não recebe sinal.

## 7. Documentação e gate

- [ ] 7.1 Seção "Resiliência, robustez e segurança" em `docs/ferramentas-de-operacao.md` e em cada documento de ferramenta, com a tabela requisito → mecanismo → teste — verificar relendo contra o código.
- [ ] 7.2 Gate de resiliência e segurança, repetido ao fim de cada mudança das três ferramentas: desfazer e retomar, idempotência, prazos, tratamento de exceção, validação de entrada, ausência de vazamento de segredo, varredura de padrões proibidos, confinamento de caminhos, permissões e limites — verificar com a saída dos comandos e a tabela de requisitos.
