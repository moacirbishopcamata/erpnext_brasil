## 1. Fundação: verificar as premissas e montar o núcleo puro

- [ ] 1.1 Verificar na prática, num par de sites descartáveis, as premissas do design: (a) entrar em duas instâncias no mesmo navegador sem derrubar a sessão uma da outra; (b) resolução de `*.localhost` pelo navegador e por ferramentas fora dele; (c) cache e Redis isolados por site; (d) socket.io servindo as duas — verificar com a tabela de resultados em `docs/soda.md`, dizendo o que falhou, e rever o design se (a) ou (b) falharem.
- [ ] 1.2 Criar `erpnext_brasil/soda/` (sem `frappe`) com UUID versão 4, descritivo único (unicidade sem caixa nem acento, 3 a 60 caracteres), sua normalização e o nome de host — verificar com testes de borda (acento, símbolo, descritivo vazio, descritivo enorme, hífens repetidos, descritivos que só diferem por caixa ou acento) e com um teste que prova que o nome do host nunca colide entre dois UUIDs distintos.
- [ ] 1.3 Alocador de portas puro, com faixa, reservadas, portas já registradas e uma função "está livre" injetável — verificar com testes dos cenários da spec `identidade-e-portas` (menor livre, escolhida ocupada, reservada, faixa esgotada).
- [ ] 1.4 Modelo do registro (instâncias, aposentados, estados) e a conciliação de estado a partir de fatos injetados (processo existe, porta em escuta, site presente) — verificar com os cenários "caiu", "órfão", "criação interrompida" e "no ar".
- [ ] 1.5 Estender `tests/test_arquitetura.py` para vigiar o pacote novo (não importa `frappe` nem `integracao/`) — verificar acrescentando um import proibido e vendo o teste falhar.
- [ ] 1.6 Plano de criação e de remoção como listas de etapas puras, com o desfazer de cada etapa — verificar com testes que simulam falha em cada etapa e conferem que o desfazer desfaz só o que foi feito.

## 2. Registro atômico e trava

- [ ] 2.1 Gravação do registro com arquivo temporário e `os.replace`, reaproveitando a escrita do Cherry, e quarentena de registro ilegível — verificar com falha injetada no meio da escrita (o registro anterior fica intacto, sem temporário) e com um registro corrompido que não é sobrescrito.
- [ ] 2.2 Trava em arquivo contra dois Sodas — verificar com dois processos tentando alocar ao mesmo tempo, sem porta nem UUID duplicados.

## 3. Ciclo de vida (com executor injetável)

- [ ] 3.0 Ler os perfis de banco do Cherry (mudança `cherry-perfis-de-banco`) e recusar a criação sem perfil — verificar com os cenários de perfil padrão, MariaDB e PostgreSQL no mesmo bench, e sem perfil.
- [ ] 3.1 Criar: `new-site` com o nome de host, `--install-app` por aplicativo e `soda_instance_id` no `site_config`; senhas por ambiente e `WSLENV`; estado "criando" gravado antes — verificar com executor simulado que nenhum argumento contém senha e que o desfazer roda em cada ponto de falha.
- [ ] 3.2 Iniciar: serviços compartilhados por `scripts/subir.sh` (uma vez), servidor da instância por `bench --site <site> serve --port <porta> --noreload`, espera de resposta com prazo — verificar com executor simulado (já no ar, serviços parados, servidor que não responde) e confirmar o comando exato gerado.
- [ ] 3.3 Parar uma instância: processo identificado por PID e registro, pedido de término educado, nunca por nome, sem afetar as outras nem os serviços compartilhados — verificar com processos de teste em pasta temporária (um que obedece e um que ignora o sinal) e trechos de `/proc` de duas instâncias.
- [ ] 3.4 Remover: nome digitado, backup por padrão, `drop-site`, porta liberada e UUID aposentado; recusa com a instância no ar — verificar com executor simulado, inclusive nome errado e remoção sem backup avisada.
- [ ] 3.5 Limite de instâncias no ar e parada dos serviços compartilhados só por pedido e só sem instância no ar — verificar com os cenários da spec.
- [ ] 3.6 Conciliação com o sistema real (leitura de `/proc`, portas em escuta, sites do bench) — verificar com fatos reais coletados no WSL e com um processo morto de propósito.

## 4. Interface desktop idêntica ao Cherry

