# Levantamento de estado: ECF (Escrituração Contábil Fiscal)

Mesma disciplina de `docs/mdfe-estado.md`/`docs/rh-estado-esocial.md` — levantar antes de
implementar, recortar uma fatia. Registrado desde 2026-08-31 como "potencialmente do tamanho do
bloco fiscal inteiro sozinho" — confirmado nesta investigação.

## Dimensão confirmada

Leiaute 12 (2026), blocos: `0` (abertura/identificação), `C` (dados do lucro real anteriores,
não aplicável a esta fatia), `E`, `J` (plano de contas e mapeamento), `K` (saldos das contas
contábeis), `L`/`M`/`N` (o núcleo do Lucro Real — e-LALUR/e-LACS e cálculo de IRPJ/CSLL), `P`
(Lucro Presumido), `T`/`U`/`X`/`Y` (informações econômicas gerais, incentivos fiscais — novo
registro `Y730` no Leiaute 12, rastreabilidade de beneficiários de doações/incentivos), e o
Bloco `S` (novo no Leiaute 12, Tributação de Entidades de Futebol — TEF/SAF, fora de escopo por
ser regime setorial raro). Confirma a estimativa anterior: é grande demais para "só continuar"
sem recortar.

## A fatia mais barata: Bloco J, porque a ECF importa direto da ECD

Confirmado (não suposto): "a ECF importa dados diretamente da ECD para compor o Bloco J (Plano
de Contas e Mapeamento) e o Bloco K (Saldos das Contas Contábeis)". O registro `J050` (Plano de
Contas do Contribuinte) tem os mesmos oito campos, na mesma ordem, que `ecd_i050.montar_i050`
**já produz** — confirmado campo a campo contra fonte secundária (documentação técnica de ERP,
mesmo padrão de confiança já aceito para DeSTDA/S-1299/R-2099). **Implementado nesta mesma
investigação** — ver `docs/ecf-bloco-j.md`.

## `COD_NAT` da ECF tem mais opções que a ECD modela — achado real, não conflito

A fonte lista `COD_NAT` do `J050` com seis valores (`01`-Ativo, `02`-Passivo, `03`-PL,
`04`-Resultado, `05`-Compensação, `09`-Outras) — dois a mais que os quatro que
`plano_de_contas.py` modela. Não é um conflito: este projeto não tem contas de compensação nem
"outras" no plano de contas (só os quatro grupos do Art. 178/187), então o subconjunto que
`montar_i050` produz continua válido dentro do domínio mais amplo do `J050`.

## O que ainda falta investigar/implementar, em ordem de proximidade com o que já existe

1. **`J051`/`J053`/`J100`** — mapeamento referencial, subcontas correlatas, centro de custos.
   Mesma decisão de escopo do `I051` (só o De-Para que o contribuinte informar).
2. **Bloco K** (saldos das contas contábeis) — também "importado direto da ECD" segundo a
   mesma fonte; candidato natural a reuso de `ecd_i200`/`ecd_i250` (lançamentos já modelados),
   não investigado a fundo ainda.
3. **Bloco 0** — abertura/identificação, mesma convenção de `0000`/`0010` já vista em
   DeSTDA/EFD-Reinf; não investigado campo a campo ainda.
4. **Blocos L/M/N** — o núcleo do Lucro Real (e-LALUR/e-LACS, cálculo de IRPJ/CSLL). Não
   dimensionado — provavelmente o maior bloco sozinho, dependente de regras de ajuste fiscal
   (adições/exclusões ao lucro líquido) que este projeto não modela ainda.
5. **Bloco P** (Lucro Presumido) — regime tributário mais simples que o Lucro Real, candidato a
   vir antes de L/M/N se a maioria dos usuários-alvo deste app estiver no Simples/Presumido.
6. **Bloco Y** (incluindo `Y730`, novo no Leiaute 12) — informações econômicas gerais e
   rastreabilidade de incentivos fiscais.

## Nada além do Bloco J implementado nesta rodada

Este documento é levantamento geral; `docs/ecf-bloco-j.md` documenta o incremento de código
real feito na mesma investigação (o Bloco J, por já ter reuso direto e testado contra a ECD).

## Fontes

- Busca agregada sobre o Manual de Orientação da ECF Leiaute 12 (ADE Cofis nº 02/2026,
  publicado em `sped.rfb.gov.br`) — texto oficial não lido diretamente nesta rodada.
- `documentacao.senior.com.br/goup/5.10.3/menu_controladoria/sped/contabil-fiscal-ecf/
  bloco-j.htm` — campos do Bloco J, consultado em 2026-08-31.
