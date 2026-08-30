# IRRF na folha: Imposto de Renda Retido na Fonte

Segundo cálculo do bloco RH, depois de `docs/rh-inss.md`. Mesmo destino final:
`SalarySlip.apply_regional_deductions` (`docs/rh-estado-hrms.md`) — ainda não plugado
lá, só a conta em si implementada e testada.

## 2026 não é "mais um ano" para o IRRF

A tabela progressiva tradicional do IRRF é conhecida há anos (a última mudança de
valores foi em 2023). O que torna 2026 diferente é a **Lei nº 15.270, de 26 de
novembro de 2025**, que cria um mecanismo novo por cima da tabela — um "redutor" que
isenta de fato quem ganha até R$ 5.000,00 mensais e reduz progressivamente o imposto
até R$ 7.350,00, sem reescrever a tabela em si. `calcular_irrf` reflete essa estrutura
em duas camadas: `calcular_irrf_tradicional` (a tabela de sempre) menos
`calcular_redutor` (o mecanismo novo), nunca menos que zero.

## Tabela tradicional vigente em 2026

| Faixa | Base de cálculo (R$) | Alíquota | Parcela a deduzir (R$) |
|---|---|---|---|
| 1 | até 2.428,80 | isento | 0,00 |
| 2 | de 2.428,81 até 2.826,65 | 7,5% | 182,16 |
| 3 | de 2.826,66 até 3.751,05 | 15% | 394,16 |
| 4 | de 3.751,06 até 4.664,68 | 22,5% | 675,49 |
| 5 | acima de 4.664,68 | 27,5% | 908,73 |

## Uma contradição de fontes, resolvida pelo próprio exemplo oficial

Uma primeira busca agregada encontrou uma fonte citando o limite de isenção como
**R$ 2.259,20** (valor de uma tabela vigente antes da atualização). Uma segunda fonte
independente (cidesp.com.br) deu **R$ 2.428,80**. Em vez de escolher por autoridade
presumida da fonte, a página oficial de exemplos da Receita Federal
(`gov.br/receitafederal/.../exemplos-de-aplicacao-da-lei-15-270-2025`) foi buscada
diretamente — os 5 exemplos publicados só fazem sentido com a tabela de
R$ 2.428,80 (o exemplo de João usa exatamente esse valor como base isenta). A
contradição foi resolvida a favor de R$ 2.428,80, com a fonte oficial como
desempate, não a maioria das fontes secundárias.

## O redutor: fórmula e por que incide sobre o bruto, não sobre a base

```
redutor = máx(0, 978,62 − 0,133145 × rendimento_bruto_mensal)
```

Aplicado sobre o **rendimento bruto mensal**, antes de qualquer dedução — não sobre a
base de cálculo (já líquida de INSS ou desconto simplificado). Isso é
propositalmente diferente de `calcular_irrf_tradicional`, que sim usa a base. A
fórmula por si só já cai a zero a partir de ~R$ 7.350,00 de bruto — não precisa de um
corte separado no código, `calcular_redutor` só formaliza esse comportamento natural
com `max(0, ...)` para o caso em que a subtração já dá negativo.

## Verificação: os 5 exemplos oficiais, reproduzidos exatamente

A fonte oficial (`gov.br/receitafederal`) publica 5 exemplos numéricos completos, cada
um citando rendimento bruto, INSS ou desconto simplificado usado, base de cálculo,
faixa/alíquota da tabela tradicional, imposto tradicional, redutor aplicado e IRRF
final. `tests/test_irrf.py::TestExemplosOficiaisRFB` reproduz os 5 como casos de teste
nomeados — não uma bateria genérica de valores, os mesmos números publicados:

| Exemplo | Bruto (R$) | Base de cálculo (R$) | Tradicional (R$) | Redutor (R$) | IRRF final (R$) |
|---|---|---|---|---|---|
| João | 3.036,00 | 2.428,80 | 0,00 | não aplicável | 0,00 |
| José | 4.000,00 | 3.392,80 | 114,76 | 446,04 | 0,00 |
| Maria | 5.000,00 | 4.392,80 | 312,89 | ≈312,89-312,90 | 0,00 |
| Rita | 6.000,00 | 5.350,40 | 562,63 | 179,75 | 382,88 |
| Vera | 7.607,20 | 7.000,00 | 1.016,27 | 0,00 (fórmula já negativa) | 1.016,27 |

Todos os 5 batem exatamente com `calcular_irrf`. No caso de Maria, o redutor calculado
por `calcular_redutor` (`978,62 − 0,133145 × 5.000,00 = 312,895`) arredonda para
**R$ 312,90** por `ROUND_HALF_UP` (convenção deste projeto, ver `docs/README.md`),
um centavo acima do R$ 312,89 citado na fonte — divergência de arredondamento
intermediário sem efeito no resultado final (ambos zeram o imposto tradicional de
R$ 312,89). Documentado aqui como divergência conhecida, não escondida; o teste dos 5
exemplos verifica só o IRRF final, não o valor intermediário do redutor nesse caso
específico.

## `calcular_desconto_simplificado`: fornecido, não usado internamente

25% do rendimento bruto, até um teto mensal (R$ 607,20 em 2026) — a alternativa a
usar INSS + dedução por dependente. A escolha entre os dois métodos é do
contribuinte/empregador e depende de dado que este módulo não tem (número de
dependentes, pensão alimentícia); por isso `calcular_irrf` recebe a base de cálculo já
pronta, e `calcular_desconto_simplificado` é oferecido só como utilidade — mesma
disciplina de `lancamento.gerar_lancamentos_compra` receber créditos tributários já
decididos pelo chamador em vez de inferi-los.

## Ainda por implementar

- **Plugar em `SalarySlip.apply_regional_deductions`** — hoje é só a conta, sem
  nenhuma integração com Frappe/doctype.
- **Dedução por dependente** (R$ 189,59/mês por dependente, valor histórico da
  tabela tradicional) não modelada como conceito de primeira classe — quem chama
  `calcular_irrf` já precisa ter descontado isso da base, se for o método escolhido.
- **Pensão alimentícia** como dedução da base — não modelada.
- **Décimo terceiro salário** (tributação separada, com sua própria tabela e sem o
  redutor da Lei 15.270/2025, que é mensal) — fora de escopo deste módulo.
- **FGTS** — implementado em seguida, ver `docs/rh-fgts.md`.
- **eSocial** — ainda não pesquisado.

## Arquivos

- `folha/irrf.py` — `calcular_irrf_tradicional`, `calcular_redutor`, `calcular_irrf`,
  `calcular_desconto_simplificado`; camada pura, sem Frappe, testável sem bench.

## Fontes

- Lei nº 15.270, de 26 de novembro de 2025 — cria o mecanismo do redutor. Texto da
  lei em si não foi lido diretamente (fonte `planalto.gov.br` não tentada nesta
  rodada); a fórmula do redutor foi obtida por fonte secundária e confirmada por
  reprodução exata dos 5 exemplos oficiais abaixo.
- `gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/tabelas/exemplos-de-aplicacao-da-lei-15-270-2025`
  — fonte oficial, acessível e legível (diferente da maioria das fontes `gov.br`
  citadas neste projeto, que vêm como PDF digitalizado) — usada tanto para resolver a
  contradição do limite de isenção quanto como o teste mais forte do módulo
  (5 exemplos completos reproduzidos em `tests/test_irrf.py`). Consultada em
  2026-08-30.
