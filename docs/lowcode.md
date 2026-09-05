# O lowcode do Frappe, e como ele convive com o `erpnext_brasil`

O que dá para fazer sem programar, onde isso colide com o app, e a regra que evita perder
trabalho no próximo `bench migrate`.

Verificado no código do Frappe em 2026-09-05.

## ⚠️ A regra que importa antes de qualquer coisa

Este app declara **223 campos customizados em 18 DocTypes** (`setup/custom_fields.py`) e os
reaplica a **toda** migração — `after_migrate` chama `create_custom_fields(..., update=True)`
(`setup/install.py`).

Portanto:

> **Alterar pela interface um campo que o `erpnext_brasil` declara é trabalho perdido.** O
> próximo `bench migrate` sobrescreve a alteração, sem aviso e sem erro.

Isso não é defeito: é o mecanismo que garante que o campo volte quando o ERPNext mexe no
DocType base. Mas dita a fronteira:

| O que você quer mudar | Onde fazer |
|---|---|
| campo fiscal que o app criou | **no código**, em `setup/custom_fields.py` |
| campo seu, que o app não conhece | à vontade pela interface |
| rótulo, ordem ou obrigatoriedade de campo do app | no código — a UI é desfeita |
| campo do ERPNext que o app não toca | à vontade pela interface |

### Como saber se um campo é do app

⚠️ **O prefixo `br_` não é critério suficiente.** Ele cobre 169 dos 223 campos; os outros
têm nomes genéricos justamente por serem conceitos que o ERPNext já deveria ter —
`bairro`, `numero_endereco`, `ncm`, `cest`, `inscricao_estadual`, `inscricao_municipal`,
`regime_tributario`, `codigo_municipio_ibge`, `origem_mercadoria`, `suframa`, entre outros.

A verificação que não erra:

```bash
bench --site meu-site.localhost console
```

```python
from erpnext_brasil.setup.custom_fields import get_custom_fields

campos = get_custom_fields()
{f["fieldname"] for lista in campos.values() for f in lista}
```

Se o `fieldname` está nesse conjunto, ele é do app: **mude no código, não na tela.**

⚠️ E o inverso também vale: ao criar um campo seu, **não use nome genérico**. Um
`ncm` criado à mão colide com o do app, e quem ganha é o `after_migrate`. Use um prefixo
próprio da empresa (`acme_...`).

---

## As ferramentas, e quando cada uma serve

| Ferramenta | O que faz | Precisa de papel especial? |
|---|---|---|
| **Customize Form** | mudar rótulo, ordem, obrigatoriedade de DocType existente | não |
| **Custom Field** | acrescentar campo | não |
| **Property Setter** | o registro que o Customize Form grava | — |
| **Client Script** | JavaScript no formulário/lista | Script Manager |
| **Server Script** | Python no servidor | Script Manager **e** configuração do site |
| **Workflow** | estados e transições com aprovação | não |
| **Notification** | e-mail/alerta ao acontecer algo | não |
| **Assignment Rule** | atribuir documento a pessoas por regra | não |
| **Auto Repeat** | recriar documento periodicamente | não |
| **Print Format Builder** | leiaute de impressão, arrastando | não |
| **Web Form** | formulário público no site | não |
| **Report Builder** | relatório sem código | não — ver [relatorios.md](relatorios.md) |

### Customize Form — o mais usado, e o mais perigoso aqui

Não altera o DocType original: grava **`Property Setter`**, uma sobreposição. Por isso a
atualização do ERPNext não apaga o que você fez.

Mas ele **não** protege contra o `after_migrate` deste app: são mecanismos diferentes, e o
nosso escreve por último.

**Casos legítimos**: esconder campo que a empresa não usa, mudar rótulo para o vocabulário
da casa, tornar obrigatório um campo do ERPNext.

### Client Script — JavaScript no formulário

Um documento `Client Script` com `dt` (o DocType), `view` (Form ou List) e o JS.

⚠️ **É código sem teste, sem revisão e sem versionamento.** Roda no navegador de todo
usuário daquele DocType. Para comportamento que pertence ao app, o lugar certo é um arquivo
`.js` declarado em `doctype_js` no `hooks.py` — que entra no git.

Client Script serve para o ajuste de um cliente específico, que não deve ir para o app.

