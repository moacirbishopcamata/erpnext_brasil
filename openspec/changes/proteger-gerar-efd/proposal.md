## Why

`gerar_efd` (`integracao/geracao_efd.py:90`) é `@frappe.whitelist()`, recebe `company` do cliente, lê a escrituração da empresa e grava um `Arquivo SPED` com `insert(ignore_permissions=True)`, sem nenhuma checagem de permissão. Qualquer usuário autenticado gera e grava a EFD de qualquer empresa (RT-02, **Alto**). Os métodos de leitura do navegador de estoque, a prontidão da EFD e o Pix usam `get_all`, `db.get_value` ou SQL cru, que ignoram as regras de permissão, e aceitam a empresa vinda do cliente (RT-03, Médio). Ver `docs/revisao-total/integracao.md`.

## What Changes

- `gerar_efd` verifica permissão de criação em `Arquivo SPED` e de leitura na `Company` antes de montar qualquer bloco, e passa a gravar sem `ignore_permissions` (ou o justifica em comentário, se o fluxo exigir).
- `filhos_do_endereco`, `conteudo_do_endereco`, `enderecos_do_item`, `verificar_prontidao_efd` e `gerar_payload_pix` verificam permissão de leitura na empresa e no armazém, ou trocam `get_all` por `get_list`.
- `empresa` vinda do cliente só vale se o usuário tem acesso a ela.
- Teste de bench por método: usuário sem papel recebe `PermissionError`; usuário com papel segue funcionando.
- Teste que falha se um método `@frappe.whitelist()` novo em `integracao/` não tiver checagem de permissão direta nem estiver numa lista de exceções justificadas (RT-19).

## Capabilities

### New Capabilities

Nenhuma. Não há spec de permissões em `openspec/specs/`; o change usa `skip_specs: true`.

### Modified Capabilities

Nenhuma.

## Impact

- `erpnext_brasil/integracao/geracao_efd.py`, `navegador_estoque.py`, `alerta_fiscal.py`, `pix.py`.
- Testes: `tests_bench/` (permissão por método) e `tests/` (a varredura por `ast` dos métodos `whitelist`).
- Comportamento visível: usuário sem acesso à empresa passa a receber `PermissionError` onde hoje recebe dados.
