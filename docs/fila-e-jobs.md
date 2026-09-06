# Fila e jobs: como este app tira trabalho do request

Caixa de ferramentas para transmissão assíncrona no Frappe — o que se usou, por quê, e o
que **não** se fez de propósito.

## O que estava errado

Três problemas, todos consequência de fazer o trabalho pesado dentro do request do clique:

1. **A tela travava até ~25 s.** A emissão resolve o recibo da SEFAZ dentro da chamada, e o
   `freeze: true` segurava o usuário enquanto isso.
2. **Emissão em massa não existia.** Cem notas eram cem cliques, cada um com a sua espera.
3. **Duplo clique consumia número.** O `freeze` é barreira de **tela**: dois navegadores,
   um `F5` no meio da espera ou uma chamada de API passavam por cima dele.

## A solução, em uma frase

`frappe.enqueue` com **`job_id` determinístico** e **`deduplicate=True`**, na fila `long`, com
`enqueue_after_commit=True` — e a tela pergunta à fila, não ao banco, se há transmissão em
andamento.

---

## As cinco decisões

### 1. `job_id` determinístico é o coração

```python
def job_id_da_emissao(doctype: str, name: str) -> str:
    return f"erpnext_brasil::emitir_nfe::{doctype}::{name}"
```

⚠️ **Sem determinismo, `deduplicate` não protege nada.** É ele que permite ao Frappe
reconhecer que o segundo pedido é o mesmo do primeiro.

E a falha é **silenciosa**: se alguém puser um `uuid` ou um timestamp aí, dois cliques
passam a enfileirar dois jobs, cada um consome um número da série, e **nada quebra** — só se
emite nota a mais. Por isso o teste-âncora procura literalmente por `uuid`, `random` e
`time.` no corpo da função.

### 2. `deduplicate` vale mais que o `freeze`

O `freeze` é da tela; o `deduplicate` é do servidor. Vale para dois navegadores abertos, para
`F5` no meio da espera e para chamadas de API — e em numeração fiscal essa diferença é
dinheiro: **número queimado não volta para a série**.

### 3. Fila `long`, timeout explícito

| Fila | Timeout |
|---|---|
| `short` | 300 s |
| `default` | 300 s |
| `long` | **1500 s** |

Uma emissão que consulte recibo já gasta ~25 s, e a SEFAZ tem dias ruins. Enfileirar na
`default` faria a transmissão morrer por timeout **justamente quando o autorizador está
lento** — o pior momento para perder o rastro do que foi enviado.

O `TIMEOUT` do app é **900 s**: explícito e menor que o da fila. Um job que passa disso não
está lento, está preso — e deixar o teto de 1500 s valer ocuparia um worker por 25 minutos
com algo que já não vai voltar.

### 4. `enqueue_after_commit=True`, sempre

O worker é **outro processo com outra conexão**. Enfileirar antes do commit abre a janela em
que o job começa a rodar e não enxerga o que a transação ainda não gravou.

Aqui o request quase não grava nada, e a regra vale do mesmo jeito: a janela é pequena, e o
erro que ela produz é **intermitente** — a pior espécie de erro, porque não reproduz.

O mesmo vale para o `publish_realtime` que avisa a tela: `after_commit=True`, porque o aviso
não pode chegar antes do dado que ele anuncia.

### 5. Um job por documento, nunca um job para o lote

Um lote único falharia inteiro por causa de uma nota — e **numeração fiscal não permite
refazer o que já passou**: o que foi autorizado, foi. Cem documentos viram cem jobs
independentes.

Pela mesma razão, um documento sem permissão **não interrompe os demais**: interromper faria
o usuário descobrir o problema documento a documento, reenfileirando tudo a cada descoberta.

---

## ⚠️ O que **não** se fez, e por quê

### Não se criou um `Transmissao Fiscal` "Pendente"

Era a tentação óbvia: gravar um registro pendente antes de enfileirar, para a tela ter o que
mostrar. Isso produziria **dois registros por emissão** — o pendente e o que `emitir_nfe`
grava —, e alguém teria de conciliá-los.

**O estado "enfileirado" não pertence ao registro fiscal.** Um documento na fila não tem
situação perante o Fisco; tem uma tarefa pendente. Ele pertence à fila, e é dela que se
pergunta (`is_job_enqueued`).

Na tela, isso aparece como **indicador separado** — não como uma sexta cor na tabela de
situações. Misturá-los faria "em transmissão" parecer uma situação fiscal, que não é.

### Não se mudou `emissao_nfe.emitir_nfe`

O trabalho pesado continua exatamente onde estava, com os mesmos testes. A fila só decide
**quando** ele roda. Envolver código testado em vez de reescrevê-lo é o que torna a mudança
barata de revisar.

### Não se engolem erros no worker

`emitir_nfe` grava o `Transmissao Fiscal` antes de levantar, e a exceção sobe para o RQ, que
a registra em `Error Log` com traceback. Capturá-la no job "para não sujar o log" esconderia
a única pista de uma emissão que falhou sem ninguém olhando.

### `transmitir_em_fila` não é `@frappe.whitelist()`

Expor o que roda no worker permitiria **pular a fila e a deduplicação** — que são exatamente
o que este módulo acrescenta.

---

## Receita para reusar

Quando outra operação deste app precisar sair do request:

1. **Função que faz o trabalho**, sem `@frappe.whitelist()`, chamando o que já existe.
2. **`job_id` determinístico** derivado do que identifica a operação.
3. **Método whitelisted** que confere permissão, pergunta `is_job_enqueued` e só então
   `frappe.enqueue(..., job_id=..., deduplicate=True, enqueue_after_commit=True)`.
4. **`publish_realtime` com `after_commit=True`** no fim do job, para a tela se atualizar.
5. **A tela pergunta à fila** o estado intermediário, e não inventa registro para representá-lo.

Candidatos naturais, ainda não feitos:

- **Transmissão do lote eSocial** — hoje síncrona, e um lote de folha é mais pesado que uma
  nota.
- **Geração do arquivo EFD**, que percorre o mês inteiro.
- **Cancelamento e CC-e** — menos urgentes, porque são eventos síncronos na SEFAZ (uma
  chamada só, sem consulta de recibo).

## Fontes

- `frappe/utils/background_jobs.py` — `enqueue`, `is_job_enqueued`, `get_queues_timeout`
  (300 s / 300 s / 1500 s).
- `frappe/realtime/__init__.py` — `publish_realtime` e o `after_commit`.
- [transmissoes-sincronas-e-assincronas.md](transmissoes-sincronas-e-assincronas.md) — o
  levantamento que originou este trabalho.