### Server Script — Python, e a trava que quase ninguém encontra

Um `Server Script` pode ser de cinco tipos: **DocType Event**, **Scheduler Event**,
**Permission Query**, **API** e **Workflow Task**.

⚠️ **Ele não funciona até alguém editar um arquivo no servidor.** Só liga por
`server_script_enabled` no `common_site_config.json` (`is_safe_exec_enabled`, em
`frappe/utils/safe_exec.py`) — e o comentário no próprio código diz que é de propósito:
*"server scripts can only be enabled via common_site_config.json"*.

```bash
bench --site meu-site.localhost set-config server_script_enabled true
```

É por isso que o botão existe na interface mas o script "não faz nada": ninguém ligou a
chave. E ligar é decisão de segurança — passa a permitir Python arbitrário (ainda que em
ambiente restrito, via `safe_exec`) a quem tiver **Script Manager**.

Um Server Script de `DocType Event` compete com os `doc_events` deste app. Ambos rodam; a
ordem entre eles não é garantia sobre a qual convém apoiar regra fiscal.

> **Recomendação deste projeto: regra fiscal nunca em Server Script.** Cálculo de imposto,
> montagem de documento e numeração vivem no código, com teste. O que o Fisco cobra não
> pode depender de um script que ninguém revisou e que não está no git.

### Workflow — aprovação sem escrever código

Estados (`Workflow Document State`) e transições (`Workflow Transition`), cada transição
condicionada a um papel. É a maneira certa de exigir que alguém aprove antes de emitir.

Combina bem com o app: um workflow que só permite **Submit** da `Sales Invoice` depois da
conferência fiscal é configuração, não código.

### Notification, Assignment Rule, Auto Repeat

- **Notification** — dispara e-mail/alerta em evento de documento ou por data. Bom para
  "certificado A1 vence em 30 dias" — embora este app já tenha alerta próprio
  ([leitor-codigo-e-alertas.md](leitor-codigo-e-alertas.md)).
- **Assignment Rule** — distribui documento entre pessoas (rodízio, carga, round-robin).
- **Auto Repeat** — recria documento periodicamente. ⚠️ Em documento fiscal, cuidado:
  recriar nota não é recriar obrigação, e a numeração é controlada pelo app.

### Web Form e Print Format Builder

- **Web Form** publica formulário no site, gravando num DocType. Útil para cadastro de
  cliente. ⚠️ `allow_guest` expõe à internet — pense em spam e LGPD antes.
- **Print Format Builder** monta leiaute arrastando campos. Serve para pedido e orçamento.
  ⚠️ **Não serve para DANFE**: a representação gráfica da NF-e tem leiaute normatizado, não
  é formato de impressão livre.

---

## Exemplo completo: conferência fiscal antes de faturar

Um problema real e pequeno: **ninguém deve enviar a nota antes de alguém do fiscal
conferir**. Resolve-se sem uma linha no repositório, em três passos e uns dez minutos.

O exemplo usa prefixo `acme_` de propósito — é campo da empresa, não do app.

### Passo 1 — o campo (Custom Field)

**Menu → Customize Form → Sales Invoice → Add Row**, no fim da lista de campos:

| Propriedade | Valor |
|---|---|
| Label | `Conferência fiscal feita` |
| Type | `Check` |
| Name (fieldname) | `acme_conferencia_fiscal` |
| Insert After | um campo do fim do formulário |
| Allow on Submit | **desmarcado** |
| No Copy | **marcado** (não herda ao duplicar) |

⚠️ **`No Copy` importa.** Sem ele, duplicar uma nota conferida traz a marca junto, e a
segunda passa sem ninguém olhar. É o tipo de detalhe que transforma um controle em teatro.

### Passo 2 — a regra (Workflow)

**Menu → Workflow → New**, sobre `Sales Invoice`:

**Estados** (`Workflow Document State`):

| Estado | docstatus | Papel que edita |
|---|---|---|
| `Rascunho` | 0 (Draft) | Sales User |
| `Aguardando fiscal` | 0 (Draft) | Sales User |
| `Conferida` | 0 (Draft) | Accounts Manager |
| `Emitida` | 1 (Submitted) | Accounts Manager |

