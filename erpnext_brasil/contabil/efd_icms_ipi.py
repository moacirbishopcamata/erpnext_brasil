# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Registros E110 e E520 do EFD-ICMS/IPI (SPED Fiscal) — apuração do ICMS e do IPI.

Por que EFD, não o "Registro de Entradas e Saídas" em papel
------------------------------------------------------------
O roteiro deste bloco pedia "apuração e livros (Registro de Entradas e Saídas, Apuração
de ICMS e de IPI)". Investigando antes de implementar: o **Ajuste SINIEF 02/2009**
dispensou, para quem é obrigado ao EFD-ICMS/IPI, a emissão e autenticação dos livros em
papel — Registro de Entradas, Registro de Saídas, Registro de Inventário, Registro de
Apuração do IPI e Registro de Apuração do ICMS. Hoje esse é o caso da esmagadora maioria
das empresas. Implementar o livro de papel seria construir um artefato que a lei já
tornou dispensável para quem mais importa — o alvo real é o **registro digital do EFD**
que o substitui, não a forma antiga.

O registro E110 traz exatamente o que `contabil/apuracao_periodo.ApuracaoPeriodo` (ICMS)
já calcula: débito bruto, crédito bruto, saldo credor anterior, saldo apurado, valor a
recolher, saldo credor a transportar. O registro **E520** faz o mesmo para IPI — layout
mais enxuto (8 campos, não 15: sem o equivalente a `VL_TOT_DED`), mas a mesma mecânica
de saldo mutuamente exclusivo (`VL_SC_IPI`/`VL_SD_IPI` correspondem a
`saldo_credor_a_transportar`/`a_recolher`, mesma inversão de `E110`). Por isso este
módulo é um **conversor**, não uma nova apuração — a conta já foi feita, aqui só se
organiza no formato que o Fisco espera. `E110` não é o registro de IPI — essa foi uma
suposição inicial errada (cheguei a cogitar "E200"), corrigida antes de escrever
qualquer código: E200/E210 são de ICMS-Substituição Tributária, E300/E310 são de ICMS-
DIFAL (EC 87/2015). A apuração do IPI vive no bloco E500-E530, não perto do E110/E2xx.

Escopo: E110/E111 (ICMS) cobrem ajuste real; E520 (IPI) ainda não
-------------------------------------------------------------------
O registro E110 tem 13 campos de valor; só 6 vêm direto de `ApuracaoPeriodo`. Os outros
7 são **ajustes de apuração** — cada um discriminado, no registro **E111** do mesmo
bloco, contra uma tabela de códigos própria por UF (Ato COTEPE/ICMS 09/2008, item
5.1.1, com fallback para a tabela federal quando o estado não tem tabela própria — a
mesma variação por UF já vista em `boleto.py`/`cnab400_retorno.py`: não modelada aqui,
o código vem pronto de quem chama).

`COD_AJ_APUR` tem **8 caracteres** — corrigido em 2026-09-03, ver
`docs/sped-fiscal.md`. A versão anterior deste módulo exigia 4, o que rejeitaria
**todo** código real da tabela 5.1.1 (`GO040024`, `GO090004`, `PE000001` — exemplos
literais do próprio Guia Prático). O tamanho `008` está declarado no layout oficial do
E111, e a estrutura por posição é:

| Posição | Conteúdo |
|---|---|
| 1-2 | Sigla da UF cuja tabela de ajuste define o código |
| 3 | Tributo: `0` = ICMS operações próprias, `1` = ICMS-ST |
| 4 | Tipo do lançamento (tabela abaixo) |
| 5-8 | Sequencial dentro da tabela da UF |

O **quarto** caractere decide para qual campo do E110 o valor do ajuste soma:

| 4º caractere | Tipo | Campo do E110 |
|---|---|---|
| `0` | Outros débitos | `VL_TOT_AJ_DEBITOS` |
| `1` | Estornos de crédito | `VL_ESTORNOS_CRED` |
| `2` | Outros créditos | `VL_TOT_AJ_CREDITOS` |
| `3` | Estornos de débito | `VL_ESTORNOS_DEB` |
| `4` | Deduções | `VL_TOT_DED` |
| `5` | Débitos especiais (extemporâneos) | `DEB_ESP` |

