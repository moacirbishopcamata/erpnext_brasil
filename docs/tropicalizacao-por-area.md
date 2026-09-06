# O que falta tropicalizar, área por área

Varredura das quatro áreas que o site do ERPNext anuncia — contabilidade, aquisições,
vendas e bancos — cruzada com o que este app já tem.

Feita em 2026-09-05 a pedido, contra as páginas oficiais de
[contabilidade](https://frappe.io/erpnext/open-source-accounting),
[aquisições](https://frappe.io/erpnext/open-source-procurement),
[vendas](https://frappe.io/erpnext/open-source-sales-invoicing) e contra o código do
ERPNext.

## ⚠️ A resposta curta

**Sim, há o que tropicalizar — mas menos do que parece, e não onde parece.**

A maior parte do que essas páginas anunciam é **neutra**: um centro de custo, um orçamento,
um relatório de idade de títulos funcionam igual no Brasil e na Índia. O que precisa de
localização é onde a **lei brasileira exige forma própria** — e nesses pontos o app já
cobre a maior parte do caminho fiscal.

Os quatro gaps reais que esta varredura encontrou estão no fim, em ordem de tamanho.

---

## Contabilidade

| Recurso anunciado | Situação |
|---|---|
| Chart of Accounts | ✅ [plano-de-contas.md](plano-de-contas.md) — grupos da Lei 6.404/76 |
| General Ledger / lançamentos | ✅ [lancamentos-contabeis.md](lancamentos-contabeis.md) |
| Tax Management (GST, VAT) | ✅ ICMS, IPI, PIS/Cofins, ST, DIFAL/FCP, e IBS/CBS/IS da reforma |
| E-invoicing | ✅ NF-e, NFC-e, CT-e, MDF-e — com cancelamento e CC-e |
| Financial Statements | ⚠️ os relatórios existem; **a forma da DRE brasileira não foi conferida** |
| Asset Register / Depreciation | 🔴 **gap** — ver abaixo |
| Bank Reconciliation | ⚠️ CNAB 400/240 e os dados bancários existem; falta o campo livre do boleto |
| Cost Centers, Dimensions, Budgeting | neutro |
| Multi-Company | ✅ [multi-tenant.md](multi-tenant.md) — configuração fiscal por `Company` |
| Multi-Currency, Inter-company | neutro (mas ver operação entre filiais, abaixo) |

Além do que a página anuncia, o app tem o que ela **não** menciona porque não existe fora
daqui: ECD, ECF, EFD-ICMS/IPI, EFD-Contribuições, EFD-Reinf, apuração periódica.

## Aquisições

| Recurso anunciado | Situação |
|---|---|
| Material Request, RFQ, Supplier Quotation | neutro |
| Purchase Order / Receipt / Invoice | ✅ campos fiscais nos três (CFOP, CST, NCM, apuração por linha) |
| Sugestão de CFOP na compra | ✅ [cfop-sugestao.md](cfop-sugestao.md) |
| Subcontratação | ✅ CFOP de industrialização por encomenda |
| **Tax Compliance / withholding** | ✅ `fiscal/impostos/retencoes.py` + [reinf-r4020.md](reinf-r4020.md) |
| Payment Order (pagamento em lote) | ⚠️ o formato brasileiro é CNAB **remessa**, que não existe aqui |
| Perpetual Inventory | neutro |
| Budget Controls, Aging, relatórios | neutro |

A entrada de mercadoria tem a peça mais difícil: **a NF-e do fornecedor precisa ser lida,
não digitada** — ✅ feito, ver [entrada-de-nfe.md](entrada-de-nfe.md).

⚠️ Correção: a primeira versão deste documento dizia que "`integracao/cte_extracao.py` já
faz isso para o CT-e". **Não faz.** Aquele módulo percorre `Shipment` → `Delivery Note` →
`br_chave_acesso`, isto é, lê **DocTypes do site**, não XML. Não havia precedente de parser
de documento fiscal recebido — `fiscal/documento/leitura_nfe.py` é o primeiro.

## Vendas

| Recurso anunciado | Situação |
|---|---|
| Quotation, Sales Order, Delivery Note | ✅ campos fiscais no `Delivery Note` e itens |
| Sales Invoice | ✅ emissão, cancelamento, CC-e, painel de situação |
| Pricing Rules, Discounts, Blanket Orders | neutro |
| Accounts Receivable | ✅ duplicatas (`cobr`), [boleto.md](boleto.md), [pix.md](pix.md) |
| Print Designer | ⚠️ **não serve para DANFE** — leiaute normatizado, não formato livre |
| CRM, Work Orders, Batch Reservation | neutro |
| Payment Reminders, aprovação em níveis | neutro (workflow, ver [lowcode.md](lowcode.md)) |

## Contas bancárias — existe no ERPNext?

**Sim, e é mais rico do que se supõe.** Em `erpnext/accounts/doctype/` há:

`Bank`, `Bank Account`, `Bank Account Type`, `Bank Account Subtype`, `Bank Transaction`,
`Bank Transaction Rule`, `Bank Reconciliation Tool`, `Bank Statement Import`,
`Bank Clearance`, `Bank Guarantee`.

O `Bank Account` guarda `account_name`, `account` (a conta contábil), `bank`, `iban`,
`bank_account_no`, `branch_code`, `is_company_account`, `party`, `statement_password`.

⚠️ **O que faltava era o vocabulário brasileiro.** Até esta varredura, `Bank` e
`Bank Account` não estavam entre os DocTypes de `setup/custom_fields.py` — e o boleto,
pronto desde sempre, não tinha de onde tirar agência, carteira nem convênio. Os campos
foram declarados; o que continua faltando é o campo livre por banco (ver abaixo).

---

# Os gaps, em ordem de tamanho

## 🔴 1. NFS-e — nota fiscal de serviço

**O maior gap de todos, e o mais fácil de não perceber**, porque tudo em volta está pronto.

O app emite NF-e (mercadoria), NFC-e (consumidor), CT-e (transporte) e MDF-e (manifesto).
**Não emite NFS-e** — e é ela que uma empresa de serviço precisa para faturar.

Já existe o preparo: o campo `codigo_servico_lc116` está declarado no `Item`, e
`fiscal/codigos/` conhece a Lei Complementar 116. O que falta é a emissão.

Por que é grande: **NFS-e é municipal**. Cada município teve o seu leiaute e o seu
webservice por duas décadas. O padrão nacional (ADN/Sefin Nacional) mudou isso, mas a
adesão é gradual.

✅ **Levantado** em [nfse-estado.md](nfse-estado.md), e o primeiro passo confirmou o que se
temia: **Porto Velho mantém emissor próprio** (SOAP/ABRASF); o nacional (REST/DPS) atende
lá só o MEI. São dois caminhos incompatíveis, e chamar qualquer um deles de "a NFS-e" seria
o erro estrutural do bloco. Os identificadores já estão implementados a partir dos XSD
oficiais; a emissão está **declarada fora de escopo por ora**, com o motivo escrito.

## 🔴 2. Boleto sem conta bancária — código pronto e sem costura

`contabil/boleto.py` monta código de barras e linha digitável (com a base do fator de
vencimento **de 2025**, não a de 1997). `cnab400_retorno.py` e `cnab240_retorno.py` leem o
retorno.

E **nada disso pode ser usado num site**, pelo mesmo motivo que a emissão de NF-e não podia
antes de `emissao_nfe.py`: falta de onde tirar os dados.

`montar_codigo_barras` exige `campo_livre` — 25 posições que cada banco define a partir de
**agência, conta, carteira, nosso número e convênio/cedente**. O `Bank Account` do ERPNext
tem `branch_code` e `bank_account_no`, e nenhum dos outros. Não há carteira, não há
convênio, não há dígito verificador separado, e o `Bank` não guarda o código COMPE.

Isto é gap de costura clássico — a família que `docs/gaps.md` trata como pior que bug.
Duas partes:

- ~~**campos brasileiros no `Bank Account`**~~ — **feito** nesta mesma varredura. O `Bank`
  ganhou `br_codigo_banco` (COMPE) e `br_ispb`; o `Bank Account` ganhou agência, os dois
  dígitos verificadores, carteira e convênio. `contabil/conta_bancaria.py` valida, e
  `integracao/conta_bancaria.py` lê do site.
- **montador de campo livre por banco** — **segue aberto**, e é a parte cara: cada banco
  compõe as 25 posições à sua maneira, e cada layout exige a especificação da instituição.
  É exatamente o tipo de coisa que não se deduz por analogia entre bancos.

Quatro decisões dessa parte, que valem registro:

- **O número da conta continua em `bank_account_no`.** Não se criou um `br_conta`: o campo
  já existe e é o que o resto do ERPNext usa; duplicá-lo produziria duas verdades sobre a
  mesma conta, e a divergência apareceria no dia em que alguém corrigisse uma e não a
  outra. Só o **dígito** virou campo novo, porque o campo livre o posiciona à parte.
- **COMPE fica no `Bank`, não no `Bank Account`.** É atributo da instituição — repeti-lo
  por conta deixaria duas contas do mesmo banco discordarem sobre qual banco é.
- **COMPE e ISPB são campos diferentes.** Três dígitos para o boleto, oito para o PIX, e
  nenhum se deduz do outro. Nem um nem outro é o `swift_number` que o ERPNext já tinha.
- **Mais de uma conta sem padrão marcado falha alto.** Escolher a primeira produziria
  boleto no banco errado, e o dinheiro entraria numa conta que ninguém está conciliando.

## 🟡 3. Depreciação e ativo imobilizado

O ERPNext traz Asset Register e três métodos de depreciação (linear, saldo decrescente,
duplo decrescente). O Brasil usa **taxas por tipo de bem** fixadas pela Receita Federal, e a
diferença entre a depreciação contábil e a fiscal é ajuste no LALUR.

Hoje o app **não tem nada** disso — só as contas de depreciação no plano de contas. Não é
urgente para faturar, e é obrigatório para apurar lucro real corretamente.

## 🟡 4. Entrada de NF-e do fornecedor, e operação entre filiais

Dois itens menores, do mesmo tipo:

- ~~**Ler o XML da NF-e do fornecedor**~~ — **feito**, ver
  [entrada-de-nfe.md](entrada-de-nfe.md). O que **não** foi feito, e é decisão declarada:
  criar os itens do documento. O `cProd` da nota é o código **do fornecedor**, e casá-lo
  por descrição ou EAN daria entrada no item errado.
- **Transferência entre filiais gera NF-e.** O "inter-company transaction" do ERPNext move
  valor entre empresas; no Brasil a mercadoria que sai de um CNPJ e entra em outro precisa
  de documento fiscal, com CFOP próprio. Não verificado se o fluxo atual emite.

---

## O que **não** é gap, e por que dizer isso importa

Anotar o que já está resolvido evita reabrir frente por engano:

- **Centro de custo, dimensão, orçamento, idade de títulos, crédito de cliente** — neutros.
  Não há forma brasileira dessas coisas.
- **Multi-moeda** — o Brasil não tem exigência própria além da conversão, já suportada.
- **Portal do fornecedor, RFQ, cotação** — neutros.
- **Conciliação bancária como *ferramenta*** — o `Bank Reconciliation Tool` serve; o que
  falta é o **formato** de arquivo (CNAB), que é outra coisa e está parcialmente pronto.
- **GIA** — já analisada e declarada fora de escopo em
  [gia-nao-e-gap.md](gia-nao-e-gap.md).

## Ordem sugerida

1. ~~**Campos brasileiros no `Bank Account`**~~ — **feito**.
2. ~~**Leitura do XML da NF-e de entrada**~~ — **feito**.
3. **NFS-e** — levantada; o que falta é o manual de integração do emissor municipal de
   Porto Velho, que a Semec anunciou. Enquanto ele não vem, seguem as peças puras comuns
   aos dois caminhos (tabelas oficiais, tipos do leiaute).
4. **Depreciação fiscal**, junto do LALUR, quando o bloco de lucro real avançar.
