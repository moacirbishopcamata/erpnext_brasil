# Levantamento de estado: eSocial

Mesma disciplina de `docs/rh-estado-hrms.md` — levantar antes de implementar. Este
documento não implementa nada; registra o que existe, o tamanho real do problema, e
que decisão de escopo ele levanta antes do próximo incremento.

## O que é

Sistema federal (`gov.br/esocial`) que unifica o envio de eventos trabalhistas,
previdenciários, fiscais e de segurança do trabalho — substitui GFIP, CAGED, RAIS,
DIRF (a partir da versão S-1.3, confirmado abaixo) e outras obrigações que hoje
`erpnext_brasil` nem tenta cobrir. Obrigatório para toda empresa com empregado CLT —
diferente da reforma tributária (IBS/CBS), que ainda está em fase de teste, o eSocial
já está em produção plena para todos os portes de empresa desde 2023 (1º e 2º grupos
desde 2019, 3º grupo — pequenas empresas e MEI com empregado — desde 2021/2023,
conforme cronograma do próprio `gov.br/esocial`, não reconfirmado nesta rodada por já
ser fato consolidado e amplamente coberto).

## Leiaute vigente: S-1.3

Substitui a versão anterior a partir da competência 01/2025 para os eventos S-1210
(pagamentos) e S-2501 (retenções de contribuição previdenciária). Finalidade
principal desta versão: viabilizar a substituição da DIRF por dados que o eSocial já
recebe periodicamente.

`gov.br/esocial/pt-br/documentacao-tecnica/leiautes-esocial-v-1.3` — **página
acessível e legível diretamente** (não PDF digitalizado), um caso raro entre as
fontes `gov.br` deste projeto. Confirma:

- **Formato**: XML/XSD estruturado — como a NF-e (`fiscal/documento/`), não JSON
  Schema. Uma busca inicial levantou a hipótese de JSON Schema (correta apenas para
  uma iniciativa separada, o "eSocial Doméstico" simplificado — não confirmada aqui
  como aplicável ao leiaute geral).
- **Três grupos de eventos**:
  - **Grupo I — Tabelas** (S-1000 a S-1070): cadastro do empregador,
    estabelecimentos, rubricas, lotações tributárias. Enviado uma vez, atualizado
    quando muda.
  - **Grupo II — Periódicos** (S-1200 a S-1299): folha de pagamento, pagamentos,
    fechamento do período — os eventos que consumiriam diretamente
    `folha/inss.py`/`folha/irrf.py`/`folha/fgts.py`.
  - **Grupo III — Não periódicos** (S-2190 a S-8299): admissão, alteração cadastral,
    desligamento, acidente de trabalho, ações judiciais.
- **Identificação do evento**: `Id` de 36 caracteres com posições fixas (tipo,
  CNPJ/CPF do empregador, timestamp) — mesma família de ideia do `Id` da NF-e
  (`chave_acesso.py`), mas layout distinto, não reaproveitável diretamente.
- **Mais de 150 regras de validação nomeadas** (`REGRA_*`) — ordem de grandeza muito
  maior que qualquer XSD já modelado neste projeto (a NF-e tem uma fração disso).

## Transmissão: mesma arquitetura da NF-e, endpoints e certificado próprios

- **WebService SOAP**, XML assinado — igual ao padrão já usado para SEFAZ
  (`fiscal/documento/autorizadores_sefaz.py`, `assinador_local.py`).
- **Assinatura**: certificado digital X.509 do próprio empregador, algoritmo SHA256 —
  mesma família técnica do assinador já implementado para NF-e; **não confirmado
  nesta rodada** se `assinador_local.py` seria diretamente reaproveitável (o formato
  do envelope/canonicalização pode divergir da NF-e o bastante para exigir ajuste).
- **Ambientes**: "Produção Restrita" (sandbox, equivalente à homologação da NF-e) e
  produção plena, endpoints distintos — confirma o mesmo padrão dual de ambiente já
  usado em `autorizadores_sefaz.py`.
- **Lotes de 1 a 50 eventos** por envio — diferente da NF-e (documento a documento);
  mais parecido com o padrão de lote do SPED.

## Por que isto é maior que qualquer coisa já modelada neste projeto

