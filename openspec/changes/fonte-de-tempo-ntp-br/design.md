## Context

- O instante de emissão vem de `agora_da_emissao()` (`integracao/configuracao_fiscal.py`): o relógio
  do servidor com o fuso de `System Settings`. Chamado por `nfe_documento`, `cte_documento` e
  `mdfe_documento`. O mapeador da NF-e fixa o modelo 55: a NFC-e não passa por ele e ganha o seu
  caminho na mudança `emitir-nfce-do-pos`, onde a guarda entra quando ela existir. Ver `proposal.md`.
- O app tem a divisão `fiscal/` (puro, nunca importa `frappe`) e `integracao/` (fina, conhece o
  Frappe), cobrada por `tests/test_arquitetura.py`, que também limita módulo de integração a 320
  linhas. A nova capacidade respeita as duas coisas.
- Há precedente de "aviso, não bloqueio" (`alerta_fiscal.avisar_ambiente_de_homologacao`) e de
  tarefa agendada de alerta (`alerta_certificado.verificar_validade_dos_certificados`, em
  `scheduler_events`). A guarda de consumo indevido (`consumo_indevido.garantir_liberado`) é o
  precedente de "recusar antes de chamar a SEFAZ".
- **Fatos da fonte** (conferidos em [ntp.br](https://ntp.br/) e material do NIC.br): o NTP.br é um
  serviço NTP do NIC.br em acordo com o Observatório Nacional, não uma API HTTP; os stratum 1 são
  `a.st1.ntp.br` a `e.st1.ntp.br`, com NTS (exceto `d.st1`); a página **não publica limites de uso**.

## Goals / Non-Goals

**Goals:**

- Medir o desvio do relógio com método padrão (RFC 5905) e dizer o quão confiável é a medição.
- Alertar a deriva e proteger a emissão sem nunca transformar "rede fora" em "emissão parada".
- Deixar claro, no código e na documentação, o limite do que um app pode fazer pela acuidade do
  sistema inteiro.

**Non-Goals:**

- Implementar NTS no app (negociação NTS-KE e AEAD): é protocolo próprio, e o daemon do servidor já
  o faz melhor.
- Disciplinar o relógio (slew/step), virar servidor NTP ou depender de `chronyc`/`ntpq`.
- Cravar a tolerância da SEFAZ para `dhEmi` (é regra do MOC, ainda não verificada neste projeto).

## Decisions

### 1. SNTP próprio sobre `socket`, e não biblioteca nem chamada ao daemon

Um cliente SNTP é um pacote de 48 bytes e quatro timestamps; cabe em ~100 linhas puras
(codificar/decodificar) mais um I/O fino. **Alternativas:** (a) `ntplib` — dependência nova para algo
trivial, num app que hoje só exige `lxml` na suíte pura; (b) ler `chronyc tracking` — reflete a
disciplina do host (inclusive NTS), mas exige binário e permissão no contêiner e só existe onde há
chrony; (c) HTTP numa "API da hora" — o NTP.br não oferece, e a Hora Legal do ON não tem endpoint
público conferido. Fica (a-próprio); (b) pode entrar depois como fonte adicional.

### 2. Cálculo e seleção no núcleo puro; rede na integração

`fiscal/` ganha o codec do pacote, `θ = ((t1−t0)+(t2−t3))/2`, `δ = (t3−t0)−(t2−t1)`, a escolha da
amostra de menor atraso por servidor e o consenso (mediana, com limite de dispersão). Tudo testável
sem socket nem relógio: os quatro timestamps entram como parâmetro. A integração só abre o socket UDP
(injetável nos testes) e guarda a última medição no cache do Frappe com TTL. É a mesma costura
`TransporteSefaz`/`ContextoSefaz`: a regra não conhece o transporte.

### 3. Consenso entre fontes, porque SNTP sem autenticação é forjável

O app não faz NTS, então uma resposta pode ser falsificada no caminho. Duas defesas: **consultar ao
menos três servidores** e só tratar como confiável quando ao menos dois concordam; e **bloquear
emissão só por medição confiável e recente**. Sem isso, quem forjasse respostas poderia travar a
emissão fiscal da empresa. Resposta com estrato 0/16, indicador de salto 3 (relógio não sincronizado)
ou "kiss-o'-death" (`RATE`) é descartada, e `RATE` reduz a frequência àquele servidor.

### 4. Frequência baixa e conservadora

O NTP.br não publica limites; por isso a medição é **horária**, uma amostra curta (poucos pacotes)
por servidor, nunca em loop. A guarda de emissão **lê o cache**, não consulta a rede a cada emissão.
**Alternativa recusada:** medir em cada emissão — adicionaria latência e carga à SEFAZ-crítica e
multiplicaria consultas a um serviço público sem limite declarado.

### 5. Limites e chaves em `site_config`, não num DocType novo

Limites (aviso, crítico), TTL da medição, lista de servidores e as chaves "guarda ligada" e
"correção ligada" são decisão operacional do administrador do servidor, não do usuário de negócio, e
o relógio é do servidor, não da empresa. `frappe.conf` com padrões no código evita DocType, campo por
empresa e migração. **Alternativa:** campos na `Company` — rejeitada, pois o mesmo servidor atende
várias empresas com um único relógio.

Padrões de engenharia propostos (**a calibrar com o MOC, não são prazo legal**): aviso a partir de
1 s; crítico a partir de 60 s; TTL da medição de 2 h (duas rodadas horárias); guarda **ligada**;
correção **desligada**. O app já recusa cravar data legal sem fonte (`alerta_fiscal`); estes números
são deliberadamente configuráveis e documentados como escolha, não como regra da SEFAZ.

### 6. Uma função de guarda, chamada no topo de cada `emitir_*`, antes de alocar número

A guarda de consumo indevido é injetada no `TransporteSefaz`, que só nasce **depois** de o número da
série ter sido alocado (`emitir_nfe`: alocação na linha 147, transporte na 187). Pendurar a guarda de
relógio ali queimaria um número a cada recusa — o oposto do que a spec exige. Por isso ela é uma
função única (`garantir_relogio_confiavel`), chamada como **primeira coisa** de `emitir_nfe`,
`emitir_cte` e da emissão do MDF-e: um ponto de implementação, três chamadores, e um teste que trava
que a chamada vem antes de `numero_do_documento`. Aviso usa `msgprint`; recusa usa `throw` com o
desvio no texto. **Alternativa:** injetar no transporte — rejeitada pelo motivo acima.

### 7. Correção de `dhEmi` opcional, desligada por padrão

Ligá-la faz o documento carregar uma hora diferente da do banco e do sistema, e o `AAMM` da chave
sai de `dhEmi`, então ela muda a chave perto da virada do mês. Só se aplica com medição confiável e
recente, o deslocamento aplicado é gravado junto ao documento (rastreável) e a ausência de medição
cai no relógio do servidor com registro. **Alternativa:** correção sempre ligada — rejeitada: esconde
um servidor desajustado em vez de forçar o conserto, e depende de uma fonte não autenticada.

## Risks / Trade-offs

- **Medição forjada (SNTP sem NTS)** → consenso de ≥ 2 de 3 fontes, bloqueio só com medição
  recente, e guarda desligável; a defesa real é o servidor usar NTS (documentado).
- **Firewall/contêiner sem UDP 123** → resultado "não medido" explícito, nunca zero; não bloqueia.
- **Carga num serviço público sem limite declarado** → medição horária, poucos pacotes, respeito a
  `RATE`; confirmar política com o NIC.br antes de produção.
- **Limite crítico mal calibrado** (alto demais não protege; baixo demais bloqueia à toa) →
  configurável, e a calibração é tarefa explícita contra o MOC antes de ligar a guarda por padrão.
- **Falsa sensação de que "todo o ERPNext" ficou preciso** → a documentação diz com todas as letras
  que isso só se obtém sincronizando o servidor; o app mede e protege o que é fiscal.

## Migration Plan

Aditivo: sem DocType, sem campo, sem patch. Entra com a guarda **ligada** só depois de a calibração
dos limites estar registrada; até lá, medição + alerta ativos e guarda em modo aviso. Reverter é
desligar as chaves em `site_config`, sem desinstalar nada.

## Open Questions

- Os servidores `.st1` aceitam NTP sem NTS sem restrição de taxa para clientes de aplicação? (a
  página do NTP.br não diz; perguntar ao NIC.br.)
- O Observatório Nacional oferece servidor NTP/endpoint próprio da Hora Legal além do NTP.br? (a
  página do ON consultada devolveu 404.)
- Qual a tolerância de `dhEmi` por documento no MOC (NF-e, CT-e, MDF-e), para calibrar os padrões?
