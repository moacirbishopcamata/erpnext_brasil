# Laboratório SUS e a LGPD: análise de conformidade

Estudo de 2026-10-12 para o change `laboratorio-sus-ciclo-completo`. Pergunta: o que a Lei 13.709/2018 (LGPD) exige de um módulo
que guarda o **prontuário do paciente** e todo o ciclo do exame laboratorial público, e como o desenho atende a cada exigência.
Não é parecer jurídico: um encarregado e um advogado de saúde pública precisam revisá-lo antes de qualquer operação real.

## 0. Nível de confiança das fontes

| Fonte | Como foi lida | Confiança |
|---|---|---|
| Lei 13.709/2018 (texto compilado) | **Lida** no arquivo `L13709.html` enviado pelo usuário (versão do Planalto com as redações antigas junto). As URLs do Planalto falharam daqui. Lidos os arts. 5, 6, 7, 11, 12, 14, 15, 16, 18 a 20, 23, 26, 27, 41, 48, 49 e 52 | **Alta** para os artigos lidos; os não lidos (33, 37, 38, 42, 46, 47) seguem a leitura por resumo |
| Resolução CD/ANPD 15/2024 (incidente) | Resumos de escritórios (Mattos Filho, Lefosse, Cescon Barrieu) | Média-alta: prazo de **3 dias úteis** consistente entre fontes |
| Lei 13.787/2018 (prontuário digital) | Resumos e a lei em cópia de terceiros | Média-alta: **20 anos** do último registro |
| Resolução CFM 1.821/2007 (guarda permanente) | Material de consultoria | Baixa-média: o CREMERJ entendeu que a lei prevaleceu |
| RIPD (art. 38) | Perguntas e respostas da ANPD (2023) por resumo; não há guia da ANPD específico para saúde | Média |
| RDC 786/2023, prazo de guarda | O change irmão leu o texto oficial e cita o **art. 81 (5 anos)**; uma busca de concurso indicou 3 anos | **Divergente: reconferir** |

Os dois arquivos enviados (`L13709.html`, com as redações antigas, e `L13709compilado.html`, vigente) foram lidos. O compilado inclui
alterações até a **Lei 15.352/2026**, que reestrutura a ANPD (hoje Agência Nacional de Proteção de Dados, com Procuradoria e Auditoria)
e mexe no art. 5º, VIII (encarregado como canal entre controlador, titulares e ANPD); **não altera os direitos do titular nem as bases
legais lidas aqui**. Tudo o que está marcado **A CONFIRMAR** vira tarefa de fonte primária no grupo 1 do `tasks.md`.

## 1. Papéis

- **Controlador**: o estabelecimento ou ente público que decide as finalidades (a Secretaria de Saúde, o município, o laboratório
  público). Quando é pessoa jurídica de direito público, aplicam-se os arts. 23 a 30 (tratamento pelo poder público).
- **Operador**: quem trata em nome do controlador. O **provedor da hospedagem** e o **fornecedor do módulo** são operadores quando
  operam o sistema; o **provedor de assinatura**, o de **mensagens** e a **RNDS** têm papéis a definir caso a caso.
- **Encarregado (DPO)**: obrigatório (art. 41), com contato público. O módulo deve mostrá-lo na página do paciente.
- Em estrutura SUS há **controladoria conjunta** possível (município e Estado, LACEN): contrato ou instrumento deve definir quem
  responde por quê. **Premissa registrada**, a confirmar com o jurídico de cada ente.

## 2. Classificação

Todo dado do módulo é **dado pessoal** e quase todo é **dado pessoal sensível** (art. 5º, II: dado referente à saúde): exame,
resultado, solicitação, hipótese diagnóstica, agravo, trabalhador em exame ocupacional. Nome, CPF, CNS e endereço são dado pessoal
comum, mas **ligados a exame viram sensíveis na prática**. Regra de projeto: tratar o cadastro inteiro como sensível.

Há **titulares vulneráveis**: crianças e adolescentes (art. 14: melhor interesse; o §1º exige consentimento específico e em destaque de
um dos pais ou do responsável para **crianças**, e o §6º manda informar de forma simples e acessível; o ECA define criança até 12 anos,
**a confirmar** o tratamento dos adolescentes — o desenho trata todo menor com responsável legal, por prudência), pessoas em investigação de agravo de notificação (estigma), trabalhadores (assimetria com o
empregador).

## 3. Bases legais por atividade de tratamento

Dado sensível só se trata nas hipóteses do **art. 11**. Consentimento é a exceção, não a regra, em saúde pública.

