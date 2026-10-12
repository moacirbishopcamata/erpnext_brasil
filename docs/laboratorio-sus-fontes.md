# Laboratório SUS: fontes oficiais do grupo 1

Registro do grupo 1 do change `laboratorio-sus-ciclo-completo` (levantamento de 2026-10-12). Para cada tarefa: o que foi lido, de onde,
o que mudou no plano e o que continua pendente. Nível de confiança: **primária** = texto oficial ou arquivo do órgão lido por inteiro;
**secundária** = resumo, blog, material de fornecedor ou de concurso; **não lida** = só existência conhecida.

## Situação das tarefas

| Tarefa | Resultado | Situação |
|---|---|---|
| 1.1 Portaria 8.276/2025 (REL) e guia da RNDS | Portaria lida; guia da RNDS inacessível por script | Parcial |
| 1.2 SIGTAP e instrumento de registro | Tabela Unificada 09/2026 lida e analisada | **Feita** |
| 1.3 Lista de notificação compulsória | Lista vigente extraída com a portaria de cada item | **Feita** |
| 1.4 Interface do GAL | Não há documentação pública; exige contato com o LACEN | Pendente de ação humana |
| 1.5 Transporte e estabilidade | RDC 504/2021 lida; estabilidade por exame não obtida | Parcial |
| 1.6 Decisões do serviço | Aguardam o usuário | Pendente |
| 1.7 LGPD (arts. 33, 37, 38, 42) e ANPD 15/2024 | Lidos | **Feita** |
| 1.8 CLSI AUTO12/AUTO02 e GS1 | Pagos ou bloqueados | Pendente |
| 1.9 LIS01/LIS02 e IHE LAW | IHE LAW lido; LIS01/02 pagos | Parcial |
| 1.10 CFBM/CRBM e assinatura | Nenhuma resolução encontrada | Pendente de consulta |
| 1.11 eSocial S-2220 e Tabela 27 | Leiaute oficial não obtido | Pendente |
| 1.12 Lei 13.787 e RDC 786 art. 81 | Lei lida; RDC 786 não lida | Parcial |
| 1.13 Tabelas da tropicalização | IBGE, CNES, SIGTAP, TUSS e fuso levantados; CBO, CID e feriados não | Parcial |

## 1.1 REL e RNDS

- **Primária**: texto da Portaria GM/MS 8.276/2025 em `bvsms.saude.gov.br/bvs/saudelegis/gm/2025/prt8276_01_10_2025.html`. O art. 2º lista 21
  itens de conteúdo mínimo. O art. 3º obriga que os resultados de todo o território nacional sigam o padrão e sejam enviados "regularmente" à
  RNDS, **sem prazo numérico e sem nomear quem envia**; as especificações técnicas ficam no Portal de Serviços do DATASUS (parágrafo único).
- **Precedente que responde "quem envia"**: a Portaria de Consolidação GM/MS 4/2017, Anexo V, arts. 22 a 25 (texto lido, redação da PRT
  1.164/2022 e 3.328/2022), obriga os **laboratórios** da rede pública, privada e universitária a notificar ao Ministério os resultados de
  testes de covid-19 e Monkeypox **em até 24 horas do resultado, por registro e transmissão na RNDS**; o laboratório solicita o uso da RNDS
  em `servicosdatasus.saude.gov.br`, a documentação técnica está em `rnds.saude.gov.br`, e a responsabilidade é dos gestores e responsáveis
  pelos laboratórios, fiscalizada pelo gestor local (art. 24). Isso é precedente, **não** regra do REL.
- **Pendente**: o guia de integração da RNDS (`rnds-guia.saude.gov.br`) é uma página dinâmica que o script não conseguiu ler. Falta o
  prazo operacional do REL e o perfil FHIR nacional.
- **Efeito no plano**: o laboratório (o módulo) assume a responsabilidade pelo envio, como no precedente; o prazo vira parâmetro.

## 1.2 SIGTAP e instrumento de registro (feita)

- **Primária**: `TabelaUnificada_202609_v2610050950.zip` do FTP do DATASUS (competência 09/2026). Tabelas `tb_registro`,
  `rl_procedimento_registro`, `tb_procedimento`, `tb_servico`.
