# Plano de contas: grupos e amarração aos tributos

Primeiro incremento do bloco contábil (`erpnext_brasil/contabil/`), depois que o
usuário confirmou que a frente fiscal (NF-e/NFC-e: montagem, transmissão, eventos,
inutilização, contingência SVC, QR Code) está madura o bastante para seguir adiante —
ver [roteiro-fiscal-depois-contábil na memória do projeto].

## Por que grupos, não uma codificação completa de contas

Diferente do setor público (PCASP, uniforme e obrigatório por lei para todos os entes),
**não existe um plano de contas único obrigatório para empresas privadas no Brasil**.
Cada empresa codifica como quiser dentro dos grupos que a lei exige. Inventar aqui uma
"conta 1.1.1.01.001" seria apostar num nível de detalhe que a lei não fixa e que este
app não tem autoridade para decidir por conta de terceiros.

O que `contabil/plano_de_contas.py` modela são os **grupos exigidos por lei** — Lei
6.404/1976 (Lei das S.A., aplicada às demais sociedades por remissão do Código Civil),
Art. 178 (balanço) e Art. 187 (demonstração do resultado) — mais as contas de tributo que
a camada fiscal já sabe calcular (`fiscal/impostos/`).

## Fonte primária inacessível

`planalto.gov.br` não respondeu às tentativas de acesso no momento da implementação
(mesma limitação já registrada para o Portal Nacional da NF-e em outros documentos deste
projeto). O texto dos Art. 178 e 187 foi confirmado em duas fontes secundárias
independentes que reproduzem a lei na íntegra (não paráfrase/resumo) — dito
explicitamente por ser exatamente a situação que a política deste projeto pede para não
esconder.

### Art. 178 — grupos do balanço

- **Ativo**: `Ativo Circulante` e `Ativo Não Circulante` (subdividido em `Ativo
  Realizável a Longo Prazo`, `Investimentos`, `Imobilizado`, `Intangível`);
- **Passivo**: `Passivo Circulante`, `Passivo Não Circulante` e `Patrimônio Líquido`
  (subdividido em `Capital Social`, `Reservas de Capital`, `Ajustes de Avaliação
  Patrimonial`, `Reservas de Lucros`, `Ações em Tesouraria`, `Prejuízos Acumulados`).

### Art. 187 — estrutura da DRE

Receita bruta → deduções (abatimentos, impostos) → receita líquida → custo → lucro
bruto → despesas (vendas, financeiras, gerais/administrativas, outras operacionais) →
resultado antes do IR → participações → resultado líquido. `Receita Líquida` e `Lucro
Bruto` são subtotais **calculados**, não contas de lançamento — por isso não têm folha
própria na árvore, só os grupos que recebem lançamento direto.

## Onde cada tributo entra

Cada tributo que `fiscal/impostos/` já calcula ganha conta em um destes lugares, nunca
inventado à parte:

| Tributo | A Recolher (Passivo) | A Recuperar/Compensar (Ativo) | Dedução da Receita |
|---|---|---|---|
| ICMS | ✓ | ✓ (compra) | ✓ (venda) |
| IPI | ✓ | ✓ (compra) | — (não é dedução de receita, compõe custo/base) |
| PIS | ✓ | ✓ (não-cumulativo) | ✓ |
| COFINS | ✓ | ✓ (não-cumulativo) | ✓ |
| ISS | ✓ | ✓ (retido pelo tomador) | ✓ |
| IBS | ✓ | — (não cumulativo por design, sem acúmulo a recuperar) | ✓ |
| CBS | ✓ | — (idem) | ✓ |
| IRRF | ✓ (retido de fornecedor) | ✓ (retido pelo cliente) | — |
| CSRF | ✓ (retido de fornecedor) | ✓ (retido pelo cliente) | — |
| INSS | ✓ (retido de fornecedor) | ✓ (retido pelo cliente) | — |

`Simples Nacional a Recolher` é a exceção: substitui ICMS/IPI/PIS/COFINS/ISS/IRPJ/CSLL
por uma guia única (DAS), por isso entra sozinho em `Obrigações Tributárias`, sem
`tributo=` de nenhum item da allowlist — a mesma exclusão mútua que `pis_cofins.py` já
documenta ("empresas do Simples Nacional não destacam PIS/COFINS").

