# Auditoria dos padrões de projeto

Pedido do usuário: "seja rígido no uso de nossos padrões de projeto; somente [ceda] se o
framework impedir isso". Os padrões estavam declarados — no `README.md` (as cinco regras
não-negociáveis, SOLID/DbC/Elegant Objects) e no `pyproject.toml` (lint e formatador).
Esta auditoria os confrontou com o código de verdade.

## O achado que dá o tom: padrão declarado ≠ padrão cumprido

`pyproject.toml` declara `[tool.ruff.lint]` com `select = ["F", "E", "W", "I", "UP", "B",
"RUF"]` desde o início do projeto. **Nunca tinha sido executado.** O resultado da primeira
execução:

| | Antes | Depois |
|---|---|---|
| Violações de lint | **135** | 0 |
| Arquivos fora do formatador | **134** | 0 |

Não é um detalhe de estilo: é a diferença entre ter um padrão e ter a intenção de um.

## Violações de desenho, corrigidas

### 1. Responsabilidade única — alerta no módulo errado (violação minha, da rodada anterior)

`verificar_transicao_da_reforma` (reforma tributária) tinha ficado dentro de
`integracao/alerta_certificado.py`. Justifiquei na hora como "mesma pergunta, mesma
tarefa diária" — mas isso é acoplamento por **acaso histórico**: a função foi parar lá
porque era onde o envio de notificação já existia, não porque pertencesse ao domínio de
certificado digital.

Corrigido com a regra "fatorar, nunca enxugar": o mecanismo de envio virou
`integracao/notificacao.py` (extraído quando ganhou o **segundo** consumidor — não
antes), e o alerta da reforma foi para `integracao/alerta_fiscal.py`, que é o módulo de
risco fiscal.

### 2. Segregação de interface — pedir mais do que se usa

Quatro funções declaravam `ajustes: list[X] = ()`: a anotação exigia `list`, o padrão era
uma tupla, e o corpo só **itera**. Trocado por `Sequence[X]` — o tipo exato do que a
função precisa. Era erro pré-existente que eu havia propagado ao copiar o padrão para os
módulos novos de ST e DIFAL.

### 3. PEP 8 — a variável `l` (54 ocorrências)

`for l in lancamentos` aparecia em código e testes. A PEP 8 proíbe `l` como nome de uma
letra por ser visualmente ambíguo com `1` e `I`, e "PEP 8 com rigor" é padrão declarado
deste projeto. Renomeada conforme o iterável (`lancamento`, `linha`, `pendencia`), não
por uma convenção genérica.

### 4. Teste que pode passar pelo motivo errado — `assertRaises(Exception)` (5 casos)

Capturar `Exception` faz o teste passar por um `AttributeError` de campo renomeado ou um
`TypeError` de assinatura mudada. Quatro casos testavam imutabilidade de dataclass e
passaram a esperar `FrozenInstanceError`; um esperava a exceção real do plano de contas
(`ContaDesconhecida`).

Este é o caso mais alinhado com o padrão 5 do README ("achado real > suposição
conveniente"): o teste **parecia** verde e verificava menos do que aparentava.

## Decisão de configuração, não de conveniência: `RUF002`/`RUF003`

As duas regras sinalizavam 44 ocorrências de "caractere ambíguo" — o `×` de "NF-e × CT-e"
e o travessão `—`. É tipografia deliberada da prosa em português, não `x` e `-` digitados
errado.

O projeto **já ignorava** `RUF001`, que é exatamente a mesma regra aplicada a strings.
Manter as duas irmãs ativas era incoerente: a mesma frase passaria numa string e falharia
numa docstring. Acrescentadas ao `ignore`, com o motivo registrado no próprio
`pyproject.toml`.

## O que **não** foi mudado, e por quê

- **`DocumentoFiscal` (`fiscal/documento/estado.py`) não é `frozen`.** Parece violar o
  padrão de dataclasses imutáveis, mas é o agregado com ciclo de vida
  (rascunho→autorizado→cancelado), implementando *imutabilidade de fronteira*: a mutação
  existe, fica contida, e só acontece por método guardado. É a escolha registrada, não um
  esquecimento.
- **Ausência de `__all__` em módulos antigos.** Não é padrão declarado do projeto;
  acrescentá-lo em vinte arquivos seria churn sem regra que o sustente. Inventar padrão
  na auditoria é o oposto de ser rígido com os que existem.

## A parte que impede a regressão

`tests/test_padroes_de_codigo.py` roda `ruff check` e `ruff format --check` como teste.
Faz pelo estilo o que `test_arquitetura.py` já fazia pela arquitetura: transforma a regra
em verificação executável.

Os testes **pulam** quando o `ruff` não está instalado, em vez de falhar — `ruff` é
ferramenta de desenvolvimento, não dependência de execução do app, e punir quem só roda o
ERPNext não traria ganho nenhum de qualidade.
