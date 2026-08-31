# CT-e: modal rodoviário (`infModal/rodo`)

Fecha mais uma pendência de `docs/cte-estado.md`. `cteModalRodoviario_v4.00.xsd` tem só 102
linhas — pequeno o suficiente para ler inteiro de uma vez, sem risco de truncamento pela
ferramenta de resumo (o obstáculo que atrasou o levantamento do CT-e nas primeiras tentativas).

## Achado principal: bem menor do que se poderia supor

O modal rodoviário do CT-e **não** carrega identificação de veículo nem de motorista. Isso é
responsabilidade do **MDF-e** — o documento que identifica veículo/motorista/rota de uma viagem
específica, que pode agrupar várias prestações de CT-e (um caminhão leva mercadoria de vários
CT-e numa mesma viagem). O modal rodoviário do CT-e carrega só:

- `RNTRC` (obrigatório) — Registro Nacional de Transportadores Rodoviários de Carga (ANTT).
- `occ` (opcional, até 10) — Ordens de Coleta associadas.

## A pegadinha do RNTRC, verificada no XSD

`TRNTRC` não é só uma sequência de dígitos: o padrão é `[0-9]{8}|ISENTO` — oito dígitos **ou** a
palavra literal `ISENTO`, usada por quem transporta com frota própria e está dispensado do
registro na ANTT. `validar_rntrc` cobre as duas pontas — rejeitaria tanto `"1234567"` (dígitos
insuficientes) quanto aceitaria `"ISENTO"` corretamente, não como erro de formato.

## Escopo

Implementado: `RNTRC` validado, `occ` aceito como lista de dicionários já montados pelo
chamador (não validado campo a campo). Modelar `emiOcc` por completo (CNPJ, IE, UF, telefone de
quem emitiu a ordem de coleta) fica para quando houver um caso de uso real — não especulativo.

## Arquivos

- `erpnext_brasil/fiscal/cte_rodoviario.py` — `validar_rntrc`, `montar_rodo`.
- `erpnext_brasil/tests/test_cte_rodoviario.py` — 8 testes.

## Fontes

- `github.com/nfephp-org/sped-cte`, `schemes/PL_CTe_400/cteModalRodoviario_v4.00.xsd` (arquivo
  inteiro, 102 linhas) e `cteTiposBasico_v4.00.xsd` (linha 7906, `TRNTRC`) — baixados e lidos
  localmente em 2026-08-31. Ver `docs/cte-estado.md` para o histórico da investigação.
