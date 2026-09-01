# MDF-e: assinatura digital (`assinar_mdfe`)

Terceiro código do MDF-e. Mesmo padrão de `docs/cte-assinatura.md`: nenhum código novo de
assinatura foi escrito — só confirmado que MDF-e usa o mesmo perfil de NF-e/CT-e, e então
`fiscal/documento/assinatura.py` foi reaproveitado sem alteração.

## Por que verificar de novo, mesmo já tendo verificado para o CT-e

Documentos "da mesma família" já divergiram nesta mesma investigação: `modal` do MDF-e
(`"1"`–`"4"`) não é o `modal` do CT-e (`"01"`–`"06"`), e `procEmi` também diverge (ver
`docs/mdfe-estado.md`). Presumir que a assinatura seguiria o mesmo perfil só por ser "da mesma
família" seria repetir a aposta que já se provou às vezes certa (CT-e) e às vezes errada
(eSocial usa SHA-256, não SHA-1) — teria que ser verificada de qualquer jeito.

## Como foi confirmado

- **Formato do `Id`**: `mdfeTiposBasico_v3.00.xsd`, `infMDFe/@Id`, padrão `MDFe[0-9]{44}`
  (linha 1230) — mesma convenção `<prefixo><chave>` da NF-e/CT-e.
- **Algoritmo, por código de produção**: `signMDFe()` de `nfephp-org/sped-mdfe`
  (`src/Common/Tools.php`) chama `Signer::sign` com `$this->algorithm`, cujo valor padrão
  declarado na própria classe é `OPENSSL_ALGO_SHA1` — o mesmo algoritmo já confirmado para o
  CT-e. Ainda não é o texto do Ajuste SINIEF 21/2010 (não localizado), mas é código que assina
  MDF-e de verdade em produção — mesmo nível de corroboração aceito para o CT-e.

## O que foi implementado

`fiscal/mdfe.py::assinar_mdfe(mdfe: dict, assinador: Assinador) -> dict` — mesma costura de
`fiscal/cte.py::assinar_cte`/`fiscal/documento/nfe.py::assinar_nfe`: serializa, assina o `Id` de
`infMDFe`, monta `Signature` como irmã de `infMDFe` dentro de `MDFe`. `NAMESPACE_MDFE`
(`http://www.portalfiscal.inf.br/mdfe`) também adicionado, para quando o orquestrador
`montar_mdfe` for implementado.

5 testes (`test_mdfe.py`, `TestAssinarMdfe`): assina o `Id` certo, o `Id` usa o prefixo `MDFe`
(nem `CTe` nem `NFe`), `Signature` é irmã de `infMDFe`, `infMDFe` não muda ao ser assinado, o
documento serializa.

## Arquivos

- `erpnext_brasil/fiscal/mdfe.py` — `assinar_mdfe`, `NAMESPACE_MDFE`.
- `erpnext_brasil/tests/test_mdfe.py` — `AssinadorFalso`, `_mdfe_minimo`, `TestAssinarMdfe`.

## Fontes

- `github.com/nfephp-org/sped-mdfe`, `schemes/PL_MDFe_300b/mdfeTiposBasico_v3.00.xsd`, atributo
  `Id` de `infMDFe` (linha 1230 do arquivo baixado em 2026-08-31).
- `github.com/nfephp-org/sped-mdfe`, `src/Common/Tools.php`, método `signMDFe()` e declaração
  `protected $algorithm = OPENSSL_ALGO_SHA1`.
