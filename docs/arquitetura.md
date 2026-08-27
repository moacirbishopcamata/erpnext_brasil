# Arquitetura

## As duas camadas

```
erpnext_brasil/
  fiscal/       regra fiscal pura — NUNCA importa frappe
    validators.py          CPF, CNPJ (inclusive alfanumérico)
    inscricao_estadual.py  as 27 UFs
    ufs.py                 resolução de UF a partir de texto livre
    impostos/              ICMS, IPI, PIS/COFINS, IBS/CBS, retenções, apuração
    documento/             chave de acesso, grupos do XML, ciclo de vida, porta
    codigos/               tabelas normativas, leitor XLSX, compatibilidade
  integracao/   camada fina — conhece frappe, não contém regra
  setup/        campos customizados e instalação
  tests/        suíte que roda sem bench, sem site e sem banco
```

A dependência aponta em **uma direção só**: `integracao/` conhece `fiscal/`, nunca o
inverso.

## Por que a camada pura existe

Um app Frappe normalmente exige bench, site e banco para rodar qualquer teste. Isso torna
a suíte lenta, frágil e impossível de executar numa máquina de desenvolvimento sem
infraestrutura montada — e, na prática, faz com que ninguém a rode.

Aqui a regra fiscal é composta de funções puras e `dataclass`. A suíte inteira roda com:

```sh
python -m unittest discover -s erpnext_brasil/tests -t .
```

Em menos de um segundo, sem instalar nada.

Isso não é conveniência: é o que permite verificar cálculo de imposto **contra a fonte
normativa** — comparar 3.000 CNPJs com a implementação de referência da Receita, validar
os 96 pares de cClassTrib da tabela oficial — sem montar um ambiente.

## A regra é executável, não aspiracional

`tests/test_arquitetura.py` percorre a árvore de imports com `ast` e falha se:

- um módulo de `fiscal/` importar `frappe`;
- `fiscal/` depender de `integracao/` (dependência invertida);
- um arquivo de teste importar `frappe` (a suíte deixaria de rodar em qualquer máquina);
- um módulo de integração crescer além do limite — sinal de regra migrando para o lugar
  errado.

O arquivo nasceu depois de uma auditoria encontrar **três módulos com `import frappe`
dentro de `fiscal/`**. A camada que o README chamava de pura não era pura. Regra de
arquitetura escrita só em prosa é aspiracional; escrita como teste, é fato.

## Inversão de dependência

A validação de classificação precisa das tabelas oficiais, mas não precisa saber que elas
vieram de um Code List do Frappe. Ela depende de `RepositorioClassificacao`, um `Protocol`
de duas operações:

```python
def cst(self) -> dict[str, CstIbsCbs]: ...
def classificacoes(self) -> dict[str, ClassificacaoTributaria]: ...
```

Duas implementações: `RepositorioEmMemoria` (testes e importação) e `RepositorioFrappe`
(produção). Trocar a origem dos códigos não toca na regra, e a orquestração de um
documento inteiro se testa com um duplo de poucas linhas.

O mesmo padrão aparece em `TransporteFiscal`, a porta de transmissão — três operações,
não as 221 que uma API de documentos fiscais expõe. Interface pequena é adaptador fácil
de escrever e de substituir.

## Resiliência: degradar ou falhar alto

A distinção é deliberada, e em software fiscal ela importa mais que em outros domínios.

**Degrada** onde a ausência é estado normal do sistema:

| Situação | Comportamento |
|---|---|
| Tabela de códigos não importada | Não acusa erro — sem ela não há como afirmar invalidez |
| Metadado JSON ilegível | Vira dicionário vazio; a validação deixa de conferir *aquele* aspecto |
| UF indeterminável do texto livre | Deixa passar em vez de travar um cadastro legítimo |
| Item sem classificação fiscal | Não impede salvar rascunho |
| Tributo sem conta configurada | Omite a linha em vez de lançar em conta genérica |

**Falha alto** onde o silêncio produziria dado errado:

| Situação | Comportamento |
|---|---|
| Autorização sem protocolo | `ValueError` — é a prova da autorização |
| Alíquota como percentual (`18`) | `ValueError` — imposto 100× maior passaria calado |
| Itens e apuração desalinhados | `zip(strict=True)` |
| Base negativa | `ValueError` |
| DV calculado sobre comprimento errado | `ChaveInvalida` |

"Resiliente" mal aplicado vira `except: pass`, que em cálculo de imposto esconde
exatamente o bug que só aparece na fiscalização. Todo `except` no código justifica por
escrito por que engolir é correto ali.

## Design by Contract

As três categorias, e onde cada uma vive:

- **Pré-condição** — no início do método de domínio. `calcular_dv` exige 43 posições;
  `calcular_icms` exige alíquota entre 0 e 1; `montar_chave` recusa campo maior que o
  layout.
- **Pós-condição** — a mais negligenciada. "A soma das partes rateadas da CSRF bate com o
  total"; "depois de autorizar, existe protocolo". Verificadas em teste e no código.
- **Invariante** — guarda dentro da transição do agregado (`só documento transmitido é
  autorizado`), não checagem externa repetida a cada leitura. `reconstituir` confere o
  invariante ao carregar: autorizado sem protocolo é dado corrompido e falha na leitura.

## O agregado e a costura

`DocumentoFiscal` tem estado privado e transições guardadas: de fora se pede a ação
(`autorizar`, `cancelar`), não se atribui o resultado. É *imutabilidade de fronteira* — a
mutação existe, mas fica contida; ninguém faz o documento mentir sobre a própria situação.

A costura crítica é a persistência do protocolo. Se a SEFAZ autoriza e o protocolo não
grava, existe nota válida no fisco e rascunho no sistema. Por isso há um teste que **muta,
projeta, reconstitui por caminho independente e compara** — não apenas verifica o retorno
do método.

## Como rodar

```sh
# suíte completa, sem infraestrutura
python -m unittest discover -s erpnext_brasil/tests -t .

# um módulo
python -m unittest erpnext_brasil.tests.test_chave_acesso -v
```
