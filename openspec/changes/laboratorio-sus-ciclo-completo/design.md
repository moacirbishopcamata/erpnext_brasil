## Context

Ver `proposal.md` (Why). Estado verificado em 2026-10-12:

- **Existe um change irmão**, `integrar-laboratorio-e-imagem`, que desenha rastreabilidade, etiquetagem e integração com
  analisadores para um laboratório com Healthcare. **Este módulo é avulso**: não depende dele, do Healthcare nem do app fiscal.
  Onde os dois resolvem o mesmo problema (identificador de tubo, custódia, quarentena, retificação em novo laudo), este change
  **reimplementa a regra na própria camada pura**, em vez de importar. Os dois poderão convergir depois; hoje duplicar uma regra
  pequena custa menos que acoplar dois módulos (mesma lógica de bounded context do projeto).
- **Padrão do projeto**: regra pura em módulos sem `frappe`, camada fina de integração, adaptadores por `Protocol`, teste
  arquitetural com `ast` impedindo a camada pura de importar `frappe` (`tests/test_arquitetura.py`).
- **GAL** (verificado em manuais de LACENs estaduais): sistema do DATASUS com a SVS/CGLAB para laboratórios de saúde pública; o
  município cadastra a requisição *antes* de enviar a amostra, o analista libera o resultado online e o município imprime o
  laudo. Manuais são de anos variados (um é de 2013); acesso exige cadastro do serviço e do usuário por LACEN. **Não foi
  encontrada interface oficial de troca de dados com sistema externo** — por isso o GAL é tratado como adaptador opcional e a
  forma de integrar é pergunta em aberto.
- **REL/RNDS** (verificado em notícia do CONASS e guias estaduais): a Portaria GM/MS 8.276/2025 instituiu o modelo REL; o
  conteúdo mínimo inclui paciente por CPF ou CNS, CNES do receptor da amostra e do executor e responsável técnico. O guia de
  implementação FHIR nacional **não foi localizado**; só guia estadual em rascunho (SES-GO, v1.0.5). Confirmar no site oficial
  da RNDS antes de montar o recurso.
- **Notificação compulsória**: a lista está no Anexo 1 do Anexo V da Portaria de Consolidação GM/MS 4/2017, alterada pelas
  Portarias 217/2023, 5.201/2024, 6.734/2025 e 10.175/2026 (verificado por resumos). O texto sobre a obrigação específica de
  laboratórios **não foi lido**.
- **SIGTAP/BPA**: um procedimento pode ser registrado em BPA individualizado ou consolidado, sem misturar na competência
  (fonte secundária). **Não foi confirmada** a regra de quais procedimentos do subgrupo 02.02 exigem individualizado.
- **RDC 786/2023** (já lida no change irmão): identificação do material (art. 104), liberação e assinatura (art. 136 e 137),
  conteúdo do laudo (art. 138), retificação em novo laudo (art. 140), guarda de 5 anos (art. 81).

## Goals / Non-Goals

**Goals:**
- Tornar **impossível por construção** anexar resultado a tubo por inferência, e **visível e recuperável** tudo o que não casa.
- Cobrir o ciclo inteiro, da solicitação à entrega e à produção, com custódia verificável também **entre unidades**.
- Funcionar **instalado sozinho** e **sem conectividade permanente** nas unidades coletoras.
- Ser desligável por adaptador: cada integração opcional pode ser removida sem perder dado nem regra.

**Non-Goals:**
- **Interpretar resultado ou apoiar decisão clínica** (possível enquadramento como software como dispositivo médico, RDC 657/2022,
  a confirmar com especialista).
- Integração com analisador (HL7/ASTM), imagem e PACS: ficam para adaptadores e para o change irmão.
- Faturamento privado (TISS), banco de sangue, biobanco e anatomia patológica (fluxo próprio).
- Substituir o GAL nos LACENs: o módulo conversa com ele, não o substitui.
- Certificação SBIS e acreditação.

## Decisions

### 1. App Frappe próprio, núcleo em camada pura

O app `laboratorio_sus` (nome provisório) guarda os DocTypes; a regra mora em módulos puros (estados, identificador, hash,
rejeição, tempos, faixa offline, validação CNS/CPF). *Alternativa recusada:* estender o Healthcare — acopla a um app GPL de
terceiro e contradiz o requisito de módulo avulso.

### 2. Portas (`Protocol`) para tudo que é de fora

Cadastro (paciente, unidade, profissional), entrada de resultado, impressão, relógio, RNDS e GAL são interfaces com
implementação própria mínima. Sem adaptador, o módulo opera com cadastro próprio e digitação conferida. Mesma inversão de
dependência de `integracao/repositorio_frappe.py`. *Alternativa recusada:* chamar Healthcare diretamente nas regras — quebra a
instalação isolada.