- Instrumentos (`tb_registro`): 01 BPA (Consolidado), 02 BPA (Individualizado), 03 a 05 AIH, 06 e 07 APAC, 08 e 09 RAAS, 10 e-SUS APS.
- **Subgrupo 02.02 (Diagnóstico em laboratório clínico): 525 procedimentos.** Resultado:
  - **505 aceitam BPA individualizado**; 428 aceitam BPA consolidado **e** individualizado (escolha do gestor); **16 só aceitam BPA
    individualizado** (obrigatório); **nenhum é só consolidado**. Os outros 20 não têm BPA (só APAC ou AIH).
  - O código CNES **145 = Serviço de Diagnóstico por Laboratório Clínico** (e 120 = Anatomia Patológica e/ou Citopatologia, 141 = Vigilância
    em Saúde); 02.03 (anatomia patológica) tem 14 procedimentos e 02.13 (vigilância) 84.
- **Efeito no plano**: o módulo registra o paciente (CNS) em toda produção, o que serve aos dois instrumentos; a regra "pode ou não
  consolidar" vem da tabela da competência, não de código fixo (como a spec já diz). A regra de **não misturar instrumentos na mesma
  competência** continua de fonte secundária.
- **Dados no repositório**: `sus_brasil/dados/sigtap_0202_202609.csv`.
- **Mapeamento TUSS × SIGTAP (achado novo)**: o FTP traz `Mapeamento_TUSS_SIGTAP.zip` (977 linhas, 144 no 02.02, com "grau de equivalência"
  de 1 a 3), de uma nota informativa de **06/03/2017**. Corrige a afirmação anterior de que não havia correspondência oficial: **TUSS ↔ SIGTAP
  existe** (o que continua sem fonte oficial é TUSS ↔ LOINC). Está desatualizado em relação à TUSS vigente. Dados em
  `sus_brasil/dados/tuss_sigtap.csv`.

## 1.3 Lista Nacional de Notificação Compulsória (feita)

- **Primária**: Portaria de Consolidação GM/MS 4/2017, Anexo V, texto da página `bvsms` (arquivo de 4,3 MB lido localmente), que traz **12
  versões** da tabela do Anexo 1, de PRT 204/2016 até a **PRT GM/MS 11.211, de 13/05/2026**. A tabela vigente tem **66 itens numerados e 81
  linhas** (com subitens), cada um com as colunas imediata (24 h) para MS, SES e SMS, e semanal.
- Itens recentes: anomalias congênitas (PRT 10.175/2026), esporotricose humana, Febre do Oropouche, parotidite, ESAVI e outros (PRT 11.211/2026).
- **Obrigação**: art. 3º, a notificação é obrigatória para médicos, outros profissionais de saúde e responsáveis por serviços de saúde
  (Lei 6.259/1975); o §2º estende a comunicação a **unidades laboratoriais**. **Imediata = até 24 horas**; **semanal = até 7 dias**
  (art. 2º, VII e VIII). Há também a **notificação negativa semanal** (art. 2º, IX).
- Limite: a coluna `primeira_aparicao` do CSV é por **nome normalizado** entre versões; uma renomeação (por exemplo "Febre Tifoide" para
  "Febre Tifóide") conta como nova. Use-a como indício, não como histórico definitivo.
- **Dados no repositório**: `sus_brasil/dados/agravos_lista_nacional.csv`.
- **Efeito no plano**: o alerta de notificação usa a lista versionada; o prazo "imediata" é 24 horas e "semanal" é 7 dias; a **notificação
  negativa semanal** (sem caso na semana) é um requisito novo para o módulo de vigilância.

## 1.4 GAL

- **Secundária**: não há documentação técnica pública de webservice, API ou formato de importação e exportação do GAL. Há **um caso real**
  de integração: o LACEN-MG (Funed) contratou o LIS Korus (Pixeon, dez/2023) e incorporou ao LIS as informações do GAL; a notícia não
  descreve o mecanismo. Em 2023 a CGLAB informou que o GAL estava em manutenção e que **uma nova aplicação estava em desenvolvimento**, e
  que há mais de 101 milhões de laudos cadastrados desde 2008.
- **Pendente de ação humana**: a tarefa pede consultar um LACEN. Sugestões: LACEN-RO (Porto Velho, CNES 2496860), a CGLAB/Ministério da
  Saúde, ou a Funed/Pixeon. Até lá, o adaptador do GAL permanece opcional e a transição é por arquivo ou digitação conferida.
- **Efeito no plano**: a possibilidade de uma **nova versão do GAL** é risco para a transição; reforça manter o GAL como adaptador.

## 1.5 Transporte e estabilidade

