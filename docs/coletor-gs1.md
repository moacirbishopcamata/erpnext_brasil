# O estoquista como coletor: leitura GS1 e GS1-128 composto

O ERPNext já serve de coletor de dados no estoque — `scan_barcode` é campo nativo em seis
DocTypes, com `barcode_scanner.js` no cliente e `erpnext.stock.utils.scan_barcode` no
servidor. O que faltava era ler a etiqueta que o fabricante brasileiro imprime.

## O problema, e por que ele falha em silêncio

O resolvedor do ERPNext busca o valor **inteiro** que foi lido em quatro cadastros, nesta
ordem: `Item Barcode` → `Serial No` → `Batch` → `Warehouse`. Funciona para um EAN-13.

Uma etiqueta **GS1-128 não é um identificador**: é uma *cadeia de elementos*, vários dados
concatenados num código só — GTIN, lote, validade, série. Nenhum cadastro contém aquele
texto inteiro, então a busca não acha nada e o estoquista lê **"não encontrado"** sem
qualquer pista do motivo. Ele conclui que o item não está cadastrado, e cadastra de novo.

E é justamente essa etiqueta que carrega o que a NF-e precisa: `nLote`, `dFab` e `dVal` do
grupo `rastro` estão **impressos nela**. Sem lê-la, o operador digita o lote à mão — que é
exatamente onde a rastreabilidade se perde.

## Como a cadeia se lê

Cada elemento começa com um **Application Identifier** (AI) de 2 a 4 dígitos. A pergunta
difícil é onde cada elemento termina, e a resposta tem duas metades:

| Metade | Regra | Exemplos |
|---|---|---|
| **Comprimento predefinido** | tamanho fixo, o próximo elemento começa em seguida, **sem separador** | `00` (18), `01` (14), `02` (14), `11`/`13`/`15`/`17` (6) |
| **Comprimento variável** | vai até o **FNC1**, ou até o fim da cadeia | `10` lote (≤20), `21` série (≤20), `30`/`37` (≤8) |

O FNC1 chega do leitor como **GS, ASCII 29** (`\x1d`).

⚠️ **Confundir as duas metades produz lixo plausível, não erro.** Tratar `01` como variável
engoliria o lote junto do GTIN; tratar `10` como fixo cortaria o lote ao meio. Os dois
devolvem string, e nenhum reclama. É o teste-âncora da suíte.

**Fonte:** *GS1 Barcode Syntax Dictionary*, publicado pela GS1 AISBL — **baixado e lido
localmente**. O `*` na coluna de flags é literalmente o sinal do dicionário para
*"Pre-defined length AI not requiring FNC1 separator"*; a tabela do módulo é transcrição
dele.

## ⚠️ O dia `00`

O linter das datas no dicionário oficial chama-se **`yymmd0`** — o `0` final não é enfeite:
o dia pode vir `00`, quando o fabricante não quis especificá-lo.

O módulo resolve `00` para o **último dia do mês**, e a escolha tem um lado seguro: numa
validade, ler `250600` como 1º/06 venceria o produto trinta dias antes da hora, e descartar
mercadoria boa é o erro caro.

📌 **Fonte a reconferir.** A GS1 publicou o GSCN 21-040 encerrando o uso de `00` para
produtos de saúde regulados a partir de janeiro de 2025. O texto do GSCN **não pôde ser
lido** — o servidor da GS1 devolve 403 para download direto —, então a data-limite e o
escopo exato estão registrados de segunda mão. Isso não muda a implementação: etiquetas
legadas com `00` continuam em circulação, e aceitá-las não é opcional.

## ⚠️ GTIN-14 com zeros contra o EAN-13 do cadastro

O AI (01) é **sempre** GTIN-14, com zeros à esquerda. O `Item Barcode` quase sempre guarda o
EAN-13 impresso na caixa.

```
etiqueta:  01 07891234567895      ← GTIN-14
cadastro:      7891234567895      ← EAN-13
```

Procurar os 14 dígitos crus não acha nada. A busca tenta as duas formas — é uma linha de
código, e é a diferença entre a leitura funcionar e não funcionar no mundo real.

## O desenho: decorador, não substituto

`integracao/leitura_gs1.py` **não reescreve** o resolvedor do ERPNext. Ele o envolve:

1. a cadeia parece GS1? → separa os elementos e resolve pelo GTIN;
2. não parece, veio malformada, ou o GTIN não está cadastrado? → **delega** ao
   `erpnext.stock.utils.scan_barcode`.

Assim toda melhoria que o ERPNext fizer no resolvedor continua valendo. Reimplementar as
quatro buscas criaria uma segunda verdade que envelheceria calada — mesmo motivo de não
haver `br_taxa_depreciacao` ao lado de `rate_of_depreciation`.

