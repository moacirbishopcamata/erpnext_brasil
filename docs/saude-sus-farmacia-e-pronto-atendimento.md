# Saúde pública (SUS): farmácia e pronto atendimento (PA/UPA 24h) sobre o Marley Health

Estudo de adequação, 2026-10-11. Pergunta: o que o Marley Health (`earthians/marley`, pacote `healthcare`,
16.6.1, GPL-3.0) já cobre para uma **farmácia do SUS** e para um **pronto atendimento / UPA 24h**, e o que falta
tropicalizar. Complementa [healthcare-estado.md](healthcare-estado.md). Nenhum código foi escrito: é base para uma
proposta OpenSpec.

Nível de confiança: o que vem do **código instalado** e da **wiki do Marley** está verificado; o que vem de
norma do SUS está citado com fonte; o que é **fonte secundária** está marcado.

## 1. Farmácia do SUS

**Conclusão: o Marley não atende.** É base clínica (cadastro, prescrição) mais o estoque do ERPNext.

### O que existe (verificado no código)

- `Medication` (forma, concentração, classe, ingredientes, itens de estoque ligados), `Drug Prescription`,
  `Medication Request` (quantidade e `item_code`), interação medicamentosa, ordem e administração em internação.
- Não há DocType de **dispensação**. Só um campo de quantidade "dispensável" no pedido.
- Estoque, lote, validade, armazéns e transferências: do **ERPNext**.

### O que falta

| Lacuna | Detalhe |
|---|---|
| Identificação do paciente | `Patient` tem `uid` genérico, **sem CPF nem CNS** |
| Codificação do medicamento | `national_drug_code` é o código dos EUA; faltam registro ANVISA e o código brasileiro da terminologia do SUS |
| Listas oficiais | RENAME (nacional) e REMUME (municipal) |
| Estabelecimento | CNES |
| Controlados | zero ocorrências de "controlled" no código; sem receita especial nem escrituração (SNGPC: **não verificado** aqui) |
| Financiamento | estoque não se separa por componente (básico, estratégico, especializado) |
| Transmissão | envio diário à **BNAFAR**; dispensação pela **RNDS** |

### Normas (fontes)

