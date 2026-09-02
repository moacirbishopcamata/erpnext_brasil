# Integração CT-e/MDF-e: mapeamento de referências por município (`mapeamento_cte.py`)

Primeiro passo da camada `integracao/` para o trabalho de CT-e/MDF-e desta fase — mesmo papel
que `integracao/mapeamento.py` cumpre para a apuração fiscal: a costura entre dado já extraído
do ERPNext e a árvore de dataclasses que `fiscal/` exige.

## Achado que limitou o escopo: falta um campo básico

Antes de escrever a costura, verificado (não suposto) se o ERPNext já tem onde guardar a chave
de acesso de uma NF-e emitida. **Não tem** — confirmado por grep em `hooks.py`: a camada de
transmissão de NF-e (`integracao/transporte_sefaz.py`/`autorizacao_sefaz.py`) já existe e
devolve o resultado da autorização, mas não está ligada a nenhum `doc_event` que persista a
chave em campo nenhum. Isso é um gap **anterior e maior** que a integração do CT-e — sem ele,
qualquer função que lesse "a chave de acesso do Delivery Note" estaria lendo um campo
inexistente.

## Por isso este incremento modela só a tradução genérica

`agrupar_por_municipio_descarga` recebe uma lista de `ReferenciaDocumentoFiscal` (chave +
código/nome do município + modelo do documento) já resolvida por quem chama, e agrupa por
município na ordem de primeira aparição — o formato exato que `fiscal.mdfe.montar_infdoc` exige
(`docs/mdfe-infdoc.md`: "o `infDoc` do MDF-e organiza as referências por município de
descarregamento, não é lista plana"). Não lê nada do Frappe, não decide de onde vem a
referência — isso fica para quando o campo de chave de acesso existir de verdade.

## Reuso

Devolve `MunicipioDescarga` de `fiscal/mdfe.py` de verdade, não um dicionário parecido — testado
explicitamente (`test_devolve_municipiodescarga_de_verdade_nao_so_um_dict_parecido`) para que o
resultado alimente `montar_infdoc` sem nenhuma tradução a mais.

## O que falta para uma integração de verdade

1. **Fechado em seguida** — ver `docs/integracao-chave-acesso.md`: `br_chave_acesso`/
   `br_protocolo_autorizacao` adicionados aos quatro documentos com apuração fiscal, validados
   contra o layout de 44 posições.
2. Wiring da transmissão de NF-e a um `doc_event` que grave a chave/protocolo depois da
   autorização — hoje `transporte_sefaz.py` existe mas não é chamado por nenhum hook (não
   fechado: exigiria gerenciar certificado A1 e ambiente de homologação, sem como testar de
   ponta a ponta nesta investigação).
3. Uma função de extração real (`Shipment` → `Shipment Delivery Note` → `Delivery Note` →
   `br_chave_acesso`, agora que o campo existe) que produza a lista de
   `ReferenciaDocumentoFiscal` que este módulo consome.
4. Wiring simétrico do lado do CT-e (`Purchase Invoice`/documento de frete → chave de CT-e).

## Arquivos

- `erpnext_brasil/integracao/mapeamento_cte.py` — `ReferenciaDocumentoFiscal`,
  `agrupar_por_municipio_descarga`.
- `erpnext_brasil/tests/test_mapeamento_cte.py` — 6 testes.

## Fontes

- `erpnext/stock/doctype/shipment/shipment.json` e `shipment_delivery_note.json` (lidos
  diretamente do clone local do `erpnext`) — confirmam que `Shipment` já vincula `Delivery
  Note` via tabela filha, candidato natural a origem da lista de documentos transportados.
