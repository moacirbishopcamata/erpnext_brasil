## 1. Fonte primária e matriz de obrigatoriedade

- [ ] 1.1 Baixar o Manual de Orientação da ECF do leiaute vigente e as tabelas dinâmicas em `sped.rfb.gov.br`, para um diretório novo e vazio fora do repositório; ler o texto do disco (nunca resumo de busca) e registrar URL, data, versão e hash de cada arquivo em `docs/ecf-fontes.md` — verificar abrindo o documento e conferindo que cada hash bate com o arquivo baixado.
- [ ] 1.2 Extrair do Manual a **matriz de obrigatoriedade por forma de tributação** (Presumido e Real): registros obrigatórios, condicionais e opcionais, inclusive fora dos blocos do pedido (Bloco `Y`, `0035`, `0930`) — verificar com a tabela em `docs/ecf-fontes.md` em que cada linha cita a página ou seção do Manual; atualizar `proposal.md` se a matriz acrescentar registro ao escopo.
- [ ] 1.3 Extrair o dicionário de campos (nome, ordem, tipo, tamanho, obrigatoriedade) dos registros que a matriz exige — verificar contando campos de cada registro já existente (`0000`, `0030`, `J050`, `K155`…) contra o dicionário e listando divergências.
- [ ] 1.4 Conferir no texto oficial da IN RFB 2.004/2021 (DOU) a lista de dispensa de ECF e a situação de imunes e isentas — verificar com a citação do artigo em `docs/ecf-fontes.md`; divergência da fonte secundária vira aviso registrado, não bloqueio.
- [ ] 1.5 Conferir na norma primária (Lei 9.249/1995, art. 15, e alterações) os percentuais de presunção por atividade, incluindo serviços hospitalares e demais serviços de saúde, e a regra de adicional e de limite de compensação de prejuízo — verificar com cada percentual citando artigo e inciso em `docs/ecf-fontes.md`.

## 2. Inventário do que existe

- [ ] 2.1 Listar os campos de `Company` que já respondem regime tributário, natureza jurídica, optante do Simples e inatividade, e o que falta — verificar com a lista campo a campo e a decisão de reaproveitar ou declarar em `setup/`.
- [ ] 2.2 Ler o app `healthcare` 16.6.1 instalado no bench e registrar como o faturamento acontece (documento gerado, `Item` usado, conta de receita) e se o SUS gera fatura — verificar com o arquivo e a linha de cada afirmação em `docs/ecf-saude.md`.
- [ ] 2.3 Escrever o teste de bench de `integracao/ecf_dados_empresa.py` que grava, relê por outro caminho e compara, declarando `MODULOS_COBERTOS` — verificar vendo o teste falhar com um campo propositalmente quebrado e passar sem ele, em bench real.

## 3. Dados de apoio e porta de aplicabilidade

- [ ] 3.1 Implementar o leitor do catálogo versionado em `contabil/` e carregar as tabelas dinâmicas que a matriz exige, com fonte e hash nos dados — verificar com teste que recusa código fora do catálogo e ano sem catálogo, e com teste que recalcula o hash do arquivo de dados.
- [ ] 3.2 Implementar a função pura de aplicabilidade (Simples, órgão público, autarquia, fundação pública, inativa; imune e isenta não dispensam) — verificar com um teste por hipótese de dispensa, um por entidade imune e um por regime não informado.
- [ ] 3.3 Acrescentar a `tests/test_arquitetura.py` a checagem de que `contabil/` e `folha/` não importam `frappe` nem `integracao` — verificar vendo o teste falhar ao inserir temporariamente um `import frappe` em `contabil/` e passar sem ele.

## 4. Bloco 0, Bloco K e configuração da ECF

- [ ] 4.1 Criar o DocType de configuração da ECF por empresa e ano-calendário com um campo por indicador exigido pela matriz, sem padrão, distinguindo sugestão de confirmado e declarando o que cada campo aceita — verificar com bench: salvar, reler por outro caminho e comparar; valor salvo não é sobrescrito por sugestão.
- [ ] 4.2 Implementar `0010`/`0020`/`0021` (e `0035`/`0930` se a matriz exigir) a partir da configuração, recusando indicador sem resposta — verificar com teste que lista os indicadores pendentes e outro que monta o registro com as respostas.
- [ ] 4.3 Implementar `K030`, `K355` e `K356` conforme o dicionário, reaproveitando a aritmética de saldos da ECD, e documentar `K915`/`K935` como preenchimento manual — verificar com teste em que o saldo do Bloco K iguala o da ECD para a mesma base.
- [ ] 4.4 Implementar `J053` somente se a matriz o exigir; caso contrário, registrar em `docs/ecf-bloco-j.md` que permanece fora, com a linha do Manual — verificar pelo apontamento no documento.

## 5. Arquivo da ECF

