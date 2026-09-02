# MDF-e: `emit`, `seg` (seguro) e `prodPred` (produto predominante)

Fecha os três últimos grupos de `infMDFe` verificados no levantamento (`emit`/`seg`/`prodPred`
— só `infModal` fica de fora, já coberto por `fiscal/mdfe_rodoviario.py` como conteúdo, mas sem
um ponto de injeção automática no `montar_ide`, ver `docs/mdfe-orquestracao.md`).

## `emit` — achado real: aceita CNPJ ou CPF

Diferente do emitente da NF-e (sempre CNPJ, pessoa jurídica), o `emit` do MDF-e aceita **CNPJ
ou CPF** — o próprio XSD documenta a série 920-969 como reservada a "emitente pessoa física com
inscrição estadual", cobrindo o transportador autônomo (TAC). `montar_emit` reusa
`validar_cpf_cnpj`, a mesma escolha exclusiva já usada em `fiscal.cte.montar_toma4`.
`enderEmit` é obrigatório no XSD (sem `minOccurs="0"`) — mesma disciplina do `enderToma` do
CT-e (`docs/cte-toma.md`): validado, não silenciosamente omitido.

## `seg` — seguro da carga, opcional e repetível

Cada item de `seg` tem `respSeg` (`1`-emitente do MDF-e / `2`-contratante do transporte,
confirmado obrigatório só a partir da Lei 11.442/07 para o modal rodoviário), CNPJ/CPF do
responsável (só relevante quando `respSeg == "2"` — o XSD marca como obrigatório nesse caso,
mas `montar_seg` deixa opcional e o chamador decide, já que a obrigatoriedade condicional por
outro campo do mesmo grupo exigiria uma validação cruzada não implementada ainda), dados da
seguradora, apólice e lista de averbações — tudo opcional dentro do item.

## `prodPred` — 12 categorias de carga, Resolução ANTT 5.849/2019

`tpCarga` tem 12 valores confirmados (granel sólido/líquido, frigorificada, conteinerizada,
carga geral, neogranel, e as cinco variantes "perigosa" das anteriores, mais granel
pressurizada). `xProd` é a descrição do item de maior valor financeiro. `cEAN`/`NCM` são
opcionais. `infLotacao` (carga lotação com localização de carregamento, estrutura aninhada mais
rara) não foi implementado — fora de escopo deste incremento.

## Arquivos

- `erpnext_brasil/fiscal/mdfe.py` — `Emitente`, `montar_emit`, `Seguro`, `montar_seg`,
  `montar_prod_pred`, mais as constantes `RESPONSAVEL_SEGURO_*` e `TIPO_CARGA_*`.
- `erpnext_brasil/tests/test_mdfe.py` — `TestMontarEmit`, `TestMontarSeg`, `TestMontarProdPred`
  (13 testes).

## Fontes

- `github.com/nfephp-org/sped-mdfe`, `schemes/PL_MDFe_300b/mdfeTiposBasico_v3.00.xsd`, grupos
  `emit` (linhas 233–293), `seg` (linhas 760–862) e `prodPred` (linhas 863–938) do arquivo
  baixado em 2026-08-31. Ver `docs/mdfe-estado.md` para o histórico da investigação.
