# MDF-e — Evento de Inclusão de Condutor (`tpEvento` 110114, `evIncCondutorMDFe`)

## O que é

Permite adicionar um condutor à viagem depois do MDF-e já autorizado (ex.: troca de
motorista em trânsito). Fonte: `evIncCondutorMDFe_v3.00.xsd` (49 linhas, lido inteiro).

## Estrutura

`descEvento` fixo, e um único grupo `condutor` (`xNome` 2-60, `CPF`) — **não** uma lista. O
XSD só aceita um condutor por evento; para incluir mais de um, é preciso um evento por
condutor.

## Achado real: `descEvento` tem uma única grafia, sem acento

`"Inclusao Condutor"` — sem cedilha nem til, e o XSD não oferece variante acentuada
alternativa. Diferente de outros eventos desta mesma frente MDF-e/CT-e (`evGTV`,
`evPrestDesacordo`) que aceitam as duas grafias — aqui só existe a forma sem acento.

## Achado real: reuso direto de `fiscal.mdfe_rodoviario.Condutor`

O grupo `condutor` deste evento tem exatamente a mesma forma (`xNome`/`CPF`) já modelada em
`fiscal.mdfe_rodoviario.Condutor`/`montar_condutor` — usada dentro de `veicTracao` na
orquestração principal do MDF-e. Reaproveitados diretamente aqui, sem duplicar a validação
de CPF nem criar um segundo tipo `Condutor`.

## Testes

5 testes novos, incluindo a confirmação da grafia sem acento e o reuso correto de
`montar_condutor` (erro de CPF do evento propaga como `EventoInvalido`, não
`MdfeRodoviarioInvalido`, mantendo a disciplina de exceção única por módulo).
