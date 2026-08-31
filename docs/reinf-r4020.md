# EFD-Reinf R-4020: Pagamentos a Pessoa Jurídica com retenção

Primeira fatia do EFD-Reinf modelada neste projeto — item citado como fora de
escopo desde as primeiras sessões.

## Irmão do eSocial, mas juridicamente separado

EFD-Reinf compartilha a infraestrutura conceitual do eSocial (leiaute XML,
`ideEvento` no mesmo espírito, ambiente de produção restrita) mas é um sistema
diferente. Os eventos série R-4000 substituem a DIRF e escrituram as quatro
retenções federais que incidem juntas sobre pagamento a PJ — IRRF, CSLL, Cofins e
PIS-Pasep, o "combo" da IN RFB 1.234/2012. Cobre o lado do **pagador** (retentor),
diferente do S-1200/eSocial (lado do empregador sobre o próprio trabalhador).

## Achado real: valores monetários são string com vírgula no XSD

O XSD declara `vlrBruto`/`vlrBaseIR`/`vlrIR`/etc. como `xs:string` com padrão
`[0-9]{1,12},[0-9]{2}` — vírgula decimal, não `xs:decimal`. Este módulo usa
`Decimal` internamente, seguindo a convenção do projeto ("dinheiro é `Decimal`") —
a conversão para o formato string com vírgula fica para quando a serialização XML
deste evento existir (mesmo estágio em que `esocial_s1200.py` começou, antes de
`esocial_serializacao.py`).

## `ideEvento` parecido com o do eSocial — mas `procEmi` é um domínio diferente

Mesmos nomes de campo do bloco eSocial (`indRetif`, `nrRecibo`, `perApur`,
`tpAmb`, `procEmi`, `verProc`), mesma ausência de `indApuracao` que S-2200/S-2299
já tinham. Mas `procEmi` aqui é `unsignedByte (1|2)` — um domínio de **dois**
valores, diferente de qualquer `procEmi` já confirmado no bloco eSocial (livre
0-9 no S-1200/S-2299, livre-exceto-8 no S-2200). Mais uma variação real, não
suposta — testada explicitamente (`test_proc_emi_so_aceita_1_ou_2`).

## O que fica de fora, deliberadamente

- **`natRend`** (natureza do rendimento, 5 dígitos) — tabela nacional da RFB, não
  trazida para este projeto (mesma disciplina de `COD_CONT` do EFD-Contribuições,
  `codCateg` do eSocial).
- **`infoProcRet`/`infoProcJud`/`infoPgtoExt`** — processos que suspendem
  retenção, pagamento a residente no exterior — grupos raros, mesma decisão de
  excluir `procJudTrab` já tomada no bloco eSocial.
- **`indFciScp`/`nrInscFciScp`/`percSCP`** (Sociedade em Conta de Participação) —
  regime societário raro.
- **Serialização XML/assinatura/envio** — mesmo padrão do eSocial: só o agregado
  de negócio nesta fatia.
- **O terceiro valor de `tpInscEstab`** (`1|2|3`, provavelmente CNPJ/CPF/CNO) —
  aceito por formato, significado do valor `3` não confirmado.

## Arquivos

- `contabil/reinf_r4020.py` — `IdeEvento`, `IdeContri`, `IdeEstab`, `Retencoes`,
  `InfoPgto`; camada pura, sem Frappe, testável sem bench.

## Fontes

- `github.com/nfephp-org/sped-efdreinf`,
  `schemes/v2_01_02/R-4020-evt4020PagtoBeneficiarioPJ-v2_01_02_B.xsd` — XSD
  literal. Mesma família de projeto open-source já usada para eSocial e NF-e neste
  projeto, não a fonte primária oficial (`sped.rfb.gov.br`). Consultado em
  2026-08-31.
