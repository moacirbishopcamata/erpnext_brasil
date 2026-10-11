## 1. Leitura da identidade

- [ ] 1.1 Porta `LeitorDeInstancias` no núcleo do Cherry e adaptador sobre o contrato do Soda — verificar com testes que lêem um registro de exemplo versionado, um de versão futura e um bench sem registro.
- [ ] 1.2 Tolerar campo desconhecido e versão de esquema maior, sem gravar nada — verificar com os dois arquivos de exemplo.

## 2. Aba Sites por instância

- [ ] 2.1 Mostrar descritivo, UUID abreviado, porta e estado, com o nome do site em segundo plano, e UUID completo copiável — verificar com teste de interface e captura de tela com e sem Soda.
- [ ] 2.2 Chaves `soda_instance_id` e `soda_descritivo` somente leitura e jamais gravadas — verificar com teste que edita `allow_tests` e relê o `site_config` por outro caminho, comparando as chaves antes e depois.

## 3. Configuração comum

- [ ] 3.1 Núcleo puro que calcula as instâncias afetadas por uma alteração comum; aviso e confirmação na interface quando houver instância no ar — verificar com testes do núcleo e um teste de interface por aba (Banco de dados, Portas e Redis, Sites, `apps.txt`).
- [ ] 3.2 Recusa de portas que caem na faixa ou numa porta alocada a instância, nomeando a instância — verificar com teste do núcleo e da interface.
- [ ] 3.3 `default_site` pelo descritivo e aviso de instância parada — verificar com teste de interface.
- [ ] 3.4 Aviso no comando `bench new-site` gerado — verificar com teste da tela.

## 4. Versão, documentação e CI

- [ ] 4.1 Versão `0.3.0` e `docs/cherry.md` com a seção de instâncias — verificar pelo teste de versão e relendo o documento.
- [ ] 4.2 Manter os pisos de cobertura do Cherry (95% no núcleo e 87% na interface) — verificar com o job do Cherry verde no PR, e o log mostrando a interface rodada.
- [ ] 4.3 Rodar os testes do Cherry, `coverage` e `ruff` em `scripts/` e `openspec validate cherry-instancias-por-uuid` — verificar com a saída verde.
- [ ] 4.4 Gate de padrões antes de fechar: contratos (pré, pós e invariante) listados por módulo no documento da ferramenta, dependências injetadas por porta, teste na costura em cada gravação, cobertura do núcleo a 100% e pisos de CI cumpridos, `ruff check`, `ruff format --check` e `tests/test_arquitetura.py` verdes — verificar com a saída dos comandos e a lista de contratos no documento.
- [ ] 4.5 Gate de resiliência e segurança (mudança `resiliencia-e-seguranca-das-ferramentas`): desfazer e retomar, idempotência, prazos em todo comando externo, tratamento de exceção na interface, validação de entrada, nenhum vazamento de segredo, varredura de padrões proibidos, confinamento de caminhos, permissões e limites — verificar com a saída dos comandos e a tabela de requisitos.
