# Configurações da EFD-ICMS/IPI no ERPNext

Lembrete direto do usuário — "não esqueça das configurações de todos esses arquivos
eletrônicos". Os módulos do EFD (`contabil/efd_bloco_0.py`, `efd_bloco_c.py`,
`efd_bloco_9.py`, `efd_icms_ipi.py`, `efd_icms_st.py`, `efd_icms_difal.py`) são funções
puras: corretas para testar sem bench, mas exigiriam de quem chama datilografar CNPJ,
inscrição estadual, código IBGE, NCM de novo — dado que já está cadastrado. Este
documento registra os campos criados para fechar essa lacuna e a camada que os lê.

Mesma disciplina já aplicada ao certificado A1 (`docs/certificado-a1-configuracao.md`)
e à ECF (`integracao/ecf_dados_empresa.py`).

## Campos novos, e por que cada um precisou existir

Nenhum destes existia no ERPNext nem neste app; sem eles o registro correspondente não
tem de onde vir.

| Campo | DocType | Registro | Por quê |
|---|---|---|---|
| `br_efd_perfil` | Company | `0000` / `IND_PERFIL` | A, B ou C. **Não é escolha da empresa**: a SEFAZ do estado define, e o perfil decide quais registros o arquivo precisa conter — por isso é cadastro, não parâmetro de chamada |
| `br_efd_atividade` | Company | `0000` / `IND_ATIV` | Industrial/equiparado ou outros. Entidade identificada por CPF só pode ser "outros" (regra do layout, já checada em `Identificacao`) |
| `br_efd_versao_leiaute` | Company | `0000` / `COD_VER` | Vale a versão vigente na data final da escrituração e muda com o tempo; constante no código envelheceria em silêncio |
| `suframa` | Company | `0000` / `SUFRAMA` | **Achado real**: `Customer`/`Supplier` já tinham o campo, a `Company` não — a lacuna era só do lado da própria empresa |
| `br_efd_tipo_item` | Item | `0200` / `TIPO_ITEM` | Obrigatório e **sem equivalente nativo** — ver a seção abaixo |
| `br_efd_codigo_genero` | Item | `0200` / `COD_GEN` | Capítulo da NCM (Tabela 4.2.1), obrigatório para quem apresenta o Bloco H |
| `br_ex_ipi` | Item | `0200` / `EX_IPI` | Exceção da TIPI aplicável ao NCM do item |

## Por que `TIPO_ITEM` não podia reaproveitar campo existente

Este app já tinha `Item.producao_propria` e `Item.finalidade_compra`. Os dois respondem
a **outra pergunta** — qual CFOP usar —, não à classificação de estoque do Fisco:

- um item de produção própria pode ser `04 - Produto Acabado` **ou** `05 - Subproduto`;
- uma compra para industrialização pode virar `01 - Matéria-Prima`, `02 - Embalagem`
  **ou** `10 - Outros insumos`.

Não há função de um para o outro. Deduzir o `TIPO_ITEM` a partir deles acertaria no caso
comum e erraria em silêncio no resto — o oposto do que este projeto faz. É campo próprio.

## A tela e o arquivo saem da mesma tabela

As opções do Select de `br_efd_tipo_item` são **derivadas** de
`efd_bloco_0.TIPOS_ITEM`, a mesma tabela que valida o registro — mesma técnica de
`ORIGENS_MERCADORIA`, que sai da tabela normativa em vez de ser redigitada.

`tests/test_custom_fields_efd.py` fecha essa costura com teste: confere que o conjunto
de códigos do Select é exatamente o que o registro aceita, e — mais forte que comparar
listas — **constrói um `Item` real com cada opção da tela**. Se alguém acrescentar um
valor num lugar só, o teste quebra antes de o usuário descobrir com o arquivo recusado.

## A camada que lê os cadastros

`integracao/efd_dados_cadastrais.py`:

- `montar_identificacao_0000(company, address, data_inicial, data_final, finalidade)`
- `montar_participante_0150(doctype, nome, address="")`
- `montar_item_0200(item_code)`

Decisões registradas:

- **`address` é explícito, não deduzido.** A `Company` pode ter vários `Address`
  vinculados e o ERPNext não tem um "endereço fiscal" único sem ambiguidade — quem chama
  decide, mesma disciplina de `ecf_dados_empresa.montar_dados_cadastrais_0030` e de
  `cte_extracao` não adivinhar qual fatura é a de frete.
- **CPF × CNPJ sai de `tax_id` pelo comprimento** (14 = CNPJ, 11 = CPF), sem campo
  paralelo — `tax_id` é onde este projeto sempre guarda o documento.
- **Sem `tax_id`, os dois campos ficam vazios**: participante estrangeiro é caso válido
  no `0150`, que não exige nenhum dos dois (só `COD_PAIS`).
- **O Select guarda `"código - descrição"`, o registro quer só o código.**
  `_codigo_do_select` faz a extração num lugar só, em vez de cada chamador fatiar a
  string do seu jeito.
- **`data_inicial`/`data_final`/`finalidade` continuam parâmetros explícitos** — são
  decisões de cada entrega, não dado cadastral estável.

## O que ainda não é configurável

- **`COD_PAIS` do participante** é fixado em `01058` (Brasil) por enquanto. A tabela de
  países do SPED (item 3.2.1, códigos do BACEN) não está modelada, e o `Country` do
  ERPNext não carrega esse código — participante estrangeiro exigiria a tabela ou um
  campo novo. Registrado como lacuna, não escondido.
- **Códigos de ajuste por UF** (`COD_AJ_APUR`, tabela 5.1.1 de cada SEFAZ) continuam
  vindo prontos de quem chama, como já registrado em `docs/sped-fiscal.md`.
