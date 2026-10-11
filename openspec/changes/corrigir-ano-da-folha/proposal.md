## Why

A folha calcula INSS e IRRF sempre com a tabela de 2026. `integracao/folha.py:93-94` chama `calcular_inss(bruto)` e `calcular_irrf(bruto, bruto - inss)` sem passar o ano, e as funções de `folha/inss.py` e `folha/irrf.py` usam `ANO_VIGENTE = 2026` como padrão. O ano do `Salary Slip` nunca é lido. A função `_tabela_do_ano` foi escrita para falhar alto em ano sem tabela, mas a falha nunca dispara. Um holerite de janeiro de 2027 sai com a tabela e o teto de 2026, sem erro e com valor errado. Achado RT-01 da revisão total (`docs/revisao-total/folha-rh.md`), **Crítico, com prazo em 01/01/2027**.

## What Changes

- `integracao/folha.py` deriva o ano do período do `Salary Slip` (`end_date`, com `start_date` como reserva) e o passa a `calcular_inss` e `calcular_irrf`.
- Holerite de ano sem tabela embutida **recusa** com mensagem que diz o ano e o que fazer (cadastrar a tabela), em vez de usar a de 2026 em silêncio.
- Os valores padrão `ano=ANO_VIGENTE` deixam de ser usados pela integração; avaliar tornar `ano` obrigatório nas funções puras para impedir a omissão.
- Teste de bench com holerite de 2025 (recusa ou tabela própria, conforme exista) e de 2027 (recusa).
- Quando a Portaria de 2027 sair, incluir a tabela de 2027 como incremento próprio, com fonte primária citada.

## Capabilities

### New Capabilities

Nenhuma capability nova de spec: não há spec de folha em `openspec/specs/`. O change usa `skip_specs: true`; a regra "folha sem tabela do ano recusa" fica nos testes e em `docs/rh-irrf.md`.

### Modified Capabilities

Nenhuma.

## Impact

- `erpnext_brasil/integracao/folha.py`, `erpnext_brasil/folha/inss.py`, `erpnext_brasil/folha/irrf.py`.
- Testes: `tests/` (função pura com ano explícito) e `tests_bench/test_folha.py`.
- Doc: `docs/rh-irrf.md`, `docs/revisao-total/folha-rh.md` (marcar resolvido).
- Comportamento visível: holerite de ano sem tabela passa a ser recusado.
