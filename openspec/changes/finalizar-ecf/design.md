## Context

Ver `proposal.md` (Why). Estado e restrições que moldam o desenho:

- Camada pura em `contabil/` (sem `frappe`) e integração fina em `integracao/` (limite de 320 linhas por módulo, imposto por `tests/test_arquitetura.py`). A pureza de `contabil/` não é imposta por teste (achado da reanálise de 2026-10-26, ainda na branch `openspec-reanalise-do-sistema`): as peças novas respeitam por convenção e a change acrescenta o teste.
- A ECF reaproveita a ECD: `ecf_bloco_j` usa `ecd_i050`/`ecd_i051`, `ecf_bloco_k` usa `ecd_i150`/`ecd_i155`. O `Arquivo SPED` já tem o tipo `ECF` nas opções.
- `integracao/ecf_dados_empresa.py` monta `IdentificacaoEcf`/`DadosCadastrais`, mas **não tem teste** (RT-08) e deixa de fora o que varia a cada entrega (`indicador_situacao_inicio_periodo`, `tipo_ecf`, `retificadora`, `codigo_versao_leiaute`).
- Fonte atual do leiaute: busca agregada sobre o Manual da ECF (ADE Cofis nº 02/2026) e documentação de ERP (Senior), **nunca o texto oficial lido**. A norma de dispensa (IN RFB 2.004/2021, art. 1º) vem de perguntas e respostas da Receita e de consultorias; a imunidade/isenção não dispensar também é fonte secundária e divergente em detalhes.
- Lição de RT-02: método exposto sem checagem de permissão e com `ignore_permissions` é achado Alto. `tests/test_whitelist_com_permissao.py` já falha se um método `@frappe.whitelist()` de `integracao/` ficar sem checagem.
- O laboratório SUS é módulo avulso, com contabilidade pública que "nunca substitui o SIAFIC" (`docs/laboratorio-sus.md`). Ele não é usuário da ECF.

## Goals / Non-Goals

**Goals:**
- Um arquivo ECF gerado de ponta a ponta para Lucro Presumido e, depois, para Lucro Real, que o PVA possa abrir.
- Toda decisão regulatória (indicador, regime, atividade, código) explícita e recusada quando ausente, nunca presumida.
- Cada fonte lida e registrada com versão, data e nível de confiança antes de virar código.

**Non-Goals:**
- Blocos `C`, `E`, `T`, `U`, `X` e `S`; e `Y` além do que a matriz de obrigatoriedade provar indispensável.
- Assinar ou transmitir a ECF: isso é do PVA com o certificado da empresa.
- Qualquer coisa da contabilidade pública do SUS.
- Calcular tributo de regime que a empresa não usa (Lucro Arbitrado, Simples).

## Decisions

1. **Fonte primária antes de código (grupo 1 das tarefas).** O Manual e as tabelas dinâmicas são baixados, lidos no disco e registrados com hash. A **matriz de obrigatoriedade por regime** que sai daí decide o escopo real: se o Manual exigir, por exemplo, um registro do Bloco `Y` para o Presumido ser aceito, ele entra, e a change é atualizada antes de seguir. *Alternativa*: continuar a partir dos documentos atuais. Rejeitada: os três bloqueios existem justamente porque a fonte nunca foi lida.

2. **Presumido antes de Real.** O Bloco P não depende do controle da Parte B, e é o regime mais comum em clínicas e laboratórios privados. O Lucro Real carrega o domínio novo mais pesado. Cada um é entregável e testável sozinho; a ordem não cria dependência de um sobre o outro. *Alternativa*: Real primeiro por ser "o núcleo". Rejeitada: adia a primeira entrega útil sem ganho.

3. **Parte B como agregado, não como campo.** `ContaParteB` é objeto de domínio puro em `contabil/`: estado privado (saldo inicial, movimentos), métodos guardados (`adicionar`, `excluir`, `compensar`, `fechar_periodo`) que recusam saldo negativo; o DocType é um registro "burro" que só mapeia colunas; um repositório faz a ida e a volta. A disciplina está na **costura** domínio↔registro: o teste grava por um caminho, relê por outro (pela conta e pelo lançamento contábil de origem) e compara. *Alternativas*: Custom Field de saldo na `Account` (não carrega movimento nem vínculo ao lançamento); JSON dentro do `Arquivo SPED` (some o histórico entre períodos). Ambas rejeitadas.

