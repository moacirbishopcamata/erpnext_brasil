## 1. Contrato comum

- [ ] 1.1 Definir, no núcleo puro de cada ferramenta, a porta de persistência e os dados imutáveis que ela troca — verificar com testes de contrato da porta usando um repositório em memória como primeira implementação.
- [ ] 1.2 Suíte de contrato parametrizada (mesma bateria, um adaptador por subclasse), incluindo atomicidade, unicidade, ordem de listagem e recusas — verificar rodando contra o repositório em memória e vendo cada caso nomear o adaptador que falha quando se quebra um de propósito.

## 2. Adaptadores

- [ ] 2.1 Adaptador JSON de cada ferramenta com escrita atômica e trava em arquivo — verificar passando na suíte de contrato e com falha injetada no meio da gravação (estado anterior intacto, sem temporário).
- [ ] 2.2 Adaptador SQLite de cada ferramenta (WAL, transação por operação, chaves estrangeiras) — verificar passando na mesma suíte, e com dois processos gravando ao mesmo tempo sem perda nem duplicidade.
- [ ] 2.3 Esquema versionado por `PRAGMA user_version` e migrações numeradas, aplicadas na abertura em transação — verificar com um arquivo de cada versão anterior real, e com um arquivo de versão posterior que deve abrir só para leitura.
- [ ] 2.4 Teste que inspeciona o esquema e falha se houver coluna com nome ou finalidade de segredo — verificar acrescentando temporariamente uma coluna `senha` e vendo o teste falhar.
- [ ] 2.5 Quarentena de arquivo ilegível nos dois formatos — verificar com um arquivo corrompido de cada formato, que não pode ser sobrescrito.

## 3. Troca de formato

- [ ] 3.1 Migração JSON para SQLite e SQLite para JSON, com releitura de conferência e cópia do formato anterior — verificar com ida e volta (estado final igual ao inicial) e com interrupção no meio (original intacto, tentativa repetível).
- [ ] 3.2 Idempotência: migrar duas vezes não duplica nem altera nada — verificar com teste.

## 4. Por ferramenta

- [ ] 4.1 Cherry: preferências em JSON ou SQLite, sem senha em nenhum — verificar com a suíte de contrato e o teste existente `test_preferencias_nao_guardam_senha` estendido aos dois formatos.
- [ ] 4.2 Soda: registro das instâncias em JSON ou SQLite, com os UUIDs aposentados e o leitor do contrato lendo os dois — verificar com a suíte de contrato e o teste de que o leitor devolve o mesmo resultado nos dois formatos.
- [ ] 4.3 Chantilly: série só em SQLite; configuração e registro de controle em JSON ou SQLite — verificar com a suíte de contrato e a ausência da opção JSON para a série.
- [ ] 4.4 Seleção e migração na interface e no terminal de cada ferramenta, mostrando formato, caminho e versão de esquema — verificar com um teste de interface por ferramenta.

## 5. Padrões, CI e documentação

- [ ] 5.1 Cobertura: núcleo a 100% e pisos de CI mantidos em cada ferramenta, com os dois adaptadores cobertos — verificar com o relatório de cobertura dos jobs de CI.
- [ ] 5.2 Seção "Persistência" em `docs/cherry.md`, `docs/soda.md` e `docs/chantilly.md` — verificar relendo contra o código.
- [ ] 5.3 Gate de padrões antes de fechar: contratos (pré, pós e invariante) listados por módulo no documento da ferramenta, dependências injetadas por porta, teste na costura em cada gravação, cobertura do núcleo a 100% e pisos de CI cumpridos, `ruff check`, `ruff format --check` e `tests/test_arquitetura.py` verdes — verificar com a saída dos comandos e a lista de contratos no documento.
- [ ] 5.4 Gate de resiliência e segurança (mudança `resiliencia-e-seguranca-das-ferramentas`): desfazer e retomar, idempotência, prazos em todo comando externo, tratamento de exceção na interface, validação de entrada, nenhum vazamento de segredo, varredura de padrões proibidos, confinamento de caminhos, permissões e limites — verificar com a saída dos comandos e a tabela de requisitos.
