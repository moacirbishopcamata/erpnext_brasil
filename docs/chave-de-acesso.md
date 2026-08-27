# Chave de acesso da NF-e

Referência do layout, do cálculo do dígito verificador e da mudança trazida pelo CNPJ
alfanumérico. Implementado em `erpnext_brasil/fiscal/documento/chave_acesso.py`.

## A mudança que quebra código antigo

A chave de acesso **deixou de ser 44 dígitos**. O XSD oficial da NF-e
(`tiposBasico_v4.00.xsd`, tipo `TChNFe`, do Pacote de Liberação 010e_v1.02) define:

```
[0-9]{6}[0-9A-Z]{12}[0-9]{26}
```

Seis dígitos, **doze posições alfanuméricas**, vinte e seis dígitos — 44 no total. O
CNPJ alfanumérico, vigente desde julho de 2026, propaga para dentro da chave.

Consequência prática: qualquer validação escrita como `^\d{44}$` passa a **rejeitar chave
legítima**. Isso vale para regex em formulário, constraint de banco, máscara de campo e
integração com terceiros. A suíte tem um teste (`test_regex_antiga_rejeitaria_chave_legitima`)
que existe só para travar o retorno desse padrão.

Note o recorte: são **12** posições alfanuméricas, não 14. A raiz e a ordem do CNPJ
aceitam letra; os dois dígitos verificadores do CNPJ, dentro da chave, continuam
numéricos.

## Layout das 44 posições

| Campo    | Posições | Tam. | Conteúdo                                          |
|----------|----------|------|---------------------------------------------------|
| `cUF`    | 1–2      | 2    | Código da UF (IBGE)                               |
| `AAMM`   | 3–6      | 4    | Ano e mês da emissão                              |
| `CNPJ`   | 7–20     | 14   | CNPJ do emitente (12 alfanuméricas + 2 dígitos)   |
| `mod`    | 21–22    | 2    | Modelo: `55` (NF-e) ou `65` (NFC-e)               |
| `serie`  | 23–25    | 3    | Série                                             |
| `nNF`    | 26–34    | 9    | Número da nota                                    |
| `tpEmis` | 35       | 1    | Forma de emissão                                  |
| `cNF`    | 36–43    | 8    | Código numérico aleatório                         |
| `cDV`    | 44       | 1    | Dígito verificador                                |

## Cálculo do dígito verificador

Módulo 11 sobre as **43 primeiras** posições:

1. **Converter cada caractere**: `valor = ord(c) - 48`. Preserva `0`–`9` (48–57 → 0–9) e
   mapeia `A`–`Z` para 17–42. É a mesma conversão do CNPJ alfanumérico, e é o que torna
   o cálculo retrocompatível: chave puramente numérica bate pelo caminho de sempre.
2. **Aplicar pesos de 2 a 9**, ciclando **da direita para a esquerda**.
3. **Somar** os produtos e tirar o resto por 11.
4. **Resto menor que 2 → dígito 0**; caso contrário, `11 - resto`.

O passo 4 tem duas formulações equivalentes na literatura — a acima, e "`11 - resto`, e
se der 10 ou 11 use 0". As duas produzem o mesmo resultado; a primeira está no código por
ser a mesma redação usada no cálculo do CNPJ, o que evita duas regras parecidas e
diferentes no mesmo repositório.

### Vetores de verificação

Ambos reproduzidos pela implementação e travados em teste.

**CNPJ numérico** — `cUF` 35, `AAMM` 2606, CNPJ `11222333000181`, `mod` 55, `serie` 001,
`nNF` 000000001, `tpEmis` 1, `cNF` 00000001:

```
base (43): 3526061122233300018155001000000001100000001
soma 342 → 342 % 11 = 1 → menor que 2 → cDV = 0
```

**CNPJ alfanumérico** — mesmo cenário com CNPJ `AB000000000001` e `AAMM` 2607
(`A` = 17, `B` = 18):

```
base (43): 352607AB00000000000155001000000001100000001
soma 421 → 421 % 11 = 3 → cDV = 11 - 3 = 8
chave:     352607AB000000000001550010000000011000000018
```

## Armadilhas conhecidas

**Zero à esquerda.** Série, número e código numérico perdem o zero à esquerda ao passar
por planilha, JSON ou coluna numérica de banco. `montar_chave` normaliza cada campo para
o tamanho do layout, e é a causa mais comum de chave inválida que não vem de erro de
cálculo.

**Minúsculas.** O padrão admite exclusivamente letras maiúsculas. A entrada é normalizada
na leitura, mas um sistema externo que envie minúscula terá a chave recusada pela SEFAZ.

**Base de comprimento errado.** Calcular o dígito sobre algo que não tem 43 posições
devolveria um valor plausível e errado, que só apareceria na rejeição. `calcular_dv`
verifica o comprimento e falha alto — é pré-condição, não cortesia.

**`cNF` não pode repetir `nNF`.** Regra de validação da SEFAZ que não está no formato da
chave e por isso não é verificada aqui; pertence à montagem do documento.

## Fontes

- `tiposBasico_v4.00.xsd`, tipo `TChNFe` — Pacote de Liberação 010e_v1.02, Portal
  Nacional da NF-e (baixado e conferido).
- NT 2026.004 — CNPJ alfanumérico nos documentos fiscais eletrônicos.
- IN RFB 2.229/2024 — instituição do CNPJ alfanumérico.
