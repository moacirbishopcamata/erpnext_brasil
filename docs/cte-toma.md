# CT-e: tomador do serviço (`ide` → `toma3`/`toma4`)

Fecha a última peça do CT-e que tinha estrutura mapeada em `docs/cte-estado.md` mas nenhuma
função de montagem — o `xs:choice` de `ide` que identifica quem paga o frete.

## Os dois casos, e por que são tão diferentes em tamanho

- **`toma3`** — o tomador é uma das partes já identificadas no próprio CT-e (código
  `TOMADOR_REMETENTE`/`TOMADOR_EXPEDIDOR`/`TOMADOR_RECEBEDOR`/`TOMADOR_DESTINATARIO`, valores
  `"0"`–`"3"`). O layout não pede mais nada: reaproveita os dados do grupo correspondente
  (`rem`/`exped`/`receb`/`dest`), então `montar_toma3` só valida o código.
- **`toma4`** — o tomador é "Outros" (`TOMADOR_OUTROS`, `"4"`), alguém que não é nenhuma das
  partes já citadas. Aqui o layout exige cadastro completo: CNPJ/CPF (escolha exclusiva, mesmo
  padrão do destinatário da NF-e), IE opcional, nome, nome fantasia opcional, telefone opcional,
  **endereço obrigatório** (`enderToma`, sem `minOccurs="0"` no XSD — diferente de `xFant`/
  `fone`/`email`, que são opcionais) e e-mail opcional.

## Ordem dos campos — não é estética, é `xs:sequence`

O XSD ordena `toma4` como `toma`, `CNPJ`|`CPF`, `IE`, `xNome`, `xFant`, `fone`, `enderToma`,
`email` — confirmado por leitura direta (`cteTiposBasico_v4.00.xsd`, linhas 3038–3113).
`montar_toma4` monta o dicionário nessa ordem exata; embaralhar a ordem de inserção produziria
XML que passa despercebido em Python mas que o schema do SEFAZ rejeitaria (`xs:sequence` é
ordem estrita, diferente de `xs:all`). Testado explicitamente
(`test_ordem_dos_campos_segue_o_xsd`).

## Reuso

`montar_toma4` reusa `validar_cpf_cnpj` de `fiscal/validators.py` — a mesma validação que
`fiscal/documento/nfe.py::montar_dest` já usa para o destinatário da NF-e. `CteInvalido` é uma
exceção nova (mesmo formato de `NFeInvalida`: mensagem + campo) — o CT-e ainda não tinha uma
exceção genérica para erro de montagem de documento (só `ChaveInvalida` e `RntrcInvalido`, cada
uma específica do seu próprio dado).

## Arquivos

- `erpnext_brasil/fiscal/cte.py` — `TomadorOutros`, `montar_toma3`, `montar_toma4`,
  `CteInvalido`.
- `erpnext_brasil/tests/test_cte.py` — 10 testes novos (`TestMontarToma3`, `TestMontarToma4`).

## Fontes

- `github.com/nfephp-org/sped-cte`, `schemes/PL_CTe_400/cteTiposBasico_v4.00.xsd`, grupo
  `ide/toma3`/`ide/toma4` (linhas 3002–3113 do arquivo baixado em 2026-08-31). Ver
  `docs/cte-estado.md` para o histórico da investigação.
