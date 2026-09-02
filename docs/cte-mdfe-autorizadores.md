# Autorizador/webservice por UF — CT-e e MDF-e

Fecha a pendência "autorizador/webservice por UF" registrada desde o marco de conclusão
dos eventos de CT-e e MDF-e (`docs/cte-estado.md`/`docs/mdfe-estado.md`). Mesmo papel que
`docs/transporte-nativo-sefaz.md` cumpre para a NF-e — mapear para onde cada UF manda o
SOAP —, mas a tabela é genuinamente diferente para cada documento, confirmado por leitura
direta, não presumido.

## CT-e (`fiscal/documento/autorizadores_cte.py`) — quatro grupos, não doze

Fonte: `nfephp-org/sped-cte`, `storage/wscte_4.00_mod57.xml` (endpoints) e
`storage/autorizadores.json` (mapa UF→grupo, chave `"57"`).

| Grupo | UFs | Quantidade |
|---|---|---|
| Webservice próprio | MG, MS, MT, PR, RS, SP | 6 |
| **SVRS** | AC, AL, AM, BA, CE, DF, ES, GO, MA, PA, PB, PI, RJ, RN, **RO**, SC, SE, TO | 18 |
| **SVSP** | AP, PE, RR | 3 |
| **AN** (só `CTeDistribuicaoDFe`, não autoriza) | — | — |

### Achado real: o mapa do CT-e diverge do da NF-e, mesmo para UFs com webservice próprio nos dois

`AM`, `BA`, `GO` rodam webservice **próprio** para NF-e (confirmado em
`docs/transporte-nativo-sefaz.md`) mas caem no **SVRS** (compartilhado) para CT-e. `PE`
também tem webservice próprio de NF-e, mas cai no **SVSP** para CT-e. Não é a mesma
infraestrutura entre os dois documentos, mesmo dentro da mesma UF e do mesmo emitente —
mais uma confirmação de que documentos "da mesma família" não compartilham webservice só
porque parece razoável presumir (mesma lição já repetida ao longo de toda a frente de
CT-e/MDF-e, agora aplicada à camada de transporte).

`RO` continua no grupo `SVRS` — mesmo grupo da NF-e, mas por coincidência de tabela, não
por regra geral (a lista de UFs do `SVRS` do CT-e não é a mesma do `SVRS` da NF-e).

`SVSP` é uma cópia funcional de `SP` (mesmo host, confirmado byte a byte); `SVRS` é uma
cópia funcional de `RS`, mesmo padrão já visto no `SVC-RS` da NF-e.

## MDF-e (`fiscal/documento/autorizadores_mdfe.py`) — um único autorizador nacional

Fonte: `nfephp-org/sped-mdfe`, `storage/wsmdfe_3.00.xml` e `storage/autorizadores.json`
(chave `"58"`).

**Achado real**: diferente da NF-e (12 grupos) e do CT-e (4 grupos), o MDF-e tem **um
único** autorizador para as 27 UFs (mais `"AN"`) — todas mapeiam para a mesma
infraestrutura, hospedada em `svrs.rs.gov.br`. Faz sentido pela natureza do documento: o
MDF-e representa uma viagem que tipicamente cruza fronteiras estaduais, então
nacionalizar o autorizador evita a UF de origem decidir sozinha para onde vai a
informação de uma viagem interestadual. Por isso `endpoint()` do módulo de MDF-e nem
recebe um mapa UF→grupo — o parâmetro `uf` existe só por uniformidade de assinatura com
os módulos irmãos, mas é ignorado.

## Testes

18 testes novos (11 para CT-e, 7 para MDF-e), incluindo a confirmação da divergência
AM/BA/GO/PE entre NF-e e CT-e, e que a UF não muda o resultado no MDF-e.

## O que ainda falta

Só a tabela de endpoints foi implementada — nem `fiscal/documento/soap.py`
(envelope SOAP) nem `integracao/transporte_sefaz.py` (adaptador de transmissão) foram
estendidos para usar essas tabelas em CT-e/MDF-e; hoje só servem a NF-e/NFC-e. Estender
o adaptador para os dois novos documentos é o próximo passo natural, mas ainda não
testável de ponta a ponta sem certificado A1/ambiente de homologação real — mesma
ressalva já registrada para a NF-e.
