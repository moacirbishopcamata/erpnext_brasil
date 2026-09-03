# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""eSocial: geração do `Id` de 36 caracteres de um evento.

Resolve o último gap de formato deixado pendente desde `docs/rh-esocial-s1200.md`
("o formato exato não foi verificado o bastante para implementar `montar_evt_remun`
gerando-o sozinho").

Composição, confirmada por duas fontes concordantes e por um exemplo literal
------------------------------------------------------------------------------------------
```
ID T NNNNNNNNNNNNNN AAAAMMDD HHMMSS QQQQQ
```

| Parte | Tamanho | Conteúdo |
|---|---|---|
| `ID` | 2 | texto fixo |
| `T` | 1 | tipo de inscrição do empregador — `1` = CNPJ, `2` = CPF |
| `N` | 14 | número do CNPJ/CPF do empregador, completado com **zeros à direita** |
| `AAAAMMDD` | 8 | data de geração do evento |
| `HHMMSS` | 6 | hora de geração do evento |
| `Q` | 5 | sequencial — só incrementa quando dois eventos são gerados no mesmo segundo |

Total: 2+1+14+8+6+5 = **36 caracteres**, batendo com o exemplo literal encontrado
(`ID2333901700001892014020213424700001`) posição a posição — usado aqui só para
confirmar a aritmética das posições, não o dígito de tipo de inscrição em si: o
`T` desse exemplo específico (`2`) não bate com o formato do número que o segue (que
tem cara de CNPJ, não CPF) — inconsistência da fonte terceira que o forneceu, não
usada para decidir o domínio de `tp_insc` (confirmado por uma segunda fonte
independente, que não tinha esse exemplo).

Por que "zeros à direita", não à esquerda
------------------------------------------------
Contraintuitivo para quem espera zero-padding numérico (à esquerda) — mas faz
sentido aqui: o CNPJ já tem 14 dígitos (não precisa de padding), e o CPF (11 dígitos)
precisa de 3 dígitos extras para completar 14. Preencher à esquerda deformaria o CPF
de verdade (ex. `00012345678901` pareceria outro número); à direita, o número real
continua legível no início da string (`12345678901000`).

Fora de escopo, deliberadamente
------------------------------------
- **Persistência do sequencial** entre chamadas no mesmo segundo — este módulo só
  formata o `Q` que recebe; decidir quando incrementar (dois eventos realmente
  gerados no mesmo segundo) é responsabilidade de quem chama, que tem visibilidade
  de todos os eventos sendo montados, não deste módulo isolado.
- **CNPJ representado só pela raiz (8 posições)**, caso especial de algumas
  classificações de contribuinte no S-1000 — não modelado; este módulo sempre espera
  o número completo (11 ou 14 dígitos) antes de completar com zeros à direita.

Funções puras: nenhuma dependência do Frappe.
"""

from datetime import datetime

__all__ = ["TIPO_INSCRICAO_CNPJ", "TIPO_INSCRICAO_CPF", "EsocialIdInvalido", "gerar_id_evento"]

TIPO_INSCRICAO_CNPJ = 1
TIPO_INSCRICAO_CPF = 2

_TAMANHO_NR_INSC_NO_ID = 14
_TAMANHO_ID = 36


class EsocialIdInvalido(ValueError):
	"""Dado que impede a geração do `Id` — tipo de inscrição, número ou sequencial
	fora do formato exigido."""


def gerar_id_evento(tp_insc: int, nr_insc: str, momento: datetime, sequencial: int = 1) -> str:
	"""Monta o `Id` de 36 caracteres do atributo `Id` de um evento do eSocial.

	`nr_insc` é o CNPJ (14 dígitos) ou CPF (11 dígitos) já limpo (sem máscara) — este
	módulo só completa com zeros à direita até 14, não valida dígito verificador
	(responsabilidade de `fiscal/validators`, como em todo o resto do bloco eSocial).
	`momento` é recebido pronto — quem chama decide se é `datetime.now()` ou um
	horário fixo (útil para reprocessar/testar de forma determinística).
	"""
	if tp_insc not in (TIPO_INSCRICAO_CNPJ, TIPO_INSCRICAO_CPF):
		raise EsocialIdInvalido(f"tp_insc deve ser 1 (CNPJ) ou 2 (CPF), recebido {tp_insc}")

	if not nr_insc.isdigit() or len(nr_insc) > _TAMANHO_NR_INSC_NO_ID:
		raise EsocialIdInvalido(
			f"nr_insc deve ter até {_TAMANHO_NR_INSC_NO_ID} dígitos numéricos, recebido {nr_insc!r}"
		)

	if not (1 <= sequencial <= 99999):
		raise EsocialIdInvalido(f"sequencial deve estar entre 1 e 99999, recebido {sequencial}")

	nr_insc_completo = nr_insc.ljust(_TAMANHO_NR_INSC_NO_ID, "0")
	data_hora = momento.strftime("%Y%m%d%H%M%S")

	id_evento = f"ID{tp_insc}{nr_insc_completo}{data_hora}{sequencial:05d}"

	assert len(id_evento) == _TAMANHO_ID, f"Id gerado com {len(id_evento)} caracteres, esperado {_TAMANHO_ID}"

	return id_evento
