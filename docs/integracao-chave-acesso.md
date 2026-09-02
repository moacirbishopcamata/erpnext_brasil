# Integração: campo `br_chave_acesso` — fecha o gap identificado no mapeamento CT-e/MDF-e

Segunda metade do que `docs/integracao-cte-mapeamento.md` deixou pendente como item (1):
"campo(s) que guardem a chave de acesso da NF-e emitida — pré-requisito de tudo o resto".

## O que foi adicionado

Dois campos em `Sales Invoice`/`Delivery Note`/`Purchase Invoice`/`Purchase Receipt`
(`setup/campos_documento.py`, seção "Documento fiscal eletrônico"):

- `br_chave_acesso` — a chave de 44 dígitos. Serve tanto para a NF-e **emitida** por este
  aplicativo (Sales Invoice/Delivery Note) quanto para a NF-e/CT-e **recebida de terceiro**
  (Purchase Invoice/Purchase Receipt) — o mesmo campo, dois sentidos, porque o formato é
  idêntico e o significado ("qual documento fiscal eletrônico corresponde a este registro") é
  o mesmo dos dois lados.
- `br_protocolo_autorizacao` — o número de protocolo devolvido pela SEFAZ na autorização.

Validado em `validate` (`integracao/chave_acesso_documento.py::validar_chave_acesso`), reusando
`fiscal.documento.chave_acesso.validar_chave` — a mesma validação de layout e dígito
verificador já usada em toda a família NF-e/CT-e/MDF-e. Mesma disciplina de
`party.validar_tax_id`: campo vazio é aceito (obrigatoriedade é configuração do DocType, não
desta validação).

## Deliberadamente não é a transmissão real

Este incremento **não** liga `integracao/transporte_sefaz.py` a nenhum evento. Preencher
`br_chave_acesso` automaticamente depois de uma autorização de verdade exigiria gerenciar
certificado A1, ambiente de produção/homologação e tratamento de erro de rede — infraestrutura
que esta investigação não tem como testar de ponta a ponta sem um certificado real e um
ambiente de homologação da SEFAZ. Por enquanto o campo é preenchido manualmente (ou por uma
integração futura que grave nele) — o que este incremento garante é que, preenchido, o valor é
uma chave válida.

## Consequência: `mapeamento_cte.py` já pode ser alimentado de verdade

Com o campo existindo, o item (3) pendente em `docs/integracao-cte-mapeamento.md` ("uma função
de extração real que produza a lista de `ReferenciaDocumentoFiscal`") passa a ter de onde ler —
antes não tinha nenhum campo fonte. A função de extração em si (Shipment → Shipment Delivery
Note → Delivery Note → `br_chave_acesso`) continua não implementada, próximo passo natural.

## Arquivos

- `erpnext_brasil/integracao/chave_acesso_documento.py` — `validar_chave_acesso`.
- `erpnext_brasil/setup/campos_documento.py` — dois campos novos em `CABECALHOS`.
- `erpnext_brasil/hooks.py` — `validar_chave_acesso` ligado ao `validate` dos quatro
  documentos que já recebem apuração fiscal completa.

Sem teste unitário dedicado — mesma disciplina de `integracao/party.py`: módulo depende do
Frappe, não é testável sem bench, e a regra de validação em si (`validar_chave`) já está
testada em `fiscal/documento/chave_acesso.py`/`test_chave_acesso.py`.
