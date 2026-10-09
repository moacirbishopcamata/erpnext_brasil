# Inventário de gaps — varredura de 2026-09-04

Levantamento sistemático de tudo que falta, feito a pedido ("é o momento de varrermos
todos os gaps"). Diferente dos "Ainda por implementar" espalhados por documento, este
arquivo cruza **o que está declarado como pendente** com **o que ninguém declarou porque
ninguém percebeu**.

A segunda categoria é a que importa: são gaps de **costura** — código escrito, testado e
documentado que, num site real, não é alcançado por nada.

## Resumo

| Categoria | Quantidade |
|---|---|
| Gaps de costura confirmados (código inalcançável ou inerte) | **5** |
| Campos que a integração usava e a instalação nunca criava | **31** — todos corrigidos |
| Módulos de integração sem teste de bench | 26 de 31 |
| Itens pendentes declarados em `docs/` | 69 |
| Documentos desatualizados encontrados | 2 |
| Fontes a reconferir | 2 |

---

## 1. Gaps de costura — os que ninguém tinha declarado

Encontrados cruzando `hooks.py`, `setup/custom_fields.py` e o grafo de importação. Todos
verificados um a um, não inferidos.

### 1.1 `br_chave_acesso` nunca é criado — o hook roda e não faz nada

`integracao/chave_acesso_documento.validar_chave_acesso` está ligado no `validate` de
`Sales Invoice`, `Delivery Note`, `Purchase Invoice` e `Purchase Receipt`. Ele lê:

```python
valor = doc.get("br_chave_acesso")
```

**Esse campo não existe em nenhum desses DocTypes.** `setup/custom_fields.py` declara 56
campos, distribuídos por `Company`, `Customer`, `Supplier`, `Address` e `Item` — e
nenhum deles é `br_chave_acesso`.

Consequência: `doc.get(...)` devolve `None`, a função retorna cedo, e a validação **nunca
executa**. O hook existe, o teste passa (porque o teste monta o campo), e em produção é
inerte. É o pior formato de bug: silencioso e com aparência de cobertura.

**Correção**: declarar `br_chave_acesso` (Data, 44 posições) nos quatro DocTypes.

### 1.2 `br_cfop_sugerido` nunca é criado — a sugestão é calculada e jogada fora

`integracao/cfop_sugestao` escreve `linha.br_cfop_sugerido` em cada linha de item de
`Sales Invoice`, `Purchase Invoice`, `Sales Order`, `Purchase Order`,
`Subcontracting Order` e `Subcontracting Receipt`.

**O campo não existe em nenhum DocType filho.** Os campos que `docs/cfop-sugestao.md`
descreve como "dois campos novos no Item" foram de fato criados — `finalidade_compra` e
`producao_propria` —, mas são as **entradas** do cálculo. O campo de **saída** ficou de
fora.

Atribuir atributo não declarado num `Document` do Frappe não levanta erro: some no save.
Ou seja, a sugestão é recalculada a cada `validate` e descartada toda vez.

**Correção**: declarar `br_cfop_sugerido` (Data, read-only) nos DocTypes filhos de item.

### 1.2-bis O maior de todos: a apuração de impostos lia 29 campos inexistentes

O teste genérico escrito para travar os gaps 1.1 e 1.2 **falhou de imediato apontando
mais 19 campos** — e a inspeção manual encontrou outros 10 que o próprio teste não via.

`integracao/documento.apurar_impostos` está ligado no `validate` de `Sales Invoice`,
`Delivery Note`, `Purchase Invoice` e `Purchase Receipt`. Ele lê **6 campos de cabeçalho**
e **13 por linha de item**, e grava **10 de resultado** por linha:

```text
cabeçalho  br_apurar_impostos  br_indicador_ie  br_regime_pis_cofins
           br_destinado_a_revenda  br_excluir_icms_pis_cofins  br_ano_competencia

entrada    br_aliquota_icms  br_reducao_icms  br_aliquota_ipi
(linha)    br_aliquota_ibs_uf  br_aliquota_ibs_mun  br_aliquota_cbs
           br_imposto_seletivo  br_frete  br_seguro  br_outras_despesas
           br_desconto_incondicional  br_cst_ibs_cbs  br_cclasstrib

saída      br_base_icms  br_valor_icms  br_valor_ipi  br_ipi_na_base_icms
(linha)    br_base_pis_cofins  br_valor_pis  br_valor_cofins
           br_base_ibs_cbs  br_valor_ibs  br_valor_cbs
```

**Nenhum dos 29 era criado pela instalação.** Consequência: toda alíquota lida caía em
`fracao(None)` → zero, e a apuração produzia **imposto zero em silêncio**, gravando o
resultado em campos que também não existiam. O cálculo tributário — a razão de existir do
app — era inerte de ponta a ponta.

Os campos de saída escaparam até da varredura por regex, porque são chaves de dicionário
aplicadas por `linha.set(campo, valor)`, não atribuições de atributo. O teste passou a ler
a constante `CAMPOS_RESULTADO` do próprio módulo em vez de procurar padrão no texto.

**Corrigido**: 29 definições novas em `setup/custom_fields.py` (de 56 para 202 campos, de
5 para 17 DocTypes), com os de resultado em somente leitura. E `pis_cofins.py` passou a
exportar `REGIMES_VALIDOS`, para que o Select de `br_regime_pis_cofins` grave exatamente
a chave que `_REGIMES` conhece — um rótulo bonito ("Não cumulativo") gravaria chave
inexistente e quebraria na primeira apuração.

**Trava contra regressão**: `tests/test_costura_campos_e_hooks.py`, 12 testes que cruzam
`hooks.py` × `custom_fields.py` × o que a integração lê e escreve. Foi ele que achou os
19 — e ele roda sem bench, porque as duas fontes são estruturas de dados puras.

### 1.3 Não existe caminho para emitir uma NF-e

A cadeia inteira está pronta e testada:

```text
fiscal/documento/nfe.py      montagem do XML
integracao/certificado_a1    carga do certificado A1
integracao/assinador_local   assinatura XMLDSig
integracao/transporte_sefaz  envio SOAP
integracao/autorizacao_sefaz orquestração da autorização
registros_fiscais/…          persistência do resultado
```

**Nada liga um documento do ERPNext a essa cadeia.** Os únicos métodos expostos
(`@frappe.whitelist()`) em todo o app são quatro, e nenhum emite:

- `alerta_fiscal.verificar_prontidao_efd`
- `importar_codigos.importar_classificacao_ibs_cbs`
- `importar_codigos.importar_arquivo`
- `pix.gerar_payload_pix`

Não há botão, não há `doc_events`, não há endpoint. Do ponto de vista de quem usa o
sistema, **o app ainda não emite nota** — por falta de um adaptador, não por falta de
implementação.

**Correção**: um método whitelisted `emitir_nfe(doctype, name)` que leia o documento,
monte, assine, transmita e grave o resultado no DocType `Transmissao Fiscal` que já
existe. É o menor incremento que transforma tudo o que está pronto em algo utilizável.

**Estado em 2026-09-04**: **feito**. `integracao/emissao_nfe.py` expõe
`emitir_nfe(doctype, name, transp, pag, cobr)` como `@frappe.whitelist()`, e é o primeiro
caminho pelo qual a cadeia inteira pode ser acionada num site real. Grava `Transmissao
Fiscal` em **todos** os desfechos — inclusive rejeição e denegação — antes de o erro subir
para quem clicou, porque emissão que falha sem rastro obriga o usuário a adivinhar o que a
SEFAZ respondeu.

Duas decisões que mereciam registro: o `ContextoSefaz` **não** é montado aqui (a primeira
versão o fazia; a docstring de `contexto_sefaz.py` diz que só `TransporteSefaz` monta,
porque é ele que cria e limpa os PEM temporários do TLS mútuo), e a UF e o CNPJ do envio
saem da **própria árvore** assinada, não de uma segunda leitura da `Company` — reler
abriria a hipótese de a nota ir para a SEFAZ errada se o cadastro mudasse no meio.

O mapeamento (metade anterior). `integracao/nfe_documento.py` já mapeia um
documento do ERPNext para a árvore da NF-e — endereços, emitente, destinatário, `ide`,
itens com `prod` e `imposto`, totais —, reaproveitando a mesma apuração do `validate` em
vez de reler os campos gravados. Falta o **orquestrador**: carregar certificado, assinar,
transmitir via `enviar_autorizacao` e gravar em `Transmissao Fiscal`.

Dois gaps nasceram desse trabalho e ficam declarados:

- **Controle de numeração sequencial por série.** `br_numero_nfe` existe e é lido, mas
  nada o aloca. A SEFAZ exige numeração sequencial sem lacuna por série — é problema de
  concorrência (dois usuários emitindo ao mesmo tempo), não de formato, e merece
  tratamento próprio.
- ~~**`transp` e `pag` vêm de quem chama.**~~ **Feito**:
  `integracao/transporte_pagamento.py` os deriva do documento. A distinção que guia o
  módulo é entre **derivar** (ler um fato registrado) e **adivinhar**: `modFrete="9"` não
  é "nada informado", é a afirmação de que não houve ocorrência de transporte, e por isso
  `br_modalidade_frete` **não tem padrão** — sem escolha, falha alto. `pag` cai em `90`
  (sem pagamento) apenas quando o total é zero, o único caso em que a ausência é dedutível
  do próprio documento.

  `Mode of Payment` do ERPNext é cadastro livre e `tPag` é tabela fechada de 15 códigos.
  Nome desconhecido cai em `99` (Outros), que é código **válido** — diz "houve pagamento,
  de forma que a tabela não distingue". Chutar `01` (Dinheiro) é que seria desonesto. Quem
  quer precisão preenche `br_tpag` no `Mode of Payment`.

### 1.4 Seis módulos de integração inalcançáveis

Nem citados em `hooks.py`, nem importados por outro módulo, nem expostos por
`@frappe.whitelist()`:

| Módulo | O que faz | Por que ficou solto |
|---|---|---|
| `cobranca_documento` | lê `Payment Schedule` → duplicatas da NF-e | depende de 1.3 |
| `configuracao_fiscal` | lê CSC, RNTRC, série, ambiente do eSocial | consumidor seria 1.3 |
| `cte_extracao` | extrai dados de CT-e recebido | sem gatilho de entrada |
| `ecf_dados_empresa` | dados cadastrais para a ECF | sem gerador de arquivo ECF |
| `efd_dados_cadastrais` | Bloco 0 do EFD a partir do site | sem gerador de arquivo EFD |
| `rastreabilidade` | liga `Batch` ao grupo `rastro` | depende de 1.3 |

**Atualização de 2026-09-04**: com `emitir_nfe` pronto, quatro dos seis deixaram de ser
órfãos — `cobranca_documento` e `rastreabilidade` entraram na montagem (duplicatas e grupo
`rastro`), e `configuracao_fiscal` já era usado pela série. `transporte_pagamento`, escrito
depois, virou o padrão de `transp`/`pag`. **`emitir_nfe` passou a ser chamável só com
`(doctype, name)`** — os três grupos derivam do documento, e os parâmetros continuam para
quem precise sobrescrever.

Sobram **dois**: `ecf_dados_empresa` e `efd_dados_cadastrais`.

**Atualização de 2026-09-05**: sobram **dois** — `cte_extracao` (sem gatilho de entrada
de CT-e recebido) e `ecf_dados_empresa` (sem gerador de arquivo ECF).
`integracao/geracao_efd.py` fechou a cadeia do EFD e desorfanou `efd_dados_cadastrais` e
`efd_escrituracao` de uma vez.

`contabil/efd_arquivo.py` (2026-09-04) resolveu metade do que faltava — a montagem do
arquivo EFD inteiro, do `0000` ao `9999`, existia **só dentro de um teste**. Lógica que só
vive em teste é lógica que ninguém pode usar; foi promovida a módulo, e o teste passou a
exercitá-la em vez de reimplementá-la.

O que ainda falta para desorfanar os dois é a **camada que lê o site**: produzir os blocos
C, D, E, H e K a partir de `Sales Invoice`, `Stock Ledger Entry` e afins.
`efd_dados_cadastrais` já cobre o Bloco 0; os demais não têm equivalente.

Higiene aplicada no mesmo passo: a tabela sigla→código IBGE das UFs vivia em
`fiscal/documento/inutilizacao.py`, com um comentário afirmando que a conversão "só é
necessária aqui". Deixou de ser verdade quando o `ide` passou a precisar dela — foi
extraída para `fiscal/codigos/uf.py`, e o teste usa `assertIs` (não `assertEqual`) para
garantir que existe **um** objeto, não duas cópias que hoje coincidem.

`importar_codigos` e `pix` também não estão em `hooks.py`, mas **são** alcançáveis por
whitelist — não entram nesta lista.

O padrão é claro: quatro dos seis dependem de um orquestrador que não existe (1.3), e os

**Atualização de 2026-09-15**: sobram **quatro** módulos inalcançáveis:
- `cte_extracao`: será desorfanado pelo change `fechar-laco-cte-mdfe` (MDF-e o consome)
- `ecf_dados_empresa`: depende de gerador de arquivo ECF (futuro)
- `efd_dados_cadastrais`: parcialmente desorfanado (Bloco 0 pronto; blocos C/D/E/H/K dependem de leitura de site)
- `conta_bancaria`: depende de módulo de campo livre do boleto (tropicalização bancária)
outros dois esperam um **gerador de arquivo** que junte os blocos já implementados do EFD
e da ECF num arquivo entregável. São dois adaptadores, não seis problemas.

---

## 2. Teste de bench — 26 de 31 módulos sem cobertura real

Só `party`, `party_bench`, `consumo_indevido`, `perda_estoque` e inventário têm teste
rodando contra um site real. Os outros 26 são exercitados apenas por teste puro com
objeto simulado.

Isso é exatamente o que permitiu os gaps 1.1 e 1.2 passarem: o teste puro monta o campo
que o site real não tem. **Um teste de bench que salvasse um `Sales Invoice` e relesse o
documento teria pego os dois na hora** — é a diferença entre "chama e verifica o retorno"
e "grava, relê por outro caminho e compara".

Prioridade dentro desta lista: os módulos ligados em `hooks.py`
(`validacao_fiscal`, `documento`, `cfop_sugestao`, `chave_acesso_documento`,
`alerta_fiscal`, `alerta_certificado`, `folha`), porque são os que rodam sozinhos em
produção.

---

## 3. Documentos desatualizados

### `estado-da-tropicalizacao.md`

Duas afirmações que deixaram de ser verdade:

- "O app hoje **não tem nenhum DocType próprio**" — tem três: `Transmissao Fiscal`,
  `Lote eSocial` (com filho `Evento do Lote eSocial`) e `Arquivo SPED`.
- "o app não tem `locale/` nenhum" — tem `locale/pt_BR.po`, com correções de tradução.

Também cita `br_chave_acesso` "numa Sales Invoice" como exemplo do que já funciona, o que
o gap 1.1 desmente.

### `sped-fiscal.md`

A lista "Ainda por implementar" citava "Blocos D, K, 1" — D e K foram implementados nos
commits `04a9fda` e `a62c956`. Atualizado nos próprios commits; registrado aqui porque a
lição vale: **lista de pendências envelhece e precisa de varredura periódica**, que é o
que este documento passa a ser.

---

## 4. Fontes a reconferir

### 4.1 A tabela de CFOP do CONFAZ chamada "vigente" não está vigente

`confaz.fazenda.gov.br/legislacao/ajustes/sinief/cfop_cvsn_70_vigente` foi baixada e lida
localmente. **Todas as redações nela terminam em `31.05.22`** ("efeitos de … a 31.05.22").
Existem o Ajuste SINIEF 03/22 (efeitos a partir de 01.06.22) e o Ajuste SINIEF 03/24, e a
própria busca devolveu páginas irmãs (`cfop_cvsn_70_vigente_nova`,
`cfop_cvsn70_vigente_01-06-22_31-03.24`) sugerindo que a numeração de versões está
espalhada por várias URLs.

Descrição oficial de CFOP era a fonte para o gap 5.1 abaixo. **Não usada** — a página com
"vigente" no nome não sustenta a afirmação.

### 4.2 QR Code da NFC-e versão 3 (NT 2025.001)

Já registrado em `docs/nfce-qrcode.md` como pendente com fonte inacessível. Continua.

---

## 5. Gaps de domínio ainda abertos

### 5.1 Natureza da operação — existe no domínio, não existe na tela

- ✅ `natOp` é obrigatório e validado contra vazio em `fiscal/documento/nfe.py` e
  `fiscal/cte.py`; é corrigível por CC-e; e está **confirmado ausente** no MDF-e, com
  teste (`assertNotIn("natOp", grupo)`), porque manifesto não é operação tributável.
- ❌ **Não há campo de natureza da operação em nenhum DocType** — mesmo problema de
  família do gap 1.2: o valor tem de vir de algum lugar e não vem.
- ✅ `natOp` **valida o limite de 60 caracteres** do XSD oficial (`leiauteNFe_v4.00.xsd`: `TString`,
  `minLength 1`, `maxLength 60`) em `fiscal/documento/nfe.py` (`_natureza`) — conferido em 2026-10-09; a linha
  anterior dizia que faltava.
- ❌ Não há sugestão de natureza a partir do CFOP, apesar de `cfop_sugestao.py` já
  determinar o CFOP — e a descrição oficial de cada CFOP depende da fonte do gap 4.1.

### 5.2 Transferência entre estabelecimentos não emite NF-e

- CFOP 5152/6152 é fato gerador; `Stock Entry` com `purpose = "Material Transfer"` não
  dispara emissão.
- **Bloqueio**: decisão de modelagem — estabelecimento com CNPJ próprio é `Company`
  separada ou `Warehouse` com CNPJ? A resposta muda o que é "transferência".

### 5.3 Estorno apurado não vira lançamento na EFD

- Valor fica no documento; falta o ajuste no E111 do Bloco E.
- Listado em `sped-fiscal.md` como pendente.

### 5.4 Quebra tolerada por UF não implementada

- Percentual varia por estado e por produto; fonte única não encontrada.
- Inventar número seria criar regra fiscal sem base.

### 5.5 NFC-e não sai do POS do ERPNext

- `POS Invoice` não recebe campo fiscal nenhum.
- Depende do change `emitir-nfce-do-pos` (6/30 tasks).

### 5.2 Os 69 itens declarados em `docs/`

Distribuição por documento (excluídos os já riscados como feitos):

| Documento | Itens | Documento | Itens |
|---|---|---|---|
| `sped-fiscal.md` | 7 | `rh-esocial-s1000.md` | 4 |
| `pcp-estado.md` | 6 | `rh-integracao-salary-slip.md` | 4 |
| `rh-irrf.md` | 6 | `pix.md` | 3 |
| `boleto.md` | 5 | `plano-de-contas.md` | 3 |
| `cte-icms-uf-fim.md` | 5 | `precificacao-custos-rastreabilidade.md` | 3 |
| `rh-esocial-s1200.md` | 5 | `sped-texto.md` | 3 |
| `rh-inss.md` | 5 | `apuracao-periodica.md` | 2 |
| `lancamentos-contabeis.md` | 4 | demais (5 docs) | 1 cada |

Alguns já estão obsoletos (`rh-inss.md` e `rh-irrf.md` listam itens marcados como
"feito, ver …" dentro da própria lista de pendências). Uma limpeza dessas listas é
trabalho de meia hora e devolve confiança ao levantamento.

### 5.3 Tropicalização de outros apps do ecossistema

Registrado em memória (`backlog-modulo-hospitalar`): Healthcare, CRM, HRMS, Payments e os
demais. Nenhum investigado. **Retomar só com sinal explícito** — não entra em nenhuma
priorização automática.

---

## Ordem sugerida

A ordem não é por tamanho, é por **quanto cada item destrava do que já está pronto**:

1. ~~**1.1, 1.2 e 1.2-bis**~~ — **feito**. 31 campos criados; três hooks já ligados
   deixaram de ser inertes, incluindo a apuração de impostos inteira.
2. ~~**1.3** — o método `emitir_nfe`~~ — **feito**. Chamável só com `(doctype, name)`;
   destravou quatro dos seis órfãos.
3. ~~**Gerador de arquivo EFD**~~ — **feito** (`contabil/efd_arquivo.py`). A montagem
   vivia só dentro de um teste.
4. ~~**5.1** — `natOp`~~ — **feito**: limite de 60 verificado nos XSD da NF-e **e** do
   CT-e, campo no DocType e sugestão por CFOP.
5. ~~Limpeza do `estado-da-tropicalizacao.md`~~ — **feito**: dizia que o app não tinha
   DocType próprio (tem cinco) nem `locale/` (tem). Documento de estado envelhece mais
   rápido que código, e mapa errado é pior que mapa nenhum.

### O que sobrou, em ordem

1. ~~**Interface do usuário — painel**~~ — **feito, e o inventário estava desatualizado.**
   Conferido em 2026-09-07: `fiscal/documento/situacao_fiscal.py` +
   `integracao/situacao_fiscal.py` existem e o painel está ligado em `emissao_nfe.js`,
   que o chama por `frappe.call`.

   ⚠️ Registro de método: este item ficou escrito como pendente **depois de pronto**. É o
   mesmo defeito que o item 5 da lista acima já apontava — "documento de estado envelhece
   mais rápido que código, e mapa errado é pior que mapa nenhum" —, agora acontecido
   dentro do próprio inventário de gaps. Conferir antes de trabalhar evitou construir de
   novo o que já existia.

   O que de fato sobra é **alcance**: o painel vive no `Sales Invoice`, a tela onde a NF-e
   é emitida. Levá-lo a `Delivery Note` e `Purchase Invoice` é decisão de produto, não
   lacuna de costura.

2. **Teste de bench dos módulos ligados em `hooks.py`** — em andamento. O bench já achou
   bugs reais que a suíte pura não via: controller ausente, nome de classe que fazia o
   Frappe apagar o DocType em silêncio, o patch de renome inerte, o retorno GS1 sem
   `has_batch_no` e o campo obrigatório que impedia gravar o bloqueio.

   **Coberto até aqui** (`tests_bench/`): `certificado_a1`, `party` e, desde 2026-09-07,
   `consumo_indevido` — sete testes que gravam por um caminho e releem por outro,
   confirmando o `autoname` de chave única, a derivação de `liberado_em` pelo controller,
   a independência entre ambientes e o vencimento automático da janela.

   **`perda_estoque` também entrou** (`tests_bench/test_perda_estoque.py`, cinco casos): a
   recusa de perda em transferência prova que o hook está ligado através do framework, e os
   demais cobrem gravação e releitura por caminho independente.

   **A recusa de sobra de inventário também entrou** — e com saldo real, não com
   `difference_amount` forçado: o teste dá entrada de 10 unidades por um `Stock Entry`
   submetido e conta 15 no `Stock Reconciliation`, deixando o **ERPNext** calcular a
   diferença positiva. Forçar o valor provaria a nossa função e não a integração, que é o
   que estes testes existem para provar.
3. **Camada que lê o site para o bloco D.** C, E, H e K ficaram prontos em 2026-09-05
   (`efd_escrituracao`, `efd_apuracao`, `efd_inventario`, `efd_producao`). O **D**
   continua aberto por motivo estrutural, não por falta de tempo: **nenhum DocType do
   ERPNext guarda documento de transporte**, então não há o que ler. Enquanto isso,
   `geracao_efd` declara o arquivo como parcial no retorno e na docstring.
4. ~~**Acionar cancelamento e CC-e**~~ — **feito** em 2026-09-05
   (`integracao/eventos_nfe.py` mais os dois botões em `emissao_nfe.js`). Era o mesmo
   gap da emissão do outro lado: cadeia completa, testada, e inalcançável de uma tela.
   Ver [cancelamento-e-carta-de-correcao.md](cancelamento-e-carta-de-correcao.md).
   **Um DocType próprio para eventos segue não sendo necessário**: `Transmissao Fiscal`
   já distingue por `tipo`, e criar outro duplicaria o mesmo registro.
5. **Transmissão exercitada contra a SEFAZ de verdade**, que depende de certificado A1
   real em homologação.

## Varredura de 2026-09-06 — o que a costura mostra hoje

Refeita pelo método da seção seguinte, depois de nove incrementos. O que mudou de figura:

### ✅ Os campos não têm mais buraco

**Zero** campos `br_` usados pela integração e não declarados em `setup/`. O gap 1.2-bis,
que foi o maior de todos, está travado por teste e permaneceu fechado ao longo de todos os
módulos novos.

### Primeira validação em bench real — 2026-09-06

O bench subiu (`~/frappe-bench`, v15, site `erpnext-brasil.localhost`) e o `bench migrate`
rodou com o código atual. Três resultados, e o terceiro é o que justifica tudo.

### ✅ O que passou

- **Os 15 módulos novos importam** num site real: nenhum `ImportError`, nenhum nome de
  classe errado, nenhuma dependência quebrada.
- **O índice composto foi criado**: `documento_tipo_documento_index` sobre
  `(documento_tipo, documento)` em `Transmissao Fiscal` — a otimização não era teórica.
- **`Finance Book` "Fiscal (Brasil)" e os três `Asset Shift Factor`** nasceram no
  `after_migrate`, como projetado.
- **`Salary Component` ficou com zero campos** — e isso é o comportamento correto: o `hrms`
  não estava instalado, e o filtro de DocType ausente funcionou.

### 🔴 O bug que só o bench mostrou

O patch de renome para o prefixo `br_` era **bem-formado, tinha seis testes verdes, e não
fazia nada**. O bench imprimiu 65 vezes:

```text
rename_field: br_inscricao_estadual not found in Company
```

A causa é de **ordem**, e vem de uma suposição sobre o que `rename_field` faz: ele **não
renomeia coluna** — faz `UPDATE tabX SET novo = antigo`, e pressupõe as duas existindo. Só
que os patches rodam **antes** do `after_migrate`, que é quem cria os campos. O patch
desistia com um aviso, e o `after_migrate` logo depois criava a coluna nova **vazia**.

Nada quebraria. O cadastro é que apareceria em branco.

Corrigido para **criar, copiar, remover**, e **provado no bench**: com `ncm='84713019'`
semeado na coluna antiga, depois do migrate o valor está em `br_ncm` e o `Custom Field`
antigo sumiu.

### O que isto diz sobre a suíte

2651 testes não pegaram um patch inerte, e não é falha deles: eles medem o que o código
**declara**, e o patch declarava certo. O que faltava era a **ordem em que o Frappe executa
as coisas** — que não está no nosso código, e por isso só aparece rodando.

É a mesma família dos 31 campos: declaração correta, efeito nenhum.

### ⚠️ O que ainda não foi exercitado

Nenhuma transmissão — SEFAZ e eSocial seguem sem nunca terem falado com o Fisco, o que
exige certificado A1 real. E o bench v16 (`~/frappe-bench-16`) tem o código, mas **o site
nunca foi criado**: o banco `_a78420228ee6f61e` não existe, e a criação falha por acesso
negado do root do MariaDB.

## ~~🔴 Eventos do CT-e com a forma do evento da NF-e~~ — pago em 2026-10-09

Achado na tarefa 3.4 de `fechar-laco-cte-mdfe`, ao escrever o envio. `eventoCTe_v4.00.xsd`
declara a raiz `eventoCTe` (`<xs:element name="eventoCTe" type="TEvento">`) e `detEvento` como
`xs:any` — o XML específico do evento (`evCancCTe`, `evCCeCTe`…) vai **dentro** dele. Os
montadores de `fiscal/documento/evento_cte.py` devolviam raiz `evento` (nome da NF-e) e os campos
soltos em `detEvento`; a SEFAZ recusaria o documento. `sped-cte` (`Tools::sefazEvento`) monta
a mesma forma que o XSD.

### ✅ Implementado

Os **11** montadores passam por `_evento_cte(inf_evento, elemento)`, que devolve a raiz `eventoCTe`
e acomoda os campos no elemento-raiz do XSD do evento (nomes lidos um a um nos XSDs do `sped-cte`):
`evCancCTe`, `evCCeCTe`, `evCECTe`, `evCancCECTe`, `evIECTe`, `evCancIECTe`, `evEPECCTe`, `evGTV`,
`evPrestDesacordo`, `evCancPrestDesacordo` e `evRegMultimodal`. `assinar_evento_cte` assina a nova
raiz. `tests/test_evento_cte.py::TestFormaDoEventoCte` trava a raiz e o elemento de cada um.

### O que ficou de fora

- **Só cancelamento e CC-e têm envio** (`eventos_cte.py`). Os outros nove existem como montagem
  pura e correta, sem adaptador Frappe nem botão.
- `montar_env_evento_cte` modela um lote `envEvento` que o CT-e não usa (o `eventoCTe` vai direto);
  ficou tolerante às duas raízes, sem uso real.
- O cabeçalho SOAP `cteCabecMsg` do evento foi copiado da autorização por analogia; confirmar em
  homologação junto com a 3.1.
- A ordem dos filhos dentro de cada `ev*` não foi reconferida montador a montador nesta passagem; os
  testes por evento seguem como estavam.

## 🟡 Fonte de tempo (NTP.br): o que a mudança `fonte-de-tempo-ntp-br` deixa de fora — 2026-10-09

Medição, alerta, guarda de emissão (NF-e e CT-e) e correção opcional do `dhEmi` estão implementados e
testados (`docs/fonte-de-tempo.md`). Ficam:

- 🔴 **Limites padrão sem fonte oficial.** Aviso a partir de 1 s e crítico a partir de 60 s são escolha
  de engenharia; a tolerância de `dhEmi` está no MOC e não foi verificada. A guarda nasce **ligada**, e
  só deve ficar assim depois da calibração (tarefa 6.2 da mudança). Resolve: ler o MOC e ajustar os
  padrões em `fiscal/relogio_politica.py`.
- 🟡 **Guarda no MDF-e e na NFC-e.** A função é a mesma; falta o ponto de emissão existir
  (`fechar-laco-cte-mdfe` 5.2 e `emitir-nfce-do-pos` 4.3a, já anotados lá).
- 🟡 **SNTP sem autenticação.** O app não faz NTS; a defesa é o consenso entre fontes. Se a ameaça de
  forjamento no caminho for relevante, é mudança à parte (cliente NTS-KE).
- 🟡 **Política de uso dos servidores `.st1`** para clientes de aplicação não é publicada; a medição é
  horária por cautela. Confirmar com o NIC.br.
- 🟡 **Servidor NTP próprio do Observatório Nacional** não confirmado (a página da Hora Legal
  consultada devolveu 404).
- 🟡 **Sem prova em PostgreSQL** do cache e do campo novo do `Transmissao Fiscal`.

## Método
s expostos e quem os chama

| Método | Botão |
|---|---|
| `emissao_nfe.emitir_nfe` | ✅ |
| `eventos_nfe.cancelar_nfe` | ✅ |
| `eventos_nfe.enviar_carta_correcao` | ✅ |
| `situacao_fiscal.situacao_fiscal` | ✅ |
| `geracao_efd.gerar_efd` | ✅ |
| `entrada_nfe.importar_nfe` | ✅ — **feito nesta varredura** |
| `alerta_fiscal.verificar_prontidao_efd` | — chamado pela tela de EFD |
| `pix.gerar_payload_pix` | — API, sem tela própria |
| `importar_codigos.importar_arquivo` | — utilitário de carga |
| `importar_codigos.importar_classificacao_ibs_cbs` | — idem |

O `importar_nfe` estava exposto e **sem botão nenhum** — o mesmo formato de gap que a
emissão teve, e criado dois commits antes. Achado por varredura, não por alguém tentar usar.

### ⚠️ Cinco módulos de integração sem chamador em produção

Contados **fora** do próprio arquivo — a primeira tentativa desta varredura contava o
próprio módulo e produziu 20 falsos positivos, o que vale registrar: heurística mal calibrada
produz um inventário que ninguém confia.

| Módulo | Situação |
|---|---|
| `conta_bancaria` | **órfão declarado** — espera o montador de campo livre do boleto, específico por banco ([tropicalizacao-por-area.md](tropicalizacao-por-area.md)) |
| `cte_extracao` | o CT-e tem domínio e mapeamento, e nenhuma orquestração ligada |
| `ecf_dados_empresa` | a ECF monta blocos e não tem gerador de arquivo ligado |
| ~~`assinador_esocial`~~ | ✅ pago — `TransporteEsocial` o usa |
| ~~`transmissao_esocial`~~ | ✅ pago — ver abaixo |

Os dois últimos diziam, juntos, o que a NF-e dizia antes de `emissao_nfe.py`: **o eSocial
não era acionável de um site**. A causa era estrutural, não esquecimento — `ContextoEsocial`
exige os arquivos PEM do TLS mútuo, e o **único** `ContextoEsocial(...)` do repositório
estava num arquivo de teste.

Pago por `integracao/transporte_esocial.py` (monta o contexto, dono do certificado) e
`integracao/transmissao_lote_esocial.py` (dois métodos whitelisted: transmitir e
reconsultar). O ciclo de vida dos PEM, que vivia dentro do `TransporteSefaz`, foi extraído
para `tls_certificado.ArquivosTls` — a alternativa era **copiar a escrita de uma chave
privada em disco**, que é o que `contexto_sefaz.py` proíbe.

⚠️ **Falta o botão**, e faltava mais do que isso. Ao procurar quem montaria o lote,
apareceu um buraco maior: **o S-1200 não tinha montador de árvore**. O S-1000 tinha
`montar_evento_s1000` desde o início; o evento da folha — o mais transmitido de todos — só
tinha as dataclasses. Dava para validar cada grupo e não dava para produzir o evento.

`montar_evento_s1200` fechou isso, e `integracao/folha_esocial.py` fechou a ponte com o
`Salary Slip` — inclusive os campos que faltavam em `Employee` (CPF, NIS, categoria, CBO,
lotação) e em `Salary Component` (código da rubrica).

✅ **A cadeia fechou** em 2026-09-06. `integracao/montagem_lote_esocial.py` compõe as peças
— holerite → S-1200 → evento assinado → lote —, e três telas a acionam:

| Onde | O quê |
|---|---|
| lista de `Salary Slip` | **Montar Lote eSocial** a partir da seleção |
| formulário do `Lote eSocial` | **Transmitir ao eSocial** |
| idem, com protocolo | **Consultar processamento** |

Transmitir e consultar são botões separados, e um exclui o outro: com protocolo, o lote já
foi recebido, e **reenviar duplicaria os eventos**.

O que falta agora é de outra ordem: **exercitar contra o ambiente de produção restrita**, que
exige certificado A1 real. Nenhum dos módulos do eSocial foi executado fora de teste.

### O que não mudou

- **28 dos 31 módulos seguem sem teste de bench.** A execução real continua não exercitada:
  as suítes novas são de costura estática (campo gravado × campo declarado, ordem dos
  efeitos, superfície exposta). O bench existe e sobe (`scripts/subir.sh`), mas não foi
  alcançável na sessão desta varredura.

## Varredura da frente de Estoque — 2026-09-06

### 🔴 O gap que o inventário não tinha: `contabil/perdas.py` inalcançável

`contabil/perdas.py` existia com o cálculo completo do estorno de crédito, testado, e
**nenhum módulo de `integracao/` o importava**. A única citação em todo o app era uma
docstring do Bloco K — e citação em docstring não torna código alcançável.

⚠️ **Isto não estava nesta lista.** O gap foi encontrado pela varredura *por área de
produto* (cruzar a página oficial do ERPNext com o que o app tem), não pela varredura de
costura que produziu as seções 1.1 a 1.4. Os dois métodos encontram coisas diferentes e não
se substituem: a de costura pergunta "o campo que este código escreve existe?"; a de área
pergunta "o que o produto oferece aqui, e nós cobrimos?".

**Pago no mesmo dia:** `integracao/perda_estoque.py` + `setup/campos_estoque.py`, ligados a
`Stock Entry` e `Stock Reconciliation` em `hooks.py`. Detalhado em `estoque-estado.md`.

### Gaps novos, declarados

1. **Transferência entre estabelecimentos não emite NF-e.** Mover mercadoria entre CNPJ
   diferentes da mesma empresa é fato gerador (CFOP 5152/6152); no ERPNext é um
   `Stock Entry` com `purpose = "Material Transfer"`, e a emissão deste app está ligada a
   `Sales Invoice`, `Delivery Note`, `Purchase Invoice` e `Purchase Receipt` — **não a
   `Stock Entry`**. A transferência acontece e nenhum documento fiscal nasce.

   Bloqueado por decisão de modelagem, não por código: estabelecimento com CNPJ próprio é
   `Company` separada ou `Warehouse` com CNPJ? A resposta muda o que é "transferência" e o
   que é "venda entre empresas".

2. **O estorno apurado não vira lançamento na EFD.** O valor fica no documento; o registro
   é ajuste de apuração no `E111` do Bloco E, já listado em `sped-fiscal.md`.

3. **Percentual de quebra tolerada por UF.** Não implementado por falta de fonte única —
   varia por estado e por produto, e inventar o número seria criar regra fiscal sem base.

### O que a varredura confirmou como já pronto

`Item` com NCM/CEST/origem, rastreabilidade de lote traduzida para o grupo `rastro` da NF-e,
Bloco H (inventário, inclusive item em poder de terceiro) e Bloco K. Cinco dos oito recursos
anunciados pelo ERPNext são fiscalmente neutros.

## ~~🔴 Consumo indevido da SEFAZ~~ — pago em 2026-09-07

Encontrado em 2026-09-07, cruzando o app com uma lista de conceitos de arquitetura backend.
Busca por `consumo indevido`, `656`, `rate limit`, `throttle` e `backoff` em todo o código e
em `docs/`: **nenhuma ocorrência**. O app transmite para a SEFAZ sem controle de cadência.

### A regra, verificada em fonte oficial

`cStat 656 — Consumo indevido pelo aplicativo da empresa` **bloqueia o CNPJ por uma hora**,
com desbloqueio automático. O gatilho típico é reconsultar depois de um `cStat 137` sem
esperar o intervalo.

⚠️ **A armadilha que torna isto grave**, e é o que muda o desenho: *"se retomar a consulta
antes de completar 1 (uma) hora, o tempo é zerado e a contagem reiniciará"*.

Ou seja: **um laço de retentativa mantém a empresa bloqueada indefinidamente**, e cada
tentativa piora a situação. É o caso raro em que a reação instintiva a um erro de
transmissão — tentar de novo — é a pior ação possível. Nada no código diz isso hoje.

### Por que a fila não resolve sozinha

`integracao/fila_fiscal.py` protege contra **duplicidade** (`job_id` determinístico +
`deduplicate`), que é outro problema. Ela não impõe **cadência**. E há um risco embutido:
`frappe.enqueue` não repete sozinho hoje, mas quem acrescentar `retry` a um job de
transmissão — coisa razoável de se querer — cria o bloqueio permanente sem perceber.

### ✅ Implementado

`fiscal/consumo_indevido.py` (a regra de tempo, pura) + `integracao/consumo_indevido.py` (a
guarda e o registro) + DocType `Bloqueio Sefaz`, ligados no **ponto único** `_contexto` do
`TransporteSefaz` — por onde as cinco operações passam antes da rede.

A guarda levanta `BloqueadoPorConsumoIndevido` com o horário de liberação e a instrução
explícita de **não insistir**. Detalhado em
[consumo-indevido.md](consumo-indevido.md).

⚠️ **A primeira versão causou uma regressão que a suíte pegou**: importar o módulo no topo
de `transporte_sefaz.py` derrubou 25 testes, porque aquele adaptador é livre de `frappe` de
propósito. Corrigido por injeção — e o desenho ficou melhor, com a dependência explícita no
construtor em vez de escondida num import.

### O que ficou de fora

**Nada — e a primeira redação desta seção errava.** Dizia que faltava cobrir CT-e e MDF-e,
o que sugere transmissão desguarnecida. Conferido: eles **não transmitem** ainda (há URLs
de autorizador e leiaute puro, nenhum caminho de envio). O risco é o futuro, e está coberto
por teste: a suíte varre todo `integracao/` procurando construções de `TransporteSefaz` e
exige `guarda` em cada uma.

### Fontes

- Portal da NF-e — Notas Técnicas e MOC do documento correspondente.
- SEFAZ-ES, comunicado sobre controle automático de consumo indevido: bloqueio de 1 hora,
  desbloqueio automático, e a contagem que reinicia a cada tentativa antecipada.

## Contrato com o ERPNext — 2026-09-09

Achado ao **medir** a tropicalização, e não ao procurar bug: o contato do app com o ERPNext
tinha quatro formas, e só três se declaravam.

| Forma | Declarada em | DocTypes |
|---|---|---|
| campo acrescentado | `setup/campos*.py` | 24 |
| comportamento ligado | `hooks.py` | 17 |
| DocType próprio | `registros_fiscais/doctype/` | 6 |
| **leitura** | ~~lugar nenhum~~ → `setup/leituras_do_erpnext.py` | **13** |

### ✅ As 13 leituras, pagas no mesmo dia

Campo e hook são coisas **nossas**, que mudam quando nós mudamos. Leitura é dependência de
estrutura **alheia** — muda quando o ERPNext muda, e nada acusava.

O caso mais grave: o Bloco K da EFD é montado a partir de `Work Order`, e o módulo
`manufacturing` **existe no app só por essa leitura** — nenhum campo, nenhum hook. Renome de
`actual_start_date` = arquivo entregue ao Fisco errado, com a suíte pura verde. Mesma
exposição em `Stock Ledger Entry` (Bloco H), `Batch` (grupo `rastro`) e `Dynamic Link` (a
ligação que revela a UF, e a UF decide CFOP e alíquota).

Agora há duas conferências: uma pura, que reprova leitura nova sem declaração; e uma de
bench, que confere DocType e coluna num site real — a única coisa no projeto que pega um
renome do ERPNext, e pega na atualização em vez de na entrega.

⚠️ Nota de método: a varredura manual achou **onze**; o teste achou **treze**. `Dynamic Link`
e `Has Role` escaparam porque a varredura procurava numa lista que ela mesma montou.

### ✅ O mapa de indicador tinha uma entrada inalcançável

`INDICADOR_POR_DOCUMENTO` mapeava `POS Invoice` para `indNFCe`, e a função **nunca recebe um
`POS Invoice`** — ele não está no `hooks.py`. Entrada inalcançável dentro de estrutura viva é
pior que ausência: dá a impressão de que o caso está coberto.

Separada em `INDICADOR_QUANDO_LIGARMOS`, que é o que ela de fato é: decisão registrada para
quando o gap for pago.

O perigo maior era o inverso, e agora tem teste: a leitura usa `.get(doctype, "indNFe")`, e
um DocType **ligado e ausente do mapa** cairia em nota modelo 55 sem erro. Para um cupom,
isso faz a combinação CST/cClassTrib passar pela tabela errada — aprovada aqui, rejeitada
pela SEFAZ.

### 🔴 Gap novo: NFC-e não sai do POS do ERPNext

`POS Invoice` é o documento de ponto de venda do ERPNext e **não recebe campo fiscal
nenhum**. A NFC-e do app é emitida a partir de `Sales Invoice` com modelo 65.

Consequência: quem usa o **POS do ERPNext** não emite NFC-e. Não é lacuna de cálculo — o
modelo 65 está pronto na camada pura (chave de acesso, autorizadores, QR Code) —, é lacuna
de **costura**: falta o conjunto de campos, o hook e o botão nessa tela.

Não foi feito agora porque é frente própria: o POS tem fluxo de caixa, contingência offline
(que a NFC-e admite e a NF-e não) e impressão de cupom. Tratá-lo de passagem produziria meia
emissão.

### O que a medição também mostrou, e não é gap

- **30 de 534 DocTypes tocados (5,6%)**, e **15 dos 21 módulos sem contato nenhum**. Não é
  lacuna: CRM, Projects, Support e afins não têm consequência fiscal. A tropicalização é
  estreita e profunda.
- **`stock` + `accounts` = 71% dos campos.**
- **Os mesmos 30 campos de linha em 4 tabelas-filhas e 16 de cabeçalho em 4 documentos** —
  mas o código **não duplica**: `campos_documento.py` gera os quatro num laço só. Quem
  replica é o modelo do ERPNext, que separa por papel comercial onde o fisco separa por
  modelo de documento.

## PostgreSQL — 2026-09-17

Segundo banco provado (`v16pg.localhost`): `new-site`, `install-app` de erpnext, erpnext_brasil
e hrms, `migrate`, índice e campos conferidos. Dois bugs **do Frappe** em Postgres foram
corrigidos em patches (`contrib/frappe/`) e um contorno ficou no `install.py` enquanto os PRs
não entram; a única consulta SQL crua do app foi reescrita e ganhou teste de bench
(`tests_bench/test_efd_inventario.py` — `efd_inventario` sai da lista de módulos sem
cobertura real). Gaps que ficam declarados: **CI continua sem bench** (nem MariaDB nem
Postgres); **`docker-compose.yml` continua só MariaDB**; **os PRs ao Frappe ainda não foram
abertos**. Detalhe em [postgresql.md](postgresql.md).

## Método


Para reproduzir esta varredura:

- **Costura**: cruzar `hooks.py` × `setup/custom_fields.py` × grafo de importação, e
  conferir se todo `doc.get("br_…")` e todo `linha.br_… =` tem campo declarado.
- **Alcançabilidade**: um módulo de `integracao/` é alcançável se aparece em `hooks.py`,
  é importado por outro módulo, ou tem `@frappe.whitelist()`. Nenhum dos três é órfão.
- **Pendências declaradas**: extrair bullets sob cabeçalhos "Ainda por implementar",
  "Fora de escopo", "Pendências", "O que falta", ignorando linhas com `~~`.
