# eSocial S-1200: primeira fatia modelada

Depois de `docs/rh-estado-esocial.md` ter identificado que o eSocial inteiro é grande
demais para "só continuar" sem recortar uma fatia — o usuário escolheu o S-1200
(evento periódico de remuneração), por ser o mais próximo do que `folha/` já
calculava (INSS, IRRF).

## O que esta fatia cobre

Só os grupos verificados contra um XSD literal: `ideEvento`, `ideEmpregador`
(`TEmpregador`) e `TItemRemuneracao` (a linha de rubrica dentro de
`detVerbas`/`itensRemun`) — mais `linhas_de_inss_irrf`, a ponte que transforma os
valores já calculados por `folha/inss.py`/`folha/irrf.py` nessas linhas.

**Não cobre**: a árvore inteira do evento (`ideTrabalhador`, `dmDev`, `infoPerApur`,
`ideEstabLot`, `remunPerApur` — os grupos que aninham as linhas de rubrica dentro da
identificação do estabelecimento/lotação e do período), nem a serialização para XML,
assinatura ou envio — isso é a "camada de transporte", uma fatia à parte que ainda não
foi atacada (ver `docs/rh-estado-esocial.md`).

## Fonte do XSD: um obstáculo novo, diferente do "PDF digitalizado"

A página oficial de leiautes do eSocial S-1.3
(`gov.br/esocial/pt-br/documentacao-tecnica/leiautes-esocial-v-1.3`) é, ao contrário
da maioria das fontes `gov.br` deste projeto, **HTML acessível e legível** — mas
grande demais para as ferramentas de busca extraírem o XSD literal sem perda de
fidelidade: uma pergunta direta sobre a estrutura do S-1200 devolveu tipos
generalizados (`xs:string`, `complexType`) sem `pattern`/`totalDigits`/tamanhos
exatos, e uma segunda tentativa retornou só o sumário do evento S-1000, não o S-1200.
Um obstáculo estruturalmente diferente do "PDF digitalizado" já visto para INSS/FGTS
— aqui o texto é lido, só que resumido demais pela ferramenta antes de chegar à
resposta.

Resolvido pela mesma estratégia usada para os XSDs da NF-e: buscar um projeto
open-source de integração fiscal que publique o XSD literal, em vez do resumo da
página oficial. Encontrado em `github.com/tiagoravache/eSocial`
(`Exemplos/ACBrDFe/ACBreSocial2.0/Schemas/evtRemun.xsd`) — mesma categoria de fonte
que `nfephp-org/sped-nfe` já usada várias vezes neste projeto para os XSDs da NF-e,
não a fonte primária oficial. Os tamanhos/padrões usados aqui batem com o que uma
busca agregada independente confirmou para os códigos de incidência
(`codIncCP`/`codIncIRRF`/`codIncFGTS`), mas não houve leitura direta do XSD publicado
pelo próprio `gov.br/esocial`.

## Campos modelados

### `ideEvento`

| Campo | Tipo/tamanho | Observação |
|---|---|---|
| `indRetif` | dígito único | 1 = original, 2 = retificação |
| `nrRecibo` | 1-40 caracteres | Opcional no XSD, mas **obrigatório quando `indRetif=2`** — verificado como invariante deste módulo, confirmado via Perguntas Frequentes do eSocial |
| `perApur` | 4-7 caracteres | Formato `AAAA-MM`; só o tamanho é verificado, não o padrão exato (regex não confirmada nesta rodada) |
| `tpAmb` | dígito único | 1 = Produção, 2 = **Produção Restrita** — mesma numeração da NF-e, rótulo diferente para o código `2` (não é "Homologação") |
| `procEmi` | dígito único | Domínio de significado (1 = aplicativo do empregador? 2 = governamental?) não confirmado nesta rodada — só o formato (dígito 0-9) é validado |
| `verProc` | 1-20 caracteres | Versão do aplicativo emissor |

### `ideEmpregador` (`TEmpregador`)

`tpInsc` (dígito único) + `nrInsc` (8 a 15 dígitos) — só o formato é validado aqui,
não o dígito verificador de CNPJ/CPF (responsabilidade de `fiscal/validators`,
chamado por quem monta o evento, mesma separação de `nfe.py` não revalidar o que
`party.py` já valida na gravação do cadastro).

### `TItemRemuneracao`

`codRubr` (1-30 caracteres) + `vrRubr` (obrigatório) + opcionalmente
`ideTabRubr`/`qtdRubr`/`fatorRubr`/`vrUnit`. Quando os três últimos estão presentes,
`__post_init__` confere que `vrRubr ≈ qtdRubr × fatorRubr × vrUnit` (tolerância de 1
centavo) — quando ausentes (o caso de INSS/IRRF, informados como valor final direto),
`vrRubr` é aceito como está.

## Por que o código de rubrica nunca é inferido

`codRubr`/`ideTabRubr` vêm da tabela de rubricas do próprio empregador (evento
S-1010, cadastro prévio e específico de cada empresa) — este projeto não a modela.
`linhas_de_inss_irrf` recebe os códigos prontos do chamador, mesma disciplina de
`boleto.montar_codigo_barras` não inferir o `campo_livre`.

## Por que uma rubrica de valor zero ainda gera linha

O eSocial espera o INSS/IRRF do período mesmo quando o valor apurado é zero.
Condicionar a linha ao valor ser positivo esconderia "não calculei" atrás de "calculei
zero" — mesma leitura de "cada propriedade precisa comunicar o que o sistema sabe",
aplicada aqui a uma ausência de linha em vez de um campo vazio na tela.

## Ainda por implementar

- **`ideTrabalhador`, `dmDev`, `infoPerApur`, `ideEstabLot`, `remunPerApur`** — os
  grupos que envolvem as linhas de rubrica na árvore completa do evento.
- **Serialização XML, assinatura, envio, consulta de processamento** — a camada de
  transporte, arquitetura já mapeada em `docs/rh-estado-esocial.md` (SOAP, X.509
  SHA256, produção restrita).
- **Tabela de rubricas (S-1010)** e o cadastro do empregador (S-1000,
  pré-requisito de qualquer evento) — não modelados.
- **Leitura direta do XSD oficial `gov.br/esocial`** — hoje só via projeto
  open-source de terceiro; se a fonte oficial se tornar extraível de forma confiável
  no futuro, vale reconferir os campos aqui contra ela.

## Arquivos

- `folha/esocial_s1200.py` — `IdeEvento`, `IdeEmpregador`, `ItemRemuneracao`,
  `linhas_de_inss_irrf`; camada pura, sem Frappe, testável sem bench.

## Fontes

- `gov.br/esocial/pt-br/documentacao-tecnica/leiautes-esocial-v-1.3` — página oficial
  acessível, consultada mas insuficiente para extrair o XSD literal do S-1200 com as
  ferramentas disponíveis nesta sessão (ver acima).
- `github.com/tiagoravache/eSocial`,
  `Exemplos/ACBrDFe/ACBreSocial2.0/Schemas/evtRemun.xsd` — XSD literal usado para os
  tipos e tamanhos de `ideEvento`/`ideEmpregador`/`TItemRemuneracao`. Projeto
  open-source de integração fiscal brasileira, não fonte primária oficial.
  Consultado em 2026-08-30.
- Busca agregada às Perguntas Frequentes do `gov.br/esocial` — usada para confirmar
  `tpAmb` (1=Produção, 2=Produção Restrita) e a obrigatoriedade de `nrRecibo` quando
  `indRetif=2`.
