# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""EFD-Reinf R-4020 (evt4020PagtoBeneficiarioPJ): Pagamentos/créditos a
beneficiário pessoa jurídica, com retenções de IRRF/CSLL/Cofins/PIS-Pasep.

Primeira fatia do EFD-Reinf modelada neste projeto
------------------------------------------------------------
Item citado como fora de escopo desde as primeiras sessões. EFD-Reinf é um sistema
irmão do eSocial (mesma infraestrutura conceitual — leiaute XML, `ideEvento` no
mesmo espírito, ambiente de produção restrita) mas juridicamente separado; os
eventos série R-4000 substituem a DIRF e escrituram as quatro retenções federais
que incidem juntas sobre pagamentos a PJ (IRRF + CSLL + Cofins + PIS-Pasep, o
"combo" de retenção da IN RFB 1.234/2012) — cobrindo o lado do **pagador**
(retentor), diferente do S-1200/eSocial (lado do empregador sobre o próprio
trabalhador).

Valores monetários são STRING com vírgula no XSD, não decimal puro
------------------------------------------------------------------------------
Achado real, não suposto: o XSD declara `vlrBruto`/`vlrBaseIR`/`vlrIR`/etc. como
`xs:string` com padrão `[0-9]{1,12},[0-9]{2}` (vírgula decimal, não ponto) — não
`xs:decimal`. Este módulo usa `Decimal` internamente (convenção deste projeto,
`docs/README.md`: "dinheiro é Decimal") — a conversão para o formato string com
vírgula que o XSD exige fica para quando a serialização XML deste evento for
implementada (ainda não está, mesmo estágio em que `esocial_s1200.py` começou antes
de ganhar `esocial_serializacao.py`).

`ideEvento` é parecido com o do eSocial, mas não é o mesmo tipo
------------------------------------------------------------------------------
Mesmos nomes de campo (`indRetif`, `nrRecibo`, `perApur`, `tpAmb`, `procEmi`,
`verProc`) e mesma ausência de `indApuracao` do S-2200/S-2299 — mas `procEmi` aqui
é `unsignedByte (1|2)`, um domínio de **dois** valores, diferente de qualquer
`procEmi` já visto no bloco eSocial (livre 0-9, ou livre-exceto-8). Mais uma
variação confirmada na fonte, não suposta por semelhança.

O que fica de fora, deliberadamente
------------------------------------------
- **`natRend`** (natureza do rendimento, 5 dígitos) — tabela nacional mantida pela
  RFB, não trazida para este projeto (mesma disciplina de `COD_CONT` no
  EFD-Contribuições, `codCateg` no eSocial); aceito só por formato.
- **`infoProcRet`/`infoProcJud`/`infoPgtoExt`** (processos que suspendem retenção,
  pagamento a residente no exterior) — grupos raros, mesma decisão de excluir
  `procJudTrab` já tomada no bloco eSocial.
- **`indFciScp`/`nrInscFciScp`/`percSCP`** (Sociedade em Conta de Participação) —
  regime societário raro, não modelado.
- **Serialização XML/assinatura/envio** — mesmo padrão do bloco eSocial: modelado
  só o agregado de negócio nesta fatia.

Fonte: mesma família de projeto open-source já usada para eSocial e NF-e
------------------------------------------------------------------------------------------
`github.com/nfephp-org/sped-efdreinf`,
`schemes/v2_01_02/R-4020-evt4020PagtoBeneficiarioPJ-v2_01_02_B.xsd` — não a fonte
primária oficial (`sped.rfb.gov.br`).

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

__all__ = [
	"AMBIENTE_PRODUCAO",
	"AMBIENTE_PRODUCAO_RESTRITA",
	"IdeContri",
	"IdeEstab",
	"IdeEvento",
	"InfoPgto",
	"ReinfInvalido",
	"Retencoes",
]

AMBIENTE_PRODUCAO = 1
AMBIENTE_PRODUCAO_RESTRITA = 2


class ReinfInvalido(ValueError):
	"""Dado que impede a montagem do evento — campo fora do padrão do XSD."""


def _validar_cnpj_ou_cpf(valor: str, campo: str) -> None:
	if not valor.isdigit() or len(valor) not in (8, 11, 14):
		raise ReinfInvalido(f"{campo} deve ter 8, 11 ou 14 dígitos numéricos, recebido {valor!r}")


