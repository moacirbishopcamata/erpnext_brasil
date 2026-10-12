## 1. Fontes primárias e decisões que dependem do serviço

- [ ] 1.1 Ler o texto oficial da Portaria GM/MS 8.276/2025 e o guia de integração da RNDS; registrar em `docs/` o que o REL exige e quem envia, e verificar que o documento cita a fonte e o nível de confiança
- [ ] 1.2 Obter o manual vigente do SIASUS/BPA e a tabela SIGTAP da competência; registrar quais procedimentos do subgrupo 02.02 exigem BPA individualizado e verificar que a regra está citada
- [ ] 1.3 Ler o Anexo 1 do Anexo V da Portaria de Consolidação GM/MS 4/2017 com as alterações vigentes; extrair a lista de agravos com prazo e verificar que cada item cita a portaria de origem
- [ ] 1.4 Investigar se o GAL tem interface de troca de dados com sistema externo (consultar um LACEN); registrar a conclusão e verificar que o adaptador do GAL fica marcado como opcional ou viável
- [ ] 1.5 Levantar a norma vigente de transporte de material biológico e os prazos de estabilidade de três exames de rotina; registrar a fonte e verificar que o manifesto usa esses limites como parâmetro
- [ ] 1.6 Resolver com o serviço as perguntas em aberto do `design.md` (licença, contingência P20, assinatura) e verificar que cada resposta foi anotada no design

## 2. Esqueleto do módulo e camada pura

- [ ] 2.1 Criar o app Frappe `laboratorio_sus` com `hooks.py`, `modules.txt` e pacote `puro/` sem `frappe`; verificar que o teste arquitetural falha ao importar `frappe` em `puro/`
- [ ] 2.2 Implementar a validação de CNS e CPF (dígito verificador) e verificar com casos válidos, inválidos e de borda nos testes unitários
- [ ] 2.3 Implementar o identificador de tubo com dígito de conferência e verificar unicidade, rejeição de dígito errado e reinício do contador sem reaproveitar
- [ ] 2.4 Implementar a máquina de estados do exame com tabela de transições e verificar que salto de estado é recusado em todos os pares inválidos
- [ ] 2.5 Implementar o encadeamento de hash da custódia e verificar que alterar qualquer evento quebra a verificação
- [ ] 2.6 Implementar a reserva e o consumo de faixa de identificadores por estação e verificar colisão, anulação do não usado e recusa fora da faixa
- [ ] 2.7 Implementar as regras de rejeição, estabilidade e tempo por etapa e verificar com testes de limite (exatamente no prazo, um minuto depois)
- [ ] 2.8 Definir as portas (`Protocol`) de cadastro, entrada de resultado, impressão, relógio, RNDS e GAL e verificar que a camada pura depende só delas

## 3. Modelo de dados e cadastros

- [ ] 3.1 Criar os DocTypes de paciente, unidade (CNES) e profissional (conselho, CBO) próprios e verificar no bench que o módulo instala sem Healthcare nem app fiscal
- [ ] 3.2 Criar as tabelas de referência versionadas com vigência (SIGTAP, agravos, motivos de rejeição) e verificar que a consulta por competência devolve a versão certa
- [ ] 3.3 Declarar em `setup/` todo Custom Field ou campo que o código lê e verificar com o teste de cobertura de bench

## 4. Solicitação de exame

- [ ] 4.1 Criar a solicitação com validações (CNS/CPF, CNES, profissional, SIGTAP da competência, prioridade, preparo) e verificar a recusa de cada caso incompleto
- [ ] 4.2 Implementar a via "paciente sem documento" com pendência de regularização e verificar que o resultado não segue à RNDS enquanto pendente
- [ ] 4.3 Implementar o cancelamento antes da coleta e o encerramento por descarte depois, e verificar que cancelado não entra na produção

## 5. Etiquetagem e custódia

- [ ] 5.1 Implementar a identificação positiva (dois identificadores) e verificar que sem confirmação não há impressão
- [ ] 5.2 Implementar a impressão no servidor (ZPL por padrão) com registro de impressão e reimpressão com motivo e "2ª via", verificando o leiaute contra a impressora ou simulador
- [ ] 5.3 Impedir a impressão em lote antecipado e verificar a recusa com vários pacientes sem coleta iniciada
- [ ] 5.4 Implementar o evento de custódia de acréscimo com hash encadeado, o verificador periódico e o alerta de quebra, verificando com adulteração direta no banco
- [ ] 5.5 Implementar o bloqueio de liberação por lacuna ou quebra e verificar com um tubo sem evento de recebimento
- [ ] 5.6 Implementar a contingência de rótulo manual com reconciliação e verificar que o tubo reconciliado fica ligado a um identificador válido

## 6. Coleta, recepção e estação offline

