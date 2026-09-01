# CT-e: assinatura digital (`assinar_cte`)

Fecha mais uma pendência de `docs/cte-estado.md`. Diferente dos incrementos anteriores do CT-e,
este não escreveu nenhum código novo de assinatura — só confirmou que a NF-e e o CT-e usam o
mesmo perfil, e então **reaproveitou `fiscal/documento/assinatura.py` sem alteração nenhuma**.

## O que precisava ser confirmado, e por quê não bastava supor

`assinatura.py` já era genérico o bastante para qualquer documento (`referencia_do_id`,
`montar_signed_info`, `montar_signature` são parametrizados por `id_elemento`, nunca fixados em
`"NFe"`). O que faltava não era código — era confirmar que o **perfil** de assinatura do CT-e
(algoritmo de digest, algoritmo de assinatura, canonicalização) é o mesmo da NF-e. Supor isso só
porque os dois são "documentos fiscais eletrônicos brasileiros da mesma família" já se provou
errado uma vez neste projeto: o eSocial usa SHA-256, não SHA-1, apesar de estar na mesma família
(ver `docs/rh-esocial-assinatura.md`). Reusar `assinatura.py` sem verificar teria sido a mesma
aposta, com a mesma chance de estar errada.

## Como foi confirmado

Duas checagens independentes, nenhuma delas o texto do Ajuste SINIEF (não localizado — o PDF do
CONFAZ que o cita é a "Visão Geral" e não desce a esse nível de detalhe técnico; extração de
texto do PDF também esbarrou em fontes CID que não renderizam como texto simples):

1. **Formato do `Id`**: `cteTiposBasico_v4.00.xsd`, `infCte/@Id`, padrão `CTe[0-9]{44}` — mesma
   convenção `<prefixo><chave>` da NF-e (`NFe[0-9]{44}`), só troca o prefixo.
2. **Algoritmo de assinatura, corroborado por código de produção**: a classe `Signer` de
   `nfephp-org/sped-common` — a base compartilhada usada por `sped-nfe`, `sped-cte`, `sped-mdfe`
   e outros pacotes da mesma família de bibliotecas — tem `OPENSSL_ALGO_SHA1` como algoritmo
   padrão. `signCTe()` de `nfephp-org/sped-cte` chama esse `Signer::sign` **sem sobrescrever o
   algoritmo**. É uma fonte mais forte que a maioria das secundárias já usadas neste projeto —
   não é um blog resumindo a regra, é a implementação que assina CT-e de verdade em produção —
   mas ainda não é o texto oficial, e está declarado como tal na docstring do módulo.

## O que foi implementado

`fiscal/cte.py::assinar_cte(cte: dict, assinador: Assinador) -> dict` — mesma costura de
`fiscal/documento/nfe.py::assinar_nfe`: serializa a árvore, assina o `Id` de `infCte`, monta o
envelope `Signature` como irmão de `infCte` dentro de `CTe`. Não há função nova em
`assinatura.py`; `assinar_cte` só troca `NFe`/`infNFe` por `CTe`/`infCte` na costura.

5 testes (`test_cte.py`, classe `TestAssinarCte`): assina o `Id` certo, o `Id` usa o prefixo
`CTe` (não `NFe`), `Signature` é irmã de `infCte` (não filha — perfil enveloped), `infCte` não
muda ao ser assinado, o documento assinado serializa para XML válido.

## Arquivos

- `erpnext_brasil/fiscal/cte.py` — `assinar_cte`.
- `erpnext_brasil/tests/test_cte.py` — `AssinadorFalso`, `_cte_minimo`, `TestAssinarCte`.

## Fontes

- `github.com/nfephp-org/sped-cte`, `schemes/PL_CTe_400/cteTiposBasico_v4.00.xsd`, atributo
  `Id` de `infCte` (linha 4917 do arquivo baixado em 2026-08-31).
- `github.com/nfephp-org/sped-common`, `src/Signer.php` — algoritmo padrão `OPENSSL_ALGO_SHA1`.
- `github.com/nfephp-org/sped-cte`, `src/Common/Tools.php`, método `signCTe()` — chamada a
  `Signer::sign` sem sobrescrever o algoritmo padrão.
- `docs/rh-esocial-assinatura.md` — o precedente deste projeto que motivou não supor o perfil
  por analogia de família de documento.
