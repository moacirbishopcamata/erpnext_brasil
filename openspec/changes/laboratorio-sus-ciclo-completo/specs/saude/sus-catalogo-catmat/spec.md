## Purpose

Dar ao módulo um catálogo de fármacos, reagentes e insumos codificado pelo CATMAT (Catálogo de Materiais do governo federal, com códigos
`BR…` na saúde), no mesmo desenho da tabela de medicamentos do e-SUS APS (LEDI), validado contra o catálogo oficial, para que estoque, produção
e integrações falem a mesma identificação e para que item inexistente ou inativo não entre em uso.

## ADDED Requirements

### Requirement: Tabela de medicamentos no desenho do e-SUS
O sistema SHALL manter o catálogo de medicamentos com os cinco campos da tabela CATMAT do e-SUS APS LEDI: **código CATMAT**, **princípio
ativo**, **concentração**, **forma farmacêutica** e **unidade de fornecimento**, e SHALL aceitar a carga dessa tabela sem perda de nenhum
campo.

#### Scenario: Carga da tabela do e-SUS
- **WHEN** a tabela de medicamentos do e-SUS APS LEDI é carregada
- **THEN** cada linha vira um registro com os cinco campos preservados

### Requirement: Código CATMAT canônico
O sistema SHALL guardar o código na forma canônica `BR` seguida de **sete dígitos com zeros à esquerda**, que corresponde ao `codigoItem`
numérico do catálogo oficial (por exemplo, `BR0268315` é o item 268315). O sistema SHALL normalizar variantes de entrada (sem zeros à
esquerda, com espaço) para a forma canônica, mantendo o código original, e SHALL recusar o que não normalizar de forma inequívoca.

#### Scenario: Código sem zeros à esquerda
- **WHEN** a carga traz `BR393493`
- **THEN** o registro é guardado como `BR0393493`, com o código original preservado

#### Scenario: Código que não normaliza
- **WHEN** a carga traz um código com barra ou caracteres estranhos
- **THEN** a linha vai à pendência de curadoria e não é carregada em silêncio

### Requirement: Apresentação como sub-registro do item
O sistema SHALL tratar o sufixo `-N` que o e-SUS acrescenta ao código (por exemplo, `BR0270558-1`, `-2`, `-3` para frascos de 80, 100 e 120 ml do
mesmo xarope) como **apresentação** do mesmo item CATMAT, guardando-o em campo próprio e usando o par (código, apresentação) como chave de
estoque. O catálogo oficial não define esse sufixo; ele é convenção do e-SUS e SHALL ser preservado para interoperar.

#### Scenario: Três frascos do mesmo item
- **WHEN** três linhas diferem só pelo sufixo e pela unidade de fornecimento
- **THEN** o catálogo tem um item CATMAT com três apresentações

### Requirement: Validação contra o catálogo oficial
O sistema SHALL validar cada código contra o catálogo oficial do Compras.gov.br (módulo de material), registrando classe, grupo, PDM (padrão
descritivo de material), NCM, situação do item e a data de atualização. Código inexistente SHALL ser recusado. Item **inativo** SHALL ficar
bloqueado para nova entrada e novo uso, preservando o histórico dos movimentos anteriores.

#### Scenario: Item inativo
- **WHEN** um código existe no catálogo oficial com situação inativa
- **THEN** ele não pode receber nova entrada nem ser usado, e o histórico permanece

### Requirement: Catálogo oficial vence a tabela do e-SUS
O sistema SHALL tratar o catálogo oficial como fonte, e a tabela do e-SUS (versão 4.2.0, alterada em 26/04/2021) como semente e compatibilidade.
Divergência de situação, classe ou descrição entre as duas SHALL ser listada para conciliação, e o oficial prevalece.

#### Scenario: Item ativo no e-SUS e inativo no oficial
- **WHEN** a conciliação encontra item ativo na tabela do e-SUS e inativo no catálogo oficial
- **THEN** o item fica bloqueado e a divergência é listada

### Requirement: Mesmo modelo para reagentes e demais insumos
O sistema SHALL usar o código CATMAT canônico também para reagentes (classe 6550, substâncias para diagnóstico *in vitro*, reagentes, conjuntos e
jogos para teste) e demais insumos de saúde (como as classes 6515 e 6545), com descrição e unidade de fornecimento, de modo que
`saude/sus-estoque-de-reagentes-e-insumos` identifique todo item por (código, apresentação).

#### Scenario: Reagente da classe 6550
- **WHEN** um reagente é cadastrado com código CATMAT da classe 6550
- **THEN** ele é validado contra o catálogo oficial e usa o mesmo formato canônico dos medicamentos

### Requirement: Carga versionada com origem
O sistema SHALL registrar, a cada carga do catálogo, a origem (API do Compras.gov.br ou tabela do e-SUS), a versão ou data, o número de linhas
carregadas, rejeitadas e pendentes, e SHALL permitir repetir a carga sem duplicar registros.

#### Scenario: Carga repetida
- **WHEN** a mesma carga é executada duas vezes
- **THEN** nenhum registro é duplicado e o resultado registra zero alterações na segunda

### Requirement: Linhas problemáticas viram pendência de curadoria
O sistema SHALL separar da carga as linhas com código inválido, código repetido para itens diferentes ou campos obrigatórios ausentes, listando-as
como pendência de curadoria com o motivo. Concentração vazia SHALL ser aceita quando o item não a tem (por exemplo, água destilada).

#### Scenario: Código repetido
- **WHEN** o mesmo código aparece em duas linhas com princípio ativo ou concentração diferentes
- **THEN** ambas vão à pendência de curadoria até a decisão humana

### Requirement: Catálogo independente do ERPNext
O sistema SHALL manter o catálogo CATMAT no núcleo, e o módulo de integração SHALL mapear o código CATMAT ao item do ERPNext sem tornar o ERPNext
a fonte do catálogo.

#### Scenario: Item sem correspondência no ERPNext
- **WHEN** o ERPNext não tem item para um código CATMAT usado no laboratório
- **THEN** o mapeamento fica pendente e o laboratório continua operando com o catálogo próprio
