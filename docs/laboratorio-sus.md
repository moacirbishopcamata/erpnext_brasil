# Laboratório SUS: módulo avulso de laboratório, farmácia e armazém públicos

Guia do change `laboratorio-sus-ciclo-completo` (`openspec/changes/laboratorio-sus-ciclo-completo/`). O que o módulo é, as decisões que o moldam, onde está cada
coisa, em que pé está e o que depende de gente ou de fonte. Estado em 2026-10-12: **plano completo** (33 capacidades, 247 tarefas, `openspec validate` passa) e **camada pura
inicial implementada** (tarefas 2.1 a 2.8) mais três tarefas de fonte do grupo 1 (1.2, 1.3, 1.7).

## O que é

Um módulo **independente do ERPNext** que cobre, para o SUS municipal: o ciclo do exame laboratorial da solicitação ao laudo assinado e à entrega; o que o GAL faz hoje; a integração com os
analisadores; o prontuário do paciente como raiz de todos os dados; a LGPD; a farmácia (catálogo CATMAT, REMUME, dispensação no balcão, RNDS e BNAFAR); o armazém e as compras de **todos os materiais** da rede
(lote rígido, notas fiscais, contabilidade pública, endereçamento, separação guiada e despacho às micro unidades). Um módulo de integração o acopla ao ERPNext (profissionais do Employee, compras, estoque, eSocial S-2220).

Contexto de implantação que originou o pedido: **Porto Velho (RO)**, com distritos e Baixo Madeira, e o Laboratório Central Municipal (LAM, CNES 6462995). Ver [laboratorio-sus-rede-do-lam.md](laboratorio-sus-rede-do-lam.md).

## Decisões que moldam tudo

1. **Família de módulos.** Núcleo `sus_brasil` (só Frappe; módulos Cadastros SUS, Exames Laboratoriais, Farmacia SUS, Materiais e Armazem, Contabilidade Publica, Seguranca e LGPD) e extensões `<Aplicação>_Brasil` (`hrms_brasil`, `healthcare_brasil`, o módulo "Integração SUS" do `erpnext_brasil` e as demais), cada uma ativa só onde a aplicação existe.
2. **Núcleo independente, integração à parte.** O núcleo (`sus_brasil/`) nunca importa ERPNext, Healthcare nem `erpnext_brasil`; só o módulo de integração conhece os dois lados. Teste arquitetural com `ast` garante.
3. **Camada pura sem `frappe`**, portas (`Protocol`) para tudo que é de fora, adaptadores opcionais.
4. **Prontuário do paciente é a raiz dos dados**: linha do tempo só de acréscimo, hash por entrada, guarda mínima de **20 anos do último registro** (Lei 13.787/2018).
5. **Casamento por identificador exato.** Resultado só se anexa ao tubo pelo identificador (Verhoeff); o resto é quarentena. Custódia com hash encadeado.
6. **Autoverificação permitida, desligada por padrão**; regra aprovada pelo responsável técnico; crítico, controle reprovado e lacuna nunca são autoverificados; revisão humana sob pedido.
7. **Assinatura ICP-Brasil do biomédico** (PAdES, carimbo de tempo), autenticação pública do laudo com segundo fator, portal do paciente pelo número da requisição, tudo responsivo.
8. **LGPD desde a concepção**: base legal por atividade (art. 11), direitos do titular, incidente em 3 dias úteis do conhecimento do afetamento de dados, RIPD como escolha de projeto.
9. **Catálogo CATMAT no desenho do e-SUS** (cinco colunas), código canônico `BR` + 7 dígitos, sufixo `-N` como apresentação, validado contra o catálogo oficial do Compras.gov.br.
10. **REMUME versionada com subgrupos**; dispensação por **terminal de balcão (POS) próprio, gratuito e não fiscal**; envio à RNDS (REDFM) e à BNAFAR.
11. **Lote como registro de primeira classe** (GS1 e UDI), recolhimento que bloqueia o município de uma vez, FEFO; **um WMS para todos os materiais** com perfil de controle por classe.
12. **Compras com NF-e conferida**, ateste por fiscal designado; **contabilidade pública** como evidência ao SIAFIC (nunca substituindo-o): custo médio ponderado ou PEPS, nunca UEPS.
13. **Armazém de verdade**: zonas, endereçamento (GLN), etiquetas (SSCC), separação guiada, ondas, despacho por rota (inclusive fluvial), comprovação de entrega e painel de situação.
14. **Tropicalizado**: pt-BR, formatos, fuso por unidade (Rondônia é UTC−4, exige `tzdata`), dias úteis com feriados, tabelas oficiais versionadas.

## Índice das capacidades (`specs/saude/`)

