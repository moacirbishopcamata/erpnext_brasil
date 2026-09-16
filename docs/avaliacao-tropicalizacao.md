# Avaliação consolidada da tropicalização do ERPNext

Atualizado em 2026-09-16, versão `0.133.0+`. Fonte canônica de números: `docs/gaps.md`.

## Resumo executivo

| Domínio | Pronto | Parcial | Não iniciado | Bloqueado |
|---|---|---|---|---|
| Documentos fiscais (NF-e, NFC-e, CT-e, MDF-e) | 4 | 2 | 0 | 1 |
| Apuração e contabilidade | 7 | 2 | 1 | 0 |
| RH e eSocial | 6 | 1 | 0 | 1 |
| Financeiro | 2 | 0 | 1 | 0 |
| Infraestrutura | 3 | 2 | 0 | 1 |

**Total:** 22 prontos, 7 parciais, 2 não iniciados, 3 bloqueados.

---

## 1. Documentos fiscais

### NF-e (modelo 55)

| Componente | Estado | Change |
|---|---|---|
| Montagem do XML | ✅ Pronto | — |
| Chave de acesso (44 dígitos) | ✅ Pronto | — |
| Assinatura XMLDSig | ✅ Pronto | — |
| Transmissão SOAP | ✅ Pronto | — |
| Consulta protocolo | ✅ Pronto | — |
| Cancelamento (110111) | ✅ Pronto | — |
| Carta de correção (110110) | ✅ Pronto | — |
| Inutilização de numeração | ✅ Pronto | — |
| Painel de status | ⚠️ Parcial — só no Sales Invoice, DN/PI sem | — |
| Numeração sequencial por série | ✅ Pronto — `numeracao_fiscal.py` com SELECT FOR UPDATE | — |
| Botão "Emitir NF-e" | ✅ Pronto — `emissao_nfe.js` | — |
| Botões cancelar/CC-e | ✅ Pronto — `emissao_nfe.js` | — |
| Consumo indevido (cStat 656) | ✅ Pronto — `consumo_indevido.py` | — |
| Transmissão contra SEFAZ real | 🔧 Em andamento — certificado A1 + homologação | `resolver-3-criticos` (5/8) |

### NFC-e (modelo 65)

| Componente | Estado | Change |
|---|---|---|
| Tudo da NF-e + QR Code | ✅ Pronto | — |
| URL de consulta por UF | ✅ Pronto | — |
| Contingência offline (tpEmis=9) | ✅ Pronto | — |
| QR Code versão 3 (NT 2025.001) | ❌ Não iniciado — fonte inacessível | — |
| NFC-e a partir do POS Invoice | ❌ Não iniciado — campos + hook + botão | `emitir-nfce-do-pos` (6/30) |

### CT-e (modelo 57)

| Componente | Estado | Change |
|---|---|---|
| Conteúdo modal rodoviário | ✅ Pronto | — |
| Assinatura | ✅ Pronto | — |
| Orquestração (TransporteSefaz) | ✅ Pronto | — |
| 11 eventos (cancelamento, CC-e, etc.) | ✅ Pronto | — |
| Autorizador por UF | ✅ Pronto | — |
| infDoc opcional (XSD confirmado) | ✅ Decidido — primeiro incremento sem infDoc | `fechar-laco-cte-mdfe` |
| Serviço real: CTeRecepcaoSincV4 (síncrono) | ✅ Decidido — sem lote nem recibo | `fechar-laco-cte-mdfe` |
| Montador puro (cte_documento.py) | ⚠️ Parcial — tasks 2.x pendentes | `fechar-laco-cte-mdfe` (5/30) |
| Transmissão contra SEFAZ real | 🔧 Em andamento — cert A1 + homologação | `resolver-3-criticos` (5/8) |

### MDF-e (modelo 58)

| Componente | Estado | Change |
|---|---|---|
| Conteúdo modal rodoviário | ✅ Pronto | — |
| Assinatura | ✅ Pronto | — |
| Orquestração | ✅ Pronto | — |
| 7 eventos (encerramento, cancelamento, etc.) | ✅ Pronto | — |
| Autorizador nacional único | ✅ Pronto | — |
| Serviço real: MDFeRecepcao (lote + recibo) | ✅ Decidido | `fechar-laco-cte-mdfe` |
| Campos Shipment/ShipmentDeliveryNote | ✅ Levantado — tarefa 1.4 | `fechar-laco-cte-mdfe` |
| Montador puro (mdfe_documento.py) | ⚠️ Parcial — tasks 4.x pendentes | `fechar-laco-cte-mdfe` (5/30) |

---

## 2. Apuração e contabilidade

