# MDF-e operacional: emitir, encerrar e cancelar a partir do `Shipment`

Fecha o laço do manifesto: do cadastro (`Shipment`) à SEFAZ e de volta ao banco. É a frente 5 da mudança
`fechar-laco-cte-mdfe`. A montagem da árvore e a chave já existiam (`docs/mdfe-estado.md`); aqui está o que
liga isso a um clique.

## O fluxo

```text
Shipment (docstatus 1)
  └─ emitir_mdfe                       integracao/emissao_mdfe.py
       garantir_relogio_confiavel()    primeira instrução, antes de alocar número
       montar_mdfe_do_documento        árvore + chave (número alocado só depois de validar tudo)
       assinar_mdfe                    A1 da Company de pickup_company
       TransporteSefaz.transmitir_mdfe lote (MDFeRecepcao) → recibo → consulta (MDFeRetRecepcao)
       Transmissao Fiscal              gravado em qualquer desfecho, antes de qualquer erro
       Shipment.br_chave_acesso / br_protocolo_autorizacao   só quando autorizado
```

| Ação | Função | Evento | Quando a tela oferece |
|---|---|---|---|
| Emitir MDF-e | `emissao_mdfe.emitir_mdfe` | — (autorização) | não emitido ou rejeitado |
| Encerrar MDF-e | `eventos_mdfe.encerrar_mdfe` | `110112` | autorizado |
| Cancelar MDF-e | `eventos_mdfe.cancelar_mdfe` | `110111` | autorizado e **não encerrado** |

Estado e botões (`public/js/emissao_mdfe.js`, ligado ao `Shipment` em `hooks.py`): o servidor devolve a situação
fiscal **e** se a viagem foi encerrada (`estado_do_mdfe`) — encerrar não cancela, o manifesto segue autorizado —,
e uma tabela mapeia o estado aos botões. Estado fora da tabela (encerrado, cancelado, denegado) não oferece nada.

## Decisões e por quê

- **Lote e recibo, não o serviço síncrono.** O MDF-e tem também `MDFeRecepcaoSinc` (GZip+Base64), mas a
  tarefa 5.1 pede o lote. O `idLote` é o número do MDF-e (9 dígitos); um MDF-e por lote.
- **Lote ainda em processamento não é rejeição.** Depois das tentativas, a emissão para com o recibo na
  mensagem e **não grava** `Transmissao Fiscal` de rejeição (mentiria sobre o que a SEFAZ disse). O número
  alocado fica no `Shipment`; a reemissão o reaproveita.
- **A empresa vem de `pickup_company`.** O `Shipment` do core não tem `company`, o `Transmissao Fiscal` exige
  e a série sai da `Company` de origem da coleta. `empresa_do_shipment` expõe isso.
- **Só o `cStat` 100 autoriza.** Não há tabela confirmada de "autorizado fora do prazo" nem de uso denegado do
  MDF-e; a leitura do CT-e não foi copiada. Evento só é registrado com `135`.
- **Não reenvia o que já foi aceito.** Emitir um manifesto autorizado, encerrar um encerrado e cancelar um
  cancelado recusam antes de alocar número, assinar ou chamar a SEFAZ.
- **Encerrado não se cancela.** Guarda local, conservadora (ver "Não verificado").
- **Rejeição deixa rastro.** `throw` desfaz a transação; por isso o registro é gravado e há `commit` antes do
  erro. O teste-âncora dá `rollback` e relê por outro caminho.
- **Município de encerramento** = o de descarga do `Shipment`, ou o código IBGE informado; a UF sai dos dois
  primeiros dígitos. Encerrar por conta de terceiro (`indEncPorTerceiro`) não é coberto.
- **O 656 vale igual.** O consumo indevido bloqueia o envio do MDF-e e dos eventos **antes** da SEFAZ (a
  guarda está em `TransporteSefaz._contexto`) e a resposta passa por `_registrar`.

## O que não tem botão

Condutor (`110114`), inclusão de DF-e (`110115`), pagamento (`110116`), confirmação de serviço (`110117`) e
alteração de pagamento (`110118`) existem no domínio, mas **não têm dado no cadastro** para alimentá-los. Um
botão sem dado convidaria a digitar à mão o que o sistema deveria saber. Teste de costura trava isso.

## Estado de verificação

| O quê | Situação |
|---|---|
| Envelope SOAP (cabeçalho, namespace, ação), estrutura dos retornos | do XSD `PL_MDFe_300b` e do `sped-mdfe` — **fonte secundária**, não o MOC nem o WSDL |
| Códigos `103`, `105`, `100`, `135` | do `sped-mdfe` e da tabela comum aos três documentos — **não lidos no MOC** |
| `cUF` do cabeçalho SOAP = UF do emitente | herdado do CT-e por analogia — **confirmar em homologação** |
| Lógica Frappe | `tests_bench/test_emissao_mdfe.py` (5) e `test_eventos_mdfe.py` (10), transporte falso — **verdes em MariaDB e PostgreSQL** |
| Transporte | `tests/test_transporte_mdfe.py` (9): guarda com zero chamadas, `656`, evento assinado |
| Envio à SEFAZ de verdade | **não feito** — exige certificado A1 e homologação (tarefa 5.1) |
| Tela | **não aberta em navegador**; só teste de costura (`tests/test_botoes_mdfe.py`) |

## Os outros eventos do MDF-e ainda têm a forma da NF-e

Só o cancelamento e o encerramento foram corrigidos: raiz `eventoMDFe` (não `evento`) e o detalhe dentro de
`evCancMDFe`/`evEncMDFe`, como foi feito no CT-e. Os outros cinco montadores de `evento_mdfe.py` ainda devolvem a
forma antiga e a SEFAZ os recusaria — estão em `docs/gaps.md`.

## Onde está

| Peça | Arquivo |
|---|---|
| Envelopes SOAP | `fiscal/documento/soap_mdfe.py` |
| Leitura das respostas | `fiscal/documento/resposta_mdfe.py` |
| Eventos (raiz e assinatura) | `fiscal/documento/evento_mdfe.py` |
| Lote e recibo | `integracao/autorizacao_sefaz_mdfe.py` |
| Evento | `integracao/eventos_sefaz_mdfe.py` |
| Transporte | `integracao/transporte_sefaz.py` (`transmitir_mdfe`, `transmitir_evento_mdfe`) — **no limite de 320 linhas** |
| Emissão e eventos no site | `integracao/emissao_mdfe.py`, `integracao/eventos_mdfe.py` |
| Tela | `public/js/emissao_mdfe.js` |
| Campos novos no `Shipment` | `br_chave_acesso`, `br_protocolo_autorizacao` (`setup/campos_documento.py`) |
