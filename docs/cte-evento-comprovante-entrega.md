# CT-e: comprovante de entrega (`evCECTe`, `tpEvento` 110180)

Terceiro evento do CT-e implementado nesta frente — código próprio (`"110180"`), sem
equivalente na NF-e (a NF-e não tem um evento de confirmação de entrega pelo destinatário).

## Estrutura, verificada em `evCECTe_v4.00.xsd` (108 linhas, lido inteiro)

Quem recebeu a carga confirma o recebimento: `nProt` (protocolo do CT-e), `dhEntrega`,
`nDoc`/`xNome` (documento e nome de quem recebeu, 2-20 e 2-60 caracteres), `latitude`/
`longitude` opcionais (coordenadas do ponto de entrega — confirmadas como **string de 6 casas
decimais**, não decimal puro, `TLatitude`/`TLongitude`), `hashEntrega` (obrigatório) e
`dhHashEntrega`. `infEntrega` (opcional, até 2000) referencia as NF-e efetivamente entregues —
"informar o grupo apenas para CT-e com tipo de serviço Normal", confirmado no XSD.

## `hashEntrega` é um cálculo real, não um campo de texto livre

Confirmado no XSD: `base64Binary` de comprimento **20 bytes** — exatamente o tamanho de um
digest SHA-1, não coincidência (a própria documentação do campo descreve o hash como "SHA1 no
formato Base64 resultante da concatenação: Chave de acesso do CT-e + Base64 da imagem
capturada da entrega"). `calcular_hash_entrega` implementa isso de verdade: `hashlib.sha1`
sobre `chave + imagem_base64` (concatenação de **texto** — a imagem já entra como sua própria
representação Base64, não bytes brutos), devolvendo o digest recodificado em Base64. Testado
contra um cálculo de referência independente, e confirmado que o digest decodificado tem
exatamente 20 bytes.

## `hashEntrega` é calculado dentro da função de montagem, não recebido pronto

`montar_evento_comprovante_entrega_cte` chama `calcular_hash_entrega` internamente com a mesma
`chave_acesso` — mesma disciplina de `nfe.montar_ide` derivar `cDV` da própria chave, nunca
aceitar um valor pronto que poderia divergir da chave real do evento.

## Reuso: chave de NF-e validada da mesma forma que `fiscal.cte.montar_infnfe`

`infEntrega` usa `ler_chave` e recusa qualquer chave que não seja modelo `55` — mesma defesa em
profundidade já aplicada em `montar_infnfe`/`montar_infdoc` do MDF-e, evitando que uma chave de
CT-e ou MDF-e colada por engano só falhasse na rejeição da SEFAZ.

## Arquivos

- `erpnext_brasil/fiscal/documento/evento_cte.py` — `calcular_hash_entrega`,
  `montar_evento_comprovante_entrega_cte`, `TIPO_EVENTO_COMPROVANTE_ENTREGA_CTE`.
- `erpnext_brasil/tests/test_evento_cte.py` — 11 testes novos.

## O que ficou de fora

- `evCancCECTe` (cancelamento do próprio comprovante de entrega) — não investigado.
- `evIECTe`/`evCancIECTe` (Insucesso de Entrega e seu cancelamento) — não investigado.
- `evEPECCTe`, `evGTV`, `evPrestDesacordo`/`evCancPrestDesacordo`, `evRegMultimodal` — não
  investigados.

## Fontes

- `github.com/nfephp-org/sped-cte`, `schemes/PL_CTe_400/evCECTe_v4.00.xsd` (108 linhas, lido
  inteiro) e `tiposGeralCTe_v4.00.xsd` (`TLatitude`/`TLongitude`) — arquivos baixados e lidos
  localmente. Ver `docs/cte-evento-cancelamento.md` para o histórico da investigação de
  eventos do CT-e.
