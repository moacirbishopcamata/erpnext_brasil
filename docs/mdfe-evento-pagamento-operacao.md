# MDF-e — Evento de Pagamento da Operação (`tpEvento` 110116, `evPagtoOperMDFe`)

## O que é

Registra como o frete da viagem foi pago — o evento mais complexo desta frente, com forma
compartilhada com o evento de alteração de pagamento (ver
`docs/mdfe-evento-alteracao-pagamento.md`). Fonte: `evPagtoOperMDFe_v3.00.xsd` (289 linhas,
lido inteiro).

## Estrutura

`infViagens` (quantidade e número da viagem, ambos `[0-9]{5}`, um grupo só, fora de
lista) e `infPag` (lista, um item por responsável pelo pagamento):

- `xNome` opcional (2-60).
- `(CPF|CNPJ|idEstrangeiro)` — **três** formas de identificar o responsável, não duas
  como a maioria dos grupos deste projeto (achado real: o MDF-e aceita responsável
  estrangeiro pelo pagamento).
- `Comp` (lista de componentes do frete): `01` Vale Pedágio, `02` Impostos, `03`
  Despesas, `04` Frete, `99` Outros — cada um com `vComp` e `xComp` opcional (mesmo
  para o tipo Outros, o XSD não exige `xComp`).
- `vContrato` (valor total do contrato).
- `indPag` (`0` à vista / `1` a prazo).
- `vAdiant` opcional — "usar apenas em pagamento à Prazo", regra de negócio aplicada
  neste módulo (rejeita se informado fora de `indPag=1`), não só decorativa.
- `indAntecipaAdiant` opcional (enumeração de um valor só, `"1"`).
- `infPrazo` opcional (lista de parcelas: `nParcela`, `dVenc`, `vParcela`) — "informar
  somente se indPag for à Prazo", mesma regra aplicada.
- `tpAntecip` opcional (`0` não permite / `1` permite / `2` permite mediante
  confirmação).
- `infBanc`, um `xs:choice` entre três formas de receber o pagamento: banco+agência,
  CNPJ de instituição de pagamento eletrônico do frete (`CNPJIPEF`), ou chave PIX.

## Achado real: `idEstrangeiro` tem uma restrição inconsistente no próprio XSD

`minLength=2`/`maxLength=20` combinados com um `xs:pattern`
(`([!-ÿ]{0}|[!-ÿ]{5,20})?`) que na prática aceita string **vazia** ou de 5 a 20
caracteres — nunca de 2 a 4, apesar do `minLength` declarado dizer "2". Este módulo valida
pelo `minLength`/`maxLength` documentados, não pelo padrão degenerado.

## Testes

11 testes novos entre os tipos compartilhados (`ComponentePagamento`, `InfoBancaria`,
`InfoPagamento`) e o evento em si, incluindo a regra "vAdiant/infPrazo só a prazo" e o
achado do `tpEvento` "110116" preencher o número que a confirmação do serviço (110117)
não usa.
