# Multiempresa e multi-site no ERPNext

Como atender mais de uma empresa, e a distinção que decide tudo o mais.

Verificado no código do Frappe e do ERPNext em 2026-09-05, não em documentação de
terceiros.

## ⚠️ "Multi-tenant" nomeia duas coisas incompatíveis

Quase toda confusão sobre o assunto vem de usar a mesma palavra para dois arranjos que
não se parecem:

| | **Multi-site** | **Multiempresa (multi-company)** |
|---|---|---|
| Banco de dados | **um por site** | **um só, compartilhado** |
| Isolamento | total | por permissão |
| Cadastros (item, cliente) | separados | **compartilhados por padrão** |
| Plano de contas | um por site | um por `Company` |
| Backup/restauração | por cliente | tudo junto |
| Atualização de versão | site a site | todos de uma vez |
| Custo por cliente | maior | menor |

**Não são alternativas de gosto.** São respostas a perguntas diferentes:

- *"Atendo clientes distintos que não podem se ver"* → **multi-site**.
- *"Uma empresa com filiais ou CNPJs do mesmo grupo, que compartilham cadastro"* →
  **multiempresa**.

Escolher errado é caro nos dois sentidos: multi-site para filiais do mesmo grupo obriga a
recadastrar item e cliente em cada uma; multiempresa para clientes distintos os deixa
enxergando os cadastros uns dos outros, com um controle de permissão como única barreira.

---

## Multi-site: um bench, vários bancos

### Como o Frappe decide de que site é a requisição

Pelo cabeçalho **`Host`** do HTTP. Em `frappe/app.py`:

```python
site = _site or request.headers.get("X-Frappe-Site-Name") or get_site_name(request.host)
```

E `get_site_name` é só `hostname.split(":", 1)[0]` — o host sem a porta. Consequências
práticas:

- **O nome da pasta do site em `sites/` é o domínio.** `sites/cliente-a.com.br/` responde
  por `cliente-a.com.br`. É por isso que os sites de desenvolvimento se chamam
  `algo.localhost`.
- **`X-Frappe-Site-Name` tem prioridade sobre o `Host`.** Útil atrás de proxy, e é
  também a razão de o proxy precisar ser confiável: quem controla esse cabeçalho escolhe
  o site.
- **`currentsite.txt`** define o site padrão para a linha de comando e para quando
  `serve_default_site` está ligado.

### Os dois modos do nginx

`bench setup nginx` gera configuração diferente conforme `dns_multitenant`:

- **`dns_multitenant: true`** — um `server_name` por site, todos na porta 80/443. É o
  arranjo normal em produção: cada cliente tem seu domínio.
- **`dns_multitenant: false`** (padrão) — **uma porta por site**, lida de `port` no
  `site_config.json`. Serve para desenvolvimento e para quando não há DNS.

```bash
bench config dns_multitenant on
bench setup nginx
```

### O que é isolado, e o que não é

**Isolado por site:** banco de dados, arquivos (`sites/<site>/private` e `public`),
`site_config.json`, `encryption_key` (a chave que decifra os campos `Password` — inclusive
a senha do certificado A1), apps instalados, usuários e permissões.

**Compartilhado pelo bench:** o código dos apps, o ambiente Python, o Redis, o scheduler e
os workers de fila. Isso importa: **atualizar o app atualiza todos os sites**, e um
`bench migrate` mal-sucedido afeta o conjunto.

### Criando

```bash
bench new-site cliente-a.com.br --install-app erpnext --install-app erpnext_brasil
bench --site cliente-a.com.br add-to-hosts     # só em desenvolvimento
```

---

## Multiempresa: um site, várias `Company`

O ERPNext trata `Company` como dimensão de quase toda transação. Criar a segunda empresa é
só criar o registro; o que exige atenção é o **isolamento**, que não vem de graça.

### Cadastros são compartilhados por padrão

`Item`, `Customer` e `Supplier` **não têm** campo `Company` — são globais no site. Para
restringir, o ERPNext oferece o DocType **`Company Restriction`**, ligado por
`permission_query_conditions` e `has_permission` (ver `erpnext/hooks.py`):

```python
permission_query_conditions = {
    "Item": "...company_restriction.get_permission_query_conditions",
    "Customer": "...",
    "Supplier": "...",
}
```

