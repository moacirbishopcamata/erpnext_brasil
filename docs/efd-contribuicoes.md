# EFD-Contribuições: Bloco M — apuração de PIS/Cofins

Item citado como fora de escopo desde as primeiras sessões deste projeto. Cobre só
o Bloco M — os registros de apuração final (M200/M210 para PIS/Pasep, M600/M610
para Cofins), não os blocos A/C/D/F que consolidam por item/documento, mesma
disciplina de `efd_icms_ipi.py` não modelar C/H, só E110/E520.

## PIS e Cofins têm o mesmo layout — confirmado, não presumido

Diferente de "semelhanças" que se revelaram falsas neste projeto (S-2200 × S-1200
no bloco eSocial, por exemplo), aqui a fonte confirma a igualdade: a documentação
do M600 cita "Campos 02 e 09", os mesmos números de campo do M200; M610 tem a
mesma estrutura do M210, trocando só o sufixo `_PIS`/`ALIQ_PIS`/`ALIQ_PIS_QUANT`
por `_COFINS`/`ALIQ_COFINS`/`ALIQ_COFINS_QUANT`. Por isso
`DetalhamentoContribuicao`/`ConsolidacaoContribuicao` são compartilhadas entre os
dois pares de função (`montar_m210`/`montar_m610`, `montar_m200`/`montar_m600`) —
reúso genuíno confirmado pela fonte, não coincidência de nome.

## Layout vigente: fatos geradores a partir de 01/01/2019

M210/M610 têm uma versão anterior (até 31/12/2018) com ordem de campos diferente
(sem separar a base antes/depois de ajuste) — não modelada; só o layout vigente.

## Fórmulas, citadas literalmente pela fonte

**M210/M610**:
- `VL_BC_CONT_AJUS = VL_BC_CONT + VL_AJUS_ACRES_BC − VL_AJUS_REDUC_BC`
- `VL_CONT_PER = VL_CONT_APUR + VL_AJUS_ACRES − VL_AJUS_REDUC − VL_CONT_DIFER + VL_CONT_DIFER_ANT`

**M200/M600**:
- `VL_TOT_CONT_NC_DEV = VL_TOT_CONT_NC_PER − VL_TOT_CRED_DESC − VL_TOT_CRED_DESC_ANT`
- `VL_CONT_NC_REC = VL_TOT_CONT_NC_DEV − VL_RET_NC − VL_OUT_DED_NC`
- `VL_CONT_CUM_REC = VL_TOT_CONT_CUM_PER − VL_RET_CUM − VL_OUT_DED_CUM`
- `VL_TOT_CONT_REC = VL_CONT_NC_REC + VL_CONT_CUM_REC`

Nenhuma recalculada por suposição — todas citadas literalmente pela fonte
(`vriconsulting.com.br`), com as posições dos campos entre parênteses na
documentação original ("Campo 07 = Campo 04 + Campo 05 - Campo 06", etc.).

## `COD_CONT` não é validado contra domínio

Referencia a "Tabela 4.3.5 — Código da Contribuição Social", uma tabela nacional
por situação/alíquota que não foi trazida para este projeto (mesma disciplina de
`esocial_s2200.py` não enumerar tabelas nacionais grandes) — aceito como string,
só o formato (até 2 caracteres) é conferido.

## Testado contra `sped_texto.montar_linha` de verdade

Mesma disciplina de `test_sped_texto.py` para os outros registros EFD: um teste
não só confere os valores calculados, mas alimenta o resultado no serializador de
linha pipe-delimited de verdade e confirma que não lança erro — prova de que a
estrutura do dicionário é serializável, não só matematicamente correta.

## Arquivos

- `contabil/efd_contribuicoes.py` — `DetalhamentoContribuicao`,
  `ConsolidacaoContribuicao`, `montar_m210`, `montar_m610`, `montar_m200`,
  `montar_m600`; camada pura, sem Frappe, testável sem bench.

## Fontes

- `vriconsulting.com.br` — páginas separadas para cada um dos quatro registros
  (M200, M210, M600, M610), lidas independentemente; a concordância de estrutura
  entre PIS e Cofins observada nelas (não presumida antes de ler) reforça a
  confiança na leitura. Não é o Guia Prático oficial (`sped.rfb.gov.br`) lido
  diretamente — mesma fonte já usada com sucesso em `efd_icms_ipi.py`. Consultado
  em 2026-08-31.
