# MDF-e: modal rodoviário (`infModal/rodo`) — veículo e motorista

Segundo código do MDF-e, depois de `docs/mdfe-infdoc.md`. Fecha o espelho invertido já previsto
em `docs/mdfe-estado.md`: é aqui, não no CT-e, que veículo e motorista são identificados.

## Reuso: `RNTRC` é o mesmo tipo do CT-e

`type="TRNTRC"` no XSD do MDF-e é idêntico ao do CT-e (`[0-9]{8}|ISENTO`) — confirmado, não
suposto. `validar_rntrc`/`RntrcInvalido` são **importados** de `fiscal/cte_rodoviario.py`, não
reimplementados; `mdfe_rodoviario.py` reexporta `RntrcInvalido` para quem só importar deste
módulo não precisar saber que a exceção "mora" em outro arquivo.

## O que é genuinamente novo (sem equivalente no CT-e)

- `veicTracao` — o veículo principal: placa, tara (obrigatórios), RENAVAM/capacidade/tipo de
  carroceria (opcionais), **`tpRod`** (tipo de rodado: Truck/Toco/Cavalo Mecânico/VAN/
  Utilitário/Outros — só existe aqui, o reboque não tem) e **`condutor`** (até 10, mas ao menos
  um é obrigatório — confirmado no XSD, sem `minOccurs="0"`).
- `veicReboque` (até 3) — mesma forma de `veicTracao` **sem** `tpRod` nem `condutor`: um
  reboque não tem "tipo de rodado" nem motorista próprio. `montar_veiculo_reboque` é uma função
  separada de `montar_veiculo_tracao` exatamente por essa diferença de campos obrigatórios —
  não um parâmetro booleano numa função só, que esconderia a diferença de forma.

## Validação de `tara` — formato específico, não decimal comum

O XSD define `tara` como `0|[1-9]{1}[0-9]{0,5}` — `"0"` sozinho, ou um número **sem zero à
esquerda**. `"0850"` não é `"850"` para o schema, é uma string diferente que o padrão rejeita.
`_validar_tara` verifica isso explicitamente (testado: `test_tara_com_zero_a_esquerda_levanta_erro`).

## Arquivos

- `erpnext_brasil/fiscal/mdfe_rodoviario.py` — `Condutor`, `Veiculo`, `montar_condutor`,
  `montar_veiculo_tracao`, `montar_veiculo_reboque`, `montar_rodo`, `MdfeRodoviarioInvalido`.
- `erpnext_brasil/tests/test_mdfe_rodoviario.py` — 16 testes.

## O que ficou de fora

- `infANTT/infCIOT` (Código Identificador da Operação de Transporte) e `infANTT/valePed`
  (vale-pedágio obrigatório) — obrigações acessórias de frete terceirizado, com fornecedores/
  responsáveis próprios, fora do escopo deste incremento.
- `prop` (proprietário do veículo, só quando não é o emitente) — caso menos comum, não
  implementado.

## Fontes

- `github.com/nfephp-org/sped-mdfe`, `schemes/PL_MDFe_300b/mdfeModalRodoviario_v3.00.xsd`
  (`veicTracao` a partir da linha 496, `veicReboque` a partir da linha 718, `condutor` a partir
  da linha 638, arquivo baixado em 2026-08-31). Ver `docs/mdfe-estado.md` para o histórico da
  investigação.
