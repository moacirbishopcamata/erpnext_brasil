# CT-e — Informações da GTV (`tpEvento` 110170, `evGTV`)

## O que é

Registra as GTV (Guias de Transporte de Valores — o documento que acoberta o transporte de
numerário/cheque/moeda ao setor de valores) efetivamente transportadas por um CT-e. Sem
equivalente na NF-e. Fonte: `evGTV_v4.00.xsd` (255 linhas, lido inteiro).

## Estrutura

`infGTV` é uma **lista** (`maxOccurs="unbounded"`) — um único evento pode reportar várias GTV.
Cada item: `nDoc` (número, 1-20), `id` (identificador para diferenciar GTV de mesmo número —
AIDF ou id interno, 1-20), `serie`/`subserie` (opcionais, 1-3), `dEmi`, `nDV` (dígito
verificador, exatamente 1 caractere), `qCarga` (quantidade de volumes/malotes), `infEspecie`
(lista, ao menos uma — `tpEspecie` 1-Numerário/2-Cheque/3-Moeda/4-Outros, `vEspecie` opcional),
`rem`/`dest` (remetente/destinatário — mesma forma exata: CNPJ/CPF exclusivo, IE opcional, UF,
`xNome`), `placa`/`UF`(veículo)/`RNTRC` (todos opcionais).

## Achado real: `descEvento` tem duas grafias válidas no XSD

O schema aceita **duas** enumerações para `descEvento`: `"Informações da GTV"` (acentuada) e
`"Informacoes da GTV"` (sem acento) — não é erro de digitação deste projeto nem do XSD; as duas
são literalmente valores válidos da mesma `xs:enumeration`. Este módulo sempre **grava** a forma
acentuada (`DESC_EVENTO_GTV = "Informações da GTV"`), consistente com o restante do projeto, mas
documenta a divergência para quem for validar contra XML de terceiro.

## Reuso

- `validar_rntrc`/`RntrcInvalido` de `fiscal.cte_rodoviario` — mesmo `RNTRC`, mesmo padrão
  `[0-9]{8}|ISENTO`, sem inventar validação nova.
- `rem`/`dest` compartilham a mesma forma exata no XSD — modelados com um único tipo
  (`ParteGtv`) e uma única função de montagem (`montar_parte_gtv`), em vez de duas classes
  idênticas com nomes diferentes.

## Fora de escopo, documentado

`CNPJ` de `rem`/`dest` é `TCnpjOpc`, que aceita `"00000000000000"` para remetente/destinatário
não estabelecido no Brasil. `validar_cnpj` deste projeto rejeita ativamente CNPJ com todos os
dígitos iguais (incluindo zeros), por desenho (`fiscal/validators.py`) — decisão deliberada
contra dado-lixo consagrado. Este evento não abre uma exceção para esse caso: GTV de
remetente/destinatário estrangeiro não é suportado por enquanto.

## Testes

16 testes novos, incluindo: as duas grafias documentadas (com a acentuada sempre gravada),
múltiplas guias no mesmo evento, `RNTRC` reaproveitando `validar_rntrc`, e as validações
próprias de `InfGtv` (`nDV` de 1 caractere, ao menos uma espécie).
