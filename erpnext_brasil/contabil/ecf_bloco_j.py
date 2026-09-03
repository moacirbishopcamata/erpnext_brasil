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

`J051` implementado em seguida — mesmo achado de reuso do `J050`
------------------------------------------------------------------------------
Confirmado na mesma fonte técnica: `J051` (mapeamento para o Plano de Contas Referencial da
RFB) tem exatamente os mesmos três campos, na mesma ordem, que `ecd_i050.montar_i051` já
produz — `REG`, `COD_CCUS`, `COD_CTA_REF`. Mesmo raciocínio do `J050`: a ECF importa o
mapeamento direto da ECD, não é coincidência de nomenclatura. `montar_j051` delega
inteiramente a `montar_i051`, só trocando `REG`.

`J053` (subcontas correlatas) e `J100` (centro de custos) — achado real de divergência
------------------------------------------------------------------------------------------
Confirmado na mesma fonte: `J053` (`REG`, `COD_IDT`, `COD_CNT_CORR`, `NAT_SUB_CNT`) **não**
tem equivalente na ECD — é específico de reorganização societária (subcontas correlatas
entre empresas incorporadas/fundidas), conceito que este projeto não modela. Fica
deliberadamente fora de escopo, mesmo que os outros dois registros do Bloco J tenham reuso
direto.

`J100` implementado como registro novo, mínimo
------------------------------------------------------------------------------
`J100` (`REG`, `DT_ALT`, `COD_CCUS`, `CCUS`) é só um cadastro de código+nome de centro de
custo — sem cálculo, sem regra de negócio. `plano_de_contas.py` não tem conceito de centro
de custo (documentado como fora de escopo no incremento anterior), mas `J100` é simples o
bastante para não precisar dele: `CentroCusto` é um tipo próprio deste módulo, autocontido,
sem tocar `plano_de_contas.py`. Isso fecha a lacuna que fazia `MapeamentoReferencial.
centro_custo` (`ecd_i050.py`) referenciar um código de centro de custo sem nenhum registro
que o declarasse.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass

from erpnext_brasil.contabil.ecd_i050 import ARVORE, montar_i050, montar_i051
from erpnext_brasil.contabil.plano_de_contas import Conta

__all__ = [
	"CentroCusto",
	"montar_j001",
	"montar_j050",
	"montar_j051",
	"montar_j100",
	"montar_j990",
]


def montar_j001(tem_dados: bool) -> dict:
	"""Monta o registro `J001` — abertura do Bloco J."""
	return {"REG": "J001", "IND_DAD": "0" if tem_dados else "1"}


def montar_j050(data_alteracao: str, arvore: tuple[tuple[str, Conta], ...] = ARVORE) -> list[dict]:
	"""Monta o registro `J050` — delega inteiramente a `ecd_i050.montar_i050`, só
	trocando `REG` de `"I050"` para `"J050"` (ver docstring do módulo)."""
	return [{**linha, "REG": "J050"} for linha in montar_i050(data_alteracao, arvore)]


def montar_j051(mapeamentos: list, arvore: tuple[tuple[str, Conta], ...] = ARVORE) -> list[tuple[str, dict]]:
	"""Monta o registro `J051` — delega inteiramente a `ecd_i050.montar_i051`, só
	trocando `REG` de `"I051"` para `"J051"` (ver docstring do módulo). Mesma
	semântica de aninhamento por posição: cada `(nome_da_conta, linha)` precisa ser
	inserido logo depois do `J050` daquela conta no arquivo final."""
	return [(nome, {**linha, "REG": "J051"}) for nome, linha in montar_i051(mapeamentos, arvore)]


@dataclass(frozen=True)
class CentroCusto:
	"""Um centro de custo — só código e nome, sem hierarquia (o `J100` não modela
	uma árvore, é uma lista plana)."""

	codigo: str
	nome: str


def montar_j100(centros: list[CentroCusto], data_alteracao: str) -> list[dict]:
	"""Monta o registro `J100` — um item por centro de custo cadastrado."""
	return [
		{"REG": "J100", "DT_ALT": data_alteracao, "COD_CCUS": centro.codigo, "CCUS": centro.nome}
		for centro in centros
	]


def montar_j990(quantidade_linhas: int) -> dict:
	"""Monta `J990` — encerramento do Bloco J, com a contagem de linhas do próprio
	bloco (mesma convenção de `destda.montar_0990`/`montar_g990`)."""
	return {"REG": "J990", "QTD_LIN": str(quantidade_linhas)}
