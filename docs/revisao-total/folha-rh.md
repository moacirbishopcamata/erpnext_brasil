# Revisão total — folha e RH (eSocial)

Versão `0.227.0`, 2026-10-11. Cobre a tarefa 3.4 do change `revisao-total-erpnext-brasil`.

## Cobertura

- **Lido:** `folha/inss.py` e `folha/irrf.py` (tabelas, anos, falha em ano sem tabela), `integracao/folha.py` (a costura com o `Salary Slip`), `montagem_lote_esocial.py` (permissão e certificado).
- **Varrido:** os 20 módulos de `folha/` contra referência normativa no docstring e contra teste.
- **Não lido:** os leiautes S-1000, S-1010, S-1200, S-1299, S-2200 e S-2299 e o SOAP do eSocial. Não conferi nenhum contra o leiaute oficial.

## Achados

### RT-01 — a folha calcula INSS e IRRF sempre com a tabela de 2026, qualquer que seja o período do holerite — **Crítico (latente até 01/01/2027)** — *corrigido no código na `0.228.0`; falta a tabela de 2027 e a prova em bench*

- `folha/inss.py:54` e `folha/irrf.py:74` definem `ANO_VIGENTE = 2026` e usam como valor padrão do parâmetro `ano` (`inss.py:79`, `irrf.py:118`, `:131`, `:149`, `:163`).
- `integracao/folha.py:93-94`, a única chamada de produção, faz `calcular_inss(bruto)` e `calcular_irrf(bruto, bruto - inss)` **sem passar o ano**. O ano do holerite (`start_date` ou `end_date` do `Salary Slip`) nunca é lido; `grep` por `ano`, `year`, `start_date`, `end_date` em `integracao/folha.py` não acha nada.
- Efeito: a função `_tabela_do_ano` (`irrf.py:108-110`) foi escrita para **falhar alto** em ano sem tabela, mas como ninguém passa o ano, a falha nunca dispara. Um holerite de janeiro de 2027 sai com a tabela e o teto de 2026, **sem erro e com valor errado**; o mesmo vale para folha retroativa de 2025.
- Prazo: o problema aparece na folha de **janeiro de 2027**, a cerca de dois meses da data desta revisão.
- Contraste: `fiscal/impostos/ibs_cbs.py:111-121` faz certo — só o ano de teste tem alíquota e qualquer outro levanta `ValueError`.
- Correção: derivar o ano do período do `Salary Slip`, passá-lo às duas funções e ter um teste de bench com holerite de 2025 e 2027 (o de 2027 deve recusar enquanto a tabela não existir).

### RT-04 (parcial) — módulos de folha sem referência normativa no docstring — **Baixo**

Nenhum dos 20 módulos de `folha/` ficou sem palavra-chave de fonte no docstring. A varredura é fraca para esta frente: a palavra "eSocial" faz parte da lista e casa com qualquer módulo `esocial_*`, então só `inss.py`, `irrf.py` e `fgts.py` têm a ausência realmente testada. `inss.py` cita a Portaria Interministerial MPS/MF nº 13, de 9/01/2026, e `irrf.py` cita a Lei nº 15.270/2025 e os cinco exemplos oficiais da Receita Federal. **Não conferi essas fontes**; a varredura só prova que a citação existe.

## Pendências já declaradas (sem achado novo)

- `base de cálculo = bruto − INSS` ignora dependentes e pensão; está documentado em `docs/rh-irrf.md`.
- Transmissão ao eSocial depende de certificado A1 e homologação; ver `docs/rh-estado-esocial.md`.
