## Context

Ver `proposal.md` (Why). Estado e restrições:

- **NFS-e**: só `fiscal/documento/identificador_nfse.py` (identificadores da DPS com 45 posições e da NFS-e com 53). As fontes primárias foram lidas em sessão anterior e não estão no repositório (a tarefa 1.1 as baixa de novo): XSD `v1.01` (`DPS`, `NFSe`, `evento`, `pedRegEvento`, `tiposComplexos`, `tiposSimples`) e o manual da API `v1.2`. Há duas diferenças de arquitetura em relação à NF-e, já documentadas: a emissão nacional é **síncrona** (sem lote e recibo) e a API de eventos é **única e genérica**.
- Todo o transporte atual do app é **SOAP com TLS mútuo** (`TransporteSefaz`). O emissor nacional é **REST/JSON com XML assinado**. O certificado A1, a assinatura (`fiscal/documento/assinatura.py`, `integracao/assinador_local.py`) e o TLS mútuo se reaproveitam; o envelope não.
- **Regra de camadas**: regra pura em `fiscal/` sem `frappe`; `integracao/` fina (≤ 320 linhas por módulo, imposto por `tests/test_arquitetura.py`); Custom Field lido pela integração declarado em `setup/`.
- **Modais**: `MODAL_*` de `fiscal/cte.py` (`"01"`…`"06"`) e os do MDF-e (`"1"`…`"4"`, sem dutoviário nem multimodal) **não são intercambiáveis**; reaproveitar a codificação de um no outro foi apontado como erro em `docs/mdfe-estado.md`. Os modais rodoviários (`cte_rodoviario.py`, 64 linhas; `mdfe_rodoviario.py`, 230 linhas) são o molde.
- A extração de CT-e recebido (`integracao/cte_extracao.py`) trabalha pela chave e exige modelo `57`; é indiferente ao modal.
- A fatura de serviço de saúde: como o Marley Health 16.6.1 fatura é **desconhecido** (mesma tarefa de leitura da change `finalizar-ecf`).
- Convenção do projeto para dado externo pesado: fonte fora do repositório, teste que depende dela pula sem variável de ambiente.

## Goals / Non-Goals

**Goals:**
- Emitir NFS-e pelo caminho nacional para o público que a Resolução CGSN nº 191/2026 obriga a partir de 1º/11/2026, com estado persistido e cancelamento.
- Nenhuma transmissão pelo caminho errado: a escolha é explícita e o que não existe é recusado com motivo.
- CT-e e MDF-e aquaviário, depois aéreo e ferroviário, cada um entregável sozinho.
- Serviço de saúde tratado sem vazar dado clínico e sem emitir nota onde não há cobrança.

**Non-Goals:**
- Emitir NFS-e de municípios sem caminho implementado, além do nacional e, condicionado ao manual, Porto Velho.
- CT-e dutoviário e multimodal; MDF-e dutoviário (não existe no leiaute).
- Decidir se o MDF-e é obrigatório em cada transporte; o app não codifica essa regra, só a documenta.
- Recepção e importação de NFS-e de terceiros (entrada).
- Provar autorização real: sem certificado A1 e ambiente de teste, fica "não executado".

## Decisions

1. **Nacional antes do municipal.** Motivos: as fontes primárias do nacional estão lidas; a obrigatoriedade de 1º/11/2026 para Simples ME/EPP cria o usuário que faltava na decisão de 2026-09; o municipal de Porto Velho depende de um manual que ainda não foi obtido. O municipal vira um grupo de tarefas **condicionado** à obtenção do documento: se não vier, o município continua recusado. *Alternativa*: municipal primeiro por ser "o de Porto Velho". Rejeitada: sem fonte, produziria código completo e sem conferência, o pior formato de gap segundo o próprio projeto.

2. **O caminho é um dado da empresa, decidido por função pura.** Uma função pura recebe município, regime e data e devolve `NACIONAL`, `MUNICIPAL` ou `DESCONHECIDO`; `DESCONHECIDO` e caminho sem implementação recusam. A regra do Simples ME/EPP entra com fonte e data (Resolução CGSN nº 191/2026, a confirmar no texto oficial). *Alternativa*: Select livre na `Company`. Rejeitada sozinha: o usuário erraria o caminho e só saberia na rejeição. O Select continua existindo para os casos que a função não decide, mas a função recusa a combinação incoerente.

3. **Transporte REST como porta.** `fiscal/` define um `Protocol` de transporte de NFS-e (enviar DPS, consultar por chave, enviar evento); `integracao/` implementa com o certificado A1 e TLS mútuo; os testes usam um transporte falso e a rejeição e o desfecho são os mesmos da NF-e (estado persistido em todos os desfechos). Mesmo desenho de inversão de dependência que já existe para `TransporteFiscal`. *Alternativa*: reaproveitar `TransporteSefaz` com um "modo REST". Rejeitada: SOAP e REST não compartilham envelope nem tratamento de resposta.

