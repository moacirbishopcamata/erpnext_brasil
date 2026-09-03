# ECF: Blocos L/M/N (núcleo do Lucro Real) — dimensionado

Fecha o dimensionamento pendente desde `docs/ecf-estado.md` ("provavelmente o maior
bloco sozinho, dependente de regras de ajuste fiscal não modeladas ainda") — confirmado
com detalhe real de campo, não mais uma estimativa. Fonte:
`documentacao.senior.com.br/.../bloco-{l,m,n}.htm`, mesmo padrão de confiança já
aceito para os demais blocos da ECF.

## Bloco L (Lucro Líquido) — sete registros

`L001`/`L990` (abertura/encerramento), `L030` (período/método de apuração — mesma
pendência de `K030`/`P030`), `L100` (Balanço Patrimonial), `L200` (método de avaliação
do estoque final — um indicador único, mas depende de decisão de negócio não
modelada), `L210` (composição de custos, formato "código+valor"), `L300`
(Demonstrativo do Resultado do Exercício).

`L100`/`L300` têm exatamente a mesma forma de `P100`/`P150` — plano de contas + saldo
— com a mesma dúvida real já registrada em `docs/ecf-bloco-p.md`: não está confirmado
se o `CODIGO` referencia o plano **próprio** da empresa ou o **referencial** da RFB.

## Bloco M (e-LALUR e e-LACS, Parte A e B) — treze registros, achado real: domínio inteiro ausente

`M001`/`M990` (abertura/encerramento), `M030` (período), e onze registros de conteúdo
(`M010` a `M510`) que implementam o **controle de Parte B do LALUR/LACS** — o
mecanismo de contas de controle fiscal que carregam, de um período para o outro, a
diferença entre resultado contábil e tributável (adições/exclusões temporárias,
compensação de prejuízo fiscal, tributação diferida com indicador próprio
`IND_LAN_ANT`, vínculo de cada lançamento do LALUR a um lançamento contábil real via
`NUM_LCTO`/`COD_CTA` em `M310`/`M360`).

**Achado real, decisivo**: este projeto **não tem, em lugar nenhum, esse conceito** —
nenhuma "conta de controle fiscal" com saldo que atravessa períodos e concilia com
lançamentos contábeis específicos. Diferente dos Blocos J/K (onde a ECF literalmente
reaproveita dado que a ECD já produz), o Bloco M não tem nada para reaproveitar:
implementar qualquer registro de conteúdo exigiria desenhar esse domínio do zero — um
incremento do tamanho de um bloco inteiro novo (equivalente a abrir uma nova frente de
`contabil/`, não uma fatia de um bloco já mapeado).

## Bloco N (Cálculo do IRPJ/CSLL) — treze registros, mesmo padrão do Bloco K/P

`N001`/`N990` (abertura/encerramento), `N030` (período), e onze registros de conteúdo.
**Oito dos onze** (`N500`/`N600`/`N610`/`N620`/`N630`/`N650`/`N660`/`N670`) seguem o
mesmo formato genérico "código+descrição+valor" já visto nos Blocos K/P — cada um é
uma memória de cálculo (compensação de prejuízo fiscal, lucro operacional, isenção/
redução, estimativa mensal, cálculo final do IRPJ/CSLL) referenciando um catálogo de
códigos da Receita não verificado. `N605` (contas contábeis do lucro operacional)
depende de saber quais contas compõem "lucro operacional" — regra de negócio não
modelada. `N615` é um cálculo bem específico de incentivos regionais (FINOR/FINAM/
FUNRES) — baixa prioridade mesmo com o catálogo disponível.

## Por que não implementar mais do que abertura/encerramento agora

A mesma razão já registrada para os Blocos K/P, mas em escala maior aqui: a maioria
absoluta do conteúdo real dos três blocos (dezessete de vinte e três registros
somados) depende de um catálogo de códigos oficiais da Receita não verificado, e o
Bloco M especificamente exige um domínio de controle fiscal (LALUR Parte B) que este
projeto não tem nenhuma base para reaproveitar. Implementar uma função "aceita
qualquer código" para os registros de memória de cálculo, ou inventar um modelo de
Parte B sem fonte, produziria um arquivo estruturalmente válido mas com dado
inventado — pior que não implementar.

## O que foi implementado

`montar_l001`/`montar_l990`, `montar_m001`/`montar_m990`, `montar_n001`/`montar_n990`
— abertura e encerramento dos três blocos, mesma convenção trivial de todos os outros
blocos da ECF.

## Arquivos

- `erpnext_brasil/contabil/ecf_bloco_l.py`, `ecf_bloco_m.py`, `ecf_bloco_n.py`.
- `erpnext_brasil/tests/test_ecf_blocos_l_m_n.py` — 9 testes.

## Próximo passo real, se este bloco for retomado

Para desbloquear qualquer registro de conteúdo dos três blocos, é preciso, nesta
ordem: (1) o catálogo oficial de códigos da Receita para os registros "código+valor"
(Manual de Orientação do Contribuinte da ECF, texto oficial — não a fonte secundária
usada até aqui, que só confirma nomes de campo, não a tabela de valores); (2) para o
Bloco M especificamente, desenhar do zero o conceito de "conta de controle Parte B"
com saldo entre períodos — decisão de escopo do usuário sobre se vale a pena antes de
qualquer código.
