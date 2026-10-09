# Fonte de tempo: NTP.br e a Hora Legal Brasileira

Mudança `fonte-de-tempo-ntp-br`. Este documento cresce junto com as tarefas; hoje cobre o que foi
medido de verdade (tarefa 2.3). O texto de operação (como sincronizar o servidor) é a tarefa 6.1.

## O que é o quê

- **Hora Legal Brasileira**: a hora oficial, gerada e mantida pelo **Observatório Nacional**.
- **NTP.br**: serviço do **NIC.br**, em acordo com o ON, que mantém servidores NTP sincronizados com a
  Hora Legal. Não é uma API HTTP: é o protocolo NTP, com NTS para autenticar.
- Servidores stratum 1 públicos: `a.st1` a `e.st1.ntp.br` (NTS em todos, exceto `d.st1`). A página
  do NTP.br **não publica limite de uso** — por isso o app mede de hora em hora, com poucos pacotes.

## Medição real (tarefa 2.3) — 2026-10-09

Rodada da sonda do app (`erpnext_brasil.integracao.relogio_oficial.medir_relogio`) a partir de uma
máquina Windows de desenvolvimento, três servidores (`a`, `b`, `c` `.st1.ntp.br`), três pacotes cada:

| Item | Resultado |
|---|---|
| Fontes que responderam | 2 de 3 (`b.st1.ntp.br`: `TimeoutError` — prazo de 2 s) |
| Fontes concordantes | 2 |
| Dispersão entre as fontes | 5,5 ms |
| Deslocamento medido | **−55,2 ms** (o relógio local está ~55 ms adiantado) |
| Confiável | sim |
| Duração da rodada | 12,8 s (inclui o prazo estourado de uma fonte e as pausas entre pacotes) |

Conferência independente no mesmo momento, `w32tm /stripchart /computer:a.st1.ntp.br /samples:3`:
**−59,4 ms, −58,6 ms e −59,2 ms**. Mesmo sinal, diferença de ~4 ms em relação à sonda — compatível com
a assimetria de rede entre os caminhos (o `w32tm` consultou `a.st1` por IPv6). O que importa para os
limites da política (1 s de aviso, 60 s crítico) é a ordem de grandeza, e ela bate.

O que isso também mostrou, e vale para o desenho:

- **Uma fonte fora do ar é normal.** O consenso de 2 em 3 absorveu o `b.st1` sem perder a
  confiabilidade — é o cenário que o mínimo de três servidores existe para cobrir.
- **A rodada demora (~13 s)** quando uma fonte não responde. Por isso a medição é uma tarefa
  agendada, nunca chamada dentro de uma emissão: a guarda lê a última medição do cache.
