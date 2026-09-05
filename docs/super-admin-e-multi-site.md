# O "super admin" do ERPNext, e como administrar vários sites

Quem manda em um site, quem manda em vários, e por que **não existe** um administrador
único de todos.

Verificado no código do Frappe em 2026-09-05.

## ⚠️ A resposta curta, antes de tudo

**Não existe super admin entre sites no Frappe.** Cada site tem o seu próprio banco de
dados, o seu próprio usuário `Administrator` e a sua própria senha. Nenhuma tela do Desk
enxerga outro site.

Quem administra vários sites o faz **por fora**: pela linha de comando (`bench`), com acesso
ao servidor. Isso não é limitação a contornar — é a mesma separação que faz um cliente não
ver o dado do outro (ver [multi-tenant.md](multi-tenant.md)).

---

## Os três níveis de poder

| Nível | Quem é | Alcance | Onde vive |
|---|---|---|---|
| **`Administrator`** | usuário embutido de cada site | **um** site, tudo dentro dele | banco daquele site |
| **`System Manager`** | papel atribuível a pessoas reais | um site, quase tudo | banco daquele site |
| **Quem opera o `bench`** | conta do sistema operacional | **todos** os sites do servidor | shell |

### `Administrator` — o atalho que pula toda verificação

Não é "um usuário com todos os papéis". É um **caso especial no código**: várias funções de
`frappe/permissions.py` verificam o nome do usuário e devolvem permitido antes de olhar
papel nenhum (linhas 108, 309 e 554), e `frappe.only_for` faz o mesmo em
`frappe/__init__.py`.

Consequências práticas:

- **Tirar papéis do `Administrator` não restringe nada.** A verificação não passa por papel.
- **Testar permissão logado como `Administrator` não prova nada** — tudo passa. Para
  conferir o que um usuário comum vê, é preciso entrar com a conta dele.
- ⚠️ **Em `developer_mode`, o `Administrator` grava arquivo no disco do app.** Um relatório
  salvo por ele vira `is_standard: "Yes"` e é exportado para dentro do app — ver
  [relatorios.md](relatorios.md). Só acontece com essa combinação.

A senha se define na criação do site (`--admin-password`) e se troca com:

```bash
bench --site meu-site.localhost set-admin-password
```

### `System Manager` — o administrador do dia a dia

É o papel que se dá a uma pessoa real. Faz quase tudo dentro do site: usuários, papéis,
configurações, importação. **Não** é caso especial no código — obedece a permissões, e
portanto pode ser restringido.

É com ele que se deve trabalhar. O `Administrator` fica para recuperação e manutenção,
como o `root`.

---

## Administrando vários sites: o `bench`

Todo comando é *por site*, e `--site all` percorre todos (`frappe/utils/bench_helper.py`,
linha 122):

```bash
bench --site all migrate                   # atualiza o esquema de todos
bench --site all backup                    # backup de todos
bench --site meu-site.localhost console    # shell Python dentro de um site
bench --site meu-site.localhost mariadb    # cliente SQL daquele banco
```

Criar e remover:

```bash
bench new-site cliente.exemplo.br \
    --install-app erpnext --install-app erpnext_brasil \
    --admin-password '...' --db-root-password '...'

bench drop-site cliente.exemplo.br         # ⚠️ apaga o banco
```

⚠️ **`--site all` num comando que muda dado é o botão mais perigoso do bench.** Um
`migrate` que quebra num app roda em todos os sites antes de alguém perceber. Backup antes,
e — se possível — um site de teste primeiro.

### O que o `bench` **não** dá

- **Painel.** Não há tela listando sites, uso ou usuários. Só `ls sites/` e a linha de
  comando.
- **Login unificado.** Entrar como administrador de dez sites são dez senhas.
- **Relatório consolidado.** Um relatório do Frappe consulta **um** banco. Somar todos os
  clientes exige processo próprio lendo cada site.

Quem quer painel usa **Frappe Cloud** (serviço pago dos próprios mantenedores) ou constrói.
Ver [hospedagem-demonstracao.md](hospedagem-demonstracao.md).

---

## Multiempresa é outra coisa

Vale repetir porque a confusão é frequente e cara:

- **Vários sites** = vários bancos, clientes que não se conhecem. Administração pelo
  `bench`.
- **Várias `Company` num site** = um banco, várias empresas do **mesmo** grupo, que
  compartilham cadastro de item e cliente. Administração pelo Desk, por um `System Manager`.

Para várias filiais/CNPJ do mesmo dono, a resposta quase sempre é **`Company`**, não site
novo — e a configuração fiscal deste app já é por `Company`, então funciona sem alteração.
Detalhes em [multi-tenant.md](multi-tenant.md).

---

## Recomendação

1. **Ninguém trabalha como `Administrator`.** Crie contas nomeadas com `System Manager` — o
   `Version` grava quem alterou, e "Administrator" não responde essa pergunta.
2. **Senha do `Administrator` diferente por site**, guardada em cofre. Ela ignora toda
   permissão.
3. **Acesso ao `bench` é acesso a todos os clientes.** Trate a conta do servidor como o
   ativo mais sensível da operação — mais que qualquer senha do Desk.
4. **Backup antes de todo `--site all`.**
5. **Teste permissão com usuário comum**, nunca com `Administrator`.

## Fontes

- `frappe/permissions.py` — `Administrator` como caso especial (linhas 108, 309, 554).
- `frappe/__init__.py` — `only_for` liberando o `Administrator`.
- `frappe/utils/bench_helper.py` — `--site all`.
- `frappe/commands/site.py` — `set-admin-password`, `new-site`, `drop-site`.
- `frappe/installer.py` — `admin_password` na criação do site.
