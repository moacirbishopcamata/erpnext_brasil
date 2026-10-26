# Healthcare (Marley Health) — estado verificado e o que falta para o Brasil

Levantamento de **2026-10-10**, a pedido do usuário ("tropicalizar também healthcare"), pagando a tarefa 5.6 do change
`tropicalizar-demais-modulos` (instalar o app de saúde num site de teste e levantar os DocTypes). A proposta que sai dele é o
change `integrar-laboratorio-e-imagem`.

## O app e a instalação

| Item | Verificado |
|---|---|
| Nome e repositório | **Marley Health**, `earthians/marley` (o GitHub redireciona de `frappe/health`); app `healthcare` |
| Versão | `version-16`, **16.6.1** (2026-09-22) |
| Licença | **GPL-3.0** (o `erpnext_brasil` é MIT) |
| Dependência | `required_apps = ["frappe/erpnext"]` — não exige o HRMS |
| Instalação | `bench get-app` + `new-site` (PostgreSQL) + `install-app erpnext` + `install-app healthcare` + `migrate`: **instala e migra** sobre Frappe 16.51.0, ERPNext 16.50.0 e PostgreSQL 18.6 (verificado nessas versões; o bench foi para 16.53.0/16.52.1 em 2026-10-26 e o `migrate` do site `hc16pg` passou, mas a verificação funcional abaixo **não foi refeita**) |
| Tamanho | 127 DocTypes no módulo `Healthcare` do site instalado |
| Site de teste | `hc16pg.localhost` (PostgreSQL). No MariaDB não foi instalado: a senha do root do servidor não estava registrada |

## O que há de laboratório (conferido no código)

`Lab Test Template` (tipos de resultado `Single`, `Compound`, `Descriptive`, `Grouped`, `Imaging`, `No Result`),
`Lab Test Group Template`, `Lab Test UOM`, `Normal Test Template`, `Sample Collection`, `Sample Type`, `Lab Test Sample`,
`Specimen`, `Lab Test` (submetível; resultado normal, descritivo, de organismo e de sensibilidade), `Lab Prescription`,
`Observation` (com `Observation Template`, `Observation Component`, `Observation Reference Range`) e `Diagnostic Report`.
Os nomes `Observation`, `Specimen` e `Diagnostic Report` coincidem com recursos do FHIR.

## O que **não** há

- **Integração com equipamento**: busca no código por analisador, instrumento, ASTM, HL7, MLLP, DICOM, PACS, worklist, LIS e
  marcas de analisadores não achou nada além de terminologia. Nenhum DocType de dispositivo, interface ou conector.
- **Pontos de entrada de resultado** existem (`record_observation_result`, `add_observation`, `edit_observation`), mas sem
  identificação do equipamento, sem controle de repetição e sem protocolo — não foram desenhados para aparelho.
