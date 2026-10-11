## Why

Por decisão do dono do projeto (2026-10-11), o **Cherry, o Chantilly e o Soda devem ser bem escritos e ter o máximo de resiliência, robustez e segurança**. São ferramentas que **alteram o ambiente** (gravam configuração, criam e removem bancos, iniciam e param o ERP, copiam comandos com segredo), então a qualidade delas não é estética: um defeito vira arquivo corrompido, instância perdida, segredo vazado ou ERP parado no meio de uma emissão fiscal. A revisão do Cherry já provou o custo: senha legível na linha de comando do processo (CH-01), arquivo truncado por uma falha no meio da escrita (CH-02), comando copiado sem escape (CH-03). Adjetivos não bastam; o pedido precisa virar **critérios que um teste confere**.

## What Changes

- Um conjunto **comum e verificável** de requisitos de **resiliência**, **robustez** e **segurança**, aplicado às três ferramentas e conferido por um **gate** em cada mudança.
- **Resiliência:** operação interrompida deixa rastro e pode ser retomada ou desfeita; falha de um passo desfaz só o que ele fez; todo comando externo tem prazo; repetir uma operação é seguro (idempotência); fechar a janela no meio de uma operação longa não deixa processo órfão nem estado pela metade.
- **Robustez:** toda entrada é validada na fronteira; limites explícitos de tamanho, quantidade e tempo; nenhuma exceção sobe sem tratamento até a janela; leitores de texto externo (`/proc`, saída de comandos, JSON de terceiros) são testados com entrada malformada e aleatória; recursos (saída de comandos, registros de log, histórico) são limitados.
- **Segurança:** segredo nunca em argumento de processo, em log, em arquivo de persistência, em mensagem de erro nem na área de transferência por tempo indefinido; comandos montados como **lista de argumentos**, nunca por concatenação em shell; caminhos validados contra saída da pasta permitida e contra links simbólicos; arquivos de estado criados com permissão restrita ao dono; ação destrutiva exige confirmação forte e é recusada na dúvida; toda ação de controle é registrada; processos são identificados por PID e diretório, nunca por nome.
- **Escrita:** código pequeno e legível, regra pura separada de I/O, contratos, nomes do domínio, sem exceção engolida em silêncio, sem `except` amplo sem motivo registrado, tipagem nos limites.
- Ferramentas de verificação **sem dependência nova**: testes de propriedade e de entrada aleatória escritos com a biblioteca padrão (`random` com semente fixa), `ruff`, e uma varredura por `ast` que falha em padrões proibidos.

Fora desta mudança: auditoria externa de segurança e criptografia do armazenamento local.

## Capabilities

### New Capabilities

- `ferramentas/resiliencia-e-seguranca`: o contrato comum de resiliência, robustez e segurança das três ferramentas de operação.

### Modified Capabilities

Nenhuma.

## Impact

- `scripts/cherry/`, `scripts/soda/`, `scripts/chantilly/` e os pacotes puros `erpnext_brasil/persistencia/`, `erpnext_brasil/soda/`, `erpnext_brasil/chantilly/`, `erpnext_brasil/bancos/`.
- Um teste de varredura por `ast` (`tests/test_seguranca_das_ferramentas.py`) que falha em `shell=True`, `os.system`, `eval`, `exec`, `pickle`, `except:` sem tipo e comando montado por concatenação.
- Testes de entrada aleatória para cada leitor de texto externo.
- Cada mudança do Cherry, do Soda e do Chantilly ganha o **gate de resiliência e segurança** além do gate de padrões.
- Documentação: seção "Resiliência, robustez e segurança" em `docs/ferramentas-de-operacao.md` e em cada documento de ferramenta.
