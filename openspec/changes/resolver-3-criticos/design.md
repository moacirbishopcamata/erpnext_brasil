## Context

A varredura de 2026-09-15 identificou três bugs críticos. Dois são de natureza de
planejamento/documentação, um é de implementação:

- B1: `proposal.md` do change `fechar-laco-cte-mdfe` contradiz `design.md` (decisão 3)
  sobre os serviços de autorização. Quem implementar seguindo o proposal usará serviços
  inexistentes (`CTeAutorizacao4`, `MDFeAutorizacao`).
- G8: `numero_do_documento(doc, modelo, serie)` existe e é testado, mas `emissao_nfe.py`
  não o chama antes de transmitir. O número é lido mas nunca alocado — concorrência
  produz número repetido → rejeição da SEFAZ.
- G9: A cadeia de emissão (`nfe.py` → `certificado_a1` → `assinador_local` →
  `transporte_sefaz` → `autorizacao_sefaz`) foi exercitada só com mock. A assinatura
  XMLDSig, o envelope SOAP e a chave de acesso nunca validaram contra a SEFAZ real.

## Goals / Non-Goals

**Goals:**

- B1: proposal.md alinhado com design.md em menos de 10 minutos.
- G8: `numero_do_documento` chamado antes de `TransporteSefaz.transmitir`; erro de
  alocação recusa a emissão antes de atingir a rede.
- G9: pelo menos uma emissão real contra homologação com cStat 100 (autorizado) ou
  cStat de rejeição com mensagem compreensível.

**Non-Goals:**

- Não implementar fila de retry para G9 — a guarda contra consumo indevido já existe.
- Não alterar o schema de `Transmissao Fiscal` — o registro já cobre todos os desfechos.
- Não criar nova capability ou spec — são fixes, não comportamento novo.

## Decisions

### 1. B1: Correção pontual, não reescrita

Atualizar apenas as linhas 22-24 do `proposal.md` do `fechar-laco-cte-mdfe` para
refletir:
- CT-e: `CTeRecepcaoSincV4` (síncrono unitário, sem lote nem recibo)
- MDF-e: `MDFeRecepcao`/`MDFeRetRecepcao` (lote + recibo)

Não reescrever o proposal inteiro — o restante está correto.

### 2. G8: Alocação antes da transmissão, com recusa em caso de falha

Inserir chamada a `numero_do_documento(doc, modelo=55, serie=doc.br_serie_nfe)`
**antes** de `TransporteSefaz.transmitir` em `emissao_nfe.py`. Se `numero_do_documento`
devolver erro (número não disponível), `frappe.throw()` antes de qualquer rede.

A numeração é por série (`br_serie_nfe` para NF-e, `br_serie_cte` para CT-e, `br_serie_mdfe`
para MDF-e) — já declarada em `setup/custom_fields.py` e lida por `campos_documento.py`.

### 3. G9: Validação manual com certificado real

Rodar `emitir_nfe` em ambiente de homologação com:
1. Certificado A1 configurado no site
2. Documento de teste com dados válidos (CNPJ, endereço, NCM)
3. Verificar cStat: 100 = sucesso; 110-199 = rejeição (investigar); 200+ = erro

Se a assinatura ou o envelope estiverem errados, a SEFAZ rejeita com mensagem descritiva.
Registrar o cStat e a mensagem para ajuste.

## Risks / Trade-offs

- **G8 pode expor bugs de concorrência** que antes eram silenciosos — isso é um ganho,
  não um risco: o bug existia, só não era detectado.
- **G9 depende de infraestrutura** (certificado A1 real) que pode não estar disponível
  no momento da implementação. O task fica registrado e pendente até a infra ficar pronta.
- **B1 é de baixo risco** — mudança pontual em 2 linhas de documento.