O **terceiro** caractere é o que separa este registro do E220 (ICMS-ST, ver
`contabil/efd_icms_st.py`): `Ajuste` exige `0` ali, e recusa um código de ST usado por
engano num E111 — os dois registros são de apurações diferentes, e o código carrega essa
informação.

`VL_AJ_DEBITOS`/`VL_AJ_CREDITOS` (os dois campos "não-total", distintos de
`VL_TOT_AJ_DEBITOS`/`VL_TOT_AJ_CREDITOS`) representam ajuste **vinculado a um documento
fiscal específico** — categoria diferente do ajuste "solto" que `Ajuste`/`montar_e111`
modelam aqui, e por isso ficam sempre zerados; não confundir com "ainda não suportado
por engano" (é uma origem de dado genuinamente diferente, fora de escopo declarado).

`montar_e110` recalcula `VL_SLD_APURADO`/`VL_ICMS_RECOLHER`/`VL_SLD_CREDOR_TRANSPORTAR`
somando os ajustes à fórmula — não reaproveita `ApuracaoPeriodo.a_recolher`/
`saldo_credor_a_transportar` direto, porque esses dois **não sabem de ajuste**
(`ApuracaoPeriodo` é escopo de débito/crédito bruto só, ver `docs/apuracao-periodica.md`).
Dedução (`VL_TOT_DED`) maior que o saldo devedor apurado é situação não coberta —
levanta erro explícito em vez de inventar um saldo credor originado de dedução (caso
raro, tratamento não confirmado em fonte).

`E530` faz o mesmo para IPI, com uma diferença estrutural importante: `COD_AJ`
**tem tabela nacional única**, publicada pela RFB (IN RFB 932/2009, atualizada pela IN
RFB 1009/2010) — não varia por UF como o `COD_AJ_APUR` do ICMS. A tabela usa faixa
numérica com natureza embutida: códigos `001`-`099` são crédito, `101`-`199` são
débito — por isso `AjusteIpi` deriva `IND_AJ` do próprio código, em vez de pedir os
dois separadamente (evita o chamador informar dois dados que podem divergir entre si).

Formato de saída: dict de campo → valor, não a linha de texto do EFD
------------------------------------------------------------------------
O layout de texto do SPED (campos separados por `|`, decimal com vírgula, escapes
próprios, um registro por linha dentro de um bloco) é uma preocupação de serialização
separada de "quais valores vão em quais campos". Resolver as duas juntas arriscaria
acertar o valor e errar o formato, ou vice-versa, sem teste dedicado para cada
responsabilidade — a mesma razão de `fiscal/documento/serializacao.py` separar a árvore
de dados do XML final. Este módulo só resolve a primeira.

Funções puras: nenhuma dependência do Frappe.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from erpnext_brasil.contabil.apuracao_periodo import ApuracaoPeriodo

__all__ = [
	"POSICAO_TIPO",
	"POSICAO_TRIBUTO",
	"TAMANHO_COD_AJ_APUR",
	"TRIBUTO_ICMS_PROPRIO",
	"TRIBUTO_ICMS_ST",
	"Ajuste",
	"AjusteIpi",
	"EfdInvalido",
	"montar_e110",
	"montar_e111",
	"montar_e520",
	"montar_e530",
]

ZERO = Decimal("0.00")

TAMANHO_COD_AJ_APUR = 8
"""Declarado como `008` no layout oficial do E111 — ver docstring do módulo."""

POSICAO_TRIBUTO = 2
"""Índice (base zero) do 3º caractere: `0` = ICMS próprio, `1` = ICMS-ST."""

POSICAO_TIPO = 3
"""Índice (base zero) do 4º caractere: o tipo do lançamento."""

TRIBUTO_ICMS_PROPRIO = "0"
TRIBUTO_ICMS_ST = "1"

