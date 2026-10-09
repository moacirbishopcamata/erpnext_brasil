# Fonte de tempo: NTP.br e a Hora Legal Brasileira

Mudança `fonte-de-tempo-ntp-br`. Descreve o que o app faz com o relógio do servidor, o que **não**
pode fazer, e como o administrador deixa o servidor certo.

## A frase mais importante

**A acuidade do instante de todo o ERPNext depende do relógio do servidor, e quem corrige o relógio
do servidor é o servidor — não este app.** O app é um app Frappe separado, não altera o ERPNext e não
mexe no relógio do sistema operacional. O que ele faz é *medir* o desvio contra a referência oficial,
*avisar* quando passa do tolerável e *proteger a emissão fiscal* de um relógio comprovadamente
errado. Para que `creation`, `modified`, lançamentos contábeis e tudo o mais carreguem a hora certa, é
preciso sincronizar o servidor (seção abaixo).

## O que é o quê

- **Hora Legal Brasileira**: a hora oficial, gerada e mantida pelo **Observatório Nacional** (base
  legal em material do ON: Decreto 4.264/2002 e Portaria MCT 293/2007).
- **NTP.br**: serviço do **NIC.br**, em acordo com o ON, que mantém servidores NTP sincronizados com a
  Hora Legal. **Não é uma API HTTP**: é o protocolo NTP, com NTS para autenticar.
- Servidores stratum 1 públicos: `a.st1` a `e.st1.ntp.br` (NTS em todos, exceto `d.st1`). A página
  do NTP.br **não publica limite de uso** — por isso o app mede de hora em hora, com poucos pacotes.

## O que o app faz

| Peça | Comportamento |
|---|---|
| **Medição** | De hora em hora (`scheduler_events`), consulta 3 servidores `.st1.ntp.br` por UDP 123, 3 pacotes cada, e calcula o deslocamento do relógio local (RFC 5905). |
| **Consenso** | A medição só é **confiável** se ao menos 2 fontes concordam dentro de 500 ms. Uma fonte sozinha, ou fontes que divergem, dão medição não confiável. |
| **Alerta** | Desvio ≥ limite de aviso notifica os responsáveis fiscais (mesmo canal do alerta de certificado A1). Repete no máximo 1×/dia no mesmo nível; **piorar de nível** avisa na hora. |
| **Guarda de emissão** | Antes de **alocar número** e transmitir NF-e ou CT-e: desvio ≥ limite crítico **recusa** a emissão; entre os dois limites emite e avisa. |
| **Correção do `dhEmi`** | **Desligada por padrão.** Ligada, soma o deslocamento medido ao instante de emissão e o grava no `Transmissao Fiscal` (`deslocamento_relogio_ms`). |

### O que cada nível autoriza

| Nível | Quando | Emissão | Alerta |
|---|---|---|---|
| `ok` | desvio < limite de aviso | normal | não |
| `aviso` | ≥ limite de aviso | emite e avisa o usuário | sim |
| `critico` | ≥ limite crítico | **recusada**, sem consumir número nem chamar a SEFAZ | sim |
| `sem_medicao` | ausente, vencida, não medida ou não confiável | **nunca bloqueia** | não |

`sem_medicao` não bloqueia de propósito: rede fora, ou fontes que discordam, não é prova de relógio
errado, e parar a emissão fiscal por uma falha da própria medição trocaria um risco por outro maior.
Nesse caso a guarda registra no log do app (`frappe.logger("erpnext_brasil")`) que não pôde
verificar, e a causa da falha da medição vai para o `Error Log` (no máximo uma vez por dia).

## Configuração (`site_config.json`)

Todas opcionais; valor inválido cai nos padrões e fica registrado no `Error Log` com o nome da chave.

| Chave | Padrão | O que é |
|---|---|---|
| `brasil_ntp_servidores` | `a/b/c.st1.ntp.br` | Lista de servidores (mínimo 2 distintos). |
| `brasil_ntp_limite_aviso_ms` | `1000` | Desvio a partir do qual avisa. **Em milissegundos.** |
| `brasil_ntp_limite_critico_ms` | `60000` | Desvio a partir do qual a guarda recusa. Tem de ser maior que o de aviso. |
| `brasil_ntp_ttl_s` | `7200` | Validade da medição, em segundos (mínimo 60). Vencida, vira `sem_medicao`. |
| `brasil_ntp_dispersao_ms` | `500` | Quanto duas fontes podem discordar e ainda "concordar". |
| `brasil_ntp_guarda` | `true` | `false` desliga a guarda de emissão (o alerta continua). |
| `brasil_ntp_corrigir_dhemi` | `false` | `true` liga a correção do instante de emissão. |