`parece_gs1` é **conservador de propósito**: na dúvida devolve `False` e deixa o caminho
antigo funcionar. Um EAN-13 ou GTIN-14 puro (só dígitos, 8/12/13/14 posições) nunca é tratado
como GS1, mesmo começando por `01`.

### A costura no cliente: patch no protótipo, não na instância

`erpnext.utils.BarcodeScanner` guarda o método **no construtor**:

```js
this.scan_api = opts.scan_api || "erpnext.stock.utils.scan_barcode";
```

Mas quem o **usa** é `scan_api_call`, que lê `this.scan_api` **na hora da chamada**:

```js
scan_api_call(input, callback) {
    frappe.call({ method: this.scan_api, args: { search_value: input, ctx: {...} } })
}
```

**Essa diferença é tudo.** Trocar a propriedade na instância exigiria *alcançar* a
instância — e cada tela a guarda num lugar diferente:

| Tela | Onde guarda | Alcançável? |
|---|---|---|
| `Stock Reconciliation` | `frm.barcode_scanner` | sim |
| `Stock Entry`, `Delivery Note`, `Purchase Receipt`, `Material Request` | `frm.cscript.barcode_scanner` | sim |
| `Pick List` | uma `const` local (`pick_list.js:296`) | **não** |

Envolvendo `scan_api_call` **no protótipo**, nada disso importa: o patch vale para toda
instância — criada antes ou depois, guardada em qualquer lugar. O `Pick List` deixou de ser
a exceção, e cinco costuras viraram uma.

#### ⚠️ Isto não é alterar o ERPNext

Nenhum arquivo do erpnext é tocado. Substitui-se um método **em memória**, no nosso próprio
JS — o mesmo mecanismo de `override_doctype_class` e `override_whitelisted_methods` do
Frappe, só que do lado do cliente, onde não existe hook equivalente.

O contrato é preservado de propósito, em duas camadas:

1. o método original é **chamado**, não reescrito — se o ERPNext mudar `scan_api_call`, a
   mudança dele continua valendo, só o método consultado é outro;
2. o resolvedor do servidor **decora** o do ERPNext em vez de substituí-lo.

Três guardas: só assume o lugar do **padrão** (um `scan_api` passado em `opts` é escolha
deliberada de quem o passou); é **idempotente**, porque o arquivo é carregado em seis telas
e envolver duas vezes empilharia decoradores; e se a classe não existir, **sai calado** — a
leitura simples continua funcionando pelo caminho de sempre, só a etiqueta GS1 deixa de ser
entendida. Derrubar a tela seria pior que perder o GS1.

### O contrato de retorno

`barcode_scanner.js` desestrutura `{ item_code, barcode, batch_no, serial_no, uom,
default_warehouse }`. O contrato é dele: devolver um dicionário com outros nomes faria o
leitor bipar, o servidor responder, e **nada acontecer na tela**.

O que a etiqueta traz e o ERPNext não tem onde guardar — validade, fabricação, quantidade,
SSCC — volta em `br_gs1`, que o JS do ERPNext ignora e fica disponível para quem quiser.

## 🔴 O defeito que só a execução mostrou

A primeira rodada num site v16 real devolveu um dicionário **bem formado** — e faltava uma
chave:

```
antes:  {barcode, item_code, uom, batch_no, serial_no, br_gs1}
depois: {barcode, item_code, uom, has_batch_no, has_serial_no, batch_no, serial_no, br_gs1}
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

O caminho GS1 contorna o `scan_barcode` do ERPNext e, com ele, o `_update_item_info` que
acrescenta `has_batch_no` e `has_serial_no`. E é exatamente disso que o JS depende para
decidir se pergunta:

```js
const require_selecting_batch = has_batch_no && !batch_no;
const require_selecting_serial = has_serial_no && !serial_no;

if (!(require_selecting_batch || require_selecting_serial))
    frappe.flags.hide_serial_batch_dialog = true;
