# Revisão total — qualidade dos testes

Versão `0.227.0`, 2026-10-11. Cobre a tarefa 3.8 do change `revisao-total-erpnext-brasil`.

## Cobertura

Varredura mecânica por `ast` sobre os 3.490 testes da suíte pura e os 222 de bench, mais a execução da suíte. Não li teste a teste.

## Números

| | Suíte pura | Bench |
|---|---|---|
| Módulos `test_*.py` | 182 | 27 |
| Testes | 3.490 (3 pulados) | 222 |
| Testes sem asserção visível no corpo (sinal fraco, ver RT-11) | 134 | 7 (6 são falso positivo) |
| Módulos sem `MODULOS_COBERTOS` | n/a | 0 |
| Módulos de bench sem nenhuma releitura de banco | n/a | 1 (`test_consulta_cep.py`) |

Regra de arquitetura já imposta por `tests/test_arquitetura.py` (nenhum teste importa `frappe`, `fiscal/` não importa `frappe` nem `integracao/`); a suíte passou.

## Verificado

- Todos os módulos de `fiscal/`, `contabil/` e `folha/` aparecem em pelo menos um teste (por nome).
- Todo teste de bench declara `MODULOS_COBERTOS`, e `scripts/cobertura_de_bench.py` reporta 13/13 dos módulos ligados no `hooks.py`.

## Achados

### RT-11 — a contagem de testes sem asserção é um sinal fraco, não um defeito confirmado — **Baixo (a verificar)**

A varredura por `ast` achou 134 testes puros e 7 de bench sem `assert*`, `raises` nem `fail` no corpo. Conferi os 7 de bench: seis (`test_mdfe_documento.py:211-236`) chamam o auxiliar `_recusa(...)`, que faz `assertEqual`, `assertIn` e `assertFalse` (`test_mdfe_documento.py:205-208`), então **têm asserção**; o sétimo (`test_consulta_cep.py:227`, "quem pode cadastrar endereço passa na checagem") é do tipo "não levanta". Ou seja, o método superconta: asserção dentro de auxiliar não é vista. Os 134 puros provavelmente seguem o mesmo padrão (amostra: `test_cobranca.py:52` `test_valida`, caso válido que só não levanta), mas **não os conferi**. Não é achado de qualidade até alguém ler a lista; registro como risco de que um teste "não levanta" fique indistinguível de um teste que esqueceu o `assert`.

### RT-08 (parcial) — o critério de cobertura de bench olha só o `hooks.py` — **Médio**

`cobertura_de_bench.py` dá 13/13, mas nove módulos de `integracao/` não têm referência em teste algum (ver [`integracao.md`](integracao.md)). Os 13/13 são verdadeiros e mesmo assim não dizem que a integração está coberta.

### RT-18 — `test_consulta_cep.py` de bench não relê o banco — **Baixo**

É o único módulo de bench sem releitura (`db.get_value`, `get_all`, `get_doc`, `exists`, `count`). Para uma consulta de CEP que só preenche lacuna e não grava, é esperado; vale confirmar que nenhum teste ali dependia de persistência.
