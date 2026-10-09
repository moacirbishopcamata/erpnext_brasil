# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A prestação de serviço de transporte: os grupos de conteúdo de `infCte` e o orquestrador.

`fiscal/cte.py` já monta `ide` (com tomador), `infDoc/infNFe`, `ICMSUFFim` e assina; faltava
o **corpo** do CT-e — quem emite, quem contrata, quanto custa, que imposto incide, o que é
transportado e por qual modal — e o orquestrador que junta tudo em `infCte` na ordem do
`xs:sequence` e deriva a chave de acesso do próprio `ide` (mesma disciplina de
`fiscal.documento.nfe.montar_infnfe`: a chave nunca é informada em paralelo).

Cada grupo abaixo foi lido em `cteTiposBasico_v4.00.xsd` (`nfephp-org/sped-cte`,
`PL_CTe_400`, baixado em 2026-09-17), não suposto por analogia com a NF-e. Os achados que
divergem da NF-e, e por isso ganham teste:

- **`rem` e `dest` são opcionais** (`minOccurs="0"`, linhas 3621 e 3813) — diferente do
  `dest` da NF-e, obrigatório. Um CT-e de subcontratação, por exemplo, pode não os ter.
- **`emit` aceita CNPJ ou CPF** e exige `CRT` (linha 3542+), como o emitente do MDF-e e
  diferente do da NF-e (só CNPJ).
- **`vPrest` exige `vTPrest` e `vRec`** — o valor total **e** o valor a receber, que podem
  diferir (adiantamento, desconto). `Comp` é opcional.
- **`imp/ICMS` é `TImp`, um `xs:choice` de sete situações** (linha 6672); aqui entram as
  duas que a apuração deste app sabe produzir para transporte: `ICMS00` (tributação normal,
  regime normal) e `ICMSSN` (Simples Nacional: `CST 90` + `indSN 1`, linha 7027). As outras
  cinco levantam `CteInvalido`, nunca são inventadas.
- **`infCarga` exige `proPred` e ao menos um `infQ`** (linha 4019+); `vCarga` é opcional.
  `cUnid` é enumeração fechada de seis códigos (`00` M3 … `05` MMBTU, documentação inline do
  XSD, linhas 4069–4075).
- **`infModal` é um `xs:any` com atributo `versaoModal` obrigatório** (linha 4573) — o
  conteúdo do modal vem de `fiscal/cte_rodoviario.py`; este módulo só põe a versão.
- **`infCTeNorm` exige `infCarga` e `infModal`**; `infDoc` e `cobr` são opcionais.

Camada pura: sem `frappe`, testável com `unittest`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from erpnext_brasil.fiscal.cte import MODAL_RODOVIARIO, CteInvalido, IdentificacaoCte, montar_ide
from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.fiscal.impostos.icms import arredondar
from erpnext_brasil.fiscal.validators import validar_cpf_cnpj

__all__ = [
	"CST_ICMS_NORMAL",
	"CST_ICMS_SIMPLES",
	"MODELO_CTE",
	"UNIDADES_DE_CARGA",
	"UNIDADE_KG",
	"UNIDADE_LITROS",
	"UNIDADE_M3",
	"UNIDADE_MMBTU",
	"UNIDADE_TON",
	"UNIDADE_UNIDADE",
	"VERSAO_MODAL",
	"EmitenteCte",
	"ParteCte",
	"QuantidadeCarga",
	"montar_dest",
	"montar_emit",
	"montar_icms00",
	"montar_icmssn",
	"montar_imp",
	"montar_infcarga",
	"montar_infcte",
	"montar_infcte_norm",
	"montar_infmodal",
	"montar_rem",
	"montar_vprest",
]

MODELO_CTE = "57"
VERSAO_MODAL = "4.00"
"""`infModal/@versaoModal` — a versão do leiaute do modal, igual à do CT-e 4.00."""

CST_ICMS_NORMAL = "00"
CST_ICMS_SIMPLES = "90"