| Atividade | Base proposta | Observação |
|---|---|---|
| Solicitar, coletar, analisar, liberar e entregar exame | Art. 11, II, **f** ("tutela da saúde, exclusivamente, em procedimento realizado por profissionais de saúde, serviços de saúde ou autoridade sanitária", redação da Lei 13.853/2019); no poder público, também art. 11, II, **b** (tratamento compartilhado necessário à execução de política pública prevista em lei ou regulamento) | Base principal. Consentimento **não** é necessário e seria frágil (pode ser retirado) |
| Prontuário e guarda | Art. 11, II, **a** (obrigação legal ou regulatória) | Lei 13.787, RDC 786 |
| Envio à RNDS (REL) | Art. 11, II, **a** e **b** (Portaria GM/MS 8.276/2025, art. 3º obriga o envio) | Compartilhamento entre entes públicos: arts. 26 e 27 |
| Notificação compulsória | Art. 11, II, **a** e **b**; vigilância em saúde | Lista nacional; dever do profissional ou serviço |
| Exame ocupacional e eSocial (S-2220) | Art. 11, II, **a** (obrigação do empregador) | Quem envia é o empregador; o laboratório só entrega o dado |
| Portal do paciente | Execução do próprio serviço; acesso do titular (art. 18, II) | Segundo fator; sem indexação |
| Mensagem de aviso ao paciente | **Consentimento** (art. 11, I) ou legítimo interesse **não** vale para sensível | Sem dado de saúde na mensagem; registrar o consentimento e permitir revogar |
| Estatística, relatório, vigilância agregada | Dado **anonimizado** (art. 12) ou art. 11, II, **c** (estudos por órgão de pesquisa) | Anonimização efetiva; ver §8 |
| Pesquisa | Art. 11, II, **c**, com anonimização sempre que possível, e art. 13 (saúde pública) | Fora do escopo do módulo; só exportação anonimizada |
| Auditoria e segurança (logs) | Art. 11, II, **g** (prevenção à fraude e à segurança do titular) ou obrigação legal | Logs sem o conteúdo do resultado |

**Vedação** do art. 11, §4º (redação da Lei 13.853/2019): comunicação ou uso compartilhado de dado de saúde entre controladores **com
objetivo de vantagem econômica** é vedado, salvo prestação de serviços de saúde, assistência farmacêutica e assistência à saúde,
"incluídos os serviços auxiliares de diagnose e terapia, em benefício dos interesses dos titulares" (e a portabilidade pedida
pelo titular e as transações financeiras e administrativas do serviço). O laboratório está **dentro da exceção**, mas só para o
que beneficia o titular. O §5º veda a operadora de plano de saúde usar dado de saúde para selecionar risco.

**Publicidade (art. 11, §2º e art. 23, I)**: quando o poder público trata sem consentimento com base nas alíneas *a* e *b*, deve
**dar publicidade** a essa dispensa, com informação clara e atualizada sobre a previsão legal, a finalidade e os procedimentos. O
módulo precisa de uma página pública com essa informação (item novo do desenho).

**Pessoa jurídica de direito privado** que recebe dado de ente público (art. 27): em regra depende de consentimento e é informada à
ANPD, salvo as exceções (hipóteses de dispensa da lei, uso compartilhado com publicidade, §1º do art. 26). Vale para laboratório
privado conveniado ao SUS. Consequência de projeto: **nenhum dado de paciente vai a
terceiro por contrapartida comercial**; qualquer integração nova passa por revisão.

## 4. Princípios do art. 6º mapeados ao desenho

| Princípio | Controle no módulo |
|---|---|
| Finalidade, adequação, necessidade | Cada campo tem finalidade registrada; formulário só pede o que a spec exige; etiqueta e manifesto levam o mínimo; código de barras só leva o identificador |
| Livre acesso | Portal do paciente pelo número da requisição; cópia do prontuário |
| Qualidade dos dados | Cadastro único, deduplicação, retificação com histórico |
| Transparência | Aviso de privacidade no portal e no comprovante; encarregado visível; lista de com quem se compartilha |
| Segurança | Perfis por função e unidade, cifragem, auditoria com antes/depois, estação offline cifrada |
| Prevenção | RIPD antes do uso; testes de abuso do portal; revisão de acesso |
| Não discriminação | Sem uso de dado de saúde para decisão em prejuízo do titular; relatório gerencial anonimizado |
| Responsabilização e prestação de contas | Registro das operações (art. 37), trilha só de acréscimo, evidência de validação das regras |

## 5. Direitos do titular (art. 18) e como o módulo os cumpre