# 4º caractere de COD_AJ_APUR — ver a tabela na docstring do módulo.
_TIPO_OUTROS_DEBITOS = "0"
_TIPO_ESTORNO_CREDITO = "1"
_TIPO_OUTROS_CREDITOS = "2"
_TIPO_ESTORNO_DEBITO = "3"
_TIPO_DEDUCAO = "4"
_TIPO_DEBITO_ESPECIAL = "5"

_TIPOS_VALIDOS = frozenset(
	{
		_TIPO_OUTROS_DEBITOS,
		_TIPO_ESTORNO_CREDITO,
		_TIPO_OUTROS_CREDITOS,
		_TIPO_ESTORNO_DEBITO,
		_TIPO_DEDUCAO,
		_TIPO_DEBITO_ESPECIAL,
	}
)


class EfdInvalido(ValueError):
	"""Dado de ajuste que não se encaixa no que os registros E110/E111 esperam."""


@dataclass(frozen=True)
class Ajuste:
	"""Um ajuste de apuração do ICMS — vira uma linha E111 e soma no campo certo do E110.

	`codigo` é o `COD_AJ_APUR` já resolvido por quem chama (tabela da UF do
	contribuinte, ou a federal quando o estado não tem tabela própria — Ato
	COTEPE/ICMS 09/2008, item 5.1.1) — este módulo não conhece nenhuma tabela de UF,
	só lê o 3º caractere (tributo) e o 4º (tipo).
	"""

	codigo: str
	descricao: str
	valor: Decimal

	def __post_init__(self) -> None:
		if len(self.codigo) != TAMANHO_COD_AJ_APUR:
			raise EfdInvalido(
				f"COD_AJ_APUR deve ter {TAMANHO_COD_AJ_APUR} caracteres "
				f"(ex. 'GO040024'), recebido {self.codigo!r}"
			)

		if self.codigo[POSICAO_TRIBUTO] != TRIBUTO_ICMS_PROPRIO:
			raise EfdInvalido(
				f"3º caractere de {self.codigo!r} deve ser {TRIBUTO_ICMS_PROPRIO!r} (ICMS operações "
				f"próprias) para um ajuste de E111 — {TRIBUTO_ICMS_ST!r} é ICMS-ST, que se "
				"discrimina no E220 (ver contabil/efd_icms_st.py)"
			)

		if self.codigo[POSICAO_TIPO] not in _TIPOS_VALIDOS:
			raise EfdInvalido(
				f"4º caractere de {self.codigo!r} deve ser um de {sorted(_TIPOS_VALIDOS)}, "
				f"recebido {self.codigo[POSICAO_TIPO]!r}"
			)

		if self.valor < ZERO:
			raise EfdInvalido(f"valor do ajuste não pode ser negativo, recebido {self.valor}")

	@property
	def tipo(self) -> str:
		return self.codigo[POSICAO_TIPO]


def montar_e111(ajustes: Sequence[Ajuste]) -> list[dict]:
	"""Uma linha E111 por `Ajuste` — ordem de campos oficial do Guia Prático EFD."""
	return [
		{"REG": "E111", "COD_AJ_APUR": a.codigo, "DESCR_COMPL_AJ": a.descricao, "VL_AJ_APUR": a.valor}
		for a in ajustes
	]


def _somar_por_tipo(ajustes: Sequence[Ajuste], tipo: str) -> Decimal:
	return sum((a.valor for a in ajustes if a.tipo == tipo), ZERO)