# `infCarga/infQ/cUnid` — enumeração e significado lidos na documentação inline do XSD.
UNIDADE_M3 = "00"
UNIDADE_KG = "01"
UNIDADE_TON = "02"
UNIDADE_UNIDADE = "03"
UNIDADE_LITROS = "04"
UNIDADE_MMBTU = "05"
UNIDADES_DE_CARGA = {
	UNIDADE_M3: "M3",
	UNIDADE_KG: "KG",
	UNIDADE_TON: "TON",
	UNIDADE_UNIDADE: "UNIDADE",
	UNIDADE_LITROS: "LITROS",
	UNIDADE_MMBTU: "MMBTU",
}


def _obrigatorio(valor, campo: str) -> str:
	texto = str(valor or "").strip()

	if not texto:
		raise CteInvalido(f"{campo} é obrigatório no CT-e e veio vazio", campo)

	return texto


def _valor(quantia) -> str:
	"""`TDec_1302`: duas casas, `ROUND_HALF_UP` — a mesma regra de todo valor do app."""
	return str(arredondar(Decimal(str(quantia or 0))))


def _percentual(fracao) -> str:
	"""`TDec_0302`: alíquota em **percentual** com duas casas. Dentro do app a alíquota é
	fração (`0.12`); esta é a única fronteira onde ela vira `12.00`."""
	return str(arredondar(Decimal(str(fracao or 0)) * 100))


# ---------------------------------------------------------------------------
# emit, rem, dest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EmitenteCte:
	"""A transportadora que emite. CNPJ **ou** CPF (transportador autônomo), IE e CRT."""

	cnpj_cpf: str
	nome: str
	regime_tributario: str
	"""CRT: 1 = Simples Nacional, 2 = Simples com excesso de sublimite, 3 = Regime Normal."""
	endereco: dict = field(default_factory=dict)
	inscricao_estadual: str = ""
	nome_fantasia: str = ""


@dataclass(frozen=True)
class ParteCte:
	"""Remetente ou destinatário da carga — mesma forma no XSD, só o nome do endereço muda."""

	nome: str
	cnpj_cpf: str
	endereco: dict = field(default_factory=dict)
	inscricao_estadual: str = ""
	email: str = ""


def _documento(parte_cnpj_cpf: str, papel: str) -> dict:
	try:
		documento = validar_cpf_cnpj(parte_cnpj_cpf)
	except ValueError as erro:
		raise CteInvalido(f"CNPJ/CPF do {papel} inválido: {erro}", "cnpj_cpf") from erro

	return {"CPF": documento} if len(documento) == 11 else {"CNPJ": documento}


def montar_emit(emitente: EmitenteCte) -> dict:
	"""`emit`, na ordem do XSD: CNPJ|CPF, IE, xNome, xFant, enderEmit, CRT."""
	grupo = _documento(emitente.cnpj_cpf, "emitente")

	if emitente.inscricao_estadual.strip():
		grupo["IE"] = emitente.inscricao_estadual.strip()

	grupo["xNome"] = _obrigatorio(emitente.nome, "razão social do emitente")

	if emitente.nome_fantasia.strip():
		grupo["xFant"] = emitente.nome_fantasia.strip()

	if not emitente.endereco:
		raise CteInvalido("emitente precisa de endereço (enderEmit é obrigatório)", "endereco")

	grupo["enderEmit"] = dict(emitente.endereco)
	grupo["CRT"] = _obrigatorio(emitente.regime_tributario, "regime tributário (CRT) do emitente")

	return grupo


def _parte(parte: ParteCte, papel: str, tag_endereco: str) -> dict:
	"""`rem`/`dest`: CNPJ|CPF, IE, xNome, ender*, email — ordem do XSD (linhas 3621 e 3813)."""
	grupo = _documento(parte.cnpj_cpf, papel)

	if parte.inscricao_estadual.strip():
		grupo["IE"] = parte.inscricao_estadual.strip()

	grupo["xNome"] = _obrigatorio(parte.nome, f"nome do {papel}")

	if not parte.endereco:
		raise CteInvalido(f"{papel} precisa de endereço ({tag_endereco} é obrigatório)", "endereco")

	grupo[tag_endereco] = dict(parte.endereco)

	if parte.email.strip():
		grupo["email"] = parte.email.strip()

	return grupo


def montar_rem(remetente: ParteCte) -> dict:
	return _parte(remetente, "remetente", "enderReme")


def montar_dest(destinatario: ParteCte) -> dict:
	return _parte(destinatario, "destinatário", "enderDest")


