# CNAB 240: Segmentos T e U do retorno de cobrança

Sucessor do CNAB 400 (`docs/boleto.md` cita `cnab400_retorno.py`, o formato mais
antigo já coberto). CNAB 240 é o formato federado pela FEBRABAN — mais recente,
mais uniforme entre bancos.

## Um título, dois registros — não um só como no CNAB 400

No CNAB 240, cada título de cobrança no retorno gera **dois** registros
consecutivos: **Segmento T** (identifica o título, `identificacao_titulo`,
20 posições) seguido de **Segmento U** (valor pago e data da ocorrência). O
pareamento T→U (que os dois registros pertencem ao mesmo título) não é verificado
por este módulo — quem lê o arquivo linha a linha garante a ordem.

## Posições confirmadas contra dois bancos independentes — mais forte que o CNAB 400

`cnab400_retorno.py` teve que se contentar com uma única fonte técnica (nenhuma
segunda fonte disponível para cruzar posição a posição). Aqui foi possível fazer
melhor: as posições foram lidas nas configurações CNAB 240 de **dois bancos
diferentes** (Banco do Brasil e Bradesco, `glauberportella/cnab-layouts`) e batem
exatamente:

| Campo | Segmento | Posição | Confirmado em |
|---|---|---|---|
| `codigo_movimento` | T e U | 16-17 | BB e Bradesco |
| `identificacao_titulo` | T | 38-57 | BB e Bradesco |
| `valor_pago` | U | 78-92 | BB e Bradesco |
| `data_ocorrencia` | U | 138-145 | BB e Bradesco |

Ainda não é a especificação oficial FEBRABAN lida diretamente — o PDF oficial
veio como imagem/fonte codificada, ilegível às ferramentas de busca (mesmo padrão
de várias fontes bancárias e governamentais grandes deste projeto). Mas
concordância entre dois bancos independentes é uma confiança maior que a fonte
única do CNAB 400.

## `codigo_movimento`: hipótese de trabalho, não confirmada como a mesma tabela

O CNAB 240 unificou boa parte do que divergia entre bancos no CNAB 400 — é
razoável supor que o código de movimento da cobrança seja a mesma tabela nacional
já usada em `cnab400_retorno.CODIGOS_OCORRENCIA`/`FOI_PAGO` (os valores comuns —
`02`, `03`, `06`, `09`, `17` — aparecem com o mesmo significado nas fontes
consultadas para os dois formatos). `cnab240_retorno.py` reaproveita
`foi_pago`/`CODIGOS_OCORRENCIA` do CNAB 400 explicitamente, mas isso é uma
**hipótese de trabalho, não uma confirmação de identidade entre as duas tabelas**
— quem for usar isto contra um banco real deve conferir antes.

## `identificacao_titulo`, não "nosso número"

As duas fontes usam esse nome para o campo que seria o equivalente ao
`nosso_numero` do CNAB 400 — mantido assim de propósito, para não presumir que os
dois formatos usam exatamente o mesmo conceito de identificação por trás de nomes
diferentes.

## Data com ano completo, não 2 dígitos

`data_ocorrencia` tem 8 posições (`DDMMAAAA`) no CNAB 240, contra 6
(`DDMMAA`) no CNAB 400 — o formato mais novo evita a suposição de século que
`cnab400_retorno._data_ddmmaa` precisa fazer.

## Arquivos

- `contabil/cnab240_retorno.py` — `SegmentoT`, `SegmentoU`, `ler_segmento_t`,
  `ler_segmento_u`, `foi_pago` (reexportado de `cnab400_retorno.py`); camada pura,
  sem Frappe, testável sem bench.

## Fontes

- `github.com/glauberportella/cnab-layouts`, `config/bb/cnab240/cobranca.yml` e
  `config/bradesco/cnab240/cobranca.yml` — configurações YAML de dois bancos
  independentes, usadas para confirmar as posições por concordância cruzada. Não é
  a especificação oficial FEBRABAN. Consultado em 2026-08-31.
