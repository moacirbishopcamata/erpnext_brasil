## 1. Fonte primária antes do código

- [x] 1.1 Registrar em `docs/nfce-contingencia.md` o tipo de emissão, o prazo de transmissão e
      o leiaute do QR Code em contingência, cada um com a fonte nomeada — **feito em
      2026-09-09**: `tpEmis = 9`, prazo de 24 h, chave e código numérico mantidos, sem série
      distinta, "NFC-e EMITIDA EM CONTINGÊNCIA" no DANFE, e o leiaute v3 literal da NT
      2025.001 v1.03
- [ ] 1.1a Reconferir os cinco parâmetros de contingência contra o MOC federal ou a SEFAZ-RO —
      hoje vêm da SEFAZ-PE (estadual oficial), porque o portal nacional responde com
      redirecionamento em loop; verificar antes de a contingência ir a produção
- [ ] 1.1b Confirmar se a SEFAZ-RO já aceita o QR Code versão 3 — verificar na SEFAZ-RO, porque
      mandar v3 para UF não migrada é rejeição 407, e a v2 implementada continua correta para
      Pessoa Jurídica enquanto não migrar
- [x] 1.2 Conferir no site v16 o nome real da tabela-filha de itens do `POS Invoice` e os campos
      que o POS já preenche — **feito em 2026-09-09** no `bench console`: `items` →
      `POS Invoice Item`; nenhum campo `br_*` no cabeçalho nem no item; o POS consolida em
      `Sales Invoice` via `consolidated_invoice` (Link somente-leitura) e `POS Invoice Merge Log`
- [ ] 1.2a Recusar emissão sobre `Sales Invoice` com `is_consolidated = 1` — verificar com teste
      de bench que a recusa nomeia o motivo e que uma fatura de venda comum continua emitindo
- [ ] 1.3 Levantar quais DocTypes do POS a emissão vai ler (`POS Invoice`, `POS Profile`,
      fechamento de caixa) — verificar que cada um entrou em `setup/leituras_do_erpnext.py` com
      os campos exatos

## 2. Decisão de contingência, pura

- [ ] 2.1 Criar `fiscal/contingencia_nfce.py` com o tipo de resultado da transmissão
      (respondeu / não respondeu / rejeitou / bloqueado) e a função que devolve a ação —
      verificar que `tests/test_arquitetura.py` continua verde (nenhum import de `frappe`)
- [ ] 2.2 Escrever `tests/test_contingencia_nfce.py` cobrindo os três casos que se parecem:
      indisponibilidade entra em contingência, rejeição **não** entra, bloqueio 656 **não**
      entra — verificar por mutação: inverter cada caso faz um teste nomeado falhar
- [ ] 2.3 Acrescentar os códigos de erro novos em `fiscal/codigos_de_erro.py` (faixa 12xx,
      documento) — verificar que `tests/test_codigos_de_erro.py` aceita e que nenhum código
      colide

## 3. Campos e ligação do POS

- [ ] 3.1 Incluir `POS Invoice` na lista de entrada do laço de `setup/campos_documento.py` —
      verificar que os campos aparecem no formulário após `bench migrate` e que a geração
      continua num laço só, sem bloco duplicado
- [ ] 3.2 Ligar `POS Invoice` no `hooks.py` às validações fiscais **e** migrar a entrada
      `POS Invoice: indNFCe` de `INDICADOR_QUANDO_LIGARMOS` para `INDICADOR_POR_DOCUMENTO`, no
      mesmo commit — verificar que `tests/test_indicador_por_documento.py` passa nos dois eixos
- [ ] 3.3 Teste de bench que salva um `POS Invoice` real, relê do banco e confere que os campos
      fiscais persistiram — verificar declarando `MODULOS_COBERTOS` e que a cobertura de bench
      sobe (`scripts/cobertura_de_bench.py`)

## 4. Emissão normal, sem contingência