⚠️ **Os limites são escolha de engenharia, não prazo da SEFAZ.** A tolerância oficial de `dhEmi` está
no MOC e **não foi verificada** neste projeto. Calibrá-los contra o MOC é pendência (tarefa 6.2 da
mudança) — até lá, ajuste conforme a sua operação. Um erro clássico: digitar o limite crítico em
segundos (`60`) em vez de milissegundos; a validação recusa quando ele fica abaixo do de aviso.

## Como sincronizar o servidor (o que realmente melhora o ERPNext inteiro)

O app não faz NTS (negociação NTS-KE e criptografia autenticada): é protocolo próprio, e o daemon de
tempo do servidor o faz melhor. A recomendação do NTP.br é usar NTS sempre que possível.

Com **chrony**, em `/etc/chrony/chrony.conf` (ou num arquivo de `sources.d`):

```text
server a.st1.ntp.br iburst nts
server b.st1.ntp.br iburst nts
server c.st1.ntp.br iburst nts
```

Depois de reiniciar o serviço, confira:

```bash
chronyc sources -v      # a fonte em uso aparece com ^*
chronyc authdata        # mostra que o NTS está ativo em cada fonte
chronyc tracking        # o desvio atual do relógio
```

> ⚠️ Estes comandos seguem a documentação geral do chrony; **não foram executados neste projeto**
> contra o NTP.br. Confirme no site do NTP.br antes de pôr em produção.

**Rede a liberar** (saída): UDP 123 (NTP) e, para o NTS, TCP 4460 (NTS-KE, porta padrão do RFC 8915 —
confirmar no NTP.br que os `.st1` usam a padrão).

**Contêiner**: o contêiner usa o relógio do **host**; sincronize o host. O app também mede de dentro
do contêiner, então a saída UDP 123 do contêiner precisa estar liberada para a *medição* funcionar —
mas a *correção* do relógio é sempre no host.

## Como ver o que o app está medindo

```bash
# Mede agora e guarda (o que o agendador faz de hora em hora):
bench --site <site> execute erpnext_brasil.integracao.medicao_do_relogio.medir_e_guardar

# Lê a última medição guardada:
bench --site <site> execute erpnext_brasil.integracao.medicao_do_relogio.ler_ultima
```

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
limites da política é a ordem de grandeza, e ela bate.

O que isso também mostrou, e vale para o desenho:

- **Uma fonte fora do ar é normal.** O consenso de 2 em 3 absorveu o `b.st1` sem perder a
  confiabilidade — é o cenário que o mínimo de três servidores existe para cobrir.
- **A rodada demora (~13 s)** quando uma fonte não responde. Por isso a medição é uma tarefa
  agendada, nunca chamada dentro de uma emissão: a guarda lê a última medição do cache.

## Segurança: o que a medição não garante

SNTP sem NTS **não autentica**: uma resposta pode, em tese, ser forjada no caminho. As defesas do app
são o eco do carimbo de origem (comparado em 64 bits), o descarte de resposta vinda de outro endereço,
e o **consenso** — a guarda só recusa com uma medição confiável (≥ 2 fontes concordando) e recente,
para que ninguém consiga parar a emissão fiscal forjando uma única resposta. A defesa de verdade é o
servidor usar NTS.

## Fora do escopo desta mudança

- Guarda na emissão do **MDF-e** (entra com a tarefa 5.2 de `fechar-laco-cte-mdfe`) e da **NFC-e**
  (mudança `emitir-nfce-do-pos`, tarefa 4.3a): a função é a mesma, falta o ponto de emissão existir.
- **NTS dentro do app.** Se virar necessário, é mudança à parte.
- Ler o estado do daemon do servidor (`chronyc tracking`) como fonte adicional.
- Saber se o Observatório Nacional oferece servidor NTP próprio além do NTP.br (a página da Hora Legal
  consultada devolveu 404) e a política de uso dos servidores `.st1` para clientes de aplicação.
- Tolerância de `dhEmi` no MOC, para calibrar os limites (tarefa 6.2).
