# Integração: extração real `Shipment` → referências fiscais

Fecha o item (3) pendente de `docs/integracao-cte-mapeamento.md`: "uma função de extração real
que produza a lista de `ReferenciaDocumentoFiscal`". Com `br_chave_acesso` existindo em
`Delivery Note` (`docs/integracao-chave-acesso.md`), a extração passa a ter de onde ler.

## O que `referencias_do_shipment` faz

Percorre `Shipment` → `Shipment Delivery Note` (tabela filha) → `Delivery Note` →
`br_chave_acesso`, e resolve o município de descarga a partir do `Address` de entrega do
próprio `Shipment` — devolve `list[ReferenciaDocumentoFiscal]`, pronta para
`mapeamento_cte.agrupar_por_municipio_descarga`.

## Município vem do `Shipment`, não de cada `Delivery Note` — decisão deliberada

Um `Shipment` pode agrupar várias `Delivery Note`, mas a viagem tem um único destino físico — o
MDF-e representa a viagem, não cada nota isoladamente (mesmo raciocínio de
`fiscal.mdfe_rodoviario` modelar veículo/motorista no MDF-e, não no CT-e). Resolver o
município por nota individualmente arriscaria fragmentar um único descarregamento físico por
causa de cadastro divergente entre notas do mesmo carregamento.

## Falha alta, não silenciosa

Se existe ao menos uma nota com chave preenchida mas o endereço de entrega não tem
`codigo_municipio_ibge`, a função levanta `CteExtracaoInvalida` em vez de descartar a
referência — perder um documento do `infDoc` em silêncio só apareceria na rejeição da SEFAZ.
Mesma disciplina de "falhar alto" já aplicada em `montar_infdoc`/`montar_ide` no resto do
projeto.

## Bug real corrigido antes do commit

A primeira versão da função tinha uma comprehension que buscava a chave via
`frappe.db.get_value` só para descartar o resultado (`if (chave := ...)`) e devolver
`linha.get("br_chave_acesso")` — um campo que **não existe** na tabela filha `Shipment
Delivery Note` (só `delivery_note`/`grand_total`, confirmado no schema). Reescrito como loop
simples antes de qualquer teste ou commit — nenhum código com esse bug chegou a ser versionado.

## O que ainda falta

- Wiring de verdade: nenhum `doc_event`/método whitelisted chama `referencias_do_shipment`
  ainda — a função existe e está correta, mas não é invocada em lugar nenhum do fluxo real
  (ex.: um botão "Montar infDoc" no `Shipment`, ou uma chamada automática ao criar o CT-e).
- Chave de **CT-e** (modelo `"57"`) — só NF-e é extraída aqui; quem contrata o transporte
  ainda não tem onde guardar a chave do CT-e recebido do transportador.
- Transmissão real ao SEFAZ (item (2) de `docs/integracao-cte-mapeamento.md`) — inalterado.

## Arquivos

- `erpnext_brasil/integracao/cte_extracao.py` — `CteExtracaoInvalida`,
  `referencias_do_shipment`.

Sem teste unitário dedicado — mesma disciplina de `integracao/party.py`/
`chave_acesso_documento.py`: módulo depende do Frappe, não testável sem bench.

## Fontes

- `erpnext/stock/doctype/shipment/shipment.json` e `shipment_delivery_note.json` (lidos
  diretamente do clone local do `erpnext`) — confirmam os nomes de campo usados
  (`delivery_address_name`, `shipment_delivery_note`, `delivery_note`).