Detalhe que decide o comportamento: **sem restrição cadastrada, o registro é visível para
todos**. `get_permission_query_conditions` devolve `None` quando não há empresa permitida
listada, e `None` significa "sem filtro". Ou seja, o isolamento é **opt-in por registro** —
esquecer de restringir não gera erro, gera visibilidade.

### O que já é separado por `Company`

Plano de contas, exercícios fiscais, depósitos, séries de numeração do ERPNext, e todas as
transações. Relatórios financeiros filtram por empresa.

---

## O que isso significa para o `erpnext_brasil`

### A configuração fiscal é por `Company`, e isso é deliberado

Todo dado fiscal sensível vive na `Company`, não no site:

| Campo | Por quê |
|---|---|
| `br_certificado_a1` + senha | cada CNPJ tem o seu; é a identidade perante o Fisco |
| `br_csc_nfce` + `br_csc_id_nfce` | emitido pela SEFAZ para aquele estabelecimento |
| `br_ambiente_sefaz` | uma empresa pode homologar enquanto outra já produz |
| `br_serie_nfe`, `br_serie_cte`… | a série pertence ao estabelecimento |
| `regime_tributario` | decide o CRT e a apuração de PIS/COFINS |

Consequência: **multiempresa funciona sem alteração no app**. Duas `Company` no mesmo site
emitem com certificados diferentes, séries diferentes e até em ambientes diferentes.

### A numeração fiscal é travada por empresa + modelo + série

`Numeracao Fiscal` tem `autoname: format:{company}-{modelo}-{serie}`, e
`integracao/numeracao_fiscal.py` trava **essa linha** com `SELECT ... FOR UPDATE`.

O efeito em multiempresa é o que se quer: duas empresas emitindo ao mesmo tempo **não
esperam uma pela outra**, porque travam linhas diferentes; duas emissões da mesma empresa e
série serializam, que é exatamente o necessário para a sequência não repetir número.

### Os registros fiscais carregam `Company`

`Transmissao Fiscal`, `Arquivo SPED`, `Lote eSocial` e `Numeracao Fiscal` têm o campo — o
que permite filtrar e, se for o caso, restringir por permissão. `Evento do Lote eSocial` não
tem, e não deve: é tabela filha, e a empresa é do pai.

### O EFD é por empresa

`gerar_efd(company, address, data_inicial, data_final)` recebe a empresa e o **endereço**,
porque a escrituração é do **estabelecimento**, não da pessoa jurídica: uma empresa com duas
inscrições estaduais entrega dois arquivos. É por isso que o endereço não é deduzido —
`docs/gaps.md` e `integracao/geracao_efd.py` registram o motivo.

---

## Como escolher

**Use multi-site quando:**

- os clientes são pessoas jurídicas sem relação entre si (caso do contador ou do provedor
  de SaaS);
- exigem backup e restauração independentes;
- podem precisar de versões diferentes do app, ou de atualizar em datas diferentes.

**Use multiempresa quando:**

- são filiais ou empresas do mesmo grupo;
- compartilham cadastro de item, cliente e fornecedor;
- alguém precisa de relatório consolidado.

**Combine os dois** quando um cliente do seu multi-site tiver várias empresas — é o arranjo
mais comum em serviço de contabilidade.

### ⚠️ Para uso fiscal, um alerta

Em **multiempresa**, o certificado A1 de cada `Company` fica acessível a quem tiver
permissão de leitura naquela empresa. O Frappe cifra a senha (campo `Password`, com a
`encryption_key` do site), mas **a mesma chave decifra tudo do site**. Se a exigência é
que o certificado de um cliente não seja alcançável por outro **nem em caso de falha de
permissão**, o arranjo correto é **multi-site**: aí a chave é outra, e o banco também.

## Fontes

- `frappe/app.py` e `frappe/utils/__init__.py` (`get_site_name`) — resolução do site pelo
  cabeçalho `Host`.
- `bench/config/nginx.py` — os dois modos de `dns_multitenant`.
- `erpnext/hooks.py` e `erpnext/stock/doctype/company_restriction/` — restrição de
  cadastros por empresa.
- Documentação oficial: <https://docs.frappe.io/framework/user/en/introduction>.