- Portaria GM/MS **5.713/2024**: envio de estoque e saídas à BNAFAR, com terminologias padronizadas
  ([texto](https://bvsms.saude.gov.br/bvs/saudelegis/gm/2024/prt5713_17_12_2024.html),
  [COSEMS-SC](https://www.cosemssc.org.br/bnafar-envio-de-informacoes-para-a-base-nacional-da-assistencia-farmaceutica/),
  [FAQ](https://www.gov.br/saude/pt-br/composicao/sectics/daf/bnafar/faq/faq/o-que-foi-estabelecido-pela-1),
  [manual SI-BNAFAR](https://mobileapps.saude.gov.br/portal-servicos/files/f3bd659c8c8ae3ee966e575fde27eb58/6a2369955fdf246346aa5cb87717e782_dzpsc5ic9.pdf)).
- Hórus substituído pelo e-SUS Assistência Farmacêutica (Portaria GM/MS 11.585/2026, prazo de cerca de 180 dias):
  **fonte secundária** ([p2saude](https://p2saude.com.br/esusaf-substitui-sistema-horus-portaria-11585/)).
  **Confirmar no Diário Oficial antes de decidir.**
- A dispensação deixou o SI-BNAFAR e segue pela RNDS (a confirmar no guia técnico da RNDS).

### Posicionamento

Muitas farmácias públicas já usam os sistemas gratuitos do Ministério. O ERP só faz sentido ali **integrando** com
eles (BNAFAR/e-SUS AF/RNDS) ou onde houver mandato para substituí-los. Isso decide o escopo antes de qualquer código.

## 2. Pronto atendimento / UPA 24h

**Conclusão: o Marley 16 tem o esqueleto certo do fluxo de urgência; falta a camada brasileira.**
Fonte: [wiki do Marley, Emergency Department](https://marleyhealth.io/wiki/emergency) ("Introduced in Version 16").

### O que existe (wiki do Marley)

- **Emergency Record**: um documento da chegada à alta. Status: Registrado → Triado → Em tratamento → Fechado.
- Chegada com modo (a pé, ambulância, encaminhamento, polícia) e queixa principal; pode nascer de agendamento ou
  consulta ("Send to Emergency").
- **Triage Level** configurável com cor e prioridade (três níveis de fábrica: Emergency, Urgent, Non-urgent).
- Sinais vitais como `Observation`, ligados ao histórico do paciente.
- Leitos (`Healthcare Service Unit`): atribuir, transferir, ocupação com entrada e saída.
- Conduta: `Patient Encounter` e `Service Request` (exame, medicação, imagem), ambos ligados ao registro.
- Desfecho: alta, internação (cria `Inpatient Record`), transferência, evasão (LWBS), óbito.
- Cobrança: consulta e leito, fatura do ERPNext, cobertura de convênio.

### O que falta para PA/UPA do SUS

| Lacuna | Detalhe |
|---|---|
| Classificação de risco | o padrão da fábrica é de 3 níveis; o SUS usa protocolo de **5 níveis por cor** (Manchester ou equivalente adotado pelo serviço; **definir e citar a fonte** antes de implementar) |
| Identificação | CPF/CNS do paciente (mesma lacuna da farmácia) |
| Estabelecimento | CNES; profissional com CBO e CNS |
| Registro de produção | BPA e/ou RAAS e e-SUS APS/AB (a confirmar qual vale para UPA) |
| Notificação | agravos de notificação compulsória (SINAN) |
| Desfecho | regulação de leitos (central de regulação) e contrarreferência |
| Faturamento | sem convênio no SUS: produção por procedimento (SIGTAP), não fatura de cliente |
| Interoperabilidade | RNDS |
| Medicação da urgência | depende da farmácia (item 1): dispensação e baixa de estoque na unidade |

Ponto de atenção: o fluxo de cobrança do Emergency Record é de **fatura ao paciente ou convênio**. No SUS o
"faturamento" é a **produção** enviada ao gestor; é uma troca de semântica, não só de campo (ver "Cada propriedade
tem uma representação nativa" nas preferências do projeto).

## 3. Serve para maternidade, ambulatório, PA e UPA?

Fonte: [documentação do Marley](https://marleyhealth.io/docs) (recursos: agendamento, ambulatorial, internação,
procedimentos clínicos, reabilitação, laboratório, padrões de código médico) e DocTypes do `healthcare` instalado.

| Serviço | Cobertura | Observação |
|---|---|---|
| Ambulatório | **Boa base** | `Patient Appointment`, `Patient Encounter` (sintomas, diagnóstico, prescrição), `Vital Signs`, procedimentos clínicos, terapia |
| PA / UPA 24h | **Esqueleto bom no v16** | `Emergency Record`, `Triage Level`, leitos, `Emergency Occupancy`; falta a camada SUS (seção 2) |
| Internação | Base | `Inpatient Record`, ocupação, ordem de medicação |
| **Maternidade** | **Não atende** | nenhum DocType de obstetrícia: o único acerto de "gestação/pré-natal" no código é uma faixa de referência de exame; sem pré-natal, partograma, parto, recém-nascido, puerpério |

Maternidade e pré-natal exigiriam modelagem própria (caderneta da gestante, consultas de pré-natal, parto e
nascimento com declaração de nascido vivo, recém-nascido vinculado à mãe, puerpério), além da integração do SUS.
**Não pesquisei** as normas da rede materna aqui; fica como lacuna aberta (seção 7).

## 4. Núcleo compartilhado

Farmácia e PA/UPA dependem das mesmas peças brasileiras; construí-las uma vez é o que paga o resto:

1. **Identidade do paciente**: CPF e CNS (com validação de dígito), por cima de `Patient`.
2. **Estabelecimento e profissional**: CNES, CBO, CNS do profissional.
3. **Terminologias**: RENAME/REMUME, SIGTAP, TUSS, código brasileiro do medicamento.
4. **Camada de integração** (`integracao/`): RNDS, BNAFAR/e-SUS AF, com a regra pura em `fiscal/`-equivalente
   (sem importar `frappe`), como o resto do projeto.

## 5. Licença

O Marley é **GPL-3.0**; este projeto é MIT. Estender sem copiar código GPL (app separado que usa a API do
`healthcare`) mantém a fronteira; copiar trechos do Marley para o app contaminaria a licença. Decisão a registrar na
proposta.

## 6. Recomendação em fases

1. **Núcleo**: identidade (CPF/CNS), CNES, terminologias, validações. Sem integração externa.
2. **PA/UPA**: classificação de risco de 5 níveis, produção (BPA/e-SUS), SINAN, desfecho com regulação.
3. **Farmácia**: dispensação, RENAME/REMUME, financiamento, controlados, envio BNAFAR/e-SUS AF e RNDS.

## 7. Em aberto (não verificado)

- Portaria 11.585/2026 e prazo do Hórus: só fonte secundária.
- Protocolo de classificação de risco oficial exigido para UPA e seus níveis.
- Exigência de SNGPC/escrituração de controlados em farmácia pública.
- Guia técnico da RNDS para dispensação e atendimento de urgência.
- Quais sistemas de produção (BPA, RAAS, e-SUS) a UPA deve alimentar.
- Normas e fluxos da rede materna (pré-natal, parto, declaração de nascido vivo): não pesquisados.
