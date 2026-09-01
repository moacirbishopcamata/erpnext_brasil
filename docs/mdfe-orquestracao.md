# MDF-e: orquestração (`montar_ide`/`montar_mdfe`)

Fecha o orquestrador do MDF-e — o mesmo papel que `fiscal/cte.py::montar_ide`/`montar_cte`
cumprem para o CT-e. Diferente do CT-e, aqui a lição do `cDV` (ver
`docs/cte-orquestracao.md`) foi aplicada **desde o início**, não corrigida depois.

## `ide` inteiro, 21 campos, verificado campo a campo

Lido e ordenado por leitura direta do XSD (`mdfeTiposBasico_v3.00.xsd`, linhas 17–232, ver
`docs/mdfe-estado.md`) — não por analogia com o CT-e. Cinco enumerações confirmadas e validadas:

- `tpEmit` (`1`/`2`/`3`: prestador de serviço/transportador de carga própria/prestador que
  emitirá CT-e Globalizado).
- `tpTransp` (`1`/`2`/`3`: ETC/TAC/CTC — opcional).
- `modal` (`1`–`4`: rodoviário/aéreo/aquaviário/ferroviário — **sem zero à esquerda, sem
  Dutoviário nem Multimodal**, diferente do `modal` do CT-e).
- `tpEmis` (`1`/`2`/`3`).
- `procEmi` (`0`/`4` — **diferente do `0`/`3` do CT-e**).

Testado explicitamente que reaproveitar valores do CT-e no MDF-e falha
(`test_modal_do_cte_e_invalido_aqui`: `"01"` é válido no CT-e, inválido aqui).

## `cDV` correto desde o início — a lição do CT-e aplicada, não repetida

`montar_ide` já nasce recebendo `chave` como parâmetro obrigatório, extraindo `cDV` via
`ler_chave` (nunca `chave[-1]` cru) e validando como pré-condição que a chave é de MDF-e
(`modelo == "58"`). Mesma disciplina de Design by Contract que o CT-e só ganhou depois de um
bug passar despercebido — aqui não houve o mesmo tropeço, exatamente porque a lição já estava
registrada em `docs/cte-orquestracao.md` antes de este módulo ser escrito.

## Sem `CFOP`/`natOp` — confirmado, não só citado

`test_campos_basicos` verifica explicitamente que `CFOP` e `natOp` **não** aparecem no `ide` do
MDF-e — não é omissão por falta de implementação, é ausência confirmada no XSD (o MDF-e não é
uma operação tributável, é um manifesto que agrupa documentos já tributados).

## Prova de ponta a ponta

`test_serializa_e_pode_ser_assinado`: `montar_ide` → `montar_mdfe` → `para_xml` → `assinar_mdfe`,
mesma prova já feita para o CT-e (`docs/cte-orquestracao.md`).

## O que ficou de fora

- `emit`, `infModal` (referência ao modal — `fiscal/mdfe_rodoviario.py` monta o conteúdo, mas
  `montar_ide` não injeta automaticamente em `infModal`; isso é responsabilidade de um
  orquestrador de nível mais alto, ainda não escrito, que junte `ide` + `emit` + `infModal` +
  `infDoc` num `infMDFe` completo).
- `seg`, `prodPred`, `tot`, `lacres` — vistos na listagem de `infMDFe`, não implementados.

## Arquivos

- `erpnext_brasil/fiscal/mdfe.py` — `IdentificacaoMdfe`, `MunicipioCarrega`, `montar_ide`,
  `montar_mdfe`, `MdfeInvalido`, mais as constantes `EMITENTE_*`, `TRANSPORTADOR_*`, `MODAL_*`,
  `PROCESSO_EMISSAO_*`, `AMBIENTE_*`.
- `erpnext_brasil/tests/test_mdfe.py` — `TestIdentificacaoMdfeValidar`, `TestMontarIde`,
  `TestMontarMdfe` (18 testes).

## Fontes

- `github.com/nfephp-org/sped-mdfe`, `schemes/PL_MDFe_300b/mdfeTiposBasico_v3.00.xsd`, grupo
  `ide` completo (linhas 17–232 do arquivo baixado em 2026-08-31). Ver `docs/mdfe-estado.md`
  para o histórico da investigação.
