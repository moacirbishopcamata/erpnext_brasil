## 1. Núcleo puro do NTP

- [x] 1.1 Criar o codec do pacote NTP (48 bytes: codificar o pedido, decodificar a resposta, extrair
      os quatro timestamps, estrato, indicador de salto e código de kiss) em `fiscal/`, sem `frappe` —
      verificar com testes que usam pacotes de bytes conhecidos e que recusam resposta curta, versão
      inválida e estrato 0/16
- [x] 1.2 Implementar deslocamento e atraso (`θ`, `δ` do RFC 5905) recebendo os quatro timestamps
      como parâmetro — verificar com casos calculados à mão (o RFC dá as fórmulas, não um exemplo
      numérico): relógio atrasado, adiantado, certo e rede assimétrica, sinal conferido
- [x] 1.3 Implementar a escolha da amostra de menor atraso por servidor e o consenso entre servidores
      (mediana, dispersão máxima, mínimo de fontes concordantes, descarte de `RATE`/estrato inválido) —
      verificar um teste por cenário da spec: concordam, divergem, uma inválida, nenhuma respondeu
      (resultado "não medido", nunca zero)
- [x] 1.4 Rodar `tests/test_arquitetura.py` — verificar que o novo módulo puro não importa `frappe` e
      que nenhum módulo de integração passa de 320 linhas

## 2. Sonda e cache

- [x] 2.1 Criar o módulo de integração que abre o socket UDP com a lista de servidores, prazo curto e
      transporte injetável — verificar com teste que usa socket falso (resposta válida, timeout,
      servidor que devolve `RATE`) sem tocar a rede
- [x] 2.2 Guardar a última medição no cache do Frappe com TTL e registrar a causa quando "não medido";
      reduzir a frequência ao servidor que devolveu `RATE` — verificar leitura da medição por caminho
      independente do que a gravou e que a medição vencida é tratada como ausente
- [x] 2.3 Medir uma vez contra `a.st1`, `b.st1` e `c.st1.ntp.br` de uma máquina real e registrar o
      resultado em `docs/` — verificar que o deslocamento medido é plausível e comparar com `w32tm` ou
      `chronyc` na mesma máquina (fora da suíte: depende de rede). Feito em `docs/fonte-de-tempo.md`:
      −55 ms contra −59 ms do `w32tm`, 2 de 3 fontes.

## 3. Configuração e alerta

- [x] 3.1 Ler limites, TTL, servidores e as chaves "guarda ligada"/"correção ligada" de `site_config`
      com os padrões do design, validando tipo e faixa — verificar que valor inválido recusa com
      mensagem que nomeia a chave, e que sem configuração valem os padrões
- [x] 3.2 Registrar a medição periódica em `scheduler_events` (`hooks.py`) e emitir o alerta de
      deriva pelo mesmo canal dos alertas fiscais — verificar com teste de costura que a tarefa está
      ligada em `hooks.py` e existe, e com teste do alerta (acima/abaixo do limite, não confiável não
      alerta)

## 4. Guarda de emissão

- [ ] 4.1 Implementar a função de guarda: consulta o cache, recusa acima do limite crítico, avisa
      entre os limites, não bloqueia sem medição confiável e recente, e respeita a chave que a
      desliga — verificar um teste por cenário da spec, com a mensagem de recusa citando o desvio
- [ ] 4.2 Chamar a guarda como primeira instrução de `emitir_nfe` e `emitir_cte` — verificar com
      teste de arquitetura que a chamada vem antes de `numero_do_documento`, e com teste de bench que
      uma recusa não consome número da série nem chama o transporte (contagem zero)
- [ ] 4.3 Chamar a guarda na emissão do MDF-e quando ela existir (tarefa 5.2 de
      `fechar-laco-cte-mdfe`) e deixar a NFC-e para `emitir-nfce-do-pos` — verificar que a pendência
      consta nas tarefas dessas duas mudanças

## 5. Correção opcional do instante de emissão

- [ ] 5.1 Fazer `agora_da_emissao()` somar o deslocamento medido só quando a correção está ligada e
      há medição confiável e recente — verificar que, com a chave desligada (padrão), o resultado é
      idêntico ao de hoje, e que sem medição utilizável cai no relógio do servidor registrando o motivo
- [ ] 5.2 Gravar o deslocamento aplicado junto ao documento emitido — verificar com teste de bench que
      o valor persiste e é relido por outro caminho
- [ ] 5.3 Conferir o `AAMM` da chave perto da virada do mês com a correção ligada — verificar com teste
      que a chave e o `dhEmi` continuam no mesmo mês

## 6. Documentação e fechamento

- [ ] 6.1 Escrever `docs/fonte-de-tempo.md`: o que o NTP.br e a Hora Legal são, como sincronizar o
      servidor com NTS (chrony), o que liberar na rede (UDP 123 e, para NTS-KE, a porta a confirmar no
      NTP.br), o que o app mede e o que não pode fazer — verificar que o texto diz que a acuidade do
      resto do ERPNext depende do servidor
- [ ] 6.2 Calibrar os limites padrão contra a tolerância de `dhEmi` do MOC e registrar a fonte — verificar
      que os padrões do design foram confirmados ou ajustados, e que a guarda só sobe para "ligada por
      padrão" depois disso; resolver as perguntas abertas do `design.md`
- [ ] 6.3 Registrar em `docs/gaps.md` o que ficou de fora (NTS no app, fonte via `chronyc`, NFC-e) —
      verificar que cada item aponta para a mudança ou decisão que o resolve
- [ ] 6.4 Rodar a suíte pura, a de bench e o `ruff`, e subir a versão em `erpnext_brasil/__init__.py` no
      mesmo commit — verificar que tudo está verde antes do commit
