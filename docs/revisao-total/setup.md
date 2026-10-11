# Revisão total — setup e instalação

Versão `0.227.0`, 2026-10-11. Cobre a tarefa 3.6 do change `revisao-total-erpnext-brasil`.

## Cobertura

- **Lido:** `setup/install.py` (`after_install`, `after_migrate`, `criar_campos_fiscais`, `revalidacao_quebra_neste_banco`), `hooks.py` (ligações de instalação), `patches.txt`.
- **Varrido por `ast`:** campos declarados (240 nomes) contra os usados pela integração (ver [`integracao.md`](integracao.md)).
- **Não lido:** `campos.py` e `campos_documento.py` campo a campo; `modelo_de_endereco.py`; `locale/`.
- **Não executado:** `bench install-app` e `bench migrate` (sem bench nesta revisão).

## Verificado

- `after_migrate` repete a criação dos campos de propósito e `create_custom_fields(update=True)` é idempotente (docstring de `install.py:1-9`).
- `criar_campos_fiscais` filtra DocType ausente (`Salary Component` vem do `hrms`, opcional) em vez de exigir o app (`install.py:130-141`), o que permite instalar o bloco fiscal num site sem RH.
- O contorno de PostgreSQL (`ignore_validate` quando `db_type == "postgres"`) está explicado com a causa lida na fonte do Frappe 16.31 e a prova em `v16pg.localhost`. É defeito do framework, não do app, e a regra do projeto manda devolver ao upstream: **a verificar** se já existe patch em `contrib/` para esse caso.
- Há um único patch registrado (`v0_177_renomear_campos_com_prefixo_br`); o piso declarado é `>=15`, e o patch é de renomeação de campo, não de dado fiscal.

## Achados

### RT-15 — `after_install` e `after_migrate` têm corpo idêntico — **Baixo**

`install.py:21-37`: as duas funções chamam as mesmas seis rotinas na mesma ordem. Se alguém acrescentar uma sétima em uma e esquecer da outra, a instalação nova e o site migrado divergem sem erro. Basta `after_install` chamar `after_migrate`, ou ambas chamarem uma função só. Sem efeito hoje.

### RT-16 — instalação e migração só provadas em bench, e o CI não roda bench — **Médio (declarado)**

Nada em `setup/` roda no CI. A prova é `tests_bench/`, local. Ver [`pilha-ci.md`](pilha-ci.md).
