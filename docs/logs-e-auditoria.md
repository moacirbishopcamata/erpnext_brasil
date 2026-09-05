# Logs e auditoria no ERPNext

O que o Frappe registra sozinho, o que precisa ser ligado, e o que **não** existe.

Verificado no código do Frappe em 2026-09-05.

## ⚠️ Log e auditoria não são a mesma coisa

Confundi-los é o erro que faz alguém achar que tem trilha de auditoria quando tem só
diagnóstico:

- **Log** responde *"o que o sistema fez?"* — para quem depura. É descartável, tem
  retenção curta, e o conteúdo é técnico.
- **Auditoria** responde *"quem mudou o quê, quando?"* — para quem presta contas. Precisa
  sobreviver, ser legível e não depender de o desenvolvedor ter lembrado de escrever.

O Frappe tem os dois, com mecanismos diferentes. E num app fiscal a distinção pesa: uma
nota alterada antes da transmissão é fato que alguém pode precisar explicar ao Fisco.

---

## Auditoria: `Version` é o coração

### Como funciona

Todo DocType com `track_changes: 1` gera um registro **`Version`** a cada alteração
(`frappe/model/document.py`, por volta da linha 2039). O `Version` guarda o **diff** —
campo, valor antigo, valor novo — e mais as linhas de tabela filha adicionadas e removidas.

Não é opcional por campo nem depende de código: o framework compara o documento antes e
depois e grava a diferença.

```json
// no <doctype>.json
"track_changes": 1
```

Os quatro DocTypes de nível superior deste app já têm — `Transmissao Fiscal`,
`Lote eSocial`, `Arquivo SPED` e `Numeracao Fiscal`.

`Evento do Lote eSocial` está com `track_changes: 0` **de propósito**: é tabela filha
(`istable: 1`), e o framework registra linhas de filha adicionadas e removidas no `Version`
**do pai**. Ligar no filho duplicaria o registro sem acrescentar informação.

### Onde se lê

- **Na aba "Activity" / "Versions"** de cada documento, na interface.
- **`Audit Trail`** (`frappe/core/doctype/audit_trail/`) — uma tela *single* que consulta
  os `Version` por DocType e documento, mostrando também linhas adicionadas e removidas.
  É **relatório**, não armazenamento: apagar os `Version` esvazia a tela.

### O que ele **não** registra

- **Leitura.** Quem *viu* um documento não fica registrado por aqui — só quem exportou
  (ver `Access Log` abaixo).
- **Alterações feitas por SQL direto.** `frappe.db.sql("UPDATE ...")` não passa pelo
  `Document`, e portanto não gera `Version`. É a razão de este projeto usar
  `doc.db_set(...)` e `frappe.get_doc(...)` em vez de SQL de escrita.
- **Documento apagado** deixa os `Version` órfãos, mas o conteúdo do último estado não é
  preservado em lugar nenhum.

---

## Os registros que o Frappe mantém

| DocType | Registra | Quem escreve |
|---|---|---|
| **`Version`** | diff de cada alteração | automático, com `track_changes` |
| **`Activity Log`** | login, logout, e eventos de comunicação | automático |
| **`Access Log`** | **exportações** — quem baixou qual relatório ou documento | automático |
| **`Permission Log`** | mudanças em permissão de papel | automático |
| **`Error Log`** | exceções não tratadas e `frappe.log_error` | automático + manual |
| **`Scheduled Job Log`** | execução de tarefa agendada | automático |
| **`API Request Log`** | chamadas à API REST | precisa ser ligado |
| **`Route History`** | navegação do usuário no Desk | automático |

O **`Access Log`** costuma ser o mais subestimado: em contexto fiscal, saber **quem exportou
a base de clientes** é a pergunta que aparece depois do problema.

---

## Logging para código próprio

### `frappe.logger` — arquivo, para diagnóstico

```python
import frappe

logger = frappe.logger("erpnext_brasil", allow_site=True)
logger.info("lote %s transmitido, protocolo %s", lote.name, protocolo)
```

- Escreve em `sites/<site>/logs/<módulo>.log`, com rotação (padrão: 100 KB, 20 arquivos).
- `allow_site=True` separa por site — importante em multi-site, senão logs de clientes
  diferentes se misturam no mesmo arquivo.
- **Não vai para o banco**, então não aparece na interface e não é auditoria.

### `frappe.log_error` — banco, para o que precisa ser visto

```python
frappe.log_error(
    title="Falha ao transmitir NF-e",
    message=frappe.get_traceback(),
    reference_doctype="Sales Invoice",
    reference_name=doc.name,
)
```

Cria um `Error Log`, visível na interface e **ligado ao documento** pelos campos de
referência — o que permite chegar nele a partir da nota.

⚠️ **Armadilha real do parâmetro**: o próprio código do Frappe avisa que "title e message
podem estar trocados", e tenta adivinhar qual é qual pela presença de quebra de linha
(`frappe/utils/error.py`). Use os argumentos **nomeados** e o problema não existe.

### O que este app faz hoje

`emissao_nfe.emitir_nfe` **não** usa `log_error`: grava um `Transmissao Fiscal` com a
resposta da SEFAZ, inclusive na rejeição. É deliberado — rejeição é **resultado**, não erro
de programa, e um `Error Log` a trataria como defeito. O registro fica onde o usuário
procura, com os dois XML.

---

## Retenção: os logs são apagados sozinhos

O DocType **`Log Settings`** define, por tipo de log, quantos dias guardar (tabela filha
`Logs to Clear`, com `ref_doctype` e `days`). Uma tarefa diária remove o excedente.

⚠️ **`Version` também pode ser incluído ali.** Se alguém puser `Version` no `Log Settings`
com 30 dias, a trilha de auditoria passa a ter 30 dias — sem aviso, sem erro, e ninguém
percebe até precisar de um histórico antigo.

Para exigência fiscal, o prazo de guarda é de **cinco anos**. Conferir o `Log Settings`
antes de confiar no histórico é parte de colocar em produção.

---

## O que **não** existe

- **Trilha de auditoria assinada ou imutável.** `Version` é um DocType comum: quem tem
  permissão de exclusão no banco apaga. Não há encadeamento por hash nem assinatura. Se a
  exigência for prova contra adulteração interna, isso precisa vir de fora — backup
  externo, replicação para banco somente-leitura, ou trilha própria.
- **Registro de leitura.** Só exportação (`Access Log`).
- **Auditoria consolidada entre sites.** Cada site tem os seus, isolados — ver
  [multi-tenant.md](multi-tenant.md).

## Recomendação para uso fiscal

1. **Manter `track_changes` ligado** em todo DocType que carregue dado fiscal.
2. **Conferir o `Log Settings`** e garantir que `Version` **não** está na lista de expurgo.
3. **Vigiar o `Access Log`** — exportação de base é o evento que mais interessa depois.
4. **Não escrever com SQL direto** em tabela de documento: o que não passa pelo `Document`
   não deixa rastro.
5. **Backup fora do servidor.** A auditoria só vale se sobreviver a quem tem acesso ao
   banco.

## Fontes

- `frappe/model/document.py` — criação de `Version` a partir de `track_changes`.
- `frappe/utils/error.py` — `log_error` e a advertência sobre os parâmetros trocados.
- `frappe/__init__.py` — `frappe.logger`, com rotação e `allow_site`.
- `frappe/core/doctype/` — `audit_trail`, `access_log`, `activity_log`, `permission_log`,
  `log_settings`, `logs_to_clear`.
