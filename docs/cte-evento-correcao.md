# CT-e: carta de correção (`evCCeCTe`, `tpEvento` 110110)

Fecha o último evento pendente citado em `docs/cte-evento-cancelamento.md`. Achado real e
grande: a CC-e do CT-e **não é texto livre** como a da NF-e.

## Estrutura, verificada campo a campo em `evCCeCTe_v4.00.xsd` (98 linhas, lido inteiro)

A NF-e tem `xCorrecao` — um campo de texto livre, 15 a 1000 caracteres, onde o emitente
escreve a correção em prosa. O CT-e tem `infCorrecao`, uma **lista repetível** de correções
estruturadas campo a campo — cada item:

- `grupoAlterado` (1-20 caracteres) — o grupo do XSD onde está o campo, ex. `"ide"`.
- `campoAlterado` (1-20 caracteres) — o nome do campo corrigido.
- `valorAlterado` (1-500 caracteres) — o novo valor.
- `nroItemAlterado` (opcional) — o índice, quando o campo corrigido está dentro de uma lista
  ("o índice inicia sempre em 1", confirmado no próprio XSD).

Modelar isso como texto livre (copiando a forma da NF-e sem verificar) teria perdido a
estrutura que o schema exige — o mesmo tipo de erro já evitado repetidas vezes neste projeto
ao verificar `modal`/`procEmi`/`ideEvento` entre CT-e e MDF-e antes de assumir.

## `xCondUso` cita uma base legal diferente — não é o mesmo texto com o nome trocado

A NF-e cita o § 1º-A do art. 7º do Convênio S/N de 15/12/1970. O CT-e cita o **Art. 58-B do
Convênio SINIEF 06/89** — norma diferente, texto integralmente diferente. A lista de
restrições também muda: a NF-e fala em "remetente ou destinatário"; o CT-e acrescenta
"emitente, tomador" — mais papéis, porque o CT-e envolve mais partes que uma nota fiscal de
mercadoria. `XCONDUSO_CCE_CTE` é uma constante nova, confirmada caractere a caractere no XSD,
não um reaproveitamento com o rótulo do documento trocado.

## `tpEvento` é o mesmo número da NF-e — confirmado, não coincidência assumida

`"110110"` bate exatamente com o código da carta de correção da NF-e. Testado explicitamente,
junto com a divergência estrutural — os dois fatos (código igual, corpo diferente) convivem
sem contradição.

## Diferença de regra de negócio sobre histórico

A NF-e exige que cada CC-e nova reúna o texto de todas as correções já feitas (regra de
negócio da SEFAZ sobre texto livre — não dá para "corrigir só uma parte" de um texto). O CT-e,
por ser estruturado, não tem essa exigência do mesmo jeito: cada carta é a lista de alterações
que ela reporta. Este módulo não impõe nenhuma das duas regras — é responsabilidade de quem
chama decidir o que incluir em `correcoes`.

## Arquivos

- `erpnext_brasil/fiscal/documento/evento_cte.py` — `CorrecaoCte`, `montar_evento_correcao_cte`,
  `TIPO_EVENTO_CORRECAO_CTE`, `XCONDUSO_CCE_CTE`.
- `erpnext_brasil/tests/test_evento_cte.py` — 9 testes novos (`TestMontarEventoCorrecaoCte`).

## Fontes

- `github.com/nfephp-org/sped-cte`, `schemes/PL_CTe_400/evCCeCTe_v4.00.xsd` (98 linhas, lido
  inteiro) — arquivo baixado e lido localmente em 2026-08-31/09-01. Ver
  `docs/cte-evento-cancelamento.md` para o histórico da investigação de eventos do CT-e.
