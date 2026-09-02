# DeSTDA (Declaração de Substituição Tributária, Diferencial de Alíquota e Antecipação)

Retomada de uma frente registrada como **genuinamente bloqueada** em 2026-08-31: sem projeto
open-source de referência (nenhum `nfephp-org/sped-destda`) e duas tentativas de ler o manual
oficial (Ato COTEPE/ICMS 47/2015) tinham falhado — uma recusada por cautela de direitos autorais
da ferramenta de busca, outra por HTTP 403. Retomada com uma **fonte nova**, não repetindo a
mesma pergunta: documentação técnica de um ERP comercial (`documentacao.senior.com.br`) que
replica os registros e campos do leiaute para a própria geração do arquivo.

## Nível de confiança, declarado — mais baixo que a maioria dos módulos SPED/eSocial

Os **códigos de registro** e a **lista de campos** vêm de fonte secundária única — o texto do
Ato COTEPE não foi lido diretamente. O significado de `IND_SIT` (situação do registro `G605`)
tem corroboração de uma fonte só (uma segunda tentativa de checagem falhou por DNS
inacessível). Registrado aqui e no docstring do módulo, não escondido — mesmo padrão de
honestidade de `docs/cfop-transporte.md`.

## O que é

Arquivo texto pipe-delimited (mesma família de `contabil/sped_texto.py`, já usado em
EFD-ICMS/IPI e ECD) que declara, mensalmente, os valores de diferencial de alíquota,
antecipação tributária e substituição tributária devidos por empresas do Simples Nacional em
operações interestaduais — instituído pelo Ajuste SINIEF 12/2015.

## Escopo: núcleo mínimo de uma declaração

Implementados:

| Registro | Papel |
|---|---|
| `0000` | Abertura do arquivo, identificação do contribuinte |
| `0001` | Abertura do Bloco 0 (indicador de conteúdo) |
| `G001` | Abertura do Bloco G (mesmo indicador) |
| `G020` | Indicador de conteúdo (ISS/ICMS/Simples Nacional/recálculo/sem dados) e período |
| `G605` | Diferencial de alíquota/antecipação — valores totais |
| `G615` | Antecipação por UF de origem (venda para consumo final) |
| `G625` | Substituição tributária por UF de destino |
| `0990`/`G990` | Encerramento de bloco, com contagem de linhas |

Fora de escopo, documentado: `0002` (inscrições como substituto), `0005` (dados
complementares), `0030` (perfil do contribuinte — a fonte disponível tinha nomes de campo
ambíguos/repetidos, não modelado até uma fonte mais clara), `0100` (contabilista), `G600`/
`G610`/`G620` (totalizadores intermediários que sistemas geradores calculam a partir dos
registros de detalhe — este módulo modela só o que o contribuinte declara).

## Reuso

`montar_linha`/`formatar_campo` de `sped_texto.py` reaproveitados sem alteração — mesmo formato
já confirmado para EFD-ICMS/IPI e ECD (pipe-delimited, data `DDMMAAAA` sem separador, decimal
com vírgula).

## Arquivos

- `erpnext_brasil/contabil/destda.py` — `Identificacao`, `montar_0000`, `montar_0001`,
  `montar_g001`, `montar_g020`, `montar_g605`, `montar_g615`, `montar_g625`, `montar_0990`,
  `montar_g990`.
- `erpnext_brasil/tests/test_destda.py` — 12 testes.

## Fontes

- `documentacao.senior.com.br/goup/5.10.4/menu_controladoria/sped/estaduais/destda/` (páginas
  `destda.htm`, `bloco-0.htm`, `bloco-g.htm`), consultado em 2026-08-31.
- Ato COTEPE/ICMS 47/2015 e Ajuste SINIEF 12/2015 — citados pela fonte secundária como base
  legal, texto original ainda não lido diretamente.
