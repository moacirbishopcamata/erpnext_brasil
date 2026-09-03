# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Registros E200/E210/E220 do EFD-ICMS/IPI — apuração do ICMS-Substituição Tributária.

Por que é módulo próprio, e não mais funções dentro de `efd_icms_ipi.py`
--------------------------------------------------------------------------------
`docs/sped-fiscal.md` registrava E200/E210 como pendência declarada desde a
implementação do E110 ("apurações distintas de E110, não cobertas"). São apurações
mesmo — não é o E110 com outros nomes de campo:

- **Escopo por UF, não por empresa.** O E200 se repete por Unidade da Federação onde o
  contribuinte é inscrito como substituto tributário (ocorrência `1:N`), cada uma com seu
  próprio período. O E110 é um só por período, para a UF do próprio estabelecimento.
- **Composição de saldo diferente.** O E210 tem campos que não existem no E110
  (`VL_DEVOL_ST`, `VL_RESSARC_ST`, `VL_RETENCAO_ST`) e **não tem** os dois campos de
  estorno do E110 (`VL_ESTORNOS_CRED`/`VL_ESTORNOS_DEB`) — ver o achado abaixo.
- **`IND_MOV_ST`**: o E210 declara explicitamente "sem operações" (`0`) contra "com
  operações" (`1`); o E110 não tem esse indicador.

Fatorar num módulo próprio segue a mesma disciplina já usada nos blocos da ECF (um
arquivo por bloco) — não é o arquivo crescendo até caber tudo.

Achado real: a apuração da ST não tem campo de estorno
------------------------------------------------------------
O 4º caractere de `COD_AJ_APUR` admite seis tipos (ver `efd_icms_ipi`), mas o E210 só
tem destino para quatro deles — `0` (outros débitos → `VL_OUT_DEB_ST`), `2` (outros
créditos → `VL_OUT_CRED_ST`), `4` (deduções → `VL_DEDUCOES_ST`) e `5` (débitos especiais
→ `DEB_ESP_ST`). Os tipos `1` (estorno de créditos) e `3` (estorno de débitos) **não têm
campo correspondente** na apuração da ST, e a própria descrição do E220 confirma isso ao
enumerar exatamente esses quatro campos como os que ele discrimina. `AjusteSt` recusa os
tipos `1`/`3` em vez de somá-los em algum campo "parecido" — silenciar aqui produziria um
E210 que fecha aritmeticamente e mente sobre a natureza do lançamento.

`VL_AJ_CREDITOS_ST`/`VL_AJ_DEBITOS_ST` ficam zerados, deliberadamente
------------------------------------------------------------------------------
Mesma decisão (e mesma razão) já registrada para `VL_AJ_CREDITOS`/`VL_AJ_DEBITOS` no
E110: são ajustes **vinculados a um documento fiscal específico**, origem de dado
genuinamente diferente do ajuste "solto" que o E220 modela — fora de escopo declarado,
não "esquecido".

Fontes e nível de confiança, declarados
--------------------------------------------
- **`COD_AJ_APUR` com 8 caracteres e a estrutura por posição** (UF + tributo + tipo +
  sequencial): confirmado no **Guia Prático oficial** da EFD-ICMS/IPI publicado pela
  SEFAZ-GO (`goias.gov.br/economia/.../Guia_pratico_5.8.pdf`, layout do E111 declarando
  `008`, com códigos literais `GO040024`/`GO090004`). Foi o que revelou o bug corrigido
  em `efd_icms_ipi.Ajuste` na mesma rodada (exigia 4 caracteres).
- **Layout campo a campo de E200/E210/E220**: fonte secundária
  (`vriconsulting.com.br`, guias 142/143/144, que reproduzem o Guia Prático da RFB),
  cruzada com as descrições de TOTVS/Senior que concordam quanto ao propósito de cada
  registro e à relação E220 → E210. O site oficial da RFB (`sped.rfb.gov.br`) recusou
  conexão nesta rodada — mesmo obstáculo já registrado em `docs/inutilizacao-nfe.md` e
  `docs/nfce-qrcode.md`.

Formato de saída: dict de campo → valor, não a linha de texto do EFD — mesma separação de
responsabilidade de `efd_icms_ipi.py` (a serialização é `contabil/sped_texto.py`).

Funções puras: nenhuma dependência do Frappe.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from erpnext_brasil.contabil.efd_icms_ipi import (
	POSICAO_TIPO,
	POSICAO_TRIBUTO,
	TAMANHO_COD_AJ_APUR,
	TRIBUTO_ICMS_ST,
	EfdInvalido,
)