# ---------------------------------------------------------------------------
# vPrest e imp
# ---------------------------------------------------------------------------


def montar_vprest(valor_total, valor_receber=None, componentes: dict | None = None) -> dict:
	"""`vPrest`: `vTPrest`, `vRec` e os `Comp` opcionais (nome → valor).

	`vRec` cai em `vTPrest` quando não informado — o caso comum, sem adiantamento. Total
	zero ou negativo é recusado: uma prestação sem valor não é fato a declarar.
	"""
	total = Decimal(str(valor_total or 0))

	if total <= 0:
		raise CteInvalido(f"valor total da prestação precisa ser positivo, recebido {total}", "vTPrest")

	receber = total if valor_receber is None else Decimal(str(valor_receber))

	if receber < 0 or receber > total:
		raise CteInvalido(f"valor a receber ({receber}) precisa estar entre 0 e o total ({total})", "vRec")

	grupo: dict = {"vTPrest": _valor(total), "vRec": _valor(receber)}

	if componentes:
		grupo["Comp"] = [
			{"xNome": _obrigatorio(nome, "nome do componente"), "vComp": _valor(v)}
			for nome, v in componentes.items()
		]

	return grupo


def montar_icms00(base, aliquota) -> dict:
	"""`ICMS00` — tributação normal: `CST 00`, `vBC`, `pICMS`, `vICMS` (linhas 6677+).

	`vICMS` é **calculado** de `vBC × pICMS`, nunca recebido em paralelo: dois valores para o
	mesmo fato é onde a divergência nasce. `aliquota` é fração (`0.12`), como em todo o app.
	"""
	base_calculo = Decimal(str(base or 0))
	fracao = Decimal(str(aliquota or 0))

	if base_calculo < 0:
		raise CteInvalido(f"base de cálculo do ICMS não pode ser negativa: {base_calculo}", "vBC")

	if not 0 <= fracao < 1:
		raise CteInvalido(f"alíquota do ICMS é fração entre 0 e 1, recebido {fracao}", "pICMS")

	return {
		"ICMS00": {
			"CST": CST_ICMS_NORMAL,
			"vBC": _valor(base_calculo),
			"pICMS": _percentual(fracao),
			"vICMS": _valor(arredondar(base_calculo * fracao)),
		}
	}


def montar_icmssn() -> dict:
	"""`ICMSSN` — emitente do Simples Nacional: `CST 90` e `indSN 1`, sem valores (linha 7027)."""
	return {"ICMSSN": {"CST": CST_ICMS_SIMPLES, "indSN": "1"}}


def montar_imp(icms: dict, icms_uf_fim: dict | None = None) -> dict:
	"""`imp`: `ICMS` (uma das situações de `TImp`) e, opcionalmente, `ICMSUFFim`."""
	if len(icms) != 1 or next(iter(icms)) not in {"ICMS00", "ICMSSN"}:
		raise CteInvalido(
			"imp/ICMS aceita, neste incremento, ICMS00 ou ICMSSN — as demais situações de TImp "
			"(ICMS20/45/60/90/OutraUF) não são montadas por suposição",
			"ICMS",
		)

	grupo: dict = {"ICMS": dict(icms)}

	if icms_uf_fim:
		grupo["ICMSUFFim"] = dict(icms_uf_fim)

	return grupo


# ---------------------------------------------------------------------------
# infCarga, infModal, infCTeNorm
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QuantidadeCarga:
	"""Um `infQ`: unidade (código `cUnid`), tipo de medida (texto livre) e quantidade."""

	unidade: str
	tipo_medida: str
	quantidade: Decimal


def montar_infcarga(produto_predominante: str, quantidades: list[QuantidadeCarga], valor=None) -> dict:
	"""`infCarga`: `vCarga` (opcional), `proPred`, `infQ` (ao menos um) — ordem do XSD."""
	grupo: dict = {}

	if valor is not None:
		grupo["vCarga"] = _valor(valor)

	grupo["proPred"] = _obrigatorio(produto_predominante, "produto predominante da carga (proPred)")

	if not quantidades:
		raise CteInvalido("infCarga exige ao menos uma quantidade (infQ)", "infQ")

	grupo["infQ"] = []

	for q in quantidades:
		if q.unidade not in UNIDADES_DE_CARGA:
			raise CteInvalido(
				f"cUnid deve ser um de {sorted(UNIDADES_DE_CARGA)}, recebido {q.unidade!r}", "cUnid"
			)

		if Decimal(str(q.quantidade)) <= 0:
			raise CteInvalido(f"qCarga precisa ser positiva, recebido {q.quantidade}", "qCarga")

		grupo["infQ"].append(
			{
				"cUnid": q.unidade,
				"tpMed": _obrigatorio(q.tipo_medida, "tipo de medida (tpMed)"),
				# TDec_1104: quatro casas.
				"qCarga": str(Decimal(str(q.quantidade)).quantize(Decimal("0.0001"))),
			}
		)

	return grupo


