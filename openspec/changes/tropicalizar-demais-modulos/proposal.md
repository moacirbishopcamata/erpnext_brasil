## Why

A varredura de 2026-09-05 (`docs/tropicalizacao-por-area.md`) cobriu contabilidade, aquisições, vendas e
bancos; as de estoque, produção e custos vieram depois. Faltava responder, **por verificação e não de
memória**, o que ainda falta nos demais módulos do ERPNext v16 e do HRMS, no módulo hospitalar e na própria
pilha que os sustenta. Esta mudança é o resultado dessa verificação: separa o que se faz agora do que exige
decisão, fonte ou terceiro, e fixa a ordem.

**"Tropicalizar todo o ERPNext" não cabe numa mudança só**, e dizer o contrário esconderia o que depende de
certificado e SEFAZ reais, de manual de emissor municipal, de fonte legal ainda não localizada e de um app
(Healthcare) que nem está instalado. A proposta entrega o que é certo e verificável, e transforma o resto em
trabalho **rastreável**, cada item com a sua evidência e o seu critério de pronto.

### O que a verificação encontrou

| Frente | Situação verificada |
|---|---|
| `accounts`, `buying`, `selling`, `stock`, `manufacturing`, `assets`, `subcontracting` | levantados e, no essencial, tropicalizados; pendências em `docs/gaps.md` |
| `projects`, `crm`, `support`, `quality_management`, `maintenance`, `portal`, `telephony`, `edi` | **sem código do app**; neutros, salvo as exceções abaixo |
| `regional` do ERPNext | traz modelo de endereço e relatórios de outros países; **o Brasil não está lá** |
| **HRMS** (`hr` e `payroll`) | o app cobre INSS, IRRF, FGTS e 6 eventos do eSocial (S-1000, S-1010, S-1200, S-1299, S-2200, S-2299); o `regional` do HRMS só tem Índia e Emirados |
| **Hospitalar** | `healthcare` é um **app Frappe à parte** e **não está instalado** neste bench (apps: frappe, erpnext, hrms, erpnext_brasil); não há como verificá-lo contra código aqui |
| **A pilha** (Frappe, ERPNext, HRMS, bench, Python, Node, MariaDB, Redis, bibliotecas) | o bench estava **15 versões menores atrás** no Frappe; ver "Pilha e segurança" |

**Lacunas novas, confirmadas** (todas por busca no código, no ERPNext do bench ou em fonte externa):

1. **Nenhum documento auxiliar é gerado** (DANFE, DACTE, DAMDFE): a busca por geração de PDF não acha nada,
   só docstrings. O Print Designer do ERPNext não serve (leiaute normatizado).
2. **Não há recebimento automático de NF-e** (`NFeDistribuicaoDFe`) nem Manifestação do Destinatário; a entrada
   depende do XML anexado à mão. É o análogo da *reconciliação de compras* que a `india-compliance` (a melhor
   localização de ERPNext existente) oferece.
3. **O código de município do `Address` só é conferido por ter 7 dígitos.** Conferido contra a lista oficial do
   IBGE (5.571 municípios): o dígito verificador vale para 5.562; **9 municípios reais o violam** — de modo que
   a regra precisa de exceções, e a coerência do prefixo com a UF vale para todos os 27 prefixos.
4. **Não há consulta de cadastro** (CNPJ, CEP): a `india-compliance` valida e preenche o cadastro a partir da
   API oficial; aqui `Número`, `Bairro` e o código IBGE são digitados à mão.
5. **Não há modelo de endereço brasileiro**: o app declara `Número` e `Bairro`, mas o modelo padrão do Frappe
   não os exibe.
6. **O ERPNext v16 oferece valoração `LIFO`** (`Item` e `Stock Settings`) e o app não diz nada. Fontes
   secundárias afirmam que o UEPS não é aceito para o imposto de renda; o artigo do RIR/2018 **não foi
   localizado** (buscas nesta sessão) — por isso aviso, não bloqueio.
