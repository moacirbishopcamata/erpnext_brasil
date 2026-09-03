# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Registros E300/E310/E311 do EFD-ICMS/IPI — apuração do ICMS-DIFAL e do FCP (EC 87/2015).

Fecha a última pendência de apuração do bloco E declarada em `docs/sped-fiscal.md`
("Registros E300/E310 (ICMS-DIFAL) — apuração distinta, não coberta"). Terceira e
última apuração do bloco, depois de E110 (operações próprias, `efd_icms_ipi.py`) e
E200/E210 (ICMS-ST, `efd_icms_st.py`).

Achado real: três registros de apuração, três tratamentos diferentes de estorno
------------------------------------------------------------------------------------------
Este é o tipo de divergência que só aparece lendo o layout de cada registro, nunca
supondo por analogia entre irmãos — a mesma lição que `modal`/`procEmi` do MDF-e × CT-e
já tinham dado neste projeto:

| Registro | Estorno de crédito | Estorno de débito |
|---|---|---|
| E110 (próprias) | campo dedicado `VL_ESTORNOS_CRED` | campo dedicado `VL_ESTORNOS_DEB` |
| E210 (ST) | **não existe campo** (tipo recusado) | **não existe campo** (tipo recusado) |
| E310 (DIFAL/FCP) | somado em `VL_OUT_DEB_DIFAL` | somado em `VL_OUT_CRED_DIFAL` |

No E310 isso está explícito no próprio nome do campo: `VL_OUT_DEB_DIFAL` é "Outros
débitos **e estornos de créditos**", e `VL_OUT_CRED_DIFAL` é "Outros créditos **e
estornos de débitos**". Não é interpretação — é o rótulo oficial do campo.

Achado real: o 3º caractere do `COD_AJ_APUR` confirma a estrutura posicional inteira
------------------------------------------------------------------------------------------------
`efd_icms_ipi.py` modelou o 3º caractere como "tributo" (`0` = ICMS próprio) e
`efd_icms_st.py` acrescentou `1` = ICMS-ST. O E311 fecha a tabela com `2` = ICMS
DIFAL/FCP, confirmado pela própria fonte ao listar os códigos `20`-`25` (o par
"3º+4º caractere") como outros débitos / estorno de créditos / outros créditos / estorno
de débitos / deduções / débito especial. Ou seja: a mesma tabela de seis tipos no 4º
caractere vale para as três apurações, e é o 3º que diz de qual apuração o código é.
`AjusteDifal` recusa código que não seja `2` ali, do mesmo jeito que os módulos irmãos.

As duas metades do E310 têm a mesma forma — e por isso são a mesma função
------------------------------------------------------------------------------------------
Dos 22 campos, 20 são dois blocos de 10 idênticos em estrutura (DIFAL nos campos 3-12,
FCP nos 13-22), com as mesmas quatro fórmulas de saldo. `_montar_metade` resolve uma
vez e é chamada duas vezes — não duas cópias com nomes trocados, que divergiriam na
primeira manutenção.

Divergência declarada: aqui a dedução excedente **não** levanta erro
------------------------------------------------------------------------------------
`montar_e110`/`montar_e210` levantam `EfdInvalido` quando a dedução supera o saldo
devedor, porque para aqueles dois registros não havia fonte confirmando o tratamento.
Para o E310 há: a fórmula oficial do campo 10 é "se (08 - 09) ≥ 0, então 10 = (08-09);
senão 10 = 0" — o piso em zero é a regra do próprio layout, não uma escolha deste
módulo. Implementado como a fonte manda, e a divergência entre os três registros fica
registrada aqui em vez de uniformizada por gosto.

