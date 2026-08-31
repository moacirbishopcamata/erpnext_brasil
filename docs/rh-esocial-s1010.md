# eSocial S-1010: Tabela de Rubricas

A peça que faltava para o S-1200 funcionar de verdade. Todo módulo do bloco S-1200
(`docs/rh-esocial-s1200.md`, `docs/rh-esocial-lote.md`) recebeu `cod_rubr`/
`ide_tab_rubr` como dado pronto de quem chama, documentando que "a tabela de
rubricas (evento S-1010) é configuração do empregador, este projeto não a modela".
Isto modela a estrutura do **evento** que cria essa configuração — não muda a
decisão de que os códigos em si continuam vindo de fora; só a forma do evento que os
cadastra agora está verificada e testada.

## Estrutura: `ideRubrica` + `dadosRubrica`

`ideRubrica` identifica a rubrica (`codRubr`/`ideTabRubr` — os mesmos valores que
`esocial_s1200.ItemRemuneracao` espera receber — mais vigência `iniValid`/
`fimValid`). `dadosRubrica` define o que ela é: descrição, natureza, tipo
(vencimento/desconto/informativa/informativa dedutora), e como incide sobre
INSS/IRRF/FGTS/PIS-PASEP.

## Quatro tabelas de domínio confirmadas, uma sem enumeração

| Código | Valores | Enumerado no XSD? |
|---|---|---|
| `codIncCP` | 24 valores (`00, 01, 11-16, 21, 22, 25, 26, 31, 32, 34, 35, 51, 91-98`) | Sim |
| `codIncFGTS` | 8 valores (`00, 11, 12, 21, 31, 91, 92, 93`) | Sim |
| `codIncCPRP` | 7 valores (`00, 11, 12, 31, 32, 91, 92`) | Sim |
| `codIncPisPasep` | 5 valores (`00, 11, 12, 91, 92`) | Sim |
| `codIncIRRF` | inteiro de 1 a 4 dígitos | **Não** — livre no XSD |

As quatro tabelas com enumeração vieram direto do XSD (`evtTabRubrica.xsd`), não
foram inventadas — `DadosRubrica` rejeita qualquer código fora delas.
`codIncIRRF` é aceito como qualquer inteiro de 1 a 4 dígitos, sem validar contra um
domínio (porque o XSD não declara um).

## O mesmo `codIncFGTS` de dois ângulos

`docs/rh-esocial-s1200.md` já tinha citado uma regra de validação do S-1200
("rubrica com `codIncFGTS` em `[21, 93]` só pode ser usada em eventos de
rescisão") — é a mesma tabela nacional modelada aqui, vista do lado do cadastro
(S-1010) em vez do lado do uso (S-1200). As duas fontes concordam sem terem sido
lidas juntas — reforça a confiabilidade da tabela.

## O que fica de fora, deliberadamente

- **`ideProcessoCP`/`ideProcessoIRRF`/`ideProcessoFGTS`/`ideProcessoPisPasep`** —
  processos judiciais que suspendem a incidência de uma rubrica sobre um tributo
  específico, cada um com sua própria tabela de `codSusp` — mesma decisão de
  excluir `procJudTrab` do S-1200: grupo raro, tabela de domínio própria não trazida
  para este projeto.
- **`novaValidade`** — variante rara do fluxo de alteração de uma rubrica.
- **`natRubr`** ("natureza da rubrica") — aceito como string não vazia, sem validar
  contra a Tabela 3 do eSocial (centenas de códigos mantidos pela RFB).
- **Operação `exclusao`** como função dedicada — `IdeRubrica` sozinho já serve para
  montá-la (o XSD dispensa `dadosRubrica` nesse caso), mas não há um
  `montar_exclusao_rubrica` separado.
- **Serialização XML/assinatura/envio** — mesmo padrão do S-1200: modelado aqui só
  o agregado de negócio, não a árvore XML completa nem o transporte.

## Arquivos

- `folha/esocial_s1010.py` — `IdeRubrica`, `DadosRubrica`, as quatro tabelas de
  incidência; camada pura, sem Frappe, testável sem bench.

## Fontes

- `github.com/nfephp-org/sped-esocial`, `schemes/v_S_01_03_00/evtTabRubrica.xsd` —
  XSD literal do evento, incluindo as quatro enumerações de código de incidência.
  Mesma família do `nfephp-org/sped-nfe` já usada para a NF-e, não a fonte primária
  oficial. Consultado em 2026-08-31.
