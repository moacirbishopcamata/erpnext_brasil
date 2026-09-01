# CT-e: orquestração (`montar_ide`/`montar_cte`)

Fecha o item que faltava depois de `docs/cte-toma.md`: um orquestrador que amarre as peças de
conteúdo do CT-e (CFOP, `ICMSUFFim`, `infNFe`, modal rodoviário, tomador) num único documento —
o mesmo papel que `fiscal/documento/nfe.py::montar_ide`/`montar_nfe` cumprem para a NF-e.

## `ide` inteiro, verificado campo a campo

Os 30 campos de `ide` foram lidos e ordenados por leitura direta do XSD
(`cteTiposBasico_v4.00.xsd`, linhas 2700–3145), não por analogia com a NF-e — o `ide` do CT-e tem
campos que a NF-e não tem (`modal`, `tpServ`, município de início/fim da prestação, `retira`) e
não tem alguns que a NF-e tem (`cMunFG` vira `cMunEnv` — o município do emitente, não da
operação; sem `idDest`/`tpNF`). Quatro enumerações confirmadas e validadas:

- `modal` (`01`–`06`: rodoviário/aéreo/aquaviário/ferroviário/dutoviário/multimodal).
- `tpServ` (`0`–`4`: normal/subcontratação/redespacho/redespacho intermediário/vinculado a
  multimodal).
- `tpCTe` (`0`/`1`/`3`: normal/complemento de valores/substituição — **não existe `2`** nesta
  tabela; CT-e de Anulação de Valores é modelado de outro jeito, fora do escopo verificado aqui).
- `retira` (`0`/`1`: sim/não — indicador se o recebedor retira no destino).
- `indIEToma` (`1`/`2`/`9`: contribuinte/isento/não contribuinte — mesma enumeração de
  `nfe.Destinatario.indicador_ie`).

## Composição, não acoplamento

`montar_ide` recebe o grupo do tomador (`toma3`/`toma4`) **já pronto** de `montar_toma3`/
`montar_toma4` — não sabe montá-lo, só onde ele entra na sequência (depois de `indIEToma`).
Mesmo espírito de `montar_infnfe` receber chaves já montadas: cada função monta só o que o XSD
diz que ela monta, e a composição acontece na chamada, não dentro da implementação.

## O que ficou de fora, deliberadamente

- **Contingência** (`dhCont`/`xJust`) — a NF-e só preenche esses campos quando `tipo_emissao !=
  "1"`, com uma regra de posição própria (`docs/rh-esocial-...` não se aplica aqui, mas o
  princípio de "campo condicional só aparece quando a condição é real" é o mesmo). Não
  implementado ainda — o CT-e "normal" (emissão sem contingência) é o caso coberto.
- `indGlobalizado` só aparece quando `globalizado=True` — CT-e Globalizado é um regime especial
  (frete internacional consolidado) fora do escopo verificado até agora; o campo existe na
  dataclass mas nada mais foi investigado sobre ele.

## Prova de ponta a ponta

`test_serializa_e_pode_ser_assinado`: `montar_ide` → `montar_cte` → `para_xml` → `assinar_cte`,
numa cadeia só — prova que as peças que foram implementadas em incrementos separados (CFOP,
tomador, assinatura) realmente se encaixam, não só que cada uma funciona isolada. Mesma
disciplina de teste de integração citada nas preferências de engenharia deste projeto: "testa a
costura, não só o componente".

## Arquivos

- `erpnext_brasil/fiscal/cte.py` — `IdentificacaoCte`, `montar_ide`, `montar_cte`, mais as
  constantes `MODAL_*`, `TIPO_SERVICO_*`, `TIPO_CTE_*`, `RETIRA_*`, `NAMESPACE_CTE`.
- `erpnext_brasil/tests/test_cte.py` — `TestIdentificacaoCteValidar`, `TestMontarIde`,
  `TestMontarCte` (16 testes).

## Fontes

- `github.com/nfephp-org/sped-cte`, `schemes/PL_CTe_400/cteTiposBasico_v4.00.xsd`, grupo `ide`
  completo (linhas 2700–3145 do arquivo baixado em 2026-08-31). Ver `docs/cte-estado.md` para o
  histórico da investigação.
