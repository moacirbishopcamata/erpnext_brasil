# Contingência off-line da NFC-e

Registro da fonte primária para a frente `emitir-nfce-do-pos` (tarefa 1.1). Nada aqui foi
escrito de memória: cada afirmação abaixo tem a origem nomeada no fim do arquivo.

## Por que a NFC-e tem contingência e a NF-e não tem essa

A venda no balcão não pode parar porque a SEFAZ não respondeu — o cliente está na frente do
caixa e a mercadoria sai. Por isso a NFC-e admite **emissão off-line**: o cupom é impresso na
hora, sem autorização, e o XML é transmitido depois.

É o inverso da NF-e modelo 55, cuja contingência é sempre *outro autorizador* (SVC-AN/SVC-RS)
e não "emitir sem autorização". **NFC-e nunca usa SVC** — já registrado em
`docs/nfce-qrcode.md`.

## Os parâmetros confirmados

| O quê | Valor | Origem |
|---|---|---|
| Tipo de emissão | `tpEmis = 9` | SEFAZ-PE |
| Prazo de transmissão posterior | **24 horas** da data/hora da emissão | SEFAZ-PE |
| Chave de acesso | a **mesma** da emissão, inclusive o código numérico original | SEFAZ-PE |
| Série | **não** há série distinta para contingência | SEFAZ-PE |
| Impresso no DANFE NFC-e | a expressão **"NFC-e EMITIDA EM CONTINGÊNCIA"** | SEFAZ-PE |

⚠️ **Estes cinco vêm de fonte estadual oficial (SEFAZ-PE), não do MOC federal.** O portal
`nfe.fazenda.gov.br` responde com redirecionamento em loop às ferramentas — o mesmo bloqueio
que já impediu a leitura do Manual de Padrões Técnicos. Antes de a contingência ir para
produção, conferir os cinco contra o MOC ou contra a SEFAZ-RO, que é a jurisdição do usuário.

A **chave igual** é o detalhe que decide o desenho: a retransmissão não é uma emissão nova.
Se o processamento da fila gerar uma chave nova, vira documento diferente do cupom que o
consumidor já levou.

## O QR Code em contingência é o ponto travado

Este é o único cenário em que o leiaute "versão 3" da NT 2025.001 muda alguma coisa de fato:

```
v3 on-line:      ?p=<chave_acesso>|<versao_qrcode>|<tpAmb>
v3 contingência: ?p=<chave_acesso>|<versao_qrcode>|<tpAmb>|<dia_data_emissao>|<vNF>|<tp_idDest>|<idDest>|<assinatura>
```

Na emissão on-line a v3 encolhe para três parâmetros e não tem assinatura. **A assinatura
existe unicamente para a NFC-e emitida em contingência** — é ela que substitui o CSC como
controle de autenticidade.

### A v3 não é obrigatória — e supor que fosse custa caro

Corrigido em 2026-09-09 lendo a NT inteira. As regras de validação do grupo ZX:

| Rejeição | Quando |
|---|---|
| **407** | QR Code **v3** e a **UF não aceita** essa versão |
| **444** | QR Code **v2** e emitente **Pessoa Física** (Produtor Rural, CPF) |
| 445 / 474 | `assinatura` informada quando não devia, e o inverso |
| 583 | valor da assinatura difere do calculado pela SEFAZ |

A NT diz textualmente que o parâmetro é *"por UF, enquanto todas as UF não migrarem"*, e que
a eliminação do CSC é *"futuramente (sem data definida)"*. Portanto: para emitente Pessoa
Jurídica em RO, a **v2 implementada continua correta**, e migrar antes de a SEFAZ-RO aceitar
a v3 troca um QR Code que funciona por uma nota rejeitada.

### O que falta, exatamente

A NT remete o algoritmo da assinatura ao **"Manual de Padrões Técnicos do DANFE NFC-e e
QR-Code", versão 6.0 (março/2025)** — inacessível às ferramentas. Falta só isto:

- qual chave assina (certificado do emitente, presumivelmente — **não confirmado**);
- qual algoritmo;
- sobre qual string exata;
- em que codificação o resultado entra na URL.

Implementar por dedução seria adivinhar um esquema criptográfico. Aqui isso é pior que em
outros lugares: assinatura errada **não falha na hora**. Falha quando o consumidor, ou o
Fisco, tenta validar o cupom — depois de a venda ter acontecido.

## O que isto impõe ao desenho

1. A fila de pendências guarda a **chave original**; retransmitir não regera chave.
2. O prazo de 24 horas é o limiar do alerta previsto na spec `fiscal/contingencia-offline`
   ("prazo de transmissão previsto no Manual") — sujeito à conferência acima.
3. Enquanto a v3 não for implementada, a contingência **só serve a emitente Pessoa
   Jurídica**, e apenas em UF que ainda aceite v2. Isso não bloqueia a frente do POS: é o
   caso do usuário. Mas precisa ser recusa explícita, não silêncio, se o emitente for CPF.

## Fontes

- **NT 2025.001 — "Simplificação Operacional: Leiaute QR-Code, Resposta Assíncrona Lote 1
  NF-e", versão 1.03 (setembro/2025)**, lida por inteiro em 2026-09-09: leiaute v3 on-line e
  contingência, regras do grupo ZX, rejeições 407/444/445/474/583, dispensa de `CDATA` na tag
  `qrCode`, e a remissão ao Manual de Padrões Técnicos. Obtida por espelho, porque o portal
  oficial não responde às ferramentas.
- **SEFAZ-PE, página de contingência da NFC-e**, consultada em 2026-09-09: `tpEmis = 9`,
  prazo de 24 horas, manutenção da chave e do código numérico, ausência de série distinta,
  expressão obrigatória no DANFE.
- **Portal Nacional da NF-e (`nfe.fazenda.gov.br`)**: inacessível às ferramentas em
  2026-09-09 — redirecionamento em loop em todas as URLs `exibirArquivo.aspx` tentadas.
  Registrado como bloqueio, não como ausência de busca.