Fora de escopo, deliberadamente
--------------------------------------
Os ajustes do E311 alimentam os quatro campos da metade **DIFAL** (confirmado pela
fonte: `VL_OUT_CRED_DIFAL`, `VL_OUT_DEB_DIFAL`, `VL_DEDUCOES_DIFAL`, `DEB_ESP_DIFAL`).
Como a fonte **não** confirma se — e como — um código do E311 se dirige à metade **FCP**,
os quatro campos equivalentes do FCP são parâmetros explícitos de `ApuracaoDifal`, não
derivados de ajuste. Inventar uma regra de roteamento DIFAL↔FCP sem fonte seria
exatamente o erro que este projeto evita.

Fontes e nível de confiança
--------------------------------
Layout campo a campo e as fórmulas de saldo: fonte secundária (`vriconsulting.com.br`,
guias 235 (E300), 258 (E310 vigente, a partir de 01/01/2017, com FCP) e 237 (E311)),
que reproduz o Guia Prático da RFB. **A versão do E310 importa**: existe uma anterior,
válida até 31/12/2016, sem a metade do FCP — este módulo implementa a vigente.
O site oficial da RFB (`sped.rfb.gov.br`) recusou conexão nesta rodada, mesmo obstáculo
já registrado em `docs/nfce-qrcode.md`.

Nome dos campos em ASCII (`VL_DEDUCOES_DIFAL`), não `VL_DEDUÇÕES_DIFAL`: a fonte
consultada escreve com acento em alguns pontos e sem em outros, variação de transcrição —
identificador de layout SPED é ASCII, e a escolha aqui é consistente com
`VL_DEDUCOES_ST` de `efd_icms_st.py`.

