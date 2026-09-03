# Testes reais (bench) de `integracao/party.py`

Segunda cobertura de verdade para um módulo de `integracao/`, depois de
`certificado_a1.py` (`docs/ambiente-dev-bench.md`). Arquivo: `tests_bench/test_party.py`,
8 testes.

## Achado real: `_pais_e_brasil()` não olha as System Settings quando há uma Company padrão

`_pais_e_brasil()` decide pelo país da `Company` em `frappe.local.flags.company` **ou**
pelo default de Company do usuário (`frappe.defaults.get_user_default`) — só cai para o
país das `System Settings` quando nenhuma das duas existir. No bench de teste usado aqui,
o default de Company do usuário é `Wind Power LLC` (país Estados Unidos), mesmo com
`System Settings.country = "Brazil"` configurado no site inteiro — confirmado direto no
console antes de escrever o teste.

Consequência prática, fora do teste: num site com uma Company padrão não-brasileira
configurada, `validar_tax_id`/`validar_ie` não fazem nada para nenhum Customer/Supplier
novo — silenciosamente, sem erro nem aviso — mesmo o sistema inteiro sendo "brasileiro"
nas System Settings. Isso não é um bug deste projeto (a decisão de priorizar a Company
sobre o país do sistema é razoável — cobre matriz estrangeira com filial BR), mas é uma
armadilha de configuração real que só apareceu testando contra um bench de verdade.
Por isso todo teste em `test_party.py` cria sua própria `Company` com `country="Brazil"`
e força `frappe.local.flags.company` explicitamente, em vez de confiar no default do
site.

## Achado real do próprio teste: nem todo CNPJ com dígitos repetidos é inválido

Escrevendo `test_cnpj_invalido_impede_o_insert`, a primeira tentativa usou
`11111111000191` (sequência repetida) como CNPJ inválido — e o teste falhou porque o
CNPJ **passou** na validação. Confirmado depois: os dígitos verificadores desse número
conferem de verdade; `fiscal/validators.py` só rejeita sequência repetida para **CPF**,
não para CNPJ. Corrigido usando `11222333000180` — o mesmo CNPJ-base válido do teste de
sucesso (`11222333000181`), só com o último dígito verificador trocado, que é uma
garantia estrutural de invalidez, não uma suposição sobre o que "parece" inválido.

## Teste de costura, não só de unidade

`test_tax_id_normalizado_sobrevive_ao_insert` e `test_ncm_normalizado_sobrevive_ao_insert`
criam o documento real (`Customer`/`Item`) via `.insert()` — disparando o `doc_events` de
verdade do `hooks.py`, não uma chamada direta à função — e releem o valor por
`frappe.db.get_value`, um caminho independente do objeto que `.insert()` devolveu. Mesma
disciplina que achou os dois bugs de `certificado_a1.py`: nenhum bug de costura apareceu
aqui, mas o teste está desenhado para pegar um se aparecer (ex.: hook que normaliza o
objeto em memória mas não grava a mudança).

## O que fica de fora, deliberadamente

`validar_ie` (Inscrição Estadual) não é coberto — depende de `uf_da_parte`, que por sua
vez depende de um `Address` vinculado com `state` preenchido (`get_default_address`),
uma camada extra de setup que não foi construída nesta rodada. Fica como próximo
candidato natural de expansão de `tests_bench/`.

## Custo de execução: ~9-14s por teste

Cada teste cria e destrói uma `Company` completa (com toda a cascata de contas/centros
de custo/depósitos padrão que o Frappe gera ao inserir uma Company) — por isso a suíte
inteira leva ~80s para 8 testes, ordens de magnitude mais lento que a suíte pura
(1731 testes em ~13s). Aceitável para este módulo: é o preço de testar a costura de
verdade, não motivo para não escrever o teste.
