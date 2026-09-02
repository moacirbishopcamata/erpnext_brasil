# ECF: Bloco J (Plano de Contas e Mapeamento) — o primeiro corte de um item enorme

Primeiro código da ECF, depois do levantamento em `docs/ecf-estado.md`. Escolhido por ser a
fatia mais barata: a própria Receita confirma que a ECF **importa o plano de contas diretamente
da ECD** — nada para recadastrar, só reaproveitar o que `ecd_i050.py` já produz.

## `J050` é `I050` com o `REG` trocado — confirmado campo a campo

`montar_j050` não reimplementa nada: delega inteiramente a `ecd_i050.montar_i050` e só troca o
valor de `REG`. Testado explicitamente (`test_j050_e_i050_com_reg_trocado`) — todos os outros
sete campos (`DT_ALT`, `COD_NAT`, `IND_CTA`, `NIVEL`, `COD_CTA`, `COD_CTA_SUP`, `CTA`) batem
exatamente entre os dois registros, linha a linha.

## `COD_NAT` da ECF tem mais opções — achado real, não conflito de reuso

A fonte usada (documentação técnica de ERP, mesmo padrão de confiança já aceito para
DeSTDA/S-1299/R-2099) lista `COD_NAT` do `J050` com seis valores — `01`-Ativo, `02`-Passivo,
`03`-PL, `04`-Resultado, e **dois que a ECD deste projeto não modela**: `05`-Compensação,
`09`-Outras. Isso não invalida o reuso: este projeto não tem contas de compensação nem "outras"
no plano de contas (`plano_de_contas.ARVORE` só tem os quatro grupos do Art. 178/187 da Lei
6.404/76), então o subconjunto que `montar_i050` produz (`01`-`04`) é sempre um valor válido
dentro do domínio mais amplo do `J050` — testado (`test_cod_nat_fica_dentro_do_subconjunto_01_a_04`).

## O que ficou de fora deste primeiro incremento

- `J051` (mapeamento para o Plano de Contas Referencial da RFB) — mesma decisão de escopo já
  tomada para `ecd_i051.montar_i051`: só o De-Para que o contribuinte escolher informar.
- `J053` (subcontas correlatas) e `J100` (centro de custos) — grupos que este projeto não
  modela ainda (sem conceito de centro de custo em `plano_de_contas.py`).

## Arquivos

- `erpnext_brasil/contabil/ecf_bloco_j.py` — `montar_j001`, `montar_j050`, `montar_j990`.
- `erpnext_brasil/tests/test_ecf_bloco_j.py` — 6 testes.

## Fontes

- `documentacao.senior.com.br/goup/5.10.3/menu_controladoria/sped/contabil-fiscal-ecf/
  bloco-j.htm`, consultado em 2026-08-31. Ver `docs/ecf-estado.md` para o levantamento
  completo da ECF.
