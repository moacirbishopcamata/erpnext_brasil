## Context

Ver `proposal.md` (Why). O Cherry grava `~/.cherry.json` com a escrita atômica de `_gravar_texto`; o Soda e o Chantilly foram desenhados com registro e série próprios (`sites/soda/registro.json`, `sites/chantilly.sqlite`). O projeto tem a prática de repositório atrás de interface (`repositorio_frappe.py` implementa `Protocol`s da regra pura) e de teste na costura.

## Goals / Non-Goals

**Goals:**
- Uma opção de SQLite em cada ferramenta, atrás da mesma interface, sem dependência fora da biblioteca padrão.
- Comportamento idêntico nos dois formatos, **provado por uma suíte de contrato única**.
- Migração segura e esquema versionado.

**Non-Goals:**
- Banco cliente-servidor, criptografia, sincronização entre máquinas, e SQLite para o estado do ERPNext (isso é do Frappe).

## Decisions

1. **Repositório por ferramenta, com um adaptador por formato.** Cada ferramenta define a sua porta (`RepositorioDePreferencias`, `RepositorioDoRegistro`, `RepositorioDeConfiguracao`) no núcleo puro; os adaptadores `Json…` e `Sqlite…` ficam na camada fina. A porta não vaza o formato: devolve e recebe dados imutáveis do domínio.
2. **Suíte de contrato parametrizada.** Uma classe de teste base por porta, subclassificada uma vez por adaptador, roda os mesmos casos nos dois. Se um adaptador diverge, o teste nomeia o caso.
3. **SQLite:** `sqlite3` da biblioteca padrão, modo WAL, `PRAGMA user_version` para o esquema, chaves estrangeiras ligadas, transação por operação lógica. A trava entre processos é do próprio banco; o adaptador JSON mantém a trava em arquivo e a escrita atômica do Cherry.
4. **Migrações de esquema** como funções numeradas e puras sobre uma conexão, aplicadas em ordem dentro de uma transação, cada uma com teste que parte do esquema anterior real.
5. **Troca de formato** como operação própria: lê tudo pelo repositório de origem, grava tudo pelo de destino numa transação, confere por releitura que o destino é igual à origem, e só então troca a configuração. A cópia do formato anterior fica ao lado até a confirmação.
6. **Nada de segredo:** o esquema é revisto por um teste que falha se existir coluna com nome de segredo, e os repositórios não têm campo para isso.
7. **Quarentena** igual nos dois formatos: arquivo ilegível é movido, nunca sobrescrito.
8. **Padrões do projeto, iguais aos do app e aos do Cherry (obrigatórios).** Design by Contract: pré-condições recusadas antes de tocar em qualquer estado (exceção própria do domínio), pós-condições gravadas como teste e invariantes nos construtores. Dados que cruzam camadas são imutáveis (`dataclass(frozen=True)`). Inversão de dependência por portas pequenas (`Protocol`): relógio, executor de comandos, repositório de persistência, leitor de `/proc`, teste de porta livre; classes concretas sem herança de implementação e sem método estático que esconda dependência. A regra é pura (sem I/O, sem `frappe`, sem tkinter) e a camada fina só traduz. Falha alto onde o silêncio daria dado errado. TDD com teste na costura: grava-se por um caminho e relê-se por outro, nunca só o retorno. Cobertura: núcleo a 100% (piso de 95% no CI), interface com piso próprio dois pontos abaixo do medido, `ruff check` e `ruff format` limpos, e `tests/test_arquitetura.py` vigiando a fronteira. Versão e documento atualizados a cada mudança visível.

## Risks / Trade-offs

- **Dois adaptadores para manter:** o custo é pago pela suíte de contrato, que impede divergência silenciosa.
- **SQLite em compartilhamento de rede:** frágil por natureza; a interface do Windows lê o arquivo do WSL pelo caminho UNC. A mitigação é abrir somente leitura e ter o resumo atômico em JSON como plano B (ver o design do Chantilly).
- **Padrão de cada ferramenta:** JSON onde a legibilidade vale (Cherry, Soda) e SQLite onde o volume exige (Chantilly). Mudar o padrão é uma decisão de produto.

## Open Questions

1. O padrão do Soda deve ser SQLite, já que elimina a trava em arquivo?
2. O Cherry precisa de SQLite para algo além das preferências (por exemplo, um diário das gravações que fez)?
3. A suíte de contrato fica em cada ferramenta ou num módulo de teste compartilhado?
