# eSocial: geração do `Id` de 36 caracteres do evento

Resolve o último gap de formato citado desde `docs/rh-esocial-s1200.md` — o
atributo `Id` de cada evento, até agora sempre recebido pronto de quem chama.

## A composição, confirmada por duas fontes e um exemplo literal

```
ID T NNNNNNNNNNNNNN AAAAMMDD HHMMSS QQQQQ
```

| Parte | Tamanho | Conteúdo |
|---|---|---|
| `ID` | 2 | texto fixo |
| `T` | 1 | tipo de inscrição do empregador — `1` = CNPJ, `2` = CPF |
| `N` | 14 | CNPJ/CPF do empregador, completado com zeros **à direita** |
| `AAAAMMDD` | 8 | data de geração |
| `HHMMSS` | 6 | hora de geração |
| `Q` | 5 | sequencial (só incrementa em eventos gerados no mesmo segundo) |

Total: 2+1+14+8+6+5 = 36. Um exemplo literal encontrado
(`ID2333901700001892014020213424700001`) confirma a aritmética das posições —
fatiado byte a byte, cada parte cai exatamente onde a tabela acima diz. **Não** foi
usado para confirmar o domínio do dígito `T`: nesse exemplo específico, `T=2`
(CPF) mas o número que segue tem 14 dígitos com formato de CNPJ, não CPF —
inconsistência da própria fonte terceira, não incorporada. O domínio `1=CNPJ/2=CPF`
foi confirmado por uma segunda fonte independente, sem esse exemplo.

## Zeros à direita, não à esquerda — e por quê

Contraintuitivo para quem espera zero-padding numérico convencional (à esquerda).
Faz sentido aqui: CNPJ já tem 14 dígitos (nunca precisa de padding); CPF tem 11,
precisa de 3 a mais. Preenchendo à esquerda, um CPF `12345678901` viraria
`00012345678901` — os zeros de padding ficam indistinguíveis de zeros que fizessem
parte do número real. À direita (`12345678901000`), o número original continua
legível no início da string, e a diferença entre padding e número real é óbvia.

## O que fica de fora, deliberadamente

- **Persistência do sequencial** entre chamadas no mesmo segundo — `gerar_id_evento`
  só formata o `Q` recebido; decidir quando dois eventos realmente colidem no mesmo
  segundo (e portanto precisam de sequenciais diferentes) exige visibilidade de
  todos os eventos sendo gerados numa janela de tempo, que este módulo isolado não
  tem.
- **CNPJ representado só pela raiz** (8 posições, caso especial de algumas
  classificações de contribuinte no cadastro do S-1000) — este módulo sempre espera
  o número completo (11 ou 14 dígitos) antes de completar à direita.
- **Dígito verificador de CNPJ/CPF** — não validado aqui, mesma separação de
  responsabilidade já usada em todo o bloco eSocial (`fiscal/validators` valida na
  gravação do cadastro, não é revalidado ao montar cada evento).

## Prova: só o sequencial muda entre dois eventos no mesmo instante

Um teste gera dois `Id` com o mesmo `momento`/`tp_insc`/`nr_insc`, sequenciais `1` e
`2` — confirma que os primeiros 31 caracteres são idênticos e só os últimos 5
(`Q`) divergem, exatamente o comportamento que "só incrementa quando há colisão de
segundo" implica.

## Arquivos

- `folha/esocial_id.py` — `gerar_id_evento`, `TIPO_INSCRICAO_CNPJ`/`_CPF`; camada
  pura, sem Frappe, testável sem bench.

## Fontes

- Busca agregada (Central de Atendimento Tecnospeed, LONDRISOFT) — duas fontes
  concordantes na composição de posições; o exemplo literal (LONDRISOFT) usado só
  para confirmar a aritmética, não o dígito `T` (inconsistência registrada acima,
  não incorporada). Nenhuma fonte oficial `gov.br/esocial` lida diretamente para
  este campo específico nesta rodada. Consultado em 2026-08-31.
