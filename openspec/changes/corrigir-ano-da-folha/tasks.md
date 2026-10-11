## 1. Ano do holerite

- [ ] 1.1 (escrito em `tests_bench/test_folha.py`, **não executado**: falta rodar no bench) Escrever o teste de bench que salva um `Salary Slip` de 2027 e espera recusa com o ano na mensagem — verificar vendo o teste falhar antes da correção e passar depois.
- [ ] 1.2 (feito em `folha/periodo.py` e `integracao/folha.py`; guarda por `ast` verde; falta a prova em bench) Derivar o ano de `end_date` (reserva `start_date`) em `apply_regional_deductions` e passá-lo às duas funções — verificar com o teste de bench de 2026 (valores iguais aos de hoje) e o de 2027 (recusa).
- [x] 1.3 **Decisão: `ano` continua com padrão nas funções puras** (42 chamadas em testes dependem dele); a omissão na integração é travada por `tests/test_periodo_folha.py::TestACosturaPassaOAno`. Decidir se `ano` vira obrigatório em `calcular_inss` e `calcular_irrf`; se sim, ajustar os chamadores e a suíte pura — verificar com `python -m unittest discover -s erpnext_brasil/tests -t .` verde.

## 2. Tabela de 2027

- [ ] 2.1 **Bloqueada (conferido em 2026-10-11): a Portaria Interministerial MPS/MF de 2027 ainda não foi publicada** (a de 2026 é a nº 13, de 9/01/2026; a de cada ano sai em janeiro, no Diário Oficial da União). Buscas por tabela de INSS e de IRRF de 2027 só acharam a tabela de 2026 e fontes secundárias que divergem entre si. Não extrapolar de 2026. Retomar em janeiro de 2027, na fonte primária (DOU e gov.br/inss; tabela do IRRF em gov.br/receitafederal). Quando a portaria de 2027 estiver publicada, incluir a tabela de INSS e IRRF de 2027 com a fonte primária citada no docstring e conferida na web — verificar com os exemplos oficiais como teste.

## 3. Documentação

- [x] 3.1 Atualizar `docs/rh-irrf.md` e marcar RT-01 resolvido em `docs/revisao-total/folha-rh.md` e `docs/revisao-total.md` — verificar relendo os dois.