4. **Catálogo oficial como dado versionado.** Os códigos dos registros "código+valor" entram como arquivo de dados com versão do leiaute, URL da fonte, data e hash, e um leitor que recusa código fora dele. Não existe modo "aceita qualquer código". Se uma tabela não puder ser obtida, **os registros que dependem dela ficam bloqueados e declarados em `docs/gaps.md`**, em vez de gerados sem conferência.

5. **Indicadores do Bloco 0 como configuração por empresa e ano-calendário.** Um DocType próprio ("configuração da ECF"), não 40 Custom Fields em `Company`. Só os indicadores que a matriz declarar obrigatórios existem; nenhum tem padrão. A tela distingue valor **confirmado** de **sugestão** (pré-preenchido do cadastro, a confirmar) e um valor salvo nunca é sobrescrito por sugestão. Uma coluna mostra por indicador o que ele comunica e o que a norma aceita.

6. **Aplicabilidade como porta, não como aviso.** A decisão "esta empresa entrega ECF?" é uma função pura de natureza jurídica, optante do Simples, atividade e regime, e a geração recusa antes de ler qualquer dado contábil. A mensagem nomeia o motivo, para o contador não procurar um botão que não existe.

7. **Montagem independente da EFD.** O montador de arquivo e o Bloco 9 da ECF ficam em `contabil/` com a projeção mínima própria, sem importar de `efd_*` (contextos delimitados distintos: duplicar um contador de linhas é mais barato que acoplar dois leiautes que mudam em calendários diferentes). A geração integrada segue o desenho de `integracao/geracao_efd.py` **com a checagem de permissão desde o primeiro commit**.

8. **Validação em duas camadas.** Estrutural, no CI: dicionário de registros do leiaute (nome, ordem, tipo, tamanho, obrigatoriedade) conferido contra cada registro emitido e contagens recalculadas do texto. Material, fora do CI: o PVA da Receita, executado por uma pessoa e registrado em `docs/` com a versão. Nunca se escreve "validado no PVA" sem execução.

9. **Saúde por configuração, não por exceção no código.** O mapeamento de receita para atividade (hospitalar × demais serviços de saúde, entre outras) é uma tabela da empresa, sem padrão. O que conta como receita bruta é o que passa pelo faturamento fiscal; o que não tem documento fiscal é **listado como "não faturado"** para o contador decidir, sem presunção (entidade privada ou filantrópica conveniada ao SUS fatura o SUS, e isso é receita: o tratamento de convênio público fica para confirmar com contador e fonte). Como o Marley Health 16.6.1 fatura (se gera `Sales Invoice` ou usa fluxo próprio) **não está verificado**, a tarefa 2.2 lê o app instalado antes de fixar de onde a receita é lida.

## Risks / Trade-offs

- [O Manual muda por ano e a tabela dinâmica também] → cada dado e cada documento fixam versão do leiaute e data da fonte; geração recusa ano sem catálogo.
- [Parte B é domínio grande e fiscalmente delicado] → entrega só depois do Presumido; agregado com invariantes testadas; compensação de prejuízo com o limite vigente conferido na lei, com fonte, antes de codificar.
- [Sem PVA no CI, "gera arquivo" pode coexistir com "PVA rejeita"] → validação estrutural forte no CI e etapa humana registrada; o resultado da geração diz explicitamente que não foi validado.
- [Fontes secundárias para dispensa e imunidade] → a porta usa a regra mais conservadora (não dispensa por imunidade) e a tarefa 1.4 confere no texto da IN no DOU; divergência vira aviso, não bloqueio da entrega do resto.
- [Percentuais de presunção de saúde de memória são perigosos] → nenhum percentual entra no código sem a norma citada e conferida (tarefa 1.5).
- [Cobertura de bench] → `ecf_dados_empresa.py` ganha teste de bench antes de qualquer geração integrada; `MODULOS_COBERTOS` declarado.

## Migration Plan

Nada a migrar: não há ECF gerada hoje. Os DocTypes novos entram por `bench migrate`; `setup/` declara qualquer Custom Field. Rollback é remover o hook e o botão: o arquivo gerado é só texto e registro, sem efeito sobre contabilidade existente.

## Open Questions

- Qual ano-calendário é o primeiro alvo de entrega? Não muda requisito nem tarefas, só qual versão do leiaute se baixa primeiro (grupo 1 resolve ao ler o Manual vigente).