A NF-e — o módulo fiscal mais complexo já implementado aqui — cobre essencialmente
**um** documento (`montar_ide`/`montar_dest`/etc.) com um conjunto de regras conhecido
e bem verificado ao longo de várias sessões. O eSocial tem **dezenas de eventos**,
cada um com sua própria estrutura de grupos/campos, mais de 150 regras de validação
cruzadas, tabelas de domínio próprias (naturezas de rubrica, motivos de afastamento,
categorias de trabalhador) — uma ordem de grandeza de escopo comparável a modelar a
NF-e inteira de novo, várias vezes.

## Decisão de escopo necessária antes de prosseguir

Diferente de INSS/IRRF/FGTS (uma fórmula cada, verificável em uma sessão), qualquer
evento do eSocial é, ele próprio, um sub-projeto do tamanho da NF-e. Não faz sentido
"continuar" aqui sem decidir **qual fatia** atacar primeiro — os candidatos naturais,
em ordem de proximidade com o que já existe:

1. **S-1200 (Remuneração de trabalhador)** — o evento periódico mais próximo do que
   `folha/` já calcula (INSS, IRRF, base de cálculo por rubrica). Ainda assim exige
   modelar rubricas, incidências (tabela de naturezas de rubrica do eSocial, que não
   é a mesma coisa que `Salary Component` do `hrms`), e o evento de fechamento
   (S-1299) que depende de todos os S-1200 do período.
2. **S-2200/S-2299 (Admissão/Desligamento)** — mais isolados entre si, mas exigem
   modelar categorias de trabalhador, tipos de admissão, motivos de desligamento —
   tabelas de domínio que este projeto não tem hoje em nenhuma forma.
3. **Só a camada de transporte** (assinatura + envio de lote + consulta de
   processamento), sem nenhum evento de negócio ainda — replica a arquitetura de
   `autorizadores_sefaz.py` para o eSocial, mas não produz nenhum XML de evento real
   sozinha.

## Ainda por implementar

O usuário escolheu **S-1200 (Remuneração)** como primeira fatia — a árvore completa de
negócio do evento (`docs/rh-esocial-s1200.md`), o envelope de lote/endpoints
(`docs/rh-esocial-lote.md`), a leitura da resposta de envio/processamento
(`docs/rh-esocial-retorno.md`), a assinatura digital (`docs/rh-esocial-assinatura.md`
— confirmado que o assinador da NF-e **não** é reaproveitável sem ajuste: mesma
canonicalização, hash SHA-256 em vez de SHA-1), a serialização da árvore em XML
(`docs/rh-esocial-serializacao.md`, provada com `lxml` de verdade) e a orquestração
serializar→assinar→mesclar→serializar de novo (`docs/rh-esocial-montagem.md`,
provada de ponta a ponta com assinatura real verificada) estão implementados.
Falta: o envio HTTP de verdade (o `requests.post` do lote com certificado,
equivalente ao `_enviar` de `integracao/autorizacao_sefaz.py` da NF-e), o formato do
`Id` de 36 caracteres do evento, e a tabela de rubricas S-1010/cadastro do
empregador S-1000 (pré-requisitos que nenhum evento pode dispensar).

## Fontes

- `gov.br/esocial/pt-br/documentacao-tecnica/leiautes-esocial-v-1.3` — página oficial
  acessível diretamente (HTML estruturado, não PDF digitalizado) — usada para os
  grupos de evento, formato XML/XSD, e a contagem de regras. Consultada em
  2026-08-30.
- Busca agregada (Tecnospeed, TOTVS, User Function — fontes de mercado, não oficiais)
  — usada só para confirmar que a competência 01/2025 já exige S-1.3 para S-1210 e
  S-2501, e o motivo da versão (substituição da DIRF).
- Busca agregada para a arquitetura de transmissão (endpoints, certificado SHA256,
  lote de 1-50 eventos, ambiente de produção restrita) — nenhuma fonte oficial
  `gov.br` lida diretamente para este ponto nesta rodada; o Manual de Orientação do
  Desenvolvedor oficial (PDF, `gov.br/esocial/.../manuais/`) foi localizado mas não
  lido (mesma limitação de PDF já registrada para outras fontes `gov.br` deste
  projeto — não confirmado se este PDF específico é ou não digitalizado como
  imagem).
