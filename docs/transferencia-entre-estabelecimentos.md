# Transferência entre estabelecimentos: não é venda, não é isenta, e a regra mudou

Decisão de modelagem tomada em 2026-09-06: **cada estabelecimento é uma `Company` própria,
com CNPJ próprio.** Este documento registra o que essa decisão implica e o que foi
construído sobre ela.

## O que a decisão muda

Enquanto a modelagem estava em aberto, `docs/gaps.md` registrava "transferência entre
estabelecimentos não emite NF-e", com um `Stock Entry` de `Material Transfer` como
suspeito. Com estabelecimento = `Company`, **o suspeito era o errado**:

- Um `Stock Entry` só move estoque **dentro** de uma `Company` — os `Warehouse` pertencem a
  ela. Entre duas `Company`, ele nem é o documento possível.
- O ERPNext já modela operação entre empresas do mesmo cadastro: `Customer` com
  `is_internal_customer` + `represents_company`, e o `Delivery Note` ganha
  `inter_company_reference` apontando para o `Purchase Receipt` do outro lado.
- E `Delivery Note` **já está** na lista de documentos que este app trata fiscalmente.

Ou seja: a decisão do usuário não abriu trabalho de emissão — ela revelou que a emissão já
existia, e que o que faltava era o **tratamento fiscal** da operação.

## ⚠️ A regra fiscal mudou, e o que "todo mundo sabe" está desatualizado

Durante décadas a transferência entre estabelecimentos do mesmo dono destacava ICMS
normalmente. A **ADC 49** encerrou isso no STF: mercadoria que troca de estabelecimento
**sem trocar de titular** não sofre circulação jurídica, e não há fato gerador.

A **LC 204/2023** levou a decisão para a Lei Kandir (art. 12, § 4º). Derrubado o veto ao
§ 5º, o CONFAZ celebrou o **Convênio ICMS 109/2024**, que revogou o 178/2023 e vale desde
**1º/11/2024**.

O resultado é contraintuitivo e as duas leituras fáceis erram, em direções opostas:

| Leitura | Conclusão | Erro |
|---|---|---|
| "não incide" | não põe nada na nota | **perde o crédito** da mercadoria |
| "é como uma venda" | destaca imposto | **tributa** o que a lei diz não ser fato gerador |

O certo: **não incide o imposto, e o crédito é transferido — obrigatoriamente**, consignado
na própria NF-e, no campo do destaque.

## Os dois caminhos, e por que a escolha não é por nota

| Caminho | Base | O que acontece |
|---|---|---|
| **Regra** (cláusulas 1ª a 4ª) | LC 87/96, art. 12, § 4º | não incide; o crédito das operações anteriores é transferido |
| **Equiparação** (cláusula 6ª) | LC 87/96, art. 12, § 5º | por opção, a transferência é equiparada a operação tributada **para todos os fins** |

A opção pela equiparação é **anual e irretratável**, registrada até 31 de dezembro para
valer no ano seguinte. Por isso `transferir_credito(equiparado=True)` **levanta** em vez de
calcular: quem optou tributa a operação normalmente, e devolver um crédito ali daria ao
optante uma segunda conta de ICMS, paralela à correta.

## O limite do crédito (cláusula quarta)

O crédito transferido é o imposto apropriado nas operações anteriores, **limitado** à
aplicação da alíquota interestadual sobre uma destas bases:

1. o valor médio da entrada em estoque;
2. o custo de produção;
3. os custos de produção, para mercadoria não industrializada.

Qual das três usar **é do contribuinte** — inventar essa escolha seria decidir contabilidade
alheia. O que o app faz é calcular o limite, aplicá-lo, e **registrar qual base foi usada**:
duas transferências com limites diferentes não se explicam sozinhas meses depois.

Quando o crédito apropriado supera o limite, a diferença **fica no remetente**.
`CreditoTransferido.credito_retido_na_origem` existe para que isso não passe despercebido —
quem vê só o valor transferido não sabe que sobrou crédito para trás.

## A alíquota interestadual, e o Espírito Santo nos dois lados

Quem fixa a alíquota interestadual não é o estado, é o **Senado** (CF/1988, art. 155, § 2º,
IV) — por isso a tabela é nacional e cabe num módulo puro.

- **Resolução SF 22/1989** — 12% geral; **7%** do Sul/Sudeste (**exceto ES**) para
  Norte/Nordeste/Centro-Oeste **e o próprio ES**.
- **Resolução SF 13/2012** — **4%** para importado sem industrialização, ou com Conteúdo de
  Importação acima de 40%. Substitui as outras duas em qualquer par de UF.

