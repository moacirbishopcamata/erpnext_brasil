# Integração — chave de CT-e do lado de quem contrata o transporte

Fecha o item (4), última pendência de `docs/integracao-cte-mapeamento.md`: até agora,
`integracao/cte_extracao.py::referencias_do_shipment` só extraía chaves de **NF-e** (modelo
55) do lado de quem emite a mercadoria transportada. Faltava o lado simétrico: uma empresa
que **contrata** transporte recebe um CT-e da transportadora, não emite nada.

## Achado real, verificado antes de implementar: `Shipment` não tem link para `Purchase Invoice`

Lido diretamente `erpnext/stock/doctype/shipment/shipment.json` (core do ERPNext, não
suposto): `Shipment` não tem nenhum campo que vincule um `Purchase Invoice` de frete —
`carrier` é texto livre (nome do transportador, usado para integração com API de courier
externa), `pickup_supplier`/`delivery_supplier` não amarram fatura nenhuma. Diferente do
caso de NF-e (onde `Shipment Delivery Note` já existe como tabela filha pronta para
percorrer), não existe uma relação de doctype pronta do lado do CT-e — inventar uma
significaria supor uma estrutura de dados que o ERPNext não tem.

## O que foi implementado: `referencia_cte_do_documento_frete`

Em vez de tentar descobrir sozinha qual `Purchase Invoice` cobre qual `Shipment` (decisão
que cabe a quem chama, não a uma função de extração), a nova função opera sobre um
`Purchase Invoice` **já identificado** como fatura de frete: lê `br_chave_acesso`, decompõe
via `ler_chave` e **recusa** se a chave não for modelo `"57"` — mesma defesa em
profundidade já aplicada a `infEntrega`/`infDoc` em todo o projeto (uma fatura de frete com
chave de NF-e colada por engano é exatamente o erro que essa checagem existe para pegar).

`municipio_codigo`/`municipio_nome` são parâmetros explícitos, não derivados — o `Purchase
Invoice` sozinho não amarra a viagem/`Shipment` a que o frete se refere; é responsabilidade
de quem chama sabê-los (mesmo espírito de honestidade sobre limites de inferência já
praticado em `referencias_do_shipment`, que usa o endereço do `Shipment`, não de cada nota).

Devolve `None` quando `br_chave_acesso` está vazio — estado normal antes da fatura ter a
chave preenchida, não erro.

## Estado da frente de integração CT-e/MDF-e

Com este incremento, os quatro itens registrados em `docs/integracao-cte-mapeamento.md`
estão todos endereçados: (1) campo `br_chave_acesso`/`br_protocolo_autorizacao`
adicionados; (2) wiring da transmissão automática — deliberadamente não fechado, exige
certificado A1/homologação real; (3) extração do lado de NF-e (`referencias_do_shipment`);
(4) extração do lado de CT-e (`referencia_cte_do_documento_frete`). Sem teste dedicado
(mesma disciplina de `integracao/party.py`/`cte_extracao.py`: depende do Frappe, não
testável sem bench).
