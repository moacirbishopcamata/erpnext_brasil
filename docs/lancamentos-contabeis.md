# Lançamentos automáticos de venda

Segundo incremento do bloco contábil, sobre o primeiro
([plano-de-contas.md](plano-de-contas.md)): `contabil/lancamento.py` transforma uma
apuração já calculada (`fiscal/impostos/apuracao.py`) num conjunto de partidas dobradas,
cada uma referenciando uma conta real de `plano_de_contas.ARVORE`.

## Por que o IPI não é uma "dedução da receita" como ICMS/PIS/COFINS

Duas normas distintas tratam de "receita bruta", com objetivos diferentes — confundi-las
seria o erro fácil de cometer aqui:

- **Lei 6.404/1976, Art. 187, I** (contábil/societária): a DRE mostra receita bruta e
  suas **deduções** (impostos, abatimentos). Um tributo destacado "por dentro" do preço
  entraria aqui.
- **Decreto-Lei 1.598/1977, Art. 12, § 4º, I** (redação da Lei 12.973/2014, tributário):
  "Na receita bruta não se incluem os tributos não cumulativos cobrados, destacadamente,
  do comprador (...) pelo vendedor (...) na condição de **mero depositário**." O IPI é o
  exemplo clássico deste dispositivo (junto do ICMS-ST): o vendedor industrial só
  repassa o valor ao Fisco, nunca o reconhece como receita própria nem por um instante.

Consequência: IPI nunca toca a conta de Receita, nem como dedução — vai direto
`Débito Clientes → Crédito IPI a Recolher`, por fora da receita desde o lançamento
inicial. ICMS, PIS e COFINS **entram** na receita bruta e saem por dedução, porque a
exclusão do DL 1.598 não os alcança (regime distinto do IPI/ICMS-ST).

## As sete partidas de uma venda típica

Para uma venda com ICMS, IPI, PIS e COFINS (sem Imposto Seletivo, sem IBS/CBS):

| Débito | Crédito | Valor |
|---|---|---|
| Clientes | Receita Bruta de Vendas e Serviços | valor dos produtos (ICMS/PIS/COFINS por dentro) |
| Clientes | IPI a Recolher | IPI destacado (por fora, não toca receita) |
| ICMS sobre Vendas | ICMS a Recolher | ICMS apurado |
| PIS sobre Vendas | PIS a Recolher | PIS apurado |
| COFINS sobre Vendas | COFINS a Recolher | COFINS apurado |

Tributo com valor zero não gera partida — uma linha "Débito X / Crédito Y, valor 0,00"
não comunica nada e só polui o razão.

## IBS/CBS: modelagem provisória, declarada como tal

Este módulo trata IBS/CBS como dedução da receita — mesmo tratamento do ICMS que
substituem. Mas a contabilização de IBS/CBS **ainda é debate aberto** entre contadores e
tributaristas: há quem defenda que devem seguir o racional do IPI (nunca tocar receita),
não o do ICMS, justamente por também serem "por fora" do preço na composição da base
(ver `fiscal/impostos/ibs_cbs.py`). A reforma tributária é recente demais (fase de teste
2026-2033) para haver pronunciamento contábil (CPC) consolidado.

Escolhido o tratamento tipo-ICMS aqui por ser o mais conservador e reversível — é mais
fácil migrar uma dedução existente para "não integra receita" no futuro do que descobrir
depois que anos de receita bruta foram subestimados. **Revisar quando o CPC ou a Receita
Federal se pronunciarem.**

### Valor simbólico até 2027 — sem passivo fictício

Em 2026 (`ANO_TESTE` de `ibs_cbs.py`), IBS/CBS somam só 1% (0,9% CBS + 0,1% IBS) e a
apuração é **meramente informativa**: o XML exige os campos, mas não existe recolhimento
algum — "calculado" e "devido" deixaram de ser a mesma coisa
(`ResultadoIBSCBS.informativo`, ver `docs/reforma-tributaria.md`). Lançar `IBS a
Recolher`/`CBS a Recolher` nesse período registraria uma dívida com o Fisco que nunca vai
ser paga.

Por isso, enquanto `informativo=True`, `gerar_lancamentos_venda` **não gera** as partidas
de dedução/passivo de IBS/CBS: o valor, que já compõe o total da nota, permanece dentro
de `Receita Bruta de Vendas e Serviços` como receita ordinária, sem reclassificação
nenhuma. A partir de 2027 (CBS plena, PIS/COFINS extintos), `informativo` vira `False` e
as partidas voltam a ser geradas normalmente — mesma lógica do tratamento tipo-ICMS
acima, só que sem lançar o lado do passivo enquanto ele for fictício.

Documento com itens divergentes sobre `informativo` (um apurado em 2026, outro já em
regime pleno) faz `gerar_lancamentos_venda` levantar `LancamentoInvalido` — não existe
uma única regra de lançamento válida para o conjunto, e decidir sozinho qual dos dois
vale seria inventar dado que ninguém informou.

## Pós-condição verificada, não só assumida

`gerar_lancamentos_venda` termina com um `assert`: a soma de tudo que entra em débito na
conta `Clientes` precisa fechar exatamente com `apuracao.total_documento` (descontado o
Imposto Seletivo, barrado antes por não ter conta própria ainda). Cada `Lancamento`
individual já é balanceado por construção (um valor, um débito, um crédito) — o que
precisa de verificação ativa é que a composição do conjunto não perdeu nem inventou
centavo em relação à apuração de origem. Mesma disciplina de Design by Contract já
aplicada em `qrcode_nfce.py`: postcondição vira `assert` executável, não comentário.

## Fora de escopo desta primeira versão

- **ISS**: `fiscal/impostos/apuracao.py` não calcula ISS (cobre mercadoria, não
  serviço) — sem apuração, sem lançamento automático ainda.
- **Imposto Seletivo**: item com `imposto_seletivo != 0` faz `gerar_lancamentos_venda`
  levantar `LancamentoInvalido` em vez de produzir um lançamento desbalanceado
  silenciosamente — não há conta própria em `plano_de_contas.py` para isso ainda.
- **CMV/baixa de estoque**: exige custo do produto vendido, dado que `ApuracaoDocumento`
  não carrega (só preço de venda e tributos).
- **Compras** (crédito de tributo recuperável): pedem o valor total da nota de entrada,
  não só a apuração de tributo — módulo próprio quando chegar a vez.

## Arquivos

- `contabil/lancamento.py` — `Lancamento`, `gerar_lancamentos_venda`; camada pura, sem
  Frappe, testável sem bench.

## Fontes

- Lei 6.404/1976, Art. 187 (DRE) — ver `docs/plano-de-contas.md`.
- Decreto-Lei 1.598/1977, Art. 12, § 4º, I (redação da Lei 12.973/2014) — confirmado em
  duas fontes secundárias consistentes (`planalto.gov.br`, fonte oficial, inacessível
  às ferramentas de busca no momento); uma primeira tentativa de citar "Art. 226, § 2º
  do Regulamento do Imposto de Renda" (de uma fonte terciária) foi verificada e
  descartada — aquele artigo, no Decreto 7.212/2010 (RIPI), trata de crédito de IPI, não
  de exclusão de receita bruta. Registrado aqui como exemplo do próprio processo de
  verificação, não só o resultado — a primeira citação parecia plausível e estava errada.
- Consultado em 2026-08-29.