⚠️ **O ES é a armadilha.** Ele é Sudeste e mesmo assim é **destino** de 7% sem ser **origem**
de 7%. Escrever "Sudeste manda a 7%" produziria 7% saindo do ES; escrever "destino é
N/NE/CO" esqueceria o ES, que também recebe a 7%. Uma tabela por região, sem o caso nomeado,
silencia os dois erros — e a diferença é de cinco pontos percentuais numa nota que ninguém
confere. É o teste-âncora da suíte.

Para Rondônia, na prática: **recebe** do Sul/Sudeste a 7% e **remete** a 12%.

## ⚠️ "Interno" no ERPNext não é "mesmo titular"

Esta é a distinção que o código teria errado mais facilmente.

`is_internal_customer` significa apenas que a contraparte representa outra `Company` do
mesmo cadastro — o que inclui **grupo econômico**. Empresas de um mesmo grupo têm **raízes
de CNPJ diferentes** e vendem umas às outras com incidência normal. A não incidência do
art. 12, § 4º vale só para o **mesmo titular**.

Por isso `mesmo_titular(cnpj_a, cnpj_b)` compara os **8 primeiros caracteres** — a raiz. O
CNPJ tem raiz (8) + ordem do estabelecimento (4) + DV (2); matriz é `0001`, filiais de
`0002` em diante. Comparar 12 faria dois estabelecimentos **nunca** serem do mesmo titular.

**Degradação segura:** sem os dois CNPJ, `mesmo_titular` devolve `False` e a operação segue
como venda. É a escolha que **mantém o imposto** — degradar para "transferência" faria o
tributo sumir por falta de cadastro.

## ⚠️ Entrada e saída não são espelho

Lido na tabela oficial da SEFAZ-PE, **baixada e conferida localmente** — e não é um detalhe
de redação:

| Código | Descrição oficial | Classifica por |
|---|---|---|
| `5.151`/`6.151` | Transferência de produção do estabelecimento | **origem** |
| `5.152`/`6.152` | Transferência de mercadoria adquirida ou recebida de terceiros | **origem** |
| `1.151`/`2.151` | Transferência para industrialização ou produção rural | **destino** |
| `1.152`/`2.152` | Transferência para comercialização | **destino** |

Quem remete classifica pelo que a mercadoria **é**; quem recebe, pelo que **vai fazer** com
ela. Em `cfop_venda`/`cfop_devolucao_venda` os dois lados usam o mesmo par `01`/`02` — aqui
não.

Exemplo concreto: mercadoria comprada de terceiro, transferida para ser industrializada no
destino, sai como **`5152`** e entra como **`1151`**. Pelo espelho entraria como `1152` — um
código que existe, é válido, e está errado.

Também têm código próprio: **`5557`/`6557`** material de uso e consumo (não é mercadoria,
não gera crédito) e **`5552`/`6552`** ativo imobilizado (crédito em 48 parcelas, LC 87/1996,
art. 20, § 5º). O mesmo código para os dois apagaria a diferença de crédito.

> **Nota de método.** A primeira consulta à tabela devolveu, para `5.151`, a descrição
> *"Entrada de mercadoria recebida em transferência…"* — que é de um código `1.xxx`, não de
> um `5.xxx`. Baixar a página e ler localmente foi o que pegou; aceitar o resumo teria
> gravado a descrição errada na docstring de um módulo fiscal.

## O que ficou fora, declarado

- **Transferência dentro do mesmo estado.** O Convênio 109/24 trata das remessas
  **interestaduais** (cláusula quinta). A interna fica com o RICMS do estado — para nós, o
  de Rondônia. Escrever regra nacional para ela seria invenção.
- **A escrituração do crédito na EFD.** A cláusula segunda manda lançar a débito no registro
  de saídas do remetente e a crédito no de entradas do destinatário. É Bloco C/E, e está nas
  pendências de `sped-fiscal.md`.
- **O Conteúdo de Importação.** O limite de 40% da Resolução 13/2012 depende da ficha CI do
  produto, dado do contribuinte. Quem chama informa `importado=True`; decidir por ele
  exigiria a ficha.

## Fontes

- **ADC 49** (STF) — ausência de fato gerador na transferência entre estabelecimentos do
  mesmo titular.
- **LC 204/2023** — art. 12, § 4º e § 5º da LC 87/1996.
- **Convênio ICMS 109/2024** (CONFAZ) — cláusulas 1ª a 6ª, lidas no texto oficial; revogou o
  Convênio 178/2023, efeitos desde 1º/11/2024.
- **Resolução SF 22/1989** e **Resolução SF 13/2012** — alíquotas interestaduais.
- **Tabela CFOP da SEFAZ-PE** — baixada e conferida linha a linha para os oito códigos.
- `customer.json`, `supplier.json`, `delivery_note.json` do erpnext **v16** —
  `is_internal_customer`, `is_internal_supplier`, `represents_company`,
  `inter_company_reference`.
