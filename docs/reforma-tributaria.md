# Reforma tributária: IBS, CBS e Imposto Seletivo

Referência do que já é obrigação vigente, do cronograma de transição e das decisões de
implementação. Código em `erpnext_brasil/fiscal/impostos/ibs_cbs.py` e
`erpnext_brasil/fiscal/documento/ibs_cbs_xml.py`.

## Não é frente futura: já bloqueia emissão

**Desde 3 de agosto de 2026**, encerrado o período de tolerância do Ato Conjunto
RFB/CGIBS nº 1/2025, documento fiscal eletrônico **sem os campos de IBS e CBS é rejeitado
pelo autorizador** para empresas do regime regular. A Nota Técnica 2025.002 rege NF-e e
NFC-e.

Para quem integra, isso não é "mais um imposto para calcular": é a diferença entre emitir
e não emitir. Uma localização que ignore IBS/CBS produz notas que não existem.

A obrigatoriedade entrou de forma **escalonada por ondas** — vale confirmar em qual onda
a operação se enquadra.

## Alíquota-teste de 2026

| Tributo | Alíquota | Competência |
|---|---|---|
| CBS | 0,9% | Federal |
| IBS | 0,1% | Estadual e municipal |
| **Total** | **1,0%** | |

Em 2026 a apuração é **meramente informativa**: não há recolhimento, desde que cumpridas
as obrigações acessórias. Os campos, porém, são obrigatórios no documento. O resultado do
cálculo carrega essa distinção no campo `informativo` — "calculado" e "devido" deixaram de
ser a mesma coisa.

O objetivo da alíquota-teste não é arrecadar: é gerar dados de faturamento simulado para
o Comitê Gestor calibrar parâmetros antes da implantação plena.

## IBS é dual

O IBS tem parcela **estadual** e **municipal**, destacadas separadamente no XML
(`pIBSUF`/`vIBSUF` e `pIBSMun`/`vIBSMun`). Tratá-lo como alíquota única é o erro que a
**rejeição 1026** acusa.

Para 2026, a regra **UB18-10** da NT 2025.002 exige `pIBSUF` igual a `0.1000` — toda a
alíquota-teste está na parcela estadual.

> A parcela municipal em zero é **inferência**, não leitura direta da norma: se fosse
> positiva, o IBS total superaria os 0,1% que compõem o teste de 1%. Confirmar contra a NT
> antes de emitir em produção.

## Por fora, não por dentro

Diferença estrutural em relação ao ICMS, e a razão de os dois cálculos **não** poderem ser
unificados:

| | ICMS | IBS e CBS |
|---|---|---|
| Integra a própria base | Sim (`base / (1 - alíquota)`) | Não |
| Integra a base do outro | — | Não |
| Efeito no preço | Embutido | Somado |

É escolha deliberada da reforma, em nome da transparência: o valor destacado é o que se
paga. Há teste comparando os dois sobre a mesma alíquota justamente para que uma
refatoração futura não "unifique" o cálculo e erre os dois de uma vez.

O **Imposto Seletivo**, quando incidir, **integra** a base de IBS e CBS — por isso entra
como parcela somada, e não como tributo calculado à parte.

## Alíquotas de 2027 em diante

**Não estão embutidas no código, e pedi-las levanta erro explícito.** Dependem de lei
ainda por fixar; inventar um número seria pior que exigir que o usuário informe o vigente.
Só 2026 tem valor em norma.

## Cronograma

| Ano | O que acontece |
|---|---|
| **2026** | Alíquota-teste de 1%, informativa. Campos obrigatórios desde 03/08. |
| **2027** | CBS plena. PIS e COFINS extintos. IPI a zero (salvo Zona Franca de Manaus). Entra o Imposto Seletivo. |
| **2029–2032** | IBS sobe gradualmente enquanto ICMS e ISS descem. |
| **2033** | ICMS e ISS extintos. IBS pleno. |

Consequência para este app: a aritmética de ICMS, IPI e PIS/COFINS **continua necessária
por mais seis anos**, convivendo com o novo regime. O que mudou é que ela deixou de ser
suficiente sozinha.

## Grupos do XML

Estrutura do item (grupo UB), validada contra o XSD oficial:

```
IBSCBS
  CST              3 dígitos
  cClassTrib       6 dígitos
  gIBSCBS
    vBC
    gIBSUF   → pIBSUF, vIBSUF
    gIBSMun  → pIBSMun, vIBSMun
    vIBS
    gCBS     → pCBS, vCBS
```

Nos **totais** (`IBSCBSTot`) há uma assimetria que derruba documento: os subgrupos
repetem os nomes `gIBSUF` e `gIBSMun` — **não existe sufixo `Tot`** —, e todos os filhos
são obrigatórios quando o grupo é informado, incluindo `vDif`, `vDevTrib`, `vCredPres` e
`vCredPresCondSus`. Campos ainda não calculados saem **zerados, não omitidos**.

> Duas fontes secundárias independentes descreviam esses subgrupos como `gIBSUFTot` e
> `gIBSMunTot`. As duas estavam erradas. Concordância entre secundárias não substitui a
> fonte normativa.

**No XML a alíquota é percentual com quatro casas** (`0.1000`), não fração. A conversão
acontece num lugar só — a única fronteira onde a regra "alíquota é fração" pode ser
desfeita.

Os totais somam os **valores já arredondados de cada item**, nunca recalculam sobre a base
agregada: o validador confere o total contra a soma dos itens.

## Ainda não implementados

Grupos de casos especiais que a NT define e que dependem do `cClassTrib` da operação:
`gIBSCBSMono` (monofásico), `gTransfCred`, `gEstornoCred`, `gCredPresOper`,
`gCredPresIBSZFM`, `gAjusteCompet`, e os campos do Imposto Seletivo.

## Fontes

- Ato Conjunto RFB/CGIBS nº 1/2025 e Ato Técnico Conjunto RFB/CGIBS nº 1/2026.
- Nota Técnica 2025.002 (NF-e e NFC-e) — regra UB18-10, rejeição 1026.
- Informe Técnico 2025.002 — Tabelas de Classificação do IBS e da CBS.
- `leiauteNFe_v4.00.xsd` e `DFeTiposBasicos_v1.00.xsd`, Pacote de Liberação 010e_v1.02.
- EC 132/2023 e LC 214/2025.