- **Primária (RDC 504/2021, 6 páginas, cópia da ANVISA)**: definições (embalagem primária, secundária, terciária; categorias A, B/UN 3373
  e espécime de risco mínimo), validação do acondicionamento com controle de temperatura (art. 11, §1º), rotulagem em português com tinta
  indelével e à prova d'água (art. 21), conteúdo mínimo da embalagem terciária com contato 24 h (art. 23), instrumento escrito entre as
  partes (art. 26), registro de quem acondicionou (art. 28) e de quem recebeu (art. 36), documento de rastreabilidade com o transportador
  (art. 32), **guarda da documentação por 5 anos** (art. 42), investigação de não conformidades (art. 6º).
- **A RDC 504 não fixa faixas de temperatura nem prazos de transporte**; manda validá-los por material. Isso corrige o desenho, que supunha
  limites normativos.
- **Secundária (livro de gestão da fase pré-analítica da SBPC/ML, 259 páginas, citando CLSI H18-A3 e GP16-A3)**: sangue total não
  centrifugado, **no máximo 2 horas** após a coleta para manter a estabilidade; para a maioria dos analitos, **10 a 22 °C**, evitando mais
  de 35 °C e abaixo de 0 °C; urina, **máximo 2 horas**, 15 a 25 °C para físico-química e 2 a 8 °C se passar de 2 horas; categorias
  de armazenamento ambiente 18 a 25 °C, refrigerado 4 a 8 °C, congelado −20 °C; exames a analisar **no local da coleta**: renina, pH e gases
  sanguíneos, ácido lático, amônia, crioglobulinas e crioaglutininas; **rejeição** (amostra não identificada, tubo incorreto, dados
  discordantes entre etiqueta e requisição, transporte ou preservação inadequados) distinta de **aceite condicionado** (volume insuficiente,
  lipemia, icterícia, hemólise), com política escrita.
- **Pendente**: os limites de estabilidade **por exame** (a tarefa pede três exames de rotina) e a fonte primária por analito.
- **Efeito no plano**: specs de remessa e de coleta atualizadas (classificação, rótulo em português, documento do transportador, guarda de
  5 anos, aceite condicionado, exames que não podem esperar).

## 1.7 LGPD e ANPD (feita)

- **Primária**: texto compilado da Lei 13.709/2018 (arquivo enviado pelo usuário) e Resolução CD/ANPD 15/2024 (PDF do regulamento).
- Art. 33: transferência internacional por garantias contratuais, política pública com publicidade (inciso VII) ou consentimento específico,
  entre outros. Art. 37: registro das operações. **Art. 38: o relatório de impacto é exigível quando a ANPD determinar**, com conteúdo mínimo
  de tipos de dados, metodologia de coleta e segurança e análise de mitigação. Art. 42: reparação, com **responsabilidade solidária do
  operador** que descumpre a lei ou as instruções, e inversão do ônus da prova a critério do juiz.
- **Resolução 15/2024**: três dias úteis para comunicar à ANPD (art. 6º) e ao titular (art. 9º), contados do **conhecimento de que o incidente
  afetou dados pessoais** (§1º); complemento em até 20 dias úteis (§3º); registro do incidente por **5 anos, mesmo se não comunicado**
  (art. 10); risco relevante com dado sensível (art. 5º, I).
- **Efeito no plano**: três correções (relógio do incidente, RIPD como escolha de projeto, registro de 5 anos); ver `docs/laboratorio-sus-lgpd.md`.

## 1.9 IHE LAW (parcial)

- **Primária**: suplemento oficial *IHE Laboratory Technical Framework Supplement, Laboratory Analytical Workflow (LAW)*, Rev. 1.4, 2015-03-16,
  *Trial Implementation* (189 páginas). Transações: **LAB-27** consulta de trabalho (`QBP^Q11` com resposta `RSP^K11`), **LAB-28** envio da
  ordem (`OML^O33` com `ORL^O34`) e **LAB-29** mudança de estado com resultado (`OUL^R22`). O espécime vai nos segmentos SPM e SAC (o recipiente
  em SAC-3). O resultado deve ser coerente com a ordem (OBR-4 e identificadores); do contrário a mudança de estado deve ser rejeitada.
- **Correção**: `ORU^R01` **não** faz parte do LAW (zero ocorrências). O plano o tratava como parte do perfil; agora é adaptador extra.
- **Pendente**: CLSI LIS01 e LIS02 (pagos), e uma revisão do suplemento mais nova que a de 2015, se existir.

## 1.12 Prontuário e guarda (parcial)