### 3. Identificador do tubo: opaco, com dígito de conferência, contador transacional, nunca reaproveitado

Sem data nem paciente embutidos; o dígito pega leitura errada (escolha de projeto, não exigência de norma). *Alternativa
recusada:* número curto que reinicia por dia — colide na virada, que é o cenário da amostra trocada.

### 4. Coleta em campo: faixa de identificadores reservada por estação

A estação offline recebe um bloco de identificadores e consome em sequência; o não usado é **anulado e registrado**, o
duplicado na sincronização vai à quarentena. Preserva "etiqueta impressa só na coleta" (nada é impresso antecipadamente; só o
*número* é reservado). *Alternativa recusada:* gerar identificador localmente sem coordenação — colisão inevitável entre estações.

### 5. Custódia só de acréscimo, encadeada por hash

Cada evento guarda o hash do anterior do mesmo tubo; verificador periódico recalcula. O histórico nativo do Frappe (`Version`) é
editável por quem tem acesso ao banco. Aplica-se também à **remessa**: entrega ao transportador e à unidade destino são eventos.

### 6. Remessa é entidade de primeira classe, com conferência por tubo nas duas pontas

O transporte é onde mais se perde custódia no ciclo SUS. A remessa tem identificador, manifesto e etiqueta sem dado pessoal;
divergência vira **ocorrência**, não ajuste silencioso de contagem. Temperatura e tempo comparados com a estabilidade do exame.

### 7. Casamento só por identificador exato; o resto é quarentena

Mesma decisão do change irmão, reimplementada: motivo enumerado, saída por decisão humana registrada com conferência do tubo
físico. A quarentena é o único destino do que é duvidoso, inclusive resultado importado do GAL divergente.

### 8. Laboratório de referência: identificador de origem nunca substituído

O vínculo com o identificador interno do LACEN é uma ligação registrada; o resultado volta pelo vínculo. Evita o erro de
"renumerar" a amostra e perder o elo com o paciente.

### 9. Estados explícitos com transições permitidas em tabela

Máquina de estados pura e testável; cada transição gera evento de custódia. Estado decide UI e CTAs (dispatcher
estado→componente), não `if` espalhado.

### 10. Produção e notificação são consequência da liberação, não de eventos intermediários

Produção só conta exame liberado; alerta de notificação nasce da liberação. Tabelas de referência (SIGTAP, lista de agravos)
são **dados versionados com vigência**, não código, porque mudam por portaria.

### 11. Segurança: perfil = função × unidade; emergência auditada; canal cifrado

Papéis do Frappe com permissão por unidade; acesso de emergência com justificativa e revisão; estação offline guarda dado cifrado
e é revogável. LGPD: dado de saúde é sensível; relatório gerencial sem identificação.

### 12. Estratégia de teste

Testes puros para estados, identificador (unicidade, dígito, reinício do contador), hash encadeado (adulteração), faixa offline
(colisão), validação CNS/CPF e tempos; teste de bench para DocTypes, permissões por unidade e fluxo completo; teste de troca
(dois tubos de pacientes diferentes lidos em sequência); teste de caos (queda no meio da sincronização offline, reenvio à RNDS).
A validação clínica e do sistema (RDC 786, art. 72) é do serviço, em modo sombra.

## Análise de perigos (segurança do paciente)