| Área | Capacidades |
|---|---|
| Ciclo do exame | `sus-solicitacao-de-exame`, `sus-rastreabilidade-e-etiquetagem`, `sus-coleta-e-recepcao`, `sus-remessa-de-amostras`, `sus-analise-e-liberacao`, `sus-resultado-e-entrega`, `sus-producao-e-notificacao` |
| Automação e analisadores | `sus-integracao-com-analisadores`, `sus-autoverificacao-e-automacao` |
| Laudo e paciente | `sus-assinatura-e-autenticidade`, `sus-autenticacao-de-resultado`, `sus-portal-do-paciente`, `sus-cadastro-de-pacientes`, `sus-prontuario-do-paciente` |
| GAL, ERPNext, eSocial | `sus-equivalencia-ao-gal`, `sus-integracao-com-erpnext`, `sus-integracao-com-esocial` |
| Dados e segurança | `sus-protecao-de-dados`, `sus-seguranca-e-privacidade`, `sus-tropicalizacao` |
| WMS do laboratório | `sus-estoque-de-reagentes-e-insumos`, `sus-armazenamento-de-amostras`, `sus-controle-de-coletas` |
| Farmácia | `sus-catalogo-catmat`, `sus-remume-e-padronizacao`, `sus-dispensacao-no-balcao`, `sus-interoperabilidade-da-assistencia-farmaceutica` |
| Materiais, compras e armazém | `sus-gestao-de-materiais`, `sus-controle-de-lotes`, `sus-compras-e-recebimento`, `sus-fracionamento-e-devolucoes`, `sus-contabilidade-publica-do-estoque`, `sus-armazenagem-e-despacho` |

## Onde está cada coisa

| O quê | Onde |
|---|---|
| Plano (proposta, design com 30+ perigos, specs, tarefas) | `openspec/changes/laboratorio-sus-ciclo-completo/` |
| Repositórios (privados, ao lado do `erpnext_brasil`) | `sus_brasil` (núcleo, MIT), `hrms_brasil`, `healthcare_brasil`, `wms_sus_brasil` (extensões `*_Brasil`, esqueletos) — em `github.com/moacirbishopcamata/<nome>` |
| Camada pura implementada | `sus_brasil/puro/` (CPF/CNS, identificador Verhoeff, estados, custódia, faixa offline, rejeição/estabilidade, tempos, portas) |
| Testes | `sus_brasil/tests/` (64 testes; `python -m unittest discover -s sus_brasil/tests -t .`) |
| Dados versionados | `sus_brasil/dados/`: `agravos_lista_nacional.csv` (PRT 11.211/2026), `sigtap_0202_202609.csv`, `tuss_sigtap.csv`, `catmat_medicamentos_esus_v420.csv`, `remume_porto_velho_2025.csv` |
| Fontes do grupo 1 e confiança | [laboratorio-sus-fontes.md](laboratorio-sus-fontes.md) |
| Análise da LGPD | [laboratorio-sus-lgpd.md](laboratorio-sus-lgpd.md) |
| Rede municipal e o LAM (CNES) | [laboratorio-sus-rede-do-lam.md](laboratorio-sus-rede-do-lam.md) |
| Estudo anterior de farmácia e PA/UPA sobre o Healthcare | [saude-sus-farmacia-e-pronto-atendimento.md](saude-sus-farmacia-e-pronto-atendimento.md) |
| Peças do repositório que o módulo de integração reaproveita | `fiscal/gs1.py` ([coletor-gs1.md](coletor-gs1.md)), `integracao/entrada_nfe.py` ([entrada-de-nfe.md](entrada-de-nfe.md)), `folha/` (eSocial), [estoque-estado.md](estoque-estado.md) |

## Achados que mudaram o plano (todos com fonte)

- O catálogo oficial CATMAT tem **API aberta** (Compras.gov.br); numa amostra de 80 códigos da tabela do e-SUS, todos existem e **9% estão inativos**. A tabela do e-SUS é de 2021.
- No CNES público, `TERCEIRO` e `CNESTERC` vêm **vazios**: não dá para saber quem usa os serviços do LAM; o módulo vai registrar a CNES solicitante em toda requisição.
- IHE LAW: `QBP^Q11`, `OML^O33`, `OUL^R22`; **`ORU^R01` não faz parte do perfil**.
- Resolução ANPD 15/2024: o relógio de 3 dias úteis conta do conhecimento de que o incidente **afetou dados pessoais**, não da classificação do risco.
- O art. 20 da LGPD, hoje, **não exige revisão por pessoa natural** (redação da Lei 13.853/2019); o módulo oferece a revisão humana de qualquer modo.
- A RDC 504/2021 (transporte de material biológico) **não fixa temperatura nem prazo**: manda validar por material.
- `ler_nfe` do repositório **não lê** o `rastro` nem o grupo de medicamento: a integração precisa estendê-lo (tarefa 24.3).

## Pendências que dependem de gente ou de acesso

- Consultar um LACEN (ou a CGLAB) sobre integração com o GAL; consultar o CFBM/CRBM sobre assinatura de laudo.
- Textos pagos ou inacessíveis: CLSI AUTO12, AUTO02, LIS01, LIS02; RDC 786 (art. 81); RDC 430/2020, 591/2021, 625/2022, SNCM; leiaute do eSocial S-2220; especificação GS1.
- Confirmar com a contabilidade do município: elemento de despesa, plano de contas, layout do SIAFIC, formato de prestação de contas ao tribunal de contas.
- Perguntas de projeto do serviço (licença, contingência de etiqueta, política de retenção de amostras) na seção "Open Questions" do `design.md`.

## Armadilhas de ferramenta (aprendidas no levantamento)

- O site do **Planalto recusa conexão de script**; peça o arquivo salvo ao usuário.
- Resumidores de página **truncam documentos longos**: baixe com `curl` e leia localmente.
- Arquivo `.dbc` do DATASUS é DBF comprimido (PKWare DCL); ler exige descompressor próprio (Python puro serve).
- `zoneinfo` no Windows exige o pacote `tzdata`.
- Em comandos de shell longos com heredoc, alguns caracteres quebram o interpretador: grave o arquivo com a ferramenta de escrita e rode o script.