def montar_e110(apuracao: ApuracaoPeriodo, ajustes: Sequence[Ajuste] = ()) -> dict:
	"""Campos do registro E110, na ordem oficial do Guia Prático EFD-ICMS/IPI.

	Pré-condição: `apuracao.tributo` precisa ser `"ICMS"` — E110 é o registro de
	apuração do ICMS; IPI tem registro próprio (`E520`, ver `montar_e520`), layout
	diferente.

	`ajustes` (ver `Ajuste`/`montar_e111`) entra na fórmula de `VL_SLD_APURADO` —
	`ApuracaoPeriodo` sozinho não sabe de ajuste algum, só débito/crédito bruto.
	"""
	if apuracao.tributo != "ICMS":
		raise ValueError(f"E110 é o registro de apuração do ICMS, recebido tributo={apuracao.tributo!r}")

	ajustes = list(ajustes)

	tot_aj_debitos = _somar_por_tipo(ajustes, _TIPO_OUTROS_DEBITOS)
	estornos_cred = _somar_por_tipo(ajustes, _TIPO_ESTORNO_CREDITO)
	tot_aj_creditos = _somar_por_tipo(ajustes, _TIPO_OUTROS_CREDITOS)
	estornos_deb = _somar_por_tipo(ajustes, _TIPO_ESTORNO_DEBITO)
	tot_ded = _somar_por_tipo(ajustes, _TIPO_DEDUCAO)
	deb_esp = _somar_por_tipo(ajustes, _TIPO_DEBITO_ESPECIAL)

	# Débitos + ajustes + estornos, menos créditos, menos o saldo credor que já vinha
	# do período anterior — o mesmo formato que ApuracaoPeriodo.saldo usa, só que agora
	# com os ajustes somados aos dois lados.
	bruto = (
		apuracao.debitos
		+ tot_aj_debitos
		+ estornos_cred
		- apuracao.creditos
		- tot_aj_creditos
		- estornos_deb
		- apuracao.saldo_credor_anterior
	)

	if bruto >= ZERO:
		if tot_ded > bruto:
			raise EfdInvalido(
				f"Dedução ({tot_ded}) maior que o saldo devedor apurado ({bruto}) — "
				"caso não coberto, não há fonte confirmada para o tratamento correto"
			)

		sld_apurado = bruto
		icms_recolher = bruto - tot_ded
		sld_credor_transportar = ZERO
	else:
		sld_apurado = ZERO
		icms_recolher = ZERO
		sld_credor_transportar = -bruto

	return {
		"REG": "E110",
		"VL_TOT_DEBITOS": apuracao.debitos,
		"VL_AJ_DEBITOS": ZERO,
		"VL_TOT_AJ_DEBITOS": tot_aj_debitos,
		"VL_ESTORNOS_CRED": estornos_cred,
		"VL_TOT_CREDITOS": apuracao.creditos,
		"VL_AJ_CREDITOS": ZERO,
		"VL_TOT_AJ_CREDITOS": tot_aj_creditos,
		"VL_ESTORNOS_DEB": estornos_deb,
		"VL_SLD_CREDOR_ANT": apuracao.saldo_credor_anterior,
		"VL_SLD_APURADO": sld_apurado,
		"VL_TOT_DED": tot_ded,
		"VL_ICMS_RECOLHER": icms_recolher,
		"VL_SLD_CREDOR_TRANSPORTAR": sld_credor_transportar,
		"DEB_ESP": deb_esp,
	}


_IND_AJ_DEBITO = "0"
_IND_AJ_CREDITO = "1"

_IND_DOC_VALIDOS = frozenset({"0", "1", "2", "3", "9"})


