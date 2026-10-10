## Why

O módulo laboratorial do Healthcare (Marley Health 16.6.1, verificado no código) guarda pedido, coleta, amostra, resultado e
laudo, mas **não conversa com nenhum equipamento**: não há DocType de dispositivo, nem leitor de HL7/ASTM, nem DICOM — só
terminologias (`Code System`) e algumas funções de API para lançar resultado (`record_observation_result`,
`add_observation`). Hoje o resultado de um analisador entra digitado, e a etiqueta do tubo é feita fora do sistema.
É exatamente aí que mora o dano ao paciente: **um resultado atribuído à amostra errada**. A mudança é necessária agora
porque o pedido do projeto é etiquetar tubos e ter **rastreabilidade de ponta a ponta**, e a RDC 786/2023 da ANVISA já exige
o que um sistema assim precisa provar (art. 71, 72, 94, 97, 104, 138, 140 — ver `design.md`).

## What Changes

- **Rastreabilidade de ponta a ponta do material biológico**, da solicitação ao descarte: cada tubo e cada alíquota
  tem identificador único, cada passagem de mão gera um evento de custódia que não se apaga nem se reescreve, e o laudo
  é recuperável até o equipamento, o lote de reagente e o controle de qualidade do dia.
- **Etiquetagem de tubos no ponto de coleta**, com identificação positiva do paciente antes de imprimir, rótulo com os
  elementos que a RDC 786 (art. 104) manda e código de barras legível pelos analisadores, e reimpressão que deixa rastro.
- **Camada de integração com analisadores** (protocolos CLSI LIS01/LIS02, ex-ASTM E1381/E1394, e HL7 v2 no perfil IHE LAW),
  como serviço **à parte** do ERPNext, com armazenamento e reenvio (*store-and-forward*): o equipamento não depende de o ERP
  estar no ar, e nenhuma mensagem é perdida nem aplicada duas vezes.
- **Quarentena de resultado**: o que não casa com uma amostra conhecida, ou casa de forma ambígua, **nunca** é anexado a
  paciente; vai para uma fila de pendências para decisão humana.
- **Terminologia laboratorial**: tabela de correspondência código local ↔ LOINC ↔ TUSS (e SIGTAP/CBHPM quando couber), com
  unidades em UCUM, versionada e sem conversão implícita de unidade.
- **Laudo e liberação** conforme a RDC 786 (art. 136 a 140): liberação com assinatura legalmente válida e **retificação
  sempre em novo laudo**, com registro da comunicação ao paciente.
- **Integração de imagem** por intermediário (PACS com DICOM e lista de trabalho da modalidade): o ERPNext guarda pedido,
  estado e laudo com o vínculo do estudo; os pixels ficam no PACS.
- **Relógio sincronizado** em todo ponto que carimba evento (ERP, serviço de interface, estação de coleta), reaproveitando a
  fonte de tempo NTP.br já existente no app fiscal.
- Nada disso altera o `erpnext_brasil` (fiscal) nem o código do Healthcare: é um **app Frappe novo** (nome provisório
  `saude_brasil`) mais um serviço de interface, ambos falando com o Healthcare por DocTypes, campos e API públicos.

## Capabilities

### New Capabilities
- `saude/rastreabilidade-da-amostra`: identidade única de tubo e alíquota, cadeia de custódia imutável, vínculo entre
  resultado, equipamento, reagente e controle, e retenção mínima de 5 anos.
- `saude/etiquetagem-de-tubos`: identificação positiva do paciente, conteúdo e formato do rótulo, impressão auditável e
  reimpressão controlada.
- `saude/integracao-com-analisadores`: recebimento idempotente de resultados, envio de ordens ao equipamento, quarentena,
  reprocessamento da fila, separação entre amostra de paciente e de controle, e política de relógio.
- `saude/terminologia-laboratorial`: correspondência versionada entre código do equipamento, LOINC, TUSS e unidade UCUM.
- `saude/laudo-e-liberacao`: liberação, conteúdo mínimo do laudo, retificação em novo laudo e comunicação de valor crítico.
- `saude/integracao-de-imagem`: pedido, lista de trabalho da modalidade, vínculo com o estudo no PACS e laudo.

### Modified Capabilities

<!-- Nenhuma: o domínio `saude/` é novo e o `fiscal/` não muda. -->

## Impact

- **Código novo**: app Frappe `saude_brasil` (DocTypes de custódia, rótulo, fila de pendências, correspondência de
  terminologia) e serviço de interface em Python (processo à parte, com fila durável local). Camada pura (analisadores
  de protocolo, regras de casamento, política de relógio) sem `frappe`, no mesmo padrão do `fiscal/`.
- **Dependências do Healthcare**: `Lab Test`, `Lab Test Template`, `Sample Collection`, `Observation`, `Diagnostic Report`,
  `Specimen`, `Patient`. Licença do Healthcare é **GPL-3.0**; o `erpnext_brasil` é MIT — ver pergunta em aberto no `design.md`.
- **Infraestrutura do laboratório**: impressoras de etiqueta térmica (ZPL ou TSPL), conversores serial/TCP para
  analisadores antigos, PACS (Orthanc ou dcm4chee), servidor NTP, e certificado ICP-Brasil para assinar laudo.
- **Regulatório**: RDC 786/2023 (ANVISA), Lei 14.063/2020 (assinatura), LGPD (dado de saúde é sensível, art. 11 e 46) e, a
  confirmar com especialista, a RDC 657/2022 (software como dispositivo médico) — o escopo foi desenhado para **não**
  interpretar resultado nem apoiar decisão clínica.
- **Não verificado nesta proposta**: nenhum protocolo foi exercitado com equipamento real; a ISO 15189:2022 e os padrões CLSI
  (pagos) não foram lidos; o IHE LAW foi lido por resumos, não pelo suplemento atual.
