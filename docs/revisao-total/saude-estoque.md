# Revisão total — saúde e estoque

Versão `0.227.0`, 2026-10-11. Cobre a tarefa 3.7 do change `revisao-total-erpnext-brasil`.

## Cobertura

- **Lido:** `docs/healthcare-estado.md` (cabeçalho e tabela de instalação), `integracao/navegador_estoque.py` (as três consultas e `_empresa`), lista de módulos de `integracao/` e `estoque/`.
- **Varrido:** `grep` por `Healthcare`, `Patient`, `Lab Test` em `erpnext_brasil/` (fora de testes).
- **Não lido:** `valoracao_estoque`, `perda_estoque`, `efd_inventario` e o JavaScript do navegador de estoque.

## Estado da saúde

Não há **nenhum código de saúde** no app: a busca por `Healthcare`, `Patient` e `Lab Test` em `.py`, `.js` e `.json` fora de testes não acha nada. A frente é só levantamento (`docs/healthcare-estado.md`) e proposta (`openspec/changes/integrar-laboratorio-e-imagem`, 46 tarefas, 0 feitas). Isso é coerente com a documentação, e a revisão não achou doc que afirme o contrário.

## Achados

### RT-03 (parcial) — navegador de estoque lê sem checar permissão — **Médio**

As três consultas de `navegador_estoque.py` usam `get_all` ou SQL cru e aceitam a empresa do cliente. Detalhe em [`integracao.md`](integracao.md).

### RT-10 — licença GPL-3.0 do Marley Health contra MIT do app — **Médio (a verificar)**

`docs/healthcare-estado.md` registra que o Marley Health é **GPL-3.0** e o `erpnext_brasil` é MIT. A proposta `integrar-laboratorio-e-imagem` integra os dois. Ligar por `hooks.py`/`doc_events`, sem importar código do Marley, tende a manter os dois separados, mas **a decisão de licenciamento não está registrada** na proposta nem no estado. Precisa de decisão do dono do projeto, e idealmente de parecer jurídico, antes de qualquer código de saúde: se o app passa a importar o Marley, a combinação pode ficar sob GPL.

### RT-17 — instalação do healthcare provada só em PostgreSQL — **Baixo (declarado)**

`docs/healthcare-estado.md`: o app de saúde foi instalado em `hc16pg.localhost` (PostgreSQL). No MariaDB não foi, por falta da senha do root do servidor. O resto do app é provado nos dois bancos; o healthcare não.