@dataclass(frozen=True)
class AjusteIpi:
	"""Um ajuste de apuração do IPI — vira uma linha E530 e soma no campo certo do E520.

	`codigo` (`COD_AJ`) é da tabela **nacional** da RFB (IN RFB 932/2009, atualizada
	pela IN RFB 1009/2010) — `001`-`099` é crédito, `101`-`199` é débito. `ind_aj` não é
	parâmetro: é derivado do próprio código, para não deixar o chamador informar os dois
	separadamente e arriscar divergência (o mesmo motivo de `montar_infnfe` derivar a
	chave do `ide` em vez de aceitá-la em paralelo).
	"""

	codigo: str
	descricao: str
	valor: Decimal
	documento_indicador: str = "9"
	"""`IND_DOC` — origem do documento que respalda o ajuste; `"9"` (outros) é o padrão
	quando não há processo judicial/administrativo/PER-DCOMP específico a informar."""
	documento_numero: str = ""

	def __post_init__(self) -> None:
		if not (len(self.codigo) == 3 and self.codigo.isdigit()):
			raise EfdInvalido(f"COD_AJ deve ter 3 dígitos, recebido {self.codigo!r}")

		if not (1 <= int(self.codigo) <= 199):
			raise EfdInvalido(f"COD_AJ deve estar entre 001 e 199, recebido {self.codigo!r}")

		if self.valor < ZERO:
			raise EfdInvalido(f"valor do ajuste não pode ser negativo, recebido {self.valor}")

		if self.documento_indicador not in _IND_DOC_VALIDOS:
			raise EfdInvalido(
				f"IND_DOC deve ser um de {sorted(_IND_DOC_VALIDOS)}, recebido {self.documento_indicador!r}"
			)

	@property
	def ind_aj(self) -> str:
		"""`"0"` (débito, códigos 101-199) ou `"1"` (crédito, códigos 001-099) — a
		faixa 100 é reservada/inexistente na tabela da RFB."""
		numero = int(self.codigo)

		if numero <= 99:
			return _IND_AJ_CREDITO

		if numero >= 101:
			return _IND_AJ_DEBITO

		raise EfdInvalido(f"COD_AJ {self.codigo!r} (100) não existe na tabela da RFB — reservado")


def montar_e530(ajustes: Sequence[AjusteIpi]) -> list[dict]:
	"""Uma linha E530 por `AjusteIpi` — ordem de campos oficial do Guia Prático EFD."""
	return [
		{
			"REG": "E530",
			"IND_AJ": a.ind_aj,
			"VL_AJ": a.valor,
			"COD_AJ": a.codigo,
			"IND_DOC": a.documento_indicador,
			"NUM_DOC": a.documento_numero,
			"DESCR_AJ": a.descricao,
		}
		for a in ajustes
	]


def montar_e520(apuracao: ApuracaoPeriodo, ajustes: Sequence[AjusteIpi] = ()) -> dict:
	"""Campos do registro E520 ("Apuração do IPI"), na ordem oficial do Guia Prático.

	Pré-condição: `apuracao.tributo` precisa ser `"IPI"` — E520 é o registro de
	apuração do IPI; ICMS tem registro próprio (`E110`, ver `montar_e110`).

	`ajustes` (ver `AjusteIpi`/`montar_e530`) entra na fórmula do saldo — mesma
	disciplina de `montar_e110`/`Ajuste`: `ApuracaoPeriodo` sozinho não sabe de ajuste
	algum, só débito/crédito bruto. Diferente do E110, o E520 não tem campo de dedução
	(`VL_TOT_DED`) — a fórmula aqui é só débito mais outros débitos, menos crédito menos
	outros créditos menos saldo credor anterior.
	"""
	if apuracao.tributo != "IPI":
		raise ValueError(f"E520 é o registro de apuração do IPI, recebido tributo={apuracao.tributo!r}")

	ajustes = list(ajustes)

	outros_debitos = sum((a.valor for a in ajustes if a.ind_aj == _IND_AJ_DEBITO), ZERO)
	outros_creditos = sum((a.valor for a in ajustes if a.ind_aj == _IND_AJ_CREDITO), ZERO)

	bruto = (
		apuracao.debitos
		+ outros_debitos
		- apuracao.creditos
		- outros_creditos
		- apuracao.saldo_credor_anterior
	)

	if bruto >= ZERO:
		sd_ipi = bruto
		sc_ipi = ZERO
	else:
		sd_ipi = ZERO
		sc_ipi = -bruto

	return {
		"REG": "E520",
		"VL_SD_ANT_IPI": apuracao.saldo_credor_anterior,
		"VL_DEB_IPI": apuracao.debitos,
		"VL_CRED_IPI": apuracao.creditos,
		"VL_OD_IPI": outros_debitos,
		"VL_OC_IPI": outros_creditos,
		"VL_SC_IPI": sc_ipi,
		"VL_SD_IPI": sd_ipi,
	}
