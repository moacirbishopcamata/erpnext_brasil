## Why

Quem usa o **POS do ERPNext** não emite NFC-e. O `POS Invoice` não recebe campo fiscal nenhum
e não está no `hooks.py`: a NFC-e do app sai hoje de um `Sales Invoice` com modelo 65, por uma
tela que não é a do caixa. Medir a tropicalização (30 de 534 DocTypes tocados) expôs esta como
a maior lacuna de **costura** do projeto — não de cálculo: o modelo 65 já está pronto e testado
na camada pura (chave de acesso, autorizadores por UF, QR Code).

Agora porque a venda no varejo é o caso em que a nota **precisa sair na hora, com o cliente na
frente do balcão** — e é o único fluxo do app em que a indisponibilidade da SEFAZ não pode
parar a venda: a NFC-e admite contingência offline, que a NF-e não admite.

## What Changes

- Conjunto de campos fiscais no `POS Invoice` (cabeçalho e itens), gerado pelo mesmo laço de
  `setup/campos_documento.py` que já atende os quatro documentos ligados — sem duplicar
  declaração.
- `POS Invoice` ligado no `hooks.py` às validações fiscais já existentes, e a entrada
  `POS Invoice: indNFCe` **migra** de `INDICADOR_QUANDO_LIGARMOS` para
  `INDICADOR_POR_DOCUMENTO`. O teste-âncora `test_indicador_por_documento` reprova se ficar nos
  dois ou em nenhum.
- Emissão de NFC-e a partir do `POS Invoice`, reusando `emissao_nfe.py` e o `TransporteSefaz`
  (com `guarda`/`registrador` já injetados — o bloqueio por cStat 656 vale para o caixa também).
- **Contingência offline da NFC-e**: emitir com `tpEmis` de contingência quando a SEFAZ não
  responde, autorizar o cupom já entregue quando ela volta, e recusar a venda apenas quando nem
  a contingência é admissível. É a diferença de comportamento que justifica frente própria.
- Impressão do cupom com o QR Code e a chave em texto, no formato que o consumidor precisa para
  conferir na SEFAZ.
- Extensão do contrato de leituras (`setup/leituras_do_erpnext.py`) com os DocTypes do POS que
  passarmos a ler — `POS Invoice` deixa de ser apenas `NOMES_USADOS_COMO_CHAVE`.

## Capabilities

### New Capabilities
- `fiscal/nfce-pos`: emissão de NFC-e (modelo 65) a partir do `POS Invoice`, incluindo os campos
  fiscais da tela de caixa, o indicador `indNFCe` e o cupom impresso com QR Code.
- `fiscal/contingencia-offline`: operar a venda quando a SEFAZ não responde — emitir em
  contingência, entregar o cupom, autorizar depois, e as condições em que a venda é recusada.

### Modified Capabilities
<!-- Nenhuma: o projeto ainda não tem specs registradas em openspec/specs/. -->

## Impact

- **Código do app**: `setup/campos_documento.py`, `hooks.py`,
  `integracao/validacao_fiscal.py` (migração da entrada do indicador),
  `integracao/emissao_nfe.py`, `setup/leituras_do_erpnext.py`, e um módulo novo de contingência
  na camada pura (`fiscal/`), sem import de `frappe`.
- **ERPNext**: leitura do `POS Invoice`, `POS Profile` e do fluxo de fechamento de caixa — todos
  estrutura alheia, portanto sujeitos ao contrato de leituras e à conferência de bench.
- **SEFAZ**: nenhum autorizador novo; modelo 65 já mapeado por UF.
- **Gaps**: paga o gap "NFC-e não sai do POS do ERPNext" declarado em `docs/gaps.md`.
- **Riscos**: contingência mal resolvida entrega cupom que nunca autoriza — o pior resultado
  possível, porque a venda já aconteceu. O desenho precisa tratar a fila de autorização
  pendente como estado persistido, não como retry em memória.
