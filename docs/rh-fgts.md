# FGTS: Fundo de Garantia do Tempo de Serviço

Terceiro cálculo do bloco RH, depois de `docs/rh-inss.md` e `docs/rh-irrf.md`.

## Diferença estrutural: não é desconto do empregado

INSS e IRRF saem do salário bruto do trabalhador. FGTS é o oposto — o empregador
deposita, por fora, numa conta vinculada em nome do trabalhador (Caixa Econômica
Federal). Não é uma dedução na folha; é uma obrigação do empregador. Isso significa
que `folha/fgts.py` não compete com `inss.py`/`irrf.py` pelo mesmo "líquido do
trabalhador" — é um cálculo paralelo, com seu próprio lançamento contábil (ainda não
modelado em `contabil/lancamento.py` — item futuro).

## Dois cálculos, duas situações diferentes

### Depósito mensal (Lei 8.036/1990, Art. 15)

8% da remuneração mensal do trabalhador (inclui gorjetas e 13º salário, quando pago).
Exceção: 2% para o contrato de aprendizagem, regulamentada pelo Decreto 5.598/2005,
Art. 24, parágrafo único.

### Multa rescisória (Lei 8.036/1990, Art. 18, §1º/§2º; Art. 484-A da CLT)

Incide sobre o **total histórico de depósitos** feitos durante o contrato — a lei
fala em "montante de todos os depósitos... atualizados monetariamente e acrescidos
dos respectivos juros", não sobre um saldo qualquer. `calcular_multa_rescisoria`
recebe esse total já pronto do chamador, nunca tenta reconstituí-lo (a série
histórica de depósitos/correção monetária é dado de outro sistema, não deste
módulo).

| Motivo do desligamento | Percentual | Fonte |
|---|---|---|
| Dispensa sem justa causa | 40% | Lei 8.036/90, Art. 18, §1º |
| Rescisão por acordo | 20% (metade da multa cheia) | CLT, Art. 484-A (incluído pela Lei 13.467/2017) |
| Culpa recíproca ou força maior (reconhecida pela Justiça do Trabalho) | 20% | Lei 8.036/90, Art. 18, §2º |
| Justa causa | 0% | Ausência de previsão de multa nesses casos |
| Pedido de demissão | 0% | idem |
| Término de contrato por prazo determinado | 0% | idem |

`ALIQUOTA_MULTA_POR_MOTIVO` é a tabela completa — `calcular_multa_rescisoria` levanta
`FGTSInvalido` para qualquer motivo fora dela, nunca assume 0% por omissão. "Sem
multa" é uma linha explícita da tabela, não o comportamento padrão para string
desconhecida — a mesma disciplina de `INSSInvalido`/`IRRFInvalido` para ano sem
tabela embutida, aplicada aqui a uma dimensão categórica em vez de temporal.

## O que fica de fora, deliberadamente

- **Prazo de recolhimento** (dia 20 do mês subsequente, antecipado ao dia útil
  anterior quando cai em dia não útil — regra vigente desde a migração para o FGTS
  Digital em 2024, segundo o `gov.br/trabalho-e-emprego`) depende de um calendário
  de feriados nacionais que nenhum outro módulo deste projeto modela — mesma
  disciplina de `boleto.py` não inferir o `campo_livre`: dado que exige uma tabela
  externa fica com quem chama.
- **Percentual de saque da conta vinculada** (80% em caso de acordo, regras do
  saque-aniversário) é direito de saque do trabalhador, categoria de regra diferente
  da obrigação de depósito/multa do empregador que este módulo cobre — não
  modelado.
- **FGTS sobre 13º/férias** não tem tratamento separado — quem chama já deve incluir
  esses valores na `remuneracao` do mês em que são efetivamente pagos.

## Arquivos

- `folha/fgts.py` — `calcular_deposito_mensal`, `calcular_multa_rescisoria`; camada
  pura, sem Frappe, testável sem bench.

## Fontes

- Lei nº 8.036, de 11 de maio de 1990 (Lei do FGTS), Art. 15 (alíquota de depósito) e
  Art. 18, §1º/§2º (multa rescisória) — tentativa de leitura direta em
  `planalto.gov.br/ccivil_03/leis/l8036consol.htm` falhou por erro de conexão
  (`ECONNRESET`) nesta sessão; texto dos artigos confirmado por busca agregada
  citando o teor exato dos dispositivos (Jusbrasil, ANTT Legis — republicações do
  texto oficial, não interpretação de terceiros).
- CLT, Art. 484-A (rescisão por acordo, incluído pela Lei nº 13.467, de 13 de julho
  de 2017 — reforma trabalhista) — confirmado por busca agregada, incluindo o
  detalhe de que a multa de acordo é exatamente metade da multa cheia (20% de 40%).
- Decreto nº 5.598, de 1º de dezembro de 2005, Art. 24, parágrafo único — alíquota
  reduzida de 2% para o contrato de aprendizagem.
- Prazo de recolhimento mensal (dia 20, regra do FGTS Digital desde 2024) —
  `gov.br/trabalho-e-emprego`, citado apenas para registrar por que este módulo não
  o implementa (depende de calendário de feriados não modelado), não usado em
  nenhum cálculo. Consultado em 2026-08-30.
