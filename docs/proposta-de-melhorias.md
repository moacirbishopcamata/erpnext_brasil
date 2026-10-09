# Proposta de melhorias — otimização, gaps e bugs (2026-10-09)

Levantada a partir de `docs/gaps.md`, do que a atualização da pilha mostrou e das falhas de teste desta sessão.
Cada item diz **o que é**, **evidência** e **como fechar**. Nada aqui foi implementado; é a fila proposta.
Itens marcados 🔒 dependem de fonte legal, certificado ou SEFAZ que não estão ao alcance de uma sessão.

## A. Bugs e riscos já observados

| # | Item | Evidência | Como fechar |
|---|---|---|---|
| ✅ A1 | **Teste de bench deixa sobra e quebra o seguinte.** `test_party` cria a `Company` em `setUp` e faz `commit`; uma execução interrompida deixa `_Test Empresa BR` e todo o módulo passa a falhar com `DuplicateEntryError` | falha de 14 testes nesta sessão | criar a empresa com `exists`-ou-reusa, ou limpar no `setUpClass`; não depender do `tearDown` |
| ✅ A2 | **`test_party` leva ~10 min** (14 testes) e é o gargalo de qualquer ciclo de bench | 602 s medidos | a empresa é recriada por teste; criar uma vez por classe (`setUpClass`) e reverter por teste |
| ✅ A3 | **`run-tests` do Frappe gasta >10 min em registros globais** antes do primeiro teste | `test_oauth20` e `test_pdf` interrompidos | usar `--skip-before-tests` no roteiro padrão e documentar em `docs/como-rodar.md` |
| ✅ A4 | **Auditor lista como "indeterminado" o que o OSV resolve** (3 CVEs do Frappe com `last_affected = 16.31.0`) | `docs/auditoria-da-pilha.md` | `faixa_afeta` aceitar `last_affected` do OSV como fallback quando o GitHub não traz faixa |
| A5 (confirmado: o app não chama pdfkit) | **`pdfkit` 1.0.0 sem correção** (CVE-2025-26240, alta) | auditoria | confirmar que nenhum caminho do app chama `from_string` com dado externo; acompanhar o upstream; `grep` em `erpnext_brasil/` e `scripts/` não acha `pdfkit` nem `from_string`; o uso é do Frappe (ver `docs/auditoria-da-pilha.md`). Acompanhar o upstream |
| ✅ A6 | **`docs/gaps.md` desatualizado**: ainda diz que `natOp` não valida 60 caracteres, mas `nfe.py` já valida (`_natureza`) | `nfe.py:135` | revisar a seção 5 contra o código e riscar o que foi pago |

## B. Gaps de costura e cobertura

| # | Item | Evidência | Como fechar |
|---|---|---|---|
| ✅ B1 | **`folha` é o único módulo ligado no `hooks.py` sem teste de bench** (12/13) | `scripts/cobertura_de_bench.py` | teste que grava um documento de folha e relê por outro caminho |
| B2 | **Só cancelamento e CC-e do CT-e têm envio**; os outros nove eventos existem só como montagem | `gaps.md` (CT-e) | adaptador + botão por evento, começando por Comprovante de Entrega e Prestação em Desacordo |
| B3 | **Guarda de relógio fora do MDF-e e da NFC-e** | `gaps.md` (fonte de tempo) | ligar quando o ponto de emissão existir (`fechar-laco-cte-mdfe` 5.2) |
| B4 | **CI não roda bench**: Custom Field, hook e DocType só são provados à mão | `CLAUDE.md` | job opcional no CI com MariaDB + Redis e o roteiro de `scripts/subir.sh`, ao menos no PostgreSQL e MariaDB |
| B5 | **Estorno apurado não vira E111 na EFD** | `gaps.md` 5.3 | 🔒 depende de tabela de ajustes por UF |

## C. Otimização

| # | Item | Observação |
|---|---|---|
| C1 | Medição de relógio e consultas à SEFAZ (status do serviço) com cache e janela já existentes: medir quanto custam no `after_migrate` e nas emissões | medir antes; sem número não há otimização |
| C2 | `importar_codigos` (293 linhas) e a carga de NCM/CFOP/CST: importar em lote com `bulk_insert` e `frappe.enqueue` | ganho esperado só se a carga for lenta; medir |
| C3 | Módulos de integração perto do teto de 320 linhas (`nfe_documento` 301, `transporte_sefaz` 299) | extrair antes que o `test_arquitetura` reprove a próxima alteração |
| C4 | Roteiro de bench em paralelo por módulo, com um site descartável por execução | reduz A1–A3 de vez |

## D. Fora do alcance sem fonte externa 🔒

Limites padrão de tolerância de `dhEmi` (MOC), quebra tolerada por UF, valoração LIFO (artigo do RIR), transferência
entre estabelecimentos (decisão de modelagem: `Company` ou `Warehouse` com CNPJ), tudo que exige homologação
SEFAZ (eventos do CT-e, cabeçalho SOAP, EPEC) e o módulo hospitalar (TISS/CNES/DICOM, sem o app `healthcare`).

## Ordem sugerida

1. **A1–A3 e C4** (testes confiáveis e rápidos) — destravam todo o resto.
2. **A4 e A6** (auditor e documentação honestos).
3. **B1 e B4** (cobertura de bench no CI).
4. **B2, C3** (funcionalidade e dívida).
5. **A5** acompanhar; **D** só com fonte.