- [ ] 4.1 Esqueleto no molde do Cherry: janela, `ttk.Notebook` com `enable_traversal`, barra de estado, marca "✓", `_problema`, HiDPI, escolha do bench reaproveitando `Bench` e `caminho_wsl`, geometria validada contra a tela — verificar com `test_app.py` (janela oculta) e a lista de diretrizes do Cherry conferida uma a uma.
- [ ] 4.2 Aba **Instâncias**: lista com o descritivo, o UUID abreviado, o botão Renomear, host, porta, banco, aplicativos, estado por texto e ícone, tempo de atividade, filtro e estado vazio com instrução; UUID completo copiável — verificar com testes de interface e captura de tela nos estados criando, parada, no ar, caiu e vazio.
- [ ] 4.2a Desempenho por instância e do seu banco, lido do resumo do Chantilly (tempos mediano e p95, CPU, memória, requisições e falhas por minuto, jobs, conexões, tamanho, consultas lentas, taxa de acerto, tempo de resposta), com a idade da leitura e "indisponível" com motivo quando faltar — verificar com um resumo de exemplo, com resumo velho e sem Chantilly, conferindo que o Soda não mede nada por conta própria.
- [ ] 4.3 Ações do item selecionado (iniciar, parar, abrir no navegador, copiar URL, ver saída, remover), cada uma habilitada conforme o estado e explicando por que não está disponível — verificar com um teste por estado.
- [ ] 4.4 Aba **Nova instância** com as restrições à vista antes do envio e a pré-visualização do host e da porta — verificar com testes de campos obrigatórios, tamanho e formato espelhados no núcleo.
- [ ] 4.5 Abas **Serviços** e **Bench** — verificar com testes de interface e a conferência de teclado (foco, Tab, Enter, Alt) de cada aba.
- [ ] 4.6 Operações longas fora da thread, com progresso por etapa, saída em tempo real e "Parar de esperar" — verificar com criação simulada lenta: a janela responde em menos de 0,5 s, como no Cherry `0.2.1`.
- [ ] 4.7 Checklist de UX da Microsoft aplicada ponto a ponto, relida na web antes — verificar com o checklist preenchido em `docs/soda.md`.

## 5. Contrato de identidade para o Cherry e o Chantilly

- [ ] 5.1 `erpnext_brasil/soda/leitura.py`: leitor puro e somente leitura do registro (identificar por UUID, por descritivo, por nome de site; listar removidas), tolerante a campos desconhecidos e a versão de esquema maior — verificar com os cenários da spec `contrato-de-identidade` como testes, inclusive o registro corrompido e a versão futura.
- [ ] 5.2 Escrever `versao_esquema` no registro e `soda_instance_id` e `soda_descritivo` no `site_config` de cada instância, e propagar o descritivo renomeado — verificar relendo o `site_config` por outro caminho depois de criar e de renomear.
- [ ] 5.3 Teste de compatibilidade: um leitor da versão 1 lê um registro da versão 1 acrescido de campo novo, e recusa gravar quando a versão for maior — verificar com os dois arquivos de exemplo versionados em `tests/`.
- [ ] 5.4 O leitor não toma a trava de escrita e nunca vê arquivo pela metade — verificar com o Soda gravando em laço enquanto um leitor lê mil vezes, sem nenhuma leitura inválida.
- [ ] 5.5 Teste cruzado: o Cherry e o Chantilly identificam as mesmas instâncias, com o mesmo UUID e o mesmo descritivo, a partir do mesmo registro — verificar com um registro de exemplo lido pelos dois (após as mudanças `cherry-instancias-por-uuid` e `chantilly-monitor-de-recursos` existirem).
- [ ] 5.6 Persistência selecionável do registro: adaptadores JSON e SQLite atrás da mesma porta, migração nos dois sentidos com cópia do formato anterior (mudança `persistencia-sqlite-opcional`) — verificar com a suíte de contrato rodando contra os dois adaptadores e com a migração falhando no meio sem perder o original.

## 6. Comandos de terminal

- [ ] 6.1 `criar`, `listar`, `iniciar`, `parar`, `remover` e `estado`, com confirmação explícita no próprio comando e ensaio sem ela — verificar com testes de que, sem a confirmação, nada é alterado e o plano é mostrado.

## 7. CI, versão e documentação

- [ ] 7.1 Job de CI do Soda no padrão do job do Cherry (`xvfb`, `python3-tk`, piso de 95% no núcleo e piso da interface dois pontos abaixo do medido) — verificar com o job verde no PR e o log mostrando que a interface rodou e não foi pulada.
- [ ] 7.2 Versão `0.1.0`, licença MIT em `scripts/soda/LICENSE`, `README.md` da pasta e `docs/soda.md` (como rodar, o que cria, o que compartilha, o que não faz, limites, produção) — verificar relendo contra o código.
- [ ] 7.3 Indexar em `docs/README.md` e apontar do `docs/cherry.md` e do `docs/ambiente-dev-bench.md` — verificar abrindo os índices.
- [ ] 7.4 Rodar suíte pura, testes do Cherry e do Soda, `coverage` e `ruff` em `erpnext_brasil/` e `scripts/` — verificar com a saída verde e `openspec validate soda-instancias-do-erp`.
- [ ] 7.5 Gate de padrões antes de fechar: contratos (pré, pós e invariante) listados por módulo no documento da ferramenta, dependências injetadas por porta, teste na costura em cada gravação, cobertura do núcleo a 100% e pisos de CI cumpridos, `ruff check`, `ruff format --check` e `tests/test_arquitetura.py` verdes — verificar com a saída dos comandos e a lista de contratos no documento.

## 8. Prova real

- [ ] 8.1 Ciclo real de criar duas instâncias, iniciar as duas, entrar nas duas ao mesmo tempo, parar uma e remover as duas, **somente com autorização explícita** e backup antes — verificar com o registro, as duas URLs respondendo ao mesmo tempo, a outra instância intacta depois da parada e o banco removido; se não houver autorização, esta tarefa fica aberta e o motivo é dito.
- [ ] 7.6 Gate de resiliência e segurança (mudança `resiliencia-e-seguranca-das-ferramentas`): desfazer e retomar, idempotência, prazos em todo comando externo, tratamento de exceção na interface, validação de entrada, nenhum vazamento de segredo, varredura de padrões proibidos, confinamento de caminhos, permissões e limites — verificar com a saída dos comandos e a tabela de requisitos.
