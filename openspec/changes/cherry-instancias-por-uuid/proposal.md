## Why

Com o Soda (`soda-instancias-do-erp`), um bench passa a ter várias instâncias do ERPNext Brasil, cada uma com **UUID único** e **descritivo único**. O Cherry, que hoje enxerga um bench como uma lista de sites com nomes, passaria a mostrar `a-1f3c9e2b.localhost` e `b-7d40aa11.localhost` sem dizer o que são, e permitiria editar uma configuração comum do bench (banco, portas, Redis, `apps.txt`) sem avisar que ela vale para **todas** as instâncias. O pedido é que o Cherry identifique cada instância pelo UUID, com o descritivo único.

## What Changes

- O Cherry passa a ler o contrato de identidade do Soda e a mostrar, onde hoje mostra o nome do site, o **descritivo**, o **UUID abreviado**, a porta e o estado (somente leitura).
- A aba **Sites** seleciona por instância; as edições por site (por exemplo `allow_tests`) vão ao `site_config` da instância escolhida, e as chaves `soda_instance_id` e `soda_descritivo` aparecem como somente leitura e nunca são alteradas pelo Cherry.
- As abas que mexem em configuração **comum** do bench (Banco de dados, Portas e Redis, `apps.txt`) avisam que a alteração vale para todas as instâncias, listando as que estão no ar, e o formulário de portas recusa portas que caem na faixa alocada às instâncias.
- O comando `bench new-site` que o Cherry gera avisa que um site criado fora do Soda não terá UUID nem descritivo, e aponta o Soda para criar instâncias.
- Sem registro do Soda, o Cherry funciona exatamente como hoje, tratando cada site como instância sem UUID.
- Segue os padrões do projeto e do próprio Cherry (núcleo a 100%, interface com piso no CI, `ruff` limpo, contratos e injeção de dependência), e a persistência das suas preferências passa a ter a opção SQLite (mudança `persistencia-sqlite-opcional`).
- Versão `0.3.0` do Cherry (mudança visível), com `docs/cherry.md` atualizado.

## Capabilities

### New Capabilities

- `ferramentas/cherry-instancias`: o Cherry identifica as instâncias do Soda pelo UUID com o descritivo único, protege a identidade e avisa o alcance das configurações comuns.

### Modified Capabilities

Nenhuma.

## Impact

- `scripts/cherry/app.py`, `scripts/cherry/config.py` (ou o leitor importado de `erpnext_brasil/soda/leitura.py`, decisão em aberto no design do Soda), `scripts/cherry/test_*.py`, `scripts/cherry/__init__.py`, `docs/cherry.md`.
- Depende do contrato de identidade da mudança `soda-instancias-do-erp`; não pode ser aplicada antes de o contrato existir.
- CI: os pisos de cobertura do Cherry (95% no núcleo, 87% na interface) continuam valendo.
