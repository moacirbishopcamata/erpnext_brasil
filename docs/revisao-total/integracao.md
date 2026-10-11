# Revisão total — integração com o Frappe (e costura)

Versão `0.227.0`, 2026-10-11. Cobre as tarefas 2.1 a 2.3 e 3.5 do change `revisao-total-erpnext-brasil`.

## Cobertura

- **Lido:** os 36 métodos `@frappe.whitelist()`, os pontos de `ignore_permissions`, as chamadas `frappe.db.sql`, `frappe.db.commit` e as de hora.
- **Varrido por `ast`/`grep`:** campos `br_*` usados em `integracao/` contra os declarados; caminhos do `hooks.py`.
- **Não lido linha a linha:** a maior parte dos 76 módulos de `integracao/`.

## Verificado e sem falha

| Verificação | Resultado | Evidência |
|---|---|---|
| Campo `br_*` lido pela integração e nunca criado | nenhum | 240 nomes declarados (`setup/` e JSON dos DocTypes) contra 119 usados. Os 5 que o script listou são falsos positivos: nomes montados por f-string (`br_municipio_{prefixo}`, `br_placa{prefixo}_mdfe`, `br_uf_{prefixo}`), conferidos um a um em `setup/campos_documento.py:318-343` e `:502-542`, e a chave `br_gs1` de um dicionário de retorno (`leitura_gs1.py:169`) |
| Caminho do `hooks.py` que não resolve | nenhum | 20 caminhos checados por `ast` (módulo existe e a função ou classe existe) |
| SQL montado com valor do usuário | nenhum | os 3 `db.sql` (`efd_inventario.py:87`, `navegador_estoque.py:95` e `:128`) usam parâmetros; o `f"""` de `navegador_estoque.py:128` só junta condições constantes |
| `except` amplo engolindo erro | 1 ocorrência de `except:` ou `except Exception:` fora de testes em linha própria, e nenhuma delas seguida de `pass` em `integracao/` e `fiscal/` | `grep -rnE "except( Exception)?:\s*$"` |
| DocType do app fora dos módulos | nenhum | 7 DocTypes em `registros_fiscais/`, módulo `Registros Fiscais` em `modules.txt`; `estoque/page` sob o módulo `Estoque` |

A trava `tests/test_costura_campos_e_hooks.py` já cobre a costura de campos e hooks (ver `docs/gaps.md`, seção 1).

## Achados

### RT-02 — `gerar_efd` não checa permissão e grava com `ignore_permissions` — **Alto** — *corrigido na `0.228.0`, sem prova em bench*

`integracao/geracao_efd.py:90-124`. O método é `@frappe.whitelist()`, recebe `company` do cliente, monta os blocos 0, C, E, H e K da empresa e grava um `Arquivo SPED` com `registro.insert(ignore_permissions=True)` (linha 124). Não há `check_permission`, `has_permission` nem `only_for` em todo o método. Qualquer usuário autenticado, mesmo sem papel de contador ou acesso à empresa, pode gerar e gravar a EFD de qualquer empresa. Os métodos irmãos de emissão e evento fazem `check_permission` antes de agir.

### RT-03 — métodos de leitura com `get_all`, `db.get_value` ou SQL cru ignoram permissão — **Médio** — *corrigido na `0.228.0`, sem prova em bench*

`frappe.get_all`, `frappe.db.get_value` e `frappe.db.sql` não aplicam as regras de permissão do usuário.

| Método | Evidência | O que vaza |
|---|---|---|
| `filhos_do_endereco` | `navegador_estoque.py:54-75` (`get_all` em `Warehouse`) | armazéns de qualquer `empresa` passada pelo cliente |
| `conteudo_do_endereco` | `navegador_estoque.py:109-141` (SQL cru em `Bin` e `Item`) | saldo de estoque por item de qualquer empresa |
| `enderecos_do_item` | `navegador_estoque.py:144-163` (`get_all` em `Bin`) | onde cada item está e a quantidade |
| `verificar_prontidao_efd` | `alerta_fiscal.py:91-112` (`db.get_value` em `Company` e `Address`) | CNPJ, inscrição estadual e município de qualquer empresa |
| `gerar_payload_pix` | `pix.py:32-40` (`db.get_value` em `Company`) | só gera o payload da chave Pix; a chave é feita para ser exibida, risco baixo |

`_empresa()` (`navegador_estoque.py:48-50`) aceita a empresa que o cliente mandar e só cai no padrão do usuário se vier vazia. Os 3 primeiros são o risco maior. Correção natural: `frappe.get_list` ou `frappe.has_permission(..., throw=True)` na empresa e no armazém.

### RT-06 — eventos de CT-e e MDF-e usam o fuso do sistema operacional, a emissão usa o do site — **Médio**

`eventos_cte.py:80` e `eventos_mdfe.py:74` usam `datetime.now().astimezone()`, que é o fuso do servidor. `configuracao_fiscal.py:179-187` (`agora_da_emissao`) usa o fuso do site e diz no docstring que é "não o do servidor". Em servidor em UTC (típico de contêiner), `dhEvento` sai com `+00:00`, e `eventos_mdfe.py:206` calcula `data_encerramento` com `_agora().date()`, que vira o dia seguinte entre 21h e 24h no horário de Brasília. Só aparece em site real; **a verificar** em bench com o servidor em UTC.

### RT-08 — nove módulos de `integracao/` sem nenhuma referência em teste — **Médio**

Nome do módulo ausente de `tests/` e `tests_bench/`: `cobranca_documento`, `ecf_dados_empresa`, `efd_dados_cadastrais`, `eventos_sefaz_mdfe`, `importar_codigos`, `inutilizacao_sefaz`, `repositorio_frappe`, `seed_codigos`, `transporte_pagamento`. Oito são exercitados por outros módulos (confirmado por `grep`); `importar_codigos` (293 linhas, dois métodos `@frappe.whitelist()`, vários `ignore_permissions`) só é citado em docstring de `fiscal/cfop.py`. `repositorio_frappe` é o adaptador que implementa os `Protocol`s da regra pura e não tem teste direto. O `scripts/cobertura_de_bench.py` não pega isto porque olha só os módulos ligados no `hooks.py`.

## Registros sem achado

- Os 28 `ignore_permissions` ficam em gravações do próprio app (registro de transmissão, número fiscal, bloqueio, seed). Os de `importar_codigos` estão atrás de `frappe.only_for` (linhas dos métodos 156 e 249). Exceção: RT-02.
- `db.commit()` aparece em 8 pontos, todos em fluxo de emissão e evento, antes do `throw`, conforme o travado em `tests/test_emissao_commit_antes_do_throw.py`.
- `montar_lote` (eSocial) não checa permissão no método, mas `evento_do_holerite` faz `holerite.check_permission("read")` (`folha_esocial.py`, por holerite) e o `insert()` do lote respeita a permissão do DocType. Sem achado.