7. **Retenção sofrida na venda de serviços**: só existe a de compra (`R-4020`).
8. **Importação** (CFOP 3.xxx, DI/DUIMP, tributos de importação): zero código e zero documentação.
9. **Projetos/Timesheet → faturamento de serviço**: depende da NFS-e e da retenção sofrida.

**HRMS** (lacunas confirmadas por listagem do `folha/` e do `hrms`):
10. **Faltam eventos do eSocial** da cadeia da folha — pagamentos (S-1210), alteração contratual (S-2206),
    afastamento (S-2230) e os de saúde e segurança do trabalho (S-2210, S-2220, S-2240) — a conferir no leiaute
    S-1.3 oficial antes de qualquer implementação.
11. **Cálculos da folha brasileira sem implementação própria**: férias (com o terço constitucional), 13º salário,
    rescisão e aviso prévio proporcional, DSR e adicionais. Cada regra exige fonte legal citada.
12. **Ponto eletrônico**: a Portaria MTP 671/2021 define REP-C, REP-A e REP-P, o **AFD** e o **AEJ**
    (substituto do AFDT/ACJEF), com assinatura CAdES. O HRMS tem `Employee Checkin` e `Attendance`, mas não gera
    esses arquivos. As datas de adequação divergem entre fontes secundárias; o texto oficial não foi lido.

**Hospitalar** (padrões do setor, pesquisados; nada verificado contra código):
13. **Faturamento TISS/TUSS** (ANS): a versão **4.03.00**, com obrigatoriedade apontada para 2026-07-01 por fonte
    secundária (a página oficial não abriu na pesquisa), e tabelas TUSS atualizadas.
14. **Interoperabilidade**: a RNDS é baseada em HL7 FHIR com perfis nacionais (BR Core); o CNES é fonte cadastral.
    A obrigatoriedade para prestadores **não foi confirmada**.
15. **Integração com equipamentos** (pedido de hoje: raio-x, laboratório, eletrocardiógrafo e afins): o Frappe
    Health **não tem suporte a DICOM** (tópico do fórum oficial, sem data); os padrões de mercado são DICOM
    (worklist, DICOMweb) para imagem, HL7 v2 e FHIR para laboratório e laudos, e um PACS externo.

### Pilha e segurança (verificado hoje na fonte)

- **Frappe 16.36.1 → 16.51.0**, **ERPNext 16.37.0 → 16.50.0**, **HRMS 16.20.1 → 16.50.0** (as pontas do
  `version-16` coincidem com as últimas tags). `bench` 5.31.0 já é o último; Node 24.21.0 também.
- **CVEs dos projetos Frappe** (API de advisories do GitHub): ERPNext 89 publicados, **0 afetam a 16.37.0**
  (a maior correção é 16.35.0); HRMS 8, **0 afetam a 16.20.1**; Frappe 86, com **3 de correção "tbd"**
  (`CVE-2026-53569`, `CVE-2026-62315`, `CVE-2026-63654`); `bench` sem advisories. **Atrasar tem custo**: houve
  dezenas de correções entre a 16.11 e a 16.35 — vários críticos (injeção de template com execução remota, SQL
  injection, tomada de conta) — e as correções do que saiu depois ainda não têm advisory publicado.
- **Mesmo o Frappe 16.51.0 fixa `pypdf==6.15.0` (22 registros no OSV = 11 CVEs distintos, 8 de gravidade
  alta, todos de negação de serviço por PDF malformado) e `Werkzeug==3.1.6`** (1 CVE); o `develop` já fixa
  `pypdf` 6.19.0. `urllib3` 2.7.0 tem 6 registros (3 CVEs, corrigidos na 2.8.0).
- **Fora do que o bench controla sozinho**: MariaDB 10.11.9 → 10.11.19 (LTS até 2028-02-16) e Python 3.14.6 →
  3.14.8 exigem trocar binário; o Redis do sistema é o `7.0.15-1ubuntu0.24.04.4` (a 7.0 do upstream está
  fora de suporte desde 2024-07-29, mas a Ubuntu aplica correções por cima — **não é prova de que está
  sem patches**).

