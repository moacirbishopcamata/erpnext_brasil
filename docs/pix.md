# Pix: payload BR Code ("Copia e Cola")

Achado ao levantar o estado dos módulos de pagamento do ecossistema Frappe (a
pedido do usuário): o app `payments` tem PayPal, Stripe, Razorpay, Braintree,
Mpesa, Paytm, Paymob, GoCardless — **nenhum Pix** (conferido no código-fonte do
app, não suposto). Este é o núcleo de cálculo puro, o mesmo tipo de peça que
`boleto.py` já cobre para código de barras/linha digitável.

## O padrão: EMV® QRCPS-MPM tropicalizado pelo Banco Central (BR Code)

TLV (Tag-Length-Value): cada campo é `<ID de 2 dígitos><tamanho de 2 dígitos><valor>`.
O Pix usa esse padrão internacional com campos próprios do Banco Central. A fonte
primária (Manual de Padrões para Iniciação do Pix, `bcb.gov.br`) é um PDF que as
ferramentas de busca não conseguiram extrair nesta rodada (mesma limitação já
vista repetidas vezes neste projeto para PDFs `gov.br` grandes) — os campos vêm
de busca agregada e de um projeto open-source de geração de QR Code Pix.

## CRC16: verificado contra o vetor de teste universal, não um exemplo isolado

O algoritmo é CRC-16/CCITT-FALSE (polinômio `0x1021`, inicial `0xFFFF`, sem XOR
final). Uma primeira tentativa de validar contra um payload de exemplo completo,
de um artigo de terceiro, **não bateu** — o CRC do artigo estava errado, sinal de
erro de transcrição na fonte, não no algoritmo. Verificado em vez disso contra o
vetor de teste padrão universal desta variante de CRC
(`CRC16-CCITT-FALSE("123456789") == 0x29B1`) — citado por praticamente toda
implementação de referência da família CRC-16, uma fonte mais forte que um
exemplo isolado porque não depende de nenhuma fonte específica de Pix ter
transcrito certo. `test_crc_no_final_bate_com_o_recalculo` prova a
auto-consistência do payload gerado (o CRC bate com o recálculo sobre o resto).

## Campos cobertos

`00` (Payload Format Indicator, fixo `01`), `01` (Point of Initiation Method —
estático `11`/dinâmico `12`), `26` (Merchant Account Information: GUI
`br.gov.bcb.pix` + chave Pix), `52` (Merchant Category Code, fixo `0000`), `53`
(Transaction Currency, fixo `986` = BRL), `54` (Transaction Amount, opcional), `58`
(Country Code, fixo `BR`), `59` (Merchant Name, até 25 caracteres), `60` (Merchant
City, até 15 caracteres), `62` (Additional Data — só o `txid`), `63` (CRC16).

## Fora de escopo, deliberadamente

- **Pix dinâmico com endpoint de cobrança** (subcampo `25` de `62`, que aponta
  para uma API de PSP) — exige backend de banco/PSP, não é cálculo puro.
- **Imagem do QR Code** — só a string do payload; desenhar o QR exigiria uma
  biblioteca nova, contra a disciplina deste projeto de não introduzir
  dependência sem necessidade real.
- **Validação de chave Pix contra o DICT** (Diretório de Identificadores de
  Contas Transacionais) — exigiria consulta ao Banco Central em tempo real.

## Sanitização: só ASCII, sem acento

O padrão EMV MPM exige texto sem acentuação nos campos de nome/cidade —
`_sanitizar` remove diacríticos via normalização Unicode antes de truncar.

## Integração: `Company.chave_pix` + método whitelisted

`setup/custom_fields.py` ganhou o campo `chave_pix` em `Company`.
`integracao/pix.py::gerar_payload_pix` lê a chave/nome da empresa e monta o
payload — cidade é parâmetro explícito (não inferido: `Company` não tem campo de
cidade direto, mora no endereço padrão, cadeia de busca frágil demais para valer
a pena aqui). Mesmo padrão de `documento.py`/`party.py`: não testável sem bench.

## PDV: peça pronta, fio ainda não puxado

O usuário pediu para conectar isto ao PDV (Point of Sale) do ERPNext. Investigado
`selling/page/point_of_sale/pos_payment.js`: é jQuery clássico (não Vue), sem um
ponto de extensão genérico para injetar conteúdo por modo de pagamento (ex.
mostrar um QR Code quando "Pix" é selecionado) — os botões de modo de pagamento
são renderizados a partir das linhas de `Sales Invoice Payment`, sem slot
documentado para plugin externo. `Mode of Payment` em si não precisa de código
nenhum para existir ("Pix" é só um registro, tipo `Bank` ou `Phone`) — o que falta
é o lado visual: mostrar o QR Code na tela do PDV quando esse modo é escolhido, o
que exigiria ou um patch client-side no próprio `pos_payment.js` (tocar arquivo do
`erpnext` core, fora da disciplina deste projeto de nunca editar o app original)
ou investigar mais a fundo se existe um hook client-side documentado que este
projeto ainda não achou. **Não implementado — gap registrado, não escondido.**

## Arquivos

- `contabil/pix.py` — `montar_payload`; camada pura, sem Frappe, testável sem
  bench.
- `integracao/pix.py` — `gerar_payload_pix`; camada fina, não testável sem
  bench.

## Fontes

- Busca agregada e um projeto open-source de geração de QR Code Pix
  (`renatomb/php_qrcode_pix`) — usados para o layout dos campos, cruzados entre
  si. Nenhuma leitura direta do Manual de Padrões para Iniciação do Pix
  (`bcb.gov.br`) — PDF ilegível às ferramentas de busca nesta rodada.
- Vetor de teste padrão universal de CRC-16/CCITT-FALSE — usado para verificar o
  algoritmo, mais forte que qualquer exemplo específico de Pix.
- `erpnext/selling/page/point_of_sale/pos_payment.js` (código-fonte lido
  diretamente do clone local) — usado para o levantamento do gap do PDV.
  Consultado em 2026-08-31.
