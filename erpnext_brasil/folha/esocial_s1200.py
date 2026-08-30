# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""eSocial S-1200 (evtRemun): Remuneração de trabalhador vinculado ao RGPS.

Primeira fatia do eSocial modelada neste projeto — escolhida por ser o evento
periódico mais próximo do que `folha/` já calcula (`docs/rh-estado-esocial.md`
registrou por que o eSocial inteiro é grande demais para "só continuar" sem recortar
uma fatia primeiro).

O que esta fatia cobre, e o que não cobre
------------------------------------------------
Este módulo modela só os grupos verificados contra o XSD literal do evento —
`ideEvento`, `ideEmpregador` e `TItemRemuneracao` (a linha de rubrica dentro de
`detVerbas`/`itensRemun`) — e a ponte que transforma o INSS/IRRF já calculados por
`folha/inss.py`/`folha/irrf.py` nessas linhas. **Não modela** a árvore inteira do
evento (`ideTrabalhador`, `dmDev`, `infoPerApur`, `ideEstabLot`, `remunPerApur`) nem a
serialização para XML/assinatura/envio — isso é a "camada de transporte", a fatia que
ficou para depois (ver `docs/rh-estado-esocial.md`). O objetivo aqui é ter as peças
verificadas e testadas antes de montar a árvore completa, mesmo espírito de
`fiscal/documento/nfe.py` ter começado por `montar_ide` antes de `montar_dest`.

Fonte do XSD: não o oficial `gov.br/esocial` diretamente
------------------------------------------------------------------
A página oficial de leiautes (`gov.br/esocial/.../leiautes-esocial-v-1.3`) é HTML
acessível — ao contrário da maioria das fontes `gov.br` deste projeto — mas grande
demais para as ferramentas de busca extraírem o XSD literal sem perda (o resumo
devolvido generaliza tipos e omite `pattern`/`totalDigits`). O XSD usado para os
tipos e tamanhos abaixo veio de `github.com/tiagoravache/eSocial`
(`Exemplos/ACBrDFe/ACBreSocial2.0/Schemas/evtRemun.xsd`) — um projeto open-source de
integração fiscal brasileira (mesma família do `nfephp-org` já usado para os XSDs da
NF-e neste projeto), não a fonte primária. Tratado com a mesma cautela: os tamanhos e
padrões batem com o que a busca agregada por `codIncCP`/`codIncIRRF`/`codIncFGTS`
confirmou de forma independente, mas não houve leitura direta do XSD publicado pelo
próprio `gov.br/esocial`.

`tpAmb`: mesmos códigos da NF-e, rótulo diferente
--------------------------------------------------------
`1` = Produção, `2` = **Produção Restrita** (não "Homologação", o rótulo usado pela
NF-e para o mesmo código `2`) — mesma numeração, nome diferente. Confirmado via
`gov.br/esocial` (Perguntas Frequentes): "2-Produção restrita é válido apenas para
teste... 1-Produção deve ser usado quando o envio for efetivamente oficial".

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

__all__ = [
	"AMBIENTE_PRODUCAO",
	"AMBIENTE_PRODUCAO_RESTRITA",
	"EsocialInvalido",
	"IdeEmpregador",
	"IdeEvento",
	"ItemRemuneracao",
	"linhas_de_inss_irrf",
]

AMBIENTE_PRODUCAO = 1
AMBIENTE_PRODUCAO_RESTRITA = 2

_TOLERANCIA_ARREDONDAMENTO = Decimal("0.01")


class EsocialInvalido(ValueError):
	"""Dado que impede a montagem do evento — campo fora do padrão do XSD."""


def _arredondar(valor: Decimal) -> Decimal:
	return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class IdeEvento:
	"""Grupo `ideEvento` do S-1200.

	`nr_recibo` é obrigatório quando `ind_retif == 2` (retificação) — o próprio XSD
	marca o campo como opcional (`minOccurs=0`), mas a regra de negócio (confirmada
	via busca agregada às Perguntas Frequentes do eSocial) o torna obrigatório nesse
	caso; verificado aqui como invariante, não deixado para a SEFAZ rejeitar depois.
	"""

	ind_retif: int
	per_apur: str
	tp_amb: int
	proc_emi: int
	ver_proc: str
	nr_recibo: str | None = None

	def __post_init__(self):
		if self.ind_retif not in (1, 2):
			raise EsocialInvalido(f"indRetif deve ser 1 (original) ou 2 (retificação), recebido {self.ind_retif}")

		if self.ind_retif == 2 and not self.nr_recibo:
			raise EsocialInvalido("nrRecibo é obrigatório quando indRetif=2 (retificação)")

		if not (4 <= len(self.per_apur) <= 7):
			raise EsocialInvalido(
				f"perApur deve ter entre 4 e 7 caracteres (formato AAAA-MM), recebido {self.per_apur!r}"
			)

		if self.tp_amb not in (AMBIENTE_PRODUCAO, AMBIENTE_PRODUCAO_RESTRITA):
			raise EsocialInvalido(f"tpAmb deve ser 1 (Produção) ou 2 (Produção Restrita), recebido {self.tp_amb}")

		if not (0 <= self.proc_emi <= 9):
			raise EsocialInvalido(f"procEmi deve ser um dígito único (0-9), recebido {self.proc_emi}")

		if not (1 <= len(self.ver_proc) <= 20):
			raise EsocialInvalido(f"verProc deve ter entre 1 e 20 caracteres, recebido {self.ver_proc!r}")

		if self.nr_recibo is not None and not (1 <= len(self.nr_recibo) <= 40):
			raise EsocialInvalido(f"nrRecibo deve ter entre 1 e 40 caracteres, recebido {self.nr_recibo!r}")