| Componente | Estado | Observação |
|---|---|---|
| ICMS (próprio, ST, DIFAL, FCP) | ✅ Pronto | — |
| IPI | ✅ Pronto | — |
| PIS/COFINS (cumulativo/não cumulativo) | ✅ Pronto | — |
| IBS/CBS (reforma tributária) | ✅ Pronto | — |
| Imposto Seletivo | ✅ Pronto | — |
| natOp (natureza da operação) | ✅ Pronto — limite 60 chars + sugestão por CFOP | — |
| ECD (escrituração contábil) | ✅ Pronto | — |
| ECF (todos os blocos) | ⚠️ Parcial — blocos prontos, sem gerador de arquivo | `ecf_dados_empresa` órfão |
| EFD-ICMS/IPI (arquivo completo) | ✅ Pronto — do 0000 ao 9999 | — |
| EFD-Contribuições | ✅ Pronto | — |
| EFD-Reinf (R-2099, R-4020) | ✅ Pronto | — |
| Bloco D da EFD | ❌ Não iniciado — nenhum DocType guarda doc de transporte | Bloqueio estrutural |
| Estorno apurado → EFD (E111) | ⚠️ Parcial — valor no documento, falta ajuste | Listado em sped-fiscal.md |
| Quebra tolerada por UF | ❌ Não iniciado — fonte única não encontrada | — |

---

## 3. RH e eSocial

| Componente | Estado | Observação |
|---|---|---|
| INSS | ✅ Pronto | — |
| IRRF (com redutor Lei 15.270/2025) | ✅ Pronto | — |
| FGTS | ✅ Pronto | — |
| eSocial S-1000 (cadastro) | ✅ Pronto | — |
| eSocial S-1010 (rubricas) | ✅ Pronto | — |
| eSocial S-1200 (remuneração) | ✅ Pronto — montador + ponte com Salary Slip | — |
| eSocial S-1299 (fechamento) | ✅ Pronto | — |
| eSocial S-2200 (admissão) | ✅ Pronto | — |
| eSocial S-2299 (desligamento) | ✅ Pronto | — |
| Lote eSocial (montagem, assinatura, SOAP) | ✅ Pronto | — |
| Transmissão eSocial real | 🔧 Em andamento — certificado A1 real necessário | — |
| Integração hrms (regional_overrides) | ✅ Pronto — sem fork | — |

---

## 4. Financeiro

| Componente | Estado | Observação |
|---|---|---|
| Boleto (FEBRABAN) | ✅ Pronto | — |
| CNAB 400/240 retorno | ✅ Pronto | — |
| PIX (payload BR Code) | ✅ Pronto | — |
| NFS-e | ❌ Não iniciado — sem padrão nacional | Fora de escopo |
| Campo livre do boleto (por banco) | ⚠️ Parcial — `conta_bancaria` órfão | Depende de tropicalização bancária |

---

## 5. Infraestrutura

| Componente | Estado | Observação |
|---|---|---|
| Camada fiscal pura (sem frappe) | ✅ Pronto — verificado por teste | — |
| Lint e formatação | ✅ Pronto — verificado por teste | — |
| Suíte pura (2851 testes) | ✅ Pronto | — |
| Testes de arquitetura (5 testes) | ✅ Pronto | — |
| Bench tests (5 de 31 módulos) | ⚠️ Parcial — 26 módulos sem cobertura | Prioridade: módulos de hooks.py |
| Certificado A1 + SEFAZ real | 🔧 Em andamento — bench achado, site existe | `resolver-3-criticos` |
| Bench WSL | ✅ Pronto — `~/.local/bin/bench` v5.31.0 | — |

---

## 6. Gaps de costura (gaps.md seção 1)

| Gap | Estado | Observação |
|---|---|---|
| 1.1 br_chave_acesso | ✅ Corrigido | — |
| 1.2 br_cfop_sugerido | ✅ Corrigido | — |
| 1.2-bis 29 campos inexistentes | ✅ Corrigido | — |
| 1.3 Caminho para emitir NF-e | ✅ Corrigido | — |
| 1.4 Módulos inalcançáveis | ⚠️ 4 restantes | cte_extracao, ecf_dados_empresa, efd_dados_cadastrais, conta_bancaria |

---

## 7. Priorização — os 5 maiores bloqueios

| # | Bloqueio | Impacto | Como desbloquear |
|---|---|---|---|
| 1 | Transmissão NF-e/CT-e/MDF-e contra SEFAZ real | Impede validação em produção | Certificado A1 + homologação SEFAZ |
| 2 | NFC-e do POS | Impede emissão em PDV | Change `emitir-nfce-do-pos` (24 tasks restantes) |
| 3 | Montador CT-e puro | Impede transmissão CT-e | Change `fechar-laco-cte-mdfe` (tasks 2.x) |
| 4 | Bench tests (26 módulos) | Bugs só aparecem em produção | Escrever tests_bench para módulos de hooks.py |
| 5 | Bloco D da EFD | Arquivo EFD parcial | Decisão de modelagem (Company vs Warehouse) |

---

## 8. Changes ativos

| Change | Progresso | Bloqueio |
|---|---|---|
| `fechar-laco-cte-mdfe` | 5/30 tasks | Montador CT-e + MDF-e |
| `emitir-nfce-do-pos` | 6/30 tasks | Campos POS + hook + botão |
| `resolver-3-criticos` | 5/8 tasks | Cert A1 + homologação (tasks 3.x) |
| `avaliar-tropicalizacao` | 0/15 tasks | Este documento |
