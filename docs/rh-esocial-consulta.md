# eSocial: consulta de processamento de lote

Resolve o gap que `docs/rh-esocial-soap.md` tinha deixado explícito: o wrapper SOAP
`<consulta>` tinha nome confirmado, mas conteúdo (`ConsultaLoteEventos-v1_0_0.xsd`)
não lido. Lido agora — é simples: um campo só, `protocoloEnvio`.

## Formato do protocolo, confirmado com precisão

`A.B.NNNNNNNNNNNNNNNNNNN` — 23 caracteres exatos, três partes separadas por ponto:

- **`A`** (1 dígito): agente processador — `1` = Serpro, `2` = Caixa.
- **`B`** (1 dígito): ambiente — `1` = Produção, `2` = Pré-produção (dados reais),
  `3` = Pré-produção (dados fictícios), `6` = Homologação, `7` = Validação,
  `8` = Testes, `9` = Desenvolvimento.
- **`N`** (19 dígitos): sequencial.

Confirmado contra o XSD, que documenta o formato explicitamente e dá exemplos
literais (`1.1.0000000000000000001` para Serpro, `2.1.0000000000000000001` para
Caixa) — usados como os próprios casos de teste deste incremento, não valores
inventados.

## Um domínio de "ambiente" que não é o mesmo dos outros dois já vistos

Este projeto já modela dois domínios diferentes chamados "ambiente" dentro do
eSocial, e nenhum dos três é o mesmo:

| Onde | Valores | Significado |
|---|---|---|
| `esocial_s1200.AMBIENTE_PRODUCAO`/`AMBIENTE_PRODUCAO_RESTRITA` | 2 valores | Ambiente do **evento em si** (dentro de `ideEvento.tpAmb`) |
| `esocial_lote`/`esocial_soap` (implícito nos endpoints) | 2 conjuntos de URL | Ambiente da **infraestrutura de transmissão** |
| `esocial_consulta.AMBIENTE_*` (este módulo) | 7 valores | Ambiente de **quem processou o lote**, parte do protocolo |

Os três compartilham vocabulário ("ambiente") mas não são intercambiáveis — mesma
disciplina de `IdeEmpregadorLote` × `esocial_s1200.IdeEmpregador` já registrada em
`docs/rh-esocial-lote.md`: nome parecido não é motivo para tratar como o mesmo
conceito.

## Retroagiu: `esocial_retorno.DadosRecepcaoLote` ganhou validação real

`docs/rh-esocial-retorno.md` tinha registrado "formato exato de `protocolo_envio`
não confirmado, só o tamanho máximo validado". Com o formato agora confirmado,
`DadosRecepcaoLote.__post_init__` usa `esocial_consulta.protocolo_e_valido` em vez
da checagem de tamanho solta — a mesma regra vale nos dois lados (o protocolo que
chega na resposta de envio é o mesmo que vai na consulta depois).

## Arquivos

- `folha/esocial_consulta.py` — `montar_consulta_lote_eventos`, `protocolo_e_valido`,
  `PADRAO_PROTOCOLO_ENVIO`; camada pura, sem Frappe, testável sem bench.

## Fontes

- `github.com/nfephp-org/sped-esocial`,
  `schemes/comunicacao/v1_5_0/ConsultaLoteEventos-v1_0_0.xsd` — XSD literal, com
  documentação embutida do formato de `protocoloEnvio` e exemplos reais (Serpro,
  Caixa). Mesma família do `nfephp-org/sped-nfe` já usada para a NF-e, não a fonte
  primária oficial. Consultado em 2026-08-30.
