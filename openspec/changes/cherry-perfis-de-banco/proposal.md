## Why

Por decisão do dono do projeto (2026-10-11), **a escolha de qual banco de dados usar é do Cherry**, que faz toda a configuração, para MariaDB e/ou PostgreSQL. Hoje o Cherry guarda uma única configuração por bench (`db_type`, `db_host`, `db_port`, `root_login` no `common_site_config.json`). Com o Soda criando várias instâncias, o mesmo bench pode ter instâncias em MariaDB e em PostgreSQL (o `docs/ambiente-dev-bench.md` já tem `v16.localhost` em MariaDB e `v16pg.localhost` em PostgreSQL). O Soda e o Chantilly não devem decidir banco: devem consumir o que o Cherry configurou.

## What Changes

- O Cherry passa a manter **perfis de banco**: configurações nomeadas (tipo `mariadb` ou `postgres`, host, porta, usuário administrador), com **exatamente um padrão**. **Senha nunca é persistida** em nenhum formato.
- O perfil padrão continua sendo gravado no `common_site_config.json` (`db_type`, `db_host`, `db_port`, `root_login`, e `root_password` apenas quando o usuário manda), de modo que `bench new-site` puro continua funcionando como hoje.
- Na primeira abertura de um bench que já tem configuração, o Cherry cria o perfil **padrão** a partir dela, sem perder nada.
- O teste de conexão (três níveis, já existente) passa a valer **por perfil**, com a senha informada na hora, e o último resultado (data, nível, sucesso; sem senha) fica guardado no perfil.
- O Cherry **publica** os perfis, somente para leitura, para o Soda e o Chantilly consumirem por um leitor puro (`erpnext_brasil/bancos/perfis.py`). O Cherry é o único escritor.
- Um perfil que instâncias do Soda usam **não pode ser removido** nem ter o tipo trocado; o Cherry diz quais instâncias o usam (pelo UUID e descritivo).
- O `bench new-site` que o Cherry gera usa o perfil escolhido.
- A persistência dos perfis segue `persistencia-sqlite-opcional` (JSON padrão, SQLite opção).
- Segue os padrões do projeto e do Cherry: núcleo a 100%, interface com piso no CI, `ruff` limpo, contratos e injeção.
- Versão `0.4.0` do Cherry.

- **Resiliência, robustez e segurança (obrigatórias, mudança `resiliencia-e-seguranca-das-ferramentas`).** Operação com vários passos registra a intenção, desfaz só o que fez e pode ser retomada depois de interrupção; repetir é seguro; todo comando externo tem prazo e saída limitada; nenhuma exceção chega sem tratamento à janela; toda entrada externa é validada e os leitores de texto externo são testados com entrada malformada e aleatória; segredo nunca em argumento, log, persistência, mensagem ou clipboard indefinido; comando é lista de argumentos, nunca shell; caminhos confinados; arquivos de estado com permissão restrita; ação destrutiva falha fechada; recursos locais limitados.

## Capabilities

### New Capabilities

- `ferramentas/cherry-perfis-de-banco`: perfis de banco (MariaDB e/ou PostgreSQL) como responsabilidade do Cherry, com padrão único, teste por perfil, publicação somente leitura e proteção contra remoção em uso.

### Modified Capabilities

Nenhuma.

## Impact

- `scripts/cherry/` (aba Banco de dados e núcleo), novo pacote puro `erpnext_brasil/bancos/` com o modelo e o leitor dos perfis.
- Depende de `persistencia-sqlite-opcional` (porta de persistência) e se integra com `soda-instancias-do-erp` (consumo) e `cherry-instancias-por-uuid` (aviso de alcance).
- Compatibilidade: benches existentes continuam funcionando; o perfil padrão nasce da configuração atual.
- Documentação: `docs/cherry.md` e `docs/ferramentas-de-operacao.md`.
