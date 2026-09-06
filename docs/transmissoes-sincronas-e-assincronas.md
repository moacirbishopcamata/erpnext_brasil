# As transmissões são assíncronas?

Depende de **qual camada** se pergunta — e a resposta tem uma consequência prática que
vale declarar.

## Resposta curta

| Documento | O protocolo é | Este app resolve |
|---|---|---|
| **NF-e / NFC-e** | assíncrono (lote → recibo → consulta) | ✅ **em fila** (worker) |
| **CT-e / MDF-e** | assíncrono, mesmo desenho | dentro da chamada |
| **Eventos** (cancelamento, CC-e) | **síncrono** | direto |
| **eSocial** | **assíncrono, sem escapatória** | dentro da chamada |
| **NFS-e nacional** | **síncrono** (`POST /nfse` devolve a nota) | — não implementado |

✅ **A emissão de NF-e roda em fila** desde 2026-09-06 — ver [fila-e-jobs.md](fila-e-jobs.md).
As demais ainda acontecem dentro do request do clique, com a tela congelada.

---

## Por documento

### NF-e: o protocolo é assíncrono, a espera é escondida

A SEFAZ recebe um **lote** e devolve um **recibo**, não a autorização. A nota autorizada só
aparece numa segunda chamada, consultando o recibo.

`TransporteSefaz.transmitir` faz as duas e **resolve até um estado final** antes de
devolver: envia, consulta o recibo e, se ainda estiver em processamento, tenta de novo —
`tentativas_consulta_recibo=5`, `intervalo_consulta_recibo=5.0` por padrão, ou seja, até
**cerca de 25 segundos** de espera.

Essa espera existe do mesmo jeito — **mudou de lugar**: acontece no worker, não no request.
O botão enfileira e devolve na hora, e a tela é avisada por `publish_realtime` quando a
SEFAZ responde.

### Eventos: genuinamente síncronos

Cancelamento e carta de correção usam `NFeRecepcaoEvento4`, que responde na hora com o
resultado. Não há recibo a consultar. É por isso que `eventos_sefaz.enviar_evento` faz uma
chamada só.

### eSocial: assíncrono por desenho, e não dá para fingir

O `enviarLoteEventos` **não devolve o resultado**. Devolve apenas a confirmação de recepção
e um `protocoloEnvio`; o resultado de cada evento vem do `consultarLoteEventos`.

`transmissao_esocial.enviar_lote` sempre faz **ao menos uma segunda chamada** quando o
envio é aceito, e nunca devolve o `RetornoEnvioLote` cru como resultado final — devolvê-lo
seria dizer "transmitido" sobre um lote que ninguém sabe se passou.

E quando o lote fica **"Em processamento"** mesmo depois das retentativas, o caminho é
`consultar_lote_esocial`, um método à parte. **Reenviar nesse estado duplicaria os
eventos** — por isso a reconsulta não é um retry escondido dentro do envio.

### NFS-e nacional: síncrona

`POST /nfse` valida a DPS e devolve a NFS-e gerada ou a rejeição, na mesma resposta
(manual oficial do Emissor Público, v1.2). É o oposto da NF-e — e um dos motivos de o
transporte da NFS-e não poder ser reaproveitado do da NF-e.

---

## ✅ Resolvido para a emissão de NF-e

O gap abaixo foi levantado aqui e **pago** em seguida — ver
[fila-e-jobs.md](fila-e-jobs.md). A emissão de NF-e agora enfileira: a tela devolve na hora,
existe emissão em massa a partir da lista, e o duplo clique passou a ser barrado **no
servidor** (`deduplicate` com `job_id` determinístico), não só pelo `freeze` da tela.

Segue síncrono, e declarado: transmissão do lote eSocial, geração do arquivo EFD, e os
eventos de cancelamento/CC-e — estes últimos com menos urgência, por serem uma chamada só.

## ⚠️ O gap que esta pergunta revelou

**Nada disso rodava em `frappe.enqueue`.** A única fila do app hoje é a importação de tabelas
de código (`importar_codigos`), que é carga de cadastro, não transmissão.

Consequências:

- **A tela ficava travada** por até ~25 s numa emissão que precisasse consultar o recibo —
  resolvido para a NF-e; ainda vale para o lote de eSocial.
- **O request pode estourar o timeout** do servidor web se a SEFAZ estiver lenta. O padrão
  do Frappe é generoso, mas somar latência de rede a 25 s de retentativa aproxima do limite.
- **Emissão em massa não tinha caminho** — resolvido: a lista de `Sales Invoice` enfileira
  a seleção, um job por documento.

### Por que ficou assim, e por que não é erro

Foi a escolha certa para o primeiro caminho funcionar: uma emissão que devolve na hora é
depurável, testável sem worker e explicável ao usuário. Um job em segundo plano acrescenta
uma máquina de estados — enfileirado, rodando, falhou, expirou — que só se paga quando há
volume.

Era **débito declarado**, não desenho final — e foi pago para a NF-e.

⚠️ **O plano original tinha um erro, e ele não sobreviveu à implementação.** Este documento
propunha gravar um `Transmissao Fiscal` como `Pendente` ao enfileirar, para o painel ter o
que mostrar. Isso produziria **dois registros por emissão** — o pendente e o que
`emitir_nfe` grava —, e alguém teria de conciliá-los.

O estado "enfileirado" **não pertence ao registro fiscal**: um documento na fila não tem
situação perante o Fisco, tem uma tarefa pendente. Ele pertence à fila, e é dela que se
pergunta (`is_job_enqueued`). Na tela, virou indicador separado — e não uma sexta cor na
tabela de situações, que faria "em transmissão" parecer situação fiscal.

O que segue valendo do plano: a reconsulta do recibo poderia virar `scheduler_events` em
vez de retentativa dentro do job. Hoje ainda é retentativa — só que num worker, onde os
25 s não incomodam ninguém.

## Fontes

- `integracao/transporte_sefaz.py` — `tentativas_consulta_recibo`, `intervalo_consulta_recibo`.
- `integracao/transmissao_esocial.py` — por que sempre há uma segunda chamada.
- `integracao/eventos_sefaz.py` — evento resolvido numa chamada só.
- `integracao/fila_fiscal.py` — a fila, o `job_id` determinístico e a deduplicação.
- Manual dos Contribuintes — Emissor Público NFS-e, v1.2 (out/2025): `POST /nfse` síncrono.