- [ ] 5.1 Implementar o montador do arquivo em `contabil/` (ordem do leiaute, encerramento de bloco, Bloco 9, contagens) com a projeção mínima própria — verificar com teste que recalcula as contagens a partir do texto e compara às declaradas.
- [ ] 5.2 Implementar a validação estrutural contra o dicionário da tarefa 1.3 (campos, tipos, tamanhos, obrigatoriedade) — verificar com testes que recusam campo a mais, a menos, fora de tamanho e obrigatório vazio.
- [ ] 5.3 Implementar a geração integrada em `integracao/` (aplicabilidade, configuração, plano e saldos, montagem, `Arquivo SPED` tipo ECF), com `has_permission` antes de qualquer leitura e sem `ignore_permissions` — verificar com `tests/test_whitelist_com_permissao.py` verde e com teste de bench em que usuário sem papel recebe `PermissionError` sem registro criado.
- [ ] 5.4 Expor a ação na tela da empresa com o resultado dizendo que o arquivo precisa ser validado e transmitido pelo PVA — verificar manualmente no bench e registrar a captura do resultado em `docs/ecf-estado.md`.

## 6. Lucro Presumido (Bloco P)

- [ ] 6.1 Criar o mapeamento da empresa de origem de receita para atividade, sem padrão, e a apuração da base presumida com os percentuais da tarefa 1.5 — verificar com testes de duas atividades, de receita sem mapeamento (recusa) e de serviço hospitalar × demais serviços de saúde.
- [ ] 6.2 Implementar `P030`, `P100` e `P150` conforme o dicionário, resolvendo no Manual se usam plano próprio ou referencial — verificar com teste cujo plano de entrada produz o registro esperado e com a citação da seção do Manual na docstring.
- [ ] 6.3 Implementar as memórias `P130`/`P200`/`P230`/`P300`/`P400`/`P500` sobre o catálogo da tarefa 3.1, com cálculo de IRPJ, CSLL e adicional reproduzível — verificar com teste que recalcula o devido a partir das linhas de base e com exemplo de cálculo da própria Receita, se o Manual o trouxer.
- [ ] 6.4 Teste de ponta a ponta do Presumido: empresa de serviços de saúde com receita hospitalar e de consultas, gerar o arquivo e conferir estrutura e contagens — verificar com o teste verde e com o arquivo anexado a `docs/ecf-bloco-p.md`.

## 7. Lucro Real (Blocos L, M, N)

- [ ] 7.1 Implementar o agregado `ContaParteB` em `contabil/` (adição, exclusão, compensação, fechamento do período, saldo que não fica negativo) — verificar com testes de invariante e de saldo final igual ao saldo inicial do período seguinte.
- [ ] 7.2 Criar o DocType da conta e do movimento da Parte B, com vínculo obrigatório ao lançamento contábil, e o repositório que reconstitui o agregado — verificar com bench: gravar o movimento e reler pela conta e pelo lançamento, comparando os dois resultados.
- [ ] 7.3 Implementar o Bloco L (sete registros) a partir do plano referencial e dos saldos — verificar com teste em que o resultado do Bloco L iguala o resultado apurado pela contabilidade na mesma base.
- [ ] 7.4 Implementar o Bloco M: lucro real a partir do resultado contábil, adições, exclusões e compensação de prejuízo com o limite vigente — verificar com teste da cadeia completa e com teste de compensação acima do limite.
- [ ] 7.5 Implementar o Bloco N com o cálculo de IRPJ e CSLL sobre o catálogo oficial — verificar com teste que recalcula o devido a partir das linhas de base.
- [ ] 7.6 Tratar entidade imune ou isenta conforme o Manual, ou recusar a geração do bloco informando o que falta — verificar com teste de entidade filantrópica de saúde.
- [ ] 7.7 Teste de ponta a ponta do Lucro Real: dois períodos consecutivos, o segundo abrindo com o saldo da Parte B do primeiro — verificar com o teste verde cruzando a costura contábil↔Parte B↔arquivo.

## 8. Fechamento

- [ ] 8.1 Atualizar `docs/ecf-estado.md`, `ecf-bloco-*.md`, `docs/gaps.md`, `docs/README.md` e `CLAUDE.md` com o que ficou pronto, o que ficou bloqueado e a versão do leiaute — verificar com `ruff` limpo, suíte pura verde e links dos documentos conferidos por script.
- [ ] 8.2 Registrar a validação no PVA: gerar o arquivo de uma empresa de teste, validar no PVA da Receita e anexar o resultado em `docs/ecf-estado.md`, ou registrar "não executado" e por quê — verificar pelo resultado anexado ou pela declaração explícita de pendência.
- [ ] 8.3 Rodar `python scripts/cobertura_de_bench.py` e os testes de bench dos módulos novos — verificar pela saída anexada ao documento de estado.
