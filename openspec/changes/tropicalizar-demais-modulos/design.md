## Context

Ver `proposal.md` para a motivação e a lista de lacunas. O app é um app Frappe **separado** (`erpnext_brasil`):
não altera o ERPNext nem o HRMS, e a camada `fiscal/` nunca importa `frappe` (cobrado por
`tests/test_arquitetura.py`). O hospitalar (`healthcare`) é outro app Frappe, **não instalado** neste bench.

Duas ressalvas de método que moldam o desenho, ambas aprendidas nesta verificação:

- **Regra conferida só em exemplos engana.** O dígito verificador do IBGE bateu em 7 municípios conhecidos
  e na fórmula de três fontes; a lista oficial inteira mostrou 9 exceções. Regra de dado oficial só entra
  depois de conferida contra o conjunto completo.
- **Fonte secundária vira aviso, nunca bloqueio.** O UEPS, a versão do TISS e as datas da Portaria 671
  aparecem em fontes secundárias; o dispositivo oficial não foi lido.

## Goals / Non-Goals

**Goals:**

- Entregar agora o que é certo, pequeno e verificável (município, endereço, aviso de LIFO, auditoria da pilha).
- Deixar o resto como roteiro **ordenado, com evidência e critério de pronto**, para que cada item vire uma
  mudança própria sem refazer a pesquisa.
- Não criar dependência nova no app para o que cabe na biblioteca padrão.

**Non-Goals:**

- Implementar DANFE, distribuição de NF-e, folha, ponto ou o módulo hospitalar nesta mudança.
- Incluir no repositório a tabela completa de municípios do IBGE (vem por importação, como as demais tabelas
  oficiais, ou numa mudança própria).
- Cravar prazo ou dispositivo legal sem fonte oficial.

## Decisions

### 1. O roteiro, por ordem de retorno

| # | Item | Por que nessa posição |
|---|---|---|
| 1 | **DANFE / DACTE / DAMDFE** | sem o documento auxiliar, a emissão autorizada não circula; é o maior buraco prático. |
| 2 | **Distribuição de NF-e e Manifestação do Destinatário** | fecha o lado da compra; é o equivalente da *reconciliação de compras* da `india-compliance`. |
| 3 | **Consulta de CNPJ e CEP** | menos digitação e menos erro de cadastro (o princípio "preencha o que o sistema já sabe"). |
| 4 | **HRMS**: eventos do eSocial, cálculos da folha, ponto (AFD/AEJ) | bloco grande, com muita regra legal; cada regra com fonte. |
| 5 | **NFS-e, retenção sofrida, projetos → serviço** | NFS-e depende do manual do emissor municipal; os outros dois dependem dela. |
| 6 | **Hospitalar** | exige instalar o app e levantar contra código; ver decisão 6. |
| 7 | **Importação** | grande, sem demanda declarada; fica por último. |

**Alternativa recusada:** ordenar pelo tamanho. O que é pequeno e certo já está nesta mudança; o roteiro
ordena o que sobra pelo que destrava mais.

### 2. Código de município: dígito verificador com exceções, e a UF como segunda barreira

A conferência é: sete dígitos; prefixo de dois dígitos = código da UF do endereço (quando a UF é conhecida);
e dígito verificador pela regra módulo 10 de pesos 1 e 2 alternados sobre os seis primeiros. **Verificado
contra os 5.571 municípios da lista oficial do IBGE, baixada em 2026-10-09**: 5.562 conformes e 9 exceções
(`2201919`, `2201988`, `2202251`, `2611533`, `3117836`, `3152131`, `4305871`, `5203939`, `5203962`); os 27
prefixos de UF correspondem cada um a uma só sigla.

- As 9 exceções entram como constante com a fonte e a data. Código novo que fuja da regra pode surgir; por isso
  há a chave `brasil_municipios_excecao_dv` em `site_config`, para o administrador não ficar travado até uma
  nova versão do app.
- **Alternativa recusada:** só avisar. A conferência existe para pegar digitação errada, e com as exceções
  conhecidas o falso positivo é raro; bloquear com saída configurável é o equilíbrio.
- **Alternativa recusada:** embutir a tabela dos 5.571. Seria a barreira mais forte (existência), mas o app
  não embute tabelas oficiais grandes — elas vêm por importação — e isso é decisão à parte.

### 3. Modelo de endereço: instalado só se faltar

Um `Address Template` para o Brasil, criado na migração **somente se o site não tiver um**, idempotente.
Mostra logradouro, número, complemento, bairro, cidade com UF e CEP. **Alternativa recusada:** sobrescrever o
modelo existente — o administrador pode ter ajustado o dele.

### 4. LIFO: aviso, não bloqueio

O aviso aparece no `Item` e no `Stock Settings`, para a instalação brasileira, com a ressalva no texto de que o
dispositivo legal está pendente de confirmação. Bloquear seria afirmar uma regra que a pesquisa desta sessão
não sustentou além de fontes secundárias. **Para virar bloqueio:** citar o artigo do RIR/2018 (Decreto
9.580/2018) lido no texto oficial.