def montar_infmodal(modal: str, conteudo: dict, versao: str = VERSAO_MODAL) -> dict:
	"""`infModal`: o atributo `versaoModal` e o XML do modal, embrulhado na tag do modal.

	Só o rodoviário está implementado (`fiscal/cte_rodoviario.montar_rodo` devolve o
	**conteúdo** de `rodo`; a tag é posta aqui). Os demais códigos levantam em vez de
	embrulhar um conteúdo que nenhum módulo deste app sabe montar.
	"""
	if modal != MODAL_RODOVIARIO:
		raise CteInvalido(
			f"modal {modal!r} ainda não tem montador — só o rodoviário ({MODAL_RODOVIARIO})", "modal"
		)

	if not conteudo:
		raise CteInvalido("infModal exige o conteúdo do modal (ex.: o grupo rodo)", "infModal")

	return {"@versaoModal": versao, "rodo": dict(conteudo)}


def montar_infcte_norm(infcarga: dict, infmodal: dict, infdoc: dict | None = None) -> dict:
	"""`infCTeNorm`: `infCarga`, `infDoc` (opcional), `infModal` — ordem do XSD (linha 4013+)."""
	grupo: dict = {"infCarga": dict(infcarga)}

	if infdoc:
		grupo["infDoc"] = dict(infdoc)

	grupo["infModal"] = dict(infmodal)

	return grupo


# ---------------------------------------------------------------------------
# infCte — o orquestrador
# ---------------------------------------------------------------------------


def montar_infcte(
	identificacao: IdentificacaoCte,
	tomador: dict,
	emitente: EmitenteCte,
	vprest: dict,
	imp: dict,
	infcte_norm: dict,
	remetente: ParteCte | None = None,
	destinatario: ParteCte | None = None,
) -> tuple[dict, str]:
	"""`infCte` completo, com `@Id`, e a chave de acesso derivada dele.

	A chave sai de `ide` + CNPJ/CPF do emitente (`montar_chave`, modelo 57), e o `cDV` do
	`ide` sai da mesma chave — uma fonte só. Devolve `(infcte, chave)` porque quem chama
	precisa da chave para `montar_cte`/registro, e extraí-la de volta do `@Id` seria
	repetir o trabalho ao contrário.

	Ordem dos filhos, lida no XSD (`TCTe`, linha 2689+): `ide`, `emit`, `rem`, `dest`,
	`vPrest`, `imp`, `infCTeNorm`. `compl`, `exped`, `receb`, `autXML`, `infRespTec` ficam
	fora deste incremento.
	"""
	identificacao.validar()
	cnpj_cpf = validar_cpf_cnpj(emitente.cnpj_cpf)
	chave = montar_chave(
		uf=identificacao.uf,
		ano_mes=identificacao.emissao.strftime("%y%m"),
		cnpj=cnpj_cpf,
		modelo=MODELO_CTE,
		serie=identificacao.serie,
		numero=identificacao.numero,
		tipo_emissao=identificacao.tipo_emissao,
		codigo_numerico=identificacao.codigo_numerico,
	)

	infcte: dict = {
		"@Id": f"CTe{chave}",
		"ide": montar_ide(identificacao, tomador, chave),
		"emit": montar_emit(emitente),
	}

	if remetente is not None:
		infcte["rem"] = montar_rem(remetente)

	if destinatario is not None:
		infcte["dest"] = montar_dest(destinatario)

	infcte["vPrest"] = dict(vprest)
	infcte["imp"] = dict(imp)
	infcte["infCTeNorm"] = dict(infcte_norm)

	return infcte, chave
