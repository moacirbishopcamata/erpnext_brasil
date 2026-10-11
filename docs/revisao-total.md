# Revisão total do ERPNext Brasil — síntese

Revisão de **2026-10-11**, versão `0.227.0`, commit `16159bb`. Executa o change `revisao-total-erpnext-brasil`. Somente leitura: nenhum código foi alterado, só documentação.

## O que esta revisão é, e o que não é

É leitura dirigida por risco e varredura mecânica, não leitura linha a linha das ~91 mil linhas. Cada anexo declara o que foi lido, o que foi só varrido e o que não foi visto. **Não rodei o bench** nem enviei nada a uma SEFAZ: tudo que depende de site real aparece como "inferido da leitura". Rodei a suíte pura (3.490 testes, verde), o `ruff` (limpo) e a auditoria da pilha no WSL2.

Anexos: [linha de base](revisao-total/linha-de-base.md) · [fiscal documental](revisao-total/fiscal-documental.md) · [fiscal tributário](revisao-total/fiscal-tributario.md) · [contábil](revisao-total/contabil-obrigacoes.md) · [folha/RH](revisao-total/folha-rh.md) · [integração](revisao-total/integracao.md) · [setup](revisao-total/setup.md) · [saúde/estoque](revisao-total/saude-estoque.md) · [testes](revisao-total/testes.md) · [segurança](revisao-total/seguranca.md) · [pilha/CI](revisao-total/pilha-ci.md) · [documentação](revisao-total/documentacao.md).

## O que está bem

- A costura de campos e hooks não tem furo: 240 campos declarados contra 119 usados, nenhum sem declaração; os 20 caminhos do `hooks.py` resolvem.
- Nenhum `eval`, `exec`, `pickle`, `shell=True`, `verify=False` nem segredo em literal; os três `db.sql` são parametrizados.
- A guarda de consumo indevido recusa antes da SEFAZ em CT-e e MDF-e, com teste que conta chamadas.
- IBS/CBS falha alto fora do ano com alíquota em norma.
- Todos os módulos de `fiscal/`, `contabil/` e `folha/` têm teste; todos os testes de bench declaram `MODULOS_COBERTOS`; cobertura de bench 13/13.

## Achados por severidade

