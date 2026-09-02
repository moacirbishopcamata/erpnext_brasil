# MDF-e: orquestrador de nível mais alto (`montar_infmodal`/`montar_infmdfe`)

Fecha a última peça que faltava: até este incremento, cada grupo de `infMDFe` (`ide`, `emit`,
`infDoc`, `seg`, `prodPred`, `tot`, `lacres`) era montado separadamente — nada os compunha num
único `infMDFe` pronto para `montar_mdfe`/`assinar_mdfe`.

## Achado sobre `infModal`: é um ponto de extensão, não um grupo fixo

Confirmado por leitura direta do XSD (linhas 294–325): `infModal` é um `xs:any` — o schema não
descreve o conteúdo do modal, delega a um dos quatro arquivos `mdfeModal*_v3.00.xsd`. O único
campo que o próprio `infModal` define é o atributo `versaoModal` (padrão `"3.NN"`, ex.
`"3.00"`), obrigatório. Isso significa que `montar_infmodal` **não sabe montar nenhum modal
específico** — só recebe o conteúdo já pronto (`{"rodo": montar_rodo(...)}` de
`fiscal.mdfe_rodoviario`, único modal implementado até agora) e anexa a versão.

## Composição, não conhecimento de como montar cada peça

`montar_infmdfe` recebe todos os grupos já montados e só sabe a **ordem** em que entram —
`ide`, `emit`, `infModal`, `infDoc`, `seg`, `prodPred`, `tot`, `lacres` (confirmada contra o XSD,
testada explicitamente com `list(infmdfe.keys())`). `seg`/`prod_pred`/`lacres` são opcionais no
XSD; passar `None` os omite do documento sem grupo vazio. Mesmo espírito de `fiscal.cte.
montar_ide` receber o tomador já pronto — cada função monta só o que o XSD diz que ela monta.

## Prova de ponta a ponta completa

`test_serializa_e_pode_ser_assinado`: `montar_ide` + `montar_emit` + `montar_infmodal` (com
`montar_rodo` de `fiscal.mdfe_rodoviario`) + `montar_infdoc` + `montar_tot` → `montar_infmdfe` →
`montar_mdfe` → `assinar_mdfe`, numa cadeia só — a mesma prova que o CT-e já tinha
(`docs/cte-orquestracao.md`), agora cobrindo o conjunto completo de peças do MDF-e, não só
`ide`.

## Arquivos

- `erpnext_brasil/fiscal/mdfe.py` — `montar_infmodal`, `montar_infmdfe`.
- `erpnext_brasil/tests/test_mdfe.py` — `TestMontarInfmodal`, `TestMontarInfmdfe` (7 testes).

## Fontes

- `github.com/nfephp-org/sped-mdfe`, `schemes/PL_MDFe_300b/mdfeTiposBasico_v3.00.xsd`, grupo
  `infModal` (linhas 294–325 do arquivo baixado em 2026-08-31). Ver `docs/mdfe-estado.md` para o
  histórico da investigação.
