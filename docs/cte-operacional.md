# CT-e operacional: emitir, cancelar e corrigir a partir da fatura de transporte

O que liga a montagem do CT-e (`docs/cte-estado.md`) a um clique na `Sales Invoice`. É a frente 3 da mudança
`fechar-laco-cte-mdfe`; o equivalente do manifesto está em `docs/mdfe-operacional.md`.

## O fluxo

```text
Sales Invoice de transporte (br_natureza_transporte preenchida)
  └─ emitir_cte                        integracao/emissao_cte.py
       garantir_relogio_confiavel()    primeira instrução, antes de alocar número
       montar_cte_do_documento         árvore + chave (número alocado só depois de validar)
       assinar_cte → transmitir_cte    CTeRecepcaoSincV4: uma chamada, sem lote nem recibo
       Transmissao Fiscal              gravado em autorizado, rejeitado e denegado
       br_chave_acesso / br_protocolo_autorizacao   só quando autorizado
```

| Ação | Função | Evento |
|---|---|---|
| Emitir CT-e | `emissao_cte.emitir_cte` | — |
| Cancelar | `eventos_cte.cancelar_cte` | `110111` (justificativa de 15 a 255) |
| Carta de correção | `eventos_cte.corrigir_cte` | `110110` (lista grupo/campo/valor; `nSeqEvento` 1 a 20) |

## Decisões e por quê

- **Síncrono.** O CT-e 4.00 não tem lote nem recibo: não há fila, `dormir` nem tentativas.
- **Só a fatura de transporte.** O botão da NF-e se cala nela e o do CT-e se cala nas outras: oferecer os dois
  convidaria a emitir o documento errado, e o número da série é consumido.
- **A situação é a do CT-e.** `situacao_fiscal` é chamada com `familia: "cte"` (modelo 57 na chave); sem isso o CT-e
  apareceria como "NF-e: Autorizado".
- **Rejeição deixa rastro.** `throw` desfaz a transação; o registro é gravado e commitado antes do erro. A
  mesma correção valeu para `emitir_nfe`, que tinha o defeito.
- **Não reenvia o que já foi aceito.** Cancelar um CT-e cancelado recusa antes de chamar a SEFAZ; a carta avança
  `nSeqEvento` e a rejeitada não o consome.
- **Quem monta o evento é a camada Frappe.** O transporte só assina e envia (`transmitir_evento_cte`).
- **O 656 vale igual** e a guarda recusa antes da SEFAZ (teste com zero chamadas).

## Estado de verificação

| O quê | Situação |
|---|---|
| Envelope e resposta | do `sped-cte` e do XSD `PL_CTe_400` — fonte **secundária** |
| Lógica Frappe | `tests_bench/test_cte_documento.py`, `test_emissao_cte.py` (5), `test_eventos_cte.py` (9) — transporte falso, MariaDB e PostgreSQL |
| Envio à SEFAZ de verdade | **não feito** — exige certificado A1 e homologação (tarefa 3.1) |
| Tela | `public/js/emissao_cte.js`, travada por teste de costura; **não aberta em navegador** |

## Pendência herdada

Os montadores de evento do CT-e tinham a forma da NF-e; cancelamento e CC-e foram corrigidos e os demais estão
em `docs/gaps.md`.
