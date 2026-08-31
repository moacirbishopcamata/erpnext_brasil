# CT-e: grupo `infDoc/infNFe` (referência à NF-e transportada)

Fecha outra lacuna de `docs/cte-estado.md`: a ponte de correlação entre o CT-e e a(s) NF-e(s)
cuja mercadoria ele transporta — o mesmo dado que o MDF-e vai precisar referenciar depois.

## O que é

`infDoc` (opcional só para redespacho intermediário e serviço vinculado a multimodal; nos demais
casos é sempre informado) é um `xs:choice` entre dois documentos originários:

- `infNF` — NF modelo 01/04 em papel, carrega o detalhamento fiscal inteiro (`vBC`, `vICMS`,
  `vBCST`, `vST`, `vProd`, `vNF`, `nCFOP`...). Caso legado, cada vez mais raro.
- `infNFe` — NF-e eletrônica, referenciada só pela `chave` de acesso (`TChDFe`, 44 posições).
  Nenhum outro dado fiscal é repetido — o CT-e não duplica o que já está na NF-e autorizada.

Só `infNFe` foi implementado. `infNF` fica documentado como fora de escopo — implementar exigiria
modelar um segundo grupo de campos fiscais completo para um caso em desuso.

## Reuso, não reimplementação

`fiscal/cte.py::montar_infnfe` não tem lógica própria de validação de chave — chama
`fiscal/documento/chave_acesso.py::ler_chave`, a mesma função usada para a chave da NF-e. O
layout de 44 posições e o cálculo do dígito verificador são idênticos entre os documentos da
família (NF-e, CT-e, MDF-e) — confirmado, não suposto, porque o próprio XSD do CT-e usa o mesmo
tipo `TChDFe` tanto para `chNFe` quanto para `chCTe` em outros grupos do documento.

Uma verificação a mais que a função faz, e que `ler_chave` sozinha não faz: recusa uma chave cujo
dígito de modelo não seja `55` (NF-e). Sem essa checagem, colar por engano a chave de outro CT-e
(modelo `57`) na lista de `infNFe` só falharia na rejeição da SEFAZ — a mesma categoria de defesa
em profundidade já usada em `montar_icms_uf_fim`/`calcular_difal` e no restante do projeto.

## Testado

5 testes (`test_cte.py`): uma chave, múltiplas chaves preservando ordem, lista vazia, chave com
dígito verificador errado (recusada por `ler_chave`), chave de CT-e recusada por não ser NF-e.

## Arquivos

- `erpnext_brasil/fiscal/cte.py` — `montar_infnfe`.
- `erpnext_brasil/tests/test_cte.py` — testes acrescentados à classe já existente.

## Fontes

- `github.com/nfephp-org/sped-cte`, `schemes/PL_CTe_400/cteTiposBasico_v4.00.xsd`, grupo
  `infCTeNorm/infDoc` (linhas 4119–4310 do arquivo baixado em 2026-08-31 — `infNF` em 4128,
  `infNFe` em 4271). Ver `docs/cte-estado.md` para o histórico da investigação.
