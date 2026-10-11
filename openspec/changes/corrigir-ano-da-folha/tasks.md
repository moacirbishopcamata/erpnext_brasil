## 1. Ano do holerite

- [ ] 1.1 Escrever o teste de bench que salva um `Salary Slip` de 2027 e espera recusa com o ano na mensagem — verificar vendo o teste falhar antes da correção e passar depois.
- [ ] 1.2 Derivar o ano de `end_date` (reserva `start_date`) em `apply_regional_deductions` e passá-lo às duas funções — verificar com o teste de bench de 2026 (valores iguais aos de hoje) e o de 2027 (recusa).
- [ ] 1.3 Decidir se `ano` vira obrigatório em `calcular_inss` e `calcular_irrf`; se sim, ajustar os chamadores e a suíte pura — verificar com `python -m unittest discover -s erpnext_brasil/tests -t .` verde.

## 2. Tabela de 2027

- [ ] 2.1 Quando a portaria de 2027 estiver publicada, incluir a tabela de INSS e IRRF de 2027 com a fonte primária citada no docstring e conferida na web — verificar com os exemplos oficiais como teste.

## 3. Documentação

- [ ] 3.1 Atualizar `docs/rh-irrf.md` e marcar RT-01 resolvido em `docs/revisao-total/folha-rh.md` e `docs/revisao-total.md` — verificar relendo os dois.
