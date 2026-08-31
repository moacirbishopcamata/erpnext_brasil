# Levantamento de estado: PCP/Manufatura (produção, matéria-prima, rastreabilidade)

Mesma disciplina de `docs/rh-estado-hrms.md`/`docs/rh-estado-esocial.md` — levantar
antes de implementar. Pedido do usuário: "Roteiro de produção (PCP, matéria-prima,
produto, rastreabilidade de produção)".

## O módulo já existe inteiro no ERPNext core — não é uma frente para criar

Confirmado (não suposto) em `erpnext/manufacturing/doctype/` e
`erpnext/stock/doctype/`: BOM (lista de materiais), `BOM Creator`, `Routing`/
`Operation`/`Workstation` (roteiro de produção), `Work Order`/`Job Card`
(ordem de produção, apontamento de chão de fábrica), `Production Plan`/
`Master Production Schedule` (planejamento — MPS/MRP), `Batch`/`Serial No`/
`Serial and Batch Bundle` (rastreabilidade de lote/série, com data de validade).
Nada disso precisa ser construído — já está lá, maduro, usado por milhares de
instalações. O que falta é olhar com lente brasileira: onde a legislação fiscal
brasileira exige algo que o core não modela.

## Gap real e concreto encontrado: Subcontratação sem tratamento fiscal

`Subcontracting Order`/`Subcontracting Receipt` (industrialização por encomenda de
terceiro) não recebem nenhum `doc_event` fiscal — mesmo gap já registrado para
`Sales Order`/`Purchase Order`. **Resolvido em parte**: `fiscal/cfop.py` ganhou os
quatro códigos de industrialização por encomenda (`5901`/`6901`/`1901`/`2901`/
`1902`/`2902`/`5902`/`6902`, ver `docs/cfop.md`) — a peça de **cálculo** existe
agora. A peça de **integração** (`doc_events` de verdade nesses doctypes) ainda não
foi feita — ver próxima seção para o motivo.

## Por que a integração automática não foi feita ainda: um campo quase reaproveitado errado

Ao planejar wire a sugestão de CFOP em `Sales Invoice`/`Purchase Invoice` via
`doc_events`, cogitei reaproveitar o campo já existente `br_destinado_a_revenda`
(que alimenta `Operacao.destinado_a_industrializacao_ou_comercio` em
`fiscal/impostos/apuracao.py`) como o indicador de `finalidade` para
`cfop_compra`/`cfop_venda`. **Verificado antes de implementar, não depois**: esse
campo **não serve** para isso. Seu significado real, confirmado lendo onde é
consumido (a regra de o IPI compor ou não a base do ICMS, Art. 155 §2º XI da CF), é
"a operação é destinada a industrialização **ou** comercialização" — um booleano
que distingue **consumo final** de **não consumo final**, não que distingue
industrialização de comercialização entre si. Usá-lo para `FINALIDADE_INDUSTRIALIZACAO`
× `FINALIDADE_COMERCIALIZACAO` produziria CFOP errado em silêncio — o tipo de bug que
só apareceria numa fiscalização, exatamente o cenário que a disciplina deste projeto
existe para evitar. Documentado aqui como o processo de verificação, não escondido —
mesma categoria do bug de dígito faltante já pego pelo teste de importação/exportação.

## O que falta de verdade para fechar essa integração

Um **campo novo, explícito** — não inferido de nenhum campo existente — que
distinga industrialização de comercialização (para compra) e produção própria de
mercadoria de terceiros (para venda). Candidatos, nenhum decidido ainda:

- Um campo no `Item` (`br_producao_propria`, Check) — "este item é produzido por
  nós, não comprado pronto?" — serviria `cfop_venda(producao_propria=...)`
  diretamente, e é uma propriedade que normalmente não muda por documento (um item
  ou é sempre fabricado aqui, ou é sempre revendido como veio).
- Um campo separado para a intenção da compra (`br_finalidade_compra`, Select:
  "Industrialização"/"Comercialização") — diferente do já existente
  `br_destinado_a_revenda`, que continua servindo só a regra de IPI-na-base.

Não implementado — decisão de onde esse campo mora e como se chama fica para
quando o usuário confirmar, não para ser suposto.

## Rastreabilidade: já cobre o que a maioria da legislação brasileira exige

`Batch` (lote) já tem `expiry_date`, `batch_qty`, e histórico de movimentação via
`Stock Ledger Entry`; `Serial No` cobre rastreio unitário. Setores regulados
específicos (ANVISA para medicamentos, INMETRO para instrumentos de medição) têm
exigências além disso (ex. rastreabilidade até o fornecedor do insumo, formato de
lote específico) — não investigado, só relevante se o negócio for desse setor.

## Ainda por implementar / decidir

- O campo explícito de finalidade (compra) / produção própria (venda), acima.
- `doc_events` de fato em `Sales Order`/`Purchase Order`/`Subcontracting Order`/
  `Subcontracting Receipt` usando esse campo + `fiscal/cfop.py`.
- NF-e de simples remessa (CFOP `5949`/`6949`, movimentação sem transferência de
  titularidade) — não pesquisado.
- Exigências setoriais de rastreabilidade (ANVISA/INMETRO) — fora de escopo até
  haver um negócio regulado de verdade usando o app.

## Arquivos

- Nenhum código novo neste levantamento — só `fiscal/cfop.py` (já commitado
  separadamente, ver `docs/cfop.md`) resultou diretamente dele.

## Fontes

- `erpnext/manufacturing/doctype/`, `erpnext/stock/doctype/`,
  `erpnext/subcontracting/doctype/` (código-fonte lido diretamente do clone
  local) — usados para confirmar o que já existe e o que falta. Consultado em
  2026-08-31.
