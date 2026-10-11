## Context

Ver `proposal.md` (Why). O Cherry `0.2.1` tem `config.py` (núcleo, 100% de cobertura) e `app.py` (interface, 89%); lê o bench pelo caminho `\\wsl.localhost\...`, escreve de forma atômica e usa dependências injetáveis. A identidade de instância vem do contrato da mudança `soda-instancias-do-erp`.

O Cherry é, como o Soda e o Chantilly, um **complemento desktop em Python puro** (só biblioteca padrão); a identificação por instância não muda isso.

## Decisions

1. **O Cherry só lê o contrato.** Escrever no registro é do Soda. O Cherry nunca grava `soda_*`, e o teste prova isso relendo o `site_config` antes e depois de cada edição.
2. **Leitor:** importar o leitor puro do Soda ou ter um leitor próprio é a decisão em aberto 7 do design do Soda; qualquer que seja, o Cherry fica atrás de uma porta (`LeitorDeInstancias`), de modo que o resto do núcleo não saiba de onde vêm as instâncias.
3. **Sem Soda, como hoje.** A ausência do registro é estado normal, não erro.
4. **Alcance da configuração comum.** O núcleo calcula "quais instâncias esta alteração afeta" (puro), e a interface só mostra e pede confirmação.
5. **Padrões do projeto, iguais aos do app e aos do Cherry (obrigatórios).** Design by Contract: pré-condições recusadas antes de tocar em qualquer estado (exceção própria do domínio), pós-condições gravadas como teste e invariantes nos construtores. Dados que cruzam camadas são imutáveis (`dataclass(frozen=True)`). Inversão de dependência por portas pequenas (`Protocol`): relógio, executor de comandos, repositório de persistência, leitor de `/proc`, teste de porta livre; classes concretas sem herança de implementação e sem método estático que esconda dependência. A regra é pura (sem I/O, sem `frappe`, sem tkinter) e a camada fina só traduz. Falha alto onde o silêncio daria dado errado. TDD com teste na costura: grava-se por um caminho e relê-se por outro, nunca só o retorno. Cobertura: núcleo a 100% (piso de 95% no CI), interface com piso próprio dois pontos abaixo do medido, `ruff check` e `ruff format` limpos, e `tests/test_arquitetura.py` vigiando a fronteira. Versão e documento atualizados a cada mudança visível.
6. **Persistência das preferências** (`~/.cherry.json`: caminho, distro, geometria): ganha a opção SQLite pela mudança `persistencia-sqlite-opcional`; nunca guarda senha.

### Resiliência, robustez e segurança

**Resiliência, robustez e segurança (obrigatórias, mudança `resiliencia-e-seguranca-das-ferramentas`).** Operação com vários passos registra a intenção, desfaz só o que fez e pode ser retomada depois de interrupção; repetir é seguro; todo comando externo tem prazo e saída limitada; nenhuma exceção chega sem tratamento à janela; toda entrada externa é validada e os leitores de texto externo são testados com entrada malformada e aleatória; segredo nunca em argumento, log, persistência, mensagem ou clipboard indefinido; comando é lista de argumentos, nunca shell; caminhos confinados; arquivos de estado com permissão restrita; ação destrutiva falha fechada; recursos locais limitados.

### Windows e Linux

Funciona nos dois sistemas com o mesmo código (mudança `ferramentas-multiplataforma`): janela no Windows operando o bench no WSL2, ou janela em Linux operando o bench local, por uma porta de plataforma com dois adaptadores; a regra pura não consulta o sistema operacional.

## Risks / Trade-offs

- **Acoplamento entre ferramentas:** o Cherry passa a depender do contrato do Soda; a porta e o teste com registro de exemplo versionado limitam o dano de uma mudança no Soda.
- **Aplicar antes do Soda:** não é possível; a mudança só começa quando o contrato existir.
