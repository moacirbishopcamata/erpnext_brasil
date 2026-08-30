# Apuração periódica de ICMS e IPI

Terceiro incremento do bloco contábil, sobre
[lancamentos-contabeis.md](lancamentos-contabeis.md): `contabil/apuracao_periodo.py`
fecha o período (normalmente um mês) — soma tudo que virou débito de ICMS/IPI nas
vendas contra tudo que virou crédito nas compras, e decide se sobra imposto a pagar ou
saldo credor para carregar adiante.

## Não é o mesmo "apuração" de `fiscal/impostos/apuracao.py`

Aquele módulo apura **um documento**: quanto de ICMS/IPI/PIS/COFINS/IBS/CBS uma NF-e
específica gera. Este apura **um período**: a soma de todos os débitos (saídas) contra
todos os créditos (entradas) de várias notas, terminando em "a recolher" ou "saldo
credor a transportar" — o livro de apuração propriamente dito, não a nota isolada.

## Fundamento constitucional — os dois tributos usam a mesma redação

- **ICMS** — Constituição Federal, Art. 155, § 2º, I: "será não-cumulativo,
  compensando-se o que for devido em cada operação (...) com o montante cobrado nas
  anteriores (...)".
- **IPI** — Constituição Federal, Art. 153, § 3º, II: "será não-cumulativo,
  compensando-se o que for devido em cada operação com o montante cobrado nas
  anteriores".

Mesma redação, mesma mecânica — por isso `ApuracaoPeriodo` é uma classe só para os dois
tributos, parametrizada por `tributo`, em vez de duas quase-iguais.

## Por que só ICMS e IPI

O roteiro deste bloco pede explicitamente "Apuração de ICMS e de IPI" — escopo
deliberado. PIS/COFINS não-cumulativo também compensa crédito e débito, mas por um
regime de apuração federal distinto (Lei 10.637/2002 e 10.833/2003, com DCTF/EFD-
Contribuições próprias) que não foi conferido nesta implementação.
`TRIBUTOS_APURAVEIS = frozenset({"ICMS", "IPI"})` é allowlist, não sugestão — estender
para "PIS"/"COFINS" sem antes ler essas leis repetiria o erro que este projeto existe
para evitar.

## `a_recolher` e `saldo_credor_a_transportar` são mutuamente exclusivos por construção

```python
@property
def a_recolher(self) -> Decimal:
    return max(self.saldo, ZERO)

@property
def saldo_credor_a_transportar(self) -> Decimal:
    return max(-self.saldo, ZERO)
```

Os dois nunca são diferentes de zero ao mesmo tempo — não por um `if/else` que alguém
poderia editar de um jeito que os dois passassem a valer juntos, mas porque `saldo` só
tem um sinal por vez e cada propriedade extrai só o seu lado.

## `apurar_periodo` lê pela conta, não por metadado

```python
debitos = sum(l.valor for l in lancamentos if l.conta_credito == f"{tributo} a Recolher")
creditos = sum(l.valor for l in lancamentos if l.conta_debito == f"{tributo} a Recuperar")
```

O nome da conta em `plano_de_contas.py` é o único vocabulário compartilhado entre quem
gera o lançamento (`lancamento.py`) e quem apura o período — evitar um segundo jeito de
marcar "isto é ICMS" (uma tag separada, um campo `tributo=` no `Lancamento`) que pudesse
divergir do primeiro. `Lancamento` de fato não carrega um campo de tributo — só débito,
crédito e valor —, e isso é suficiente porque o nome da conta já diz tudo que a apuração
precisa saber.

## Ainda por implementar

- **Saldo credor anterior é parâmetro, não persistido**: cada chamada de
  `apurar_periodo` recebe `saldo_credor_anterior` explicitamente — nenhum mecanismo
  ainda guarda o saldo de um período para o próximo automaticamente (isso pertence à
  camada de negócio/doctype, quando existir).
- **PIS/COFINS**: fora de escopo desta versão, ver acima.
- ~~Livro de apuração como documento~~ — o livro de papel foi dispensado pelo Ajuste
  SINIEF 02/2009 para quem é obrigado ao EFD; o artefato real é o registro digital,
  ver [sped-fiscal.md](sped-fiscal.md) (`contabil/efd_icms_ipi.montar_e110`).

## Arquivos

- `contabil/apuracao_periodo.py` — `ApuracaoPeriodo`, `apurar_periodo`; camada pura,
  sem Frappe, testável sem bench.

## Fontes

- Constituição Federal de 1988, Art. 155, § 2º, I (ICMS) e Art. 153, § 3º, II (IPI) —
  confirmados via o portal do STF (`portal.stf.jus.br/constituicao-supremo`) e fontes
  secundárias consistentes — consultado em 2026-08-30.
