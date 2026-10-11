## Why

As três ferramentas guardam estado em arquivos diferentes, cada uma à sua maneira: o Cherry grava `~/.cherry.json`, o Soda guardaria o registro das instâncias em JSON, e o Chantilly já precisa de SQLite para as séries. JSON é simples e legível, mas dois processos gravando o mesmo arquivo exigem trava própria, e a atomicidade é feita à mão. SQLite oferece transação, trava entre processos e consulta de graça, sem servidor, na biblioteca padrão. Em vez de escolher um para todos, a decisão é **oferecer SQLite como opção de persistência** em cada ferramenta, atrás da mesma interface, com JSON continuando disponível onde a legibilidade vale mais.

## What Changes

- Uma **porta de persistência** pequena e comum (o repositório do domínio de cada ferramenta), com **dois adaptadores**: JSON e SQLite. A escolha é por configuração, por ferramenta.
- **Cherry:** as preferências (`~/.cherry.json`) ganham a opção SQLite; senha nunca é persistida em nenhum formato.
- **Soda:** o registro das instâncias (UUID, descritivo, portas, estado, aposentados) ganha a opção SQLite; o JSON continua o padrão.
- **Chantilly:** a série histórica **só em SQLite** (volume e consulta tornam JSON impraticável); a configuração (limiares, preços) e o registro das ações de controle ganham a opção JSON ou SQLite.
- **Migração nos dois sentidos** entre JSON e SQLite, sem perder dado, com cópia do formato anterior até o usuário confirmar.
- **Uma suíte de contrato** que roda a mesma bateria de testes contra os dois adaptadores de cada ferramenta, para provar que se comportam igual.
- **Versão de esquema** do SQLite (`PRAGMA user_version`) e migrações aplicadas na abertura, com teste de cada migração.
- Todas as três seguem os padrões do projeto: contratos, imutabilidade de fronteira, injeção de dependência, teste na costura, núcleo a 100% e pisos de cobertura no CI.

Fora desta mudança: banco de dados cliente-servidor, criptografia do arquivo, sincronização entre máquinas.

## Capabilities

### New Capabilities

- `ferramentas/persistencia-selecionavel`: o contrato comum de persistência selecionável (JSON ou SQLite) das ferramentas, com migração, esquema versionado e paridade comprovada por teste.

### Modified Capabilities

Nenhuma.

## Impact

- `scripts/cherry/`, `erpnext_brasil/soda/` e `scripts/soda/`, `erpnext_brasil/chantilly/` e `scripts/chantilly/`: cada um ganha um repositório com dois adaptadores. Nenhum usa dependência fora da biblioteca padrão (`sqlite3`, `json`).
- Testes: uma suíte de contrato por ferramenta, parametrizada pelos dois adaptadores.
- Depende das mudanças `soda-instancias-do-erp` e `chantilly-monitor-de-recursos` para os repositórios novos; as preferências do Cherry podem ser migradas antes, de forma independente.
- Documentação: uma seção "Persistência" em `docs/cherry.md`, `docs/soda.md` e `docs/chantilly.md`.
