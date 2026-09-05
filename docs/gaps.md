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
| Módulos de integração sem teste de bench | 28 de 31 |
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

`importar_codigos` e `pix` também não estão em `hooks.py`, mas **são** alcançáveis por
whitelist — não entram nesta lista.

O padrão é claro: quatro dos seis dependem de um orquestrador que não existe (1.3), e os
outros dois esperam um **gerador de arquivo** que junte os blocos já implementados do EFD
e da ECF num arquivo entregável. São dois adaptadores, não seis problemas.

---

## 2. Teste de bench — 28 de 31 módulos sem cobertura real

Só `party`, `party_bench` e um terceiro módulo têm teste rodando contra um site real. Os
outros 28 são exercitados apenas por teste puro com objeto simulado.

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
- ❌ `natOp` **não valida o limite de 60 caracteres** que o XSD oficial declara
  (`leiauteNFe_v4.00.xsd`: `TString`, `minLength 1`, `maxLength 60`, lido localmente).
  Uma natureza longa demais passa na montagem e é recusada pela SEFAZ. O projeto já tem
  precedente de validar tamanho (`JUSTIFICATIVA_CONTINGENCIA_MAXIMA`).
- ❌ Não há sugestão de natureza a partir do CFOP, apesar de `cfop_sugestao.py` já
  determinar o CFOP — e a descrição oficial de cada CFOP depende da fonte do gap 4.1.

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
2. **1.3** — o método `emitir_nfe`. Destrava a cadeia inteira de emissão e, de quebra,
   quatro dos seis módulos órfãos.
3. **Teste de bench dos sete módulos ligados em `hooks.py`** — para que a classe de erro
   dos itens 1.1/1.2 não volte a passar despercebida.
4. **Gerador de arquivo EFD/ECF** — junta blocos já implementados (0, C, D, E, H, K, 9) e
   destrava os dois módulos órfãos restantes.
5. **5.1** — limite de 60 caracteres do `natOp` (barato e verificado) e o campo de
   natureza da operação; a sugestão automática fica bloqueada pelo gap 4.1.
6. Limpeza das listas de pendência e do `estado-da-tropicalizacao.md`.

## Método

Para reproduzir esta varredura:

- **Costura**: cruzar `hooks.py` × `setup/custom_fields.py` × grafo de importação, e
  conferir se todo `doc.get("br_…")` e todo `linha.br_… =` tem campo declarado.
- **Alcançabilidade**: um módulo de `integracao/` é alcançável se aparece em `hooks.py`,
  é importado por outro módulo, ou tem `@frappe.whitelist()`. Nenhum dos três é órfão.
- **Pendências declaradas**: extrair bullets sob cabeçalhos "Ainda por implementar",
  "Fora de escopo", "Pendências", "O que falta", ignorando linhas com `~~`.