- [ ] 6.1 Implementar a coleta com preparo conferido e observação registrada e verificar que a observação aparece no laudo
- [ ] 6.2 Implementar a rejeição com lista enumerada e a recoleta com novo tubo ligado ao rejeitado, e verificar que o identificador antigo nunca é reaproveitado
- [ ] 6.3 Implementar a recepção com leitura do tubo e conferência com a solicitação, verificando que tubo sem solicitação fica retido
- [ ] 6.4 Implementar a estação offline com dado cifrado, sincronização e revogação de credencial, e verificar a colisão de identificador e a perda da estação

## 7. Remessa de amostras

- [ ] 7.1 Implementar a remessa com manifesto e etiqueta sem dado pessoal, e verificar que a etiqueta decodificada não revela paciente
- [ ] 7.2 Implementar a conferência por tubo na saída e na chegada com ocorrência de transporte, verificando tubo faltante, a mais e danificado
- [ ] 7.3 Implementar o registro de temperatura e tempo comparados à estabilidade do exame e verificar o encaminhamento à rejeição
- [ ] 7.4 Implementar o estado "em trânsito" com alerta por tempo e verificar que a remessa sem chegada abre o alerta
- [ ] 7.5 Implementar o vínculo com o identificador do laboratório de referência e verificar que resultado sem vínculo vai à quarentena

## 8. Análise e liberação

- [ ] 8.1 Implementar a entrada de resultado digitado com dupla conferência e verificar que sem conferência não libera
- [ ] 8.2 Implementar o casamento por identificador exato e a quarentena com motivo enumerado, verificando identificador inexistente, ambíguo e com um dígito errado
- [ ] 8.3 Implementar unidade e faixa de referência sem conversão implícita e verificar a retenção por unidade diferente
- [ ] 8.4 Implementar o controle de qualidade por exame e lote com retenção dos resultados do período e verificar com controle reprovado
- [ ] 8.5 Implementar a liberação por profissional habilitado, o conteúdo mínimo do laudo e a assinatura, verificando a recusa de resultado retido
- [ ] 8.6 Implementar a retificação em novo laudo e a comunicação de valor crítico, verificando que o original nunca é editado
- [ ] 8.7 Implementar o adaptador de importação por arquivo passando pelo mesmo casamento e quarentena, verificando que não há caminho que os contorne

## 9. Entrega, RNDS, GAL e relatórios

- [ ] 9.1 Implementar a entrega ao solicitante com ciência e a lista de pendências, verificando o prazo vencido
- [ ] 9.2 Implementar o tempo de resposta por etapa e o relógio sincronizado com bloqueio por desvio, verificando urgência atrasada e relógio adiantado e atrasado
- [ ] 9.3 Implementar a montagem e o envio idempotente do REL à RNDS em homologação, com pendências por dado faltante, verificando reenvio e retificação
- [ ] 9.4 Implementar o adaptador do GAL conforme a conclusão da tarefa 1.4 e verificar a quarentena de resultado divergente
- [ ] 9.5 Implementar a consulta pelo paciente com autenticação e auditoria, verificando que resultado retido aparece como "em andamento"

## 10. Produção e notificação

- [ ] 10.1 Implementar a produção por competência, unidade e procedimento SIGTAP contando só exame liberado, e verificar exame rejeitado e recoletado
- [ ] 10.2 Implementar o instrumento de registro conforme a tabela vigente e o fechamento imutável com retificação, verificando a correção depois do fechamento
- [ ] 10.3 Implementar o alerta de notificação compulsória com a lista versionada e verificar que resultado anterior à vigência não gera alerta

## 11. Segurança e privacidade

- [ ] 11.1 Implementar perfis por função e unidade e verificar o acesso negado de coletador de outra unidade
- [ ] 11.2 Implementar o acesso de emergência com justificativa e a lista de revisão, verificando a recusa sem motivo
- [ ] 11.3 Implementar a trilha de leitura, impressão e exportação com retenção de cinco anos e verificar o registro de uma impressão de laudo
- [ ] 11.4 Implementar relatórios gerenciais sem identificação e a exportação identificada com permissão, verificando a ausência de nome e documento

## 12. Validação, modo sombra e documentação

- [ ] 12.1 Escrever o teste de bench do fluxo completo (solicitação à entrega, com remessa e rejeição) e verificar que passa em WSL2/Linux
- [ ] 12.2 Declarar `MODULOS_COBERTOS` nos testes de bench e verificar que `scripts/cobertura_de_bench.py` não aponta o módulo sem teste
- [ ] 12.3 Escrever os testes de caos (queda na sincronização offline, reenvio à RNDS, relógio fora da tolerância) e verificar que nenhum duplica nem perde evento
- [ ] 12.4 Rodar o modo sombra em uma unidade e comparar com o processo atual, verificando um relatório de divergência até zerar as causas
- [ ] 12.5 Documentar o módulo em `docs/` com índice em `docs/README.md`, a análise de perigos e as lacunas em `docs/gaps.md`, e verificar que `ruff check`, `ruff format --check` e a suíte pura passam