Funções puras: nenhuma dependência do Frappe.
"""

from collections.abc import Sequence
from dataclasses import dataclass, fields
from decimal import Decimal

from erpnext_brasil.contabil.efd_icms_ipi import (
	POSICAO_TIPO,
	POSICAO_TRIBUTO,
	TAMANHO_COD_AJ_APUR,
	EfdInvalido,
)

__all__ = [
	"IND_MOV_COM_OPERACOES",
	"IND_MOV_SEM_OPERACOES",
	"TRIBUTO_ICMS_DIFAL",
	"AjusteDifal",
	"ApuracaoDifal",
	"montar_e300",
	"montar_e310",
	"montar_e311",
]

ZERO = Decimal("0.00")

TRIBUTO_ICMS_DIFAL = "2"
"""3º caractere do `COD_AJ_APUR` para a apuração do DIFAL/FCP — ver docstring."""

IND_MOV_SEM_OPERACOES = "0"
IND_MOV_COM_OPERACOES = "1"

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


@dataclass(frozen=True)
class AjusteDifal:
	"""Um ajuste da apuração do DIFAL/FCP — vira uma linha E311 e soma no campo certo
	do E310.

	Aceita os seis tipos (diferente de `efd_icms_st.AjusteSt`, que recusa os dois de
	estorno): no E310 os estornos **têm** destino, somados nos campos "outros" do lado
	oposto — estorno de crédito soma em débito, estorno de débito soma em crédito (ver
	docstring do módulo).
	"""

	codigo: str
	descricao: str
	valor: Decimal

	def __post_init__(self) -> None:
		if len(self.codigo) != TAMANHO_COD_AJ_APUR:
			raise EfdInvalido(
				f"COD_AJ_APUR deve ter {TAMANHO_COD_AJ_APUR} caracteres "
				f"(ex. 'MG200001'), recebido {self.codigo!r}"
			)

		if self.codigo[POSICAO_TRIBUTO] != TRIBUTO_ICMS_DIFAL:
			raise EfdInvalido(
				f"3º caractere de {self.codigo!r} deve ser {TRIBUTO_ICMS_DIFAL!r} (ICMS "
				"DIFAL/FCP) para um ajuste de E311 — '0' é operações próprias (E111) e "
				"'1' é ICMS-ST (E220)"
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


@dataclass(frozen=True)
class ApuracaoDifal:
	"""Os valores da apuração do DIFAL e do FCP que não vêm de ajuste do E311.

	`total_debitos`/`total_creditos` do DIFAL são o que
	`fiscal.impostos.icms.calcular_difal` produz por documento, somado no período —
	o mesmo dado que o `ICMSUFFim` da NF-e/CT-e carrega. Os campos `_fcp` são a metade
	do Fundo de Combate à Pobreza, que o mesmo cálculo já devolve (`fcp`).

	Os quatro campos `*_fcp` de ajuste (`outros_debitos_fcp`, `outros_creditos_fcp`,
	`deducoes_fcp`, `debito_especial_fcp`) são explícitos, não derivados do E311 — ver
	"Fora de escopo" na docstring do módulo.
	"""

	total_debitos: Decimal = ZERO
	total_creditos: Decimal = ZERO
	saldo_credor_anterior: Decimal = ZERO
	total_debitos_fcp: Decimal = ZERO
	total_creditos_fcp: Decimal = ZERO
	saldo_credor_anterior_fcp: Decimal = ZERO
	outros_debitos_fcp: Decimal = ZERO
	outros_creditos_fcp: Decimal = ZERO
	deducoes_fcp: Decimal = ZERO
	debito_especial_fcp: Decimal = ZERO

	def __post_init__(self) -> None:
		for campo in fields(self):
			valor = getattr(self, campo.name)

			if valor < ZERO:
				raise EfdInvalido(f"{campo.name} não pode ser negativo, recebido {valor}")


def montar_e300(uf: str, data_inicial: str, data_final: str) -> dict:
	"""Campos do E300 — o período de apuração do DIFAL/FCP **de uma UF**.

	Mesma forma do E200 (ST): se repete por UF, não é um só por período como o E110.
	"""
	if len(uf) != 2 or not uf.isalpha():
		raise EfdInvalido(f"UF deve ter 2 letras, recebido {uf!r}")

	return {"REG": "E300", "UF": uf.upper(), "DT_INI": data_inicial, "DT_FIN": data_final}


def montar_e311(ajustes: Sequence[AjusteDifal]) -> list[dict]:
	"""Uma linha E311 por `AjusteDifal` — mesma forma de E111/E220."""
	return [
		{"REG": "E311", "COD_AJ_APUR": a.codigo, "DESCR_COMPL_AJ": a.descricao, "VL_AJ_APUR": a.valor}
		for a in ajustes
	]


def _somar_por_tipo(ajustes: Sequence[AjusteDifal], tipo: str) -> Decimal:
	return sum((a.valor for a in ajustes if a.tipo == tipo), ZERO)


def _montar_metade(
	saldo_credor_anterior: Decimal,
	total_debitos: Decimal,
	outros_debitos: Decimal,
	total_creditos: Decimal,
	outros_creditos: Decimal,
	deducoes: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
	"""As três fórmulas de saldo, idênticas nas metades DIFAL e FCP do E310.

	Devolve `(saldo_devedor_antes_das_deducoes, a_recolher, saldo_credor_a_transportar)`,
	exatamente como o layout define:

	- devedor  = (débitos + outros débitos) - (saldo credor anterior + créditos + outros créditos), quando ≥ 0
	- recolher = devedor - deduções, quando ≥ 0 (**piso em zero pela própria fórmula
	  oficial** — divergência declarada em relação a E110/E210, ver docstring do módulo)
	- credor a transportar = o inverso do devedor, quando > 0
	"""
	debitos = total_debitos + outros_debitos
	creditos = saldo_credor_anterior + total_creditos + outros_creditos

	saldo = debitos - creditos

	devedor = saldo if saldo >= ZERO else ZERO
	credor_transportar = -saldo if saldo < ZERO else ZERO
	recolher = max(devedor - deducoes, ZERO)

	return devedor, recolher, credor_transportar


def montar_e310(apuracao: ApuracaoDifal, ajustes: Sequence[AjusteDifal] = ()) -> dict:
	"""Campos do registro E310 (versão vigente, a partir de 01/01/2017), na ordem do
	layout — 22 campos, sendo dois blocos de 10 com a mesma estrutura (DIFAL e FCP).

	Os ajustes do E311 alimentam só a metade DIFAL (ver docstring do módulo); os
	valores equivalentes do FCP vêm de `ApuracaoDifal`. `IND_MOV_FCP_DIFAL` é derivado
	dos valores, nunca recebido em paralelo — mesma razão do `IND_MOV_ST` do E210.
	"""
	ajustes = list(ajustes)

	# Estorno de crédito soma em "outros débitos"; estorno de débito, em "outros
	# créditos" — o rótulo oficial do campo diz isso literalmente.
	outros_debitos = _somar_por_tipo(ajustes, _TIPO_OUTROS_DEBITOS) + _somar_por_tipo(
		ajustes, _TIPO_ESTORNO_CREDITO
	)
	outros_creditos = _somar_por_tipo(ajustes, _TIPO_OUTROS_CREDITOS) + _somar_por_tipo(
		ajustes, _TIPO_ESTORNO_DEBITO
	)
	deducoes = _somar_por_tipo(ajustes, _TIPO_DEDUCAO)
	debito_especial = _somar_por_tipo(ajustes, _TIPO_DEBITO_ESPECIAL)

	devedor, recolher, credor_transportar = _montar_metade(
		apuracao.saldo_credor_anterior,
		apuracao.total_debitos,
		outros_debitos,
		apuracao.total_creditos,
		outros_creditos,
		deducoes,
	)

	devedor_fcp, recolher_fcp, credor_transportar_fcp = _montar_metade(
		apuracao.saldo_credor_anterior_fcp,
		apuracao.total_debitos_fcp,
		apuracao.outros_debitos_fcp,
		apuracao.total_creditos_fcp,
		apuracao.outros_creditos_fcp,
		apuracao.deducoes_fcp,
	)

	campos = {
		"REG": "E310",
		"IND_MOV_FCP_DIFAL": IND_MOV_SEM_OPERACOES,
		"VL_SLD_CRED_ANT_DIFAL": apuracao.saldo_credor_anterior,
		"VL_TOT_DEBITOS_DIFAL": apuracao.total_debitos,
		"VL_OUT_DEB_DIFAL": outros_debitos,
		"VL_TOT_CREDITOS_DIFAL": apuracao.total_creditos,
		"VL_OUT_CRED_DIFAL": outros_creditos,
		"VL_SLD_DEV_ANT_DIFAL": devedor,
		"VL_DEDUCOES_DIFAL": deducoes,
		"VL_RECOL_DIFAL": recolher,
		"VL_SLD_CRED_TRANSPORTAR_DIFAL": credor_transportar,
		"DEB_ESP_DIFAL": debito_especial,
		"VL_SLD_CRED_ANT_FCP": apuracao.saldo_credor_anterior_fcp,
		"VL_TOT_DEB_FCP": apuracao.total_debitos_fcp,
		"VL_OUT_DEB_FCP": apuracao.outros_debitos_fcp,
		"VL_TOT_CRED_FCP": apuracao.total_creditos_fcp,
		"VL_OUT_CRED_FCP": apuracao.outros_creditos_fcp,
		"VL_SLD_DEV_ANT_FCP": devedor_fcp,
		"VL_DEDUCOES_FCP": apuracao.deducoes_fcp,
		"VL_RECOL_FCP": recolher_fcp,
		"VL_SLD_CRED_TRANSPORTAR_FCP": credor_transportar_fcp,
		"DEB_ESP_FCP": apuracao.debito_especial_fcp,
	}

	# "Sem operações" é exatamente "nenhum valor informado" — derivado dos campos já
	# montados, sem uma segunda lista de valores que pudesse divergir desta.
	tem_movimento = any(
		valor != ZERO
		for chave, valor in campos.items()
		if chave.startswith("VL_") or chave.startswith("DEB_")
	)
	campos["IND_MOV_FCP_DIFAL"] = IND_MOV_COM_OPERACOES if tem_movimento else IND_MOV_SEM_OPERACOES

	return campos