**Transições** (`Workflow Transition`):

| De | Ação | Para | Papel | Condição |
|---|---|---|---|---|
| `Rascunho` | Enviar para conferência | `Aguardando fiscal` | Sales User | — |
| `Aguardando fiscal` | Conferir | `Conferida` | Accounts Manager | `doc.acme_conferencia_fiscal` |
| `Conferida` | Emitir | `Emitida` | Accounts Manager | — |

A condição é uma expressão Python sobre `doc`. Aqui ela garante que o passo 1 foi
efetivamente marcado — o workflow sozinho não olharia o campo.

⚠️ **Só existe um workflow ativo por DocType.** Se o cliente já tem um na `Sales Invoice`,
acrescente estados ao existente em vez de criar outro.

### Passo 3 — deixar visível (Client Script)

O workflow já mostra o estado no alto do formulário. O que falta é o aviso **antes** de o
usuário tentar:

**Menu → Client Script → New**, `DocType` = `Sales Invoice`, `View` = `Form`:

```javascript
frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        if (frm.doc.docstatus !== 0) return;
        if (frm.doc.acme_conferencia_fiscal) return;

        frm.dashboard.set_headline(
            __("Pendente de conferência fiscal — não emita antes de o fiscal marcar."),
            "orange"
        );
    },
});
```

`refresh` roda a cada abertura e a cada gravação, então o aviso some sozinho quando a marca
é posta. Nada de `setInterval` nem de observar o campo.

### O que este exemplo deliberadamente **não** faz

- **Não calcula imposto nem monta documento fiscal.** Isso é código no app, com teste — é
  exatamente a linha da seção seguinte.
- **Não usa Server Script.** Não precisa, e evita ligar `server_script_enabled` só por
  causa disto.
- **Não cria campo com nome genérico.** `acme_conferencia_fiscal` não colide com nada do
  app nem do ERPNext.

### Como levar isso para outro site

O que a interface cria vive **no banco daquele site** — não está no git e não vai junto com
o app. Para repetir num segundo site, exporte os documentos criados (Custom Field, Workflow,
Client Script) por **fixtures** ou pelo próprio `bench --site ... export-fixtures`, ou
refaça à mão. Ver [super-admin-e-multi-site.md](super-admin-e-multi-site.md).

Se a regra vale para **todos** os clientes, ela não pertence à tela: pertence ao app.

---

## Como decidir: lowcode ou código?

```
A regra vem de lei/norma fiscal, ou de cálculo que precisa estar certo?
  └─ sim → CÓDIGO, no app, com teste. Sem exceção.
  └─ não → é regra de UM cliente, que não vale para os outros?
             └─ sim → lowcode (Customize Form, Client Script, Workflow)
             └─ não → código no app: se vale para todos, pertence ao repositório
```

O critério é **quem responde se estiver errado**. Tributo errado é autuação — precisa de
teste, revisão e histórico em git. Um campo escondido na tela é preferência.

## Checklist antes de usar lowcode neste app

1. O `fieldname` está em `get_custom_fields()`? **Pare** — é do app, mude no código.
2. É cálculo de imposto ou montagem de documento fiscal? **Pare** — é código.
3. Vale para todos os clientes? Então pertence ao app, não à tela de um.
4. Campo novo leva prefixo da empresa — nome genérico colide com o app.
5. Server Script exige ligar `server_script_enabled` — e isso é decisão de segurança.
6. O que a interface criar **não está no git**: exporte como fixture, ou some no próximo
   site.

## Fontes

- `frappe/custom/doctype/` — `custom_field`, `customize_form`, `property_setter`,
  `client_script`.
- `frappe/core/doctype/server_script/server_script.py` — `only_for("Script Manager")`, os
  cinco tipos de script.
- `frappe/utils/safe_exec.py` — `is_safe_exec_enabled`, ligado só pelo
  `common_site_config.json`.
- `frappe/workflow/doctype/`, `frappe/automation/doctype/`, `frappe/website/doctype/web_form/`.
- `erpnext_brasil/setup/install.py` — `after_migrate` reaplicando os campos com
  `update=True`.
- `erpnext_brasil/setup/custom_fields.py` — `get_custom_fields()`, 223 campos em 18
  DocTypes (contados na versão 0.160.0).
