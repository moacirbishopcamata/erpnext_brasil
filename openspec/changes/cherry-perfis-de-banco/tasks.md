## 1. Modelo e leitor

- [x] 1.1 Pacote puro `erpnext_brasil/bancos/` com `PerfilDeBanco` imutável (nome, tipo, host, porta, usuário, padrão, último teste) e as pré-condições — verificar com testes de borda (tipo desconhecido, porta fora da faixa, nome repetido sem distinção de caixa, nome vazio) e a ausência de campo de senha.
- [x] 1.2 Repositório de perfis sobre a porta de persistência, com exatamente um padrão, e leitor somente leitura sem trava de escrita — verificar com a suíte de contrato nos três adaptadores e com leitura durante gravação.
- [x] 1.3 Migração da configuração atual para o perfil padrão, sem alterar o `common_site_config.json` — verificar com um arquivo real de exemplo e comparação de bytes antes e depois.

## 2. Regras

- [x] 2.1 Padrão único: criar, trocar e remover mantêm um só padrão; o padrão é gravado no `common_site_config.json` — verificar relendo o arquivo por outro caminho depois de cada operação.
- [x] 2.2 Perfil em uso por instância do Soda não é removido nem muda de tipo ou servidor, e a recusa lista as instâncias — verificar com um registro do Soda de exemplo.
- [x] 2.3 Teste de conexão por perfil, guardando só data, nível e resultado — verificar com executor injetado e busca da senha em todos os arquivos do bench temporário, que não pode estar lá.

## 3. Interface e comando

- [ ] 3.1 Aba **Banco de dados** com a lista de perfis, o padrão marcado, formulário com restrições visíveis e teste por perfil, no molde do Cherry — verificar com testes de interface e captura de tela.
- [x] 3.2 `bench new-site` gerado a partir do perfil escolhido — verificar com os cenários MariaDB e PostgreSQL e com o critério de nomes seguros já existente.
- [x] 3.3 Aviso de alcance (instâncias no ar) ao trocar o padrão — verificar com teste de interface.

## 4. Versão, documentação e padrões

- [x] 4.1 Versão `0.4.0` e `docs/cherry.md` com os perfis — verificar pelo teste de versão e relendo o documento.
- [x] 4.2 Cobertura do núcleo a 100% e pisos de CI mantidos — verificar com o job do Cherry verde.
- [x] 4.3 Gate de padrões: contratos, injeção, teste na costura, `ruff check`, `ruff format --check` e `tests/test_arquitetura.py` verdes — verificar com a saída dos comandos.
- [ ] 4.4 Gate de resiliência e segurança (mudança `resiliencia-e-seguranca-das-ferramentas`): desfazer e retomar, idempotência, prazos em todo comando externo, tratamento de exceção na interface, validação de entrada, nenhum vazamento de segredo, varredura de padrões proibidos, confinamento de caminhos, permissões e limites — verificar com a saída dos comandos e a tabela de requisitos.