| ID | Sev. | Achado | Onde | Anexo |
|---|---|---|---|---|
| RT-01 | **Crítico** (latente até 01/01/2027) | INSS e IRRF sempre com a tabela de 2026: o ano do holerite nunca é passado | `integracao/folha.py:93-94`, `folha/inss.py:54`, `folha/irrf.py:74` | [folha-rh](revisao-total/folha-rh.md) |
| RT-02 | **Alto** | `gerar_efd` sem checagem de permissão e com `insert(ignore_permissions=True)` | `integracao/geracao_efd.py:90-124` | [integracao](revisao-total/integracao.md) |
| RT-03 | Médio | Leituras de estoque, prontidão da EFD e Pix por `get_all`, `db.get_value` ou SQL cru, com empresa vinda do cliente | `navegador_estoque.py:54-163`, `alerta_fiscal.py:91`, `pix.py:32` | [integracao](revisao-total/integracao.md) |
| RT-04 | Médio | 23 de 137 módulos puros sem fonte normativa; 7 deles calculam tributo | `fiscal/impostos/icms.py`, `ipi.py`, `pis_cofins.py`, `apuracao.py`, entre outros | [fiscal-tributario](revisao-total/fiscal-tributario.md) |
| RT-05 | Médio | 14 `etree.fromstring` sem parser endurecido; um recebe XML do usuário (`importar_nfe`) | `fiscal/documento/leitura_nfe.py:261` e mais 13 | [seguranca](revisao-total/seguranca.md) |
| RT-06 | Médio (a verificar em bench) | Eventos de CT-e e MDF-e usam o fuso do servidor; a emissão usa o do site | `eventos_cte.py:80`, `eventos_mdfe.py:74` | [integracao](revisao-total/integracao.md) |
| RT-07 | Médio | `auditar_pilha.py` lê o MariaDB 10.11.9 em vez do 10.11.19 (ordem de texto) e dá aviso falso | `scripts/auditar_pilha.py:463-465` | [pilha-ci](revisao-total/pilha-ci.md) |
| RT-08 | Médio | Nove módulos de `integracao/` sem referência em teste; `importar_codigos` tem métodos `whitelist` e `ignore_permissions` | `importar_codigos`, `repositorio_frappe` e outros 7 | [integracao](revisao-total/integracao.md) |
| RT-09 | Médio | Docs defasados ou fora do índice; um link quebrado | `estado-da-tropicalizacao.md`, `nfse-estado.md:33` e outros | [documentacao](revisao-total/documentacao.md) |
| RT-10 | Médio (a verificar) | Marley Health é GPL-3.0 e o app é MIT; nenhuma decisão registrada | `docs/healthcare-estado.md` | [saude-estoque](revisao-total/saude-estoque.md) |
| RT-12 | Médio (declarado) | MDF-e e CT-e sem prova em homologação; envelope e códigos de fonte secundária | tarefas 3.1 e 5.1 de `fechar-laco-cte-mdfe` | [fiscal-documental](revisao-total/fiscal-documental.md) |
| RT-13 | Médio (declarado) | Cinco montadores de evento do MDF-e com a forma da NF-e | `docs/gaps.md:817` | [fiscal-documental](revisao-total/fiscal-documental.md) |
| RT-16 | Médio (declarado) | Sem job de bench no CI | `docs/gaps.md` seção 2 | [pilha-ci](revisao-total/pilha-ci.md) |
| RT-11 | Baixo (a verificar) | Contagem de testes "sem asserção" superconta (auxiliares); 134 puros não conferidos | `tests/` | [testes](revisao-total/testes.md) |
| RT-14 | Baixo | Docstring de `gerar_efd` diz que faltam D/H/K; só falta D | `geracao_efd.py:93-96` | [contabil](revisao-total/contabil-obrigacoes.md) |
| RT-15 | Baixo | `after_install` e `after_migrate` com corpo idêntico | `setup/install.py:21-37` | [setup](revisao-total/setup.md) |
| RT-17 | Baixo (declarado) | Healthcare instalado só em PostgreSQL | `docs/healthcare-estado.md` | [saude-estoque](revisao-total/saude-estoque.md) |
| RT-18 | Baixo | Bench de CEP sem releitura de banco | `tests_bench/test_consulta_cep.py` | [testes](revisao-total/testes.md) |
| RT-19 | Baixo | 28 `ignore_permissions` sem teste que vigie `whitelist` novo | `integracao/` | [seguranca](revisao-total/seguranca.md) |

Contagem: 1 Crítico, 1 Alto, 11 Médios, 6 Baixos (19). Quatro já estavam declarados na documentação (RT-12, RT-13, RT-16, RT-17); os outros 15 são achados desta revisão.

## O que depende do ambiente (não resolvível por leitura)

- Autorizar NF-e, CT-e e MDF-e em SEFAZ de homologação com certificado A1.
- Rodar o bench: RT-06 (fuso) e qualquer afirmação sobre Custom Field, hook e DocType só se fecham lá.
- Conferir `lxml` instalado no bench-16 para RT-05.
- Parecer sobre licença (RT-10).

## Pilha

Sem série fora de suporte. `frappe 16.51.1` existe (a instalada é a 16.51.0). Um CVE alto (`pdfkit`, CVE-2025-26240, sem correção), já aceito e registrado em `docs/auditoria-da-pilha.md`, e o app não referencia `pdfkit`. O aviso de MariaDB atrasado é falso (RT-07).

## Fila de correções proposta

Cada item é um change OpenSpec separado, em `openspec/changes/`:

1. **`corrigir-ano-da-folha`** — RT-01, antes de janeiro de 2027. Criado.
2. **`proteger-gerar-efd`** — RT-02 e RT-03 (permissão nos métodos que leem ou gravam por empresa). Criado.
3. **Sem change criado, a decidir** — RT-04 (conferir fonte de ICMS/IPI/PIS-COFINS/apuração), RT-05 (parser único de XML), RT-06 (fuso do site nos eventos), RT-07 (ordenação numérica em `auditar_pilha.py`), RT-08 (testes dos nove módulos), RT-16 (job de bench). São Médios; a revisão propõe, não decide a ordem.

## Reconciliação feita

`docs/README.md` (três páginas que faltavam e esta revisão), `CLAUDE.md` (descrição do CI), `docs/estado-da-tropicalizacao.md` (aviso de defasagem) e `docs/gaps.md` (nota apontando os achados novos).