@dataclass(frozen=True)
class IdeEvento:
	"""`ideEvento` do R-4020 — mesmos nomes de campo do bloco eSocial, mas
	`proc_emi` aqui é um domínio de **dois** valores (`unsignedByte 1|2`), não os
	domínios já vistos em `esocial_s1200`/`esocial_s2200`/`esocial_s2299`."""

	ind_retif: int
	per_apur: str
	tp_amb: int
	proc_emi: int
	ver_proc: str
	nr_recibo: str | None = None

	def __post_init__(self):
		if self.ind_retif not in (1, 2):
			raise ReinfInvalido(
				f"indRetif deve ser 1 (original) ou 2 (retificação), recebido {self.ind_retif}"
			)

		if self.ind_retif == 2 and not self.nr_recibo:
			raise ReinfInvalido("nrRecibo é obrigatório quando indRetif=2 (retificação)")

		if len(self.per_apur) != 7:
			raise ReinfInvalido(f"perApur deve ter 7 caracteres (formato AAAA-MM), recebido {self.per_apur!r}")

		if self.tp_amb not in (AMBIENTE_PRODUCAO, AMBIENTE_PRODUCAO_RESTRITA):
			raise ReinfInvalido(f"tpAmb deve ser 1 (Produção) ou 2 (Produção Restrita), recebido {self.tp_amb}")

		if self.proc_emi not in (1, 2):
			raise ReinfInvalido(f"procEmi deve ser 1 ou 2 neste evento, recebido {self.proc_emi}")

		if not (1 <= len(self.ver_proc) <= 20):
			raise ReinfInvalido(f"verProc deve ter entre 1 e 20 caracteres, recebido {self.ver_proc!r}")


@dataclass(frozen=True)
class IdeContri:
	"""`ideContri` — identifica o contribuinte declarante (o retentor/pagador)."""

	tp_insc: int
	nr_insc: str

	def __post_init__(self):
		if self.tp_insc not in (1, 2):
			raise ReinfInvalido(f"tpInsc deve ser 1 (CNPJ) ou 2 (CPF), recebido {self.tp_insc}")

		_validar_cnpj_ou_cpf(self.nr_insc, "nrInsc")


@dataclass(frozen=True)
class IdeEstab:
	"""`ideEstab` — `tp_insc_estab` tem três valores possíveis (`1|2|3`),
	provavelmente CNPJ/CPF/CNO — significado do terceiro valor não confirmado nesta
	rodada, aceito só por formato."""

	tp_insc_estab: int
	nr_insc_estab: str

	def __post_init__(self):
		if self.tp_insc_estab not in (1, 2, 3):
			raise ReinfInvalido(f"tpInscEstab deve ser 1, 2 ou 3, recebido {self.tp_insc_estab}")

		if not self.nr_insc_estab.isdigit() or len(self.nr_insc_estab) not in (11, 14):
			raise ReinfInvalido(
				f"nrInscEstab deve ter 11 ou 14 dígitos numéricos, recebido {self.nr_insc_estab!r}"
			)


@dataclass(frozen=True)
class Retencoes:
	"""`retencoes` — as quatro retenções federais que incidem juntas sobre o
	pagamento a PJ (IRRF, CSLL, Cofins, PIS-Pasep). Todos os campos são opcionais no
	XSD (nem todo pagamento sofre todas as quatro) — nenhum default assumido além de
	`None`, quem chama informa só as que se aplicam."""

	vlr_base_ir: Decimal | None = None
	vlr_ir: Decimal | None = None
	vlr_base_csll: Decimal | None = None
	vlr_csll: Decimal | None = None
	vlr_base_cofins: Decimal | None = None
	vlr_cofins: Decimal | None = None
	vlr_base_pp: Decimal | None = None
	vlr_pp: Decimal | None = None

	def __post_init__(self):
		for nome, valor in (
			("vlrBaseIR", self.vlr_base_ir),
			("vlrIR", self.vlr_ir),
			("vlrBaseCSLL", self.vlr_base_csll),
			("vlrCSLL", self.vlr_csll),
			("vlrBaseCofins", self.vlr_base_cofins),
			("vlrCofins", self.vlr_cofins),
			("vlrBasePP", self.vlr_base_pp),
			("vlrPP", self.vlr_pp),
		):
			if valor is not None and valor < Decimal("0"):
				raise ReinfInvalido(f"{nome} não pode ser negativo, recebido {valor}")


@dataclass(frozen=True)
class InfoPgto:
	"""`infoPgto` — um pagamento/crédito específico, com a data do fato gerador
	(pagamento ou crédito, o que ocorrer primeiro) e o valor bruto."""

	dt_fg: date
	vlr_bruto: Decimal
	retencoes: Retencoes | None = None

	def __post_init__(self):
		if self.vlr_bruto < Decimal("0"):
			raise ReinfInvalido(f"vlrBruto não pode ser negativo, recebido {self.vlr_bruto}")
