# eSocial: montagem do evento assinado (serializar → assinar → mesclar → serializar)

Fecha a lacuna que `docs/rh-esocial-serializacao.md` tinha deixado explícita: como
combinar a árvore sem assinatura com a assinatura de verdade, sem que nenhum dos dois
módulos passe a depender do outro por completo.

## A sequência, e por que a ordem importa

1. Serializa a árvore **sem** `Signature` (`para_xml`).
2. Assina esses bytes (`Assinador.assinar`), usando o `Id` do elemento do evento como
   referência — a assinatura não existe antes de haver bytes para canonicalizar.
3. Mescla o `Signature` resultante como **irmão** do elemento do evento, dentro da
   mesma raiz `eSocial` — nunca dentro dele. Confirmado contra a estrutura já
   verificada do XSD do próprio evento (`eSocial` contendo `evtRemun` e `ds:Signature`
   como irmãos, ver `docs/rh-esocial-s1200.md`).
4. Serializa a árvore completa de novo, desta vez com a assinatura dentro.

## Continua puro: o assinador entra por injeção de dependência

`montar_evento_assinado(arvore, id_evento, assinador)` não importa `cryptography` nem
`lxml`, e não sabe que `AssinadorLocalEsocial` existe — recebe qualquer objeto que
implemente o `Protocol` `Assinador` (`folha/esocial_assinatura.py`). Mesma separação
porta/adaptador já usada para a NF-e
(`fiscal/documento/assinatura.Assinador` × `integracao/assinador_local.AssinadorLocal`),
aplicada aqui pela segunda vez no mesmo projeto.

Isso permite dois níveis de teste, e os dois foram escritos:

- **Orquestração isolada**, com `_AssinadorFalso` (nenhuma criptografia real) —
  prova que a árvore é montada certa, o `Signature` fica no lugar certo, o assinador
  recebe exatamente o XML sem assinatura e o `Id` correto.
- **Ponta a ponta**, com `AssinadorLocalEsocial` de verdade (certificado autoassinado
  em memória) — prova que as duas peças realmente se encaixam: o XML final assinado
  é bem formado (`lxml`), e a assinatura dentro dele **verifica** com a chave pública
  do certificado usando SHA-256. Não é só "a peça pura funciona" e "a peça
  criptográfica funciona" isoladas — é as duas juntas produzindo um documento que uma
  verificação de assinatura de verdade aceita.

## Genérico, não amarrado ao S-1200

`montar_evento_assinado` não conhece `evtRemun`/`ideEvento`/nada do S-1200 — só
espera uma árvore no formato `{"eSocial": {"@xmlns": ..., "<elementoDoEvento>":
{"@Id": ..., ...}}}`. Qualquer evento futuro (S-2200, S-2299, ...) que produza uma
árvore nesse formato usa a mesma função sem alteração nenhuma.

## O que ainda falta

- **Envio HTTP de verdade** — este módulo produz o XML assinado, pronto para entrar
  num `EventoLote` (`esocial_lote.py`); o `POST` SOAP com o lote em si ainda não
  existe.
- ~~Geração do `Id` de 36 caracteres~~ — resolvido em `docs/rh-esocial-id.md`
  (`folha/esocial_id.py::gerar_id_evento`); `montar_evento_assinado` continua
  recebendo `id_evento` como parâmetro, desacoplado de como ele foi gerado.
- **Múltiplas assinaturas num mesmo lote** — cada evento é assinado individualmente
  antes de entrar no envelope; a orquestração de assinar N eventos e montar um
  `LoteEventos` com eles ainda não foi escrita.

## Arquivos

- `folha/esocial_montagem.py` — `montar_evento_assinado`; camada pura (o assinador é
  injetado), sem Frappe, sem dependência direta de criptografia, testável sem bench.

## Fontes

- Nenhuma fonte externa nova — combina `esocial_serializacao.py`,
  `esocial_assinatura.py` e `integracao/assinador_esocial.py`, já verificados nos
  incrementos anteriores.