@dataclass(frozen=True)
class IdeEmpregador:
	"""Grupo `ideEmpregador` (`TEmpregador`) — `tp_insc` 1=CNPJ, `tp_insc` 4=CPF (para
	o empregador doméstico), mesma convenção usada em outros eventos do eSocial —
	**enumeração não confirmada por leitura direta do XSD oficial nesta rodada**, só
	pelo padrão amplamente documentado em fontes de mercado; `nr_insc` em si é
	validado apenas pelo formato XSD (8 a 15 dígitos), não pelo dígito verificador de
	CNPJ/CPF — essa validação já existe em `fiscal/validators` e é responsabilidade
	de quem monta o evento, não deste módulo (mesma separação de `nfe.py` não validar
	de novo o que `party.py` já valida na gravação do cadastro)."""

	tp_insc: int
	nr_insc: str

	def __post_init__(self):
		if not (0 <= self.tp_insc <= 9):
			raise EsocialInvalido(f"tpInsc deve ser um dígito único (0-9), recebido {self.tp_insc}")

		limpo = self.nr_insc

		if not limpo.isdigit() or not (8 <= len(limpo) <= 15):
			raise EsocialInvalido(f"nrInsc deve ter entre 8 e 15 dígitos numéricos, recebido {self.nr_insc!r}")


@dataclass(frozen=True)
class ItemRemuneracao:
	"""Uma linha de `detVerbas`/`itensRemun` (`TItemRemuneracao`) — o valor de uma
	rubrica no período.

	`cod_rubr`/`ide_tab_rubr` vêm da tabela de rubricas do próprio empregador (evento
	S-1010, cadastro prévio) — este módulo nunca infere um código de rubrica, mesma
	disciplina de `boleto.montar_codigo_barras` não inferir o `campo_livre`: dado que
	depende de uma tabela externa ao alcance de quem chama, não deste módulo.

	Duas formas válidas de uma linha, mutuamente exclusivas na prática (o XSD marca
	`qtd_rubr`/`fator_rubr`/`vr_unit` como opcionais, `vr_rubr` como obrigatório):
	quantidade × fator × valor unitário (uma verba calculada, ex. horas extras), ou só
	o valor final já pronto (ex. um desconto informado diretamente, como INSS/IRRF) —
	`__post_init__` confere a consistência apenas quando os três primeiros estão
	presentes; quando ausentes, `vr_rubr` é aceito como está.
	"""

	cod_rubr: str
	vr_rubr: Decimal
	ide_tab_rubr: str | None = None
	qtd_rubr: Decimal | None = None
	fator_rubr: Decimal | None = None
	vr_unit: Decimal | None = None

	def __post_init__(self):
		if not (1 <= len(self.cod_rubr) <= 30):
			raise EsocialInvalido(f"codRubr deve ter entre 1 e 30 caracteres, recebido {self.cod_rubr!r}")

		if self.ide_tab_rubr is not None and not (1 <= len(self.ide_tab_rubr) <= 8):
			raise EsocialInvalido(f"ideTabRubr deve ter entre 1 e 8 caracteres, recebido {self.ide_tab_rubr!r}")

		if self.qtd_rubr is not None and self.fator_rubr is not None and self.vr_unit is not None:
			calculado = _arredondar(self.qtd_rubr * self.fator_rubr * self.vr_unit)

			if abs(calculado - self.vr_rubr) > _TOLERANCIA_ARREDONDAMENTO:
				raise EsocialInvalido(
					f"vrRubr ({self.vr_rubr}) não bate com qtdRubr*fatorRubr*vrUnit "
					f"({calculado}) além da tolerância de arredondamento"
				)


def linhas_de_inss_irrf(
	inss: Decimal, irrf: Decimal, *, cod_rubrica_inss: str, cod_rubrica_irrf: str
) -> tuple[ItemRemuneracao, ...]:
	"""Ponte entre os valores já calculados por `folha/inss.py`/`folha/irrf.py` e as
	linhas de `detVerbas` do S-1200.

	`cod_rubrica_inss`/`cod_rubrica_irrf` vêm de quem chama — a tabela de rubricas
	(evento S-1010) é configuração do empregador, este módulo não a modela (ver
	docstring de `ItemRemuneracao`). Uma rubrica com valor zero ainda gera linha: o
	eSocial espera o INSS/IRRF do período mesmo quando o valor apurado for zero,
	tornar a linha condicional ao valor esconderia o cálculo em vez de mostrar
	"apurado como zero" (mesmo espírito de "toda ação precisa de confirmação visual
	do que mudou" — aqui, "todo período tem um valor apurado", zero incluso).
	"""
	return (
		ItemRemuneracao(cod_rubr=cod_rubrica_inss, vr_rubr=inss),
		ItemRemuneracao(cod_rubr=cod_rubrica_irrf, vr_rubr=irrf),
	)
