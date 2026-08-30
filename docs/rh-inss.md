# INSS: contribuição previdenciária do empregado

Primeiro cálculo do bloco RH, depois do levantamento do estado do `hrms`
(`docs/rh-estado-hrms.md`). Mesmo destino final documentado ali:
`SalarySlip.apply_regional_deductions`, o hook que o `hrms` já expõe para isto — ainda
não plugado lá, só a conta em si implementada e testada.

## A tabela muda todo ano — nunca hardcode "a" tabela, hardcode "a de determinado ano"

Diferente de uma regra fiscal estável (um XSD, uma fórmula constitucional), a tabela de
salário de contribuição do INSS é reajustada anualmente por Portaria Interministerial
(MPS/MF) — o mesmo padrão de risco já visto no fator de vencimento do boleto (mudou de
base em 2025) e na alíquota-teste de IBS/CBS (só o ano vigente embutido, resto levanta
erro). `_FAIXAS_POR_ANO` é um dicionário por ano; `calcular_inss` levanta
`INSSInvalido` para qualquer ano sem tabela embutida — nunca extrapola nem reaproveita o
ano anterior por semelhança.

## Tabela vigente: 2026 (Portaria Interministerial MPS/MF nº 13, de 9/01/2026)

Vigência a partir de 1º de janeiro de 2026. A fonte primária (`gov.br/previdencia`) foi
localizada e citada — mas o PDF publicado é digitalizado como imagem e não pôde ser
lido por texto pelas ferramentas de busca, mesma limitação já registrada para outras
fontes `gov.br` neste projeto. Os valores foram confirmados em duas fontes secundárias
independentes, que reproduziram exatamente os mesmos quatro limites de faixa, alíquotas
e parcelas a deduzir.

| Faixa | Salário de contribuição (R$) | Alíquota | Parcela a deduzir (R$) |
|---|---|---|---|
| 1 | até 1.621,00 | 7,5% | 0,00 |
| 2 | de 1.621,01 até 2.902,84 | 9% | 24,32 |
| 3 | de 2.902,85 até 4.354,27 | 12% | 111,40 |
| 4 | de 4.354,28 até 8.475,55 (teto) | 14% | 198,49 |

## Verificação além das duas fontes: cálculo faixa a faixa, independente da tabela publicada

O teste `test_bate_com_calculo_faixa_a_faixa` não repete a tabela de "parcela a
deduzir" — soma o valor progressivamente, faixa por faixa, com uma fórmula
matematicamente equivalente mas escrita de forma totalmente diferente (sem parcela a
deduzir nenhuma). Os dois métodos batem (dentro de 1 centavo de arredondamento
intermediário) para uma bateria de salários cobrindo as quatro faixas e os limites
exatos — a mesma disciplina de "conferir a fonte de dois jeitos diferentes", agora
aplicada matematicamente em vez de com uma segunda fonte externa.

## Teto: a base de cálculo satura, não o salário

Acima de R$ 8.475,55 de salário de contribuição, o desconto não cresce mais — a base é
limitada ao teto, não ao salário efetivo. `calcular_inss` testa explicitamente que um
salário de R$ 1.000.000,00 desconta exatamente o mesmo que um de R$ 8.475,55
(`test_acima_do_teto_desconta_o_mesmo_que_no_teto`, `test_nunca_excede_o_desconto_
maximo`) — e a função tem uma pós-condição (`assert`) verificando isso em tempo de
execução, não só confiada à fórmula: se a tabela algum dia tiver um erro que produza
valor acima do teto máximo, a função falha alto em vez de devolver um número plausível
e errado.

## Ainda por implementar

- **Plugar em `SalarySlip.apply_regional_deductions`** — feito, ver
  `docs/rh-integracao-salary-slip.md` (não exercitado contra bench real ainda).
- **INSS patronal** (a contribuição do empregador sobre a folha, alíquota e regras
  diferentes — inclusive Simples Nacional/Desoneração da Folha têm tratamento
  próprio) — não coberto, só a contribuição do empregado.
- **Categorias diferentes de segurado** (contribuinte individual, facultativo — a
  fonte já mostra que têm tabela própria, diferente da de empregado) — fora de escopo,
  este módulo cobre só "empregado, empregado doméstico e trabalhador avulso".
- **IRRF na folha** — implementado em seguida, ver `docs/rh-irrf.md`.
- **FGTS**, **eSocial** — os outros itens já listados no levantamento de estado,
  nenhum pesquisado ainda.

## Arquivos

- `folha/inss.py` — `calcular_inss`; camada pura, sem Frappe, testável sem bench.

## Fontes

- Portaria Interministerial MPS/MF nº 13, de 9 de janeiro de 2026 (vigência desde
  1º/01/2026) — fonte oficial (`gov.br/previdencia`) localizada e citada, PDF
  digitalizado como imagem, ilegível às ferramentas de busca; valores confirmados em
  duas fontes secundárias independentes e conferidos matematicamente contra um cálculo
  faixa a faixa independente — consultado em 2026-08-30.
