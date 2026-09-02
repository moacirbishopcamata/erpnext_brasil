# EFD-Reinf R-2099 (Fechamento dos Eventos Periódicos) — a outra metade do gatilho da DCTFWeb

Continuação direta de `docs/rh-esocial-s1299.md`: a DCTFWeb é disparada pelos eventos de
fechamento do eSocial **e** do EFD-Reinf. Este é o segundo gatilho.

## Achado real: sem `transDCTFWeb`

Diferente do S-1299, o R-2099 **não tem** nenhum campo equivalente a `transDCTFWeb` —
confirmado por leitura direta do XSD, não suposto por analogia. O gatilho explícito de
"solicitar transmissão imediata da DCTFWeb" existe só do lado do eSocial; o `infoFech` do
EFD-Reinf tem sete indicadores `S`/`N`, **todos obrigatórios** (nenhum opcional, diferente do
S-1299, onde `indExcApur1250`/`transDCTFWeb`/`naoValid` eram opcionais).

## `ideEvento` do R-2099 não é o mesmo tipo do R-4020 — terceira vez confirmando a mesma lição

`reinf_r4020.IdeEvento` tem `ind_retif`/`nr_recibo` (é um evento de folha, sujeito a
retificação); o `ideEvento` do R-2099 **não tem** nenhum dos dois — só `perApur`, `tpAmb`,
`procEmi`, `verProc`. Mesma categoria de erro já evitada duas vezes antes neste projeto
(`modal` do CT-e/MDF-e, `ideEvento` do S-1299/S-1200): grupos com o mesmo nome em documentos
irmãos não são garantidamente o mesmo tipo. `IdeEventoFechamento` é uma dataclass nova, testada
explicitamente (`test_nao_tem_ind_retif_nem_nr_recibo`).

`perApur` aqui tem validação mais direta que os outros eventos: o próprio XSD declara
`xs:gYearMonth` com `pattern "20([1-9][0-9])-(0[1-9]|1[0-2])"` — não só "7 caracteres" (que
aceitaria `"2026-99"`), mas o mês de fato restrito a `01`-`12`.

## Reuso: `IdeContri` de `reinf_r4020.py`, sem alteração

Mesmo `tpInsc` (`1|2`) e `nrInsc` (8/11/14 dígitos) confirmados idênticos entre os dois
eventos — reaproveitado diretamente e testado (`test_e_o_mesmo_tipo_do_r4020`), mesmo padrão de
`esocial_s1299.py` reaproveitar `IdeEmpregador` do S-1200.

## Arquivos

- `erpnext_brasil/contabil/reinf_r2099.py` — `IdeEventoFechamento`, `IdeRespInf`,
  `InfoFechamentoReinf`, `montar_info_fech_reinf` (mais `IdeContri` reexportado de
  `reinf_r4020.py`).
- `erpnext_brasil/tests/test_reinf_r2099.py` — 13 testes.

## Estado da frente "DCTFWeb"

Os dois gatilhos (S-1299 do eSocial, R-2099 do EFD-Reinf) estão modelados. O que falta para uma
DCTFWeb de verdade "acontecer" não é mais código deste projeto — é a transmissão de ambos os
eventos com sucesso ao ambiente nacional, responsabilidade da camada de transporte (ainda não
implementada para eSocial/EFD-Reinf, só para NF-e/CT-e/MDF-e).

## Fontes

- `github.com/nfephp-org/sped-efdreinf`, `schemes/v2_01_02/R-2099-evtFechamento-v2_01_02_B.xsd`
  (evento inteiro, 244 linhas) — arquivo baixado e lido localmente em 2026-08-31. Ver
  `docs/rh-esocial-s1299.md` para o histórico da investigação da frente DCTFWeb.