| Direito | Como |
|---|---|
| Confirmação e acesso | Portal pelo número da requisição + segundo fator; cópia do prontuário sob pedido |
| Correção | Correção de cadastro com motivo e histórico; resultado liberado **não se altera**, corrige-se por novo laudo |
| Anonimização, bloqueio ou eliminação | **Limitados pela guarda legal** (art. 16, I): o dado do prontuário não se elimina antes do prazo; o titular recebe explicação |
| Portabilidade | Exportação em formato estruturado (FHIR) a pedido |
| Informação sobre compartilhamento (art. 18, VII) | Página com a lista de destinatários (RNDS, vigilância, empregador no ocupacional) |
| Avisar quem recebeu o dado (art. 18, §6º) | Ao corrigir, bloquear ou anonimizar, o módulo avisa os destinatários (RNDS, empregador) de forma registrada |
| Revogação de consentimento | Só para o que depende dele (mensagem); o tratamento do exame continua |
| Revisão de decisão automatizada (art. 20) | **Ponto crítico**: a autoverificação é decisão automatizada que afeta o paciente. Oferecer **revisão humana sob pedido**, informar os critérios e procedimentos (art. 20, §1º) e manter a regra versionada |
| Petição à ANPD e oposição | Canal do encarregado |

Prazos (art. 19, lido): confirmação ou acesso **em formato simplificado, imediatamente**; **declaração clara e completa** (origem,
critérios, finalidade) em até **15 dias**; atendimento **sem custo** (art. 18, §5º) e em formato que favoreça o acesso (art. 19, §1º),
por meio eletrônico seguro ou impresso. A ANPD pode diferenciar os prazos por setor (art. 19, §4º): **a confirmar se já o fez para saúde**.
Se não puder atender de imediato, a resposta indica as razões de fato ou de direito (art. 18, §4º).

## 6. Prontuário, guarda e eliminação

- **Lei 13.787/2018**: o prontuário digital exige sistema que garanta integridade, autenticidade e confidencialidade; o prazo
  mínimo de guarda é de **20 anos a partir do último registro**; a eliminação depois disso deve ser **registrada**, resguardar a
  intimidade e o sigilo, e pode devolver o prontuário ao paciente. Regulamento pode fixar prazo diferente conforme o uso para
  estudo e prova.
- **RDC 786/2023**: guarda dos registros do laboratório por **5 anos (art. 81, lido no change irmão)**. A busca desta análise
  indicou 3 anos em material não normativo: **reconferir**.
- **Resolução CFM 1.821/2007**: guarda permanente de prontuário eletrônico; o CREMERJ (2021) entendeu que a lei prevaleceu.
- **LGPD art. 16, I**: a guarda por obrigação legal justifica manter o dado depois do fim do tratamento.
- **Decisão de projeto**: o relógio de guarda é **do prontuário**, parametrizável, com piso de **20 anos do último registro**
  (o maior entre os prazos aplicáveis); o módulo **não elimina** sozinho. A eliminação é um procedimento com aprovação, evidência
  e registro; a devolução ao paciente é uma opção.
- Dado fora do prontuário (logs técnicos, mensagens da fila, arquivos temporários, PDF enviado para conferência) tem **prazo
  curto** e eliminação automática.

## 7. Compartilhamentos

| Destino | Base | Risco | Controle |
|---|---|---|---|
| RNDS | Art. 11, II, a/b; Portaria 8.276/2025 | Envio de paciente sem identificação confiável | Só envia com CPF/CNS válido; sem pendência |
| Vigilância (SINAN) | Obrigação legal | Estigma | Perfil próprio; território; sem acesso irrestrito |
| Empregador (S-2220) | Obrigação legal do empregador | Empregador ver resultado além do ASO | Dado **mínimo** do exame ocupacional; nunca o laudo clínico completo |
| ERPNext (integração) | Operação interna | Perfis do ERPNext vendo dado clínico | Relatórios sem identificação; permissão específica |
| Provedor de assinatura | Operador | Chave e documento | Assinar só o hash; cifrar; contrato de operador |
| Provedor de mensagens | Consentimento | Vazamento por texto | Sem dado de saúde na mensagem |
| GAL (transição) | Art. 26 entre entes públicos | Duplicidade e divergência | Quarentena; sem reescrever |
| Hospedagem em nuvem | Operador | **Transferência internacional (art. 33)** se o provedor estiver fora do Brasil | Preferir hospedagem no Brasil; registrar país; cláusulas contratuais |

## 8. Anonimização e uso estatístico

Remover nome e documento **não anonimiza** (art. 12): data de nascimento + município + agravo raro reidentifica. Regra de projeto:
relatório gerencial usa **contagens mínimas** (supressão de células pequenas, por exemplo menos de cinco casos), faixa etária em vez
de data, e município apenas quando a população permite. O método de anonimização é parâmetro; **a validação de reidentificação
é tarefa explícita**.

## 9. Segurança, incidente e prestação de contas

- **Segurança (arts. 46 a 49)**: medidas técnicas e administrativas desde a concepção; o desenho já tem perfil por unidade,
  cifragem, auditoria, hash encadeado, estação offline cifrada e limite de tentativas.
