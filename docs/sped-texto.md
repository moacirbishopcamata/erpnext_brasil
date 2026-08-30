# Serialização de texto do SPED (linha pipe-delimited)

Décimo incremento do bloco contábil — a camada que faltava para transformar os `dict`s
que `efd_icms_ipi.py`, `ecd_i050.py`, `ecd_i150.py` e `ecd_i200.py` já produzem numa
linha de arquivo de verdade.

## Por que separado dos módulos que montam cada registro

"Quais valores vão em quais campos" e "como formatar isso como texto" são
responsabilidades diferentes — resolver as duas juntas arriscaria acertar o valor e
errar o formato, ou vice-versa, sem teste dedicado para cada uma. Essa separação já
estava planejada desde o primeiro registro implementado (E110): cada doc do bloco
SPED/ECD registrava "formato de saída é `dict`, não a linha de texto" como decisão
deliberada, não pendência esquecida. Este módulo fecha essa decisão.

## Formato confirmado

- Campos separados por `|`; a linha **começa e termina** com `|`.
- Data: `DDMMAAAA`, **sem separador** — uma primeira busca encontrou uma fonte que
  afirmava `DD/MM/AAAA` (com barras); uma segunda busca, com um exemplo literal de
  arquivo real (`01012024`, não `01/01/2024`), corrigiu isso antes de qualquer código
  ser escrito.
- Numérico: vírgula como separador decimal (`1234,56`, nunca `1234.56`).
- Campo vazio (texto ou data): string vazia entre os dois `|` — nunca máscara, nunca
  `None`/`"None"` literal.
- Campo de texto não pode conter `|` — é o próprio delimitador; `montar_linha`/
  `formatar_campo` rejeitam explicitamente em vez de produzir uma linha ambígua.

## `montar_linha` não conhece o significado de nenhum campo

Recebe qualquer `dict` que este bloco já produz (`{"REG": "...", campo: valor, ...}`) e
formata na ordem em que o `dict` já os tem — a ordem correta é responsabilidade de quem
montou o `dict` (cada `montar_e110`/`montar_i050`/etc. já constrói na ordem oficial do
registro), não desta função. Testado com registros de verdade
(`TestIntegracaoComRegistrosReais`), não só `dict`s inventados para o teste.

## Ainda por implementar

- **Sequenciamento de registros relacionados num arquivo** — `ecd_i200.montar_i200_i250`
  devolve `(I200, [I250, I250])` e `ecd_i050.montar_i051` devolve `(nome_da_conta,
  I051)`, exatamente porque a posição relativa dentro do arquivo final importa (I250
  depois do I200 correspondente; I051 depois do I050 da conta certa) — este módulo só
  formata uma linha isolada, não decide a ordem entre linhas relacionadas.
- **Blocos de abertura/fechamento** (registro `0000`, totalizadores por bloco, registro
  `9999` de encerramento) — nenhum gerado ainda; um arquivo SPED real não é só a
  concatenação das linhas de dado.
- **Escrita em arquivo** (quebra de linha, codificação) — `montar_linha` devolve a
  string de uma linha; escrever várias linhas separadas por `\n` num arquivo `.txt`
  fica para quem monta o arquivo inteiro.

## Arquivos

- `contabil/sped_texto.py` — `formatar_campo`, `montar_linha`; camada pura, sem Frappe,
  testável sem bench.

## Fontes

- Formato de campo (pipe-delimited, tipos de campo, data sem separador) — confirmado
  em fontes secundárias consistentes, com correção de uma primeira leitura errada sobre
  o formato de data (ver acima) — consultado em 2026-08-30.
