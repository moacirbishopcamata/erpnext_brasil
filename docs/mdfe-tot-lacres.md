# MDF-e: `tot` (totalizadores) e `lacres`

Fecha dois dos quatro grupos que restavam de `infMDFe` (`emit`/`seg`/`prodPred` continuam fora
de escopo). Ambos pequenos e diretos — sem obstáculo de investigação, arquivo já em cache local.

## `tot` — totalizadores da carga

`vCarga` (valor), `cUnid` (`"01"` KG / `"02"` TON — só duas opções, confirmadas no XSD) e
`qCarga` (peso bruto) são obrigatórios. `qCTe`/`qNFe`/`qMDFe` (quantidade de cada tipo de
documento vinculado) são opcionais — o XSD não obriga nenhum dos três, coerente com um MDF-e
poder vincular só CT-e, só NF-e, ou os dois ao mesmo tempo (ver `docs/mdfe-infdoc.md`).

## `lacres` — lista simples, sem dataclass

Só `nLacre` (número do lacre, string) — sem outro campo. Por isso `montar_lacres` recebe
`list[str]`, não uma lista de uma dataclass de um campo só (que seria over-engineering para uma
estrutura que o próprio XSD não complica). Devolve `{}` quando a lista é vazia, nunca um grupo
`lacres` vazio no documento — `lacres` tem `minOccurs="0"`.

## Arquivos

- `erpnext_brasil/fiscal/mdfe.py` — `montar_tot`, `montar_lacres`, `UNIDADE_PESO_KG`/
  `UNIDADE_PESO_TON`.
- `erpnext_brasil/tests/test_mdfe.py` — `TestMontarTot`, `TestMontarLacres` (5 testes).

## Fontes

- `github.com/nfephp-org/sped-mdfe`, `schemes/PL_MDFe_300b/mdfeTiposBasico_v3.00.xsd`, grupos
  `tot` (linhas 1017–1078) e `lacres` (linhas 1079–1099) do arquivo baixado em 2026-08-31. Ver
  `docs/mdfe-estado.md` para o histórico da investigação.
