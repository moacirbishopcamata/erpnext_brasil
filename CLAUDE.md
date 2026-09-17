# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é

Localização fiscal brasileira para o ERPNext, distribuída como **app Frappe separado** — o ERPNext
nunca é forkado nem editado. Cobre cadastros fiscais (CPF/CNPJ inclusive alfanumérico, IE das 27
UFs), aritmética de impostos (ICMS, IPI, PIS/COFINS, IBS/CBS, retenções), NF-e/NFC-e/CT-e/MDF-e
(montagem, assinatura, SOAP, eventos), SPED/ECD/ECF/EFD, boleto/Pix e eSocial/folha.

Idioma do projeto é **pt-BR** — código, docstrings, nomes de teste, docs e artefatos OpenSpec.
Os cabeçalhos estruturais do OpenSpec e as palavras SHALL/MUST ficam em inglês.

## Comandos

```sh
# Suíte pura (~2.850 testes) — sem bench, sem site, sem banco. É o que a CI roda.
python -m unittest discover -s erpnext_brasil/tests -t .

# Um módulo / um teste
python -m unittest erpnext_brasil.tests.test_chave_acesso -v
python -m unittest erpnext_brasil.tests.test_chave_acesso.TestClasse.test_metodo

# Lint e formato (config em pyproject.toml: tab, aspas duplas, linha 110 — igual ao erpnext)
ruff check erpnext_brasil/
ruff format --check erpnext_brasil/

# Dependências opcionais fora do bench — sem elas, testes de assinatura/SOAP são pulados (skipUnless)
pip install lxml cryptography requests

# Quais módulos ligados em hooks.py ainda não têm teste de bench
python scripts/cobertura_de_bench.py
```

Testes de bench (`erpnext_brasil/tests_bench/`) só rodam num bench de verdade — WSL2 + Docker,
bench **não roda nativo no Windows** (ver `docs/ambiente-dev-bench.md`). O padrão do projeto é o
bench **v16** (`~/frappe-bench-16`, site `v16.localhost`):

```sh
bash scripts/subir.sh                      # sobe MariaDB, Redis e o servidor (idempotente)
SO_SERVICOS=1 bash scripts/subir.sh        # só MariaDB e Redis — suficiente para migrate/run-tests
bench --site v16.localhost set-config allow_tests true     # uma vez
bench --site v16.localhost run-tests --app erpnext_brasil
bench --site v16.localhost run-tests --app erpnext_brasil --module erpnext_brasil.tests_bench.test_party
bench --site v16.localhost migrate         # reaplica campos customizados (after_migrate)
```

## Arquitetura — a regra é executável

Duas camadas, dependência numa direção só, **imposta por `tests/test_arquitetura.py`** (percorre a
árvore de imports com `ast`):

- `fiscal/`, `contabil/`, `folha/` — regra fiscal pura: funções e `dataclass(frozen=True)`.
  **Nunca importam `frappe`**, nunca importam `integracao/`. Testável com `unittest` puro.
- `integracao/` — a única camada que fala com o Frappe (`frappe.get_doc`, `frappe.throw`,
  `doc_events`). Deliberadamente fina: **limite de 320 linhas por módulo é testado**; se um módulo
  cresce, a regra está no lugar errado e deve descer para a camada pura.
- `setup/` — campos customizados e instalação. `setup/campos.py` une os quatro mapas
  (`custom_fields`, `campos_documento`, `campos_folha`, `campos_estoque`) em `MAPAS`; instalação e
  teste leem o mesmo dado. Novo mapa = uma linha em `MAPAS`. Não importa `frappe`.
- `registros_fiscais/doctype/` — DocTypes próprios (Transmissão Fiscal, Numeração Fiscal, Lote
  eSocial, Arquivo SPED, Pendência NFC-e, Bloqueio SEFAZ). `estoque/page/` — página do Desk.
