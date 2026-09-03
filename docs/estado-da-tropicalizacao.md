# Estado da tropicalização — panorama geral

Documento de andamento, pedido pelo usuário ("como está o andamento da tropicalização?").
Diferente dos `*-estado.md` por frente (`mdfe-estado.md`, `rh-estado-esocial.md`,
`ecf-estado.md`), este olha o app inteiro: o que está pronto, o que está pela metade, o
que nem começou, e — o mais importante — **o que impede um uso real hoje**.

Atualizado em 2026-09-03, versão `0.133.0`.

## Números

| | |
|---|---|
| Módulos de regra pura (`fiscal/`, `contabil/`, `folha/`) | 101 |
| Módulos de integração com o Frappe | 30 |
| Arquivos de teste | 100 |
| Testes automatizados | 1955 (suíte pura, sem bench) |
| Documentos em `docs/` | 102 |
| Linhas de código | ~35.300 |
| Commits | 161 |

## O que está pronto e testado

### Documentos fiscais eletrônicos

| Documento | Estado |
|---|---|
| **NF-e (55)** | Montagem, chave, assinatura, transmissão, consulta, cancelamento, carta de correção, inutilização |
| **NFC-e (65)** | Tudo da NF-e mais QR Code (on-line e contingência offline), URL de consulta por UF |
| **CT-e (57)** | Conteúdo completo do modal rodoviário, assinatura, orquestração, **11 eventos**, autorizador por UF |
| **MDF-e (58)** | Conteúdo completo do modal rodoviário, assinatura, orquestração, **7 eventos**, autorizador nacional |

### Apuração e contabilidade

- Cálculo de ICMS (próprio, ST, DIFAL, FCP), IPI, PIS/COFINS, IBS/CBS e Imposto Seletivo
- Plano de contas brasileiro (Lei 6.404/76), partidas dobradas, apuração periódica
- **ECD** (I050/I051/I150/I155/I200/I250)
- **ECF** — todos os blocos dimensionados (0, J, K, L, M, N, P), com o teto de avanço
  documentado em `ecf-estado.md`
- **EFD-ICMS/IPI** — **arquivo completo do `0000` ao `9999`**: Bloco 0 (cadastros),
  Bloco C (documentos), Bloco E (as três apurações: própria, ST, DIFAL/FCP) e Bloco 9
  (controle), montado e serializado de ponta a ponta com teste de costura
- **EFD-Contribuições** (M200/M210/M600/M610)
- **EFD-Reinf** (R-2099, R-4020)

### RH e folha

- INSS, IRRF (com o redutor da Lei 15.270/2025), FGTS
- **eSocial**: S-1000, S-1010, S-1200, S-1299, S-2200, S-2299, lote, assinatura
  (SHA-256), SOAP 1.1, consulta, retorno, e **transmissão HTTP real**
- Integração com o `hrms` via `regional_overrides`, sem fork

### Financeiro

- Boleto (código de barras e linha digitável FEBRABAN), CNAB 400 e CNAB 240 de retorno
- Pix (payload BR Code / "Copia e Cola")

### Infraestrutura de qualidade

- Camada fiscal pura, sem uma linha de framework — **verificado por teste**
- Lint e formatação do projeto — **verificados por teste** (ver `auditoria-padroes.md`)
- Cobertura real com bench para `certificado_a1` e `party` (`tests_bench/`)
- Alertas: vencimento do certificado A1, documento aprovado em homologação, prontidão
  da EFD, virada de fase da reforma tributária

## O que falta para um uso real — em ordem de impacto

Esta é a parte honesta do documento. O app calcula, monta, assina e transmite; o que
falta é sobretudo **onde guardar o resultado** e **como o usuário opera isso**.

### 1. DocTypes próprios — a lacuna estrutural

O app hoje **não tem nenhum DocType próprio**. Só acrescenta campos customizados a
DocTypes do ERPNext. Isso basta enquanto o dado é atributo de um documento existente
(`br_chave_acesso` numa Sales Invoice), e **não basta** para o que tem vida própria:

- o **XML** autorizado (não é um campo, é um arquivo com histórico);
- os **eventos** de um documento (cancelamento, CC-e, EPEC) — vários por documento, cada
  um com seu protocolo e data;
- o **lote do eSocial** (protocolo de envio, retorno por evento, estado do polling);
- o **arquivo SPED gerado** (período, tipo, hash, quem gerou, quando).

Sem isso, transmitir de verdade não tem onde registrar o que aconteceu. **É a próxima
frente estrutural.**

### 2. Tradução (`locale/`) — infraestrutura ausente

O código nasce em português (regra do projeto), então não há o que traduzir *do* inglês.
Mas o app não tem `locale/` nenhum, e por isso:

- não participa do mecanismo de tradução do Frappe (que hoje usa gettext `.po`);
- não pode **completar nem corrigir** a tradução pt-BR do ERPNext core onde ela erra ou
  omite termo fiscal brasileiro;
- não tem como oferecer o app em outro idioma, se um dia for o caso.

### 3. Interface do usuário

Não há tela própria: nem botão "Emitir NF-e" num Sales Invoice, nem painel de status de
transmissão, nem tela de geração de SPED. Tudo é chamável por código. O gap do PDV
(mostrar o QR Code do Pix na tela de pagamento) está levantado em `pix.md`.

### 4. Transmissão de verdade, exercitada

O código de transmissão existe e está testado com sessão HTTP falsa, mas **nunca foi
executado contra a SEFAZ ou o eSocial de verdade** — falta um certificado A1 real e
ambiente de homologação. Isso é limitação de ambiente, não do código, e está registrado
desde o começo.

### 5. Pendências pontuais já documentadas

- QR Code "versão 3" da NFC-e (NT 2025.001) — bloqueado por fonte inacessível
- Prazos das obrigações acessórias — bloqueado por divergência entre fontes
- Blocos D/H/K/1 da EFD, `C170` e demais filhos do `C100`
- Bloco M da ECF (exige modelar LALUR Parte B do zero)
- Catálogo de códigos da RFB para vários registros de ECF/EFD
- NFS-e (municipal, sem padrão nacional consolidado no escopo até agora)

## Como ler este documento junto dos outros

`docs/README.md` indexa tudo. Os `*-estado.md` por frente têm o detalhe de cada uma; este
aqui é o mapa. Quando uma frente fecha, o resumo dela sobe para "o que está pronto" aqui
e o detalhe fica lá.
