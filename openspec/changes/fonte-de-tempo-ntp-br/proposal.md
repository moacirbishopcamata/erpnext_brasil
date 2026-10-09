## Why

Todo documento fiscal que o app emite carrega um instante de emissão (`dhEmi`) que sai do **relógio
do servidor** — `agora_da_emissao()` (`integracao/configuracao_fiscal.py`), chamado pela NF-e, pelo
CT-e e pelo MDF-e (a NFC-e terá o seu caminho na mudança `emitir-nfce-do-pos`). Se esse relógio deriva, o documento nasce com a hora errada, e nada
no app mede, avisa ou recusa: o erro só aparece como rejeição da SEFAZ (ou, pior, como documento
autorizado com instante incorreto). O mesmo relógio carimba tudo o mais no ERPNext.

O Brasil tem uma fonte oficial de hora: a **Hora Legal Brasileira**, gerada e mantida pelo
Observatório Nacional (ON) e disseminada na internet pelo **NTP.br**, serviço do NIC.br que mantém
servidores stratum 1 sincronizados com ela (`a.st1.ntp.br` a `e.st1.ntp.br`, com NTS). O pedido é
usar essa fonte como referência de acuidade temporal.

Um esclarecimento que muda o desenho: o NTP.br **não é uma API HTTP** — é o protocolo NTP (com NTS
para autenticar). E o app, sendo um app Frappe separado que não pode editar o ERPNext, **não corrige
o relógio do sistema inteiro**: quem faz isso é o daemon de tempo do servidor (chrony/systemd-timesyncd).
O que o app pode fazer — e hoje não faz — é **medir o desvio** contra a referência oficial, **avisar**
quando passa do tolerável e **proteger a emissão fiscal** de um relógio comprovadamente errado.

## What Changes

- **Sonda de relógio contra o NTP.br**: cliente NTP simples (SNTP, sem dependência nova) que consulta
  mais de um servidor do NTP.br e calcula o **deslocamento** e o **atraso de rede** do relógio local
  pelo algoritmo do RFC 5905, devolvendo uma medição que diz o quão confiável ela é (fontes que
  responderam, dispersão entre elas).
- **Alerta recorrente de deriva**: tarefa agendada que mede e avisa quando o desvio passa de um
  limite configurável, pelo mesmo canal dos alertas fiscais existentes (`alerta_fiscal`), sem
  inventar mecanismo novo.
- **Guarda de emissão**: antes de alocar número e transmitir NF-e, CT-e ou MDF-e (e a NFC-e, quando
  ela existir), o app consulta a última medição; acima do limite **crítico** recusa a emissão com mensagem que diz o desvio medido e o
  que fazer, e acima do limite de **aviso** apenas avisa — mesma distinção "aviso, não bloqueio" que
  o app já aplica ao ambiente de homologação. A medição ausente ou vencida **não** bloqueia (rede
  fora não pode parar a emissão).
- **Correção de `dhEmi` pelo desvio medido: opcional e desligada por padrão.** Ligá-la é uma decisão
  consciente (o documento passa a carregar uma hora diferente da do banco e do sistema).
- **Guia de operação**: como pôr o servidor (e o contêiner, via host) para sincronizar com o NTP.br
  usando NTS — que é a única forma de melhorar o instante de **todo** o ERPNext.
- **Fora do escopo**: alterar Frappe/ERPNext; tornar-se servidor NTP; carimbos `creation`/`modified`
  do Frappe (dependem do relógio do servidor/banco, não do app); tolerância oficial da SEFAZ para
  `dhEmi` (vem do MOC, e o app não crava prazo legal sem fonte — ver `design.md`).

## Capabilities

### New Capabilities

- `fiscal/fonte-de-tempo`: medição do desvio do relógio local contra a Hora Legal Brasileira
  (NTP.br), alerta de deriva e proteção da emissão fiscal contra relógio fora do limite.

### Modified Capabilities

<!-- Nenhum requisito existente muda: a guarda de emissão é comportamento novo, descrito na
     capacidade nova. `fiscal/cte-operacional` e `fiscal/mdfe-operacional` não são tocados. -->

## Impact

- **Código novo**: módulo puro de cálculo NTP (deslocamento/atraso/seleção, sem rede) e um módulo
  de integração com o socket UDP; tarefa em `scheduler_events` (`hooks.py`); campos de configuração
  (limites, servidores, correção ligada/desligada) declarados em `setup/`.
- **Código existente tocado**: `agora_da_emissao()` (só se a correção opcional for ligada) e os
  pontos de emissão (`emitir_nfe`, `emitir_cte` e a do MDF-e), para chamar a guarda; `alerta_fiscal` como canal de aviso.
- **Dependências**: nenhuma nova (`socket` e `struct` da biblioteca padrão). Rede de saída: UDP 123
  para os servidores do NTP.br e, se NTS for usado pelo app, TCP 4460 para o NTS-KE — ponto a
  confirmar no site do NTP.br (ver `design.md`).
- **Operação**: ambientes sem saída UDP 123 (comum em contêiner/firewall corporativo) ficam sem
  medição; o comportamento nesse caso é "não bloqueia, mas diz que não mediu".
- **Fontes consultadas**: [ntp.br](https://ntp.br/) (servidores stratum 1 e NTS, relação com o ON);
  apresentações do NIC.br sobre NTP/NTS; base legal da Hora Legal em material do Observatório
  Nacional (Decreto 4.264/2002, Portaria MCT 293/2007). A página do ON sobre a Hora Legal devolveu
  404 na consulta — ficam como pendência de verificação os servidores NTP do próprio ON.
