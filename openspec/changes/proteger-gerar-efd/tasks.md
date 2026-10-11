## 1. `gerar_efd`

- [ ] 1.1 (**não feito**: falta o teste de bench de permissão por método) Escrever o teste de bench em que um usuário sem papel contábil chama `gerar_efd` e espera `PermissionError`, sem `Arquivo SPED` criado — verificar vendo-o falhar antes da correção e passar depois.
- [ ] 1.2 (feito em `geracao_efd.py`; falta a prova em bench) Acrescentar `frappe.has_permission("Arquivo SPED", "create", throw=True)` e `frappe.has_permission("Company", "read", company, throw=True)` no início de `gerar_efd`; trocar o `insert` por um que respeite a permissão — verificar com o teste da 1.1 e o fluxo feliz com usuário autorizado.

## 2. Leituras por empresa

- [ ] 2.1 (**não feito**) Teste de bench: usuário restrito a uma empresa não lê armazéns, saldos nem prontidão de outra — verificar vendo-o falhar antes e passar depois.
- [ ] 2.2 (feito em `navegador_estoque.py`, `alerta_fiscal.py` e `pix.py`; falta a prova em bench) Aplicar checagem de permissão (ou `get_list`) em `filhos_do_endereco`, `conteudo_do_endereco`, `enderecos_do_item`, `verificar_prontidao_efd` e `gerar_payload_pix` — verificar com o teste da 2.1 e `tests_bench/` verde.

## 3. Trava contra regressão

- [x] 3.1 Teste da suíte pura que varre `integracao/` por `ast` e falha se um método `@frappe.whitelist()` não tiver checagem de permissão direta e não estiver numa lista de exceções com motivo — verificar acrescentando temporariamente um método sem checagem e vendo o teste falhar.

## 4. Documentação

- [x] 4.1 Marcar RT-02, RT-03 e RT-19 resolvidos em `docs/revisao-total/integracao.md`, `seguranca.md` e `docs/revisao-total.md` — verificar relendo os três.
