## 1. Linha de base

- [x] 1.1 Registrar versão (`__version__`), commit, data e os números atuais (módulos por pacote, linhas, testes, docs, commits) em `docs/revisao-total/linha-de-base.md` — verificar conferindo cada número com o comando que o gerou, citado no próprio arquivo.
- [x] 1.2 Rodar a suíte pura, `ruff check` e `ruff format --check` e registrar o resultado — verificar pela saída copiada no documento.
- [x] 1.3 Rodar `python scripts/cobertura_de_bench.py` e listar os módulos ligados no `hooks.py` sem teste de bench — verificar pela lista no documento.

## 2. Costura (transversal)

- [x] 2.1 Cruzar `hooks.py` ↔ `setup/campos.py`/`campos_documento.py` ↔ campos lidos e escritos em `integracao/` (por `ast`, não por nome) — verificar com a lista de campos usados sem declaração, ou "nenhum" com o método descrito.
- [x] 2.2 Cruzar DocTypes em `registros_fiscais/doctype/` e `estoque/page` com `modules.txt`, `patches.txt` e a instalação — verificar listando DocType não instalado ou órfão.
- [x] 2.3 Auditar pós-condições de persistência (contagem de linhas afetadas, Id de volta ao domínio) nos repositórios e mapeadores de `integracao/` — verificar com arquivo e linha de cada ponto sem checagem.

## 3. Revisão por frente

Para cada frente: ler os módulos que gravam, transmitem ou calculam; conferir a fonte normativa; classificar cada achado (Crítico, Alto, Médio, Baixo) com evidência; escrever `docs/revisao-total/<frente>.md`. Verificação de cada item: o anexo existe, todo achado tem evidência e a cobertura (o que foi lido e o que foi só varrido) está declarada.

- [x] 3.1 Fiscal documental (NF-e, NFC-e, CT-e, MDF-e, NFS-e, eventos, contingência, chave, QR Code, consumo indevido) — anexo `fiscal-documental.md`.
- [x] 3.2 Fiscal tributário (ICMS, IPI, PIS/COFINS, ST, IBS/CBS, CFOP, NCM, tabelas) — anexo `fiscal-tributario.md`.
- [x] 3.3 Contábil e obrigações acessórias (SPED Fiscal e Contribuições, ECD, ECF, Reinf, GIA) — anexo `contabil-obrigacoes.md`.
- [x] 3.4 Folha e RH (eSocial, `regional_overrides` do hrms, folha) — anexo `folha-rh.md`.
- [x] 3.5 Integração Frappe (`integracao/`, hooks, `repositorio_frappe.py`, JS em `public/`) — anexo `integracao.md`.
- [x] 3.6 Setup e instalação (`setup/`, `after_install`/`after_migrate`, patches, fixtures, `locale`) — anexo `setup.md`.
- [x] 3.7 Saúde e estoque (healthcare, WMS/inventário, changes `integrar-laboratorio-e-imagem` e `tropicalizar-healthcare`) — anexo `saude-estoque.md`.
- [x] 3.8 Qualidade dos testes: testes que só checam retorno sem reler por caminho independente, módulos sem teste, `MODULOS_COBERTOS` incoerente — anexo `testes.md`.
- [x] 3.9 Segurança: segredos, certificado A1 e senha, SQL cru, entrada de usuário em XML/SOAP, permissões de DocType e `whitelist` — anexo `seguranca.md`.

## 4. Pilha, CVE e CI

- [x] 4.1 Rodar `python3 scripts/auditar_pilha.py --bench ~/frappe-bench-16` (WSL2) e conferir na web a LTS mais nova de cada componente e CVE de Frappe/ERPNext/bench — verificar com a saída do script e as URLs consultadas, com data. Backup antes de qualquer alteração; esta revisão só relata.
- [x] 4.2 Revisar `.github/workflows/ci.yml` e a lacuna de job de bench declarada em `docs/gaps.md` seção 2 — verificar com proposta concreta do que um job de bench exigiria.

## 5. Documentação

- [x] 5.1 Conferir `docs/README.md` contra os arquivos de `docs/`, e cada `*-estado.md` contra o código (versão, números, itens "pendentes" que já foram feitos) — verificar com a lista de docs defasados; erro factual simples é corrigido na hora.
- [x] 5.2 Reconciliar `docs/gaps.md` e `docs/estado-da-tropicalizacao.md` com a revisão — verificar pela data e versão novas no cabeçalho e pelos números batendo com a linha de base.

## 6. Síntese e fila de correções

- [x] 6.1 Escrever `docs/revisao-total.md`: números, achados por severidade, cobertura real por frente, o que não foi executado (bench, homologação SEFAZ) e o que depende de ambiente — verificar relendo que cada achado da síntese tem link para o anexo e evidência.
- [x] 6.2 Indexar `docs/revisao-total.md` e `docs/revisao-total/` em `docs/README.md` — verificar abrindo o índice.
- [x] 6.3 Para cada achado Crítico e Alto, criar a proposta de change de correção (`openspec/changes/<nome>`) ou registrar por que não — verificar com `openspec list` mostrando as propostas novas.
- [x] 6.4 Rodar de novo suíte pura e `ruff` para confirmar que a revisão não alterou código — verificar com `git diff --stat` mostrando só `docs/` e `openspec/`.
