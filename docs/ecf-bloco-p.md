# ECF: Bloco P (Lucro Presumido) — dimensionado, núcleo mínimo implementado

Fonte: `documentacao.senior.com.br/.../bloco-p.htm`, mesmo padrão de confiança já
aceito para os Blocos 0/J/K.

## Dez registros confirmados

`P001`/`P990` (abertura/encerramento), `P030` (período/método de apuração), `P100`
(Balanço Patrimonial), `P150` (Demonstração do Resultado), `P130`/`P200`/`P230`/`P300`/
`P400`/`P500` (memórias de cálculo — demonstração de rendimento incentivado, base do
IRPJ, isenção/redução, cálculo do IRPJ, base da CSLL, cálculo da CSLL).

## Achado real: seis registros compartilham o mesmo formato genérico "código + valor"

`P130`/`P200`/`P230`/`P300`/`P400`/`P500` têm todos a forma `REG`, `CODIGO`,
`DESCRICAO`, `VALOR` — cada um é uma tabela de memória de cálculo referenciando um
**catálogo de códigos** publicado pela Receita Federal que este incremento não
verificou. Uma função genérica "aceita qualquer código" não encodificaria nenhum
conhecimento de domínio real — seria indistinguível de escrever o `dict` na mão, e
daria a falsa impressão de que os códigos foram conferidos contra a tabela oficial
quando não foram. Por isso nenhum dos seis foi implementado.

## `P030` — mesma pendência já registrada para `K030`

Precisa saber qual método de apuração de IRPJ/CSLL a empresa usa — este projeto não
modela isso ainda (depende do núcleo L/M/N/Lucro Presumido entrar de verdade).

## `P100`/`P150` — candidatos reais de reuso, não implementados por dúvida real

`P100` (Balanço Patrimonial) combina exatamente os campos de plano de contas já
produzidos por `ecd_i050.montar_i050` com os de saldo já produzidos por
`ecd_i150.montar_i155`/`ecf_bloco_k.montar_k155` — o mesmo padrão de reuso que já
funcionou para `J050`/`K155`. **Não implementado**: a fonte não confirma se `P100`
recebe o plano de contas **próprio** da empresa ou o **referencial** da RFB (o nome do
campo é `CODIGO`, não `COD_CTA` como nos outros registros próprios — indício, não
confirmação, de que seja referencial). Implementar com a suposição errada geraria um
arquivo estruturalmente válido mas semanticamente incorreto. `P150` (Demonstração do
Resultado) tem a mesma forma e a mesma dúvida.

## O que foi implementado

`montar_p001`/`montar_p990` — abertura e encerramento do bloco, mesma convenção
trivial já usada em todos os outros blocos da ECF.

## Arquivos

- `erpnext_brasil/contabil/ecf_bloco_p.py` — `montar_p001`, `montar_p990`.
- `erpnext_brasil/tests/test_ecf_bloco_p.py` — 3 testes.