- [ ] 4.1 Emitir NFC-e a partir do `POS Invoice` reusando `integracao/emissao_nfe.py` e o
      `TransporteSefaz` com `guarda`/`registrador` injetados — verificar em homologação que o
      documento é autorizado e que a chave gravada bate com a da camada pura
- [ ] 4.2 Gravar no documento protocolo, chave e situação; apresentar código e motivo em pt-BR
      quando a SEFAZ rejeitar — verificar com teste de bench que relê do banco por caminho
      independente
- [ ] 4.3 Confirmar que o bloqueio por consumo indevido recusa a transmissão do POS **antes** de
      chamar a SEFAZ — verificar com teste que conta as chamadas ao transporte (zero)
- [ ] 4.4 Fatorar em módulos se `integracao/` passar de 320 linhas — verificar com a conferência
      de tamanho já existente

## 5. Fila de pendências

- [ ] 5.1 Criar o DocType `Pendencia Nfce` em `registros_fiscais/doctype/` com chave, momento de
      entrada, motivo, situação e tentativas — verificar que o registro sobrevive a reinício do
      bench, relendo pelo `bench console`
- [ ] 5.2 Registrar a pendência ao emitir em contingência, num caminho que **não** derruba a
      venda se a gravação falhar (try/except + `frappe.log_error`, como em
      `integracao/consumo_indevido.py`) — verificar com teste que força a falha de gravação e
      confere que a venda conclui e o erro é registrado
- [ ] 5.3 Consulta que devolve quantos documentos estão pendentes e há quanto tempo — verificar
      com teste de bench sobre registros criados no próprio teste

## 6. Autorização posterior

- [ ] 6.1 Processar a fila por `scheduler_events`, consultando a chave antes de reemitir —
      verificar com teste que roda o processamento duas vezes sobre a mesma pendência e confere
      que só há uma emissão
- [ ] 6.2 Tratar os três desfechos distintamente: autorizada fecha a pendência, rejeitada marca
      tratamento humano, denegada idem — verificar um teste por desfecho
- [ ] 6.3 Alerta quando a pendência ultrapassa o prazo do MOC (tarefa 1.1) — verificar com
      relógio injetado, sem `sleep`
- [ ] 6.4 Deixar o agendador desligado por configuração até a conferência em bench — verificar
      que a instalação limpa não processa fila nenhuma sem o operador ligar

## 7. Cupom

- [ ] 7.1 Decidir entre *Print Format* do Frappe e o caminho de impressão do próprio POS
      (pergunta aberta do `design.md`) e registrar a escolha na docstring — verificar que o
      cupom sai pela tela do caixa
- [ ] 7.2 Cupom de venda autorizada com chave em texto, QR Code e endereço de consulta da SEFAZ
      da UF do emitente — verificar conferindo o QR Code gerado contra o portal de homologação
- [ ] 7.3 Cupom de venda em contingência com a expressão "NFC-e EMITIDA EM CONTINGÊNCIA" e o
      QR Code versão 2 (`montar_qrcode_offline`) — verificar que a expressão sai impressa e que
      a chave do cupom é a mesma que a fila vai retransmitir
- [ ] 7.4 Recusar explicitamente a contingência quando o emitente for Pessoa Física (CPF) —
      verificar com teste: a v2 é rejeição 444 nesse caso, e a v3 depende do algoritmo de
      assinatura ainda não confirmado; silêncio aqui produziria cupom irrecuperável

## 8. Fechamento

- [ ] 8.1 Documentar a frente em `docs/nfce-pos.md` e marcar o gap como pago em `docs/gaps.md` —
      verificar que o gap deixa de constar como aberto
- [ ] 8.2 Rodar a suíte pura, a de bench e o `ruff`, e conferir o bump de versão em
      `erpnext_brasil/__init__.py` no mesmo commit — verificar que tudo está verde antes do
      commit local
