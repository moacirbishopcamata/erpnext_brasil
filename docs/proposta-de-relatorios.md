# Proposta de relatórios por módulo (2026-10-09)

**Estado hoje: o app não tem nenhum `Report`.** A pesquisa em `erpnext_brasil/` não acha Script Report, Query Report
nem Report Builder; os dados existem (DocTypes próprios e campos `br_*`), mas só se chega a eles pela lista padrão.
Esta é a fila proposta. Nada foi implementado.

## Como construir (regra única para todos)

- **Script Report** (Python em `integracao/`, fino) que chama uma **consulta pura** em `fiscal/`/`contabil/` — a mesma
  separação do resto do app: o relatório não contém regra fiscal. Filtros obrigatórios: `company` e período.
- **Uma consulta por objeto, reusada**: o resumo de `Transmissao Fiscal` alimenta o relatório, o painel e o alerta; não
  são três consultas parecidas (ver o princípio de OOUX do `CLAUDE.md` global).
- **Falha alto onde o silêncio dá dado errado**: relatório fiscal nunca omite documento por filtro implícito; o que
  ficou de fora aparece como linha de conferência ("N documentos sem chave").
- **Permissão por papel** (`Fiscal`/`Accounts Manager`) declarada no `Report`, e `Report` entra em
  `setup/leituras_do_erpnext.py` quando ler DocType do ERPNext.
- Testes: a consulta pura na suíte comum; um teste de bench por relatório que grava dados reais e relê pelo caminho do
  relatório (a lição desta sessão: teste que só chama a função não pega a costura).

## Por módulo

### Registros Fiscais (DocTypes do app)

| Relatório | Fonte | Para quê |
|---|---|---|
| ✅ **Notas por situação e rejeição** (`Notas por Situacao`, 2026-10-09) | `Transmissao Fiscal` (`situacao`, `codigo_status`, `tipo`, `ambiente`) | quantas autorizadas, rejeitadas, denegadas; ranking dos `cStat` de rejeição |
| **Lacunas de numeração** | `Numeracao Fiscal` × `Transmissao Fiscal` | números alocados sem desfecho (inutilização pendente) |
| **Bloqueios por consumo indevido** | `Bloqueio Sefaz` | CNPJ bloqueado, desde quando, quanto falta (regra do 656) |
| **NFC-e pendentes de transmissão** | `Pendencia NFCe` (`transmitir_ate`, `tentativas`) | contingência a vencer — o prazo é legal |
| **Desvio do relógio** | `Transmissao Fiscal` (`deslocamento_relogio_ms`, `instante_corrigido`) | quando o `dhEmi` foi corrigido e por quanto (ver `fonte-de-tempo.md`) |
| **Arquivos SPED por competência** | `Arquivo SPED` | gerado/entregue/recibo por tipo e período |
| **Lotes do eSocial** | `Lote eSocial`, `Evento do Lote eSocial` | rejeitados, em consulta, sem retorno |

### Fiscal (impostos e documentos)

| Relatório | Fonte | Para quê |
|---|---|---|
| **Apuração por imposto e período** | `contabil/apuracao_periodo` | ICMS, IPI, PIS, COFINS, ST, DIFAL — débito, crédito, saldo |
| **Livro de entradas e de saídas** | `Purchase/Sales Invoice` + campos `br_*` | por CFOP, CST, NCM; base do SPED, conferível antes de gerar |
| **Documentos sem chave / sem CFOP / sem NCM** | campos `br_*` | a lista de pendências que impede a emissão |
| **Cobertura de CFOP sugerido × usado** | `cfop_sugestao` | onde o usuário divergiu da sugestão |
| **Prontidão fiscal** | `contabil/prontidao_fiscal` | o que falta configurar antes de emitir (certificado, séries, UF) |
| **Vencimento de certificado A1** | `alerta_certificado` | já existe como alerta; falta a visão em lista |
| **Retenções** | itens com retenção (a levantar, ver `tropicalizar-demais-modulos` 5.7) | 🔒 depende da mudança de retenção sofrida |

### Estoque

| Relatório | Fonte | Para quê |
|---|---|---|
| **Inventário (Bloco H)** | `Bin`/`Stock Ledger Entry` via `efd_bloco_h` | o saldo que será declarado, com valor e método de valoração |
| **Produção (Bloco K)** | `Work Order` via `efd_bloco_k` | insumo × produto por ordem |
| **Rastreabilidade por lote** | `Batch` (`nLote`, `dVal`, `dFab`) | lotes a vencer; ligação com a NF-e |
| **Perdas e quebras** | `contabil/perdas` | perda por motivo e depreciação fiscal |
| **Valoração fora do padrão** | `Item.valuation_method` | itens em LIFO, ligado ao aviso novo (`valoracao.py`) |
| **Custo de aquisição** | `contabil/custo_aquisicao` | composição do custo (frete, seguro, impostos recuperáveis) |

### Contábil e financeiro

| Relatório | Fonte | Para quê |
|---|---|---|
| **Livro razão e diário no formato ECD** | `ecd_i050/i150/i200` | conferência antes de gerar a escrituração |
| **Depreciação fiscal × societária** | `depreciacao`, `Asset Shift Factor` | diferença por bem e por turno (art. 323 do RIR) |
| **Retorno de cobrança (CNAB)** | `cnab240/400_retorno`, `boleto`, `pix` | liquidado, rejeitado, em aberto |
| **Lucratividade** | `contabil/lucratividade` | margem por item/cliente já com impostos |

### Folha e RH (HRMS)

| Relatório | Fonte | Para quê |
|---|---|---|
| **Eventos do eSocial por situação** | `folha/esocial_*` | S-1000/1010/1200/1299 enviados × aceitos |
| **Conferência folha × S-1200** | `folha_para_esocial` | divergência entre o que a folha calculou e o evento |
| **Ponto eletrônico (AFD/AEJ)** | 🔒 Portaria MTP 671/2021 | depende do levantamento 5.5 |
| **Saúde ocupacional (S-2220/2240)** | 🔒 | depende do levantamento 5.4 |

### Hospitalar 🔒

Sem relatório proposto: o app `healthcare` não está instalado e o módulo (TISS, CNES, DICOM) ainda não foi desenhado.

## Ordem sugerida

1. **Notas por situação e rejeição**, **Lacunas de numeração** e **Bloqueios** — dados já gravados, risco legal imediato.
2. **Documentos sem chave/CFOP/NCM** e **Prontidão fiscal** — evitam a rejeição antes de ela existir.
3. **Inventário (H)**, **Rastreabilidade por lote**, **Apuração por imposto** — conferência antes do SPED.
4. Os demais, por demanda.

Cada relatório vira um item pequeno e independente (consulta pura + Script Report + teste de bench); a primeira leva
são três e valida o molde antes de multiplicar.

## Primeiro relatório entregue (2026-10-09)

`Notas por Situacao` (Registros Fiscais): `fiscal/relatorio_notas.py` (consulta pura, 8 testes) + Script Report em
`registros_fiscais/report/notas_por_situacao/` + `tests_bench/test_relatorio_notas.py` (6 testes reais). É o molde dos
demais: empresa e período obrigatórios, nada descartado em silêncio, aviso para autorização sem chave. O nome vai sem
acento, como os DocTypes do app (`Transmissao Fiscal`), porque o Frappe deriva o diretório do nome.
