## Why

A ECF é a única obrigação da família SPED que o app ainda não consegue entregar. Hoje há peças soltas, sem arquivo: o Bloco J completo (menos `J053`), `K155`/`K156`, o núcleo do Bloco 0 (`0000`/`0001`/`0030`/`0990`) e, nos Blocos L, M, N e P, **só abertura e encerramento** (`L001`/`L990`, `M001`/`M990`, `N001`/`N990`, `P001`/`P990`). Não há montagem do arquivo, Bloco 9, contagem de linhas, geração a partir da empresa nem tela. Três bloqueios, documentados em `docs/ecf-estado.md`, `docs/ecf-blocos-l-m-n.md` e `docs/ecf-bloco-p.md`, explicam por que o trabalho parou:

1. o **catálogo de códigos da Receita** dos registros "código+valor" (17 dos 23 registros de conteúdo de L/M/N; 6 dos 10 de P) nunca foi lido na fonte;
2. o **controle da Parte B do LALUR/LACS** (Bloco M, 13 registros) pede um domínio que o app não tem: conta de controle fiscal com saldo que atravessa períodos;
3. os **indicadores regulatórios** do Bloco 0 (`0010`/`0020`/`0021`, mais de 40 perguntas) não têm valor padrão seguro e não há cadastro que as responda.

Cada bloqueio é uma decisão de modelagem, não um detalhe de preenchimento. Fechar a ECF exige tomá-las explicitamente, com a fonte oficial na mão, em vez de continuar entregando registros isolados que nunca formam um arquivo.

## What Changes

- **Ler a fonte primária antes de qualquer código**: Manual de Orientação da ECF (Leiaute 12, ADE Cofis nº 02/2026) e as tabelas dinâmicas da Receita, hoje conhecidos só por busca agregada. Produzir uma **matriz de obrigatoriedade por forma de tributação** (quais registros cada regime precisa para o PVA aceitar o arquivo, inclusive blocos fora dos sete do pedido, como o `Y`).
- **Arquivo ECF completo**: montagem na ordem do leiaute, Bloco 9 (`9001`/`9900`/`9990`/`9999`), contagem de linhas, geração a partir da empresa e do período para o `Arquivo SPED` do tipo `ECF`, com checagem de permissão desde o primeiro método exposto (lição de RT-02).
- **Porta de aplicabilidade**: a geração recusa, com motivo, quem a ECF não alcança — optante do Simples Nacional, órgão público, autarquia e fundação pública, pessoa jurídica inativa — em vez de produzir um arquivo inútil.
- **Fechar Bloco 0 e Bloco K**: os indicadores de `0010`/`0020`/`0021` viram configuração **explícita** da empresa, sem valor padrão, e a geração recusa enquanto houver pergunta sem resposta; `K030`/`K355`/`K356`; `0035`/`0930` só se a matriz de obrigatoriedade os exigir. `K915`/`K935` continuam preenchimento manual do usuário no PVA (já confirmado).
- **Lucro Presumido (Bloco P)** primeiro, por não depender do controle da Parte B: `P030`, `P100`, `P150` e as memórias de cálculo `P130`/`P200`/`P230`/`P300`/`P400`/`P500` sobre catálogo versionado e conferido.
- **Lucro Real (Blocos L, M, N)** depois: os sete registros do Bloco L (lista e campos a confirmar no Manual, ver `docs/ecf-blocos-l-m-n.md`); o **controle da Parte B** como domínio novo (conta de controle fiscal, movimentos de adição, exclusão e compensação, vínculo com o lançamento contábil); `M` e `N` derivados dele.
- **Aplicação ao módulo de saúde**, quando ele está em uso (hospital, clínica, laboratório privado): a presunção do Lucro Presumido depende da atividade, e os serviços hospitalares têm percentual diferente dos demais serviços de saúde; entidades filantrópicas e imunes não são dispensadas por serem imunes; e o laboratório municipal do SUS, sendo órgão público, **fica fora** da ECF (sua contabilidade é pública e vai ao SIAFIC, nunca substituído por este app). O mapeamento da receita para a atividade é configuração explícita, sem padrão.
- **Fora do pedido, declarado**: Blocos `C`, `E`, `T`, `U`, `X` e `S` (Entidades de Futebol), e `Y` salvo o que a matriz de obrigatoriedade mostrar como indispensável.
- **Sem prova de entrega**: o PVA da Receita valida o arquivo e a transmissão assinada é feita por ele. O app gera e confere a estrutura; a aceitação no PVA fica como etapa humana registrada, nunca marcada como feita sem execução.

## Capabilities

### New Capabilities

- `fiscal/ecf-arquivo`: geração do arquivo da ECF a partir da empresa e do período — aplicabilidade, Blocos 0, J, K e 9, ordem e contagem, registro no `Arquivo SPED`, permissão e recusa explícita de dado ou indicador faltante.
- `fiscal/ecf-lucro-presumido`: Bloco P para a empresa no Lucro Presumido, com presunção por atividade e memórias de cálculo conferidas contra o catálogo oficial.
- `fiscal/ecf-lucro-real`: Blocos L, M e N para a empresa no Lucro Real, incluindo o controle da Parte B do LALUR/LACS que atravessa períodos.

### Modified Capabilities

Nenhuma. A ECD e o SPED Fiscal já existentes não mudam de requisito; o reaproveitamento do plano de contas e dos saldos é leitura.

## Impact

- Código novo em `erpnext_brasil/contabil/` (registros, agregado da Parte B, montagem do arquivo — sem `frappe`) e `erpnext_brasil/integracao/` (geração a partir da empresa; fina, abaixo do limite de 320 linhas por módulo).
- DocTypes novos em `registros_fiscais/` para o controle da Parte B e para as respostas regulatórias do Bloco 0; Custom Fields declarados em `setup/` e campos lidos na integração cobertos por `tests_bench/`.
- Dados versionados do catálogo da Receita com fonte e hash, ao lado das listas de códigos existentes.
- Dependências: ECD (`ecd_i050`, `ecd_i150`) como origem de plano e saldos; `ecf_dados_empresa.py` (hoje sem teste de bench, RT-08) passa a ter cobertura.
- Risco regulatório: leiaute e tabelas mudam todo ano; cada documento gerado fixa versão do leiaute e data da fonte.