```

Com `has_batch_no` **indefinido**, a expressão é falsa e o seletor é **suprimido**. O
cenário concreto: item com controle de lote, etiqueta GS1 que traz GTIN mas **não** traz o
AI (10) — a linha entra **sem lote**, e nada pergunta.

> Perder o lote em silêncio é justamente o que este módulo existe para evitar. O caminho de
> delegação nunca teve o problema (o `scan_barcode` chama `_update_item_info` internamente);
> só o atalho o tinha.

**Por que a suíte não pegou.** Ela conferia que o retorno tinha as chaves do contrato — e
todas estavam lá. O defeito era o que **faltava**: um campo que o nosso código nunca
prometeu e o JS do outro app consome. Só comparar as respostas dos **dois caminhos**, num
site de verdade, mostrou a diferença.

A correção reusa `_update_item_info` (que também resolve o `default_warehouse` a partir do
contexto). É função **privada** de outro app, então a falha de importação degrada para o
mínimo em vez de derrubar a leitura — e a **ordem** tem teste próprio: completar antes de
gravar `batch_no`, senão a decisão do JS é tomada com o dado que ainda não chegou.

## Como pôr em uso

### 1. Cadastrar o código de barras no item

`Item` → aba **Códigos de Barras** → uma linha por `barcode`. O que se cadastra é o **EAN-13
impresso na caixa**; o GTIN-14 da etiqueta é resolvido sozinho (ver a seção do enchimento).

Sem esse cadastro nada funciona — nem GS1, nem leitura simples. É o único passo obrigatório.

### 2. Configurar o leitor para emitir o FNC1

O leitor precisa transmitir o FNC1 como **GS (ASCII 29)**. É o padrão da maioria dos
aparelhos em modo GS1, mas alguns vêm configurados para suprimir caracteres de controle — e
aí a etiqueta chega sem separador.

**Como saber que é isso:** a leitura falha só nas etiquetas que têm lote **e** algo depois
dele. Uma etiqueta com o lote no fim funciona (o fim da cadeia também termina o elemento).
Esse padrão de falha é a assinatura do separador ausente.

O módulo recusa a cadeia nesse caso — o lote passaria de 20 caracteres —, em vez de gravar
um lote com o resto da etiqueta grudado.

### 3. Bipar

Nas cinco telas ligadas (`Stock Entry`, `Stock Reconciliation`, `Delivery Note`,
`Purchase Receipt`, `Material Request`) o campo é o mesmo **Scan Barcode** de sempre. Não há
tela nova nem botão novo: o estoquista não precisa saber que algo mudou — a etiqueta que
antes dava "não encontrado" agora preenche item, lote e série de uma vez.

## Sobre "GS1-128 composto"

O *composite component* (CC-A/CC-B) é uma questão de **simbologia**: um símbolo 2D empilhado
sobre o linear. O leitor entrega o conteúdo dele **concatenado** à cadeia do símbolo linear,
com os mesmos Application Identifiers.

Do lado do dado — que é o lado deste módulo — **não há diferença**. É por isso que ler
composto não exigiu código a mais: quem separa AI corretamente já lê os dois. Vale dizer
isso explicitamente porque a expectativa oposta é comum.

## Validação em bench v16

Exercitado em `v16.localhost` com um `Item` de teste cadastrado com o EAN-13
`7891234567895`:

```
etiqueta: '01' + '0' + EAN + '17250600' + '10LOTE-A1' + <GS> + '21SN-9'

RESULTADO GS1:
  item_code    GS1-TESTE
  batch_no     LOTE-A1          <- do AI (10)
  serial_no    SN-9             <- do AI (21)
  has_batch_no 1                <- a correção acima
  br_gs1       validade 2025-06-30   <- AI (17) com dia 00, virou 30/06

EAN-13 puro  -> delegou ao ERPNext (voltou com has_batch_no/has_serial_no)
valor inexistente -> {} , como o ERPNext devolve
```

Os três caminhos do decorador foram percorridos: **GS1 resolvido**, **delegação** e
**não encontrado**.

⚠️ **O que não foi exercitado é a tela.** A troca do `scan_api` no JS está conferida por
forma (o método existe, está exposto, e os dois lugares onde a instância mora são tratados),
mas nenhum formulário foi aberto num navegador para ver o campo preencher a linha.

## O que fica de fora, declarado

- **Dígito verificador do GTIN.** `fiscal/validators.py` já faz módulo 10; validar de novo
  criaria duas verdades sobre o mesmo dígito.
- **AI que o app não usa** — peso, dimensão, preço, destino. O dicionário tem mais de cem;
  transcrever todos sem uso seria carregar tabela que ninguém verifica. Um AI desconhecido é
  **recusado**, não adivinhado: sem saber o comprimento, não se sabe onde o elemento termina.
- **Leitor configurado com outro separador.** Normalizar isso é configuração de equipamento;
  aceitar um segundo separador aqui faria etiqueta malformada passar por boa.
- **Coletor offline.** `scan_barcode` é chamada ao servidor. Galpão sem cobertura precisa de
  fila local, que o Desk não faz.

## Fontes

- **GS1 Barcode Syntax Dictionary** (GS1 AISBL) — comprimentos, flags e a regra do FNC1.
  Baixado e conferido linha a linha.
- **GSCN 21-040** — fim do dia `00` para saúde regulada; 📌 não lido diretamente (403).
- `erpnext/public/js/utils/barcode_scanner.js` e `erpnext/stock/utils.py::scan_barcode` do
  erpnext **v16** — contrato de retorno e ordem das quatro buscas.
- `stock_entry.js`, `stock_reconciliation.js`, `pick_list.js`, `controllers/transaction.js`
  do erpnext **v16** — onde cada tela guarda a instância do leitor.
