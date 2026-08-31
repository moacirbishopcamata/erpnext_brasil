# CT-e: grupo `ICMSUFFim` (partilha de ICMS em prestação interestadual)

Primeiro código de CT-e depois do levantamento em `docs/cte-estado.md`. Escopo deliberadamente
estreito — só o que já estava 100% verificado contra o XSD oficial.

## O que é

`imp/ICMSUFFim`, grupo opcional do CT-e para prestações de transporte interestaduais a
consumidor final não contribuinte do ICMS — mesma partilha de base entre UF de origem e UF de
destino que a EC 87/2015 criou para mercadorias (`ICMSUFDest` da NF-e), aplicada ao serviço de
transporte. Confirmado por leitura direta do XSD (`cte_v4.00.xsd`, linha 3960, ver
`docs/cte-estado.md`): os nomes de campo **divergem** dos da NF-e —
`vBCUFFim`/`pFCPUFFim`/`pICMSUFFim`/`pICMSInter`/`vFCPUFFim`/`vICMSUFFim`/`vICMSUFIni`, não
`vBCUFDest`/`pICMSUFDest`/`vICMSUFDest`.

## Por que só isso, e não o CFOP de transporte também

O levantamento confirmou que `ide.CFOP` do CT-e usa o mesmo tipo `TCfop` de 4 dígitos de
`fiscal/cfop.py`, mas os **valores específicos** de prestação de serviço de transporte não
tinham sido verificados ainda quando este incremento foi escrito. **Feito em seguida** — ver
`docs/cfop-transporte.md` (`fiscal/cfop_transporte.py`), com o nível de confiança mais baixo
declarado explicitamente (fonte secundária cruzada, Ajuste SINIEF original não localizado).

## Reuso, não reimplementação

`fiscal/cte.py::montar_icms_uf_fim` não calcula nada sozinho — delega inteiramente a
`fiscal/impostos/icms.py::calcular_difal`, já testado e documentado (`docs/apuracao-periodica.md`
e docstring própria). A única coisa nova é o mapeamento de nome de campo. Testado (`test_cte.py`,
4 testes): delega de fato (mesmo resultado de uma chamada direta), usa os nomes certos (não os da
NF-e), zera FCP quando não informado, e propaga `base_dupla` (prova de que o parâmetro não é
ignorado).

## O que falta para uma prestação de CT-e completa

- CFOP de transporte (acima).
- `toma3`/`toma4` (tomador do serviço) — não investigado.
- `infCarga`/`infDoc` — ponte com a NF-e transportada, prioritária para o MDF-e depois.
- Modal (rodoviário como primeiro candidato, não confirmado como prioridade).
- Assinatura e transmissão — hipótese de reuso do padrão da NF-e, não verificada.

## Arquivos

- `erpnext_brasil/fiscal/cte.py` — `montar_icms_uf_fim`.
- `erpnext_brasil/tests/test_cte.py` — 4 testes.

## Fontes

- `github.com/nfephp-org/sped-cte`, `schemes/PL_CTe_400/cte_v4.00.xsd`, grupo `imp/ICMSUFFim`
  (linha 3960 do arquivo baixado em 2026-08-31 — ver `docs/cte-estado.md` para o histórico da
  investigação).
- Art. 155 §2º VII/VIII da Constituição Federal (EC 87/2015) — mesma base legal já citada em
  `fiscal/impostos/icms.py::calcular_difal`.
