# O algoritmo de busca do Frappe

Levantado a pedido do usuário ("o Frappe usa algoritmo Jaro-Winkler para pesquisas
fuzzy?" e, em seguida, "documente o algoritmo de pesquisa usado pelo Frappe"). **Lido
direto no código-fonte** do Frappe instalado no bench, não de memória nem de
documentação de terceiro — `frappe/search/sqlite_search.py`.

## Resposta curta: não é Jaro-Winkler

Não há nenhuma ocorrência de `jaro`, `winkler` ou `levenshtein` no código do Frappe. A
busca aproximada combina **trigramas + Jaccard + Ratcliff-Obershelp**.

## São dois mecanismos diferentes, e confundi-los leva a expectativa errada

| Mecanismo | Onde aparece | Como funciona |
|---|---|---|
| **Busca de link** (`search_link`) | Campos Link, autocompletar de Cliente/Item/Conta | `LIKE` no banco — **sem** aproximação nenhuma |
| **Busca global** (`sqlite_search`) | A busca do topo do Desk, sobre um índice SQLite | Índice de texto + o algoritmo descrito abaixo |

Ou seja: digitar "Camatta" num campo de Cliente **não** encontra "Camata". Só a busca
global tem tolerância a erro de digitação.

## O algoritmo da busca global, etapa a etapa

### 1. Trigramas com padding

```python
def _generate_trigrams(self, word):
    word = f"  {word.lower()}  "  # Add padding
    return [word[i : i + 3] for i in range(len(word) - 2)]
```

A palavra é minúscula e recebe dois espaços de cada lado antes de ser quebrada em
trincas. O padding não é detalhe: ele faz o **começo e o fim** da palavra virarem
trigramas próprios (`"  c"`, `"ca "`), de modo que uma diferença na borda pesa tanto
quanto uma no meio.

### 2. Candidatos vindos do índice

Uma consulta SQL busca palavras que compartilhem **ao menos um trigrama**, já filtrando
por diferença de comprimento (`ABS(v.length - ?) <= MAX_EDIT_DISTANCE`) e ordenando por
trigramas em comum e frequência. É o filtro barato que evita comparar o termo com o
vocabulário inteiro.

### 3. Similaridade de Jaccard sobre os trigramas

```python
intersection = len(word_trigram_set & candidate_trigrams)
union = len(word_trigram_set | candidate_trigrams)
trigram_similarity = intersection / union if union > 0 else 0

if trigram_similarity < 0.3:
    continue
```

Interseção dividida pela união dos conjuntos de trigramas, com corte em **0,3**.
Candidato abaixo disso nem chega à etapa seguinte.

### 4. Similaridade de sequência (Ratcliff-Obershelp)

```python
seq_similarity = difflib.SequenceMatcher(None, word, candidate_word).ratio()
```

`difflib.SequenceMatcher` é da biblioteca padrão do Python e implementa
Ratcliff-Obershelp (maior subsequência comum, aplicada recursivamente às sobras). Roda
**só nos candidatos promissores** — o comentário do próprio código diz "only for
promising candidates", porque é a parte cara.

### 5. Nota final, com peso e bônus de frequência

```python
combined_similarity = (
    trigram_similarity * SIMILARITY_TRIGRAM_WEIGHT
    + seq_similarity * SIMILARITY_SEQUENCE_WEIGHT
)
frequency_boost = min(MAX_FREQUENCY_BOOST, 1.0 + (freq / FREQUENCY_BOOST_FACTOR))
final_score = combined_similarity * frequency_boost
```

Média ponderada das duas similaridades, multiplicada por um bônus pequeno e **limitado**
para palavras frequentes — o teto existe para que frequência desempate, não domine.

## Por que a diferença para Jaro-Winkler importa

O Jaro-Winkler dá **peso extra ao prefixo comum**: foi desenhado para nomes próprios em
registros civis, onde o erro tende a estar no fim ("Camata" × "Camatta"). A abordagem do
Frappe é neutra quanto à posição do erro, e o padding dos trigramas até reforça essa
neutralidade.

Consequência prática para este projeto: se em algum momento houver busca aproximada de
**razão social** ou de **descrição de produto para achar NCM**, vale saber que:

- para termos longos e com palavras trocadas de ordem, a abordagem por trigramas se sai
  bem;
- para erro de digitação no fim de nomes curtos, o Jaro-Winkler seria melhor — e
  precisaria ser implementado, porque o Frappe não o traz.

Nenhuma das duas situações apareceu ainda no `erpnext_brasil`: as buscas que o app faz
hoje são por chave exata (código de município IBGE, NCM, CFOP, código de ajuste), onde
aproximação seria indesejável — achar "quase" o CFOP certo é pior que não achar nada.

## Fonte

`frappe/search/sqlite_search.py` (funções `_generate_trigrams` e o cálculo de
similaridade), lido no clone do bench WSL2 em 2026-09-03. Os trechos acima são citações
literais do arquivo.