__all__ = [
	"AjusteSt",
	"ApuracaoSt",
	"montar_e200",
	"montar_e210",
	"montar_e220",
]

ZERO = Decimal("0.00")

IND_MOV_SEM_OPERACOES = "0"
IND_MOV_COM_OPERACOES = "1"

# Os quatro tipos de ajuste que têm destino no E210 — ver o achado na docstring do módulo.
_TIPO_OUTROS_DEBITOS = "0"
_TIPO_OUTROS_CREDITOS = "2"
_TIPO_DEDUCAO = "4"
_TIPO_DEBITO_ESPECIAL = "5"

_TIPOS_VALIDOS_ST = frozenset(
	{_TIPO_OUTROS_DEBITOS, _TIPO_OUTROS_CREDITOS, _TIPO_DEDUCAO, _TIPO_DEBITO_ESPECIAL}
)

_TIPOS_ESTORNO = frozenset({"1", "3"})


@dataclass(frozen=True)
class AjusteSt:
	"""Um ajuste da apuração do ICMS-ST — vira uma linha E220 e soma no campo certo do
	E210.

	Espelha `efd_icms_ipi.Ajuste`, com duas diferenças reais (não cosméticas): o 3º
	caractere precisa ser `1` (ICMS-ST, não operações próprias), e os tipos de estorno
	(`1`/`3`) são recusados porque o E210 não tem campo para eles — ver docstring do
	módulo.
	"""

	codigo: str
	descricao: str
	valor: Decimal

	def __post_init__(self) -> None:
		if len(self.codigo) != TAMANHO_COD_AJ_APUR:
			raise EfdInvalido(
				f"COD_AJ_APUR deve ter {TAMANHO_COD_AJ_APUR} caracteres "
				f"(ex. 'MG100001'), recebido {self.codigo!r}"
			)

		if self.codigo[POSICAO_TRIBUTO] != TRIBUTO_ICMS_ST:
			raise EfdInvalido(
				f"3º caractere de {self.codigo!r} deve ser {TRIBUTO_ICMS_ST!r} (ICMS-ST) para um "
				"ajuste de E220 — operações próprias se discriminam no E111 "
				"(ver contabil/efd_icms_ipi.py)"
			)

		tipo = self.codigo[POSICAO_TIPO]

		if tipo in _TIPOS_ESTORNO:
			raise EfdInvalido(
				f"4º caractere {tipo!r} é estorno, e a apuração do ICMS-ST não tem campo de "
				"estorno (o E210 só tem outros débitos/outros créditos/deduções/débitos "
				"especiais) — ver docstring do módulo"
			)

		if tipo not in _TIPOS_VALIDOS_ST:
			raise EfdInvalido(
				f"4º caractere de {self.codigo!r} deve ser um de {sorted(_TIPOS_VALIDOS_ST)}, "
				f"recebido {tipo!r}"
			)

		if self.valor < ZERO:
			raise EfdInvalido(f"valor do ajuste não pode ser negativo, recebido {self.valor}")

	@property
	def tipo(self) -> str:
		return self.codigo[POSICAO_TIPO]


@dataclass(frozen=True)
class ApuracaoSt:
	"""Os valores da apuração do ICMS-ST que **não** vêm de ajuste.

	Não reaproveita `contabil.apuracao_periodo.ApuracaoPeriodo` de propósito: aquele
	modela débito/crédito bruto de um tributo com não cumulatividade constitucional
	(`TRIBUTOS_APURAVEIS = {ICMS, IPI}`, escopo declarado lá), e a ST não é isso — o
	débito é o imposto **retido** de terceiro (`retencao`, que
	`fiscal.impostos.icms.calcular_icms_st` produz por item), e os créditos são
	devolução/ressarcimento, conceitos que não existem naquela classe. Duas classes com
	nomes próprios, mapeadas explicitamente, em vez de uma classe com campos que só
	valem em metade dos casos.
	"""

	retencao: Decimal
	saldo_credor_anterior: Decimal = ZERO
	devolucao: Decimal = ZERO
	ressarcimento: Decimal = ZERO

	def __post_init__(self) -> None:
		for nome, valor in (
			("retencao", self.retencao),
			("saldo_credor_anterior", self.saldo_credor_anterior),
			("devolucao", self.devolucao),
			("ressarcimento", self.ressarcimento),
		):
			if valor < ZERO:
				raise EfdInvalido(f"{nome} não pode ser negativo, recebido {valor}")


