# Leitor de código de barras e alertas do Frappe

Duas perguntas do usuário viraram dois incrementos: "posso usar leitores de código de
barras normal 1D e 2D?" e "o Frappe lança alertas?". As duas respostas são sim — e as
duas expuseram uma lacuna real que valia fechar.

## Leitores 1D e 2D: sim, mas eles entregam coisas diferentes

Praticamente todo leitor é HID: o sistema o vê como teclado, ele "digita" o que leu e dá
Enter. Nenhum driver, nenhuma integração. O ERPNext já tem suporte nativo (tabela de
códigos de barras no `Item`, campo "Scan Barcode" no PDV e nos documentos de estoque), e
o Frappe ainda embute `html5-qrcode` para leitura por câmera.

A pegadinha está no **conteúdo**, não no leitor:

| Documento | Código impresso | O que chega no campo |
|---|---|---|
| DANFE (NF-e), DACTE (CT-e), DAMDFE (MDF-e) | 1D, Code128C | os 44 dígitos da chave |
| DANFCe (NFC-e) | 2D, QR Code | uma **URL inteira**, com a chave no meio |

Ou seja: com 1D no DANFE já funcionava. Com 2D no cupom da NFC-e, o que chegava era
`https://.../qrcode?p=3526...|2|1|1|A1B2...` — a validação recusava, e a conclusão
natural (e errada) do usuário seria "o leitor 2D não funciona". O leitor funciona; o QR
Code da NFC-e simplesmente não contém a chave pura, e sim uma URL de consulta pública
(ver `docs/nfce-qrcode.md`).

### `fiscal/documento/leitura_codigo.py`

`extrair_chave(leitura)` aceita as três formas que aparecem na prática:

1. os 44 dígitos crus (leitor 1D);
2. a chave formatada com espaços, como o DANFE a imprime por extenso (colada à mão);
3. a URL completa do QR Code (leitor 2D), inclusive com `|` percent-encoded.

**Corta no primeiro `|`, não conta campos.** A sequência do QR Code tem duas variantes —
on-line (`chave|versão|ambiente|cscId`) e contingência off-line
(`chave|versão|ambiente|dia|valor|digest|cscId`) — e a chave é o primeiro pedaço nas
duas. Cortar no primeiro separador continua certo se a contingência ganhar mais um campo
amanhã; contar campos, não.

**Isola o candidato antes de remover separadores.** A ordem importa: remover pontuação
da URL inteira primeiro juntaria os dígitos de porta, versão e caminho com os da chave, e
poderia "achar" 44 dígitos onde não há chave nenhuma. Há teste para exatamente esse caso.

**Não adivinha.** Um EAN-13 de produto lido por engano no campo falha alto, em vez de ser
interpretado como pedaço de chave. E a chave extraída passa por `validar_chave` (layout e
dígito verificador) — extrair não é confiar.

O hook `integracao/chave_acesso_documento.validar_chave_acesso` passou a usar
`extrair_chave`. O campo aceita mais formas de **entrada** e continua guardando
exatamente o mesmo valor canônico de antes.

## Alertas: sim, e o vencimento do certificado A1 era o caso óbvio

O Frappe tem `frappe.msgprint`/`throw`/`show_alert`, o doctype **Notification**
(configurável na tela, inclusive "N dias antes de uma data"), o **Notification Log** (o
sininho) e `scheduler_events` no `hooks.py`.

O caso que valia automatizar: **o certificado A1 vale um ano e, quando vence, a emissão
simplesmente para**. `assinador_local.carregar_certificado` já recusava certificado
vencido — mas na hora de emitir, o pior momento possível para descobrir.

### A regra de quando avisar é pura (`fiscal/documento/validade_certificado.py`)

Avisar todo dia nos últimos 30 vira ruído, e ruído é ignorado — o alerta perderia a
função que justifica existir. Dois regimes:

- **Marcos** (30, 15 e 7 dias): um aviso em cada, e só nesses dias.
- **Urgência** (3 dias ou menos, e depois de vencido): aviso todos os dias.

Vencido também alerta, e é o caso mais importante: quem deixou passar é justamente quem
mais precisa ser avisado.

O módulo recebe `hoje` por parâmetro em vez de chamar `date.today()` internamente — sem
isso, não daria para testar nenhuma data que não fosse a de hoje.

### A leitura da validade precisou ser separada da que recusa vencido

`carregar_certificado` **recusa** certificado vencido; o alerta precisa justamente
conseguir abrir o vencido, ou nunca informaria o caso mais urgente. Daí
`assinador_local.expiracao_do_certificado`, que abre sem julgar. As duas compartilham
`_abrir_pkcs12`, então a leitura do formato não foi duplicada — fatorada, não copiada.

### `integracao/alerta_certificado.py`, agendado diariamente

- **Falha de uma empresa não derruba as outras**: num site multiempresa, senha errada ou
  anexo removido em uma `Company` é registrado no log e a varredura continua. Tarefa
  agendada que morre no primeiro erro deixa de avisar exatamente quem depende dela.
- **Destinatários**: usuários ativos com o papel "Accounts Manager", com fallback para
  "System Manager" — site pequeno pode não ter a função separada. Sem ninguém em nenhum
  dos dois, registra no log em vez de criar notificação órfã.
- **Diário, não horário**: a regra raciocina em dias; de hora em hora repetiria o mesmo
  alerta 24 vezes no dia do marco.
