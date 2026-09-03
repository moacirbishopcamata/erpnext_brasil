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

## Auditoria: que outras funcionalidades precisavam de alerta

Pergunta seguinte do usuário. Levantados todos os pontos de risco do app; os dois abaixo
tinham risco real **e** base já verificada no código, e foram implementados em
`integracao/alerta_fiscal.py`.

### 1. Documento fiscal aprovado com o ambiente em Homologação

O pior tipo de falha: silenciosa e cara. Documento transmitido em homologação **não tem
valor fiscal nenhum** — a SEFAZ autoriza, o número é consumido no ambiente de teste, e a
mercadoria circula sem documento válido. Quem esquece o ambiente em Homologação depois de
testar não recebia erro nenhum.

Decisões:

- **Aviso, não bloqueio** (`msgprint`, não `throw`): homologar é uso legítimo, e travar o
  envio impediria justamente o teste que o ambiente existe para permitir.
- **Em `on_submit`, não em `validate`**: em `validate` apareceria a cada gravação de
  rascunho, e alerta repetido é alerta ignorado.
- **Só quando há chave de acesso preenchida**: sem chave o documento não foi transmitido
  a lugar nenhum e o ambiente é irrelevante — avisar ali seria ruído em todo lançamento
  manual.

### 2. Cadastro incompleto para gerar a EFD

Os registros recusam dado ausente um a um, mas só na montagem, e a montagem para no
primeiro erro: quem tem mil itens descobre um problema por rodada. `verificar_prontidao_efd`
varre antes e devolve a **lista completa**.

A regra do que é pendência mora em `contabil/prontidao_fiscal.py` (puro, testável sem
bench) e **não inventa exigência**: é exatamente o que `efd_bloco_0`/`efd_bloco_c` já
exigem. Onde o registro aceita vazio, aqui também não vira bloqueio — o NCM ausente, por
exemplo, é **atenção** e não bloqueio, porque o layout o exige de indústria e equiparada,
não de todo mundo. Alertar sobre campo opcional treinaria o usuário a ignorar o alerta,
que é como um alerta morre.

Cada pendência diz **onde resolver** na tela ("Empresa > EFD-ICMS/IPI"), não o nome
interno do campo: quem lê precisa saber para onde ir.

### 3. Virada de fase da reforma tributária (segunda rodada da auditoria)

O achado mais grave das duas auditorias, e o único que **também exigiu corrigir código**,
não só avisar.

`ibs_cbs.py` embute alíquotas de um único ano: 2026, o ano-teste (1% no total). Isso está
certo — as de 2027 em diante dependem de lei ainda por fixar. O perigo estava no
**padrão**: `Operacao.ano` nasce valendo o ano-teste, e `operacao_de_documento` usava
esse padrão quando o documento não tinha ano de competência preenchido.

Consequência em 2027: documento sem aquele campo seria apurado com **1%**, enquanto a CBS
plena já vale e PIS/COFINS já foram extintos. Erro silencioso, de valor grande, e **para
menos** — o tipo que só aparece numa fiscalização.

Duas correções:

1. **`_ano_da_operacao` passou a usar o ano do próprio documento** (`posting_date` ou
   `transaction_date`) quando o campo está vazio, em vez do ano-teste fixo. Com isso, um
   documento de 2027 pede as alíquotas de 2027 e `aliquotas_do_ano` **falha alto** — que
   é o comportamento correto, e já existia; só nunca era alcançado. Em 2026 nada muda: o
   ano do documento **é** o ano-teste, e há teste garantindo isso.
2. **Alerta diário** (`verificar_transicao_da_reforma`) para avisar na virada do ano, não
   na primeira nota que o usuário tentar emitir.

O alerta também dispara para ano **anterior** a 2026, por motivo oposto: IBS/CBS não
existiam, então é sinal de ano digitado errado.

### O que deliberadamente NÃO virou alerta: prazos das obrigações acessórias

Seria o alerta mais óbvio de um ERP fiscal — e foi deixado de fora de propósito. Ao
levantar as datas, as fontes consultadas **divergem entre si**:

- EFD-Contribuições aparece como "dia 15" numa fonte e "10º dia útil do 2º mês
  subsequente" noutra;
- ECD aparece como "30 de junho" e como "último dia útil de maio";
- o prazo da EFD-ICMS/IPI **varia por UF**, então não existe uma data nacional;
- o site oficial da RFB continua recusando conexão (mesmo obstáculo de
  `docs/nfce-qrcode.md` e `docs/sped-fiscal.md`).

Cravar data legal errada em código é **pior** que não ter o alerta: o usuário confiaria e
perderia o prazo — com multa. Fica como pendência explícita, a ser implementada quando
houver fonte primária confirmada, e provavelmente **como configuração** (o prazo muda por
legislação e por UF), não como constante.
