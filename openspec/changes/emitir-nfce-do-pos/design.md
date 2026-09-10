## Context

Ver `proposal.md` — Why. O que o desenho precisa levar em conta do estado atual:

- O app tem camadas puras (`fiscal/`, `contabil/`, `folha/`) **sem nenhum import de `frappe`**,
  conferido por `tests/test_arquitetura.py`. `integracao/` é a única camada que fala com o
  framework, com teto de 320 linhas por módulo.
- `TransporteSefaz` é deliberadamente livre de `frappe`: sessão, relógio, guarda de bloqueio e
  registrador de resposta são **injetados**. Foi o que permitiu tratar o cStat 656 sem tocar no
  adaptador.
- O modelo 65 já existe na camada pura: chave de acesso, autorizadores por UF, QR Code,
  tabelas. Nada disso precisa nascer.
- `POS Invoice` hoje não recebe campo fiscal nenhum, não está no `hooks.py`, e aparece só em
  `NOMES_USADOS_COMO_CHAVE` do contrato de leituras.
- Toda leitura de estrutura do ERPNext é declarada em `setup/leituras_do_erpnext.py` e conferida
  por um teste puro e outro de bench — este último é a única coisa no projeto que pega um renome
  do ERPNext na atualização em vez de na entrega ao Fisco.
- Erro tem **código numérico ≥1000 para a máquina e mensagem em pt-BR para a pessoa**
  (`fiscal/codigos_de_erro.py`).

## Goals / Non-Goals

**Goals:**

- A decisão de contingência é **pura e testável sem bench** — ela é a parte que erra caro.
- A pendência de autorização é **estado persistido no banco**, não fila em memória nem retry no
  processo que atendeu a venda.
- Reuso da emissão existente: o POS não ganha um segundo caminho de emissão paralelo ao
  `emissao_nfe.py`.

**Non-Goals:**

- **Não** implementar operação com o navegador offline. A contingência aqui é da *SEFAZ*
  indisponível, com o servidor Frappe de pé. POS totalmente offline (cliente sem servidor) é
  outra frente e outro conjunto de problemas.
- **Não** tratar contingência de NF-e (modelo 55) — SVC e FS-DA têm regras próprias e não
  entram nesta change.
- **Não** substituir a tela de POS do ERPNext por uma nossa.

## Decisions

### 1. A decisão de contingência vive em `fiscal/`, pura; quem age é `integracao/`

Um módulo puro recebe **o que aconteceu na transmissão** (respondeu / não respondeu / rejeitou /
bloqueado) e o instante atual, e devolve **o que fazer** (emitir normal, entrar em contingência,
recusar). Sem `frappe`, sem rede, sem relógio próprio.

*Por quê:* é a Lei 5 do projeto — separar a decisão da ação. A alternativa (decidir dentro do
`try/except` da chamada HTTP) só é testável com bench e com a SEFAZ simulada, e é exatamente
onde os três casos parecidos — indisponibilidade, rejeição e bloqueio 656 — se confundem. Com a
decisão pura, cada confusão vira um teste de uma linha.

*Alternativa considerada:* usar o `codigo` do cStat direto no `except`. Recusada: cStat só
existe quando **houve** resposta; a indisponibilidade é justamente a ausência dele.

### 2. A pendência é um DocType próprio, não um campo de situação no `POS Invoice`

Um registro por documento em contingência, com chave de acesso, momento de entrada, motivo e
situação da autorização posterior.

