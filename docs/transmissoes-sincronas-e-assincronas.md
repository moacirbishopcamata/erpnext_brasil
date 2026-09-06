# As transmissões são assíncronas?

Depende de **qual camada** se pergunta — e a resposta tem uma consequência prática que
vale declarar.

## Resposta curta

| Documento | O protocolo é | Este app resolve |
|---|---|---|
| **NF-e / NFC-e** | assíncrono (lote → recibo → consulta) | **dentro da chamada** |
| **CT-e / MDF-e** | assíncrono, mesmo desenho | dentro da chamada |
| **Eventos** (cancelamento, CC-e) | **síncrono** | direto |
| **eSocial** | **assíncrono, sem escapatória** | dentro da chamada |
| **NFS-e nacional** | **síncrono** (`POST /nfse` devolve a nota) | — não implementado |

⚠️ **Nenhuma transmissão deste app roda em job de segundo plano.** Todas acontecem dentro
do request HTTP do clique, com a tela congelada (`freeze: true`).

---

## Por documento

### NF-e: o protocolo é assíncrono, a espera é escondida

A SEFAZ recebe um **lote** e devolve um **recibo**, não a autorização. A nota autorizada só
aparece numa segunda chamada, consultando o recibo.

`TransporteSefaz.transmitir` faz as duas e **resolve até um estado final** antes de
devolver: envia, consulta o recibo e, se ainda estiver em processamento, tenta de novo —
`tentativas_consulta_recibo=5`, `intervalo_consulta_recibo=5.0` por padrão, ou seja, até
**cerca de 25 segundos** de espera.

Do ponto de vista de quem clicou, a emissão é síncrona: o botão trava e volta com a nota
autorizada ou com a rejeição.

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

## ⚠️ O gap que esta pergunta revela

**Nada disso roda em `frappe.enqueue`.** A única fila do app hoje é a importação de tabelas
de código (`importar_codigos`), que é carga de cadastro, não transmissão.

Consequências:

- **A tela fica travada** por até ~25 s numa emissão que precise consultar o recibo, e por
  outro tanto num lote de eSocial.
- **O request pode estourar o timeout** do servidor web se a SEFAZ estiver lenta. O padrão
  do Frappe é generoso, mas somar latência de rede a 25 s de retentativa aproxima do limite.
- **Emissão em massa não tem caminho.** Faturar cem notas hoje significa cem cliques, cada
  um com a sua espera.

### Por que ficou assim, e por que não é erro

Foi a escolha certa para o primeiro caminho funcionar: uma emissão que devolve na hora é
depurável, testável sem worker e explicável ao usuário. Um job em segundo plano acrescenta
uma máquina de estados — enfileirado, rodando, falhou, expirou — que só se paga quando há
volume.

Mas é **débito declarado**, não desenho final. O caminho, quando o volume aparecer:

1. `frappe.enqueue` para a emissão, gravando `Transmissao Fiscal` como `Pendente` de
   imediato — a situação já existe no `Select`, e foi criada pensando nisto;
2. o painel de situação fiscal (já existe) passa a mostrar "em transmissão";
3. a reconsulta do recibo vira `scheduler_events`, não retentativa dentro do request.

O passo 1 é barato porque o registro em todos os desfechos já é a disciplina do app: o que
falta é quem o crie antes da resposta, não depois.

## Fontes

- `integracao/transporte_sefaz.py` — `tentativas_consulta_recibo`, `intervalo_consulta_recibo`.
- `integracao/transmissao_esocial.py` — por que sempre há uma segunda chamada.
- `integracao/eventos_sefaz.py` — evento resolvido numa chamada só.
- Manual dos Contribuintes — Emissor Público NFS-e, v1.2 (out/2025): `POST /nfse` síncrono.