- `tests/` — nenhum arquivo pode importar `frappe` (também testado). `tests_bench/` — testes que
  exigem bench; cada arquivo declara `MODULOS_COBERTOS = (...)` com os módulos de `integracao/`
  que exercita (lido por `scripts/cobertura_de_bench.py`, não inferido).

Pontos de entrada: `hooks.py` (doc_events em `validate`, não `on_submit`, para o erro aparecer no
formulário; `after_migrate` recria campos idempotentemente; `regional_overrides` só tem efeito com
`hrms` instalado). Os DocTypes do ERPNext que recebem apuração fiscal completa são Sales/Purchase
Invoice, Delivery Note, Purchase Receipt e POS Invoice.

### Padrões que atravessam o código

- **Inversão de dependência via `Protocol`**: a regra depende de `RepositorioClassificacao`
  (`fiscal/codigos/repositorio.py`) e da porta `TransporteFiscal` (`fiscal/documento/porta.py`);
  `integracao/` fornece as implementações Frappe. Testes usam duplos em memória.
- **Agregado com estado privado**: `DocumentoFiscal` (`fiscal/documento/estado.py`) só muda por
  método guardado (`autorizar`, `cancelar`); `autorizar` exige protocolo e `reconstituir` recusa
  autorizado sem protocolo. Adaptador de transporte devolve resposta, quem transiciona é o agregado.
- **`Decimal` com `ROUND_HALF_UP`**, nunca float. **Alíquota é fração** (`0.18`); percentual
  levanta `ValueError`. A conversão para percentual acontece num lugar só, na serialização XML.
- **Ordem de apuração fixa** em `fiscal/impostos/apuracao.py`: IPI → ICMS → PIS/COFINS → IBS/CBS.
  ICMS é por dentro; IBS/CBS por fora — não unificar.
- **Grupos do XML são dicionários com nomes oficiais de tag**, não strings; um teste confere cada
  tag emitida contra `fiscal/documento/elementos_nfe.json` (extraído do XSD oficial).
- **Degradar vs. falhar alto** é decisão consciente: tabela oficial não importada/UF indeterminável
  deixam passar; autorização sem protocolo, base negativa, alíquota percentual falham alto. Todo
  `except` justifica por escrito por que engolir ali é correto.
- **Todo campo customizado deste app começa com `br_`**, sem exceção (patch `v0_177`).
  CPF/CNPJ vive em `tax_id` do ERPNext — não criar campo paralelo para o que o núcleo já modela.

## Disciplina do projeto (não-negociável)

1. **Nenhuma regra fiscal nasce de memória** — conferir contra lei/IN/Ajuste SINIEF/NT/XSD antes
   de codar; fonte secundária tem nível de confiança declarado no próprio módulo.
2. **Nunca supor por analogia** entre NF-e, CT-e e MDF-e — divergem em detalhes que só o XSD de
   cada um revela (ex.: `modal` do CT-e é `01`-`06`, do MDF-e é `1`-`4`).
3. **Todo incremento vira `.md` em `docs/`** (índice em `docs/README.md`), citando fonte e o que
   ficou de fora. Gaps declarados em `docs/gaps.md`.
4. **Teste mira na costura**: muta, projeta, relê por caminho independente e compara — não só
   "devolveu sem erro". Nome do teste descreve o achado
   (`test_k155_reaproveita_i155_com_indicadores_renomeados`).
5. **Achado real > suposição conveniente** — contradição descoberta é registrada, nunca silenciada.

Docstrings de módulo explicam *por que* a decisão foi tomada e o que o bench provou; manter esse
estilo ao criar módulos novos. Tipografia real em prosa (`—`, `×`) é deliberada (RUF001-003 desligados).

## OpenSpec

Mudanças são planejadas em `openspec/changes/<nome>/` (proposal, design, specs, tasks) e specs
consolidadas em `openspec/specs/`. Comandos `/opsx:*` (`propose`, `apply`, `update`, `sync`,
`archive`, `explore`) em `.claude/commands/opsx/`. Artefatos em pt-BR.