*Por quê:* o requisito é que a pendência sobreviva a reinício e seja consultável ("quantos e há
quanto tempo"). Campo de situação no próprio documento resolveria o primeiro, mas não dá lista
nem prazo sem varrer todos os `POS Invoice`. E a fila precisa de tentativas registradas — um
campo não tem onde guardá-las.

*Alternativa considerada:* reusar o `Bloqueio Sefaz` já existente. Recusada: bloqueio é estado
do **emitente**, pendência é estado do **documento**. Já é o erro que a memória "nunca assumir
por analogia" nomeia.

### 3. A autorização posterior roda por `scheduler_events`, e o disparo é idempotente

O agendador reprocessa a fila; o processamento de um documento já autorizado não faz nada.

*Por quê:* precisa acontecer sem o operador. E porque um cupom já entregue não admite emissão
duplicada — se a autorização foi obtida e o registro não fechou, a nova rodada tem de consultar
a chave, não emitir outra.

### 4. Campos do POS saem do mesmo laço que já gera os quatro documentos

`setup/campos_documento.py` gera cabeçalho e itens dos quatro documentos ligados num laço só.
`POS Invoice` entra na lista de entrada desse laço.

*Por quê:* a medição já mostrou que o código **não duplica** — quem replica é o modelo do
ERPNext. Escrever um bloco separado para o POS criaria a duplicação que hoje não existe.

*Cuidado:* a tabela-filha de itens do `POS Invoice` é `POS Invoice Item`, e o `parenttype` que
o `Custom Field` recebe muda. Verificar no site, não por analogia com `Sales Invoice Item`.

### 5. A migração do indicador é um movimento só, com teste dos dois lados

`POS Invoice: indNFCe` sai de `INDICADOR_QUANDO_LIGARMOS` e entra em `INDICADOR_POR_DOCUMENTO`
**no mesmo commit** em que o `hooks.py` liga o DocType.

*Por quê:* `test_indicador_por_documento` já reprova as duas metades: ligado e fora do mapa
(cairia em `indNFe` silenciosamente — cupom conferido pela tabela de nota) e no mapa e não
ligado (entrada inalcançável). Fazer em dois commits deixa a suíte vermelha no meio, o que é
correto e desconfortável; fazer junto é o certo aqui porque é uma mudança só.

### 6. A fatura consolidada do caixa é recusada explicitamente pela emissão

Descoberto ao inspecionar o site v16, não previsto no desenho inicial: o POS **consolida**
os cupons num `Sales Invoice` (campo `consolidated_invoice`, Link somente-leitura, via
`POS Invoice Merge Log`), e o consolidado carrega `is_consolidated = 1`.

`Sales Invoice` **está ligado** aos nossos hooks fiscais. Ou seja, a fatura que agrega as
vendas do caixa passa pela mesma porta de emissão que uma venda comum — e emitir sobre ela
documentaria as mesmas operações duas vezes, uma no cupom e outra na nota.

A emissão passa a recusar `is_consolidated`, com código e mensagem próprios.

*Verificado, e o resultado foi o oposto do temido:* a validação de classificação **não**
trava a consolidação hoje. `problemas_dos_itens` ignora item sem classificação nenhuma de
propósito ("exigir aqui impediria de salvar um rascunho"), e o consolidado nasce sem campo
fiscal porque `POS Invoice Item` não tem nenhum `br_*`. Não há bug ativo — há um caminho
aberto que precisa de porta.

*Alternativa considerada:* tirar `Sales Invoice` consolidado do hook de validação. Recusada:
o hook não é o problema — ele já degrada corretamente. O que falta é recusa **na emissão**,
que é onde o documento em duplicidade nasceria.

### 7. Valores do MOC não entram no código sem fonte primária conferida

O tipo de emissão da contingência offline da NFC-e, o prazo de transmissão posterior e o formato
do QR Code em contingência vêm do Manual de Orientação do Contribuinte. Nenhum deles é escrito
de memória: a tarefa correspondente exige abrir a fonte e registrar a referência na docstring.

*Por quê:* é a regra do projeto, e aqui o custo do erro é cupom entregue ao consumidor com
documento que a SEFAZ nunca vai aceitar.

## Risks / Trade-offs

- **Cupom entregue que nunca autoriza** → é o pior resultado possível e o motivo da decisão 2:
  a pendência é registro persistido, com alerta quando ultrapassa o prazo do MOC, e a rejeição
  posterior é marcada como exigindo tratamento humano em vez de descartada.
- **Entrar em contingência quando a SEFAZ na verdade rejeitou** → a decisão pura separa
  "respondeu" de "não respondeu"; um teste por caso, incluindo o bloqueio 656, que não é
  nenhum dos dois.
- **Emissão duplicada na retomada** → o processamento da fila é idempotente e consulta a chave
  antes de emitir de novo (decisão 3).
- **Ler estrutura do POS sem declarar** → todo DocType novo lido entra em
  `setup/leituras_do_erpnext.py`; a conferência de bench reprova o que ficar de fora.
- **Teto de 320 linhas em `integracao/`** → a fila e a emissão do POS provavelmente não cabem
  num módulo só. Fatorar em módulos, nunca enxugar a prosa.

## Migration Plan

1. Campos declarados e `bench migrate` — inertes enquanto o hook não estiver ligado.
2. Hook + migração do indicador, no mesmo commit.
3. Emissão normal do POS, sem contingência: já entrega valor e é reversível desligando o hook.
4. Contingência e fila, com o agendador desligado por configuração até a conferência em bench.

Reversão: desligar o hook devolve o comportamento anterior; os campos ficam declarados e vazios,
sem efeito. Documentos já em contingência continuam na fila e precisam ser resolvidos — por isso
o passo 4 é o último.

## Open Questions

- O cupom impresso sai por *Print Format* do Frappe ou pelo caminho de impressão do próprio POS
  do ERPNext? A resposta muda o formato de entrega, não o conteúdo exigido pela spec nem a
  quebra de tarefas.
- Se o mesmo caixa emitir em contingência para dois emitentes (empresas) diferentes, a fila é
  única com filtro ou uma por empresa? Só afeta a consulta, não o registro.