4. **Dados oficiais versionados.** Anexos A (municípios e países), B (NBS e lista nacional) e C (INDOP IBS/CBS) viram arquivos de dados com versão, URL, data e hash, lidos por um leitor que recusa código fora da tabela. Mesmo padrão do catálogo da ECF; se os dois ficarem idênticos na prática, um leitor comum é extraído **depois** (duplicar a projeção hoje custa menos que acoplar dois contextos).

5. **Saúde: tabela e recusa, nunca heurística.** O código do serviço vem da tabela oficial, escolhido pelo cadastro do item (configuração explícita por item de serviço). A fonte consultada indica os itens 4.02 (análises clínicas e congêneres) e 4.03 (hospitais, clínicas, laboratórios) da LC 116/2003 e os desdobros 4.03.01 a 4.03.03 do nacional, com sobreposição entre 4.02 e 4.03 que **depende do caso e do município**: por isso não há mapeamento automático. A discriminação é montada de modelo fixo (item + competência); o sistema não lê nem copia texto de atendimento. A distinção paciente × operadora vem do pagador da fatura. *Alternativa*: inferir o item pela descrição. Rejeitada: erro fiscal silencioso.

6. **Modais seguem o molde rodoviário.** Para cada modal, um módulo puro `*_<modal>.py` (validação dos campos, montagem do grupo), Custom Fields por modal em `setup/` com `depends_on` pelo modal escolhido, `montar_infmodal`/`montar_ide` recebendo o grupo, e a recusa "só rodoviário" substituída por recusa **do modal não implementado**. Ordem: aquaviário (uso concreto no Baixo Madeira), aéreo, ferroviário. O leiaute vem do XSD oficial lido inteiro no disco; os testes de conformidade ao XSD usam o arquivo fora do repositório e pulam sem a variável de ambiente.

7. **Emissão de MDF-e permanece ação do usuário.** O despacho de armazém (módulo `sus_brasil`) pode **sugerir** a emissão, mas nunca emitir. A obrigatoriedade varia por UF e por contribuinte (um manual da Sefin-RO afirma, citando a cláusula terceira do Ajuste SINIEF 21/2010, que são obrigados os emitentes de NF-e ou CT-e e que o transporte interno passou a ser exigido em 2021-07-01 em Rondônia; fonte secundária de busca, a ler no original), e um órgão público pode não ser emitente de NF-e naquela operação.

8. **Permissão desde o primeiro método.** Todo método exposto novo (`emitir_nfse`, `cancelar_nfse`) checa permissão antes de ler; `tests/test_whitelist_com_permissao.py` já trava a regressão (lição de RT-02).

## Risks / Trade-offs

- [Leiaute e Notas Técnicas do CGNFS-e mudam; a NT 008/2026 v1.02 é citada em fonte secundária] → todo documento fixa versão do leiaute e data da fonte; a tarefa 1.1 baixa a versão vigente antes de codificar.
- [A resolução do Simples é conhecida por fontes secundárias] → conferir o texto oficial (tarefa 1.2); a função de caminho guarda a fonte e a data.
- [Sem certificado A1 e sem Produção Restrita, não há prova de autorização] → transporte falso nos testes; a síntese de fechamento diz "não executado" e lista o que um teste real exige.
- [Segredo e certificado no TLS mútuo REST] → reusar o caminho existente de leitura do A1; nenhum segredo em log; teste que garante a mensagem de erro sem o conteúdo do certificado.
- [Dado clínico vazar pela discriminação] → montagem por modelo fixo, sem campo livre vindo do atendimento, com teste que passa um atendimento com diagnóstico e confere a ausência dele.
- [XSD dos modais é grande] → leitura em partes pelo disco, nunca resumo; os testes que dependem dele pulam sem o arquivo, então a CI não prova conformidade ao XSD (declarado).
- [Escopo grande numa change] → dois blocos independentes (NFS-e; modais) com tarefas separadas e entregáveis um a um; se o ritmo pedir, a change pode ser dividida na aplicação sem perder rastro.

## Migration Plan

Nada a migrar: não há NFS-e emitida hoje, e a recusa de modais continua valendo até cada modal ficar pronto. Custom Fields e DocTypes novos entram por `bench migrate`. Rollback: remover o botão e o hook; o estado gravado é só registro de documento.

## Open Questions

- O manual de integração municipal de Porto Velho será obtido? Não muda requisito nem o desenho do nacional; define só se o grupo 6 das tarefas executa ou fica registrado como bloqueado.
