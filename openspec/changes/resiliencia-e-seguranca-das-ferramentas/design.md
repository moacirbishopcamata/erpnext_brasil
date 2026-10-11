## Context

Ver `proposal.md` (Why). A revisão do Cherry (`docs/revisao-do-cherry.md`) é o catálogo do que dá errado quando essas qualidades faltam: CH-01 (segredo em argumento), CH-02 (escrita não atômica), CH-03 (comando sem escape), CH-05 (janela travada) e o defeito achado ao escrever o teste (`_gravar_banco` lia JSON fora do `try`). A persistência nova já mostrou outro: a suíte de concorrência encontrou gravações perdidas no Windows (`os.replace` contra um leitor; conversão para WAL concorrente; migração repetida), todas corrigidas por teste.

## Goals / Non-Goals

**Goals:**
- Critérios de resiliência, robustez e segurança que **um teste confere**, comuns às três ferramentas.
- Nenhuma dependência nova (varredura por `ast`, entrada aleatória com `random` e semente fixa).
- Reaproveitar os blocos: `persistencia` (escrita atômica, trava, quarentena), o executor injetável, o redator de segredo, o confinamento de caminhos.

**Non-Goals:** auditoria externa, criptografia do armazenamento, assinatura de binários.

## Decisions

1. **Blocos comuns em pacote puro `erpnext_brasil/sistema/`** (sem `frappe`, sem tkinter): `execucao` (executor com prazo, limite de saída e redação de segredo), `caminhos` (confinamento, recusa de `..` e de link simbólico), `redator` (mascara valores de segredo em texto), `limites` (rotação de log, teto de saída). As três ferramentas os usam; nenhuma reimplementa.
2. **Executor único.** Toda chamada externa passa por `executar(comando: list[str], *, prazo, limite_de_saida, ambiente)`, que devolve um resultado imutável (código, saída truncada, indicador de truncamento, duração, se estourou o prazo) e **nunca** usa shell. É a porta que os testes substituem.
3. **Redator de segredo.** O conjunto de valores secretos conhecidos (senhas digitadas na sessão) é registrado no redator; toda mensagem exibida ou gravada passa por ele. É defesa em profundidade: o objetivo continua sendo o segredo nem chegar ao texto.
4. **Operações com intenção registrada.** Um "diário de operação" mínimo (no registro de cada ferramenta) guarda, antes do primeiro passo, o plano e o passo concluído mais recente. A abertura seguinte lê o diário, e uma operação sem desfecho vira "interrompida". É o mecanismo do estado "criando" do Soda, generalizado.
5. **Tratamento de exceção na interface.** Um único ponto (`report_callback_exception` do Tk, e um decorador nos manipuladores) converte exceção em mensagem e registro, mantém a janela viva e fecha o diário da operação como "falhou".
6. **Varredura por `ast` como trava.** `tests/test_seguranca_das_ferramentas.py` percorre `scripts/cherry`, `scripts/soda`, `scripts/chantilly` e os pacotes puros e falha em `shell=True`, `os.system`, `eval`, `exec`, `pickle`, `except:` sem tipo, `subprocess` fora do executor único, e em `open(..., "w")` fora da escrita atômica. Exceções legítimas entram numa lista curta com motivo.
7. **Leitores de texto externo testados com entrada aleatória.** Para cada leitor (`/proc/stat`, `/proc/meminfo`, `/proc/<pid>/stat`, `cmdline`, saída do `bench`, JSON de terceiros), um teste alimenta entradas truncadas, vazias, com bytes inválidos e mil entradas aleatórias de semente fixa, e exige "indisponível" com motivo, nunca exceção.
8. **Permissões.** Arquivos novos de estado nascem restritos ao dono (`mkstemp` já cria `0600`; o SQLite recebe `chmod 0600` após criado). No Windows a permissão POSIX não existe: o teste dessa parte roda em Linux/WSL e o documento diz que no Windows vale a ACL da pasta do usuário.
9. **Falhar fechado.** Em ação destrutiva, a dúvida recusa: processo sem `cwd` legível, bench não resolvido, estado desconhecido.
10. **Padrões de código.** Os do projeto (ver `PADROES` nos outros designs), mais: módulos pequenos com um motivo para mudar, nomes do domínio, tipagem nos limites, nenhuma exceção engolida, docstring que diz o contrato e a fonte.

## Risks / Trade-offs

- **Custo:** mais código e mais teste. Mitigação: os blocos comuns são escritos uma vez e as três ferramentas os usam.
- **Falsos positivos da varredura:** a lista de exceções existe, com motivo, e o teste cobra que cada exceção ainda seja necessária.
- **Permissão no Windows:** não há equivalente simples; a mitigação é documentar e testar em WSL.
- **Entrada aleatória não é prova:** reduz a chance de erro grosseiro; o resto é o contrato e a revisão.

## Open Questions

1. O diário de operação fica no registro de cada ferramenta ou num arquivo comum? Proposta: no registro de cada uma, para não criar um terceiro formato.
2. O limite padrão de saída capturada (proposta: 1 MiB) e o de rotação de log (proposta: 5 MiB × 3) estão adequados?
