# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""ECF (Escrituração Contábil Fiscal): Bloco J — Plano de Contas e Mapeamento.

Por que existe — o primeiro corte de um item de backlog "do tamanho do bloco fiscal
inteiro sozinho"
------------------------------------------------------------------------------
ECF é grande demais para "só continuar" sem recortar uma fatia primeiro — mesma disciplina já
aplicada ao eSocial (`docs/rh-estado-esocial.md`) e ao CT-e/MDF-e antes deles. Levantamento
completo em `docs/ecf-estado.md`. Este módulo cobre a fatia mais barata e mais próxima de já
estar pronta: o Bloco J, porque a ECF **importa o plano de contas diretamente da ECD** — não
recadastra nada, reaproveita.

`J050` é `I050` com o `REG` trocado — confirmado, não suposto
------------------------------------------------------------------------------
Confirmado por fonte secundária (documentação técnica de ERP, mesmo padrão de confiança já
aceito para DeSTDA/S-1299/R-2099): o registro `J050` (Plano de Contas do Contribuinte) tem
exatamente os mesmos oito campos, na mesma ordem, que `ecd_i050.montar_i050` já produz —
`DT_ALT`, `COD_NAT`, `IND_CTA`, `NIVEL`, `COD_CTA`, `COD_CTA_SUP`, `CTA`. Isso não é coincidência
de nomenclatura: a própria documentação da Receita confirma que a ECF importa o Bloco J
diretamente da ECD, então os dois registros descrevem o mesmo dado. `montar_j050` delega
inteiramente a `montar_i050`, só trocando o valor de `REG`.

`COD_NAT` da ECF tem duas opções a mais que a ECD modela — não um conflito
------------------------------------------------------------------------------------------
A fonte lista `COD_NAT` do `J050` com seis valores (`01`-Ativo, `02`-Passivo, `03`-PL,
`04`-Resultado, **`05`-Compensação, `09`-Outras**) — dois a mais que os quatro que
`plano_de_contas.py`/`ecd_i050.py` modelam. Isso não é um conflito: contas de compensação e
"outras" são categorias que este projeto não tem no plano de contas (`plano_de_contas.ARVORE`
só tem os quatro grupos do Art. 178/187 da Lei 6.404/76) — o reuso de `montar_i050` continua
válido porque o subconjunto que ele produz (`01`-`04`) é um subconjunto legítimo do domínio mais
amplo do `J050`, não um valor fora da tabela.

O que fica de fora deste primeiro incremento
------------------------------------------------------
`J051` (mapeamento para o Plano de Contas Referencial da RFB) — mesma decisão de escopo já
tomada para `ecd_i051.montar_i051` (só o De-Para que o contribuinte escolheu informar, não a
tabela referencial inteira); `J053` (subcontas correlatas) e `J100` (centro de custos) — grupos
que este projeto não modela ainda (sem conceito de centro de custo em `plano_de_contas.py`).

Funções puras: nenhuma dependência do Frappe.
"""

from erpnext_brasil.contabil.ecd_i050 import ARVORE, montar_i050
from erpnext_brasil.contabil.plano_de_contas import Conta

__all__ = ["montar_j001", "montar_j050", "montar_j990"]


def montar_j001(tem_dados: bool) -> dict:
	"""Monta o registro `J001` — abertura do Bloco J."""
	return {"REG": "J001", "IND_DAD": "0" if tem_dados else "1"}


def montar_j050(data_alteracao: str, arvore: tuple[tuple[str, Conta], ...] = ARVORE) -> list[dict]:
	"""Monta o registro `J050` — delega inteiramente a `ecd_i050.montar_i050`, só
	trocando `REG` de `"I050"` para `"J050"` (ver docstring do módulo)."""
	return [{**linha, "REG": "J050"} for linha in montar_i050(data_alteracao, arvore)]


def montar_j990(quantidade_linhas: int) -> dict:
	"""Monta `J990` — encerramento do Bloco J, com a contagem de linhas do próprio
	bloco (mesma convenção de `destda.montar_0990`/`montar_g990`)."""
	return {"REG": "J990", "QTD_LIN": str(quantidade_linhas)}
