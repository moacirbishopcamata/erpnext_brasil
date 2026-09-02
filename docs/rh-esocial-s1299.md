# eSocial S-1299 (Fechamento dos Eventos Periódicos) — o que "DCTFWeb" significa aqui

Investigado a pedido de retomar o backlog de obrigações acessórias ("DCTFWeb", item registrado
desde 2026-08-31). Achado que reformula o escopo do item inteiro do backlog.

## A DCTFWeb não é um arquivo que o contribuinte constrói

Confirmado por busca agregada: o sistema DCTFWeb é ativado **automaticamente pela Receita
Federal** depois que os eventos de fechamento do eSocial (S-1299, este documento) e do
EFD-Reinf (R-2099, ainda não implementado) são transmitidos com sucesso. Não existe um "leiaute
de DCTFWeb" para o contribuinte montar e enviar como arquivo — existe um evento de fechamento
que **dispara** a geração server-side da declaração. O campo `transDCTFWeb` do S-1299 confirma
isso diretamente: "Solicitação de transmissão imediata da DCTFWeb" — é literalmente o gatilho.

Isso muda o item do backlog de "implementar DCTFWeb" para "implementar os eventos de
fechamento que o consomem" — S-1299 (eSocial, este incremento) e R-2099 (EFD-Reinf, pendente).

## O evento, verificado contra o XSD literal

`evtFechaEvPer.xsd` (`nfephp-org/sped-esocial`) tem só 112 linhas — lido inteiro. Três grupos:

- `ideEvento` — tipo próprio `T_ideEvento_folha_sem_retificacao`.
- `ideEmpregador` — mesmo `TEmpregador` já usado no S-1200, reaproveitado direto.
- `infoFech` — os indicadores de quais eventos periódicos existiram no período, mais três
  campos de controle.

## `ideEvento` do S-1299 não é o mesmo tipo do S-1200 — verificado, não suposto

Confirmado por leitura direta de `tipos.xsd`: `T_ideEvento_folha_sem_retificacao` **não tem**
`indRetif`/`nrRecibo` (o fechamento não é retificado no mesmo sentido dos eventos de folha) e
**tem** um campo que o S-1200 não tem, `indGuia` (opcional). Reaproveitar
`esocial_s1200.IdeEvento` aqui produziria um objeto com campos que o XSD nem tem e sem um que
ele tem — mesma categoria de erro já evitada ao não reaproveitar o `modal` do CT-e no MDF-e.
Por isso `IdeEventoFechamento` é uma dataclass nova, testada explicitamente
(`test_ide_evento_fechamento_nao_tem_ind_retif`) para não virar um alias por acidente numa
refatoração futura.

## `indGuia`: campo quase vazio de propósito

Confirmado em fonte secundária (documentação técnica de ERP — mesmo padrão de confiança já
aceito para DeSTDA): `indGuia` só tem um valor definido hoje (`1` = DAE) e a própria
documentação do campo diz "será tratado em versões futuras" — não é uma enumeração incompleta
por falta de investigação, é o próprio leiaute ainda não ter mais opções.

## Reuso: `validar_digito_unico` virou pública

`esocial_s1200.py` tinha `_validar_digito_unico` como privada; ganhou uma segunda chamadora
real neste incremento e virou `validar_digito_unico` — mesmo motivo generalizar de
`integracao/party.uf_da_parte` (não suposição de uso futuro, motivo real e presente).

## O que não está neste incremento

- **R-2099** (fechamento do EFD-Reinf, também dispara DCTFWeb) — pendente, próximo natural.
- Verificação cruzada de que os indicadores `evt_*` batem com os eventos de fato enviados no
  lote — responsabilidade de quem monta o fechamento com acesso ao lote inteiro, não deste
  grupo isolado.
- GIA, ECF — continuam no backlog, não investigados nesta rodada.

## Arquivos

- `erpnext_brasil/folha/esocial_s1299.py` — `IdeEventoFechamento`, `InfoFechamento`,
  `montar_info_fech`.
- `erpnext_brasil/folha/esocial_s1200.py` — `validar_digito_unico` (renomeada de
  `_validar_digito_unico`).
- `erpnext_brasil/tests/test_esocial_s1299.py` — 11 testes.

## Fontes

- `github.com/nfephp-org/sped-esocial`, `schemes/v_S_01_03_00/evtFechaEvPer.xsd` (evento
  inteiro, 112 linhas) e `tipos.xsd` (`T_ideEvento_folha_sem_retificacao`, linha 93) — arquivos
  baixados e lidos localmente em 2026-08-31.
- `documentacao.senior.com.br/gestao-de-pessoas-hcm/esocial/leiautes/periodicos/s-1299.htm` —
  significado de `indGuia`, consultado em 2026-08-31.