## What Changes

**Já executado nesta sessão** (registrado aqui para a mudança não repetir):
atualização de Frappe, ERPNext e HRMS para as últimas tags, com os dois patches de PostgreSQL de `contrib/`
**refeitos sobre a 16.51.0**; `pypdf`, `Werkzeug` e `urllib3` nas versões corrigidas; Redis 7.2.16 compilado
com checksum conferido; `subir.sh` aceitando `BASE_REDIS`.

**Implementado por esta mudança** (certo, pequeno e verificável sem fonte nova):

- **Código de município conferido de verdade**: dígito verificador **com as 9 exceções reais do IBGE** e uma
  válvula de configuração, e coerência com a UF do endereço.
- **Modelo de endereço brasileiro** instalado quando o site não tem um para o Brasil.
- **Aviso de valoração `LIFO`** no `Item` e no `Stock Settings` — aviso, com a ressalva da fonte.
- **Auditoria reprodutível da pilha**: um script que repete as consultas feitas à mão (versões e fim de suporte,
  advisories dos projetos Frappe, bibliotecas Python) e sai com código diferente de zero quando acha algo.

**Registrado como roteiro, cada um virando mudança própria** (ordem e critérios no `design.md`): DANFE/DACTE/
DAMDFE; distribuição de NF-e e manifestação; consulta de CNPJ/CEP; retenção sofrida; importação; projetos →
serviço; eventos do eSocial e cálculos da folha; ponto (AFD/AEJ); e a frente hospitalar (TISS/TUSS, RNDS/FHIR,
equipamentos). Mais as pendências já abertas: NFS-e, campo livre do boleto e CNAB remessa, subcontratação, E111,
quebra por UF, LALUR Parte B, Bloco D e a seção 5 do MDF-e.

## Capabilities

### New Capabilities

- `fiscal/cadastro-brasileiro`: o endereço e o município do cadastro seguem as regras do IBGE e o formato
  brasileiro, em vez de aceitar qualquer sequência de sete dígitos.
- `fiscal/valoracao-de-estoque`: o método de valoração escolhido é confrontado com a legislação do imposto de
  renda, avisando quando o ERPNext oferece o que o Brasil não admite.
- `fiscal/auditoria-da-pilha`: a pilha que sustenta o ERPNext é conferida contra versões suportadas e
  vulnerabilidades conhecidas, de forma reprodutível.

### Modified Capabilities

<!-- Nenhum requisito existente muda. -->

## Impact

- **Código novo**: `fiscal/codigos/municipio.py` (puro), ajuste em `integracao/party.py`, um instalador de modelo
  de endereço em `setup/`, um validador de valoração em `integracao/`, `scripts/auditar_pilha.py` e entradas em
  `doc_events` (`Item`, `Stock Settings`).
- **Compatibilidade**: o código de município passa a ser recusado se o dígito verificador ou a UF não baterem
  (salvo as exceções); endereços já salvos com código inválido falharão na **próxima** gravação, com mensagem
  que diz o dígito esperado.
- **Dependências do app**: nenhuma nova (biblioteca padrão). **Rede nesta mudança**: só o script de auditoria,
  sob demanda.
- **Operação**: o bench local foi atualizado; os pins de `pypdf` e `Werkzeug` do Frappe estão **à frente** do
  `version-16` upstream até ele absorver as correções.
- **Fontes**: código e docs do repositório; ERPNext v16 do bench; API de advisories do GitHub, OSV, endoflife.date e
  GitHub releases; lista oficial de municípios do IBGE (baixada só para conferir a regra, não incluída no
  repositório); `india-compliance`; páginas do NTP.br; buscas sobre TISS, RNDS, DICOM e a Portaria 671/2021
  (fontes secundárias, indicadas como tal).