IBS/CBS não têm conta "a recuperar": a reforma tributária desenha os dois como não
cumulativos por design (crédito amplo e imediato no próprio período, sem a lógica de
saldo credor acumulado que ICMS/PIS/COFINS têm hoje) — ver `fiscal/impostos/ibs_cbs.py`.

## `TRIBUTOS_CONHECIDOS` é allowlist, não sugestão

`validar_arvore()` recusa qualquer `Conta` cujo `tributo=` não esteja na allowlist do
módulo. Isso existe para que "amarrar aos tributos" seja uma garantia testável — um
tributo novo (ex.: quando IBS/CBS deixarem de ser alíquota-teste) precisa entrar na
allowlist primeiro, nunca aparecer solto numa conta sem que o teste
`test_todo_tributo_conhecido_tem_ao_menos_uma_conta` force a decisão de onde ele mora.

## Obstáculo de integração já identificado: o seletor de plano de contas do ERPNext não é extensível por hook

Investigado ao planejar como este módulo chegaria ao assistente de criação de empresa do
ERPNext (`Company` → "Chart of Accounts"). `erpnext/accounts/doctype/account/
chart_of_accounts/chart_of_accounts.py`'s `get_chart`/`get_charts_for_country` varrem
`os.path.join(os.path.dirname(__file__), "verified")` — **um caminho fixo dentro do
próprio app `erpnext`**, não uma lista que outros apps instalados possam estender via
hook do Frappe. Um app separado (`erpnext_brasil`, que nunca edita `erpnext`) não
consegue registrar um template ali sem sobrescrever o método inteiro.

Caminho de integração mais provável, a explorar num incremento futuro (ainda não
implementado): `override_whitelisted_methods` em `hooks.py` — mecanismo padrão do Frappe
para um app substituir um método `@frappe.whitelist()` de outro app por uma versão
própria — reimplementando `get_charts_for_country`/`get_chart` para também varrer uma
pasta de `erpnext_brasil`. Alternativa mais simples e menos frágil a mudanças futuras do
ERPNext: não depender do seletor de UI nenhum, e sim criar as contas diretamente
(`frappe.get_doc("Account", ...)`, reaproveitando `create_charts` já existente) num
`doc_event`/passo de setup próprio deste app, disparado depois que uma `Company`
brasileira é criada.

## Arquivos

- `contabil/plano_de_contas.py` — a árvore (`Conta`, `ARVORE`) e as validações
  (`validar_arvore`, `contas_do_tributo`); camada pura, sem Frappe, testável sem bench.

## Ainda por implementar

- Conversão da árvore para o formato JSON de template de plano de contas do ERPNext
  (nested dict com `root_type`/`account_type`) — hoje só existe como estrutura Python.
- O mecanismo de integração descrito acima (`override_whitelisted_methods` ou criação
  direta de contas via `doc_event`).
- Códigos de conta (numeração) — deliberadamente fora do escopo deste módulo (ver "Por
  que grupos, não uma codificação completa" acima); cada instalação real escolhe a sua.
- Contas específicas de IPI que não são dedução de receita (compõe custo/base do
  produto, tratamento contábil diferente de ICMS/PIS/COFINS/ISS) — hoje só tem
  `a Recolher`/`a Recuperar`, sem conta própria de "IPI sobre Vendas" na DRE.

## Fontes

- Lei 6.404/1976, Art. 178 e Art. 187 — confirmados em duas fontes secundárias
  independentes que reproduzem a lei na íntegra (`planalto.gov.br`, fonte oficial,
  inacessível às ferramentas de busca no momento) — consultado em 2026-08-29.
- `erpnext/accounts/doctype/account/chart_of_accounts/chart_of_accounts.py` (mecanismo
  de descoberta de templates, lido diretamente do código-fonte do `erpnext` instalado
  neste ambiente) — consultado em 2026-08-29.
- `fiscal/impostos/{icms,ipi,pis_cofins,ibs_cbs,retencoes}.py` deste app, para os
  identificadores de tributo e as regras de recuperação/retenção já implementadas.