def montar_e200(uf: str, data_inicial: str, data_final: str) -> dict:
	"""Campos do E200 — o período de apuração da ST **de uma UF**.

	Repete-se por UF onde o contribuinte é substituto tributário (ocorrência `1:N` no
	layout), diferente do E110, que é um só por período. `data_inicial`/`data_final`
	saem no formato do SPED (`DDMMAAAA`) — a formatação em si é
	`contabil/sped_texto.py`, aqui os valores passam como vieram.
	"""
	if len(uf) != 2 or not uf.isalpha():
		raise EfdInvalido(f"UF deve ter 2 letras, recebido {uf!r}")

	return {"REG": "E200", "UF": uf.upper(), "DT_INI": data_inicial, "DT_FIN": data_final}


def montar_e220(ajustes: Sequence[AjusteSt]) -> list[dict]:
	"""Uma linha E220 por `AjusteSt` — mesma forma do E111, campos do layout oficial."""
	return [
		{"REG": "E220", "COD_AJ_APUR": a.codigo, "DESCR_COMPL_AJ": a.descricao, "VL_AJ_APUR": a.valor}
		for a in ajustes
	]


def _somar_por_tipo(ajustes: Sequence[AjusteSt], tipo: str) -> Decimal:
	return sum((a.valor for a in ajustes if a.tipo == tipo), ZERO)


def montar_e210(apuracao: ApuracaoSt, ajustes: Sequence[AjusteSt] = ()) -> dict:
	"""Campos do registro E210, na ordem do layout.

	    `IND_MOV_ST` é derivado, não parâmetro: "sem operações" é exatamente o caso em que
	    nenhum valor e nenhum ajuste foi informado — deixar o chamador declarar isso em
	    paralelo aos valores permitiria os dois divergirem (mesma razão de `AjusteIpi`
	    derivar `IND_AJ` do próprio código, em `efd_icms_ipi.py`).

	`VL_SLD_DEV_ANT_ST` é "saldo devedor **antes** das deduções" — por isso as deduções
	    (`VL_DEDUCOES_ST`) entram só no campo seguinte (`VL_ICMS_RECOL_ST = 11 - 12`), não na
	    composição do saldo. Débito especial (`DEB_ESP_ST`) fica fora da conta toda: é valor
	    extra-apuração, recolhido à parte — mesmo tratamento que `DEB_ESP` já tem no E110.
	"""
	ajustes = list(ajustes)

	out_cred = _somar_por_tipo(ajustes, _TIPO_OUTROS_CREDITOS)
	out_deb = _somar_por_tipo(ajustes, _TIPO_OUTROS_DEBITOS)
	deducoes = _somar_por_tipo(ajustes, _TIPO_DEDUCAO)
	deb_esp = _somar_por_tipo(ajustes, _TIPO_DEBITO_ESPECIAL)

	creditos = apuracao.saldo_credor_anterior + apuracao.devolucao + apuracao.ressarcimento + out_cred
	debitos = apuracao.retencao + out_deb

	saldo = debitos - creditos

	if saldo >= ZERO:
		if deducoes > saldo:
			raise EfdInvalido(
				f"Dedução ({deducoes}) maior que o saldo devedor apurado ({saldo}) — mesmo "
				"caso não coberto que o E110 já recusa, sem fonte confirmada para o "
				"tratamento correto"
			)

		sld_dev_ant = saldo
		icms_recol = saldo - deducoes
		sld_cred_transportar = ZERO
	else:
		sld_dev_ant = ZERO
		icms_recol = ZERO
		sld_cred_transportar = -saldo

	tem_movimento = any(
		valor != ZERO
		for valor in (
			apuracao.retencao,
			apuracao.saldo_credor_anterior,
			apuracao.devolucao,
			apuracao.ressarcimento,
			out_cred,
			out_deb,
			deducoes,
			deb_esp,
		)
	)

	return {
		"REG": "E210",
		"IND_MOV_ST": IND_MOV_COM_OPERACOES if tem_movimento else IND_MOV_SEM_OPERACOES,
		"VL_SLD_CRED_ANT_ST": apuracao.saldo_credor_anterior,
		"VL_DEVOL_ST": apuracao.devolucao,
		"VL_RESSARC_ST": apuracao.ressarcimento,
		"VL_OUT_CRED_ST": out_cred,
		"VL_AJ_CREDITOS_ST": ZERO,
		"VL_RETENCAO_ST": apuracao.retencao,
		"VL_OUT_DEB_ST": out_deb,
		"VL_AJ_DEBITOS_ST": ZERO,
		"VL_SLD_DEV_ANT_ST": sld_dev_ant,
		"VL_DEDUCOES_ST": deducoes,
		"VL_ICMS_RECOL_ST": icms_recol,
		"VL_SLD_CRED_ST_TRANSPORTAR": sld_cred_transportar,
		"DEB_ESP_ST": deb_esp,
	}
