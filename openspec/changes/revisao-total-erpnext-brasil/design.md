## Context

Ver `proposal.md` (Why). Restrições do projeto que moldam o método:

- `fiscal/`, `contabil/` e `folha/` nunca importam `frappe`; `integracao/` é a costura. `tests/test_arquitetura.py` já impõe isso com `ast`.
- Docstrings registram a fonte normativa e o nível de confiança de cada regra; o que está incompleto vai em `docs/gaps.md`.
- O CI roda só suíte pura + `ruff`. Costura com Frappe (Custom Field, hook, DocType) só é provada por `tests_bench/`, e só em WSL2/Linux.
- "Padrão declarado ≠ padrão cumprido" foi o achado dominante das auditorias anteriores (ruff configurado e nunca executado; 31 campos lidos e nunca criados).

## Goals / Non-Goals

**Goals:**
- Um retrato único, datado e reproduzível do app inteiro, com severidade comparável entre frentes.
- Achar o que ninguém declarou: costura quebrada, regra fiscal sem fonte, teste que não cruza a costura, doc que mente sobre o código.
- Sair com uma fila priorizada de changes de correção, cada um pequeno o bastante para uma sessão.

**Non-Goals:**
- Corrigir código na própria revisão (exceto erro factual em doc).
- Reescrever arquitetura, trocar de pilha ou subir versão de dependência.
- Provar autorização em SEFAZ real; isso exige certificado A1 e homologação e fica como pendência de ambiente.
- Revisar o ERPNext, o Frappe ou o hrms; bug neles vira patch em `contrib/`.

## Decisions

1. **Frentes em vez de camadas.** Fiscal documental, fiscal tributário, contábil, folha/RH, integração, setup, saúde/estoque, testes, segurança. Revisar por camada técnica esconderia o achado de costura entre `fiscal/` e `integracao/`.
2. **Severidade em quatro níveis.** *Crítico*: dado fiscal ou contábil errado, ou erro silencioso em produção. *Alto*: código inalcançável ou inerte num site real. *Médio*: fonte normativa ausente, teste que não cruza a costura, doc defasada que induz erro. *Baixo*: estilo, nomenclatura, duplicação.
3. **Todo achado cita evidência.** Arquivo e linha, saída de comando ou URL da fonte com data. Achado sem evidência não entra; hipótese vai numa seção própria "a verificar".
4. **Costura primeiro.** Em cada frente, cruzar `hooks.py` ↔ `setup/` ↔ o que a integração lê e escreve (Custom Field declarado, hook alcançável, DocType instalado) e conferir se há teste de bench com `MODULOS_COBERTOS` declarado (`scripts/cobertura_de_bench.py`). Pós-condição de persistência (linhas afetadas) e releitura por caminho independente entram na checagem.
5. **Regra fiscal: fonte normativa ou aviso.** Cada regra revisada é conferida contra a fonte primária (MOC, NT, Ajuste SINIEF, leiaute) quando acessível; fonte só secundária gera aviso com o nível de confiança, nunca bloqueio.
6. **Evidência de execução.** Suíte pura, `ruff check`, `ruff format --check` e `scripts/auditar_pilha.py` rodam de novo e entram com o resultado. Bench só entra se rodado de verdade; senão a síntese diz "não executado".
7. **Saída em dois níveis.** Síntese curta em `docs/revisao-total.md` (números, principais achados, fila de changes) e anexos em `docs/revisao-total/<frente>.md`, indexados em `docs/README.md`.
8. **Revisão em linha.** Frente a frente, na mesma sessão de trabalho, para a severidade ficar consistente. Subagentes só se o usuário pedir.

## Risks / Trade-offs

- **Tamanho (~91 mil linhas):** leitura exaustiva é inviável. Mitigação: amostragem dirigida por risco (módulos que gravam, transmitem ou calculam imposto) e varredura mecânica (`ast`, `grep`) para o resto; a síntese declara a cobertura real de cada frente.
- **Fonte normativa inacessível ou paga:** vira aviso com nível de confiança, não bloqueio.
- **Sem bench, a costura fica sem prova:** a síntese separa "provado em bench" de "inferido da leitura".
- **Docs defasam de novo:** cada documento gerado fixa `__version__` e data.
- **Banco compartilhado:** qualquer execução de bench segue `docs/ambiente-dev-bench.md` e faz backup antes.

## Open Questions

Nenhuma que bloqueie o início. A confirmar na aplicação: rodar bench nesta revisão (exige WSL2) ou entregar só a leitura estática.