### 5. Auditoria da pilha: um script, sem dependência, com saída para automação

`scripts/auditar_pilha.py` usa só a biblioteca padrão e repete as consultas manuais: versões e fim de suporte
(endoflife.date), últimas tags (GitHub), advisories dos quatro projetos Frappe e vulnerabilidades das
bibliotecas (OSV). Três cuidados que vieram dos tropeços desta sessão: o campo de faixa dos advisories do GitHub
às vezes traz **só a versão corrigida** (e `tbd` quando ainda não há); o OSV lista cada CVE **duas vezes**
(GHSA e PYSEC), então se conta por CVE; e **fonte que não responde é "não verificado"**, nunca "em dia".
Código de saída diferente de zero em falha, vulnerabilidade alta/crítica ou componente não verificável.

**Alternativa recusada:** `pip-audit` / Dependabot. Cobrem as bibliotecas, mas não o par Frappe/ERPNext/HRMS/
bench nem o fim de suporte de MariaDB, Redis, Node e Python — que foi onde a defasagem apareceu.

### 6. Hospitalar: um app à parte, e equipamento por intermediário

- **Limite de contexto.** A localização de saúde (TISS, TUSS, CNES, RNDS) vai num **app próprio**, e não dentro
  do `erpnext_brasil`: o `healthcare` pode não estar instalado, e o app fiscal não deve exigir o que não usa
  (mesma razão de o HRMS entrar por `regional_overrides`). Cada contexto mapeia a sua projeção; nenhum importa o outro.
- **Equipamentos nunca falam direto com o ERPNext.** O padrão de mercado é um intermediário por tipo: um **PACS**
  com DICOM e DICOMweb para imagem (raio-x, tomografia, ultrassom) — o Orthanc e o dcm4chee são abertos —, um
  *gateway* HL7 v2/ASTM para os analisadores de laboratório e para o eletrocardiógrafo, e FHIR
  (`ServiceRequest`, `DiagnosticReport`, `ImagingStudy`, `Observation`) como contrato de troca, que é também o
  que a RNDS adota. O ERPNext guarda o **pedido, o estado e o laudo** com ligação ao estudo; as imagens ficam no PACS.
- **Primeiro passo é levantar, não codar:** instalar o Frappe Health v16 num site de teste, listar os
  DocTypes de pedido/resultado/laudo e conferir o que ele já tem (o fórum oficial registra que **não tem DICOM**).
  Só então desenhar a ponte, sobre as normas e não sobre um fornecedor.

### 7. Pins do Frappe: acompanhar o `develop`, devolver ao upstream

`pypdf` 6.19.0 e `Werkzeug` 3.1.9 estão num commit local do branch de patches do Frappe do bench, vindo do
mesmo critério dos patches de `contrib/`: o `develop` já fixa `pypdf` 6.19.0 e há PR para o `Werkzeug`. Vira o
terceiro patch de `contrib/frappe/`, com texto de PR em inglês. As versões têm 12 a 24 dias — **além da
quarentena de 7 dias** que o próprio Frappe aplica (`exclude-newer = "7 days"`).

### 8. Biblioteca para o DANFE: avaliar antes de adotar

`brazilfiscalreport` (LGPL-3.0, `fpdf2`) gera DANFE, DACTE e DAMDFE a partir do XML. Duas cautelas: a **licença**
(o app é MIT; LGPL como dependência dinâmica é compatível, mas empacotar numa imagem Docker acende obrigações) e a
**idade** (a 1.3.0 saiu um dia antes desta pesquisa; seguir a mesma quarentena de 7 dias). A alternativa é um
*Print Format* Jinja no próprio Frappe 16, que já gera PDF — sem dependência nova, mas com o leiaute normatizado
a cargo do app. A decisão fica para a mudança do DANFE, com um protótipo de cada.

## Risks / Trade-offs

- **Código de município bloqueando um endereço válido** → 9 exceções conhecidas, chave de configuração e mensagem
  que diz o dígito esperado.
- **Aviso de LIFO lido como proibição** → o texto diz que o dispositivo legal está pendente.
- **Pins do Frappe à frente do `version-16`** → documentado; sai quando o upstream absorver.
- **Script de auditoria depender de serviços externos** → fonte fora do ar é "não verificado", e nunca "em dia".
- **A mudança parecer maior do que entrega** → o `proposal.md` separa o implementado do roteiro, item a item.

## Migration Plan

Aditivo. O modelo de endereço entra pela migração e só se não existir; os avisos e a conferência de município
entram em `doc_events`. Reverter é tirar as entradas de `hooks.py`; nenhum dado é alterado, e o modelo de
endereço criado pode ser apagado pelo Desk.

## Open Questions

- O artigo do RIR/2018 que veda o UEPS (para promover o aviso a bloqueio).
- O texto oficial da Portaria MTP 671/2021 e as datas de adequação do programa de tratamento do ponto.
- Se a RNDS é obrigatória para prestadores privados, e por qual portaria.
- Qual o *Print Format* ou biblioteca do DANFE (decisão 8), depois do protótipo.
