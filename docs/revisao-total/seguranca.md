# Revisão total — segurança

Versão `0.227.0`, 2026-10-11. Cobre a tarefa 3.9 do change `revisao-total-erpnext-brasil`.

## Cobertura

Varredura por `grep` e `ast` em `erpnext_brasil/` fora de testes, e leitura dos pontos que ela destacou. Não revisei o fluxo do certificado A1 (`carregar_certificado_da_empresa`) por dentro.

## Sem ocorrência

| Busca | Resultado |
|---|---|
| `eval(`, `exec(`, `pickle.`, `yaml.load(`, `shell=True`, `os.system`, `subprocess` | nenhuma |
| `verify=False`, `CERT_NONE`, `check_hostname` | nenhuma |
| atribuição de `password`, `senha`, `secret`, `token` a literal | nenhuma |
| `logger`, `print` ou `log_error` com `senha`, `pfx`, `password` | nenhuma |
| SQL com valor do usuário concatenado | nenhum (3 `db.sql`, todos parametrizados) |

## Achados

### RT-02 — `gerar_efd` sem permissão — **Alto**

Ver [`integracao.md`](integracao.md).

### RT-03 — leituras sem permissão — **Médio**

Ver [`integracao.md`](integracao.md).

### RT-05 — 14 pontos de `etree.fromstring` sem parser endurecido — **Médio**

`etree.fromstring(bruto)` com o parser padrão em `fiscal/documento/evento.py:359`, `inutilizacao.py:274`, `leitura_nfe.py:261`, `resposta_cte.py:99` e `:178`, `resposta_mdfe.py:142`, `resposta_sefaz.py:93`, `soap.py:107`, `folha/esocial_retorno_leitura.py:54`, `esocial_soap.py:124`, `integracao/assinador_esocial.py:57` e `:102`, `assinador_local.py:136` e `:183`. Nenhum usa `XMLParser(resolve_entities=False, no_network=True, huge_tree=False)`.

- **Entrada do usuário:** `importar_nfe(doctype, name, xml)` (`entrada_nfe.py:114`) recebe o XML pelo cliente e chega em `leitura_nfe.py:261`. As demais fontes são respostas de SEFAZ.
- **Teste feito:** no `lxml 6.1.3` desta máquina, entidade externa (`file:///`) **não** é resolvida e entidade interna aninhada expande (teste com três níveis devolveu o texto expandido). Ou seja, a leitura de arquivo local não funciona nesta versão, e a expansão interna segue limitada pelos limites padrão do `lxml`.
- **O risco real é a versão:** o app declara piso `>=15` e herda o `lxml` do Frappe; em `lxml` antigo (< 5) o padrão resolvia entidades. **A verificar** a versão instalada no bench-16 e o piso. Correção barata: um parser único, central, usado nos 14 pontos.

### RT-19 — `ignore_permissions` em 28 pontos sem inventário — **Baixo**

Os usos em `numeracao_fiscal`, `consumo_indevido`, `emissao_*`, `eventos_*`, `inutilizacao_fiscal`, `transmissao_lote_esocial`, `depreciacao_ativo`, `notificacao`, `seed_codigos` e `importar_codigos` são gravações do próprio app depois de uma checagem a montante, exceto RT-02. Vale um teste que falhe se aparecer um `ignore_permissions` novo em método `@frappe.whitelist()` sem `check_permission` antes.

## Fora do escopo

Dependência vulnerável da pilha (`pdfkit`): ver [`pilha-ci.md`](pilha-ci.md).