- **Primária (Lei 13.787/2018, texto em cópia de terceiros do DOU)**: art. 6º, **prazo mínimo de 20 anos a partir do último registro** para
  eliminar prontuário em papel ou digitalizado; **§5º aplica-se também aos prontuários "gerados e mantidos originalmente de forma
  eletrônica"**; §1º permite prazos diferentes por regulamento; §2º devolução ao paciente; §4º registro da destinação final. Art. 2º, §2º:
  na digitalização usa-se certificado ICP-Brasil "ou outro padrão legalmente aceito" (a lei **não** cita o NGS2). Art. 4º: meios de
  armazenamento protegem contra acesso, uso, alteração, reprodução e destruição não autorizados.
- **Primária (perguntas e respostas da ANVISA sobre a RDC 786, publicadas pela SBAC)**: "não existe normativo sanitário federal que determine
  o tempo de guarda de qualquer material biológico" no serviço de análises clínicas (trata do **material**, não dos registros).
- **Não lida**: o texto da RDC 786/2023, inclusive o art. 81 (guarda dos registros). O change irmão afirma ter lido o art. 81 (5 anos); aqui
  **não foi possível confirmar**. Fontes secundárias divergem (3 e 5 anos).
- **Decisão**: o piso de 20 anos do prontuário (a lei) prevalece sobre qualquer prazo menor da RDC; a divergência entre 3 e 5 anos deixa de
  alterar o desenho. A tarefa fica aberta até ler o art. 81.

## 1.13 Tabelas brasileiras da tropicalização (parcial)

| Tabela | Fonte | Situação |
|---|---|---|
| Municípios e distritos (IBGE) | `servicodados.ibge.gov.br/api/v1/localidades` | Lida. Rondônia tem 52 municípios; Porto Velho é `1100205`. **O CNES usa o código de 6 dígitos (`110020`)**. Os 12 distritos de Porto Velho: sede, Abunã, Calama, Demarcação, Extrema, Fortaleza do Abunã, Jaci-Paraná, Mutum-Paraná, Nazaré, Nova Califórnia, São Carlos, Vista Alegre do Abunã |
| Estabelecimentos (CNES) | API `apidadosabertos.saude.gov.br/cnes/estabelecimentos` (filtro `codigo_municipio`, 39 campos) e arquivos `.dbc` do FTP do DATASUS | Lida. A API só tem estabelecimentos e tipos de unidade. **`TERCEIRO` e `CNESTERC` vêm vazios**. Código 6 vs 7 dígitos |
| SIGTAP | FTP do DATASUS (tabela mensal) | Lida |
| TUSS × SIGTAP | FTP do DATASUS (2017) | Lida; desatualizada |
| Fuso | Python `zoneinfo` | **`America/Porto_Velho` não existe sem o pacote `tzdata` no Windows**; Rondônia usa UTC−4, não o horário de Brasília. Dependência nova para o módulo |
| CBO, CID, feriados nacionais, raça/cor | — | Não levantadas |

## O que mudou no plano por causa desta leitura

1. Relógio do incidente conta do conhecimento do afetamento de dados, não da classificação (spec de proteção de dados).
2. RIPD é pré-condição **por escolha de projeto**; o art. 38 só o exige sob determinação da ANPD.
3. Registro de incidente por 5 anos, mesmo se não comunicado.
4. Perfil LAW: `QBP^Q11`, `OML^O33`, `OUL^R22`; `ORU^R01` fora do perfil; resultado coerente com a ordem.
5. Remessa: classificação do material, rótulo em português e indelével, documento do transportador, guarda de 5 anos, sem limites normativos
   de temperatura e prazo.
6. Coleta: aceite condicionado distinto da rejeição, com política escrita.
7. Tropicalização: fuso por unidade (Rondônia, UTC−4) e dependência de `tzdata`.
8. Mapeamento TUSS × SIGTAP oficial existe (2017); notificação negativa semanal é requisito novo; código CNES 145 confirmado.

## Pendências que dependem de pessoas ou de acesso

- Consultar um LACEN sobre integração com o GAL (1.4).
- Responder as perguntas de projeto do serviço (1.6).
- Obter o texto da RDC 786/2023 (art. 81) e os textos pagos de CLSI AUTO12, AUTO02, LIS01 e LIS02 e da especificação GS1 (1.8, 1.9, 1.12).
- Consultar o CFBM/CRBM sobre assinatura de laudo (1.10).
- Obter o leiaute oficial do S-2220 e a Tabela 27 (1.11).
