# Sugestão de CFOP em Pedidos, Documentos Fiscais e Subcontratação

Fecha a lacuna registrada em `docs/pcp-estado.md`: `fiscal/cfop.py` já sabia
calcular o código certo, mas nenhum documento chamava. Nomenclatura do campo novo
decidida pelo próprio Claude, a pedido explícito do usuário ("pode decidir a
melhor nomenclatura, você mesmo").

## Dois campos novos no `Item`, deliberadamente separados de um campo existente

- **`Item.producao_propria`** (Check) — "este item é fabricado por esta empresa,
  não comprado pronto?". Alimenta `cfop_venda(producao_propria=...)`.
- **`Item.finalidade_compra`** (Select: Industrialização/Comercialização) —
  "para que esta empresa compra este item?". Alimenta
  `cfop_compra(finalidade=...)`.

Nenhum dos dois reaproveita `br_destinado_a_revenda`
(`Operacao.destinado_a_industrializacao_ou_comercio`), que decide uma coisa
diferente: se o IPI compõe a base do ICMS (consumo final × não consumo final,
Art. 155 §2º XI CF) — um eixo que **não distingue** industrialização de
comercialização entre si, o eixo que o CFOP precisa. Ver `docs/pcp-estado.md`
para o processo que evitou esse erro antes de escrever qualquer código.

## `mesmo_estado`: comparando a UF da empresa com a da outra parte

`integracao/party.uf_da_parte` (antes `_uf_da_parte`, privada — tornada pública
porque ganhou uma segunda chamadora real, motivo genuíno de generalizar, não
suposição de uso futuro) já sabia achar a UF de qualquer parte a partir do
endereço padrão, inclusive da própria `Company`. `cfop_sugestao.py` só chama essa
função dos dois lados (empresa × cliente/fornecedor) e compara.

## Sugestão nunca vira valor confirmado — e por que isso é sempre seguro aqui

`br_cfop_sugerido` é somente leitura, recalculado a cada `validate`. Diferente de
um campo que o usuário edita e uma sugestão pisaria por cima, esta coluna nunca
tem um "valor confirmado" — é sempre e só uma sugestão, então recalcular sempre é
seguro. Sem dado suficiente (item sem `producao_propria` marcado, sem
`finalidade_compra` escolhida, ou UF que não pôde ser determinada em algum dos
dois lados), o campo fica vazio — nunca um CFOP inventado.

## Onde entra: seis documentos, duas regras diferentes

| Documento | Regra | Função |
|---|---|---|
| `Sales Order`, `Sales Invoice`, `Delivery Note` | Depende de `Item.producao_propria` | `cfop_venda` |
| `Purchase Order`, `Purchase Invoice`, `Purchase Receipt` | Depende de `Item.finalidade_compra` | `cfop_compra` |
| `Subcontracting Order` (remessa) | Só `mesmo_estado`, nenhum campo do Item | `cfop_remessa_para_industrializacao` |
| `Subcontracting Receipt` (retorno) | Só `mesmo_estado`, nenhum campo do Item | `cfop_retorno_de_industrializacao` |

`Sales Invoice`/`Delivery Note`/`Purchase Invoice`/`Purchase Receipt` já tinham
apuração fiscal completa (`integracao/documento.apurar_impostos`) — a sugestão de
CFOP roda no mesmo `validate`, como item adicional da lista, não substituindo
nada. `Sales Order`/`Purchase Order`/`Subcontracting Order`/`Subcontracting
Receipt` não têm apuração (documentos internos, sem chave de acesso, sem
assinatura) — só a sugestão de CFOP, útil para quando o pedido virar NF-e depois.

## Estado de verificação: não exercitado contra um bench real

Mesma situação de `integracao/documento.py`/`integracao/party.py`: depende do
Frappe (`frappe.get_cached_doc`), sem bench disponível nesta sessão para rodar de
ponta a ponta. A regra pura (`fiscal/cfop.py`) está testada exaustivamente sem
bench (34 testes); esta camada de costura não tem teste automatizado, mesmo
motivo já registrado para o resto da camada `integracao/`.

## Arquivos

- `setup/custom_fields.py` — `Item.producao_propria`, `Item.finalidade_compra`.
- `setup/campos_documento.py` — `br_cfop_sugerido` nas linhas de item de dez
  doctypes (os quatro com apuração completa + os seis novos).
- `integracao/party.py` — `uf_da_parte` (antes privada).
- `integracao/cfop_sugestao.py` — `sugerir_cfop_compra_venda`,
  `sugerir_cfop_subcontratacao`; camada fina, não testável sem bench.
- `hooks.py` — `doc_events` dos seis documentos novos.