- **Incidente (art. 48 e Resolução CD/ANPD 15/2024)**: comunicar à ANPD e aos titulares em até **3 dias úteis** do conhecimento
  quando houver risco ou dano relevante; dado de saúde em larga escala é gatilho forte. O módulo precisa de **fluxo de incidente**:
  detecção, registro, classificação, relógio de prazo, modelo de comunicação, quem decide.
- **Registro das operações (art. 37)**: inventário das atividades de tratamento (esta tabela é o ponto de partida).
- **RIPD (art. 38)**: elaborar **antes** de operar, pela unidade responsável com apoio do encarregado; a ANPD pode exigi-lo.
  Não há guia da ANPD para saúde; usar o guia de RIPD do governo federal como metodologia de referência.
- **Sanções (art. 52, lido)**: advertência com prazo; multa simples de até **2% do faturamento da pessoa jurídica de direito
  privado** no Brasil, limitada a **R$ 50 milhões por infração**; multa diária; publicização; **bloqueio** e **eliminação** dos dados
  da infração; **suspensão parcial do banco de dados** e **suspensão do tratamento** (até 6 meses, prorrogáveis); proibição parcial
  ou total de tratar dados. A multa pecuniária (inciso II) cita a pessoa jurídica de direito **privado**; o **§3º** manda que os incisos I, IV, V, VI, X, XI e
  XII (advertência, publicização, bloqueio, eliminação, suspensões e proibição) **possam ser aplicados a entidades e órgãos públicos**,
  sem prejuízo da Lei 8.112/1990, da Lei 8.429/1992 e da Lei 12.527/2011 (**lido**). Para um laboratório público, o risco real é a **suspensão do tratamento**, não a multa.

## 10. Decisão automatizada e a autoverificação (art. 20)

Texto vigente lido (redação da Lei 13.853/2019): o titular pode **solicitar a revisão de decisões tomadas unicamente com base em
tratamento automatizado** que afetem seus interesses. A redação original dizia "revisão **por pessoa natural**"; a MP 869/2018 e a Lei
13.853/2019 **tiraram** essa exigência, e o §3º que a tratava foi **vetado**. Logo, a lei hoje **não manda** revisão humana, mas
garante a revisão, e o §1º obriga o controlador a fornecer, sob pedido, **informações claras e adequadas sobre os critérios e os
procedimentos** da decisão automatizada (o §2º dá à ANPD o poder de auditar aspectos discriminatórios quando o controlador nega a
informação por segredo comercial).

O desenho oferece **revisão humana de qualquer modo** (custa pouco, protege o paciente e a ANPD pode regulamentar) e **informa a regra
aplicada**. A autoverificação decide, sem humano, o que o paciente recebe; por isso: (1) a regra é **cadastrada, aprovada e versionada**;
(2) o laudo **declara** que foi autoverificado e por qual regra; (3) o paciente ou o solicitante pode **pedir revisão**; (4) a **taxa
de discordância** é monitorada; (5) resultado crítico nunca é autoverificado. Isso conecta a LGPD à qualidade analítica.

## 11. Riscos e lacunas

| Risco | Gravidade | Resposta |
|---|---|---|
| Número da requisição adivinhado no portal | Alta | Aleatório, segundo fator, limite de tentativas, resposta idêntica |
| PDF do laudo indexado ou em cache | Média | Cabeçalhos de não indexação; sem cache compartilhado; link com validade |
| Empregador recebendo mais que o ASO | Alta | Dado mínimo do ocupacional; configuração explícita de quem transmite |
| Autoverificação errada em massa | Alta | Aprovação, monitoramento, desligamento por regra |
| Estação offline perdida | Média | Cifragem, revogação, apagar após sincronizar |
| Operador e controlador mal definidos | Média | Contrato por ente; **A CONFIRMAR** com jurídico |
| Guarda de 20 anos x direito de eliminação | Média | Art. 16, I; explicação ao titular; eliminação formal após prazo |
| Reidentificação em estatística | Média | Supressão de células pequenas; teste de reidentificação |
| Hospedagem fora do Brasil | Média | Hospedagem nacional; art. 33 |

## 12. O que fica para o jurídico e o encarregado

1. Reconferir os artigos da Lei 13.709 no texto compilado (§0).
2. Definir controlador e operadores de cada ente e os instrumentos (convênio, contrato).
3. Aprovar as bases legais da tabela do §3, em especial o aviso por mensagem e o ocupacional.
4. Elaborar o RIPD antes da operação.
5. Reconferir o prazo de guarda da RDC 786 e decidir o piso do prontuário (20 anos propostos).
6. Definir o prazo e o fluxo de atendimento aos direitos do titular.