| # | Perigo | Controle de projeto | Como se verifica |
|---|---|---|---|
| P1 | Tubo coletado de um paciente e etiquetado para outro | Identificação positiva; etiqueta só na coleta; sem lote antecipado | Teste de impressão sem confirmação |
| P2 | Etiqueta duplicada ou trocada | Reimpressão com motivo e "2ª via"; impressão auditada | Teste de reimpressão |
| P3 | Tubo sem rótulo na bancada | Coleta não confirma sem impressão; recepção retém código desconhecido | Teste de falha de impressora |
| P4 | Alíquota com rótulo de outro paciente | Rótulo só após ler o tubo pai | Teste de recusa sem leitura |
| P5 | Leitura de código errada | Dígito de conferência; casamento exato | Teste com um dígito alterado |
| P6 | Mesmo identificador em duas estações offline | Faixa reservada por estação; duplicado em quarentena | Teste de sincronização com colisão |
| P7 | Tubo perdido ou trocado no transporte | Conferência por tubo nas duas pontas; ocorrência; alerta de trânsito | Teste de tubo a mais e faltante |
| P8 | Amostra degradada aceita | Temperatura e tempo comparados à estabilidade; rejeição enumerada | Teste de estabilidade vencida |
| P9 | Resultado atribuído a tubo por aproximação | Identificador exato; senão quarentena | Teste de identificador inexistente |
| P10 | Erro de digitação do resultado | Dupla conferência; unidade e faixa explícitas | Teste de resultado sem conferência |
| P11 | Resultado de controle gravado em paciente | Controle separado; controle reprovado retém | Teste com controle e com paciente |
| P12 | Unidade ou escala errada | Sem conversão implícita; retenção | Teste de unidade diferente |
| P13 | Laudo corrigido em silêncio | Retificação só em novo laudo | Teste de edição de laudo liberado |
| P14 | Valor crítico não comunicado | Pendência de comunicação em destaque | Teste de crítico sem registro |
| P15 | Laudo entregue à unidade errada | Entrega por unidade solicitante e perfil por unidade | Teste de acesso de outra unidade |
| P16 | Vazamento de dado de saúde | Dado mínimo em etiqueta e manifesto; trilha; emergência auditada; estação cifrada | Teste de decodificação do código; revisão de acesso |
| P17 | Hora errada no carimbo | Relógio sincronizado; bloqueio por desvio | Teste de desvio adiantado e atrasado |
| P18 | Alteração do registro por acesso ao banco | Hash encadeado; verificador | Teste de adulteração |
| P19 | Resultado divergente entre este módulo e o GAL | Nenhum sobrescreve; quarentena | Teste de divergência |
| P20 | Etiquetadora parada na coleta | Contingência com rótulo manual e reconciliação | **Pergunta em aberto** (definir o procedimento) |

## Risks / Trade-offs

- **Software como dispositivo médico (RDC 657/2022)** → escopo sem interpretação clínica; enquadramento do roteamento **não
  confirmado**; consultar a ANVISA ou especialista antes de operar fora do próprio serviço.
- **Duplicação com o change irmão** → regras reimplementadas em dois lugares. Mitigação: contratos (specs) alinhados nos nomes;
  convergência futura num pacote comum só quando os dois estiverem estáveis.
- **Integração com o GAL desconhecida** → sem interface oficial localizada. Mitigação: GAL como adaptador opcional; ciclo funciona
  sem ele; tarefa de fonte primária antes de codificar.
- **Quarentena vira lixeira** → se ninguém trabalha a fila, o resultado fica parado. Mitigação: painel, envelhecimento e alerta.
- **Fadiga de alerta** → poucos motivos, todos bloqueantes, nenhum aviso decorativo.
- **Conectividade ruim nas unidades** → estação offline reduz o risco, mas aumenta a superfície de segurança (dado local).
  Mitigação: cifragem, apagar após sincronizar, credencial revogável.
- **Normas mudam por portaria** (SIGTAP, lista de agravos, REL) → tabelas versionadas com vigência, não código fixo.
- **Sem equipamento nem unidade real** → nada foi exercitado em campo; modo sombra em uma unidade antes de ampliar.

## Migration Plan

1. **Uma unidade coletora e o laboratório**, fluxo completo com digitação conferida e a impressora disponível, em paralelo ao
   processo atual (modo sombra: o módulo registra, o papel continua valendo).
2. **Remessa** entre essa unidade e o laboratório, depois a central de recebimento.
3. **Entrega ao solicitante** e prazo por etapa.
4. **RNDS** em homologação, depois produção; **GAL** conforme interface confirmada.
5. **Produção e notificação**, conferidas contra o fechamento manual de uma competência.
6. **Demais unidades e coleta em campo**.

Reversão: voltar uma unidade ao processo anterior não apaga o que já foi gravado (custódia imutável). Nenhum passo altera outro
módulo do repositório.

## Open Questions

- Nome do app e do repositório (provisório: `laboratorio_sus`) e **licença** (MIT, como o `erpnext_brasil`, ou GPL).
- **Interface de troca de dados do GAL** (existe serviço ou arquivo para sistema externo?) e quais LACENs/estados serão atendidos.
- Obrigação e prazo do **envio do REL** para serviços públicos e quem envia (laboratório ou estabelecimento).
- Quais **procedimentos SIGTAP** exigem BPA individualizado e a fonte oficial dessa regra.
- **Norma de transporte** de material biológico aplicável (tipo de embalagem, temperatura) para o manifesto.
- **Contingência** quando etiquetadora ou sistema caem (define o P20).
- **Provedor de assinatura** do laudo (ICP-Brasil: A1, A3 ou nuvem) e quem libera nos serviços públicos.
- Escopo de **anatomia patológica e microbiologia**, que têm fluxos próprios.
- Se o módulo terá **ponte para o Healthcare** já na primeira versão (hoje: não).
