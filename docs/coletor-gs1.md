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

### A costura no cliente

`erpnext.utils.BarcodeScanner` lê `opts.scan_api` **no construtor** e guarda na instância;
quem constrói é cada tela do ERPNext, e não há hook para interferir nisso. O que sobra — e
basta — é trocar a propriedade na instância já criada, no `refresh`.

⚠️ **A instância mora em dois lugares**, lido tela por tela no erpnext v16:

| Tela | Onde | Origem |
|---|---|---|
| `Stock Reconciliation` | `frm.barcode_scanner` | `stock_reconciliation.js` |
| `Stock Entry` | `frm.cscript.barcode_scanner` | `extend_cscript` |
| `Delivery Note`, `Purchase Receipt`, `Material Request` | `frm.cscript.barcode_scanner` | `TransactionController` |

Procurar só num dos dois faria a leitura GS1 funcionar em **metade** das telas — e é o pior
tipo de falha, porque o estoquista aprenderia que "às vezes funciona".

### O contrato de retorno

`barcode_scanner.js` desestrutura `{ item_code, barcode, batch_no, serial_no, uom,
default_warehouse }`. O contrato é dele: devolver um dicionário com outros nomes faria o
leitor bipar, o servidor responder, e **nada acontecer na tela**.

O que a etiqueta traz e o ERPNext não tem onde guardar — validade, fabricação, quantidade,
SSCC — volta em `br_gs1`, que o JS do ERPNext ignora e fica disponível para quem quiser.

## Sobre "GS1-128 composto"

O *composite component* (CC-A/CC-B) é uma questão de **simbologia**: um símbolo 2D empilhado
sobre o linear. O leitor entrega o conteúdo dele **concatenado** à cadeia do símbolo linear,
com os mesmos Application Identifiers.

Do lado do dado — que é o lado deste módulo — **não há diferença**. É por isso que ler
composto não exigiu código a mais: quem separa AI corretamente já lê os dois. Vale dizer
isso explicitamente porque a expectativa oposta é comum.

## O que fica de fora, declarado

- **`Pick List`.** Ele cria a instância do leitor numa `const` local
  (`pick_list.js:296`), sem guardá-la em lugar alcançável. Não há seam sem alterar o
  ERPNext — e alterar o ERPNext é o que este projeto não faz.
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