- **Issues públicas** do projeto: nenhuma sobre ASTM, analisador ou LIS; três sobre DICOM (#26 `pynetdicom`, #52 visualizador,
  #71 RIS), abertas desde 2019 a 2022.
- **TUSS, CNES, TISS, SIGTAP, RNDS**: nada no app. LOINC, SNOMED CT, RxNorm, UCUM e ICD existem só como **entradas de `Code System`**.

## CRM

O ERPNext 16.50 **tem CRM no próprio módulo `crm`**: `Lead`, `Opportunity`, `Prospect`, `Campaign`, `Contract`, `Appointment`,
`CRM Note`, `Sales Stage`, motivos de perda, concorrentes, segmentos de mercado, nove relatórios (pipeline, conversão, tempo de
primeira resposta etc.) e gráficos. Há também o **Frappe CRM**, app separado e mais novo (v1.87.0, licença **AGPL-3.0**), que o
ERPNext reconhece (`Frappe CRM Allowed User`, `CRM Settings`). O `erpnext_brasil` e o Healthcare não usam `Lead` nem `Opportunity`.

## TISS: uma correção do que o projeto registrava

O `proposal.md` de `tropicalizar-demais-modulos` dizia "TISS 4.03.00, obrigatoriedade apontada para 2026-07-01 (fonte secundária)".
Pelas páginas oficiais da ANS (lidas em 2026-10-10):

- O **histórico oficial** lista a versão **04.03.00** a partir da competência nov/2025 (publicada em 28/11/2025, vigência
  01/12/2025, implantação até **30/06/2026**); jul/2026 teve limite 31/10/2026 e set/2026 (publicada em 30/09/2026, vigência
  01/10/2026) tem limite **31/12/2026**.
- A página **"Padrão TISS – Setembro/2026"** lista: Organizacional 202609, Conteúdo e Estrutura 202511, Representação de
  Conceitos (TUSS) 202609, Segurança e Privacidade 202511 e Comunicação **04.03.00 e 01.06.00**.
- A página **"Monitora TISS"** ainda diz que a vigente é a **04.02.00** (vigência 01/06/2025, implantação até 30/11/2025) e que não
  se espera versão nova antes do fim da implantação. **As duas páginas oficiais divergem**; vale a do histórico, mais recente.
- A "obrigatoriedade em 01/07/2026" **não consta** nas páginas lidas: o prazo oficial de implantação da 04.03.00 é 30/06/2026.

## RDC 786/2023 (ANVISA): o que obriga o sistema

Lida no texto oficial consolidado (com a RDC 824/2023). Artigos que fundamentam o change:

| Artigo | Exigência |
|---|---|
| 71 | política de acesso; controle de lançamento e alteração com histórico de data, horário, usuário e local; liberação automática ou manual sistematizada; privacidade; proteção contra acesso não autorizado |
| 72 | avaliar e verificar o sistema antes de implantar, documentando disponibilidade, confiabilidade, integridade dos dados e responsabilidades |
| 73 | gerenciar os riscos das tecnologias usadas |
| 81 | guardar documentação e registros por no mínimo **5 anos** |
| 94, 97 | rastreabilidade do material biológico da coleta ao descarte; recuperar as informações que rastreiam o laudo |
| 100, 102 | cadastro do paciente e do exame (inclusive quem coletou, quem recebeu e o horário da coleta) |
| 104 | identificar o material na coleta ou no recebimento: nome, nascimento ou idade, tipo de material, data e hora da coleta |
| 136 a 140 | liberação e assinatura legalmente válida (Lei 14.063/2020); conteúdo mínimo do laudo; **retificação só em novo laudo**, com contato registrado |
| 141 a 147 | controle da qualidade por analito (interno e externo) |
| 154 | prazo de adequação de 180 dias a partir da publicação |

**Não aparecem** na norma: relógio sincronizado e interface com equipamento. O relógio decorre do art. 71, II (horário no
histórico); a interface decorre do dever de rastrear e de garantir a integridade.

## Referências de integração com analisadores (fontes secundárias)

CLSI **LIS01/LIS02** (ex-ASTM E1381/E1394); **HL7 v2** no perfil **IHE LAW** (LAB-27 consulta, LAB-28 ordem `OML^O33`, LAB-29
resultado `OUL^R22`); `ORU^R01` para resultado; **CLSI POCT01-A2**; **CLSI AUTO12** (rótulo); DICOM com lista de trabalho da
modalidade e DICOMweb, Orthanc como PACS aberto; SENAITE LIMS como referência de interfaces de instrumento (licença não
confirmada). **Nenhuma norma paga foi lida.**

## Como SAP e TOTVS tratam

- **TOTVS Saúde Hospitais e Clínicas** (RM): cadastro de convênio com aba própria de parâmetros TISS e de taxa administrativa;
  adaptado ao TISS 4.0 (versão 12.1.2302); gestão de glosa centralizada com motivos separados em auditoria administrativa e
  médica e recurso na mesma tela; faturamento que reaproveita insumos, procedimentos e taxas dos outros módulos. O repasse médico
  é citado em material comercial, **sem detalhe técnico encontrado**.
- **SAP IS-H / i.s.h.med**: a SAP encerra o IS-H; **não achei localização de saúde para o Brasil** (TISS/TUSS). A localização
  brasileira da SAP é fiscal, em geral por parceiros.
- **MV e Tasy (Philips)**: integram TUSS, CBHPM, Brasíndice e Simpro ao faturamento e ao padrão TISS; a Brasíndice e a Simpro são
  tabelas de preço de medicamento e material que precisam ser correlacionadas à TUSS. Fontes de fornecedor e de blog.

## Fontes

ANS: página do Padrão TISS, histórico das versões dos componentes e "Padrão TISS – Setembro/2026"; ANVISA: RDC 786/2023
(texto consolidado); Lei 13.787/2018 e Resolução CFM 2.299/2021 (resumos); RNDS: perfil `BRResultadoExameLaboratorial` e guias da
SES-GO; IHE (wiki do LAW e suplementos); Orthanc Book (worklists); `earthians/marley` (código e issues); `frappe/crm`.
