## Purpose

Modelar a REMUME (Relação Municipal de Medicamentos Essenciais) como lista padronizada versionada, com grupos e subgrupos, financiamento, unidade
padronizada e restrição de uso, para que a dispensação só aconteça com o que o município padronizou, onde e para quem foi padronizado. O modelo
segue a estrutura da REMUME de Porto Velho (6ª edição, 2025).

## ADDED Requirements

### Requirement: Edição da lista com ato, data e vigência
O sistema SHALL registrar cada edição da REMUME com número da edição, ato que a aprovou (por exemplo, Portaria 05/2025-DAF/GAB/SEMUSA), data de
atualização, data de publicação, vigência e prazo da próxima revisão, mantendo as edições anteriores. Uma nova edição SHALL valer a partir da
vigência, e itens novos que o município ainda não adquiria SHALL respeitar o prazo de transição do ato (180 dias na edição de 2025).

#### Scenario: Nova edição publicada
- **WHEN** uma nova edição da REMUME é cadastrada com vigência futura
- **THEN** a edição anterior segue valendo até a vigência, e a dispensação usa a edição vigente na data

### Requirement: Item com a estrutura da REMUME
O sistema SHALL representar cada item da REMUME com: número do item, medicamento (denominação genérica, DCB ou DCI), concentração ou composição, forma
farmacêutica, competência e financiamento, restrição de uso (subgrupo ou programa) e unidades padronizadas, e SHALL permitir observações do
item.

#### Scenario: Item da edição de 2025
- **WHEN** o item "Aciclovir 200 mg, comprimido" é cadastrado
- **THEN** ele traz a competência (Componente Básico), o subgrupo (Farmácia Básica Municipal) e as unidades padronizadas (FBM, FRM, SAE)

### Requirement: Grupos e subgrupos
O sistema SHALL organizar a lista em níveis: **competência e financiamento** (Componente Básico da Assistência Farmacêutica, Componente
Estratégico, Componente Básico e Estratégico, Hospitalar Municipal), **subgrupo** (Farmácia Básica Municipal, Programa de Saúde Mental, Programa
Hiperdia, Programa de Tuberculose, Programa de Toxoplasmose, Programa Saúde da Mulher, Programa de Hanseníase, Programa Malária, Programa Nacional de
Controle ao Tabagismo, Uso Hospitalar e Pronto Atendimento, entre outros) e **item**. Os subgrupos SHALL ser cadastráveis, e um item SHALL
pertencer a um subgrupo por edição.

#### Scenario: Item de programa
- **WHEN** o item pertence ao subgrupo "Programa de Saúde Mental"
- **THEN** ele só é dispensável conforme as regras do programa, nas unidades padronizadas

### Requirement: Unidades padronizadas ligadas a estabelecimentos
O sistema SHALL tratar as siglas de unidade padronizada (FBM, FBMD, FRM, SAE, SAMU, MMME, PA, UPA, CAPS, CEM, CER, CRE, PNCT) como tipos
de ponto de dispensação cadastráveis, cada um ligado a um ou mais estabelecimentos (CNES), e SHALL permitir um item em várias unidades. O
sistema SHALL NOT assumir que a lista de siglas é fixa.

#### Scenario: Nova sigla de unidade
- **WHEN** a secretaria cadastra uma nova unidade padronizada
- **THEN** ela pode ser usada em itens e ligada a estabelecimentos sem alteração de código

### Requirement: Restrição de uso
O sistema SHALL registrar a restrição de uso do item (por exemplo, uso restrito ao atendimento na unidade, uso restrito a procedimento,
restrição a paciente inscrito no programa, exclusivo hospitalar) e SHALL aplicá-la na dispensação: item de programa exige a inscrição do paciente
no programa, e item de uso restrito à unidade não é dispensado para levar.

#### Scenario: Medicamento de programa para paciente não inscrito
- **WHEN** o atendente tenta dispensar item de programa a paciente sem inscrição no programa
- **THEN** a dispensação é recusada com o motivo, e a exceção exige o farmacêutico

### Requirement: Vínculo da REMUME com o CATMAT e a OBM
O sistema SHALL ligar cada item da REMUME a um ou mais códigos do catálogo (CATMAT, e a Ontologia Brasileira de Medicamentos quando disponível) por
princípio ativo, concentração e forma, e SHALL listar como pendência de curadoria o item sem ligação ou com ligação ambígua. A ligação SHALL ser decisão
humana registrada quando a correspondência automática não for exata.

#### Scenario: Correspondência não exata
- **WHEN** a ligação automática só acerta o princípio ativo
- **THEN** o item vai à curadoria, e a decisão humana fica registrada

### Requirement: Carga da REMUME com qualidade medida
O sistema SHALL carregar a REMUME a partir do documento da edição, registrando quantos itens foram lidos, ligados e pendentes, e SHALL separar
para curadoria o item cuja descrição, financiamento ou subgrupo não foi lido com segurança, em vez de carregá-lo com dado inferido.

#### Scenario: Item com descrição embaralhada
- **WHEN** o texto de um item do documento não pode ser dividido com segurança
- **THEN** o item vai à curadoria com o texto bruto, e não é dispensável até ser conferido

### Requirement: Inclusões e exclusões com justificativa
O sistema SHALL registrar toda inclusão, exclusão ou alteração de item entre edições com a justificativa e a deliberação da comissão responsável (a
Comissão Permanente de Farmácia e Terapêutica), de modo que a história de cada item seja reconstituível.

#### Scenario: Item excluído
- **WHEN** um item deixa de constar na nova edição
- **THEN** a exclusão fica registrada com a justificativa, e o item deixa de ser dispensável a partir da vigência
