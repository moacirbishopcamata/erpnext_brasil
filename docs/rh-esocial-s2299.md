# eSocial S-2299: Desligamento de Trabalhador

Par natural do S-2200 (`docs/rh-esocial-s2200.md`) — o evento que fecha o vínculo
aberto lá.

## `verbasResc.dmDev` reaproveita de verdade a estrutura do S-1200

Diferente de toda pegadinha "parece igual mas não é" já registrada neste bloco
eSocial (`tpInsc` do envelope de lote, hash da assinatura, `procEmi` do S-2200),
aqui é o oposto: as verbas rescisórias usam **o mesmo complexType** `dmDev` já
modelado em `esocial_s1200.DmDev` — confirmado pela fonte ("inclui estabelecimentos
`infoPerApur`/`infoPerAnt` e detalhamento de rubricas", a mesma árvore
`InfoPerApur`/`IdeEstabLot`/`RemunPerApur`/`ItemRemuneracao`). `VerbasResc` importa
e reaproveita `esocial_s1200.DmDev` diretamente — testado explicitamente
(`test_valido_reaproveita_dm_dev_do_s1200`), não uma cópia parecida.

## Três eventos, três variações diferentes de `procEmi` — nenhuma suposta

| Evento | Tipo XSD | Domínio |
|---|---|---|
| S-1200 | `TS_procEmi` (dentro de `ideEvento` genérico) | 0-9 livre |
| S-2200 | `TS_procEmi_sem_8` | 0-9, exceto 8 |
| S-2299 | `TS_procEmi` | 0-9 livre |

Cada um lido na fonte, nenhum copiado do vizinho por suposição — o S-2299 volta a
usar o tipo genérico, então `8` é aceito de novo (testado:
`test_proc_emi_8_e_aceito_neste_evento`, o espelho do teste que rejeita `8` no
S-2200).

## `mtvDeslig`: Tabela 19, genuinamente não localizada

O motivo do desligamento é um código de 2 dígitos que referencia a "Tabela 19" do
eSocial. Confirmado que essa tabela **não** está embutida em nenhum dos XSDs
consultados (nem `evtDeslig.xsd`, nem `tipos.xsd`) — diferente das quatro tabelas de
incidência do S-1010, que estavam inteiras no schema. `mtv_deslig` é aceito só por
formato (2 dígitos numéricos).

Isso limita, por ora, qualquer ponte automática com
`folha/fgts.calcular_multa_rescisoria` — aquela função usa chaves semânticas
(`"sem_justa_causa"`, `"acordo"`, `"culpa_reciproca_ou_forca_maior"`, etc.), não os
códigos numéricos da Tabela 19. Uma função de tradução entre os dois exigiria a
tabela real, que não foi trazida para este projeto — registrado como gap, não
resolvido por adivinhação.

## `indGuia`: campo novo, domínio não localizado

Nenhum dos outros dois eventos do bloco (`S-1200`, `S-2200`) tem um campo
equivalente — relacionado à guia de recolhimento rescisório (GRRF/FGTS
rescisório), mas o simpleType `TS_indGuia` não foi encontrado nesta rodada. Aceito
como string opcional, sem validar contra domínio.

## O que fica de fora, deliberadamente

- **`pensAlim`/`percAliment`** (pensão alimentícia sobre a rescisão) — os tipos
  `TS_pensAlim`/`TS_percAliment` não foram localizados (a busca truncou antes de
  alcançá-los).
- **`procJudTrab`/`infoMV`/`procCS`** dentro de `verbasResc` — mesma decisão de
  excluir grupos raros já tomada em `esocial_s1200.IdeTrabalhador`.
- **Serialização XML/assinatura/envio** — mesmo padrão dos outros eventos.

## Arquivos

- `folha/esocial_s2299.py` — `IdeEvento`, `InfoDeslig`, `VerbasResc` (reaproveita
  `esocial_s1200.DmDev`); camada pura, sem Frappe, testável sem bench.

## Fontes

- `github.com/nfephp-org/sped-esocial`, `schemes/v_S_01_03_00/evtDeslig.xsd` e
  `tipos.xsd` — XSDs literais. Mesma família do `nfephp-org/sped-nfe` já usada para
  a NF-e, não a fonte primária oficial. Consultado em 2026-08-31.
