# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""eSocial S-1200 (evtRemun): Remuneração de trabalhador vinculado ao RGPS.

Primeira fatia do eSocial modelada neste projeto — escolhida por ser o evento
periódico mais próximo do que `folha/` já calcula (`docs/rh-estado-esocial.md`
registrou por que o eSocial inteiro é grande demais para "só continuar" sem recortar
uma fatia primeiro).

O que esta fatia cobre, e o que não cobre
------------------------------------------------
Este módulo modela os grupos verificados contra o XSD literal do evento —
`ideEvento`, `ideEmpregador`, `ideTrabalhador` (com `infoComplem`), `TItemRemuneracao`,
`RemunPerApur`, `IdeEstabLot`, `InfoPerApur` e `DmDev` — a árvore inteira que aninha
uma linha de rubrica dentro do período/estabelecimento/lotação/categoria do
trabalhador. **Não modela**: `infoMV` (múltiplos vínculos empregatícios) e
`procJudTrab` (processos judiciais que afetam a tributação) dentro de
`ideTrabalhador` — grupos raros, deliberadamente fora de escopo, ver docstring de
`IdeTrabalhador`; `infoPerAnt`/`ideADC` dentro de `DmDev` (remuneração de período
anterior por acordo/convenção coletiva retroativos) — outro grupo raro, mesma
decisão; e a serialização para XML/assinatura/envio, que é a "camada de transporte",
uma fatia à parte (ver `docs/rh-estado-esocial.md`). O objetivo aqui é ter a árvore de
negócio pronta e testada antes de montar o envelope XML, mesmo espírito de
`fiscal/documento/nfe.py` ter modelado `Identificacao`/`montar_ide` antes de qualquer
assinatura ou envio.

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
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

__all__ = [
	"AMBIENTE_PRODUCAO",
	"AMBIENTE_PRODUCAO_RESTRITA",
	"DmDev",
	"EsocialInvalido",
	"IdeEmpregador",
	"IdeEstabLot",
	"IdeEvento",
	"IdeTrabalhador",
	"InfoComplem",
	"InfoPerApur",
	"ItemRemuneracao",
	"RemunPerApur",
	"linhas_de_inss_irrf",
]

AMBIENTE_PRODUCAO = 1
AMBIENTE_PRODUCAO_RESTRITA = 2

_TOLERANCIA_ARREDONDAMENTO = Decimal("0.01")


class EsocialInvalido(ValueError):
	"""Dado que impede a montagem do evento — campo fora do padrão do XSD."""


def _arredondar(valor: Decimal) -> Decimal:
	return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _validar_digito_unico(valor: int, campo: str) -> None:
	if not (0 <= valor <= 9):
		raise EsocialInvalido(f"{campo} deve ser um dígito único (0-9), recebido {valor}")


def _validar_nr_insc(valor: str, campo: str = "nrInsc") -> None:
	"""`nrInsc` (`TEmpregador`/`IdeEstabLot`) — mesmo formato XSD nos dois grupos:
	8 a 15 dígitos numéricos. Só o formato; o dígito verificador de CNPJ/CPF é
	responsabilidade de `fiscal/validators`, chamado por quem monta o evento."""
	if not valor.isdigit() or not (8 <= len(valor) <= 15):
		raise EsocialInvalido(f"{campo} deve ter entre 8 e 15 dígitos numéricos, recebido {valor!r}")


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

		_validar_digito_unico(self.proc_emi, "procEmi")

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
		_validar_digito_unico(self.tp_insc, "tpInsc")
		_validar_nr_insc(self.nr_insc)


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


@dataclass(frozen=True)
class InfoComplem:
	"""Grupo `infoComplem` de `ideTrabalhador` — dados cadastrais complementares do
	trabalhador exigidos apenas em admissões/situações específicas; quando presente,
	os quatro campos abaixo (fora os dois opcionais) são obrigatórios pelo XSD."""

	nm_trab: str
	dt_nascto: date
	cod_cbo: str
	nat_atividade: int | None = None
	qtd_dias_trab: int | None = None

	def __post_init__(self):
		if not (2 <= len(self.nm_trab) <= 70):
			raise EsocialInvalido(f"nmTrab deve ter entre 2 e 70 caracteres, recebido {self.nm_trab!r}")

		if not self.cod_cbo.isdigit() or not (4 <= len(self.cod_cbo) <= 6):
			raise EsocialInvalido(f"codCBO deve ter entre 4 e 6 dígitos numéricos, recebido {self.cod_cbo!r}")

		if self.nat_atividade is not None:
			_validar_digito_unico(self.nat_atividade, "natAtividade")

		if self.qtd_dias_trab is not None and not (0 <= self.qtd_dias_trab <= 99):
			raise EsocialInvalido(f"qtdDiasTrab deve ter 1 ou 2 dígitos, recebido {self.qtd_dias_trab}")


@dataclass(frozen=True)
class IdeTrabalhador:
	"""Grupo `ideTrabalhador` — cobre `cpfTrab`/`nisTrab`/`infoComplem`.

	**Fora de escopo, deliberadamente**: `infoMV` (o trabalhador tem outros vínculos
	simultâneos que afetam o teto do INSS) e `procJudTrab` (uma decisão judicial muda
	a tributação de alguma verba) — ambos raros e cada um exigiria sua própria tabela
	de domínio; incluí-los sem uma fonte tão bem verificada quanto o resto deste
	módulo arriscaria uma modelagem errada silenciosa, pior que não ter nenhuma."""

	cpf_trab: str
	nis_trab: str | None = None
	info_complem: InfoComplem | None = None

	def __post_init__(self):
		if not self.cpf_trab.isdigit() or len(self.cpf_trab) != 11:
			raise EsocialInvalido(f"cpfTrab deve ter exatamente 11 dígitos numéricos, recebido {self.cpf_trab!r}")

		if self.nis_trab is not None and (not self.nis_trab.isdigit() or len(self.nis_trab) != 11):
			raise EsocialInvalido(f"nisTrab deve ter exatamente 11 dígitos numéricos, recebido {self.nis_trab!r}")


@dataclass(frozen=True)
class RemunPerApur:
	"""Grupo `remunPerApur` — as linhas de rubrica (`itensRemun`) de um período,
	dentro de um estabelecimento/lotação (`IdeEstabLot`). Limite do XSD: 1 a 200
	itens; `infoSaudeColet`/`infoAgNocivo` não modelados (grupos condicionais a
	situações específicas — plano de saúde coletivo, agente nocivo — fora de escopo
	pela mesma razão de `infoMV`/`procJudTrab`)."""

	itens_remun: tuple[ItemRemuneracao, ...]
	matricula: str | None = None
	ind_simples: int | None = None

	def __post_init__(self):
		if not self.itens_remun:
			raise EsocialInvalido("remunPerApur precisa de ao menos uma linha em itensRemun")

		if len(self.itens_remun) > 200:
			raise EsocialInvalido(f"itensRemun aceita no máximo 200 linhas, recebido {len(self.itens_remun)}")

		if self.matricula is not None and not (1 <= len(self.matricula) <= 30):
			raise EsocialInvalido(f"matricula deve ter entre 1 e 30 caracteres, recebido {self.matricula!r}")

		if self.ind_simples is not None:
			_validar_digito_unico(self.ind_simples, "indSimples")


@dataclass(frozen=True)
class IdeEstabLot:
	"""Grupo `ideEstabLot` — identifica o estabelecimento/lotação tributária a que
	pertence cada `RemunPerApur`. Limite do XSD: até 24 lotações por período, até 8
	`RemunPerApur` por lotação (competências concorrentes, ex. mês normal + rescisão
	no mesmo período)."""

	tp_insc: int
	nr_insc: str
	cod_lotacao: str
	remun_per_apur: tuple[RemunPerApur, ...]
	qtd_dias_av: int | None = None

	def __post_init__(self):
		_validar_digito_unico(self.tp_insc, "tpInsc")
		_validar_nr_insc(self.nr_insc)

		if not (1 <= len(self.cod_lotacao) <= 30):
			raise EsocialInvalido(f"codLotacao deve ter entre 1 e 30 caracteres, recebido {self.cod_lotacao!r}")

		if not self.remun_per_apur:
			raise EsocialInvalido("ideEstabLot precisa de ao menos um remunPerApur")

		if len(self.remun_per_apur) > 8:
			raise EsocialInvalido(
				f"remunPerApur aceita no máximo 8 ocorrências, recebido {len(self.remun_per_apur)}"
			)

		if self.qtd_dias_av is not None and not (0 <= self.qtd_dias_av <= 99):
			raise EsocialInvalido(f"qtdDiasAv deve ter 1 ou 2 dígitos, recebido {self.qtd_dias_av}")


@dataclass(frozen=True)
class InfoPerApur:
	"""Grupo `infoPerApur` — a lista de estabelecimentos/lotações do período. Limite
	do XSD: até 24 `ideEstabLot`."""

	ide_estab_lot: tuple[IdeEstabLot, ...]

	def __post_init__(self):
		if not self.ide_estab_lot:
			raise EsocialInvalido("infoPerApur precisa de ao menos um ideEstabLot")

		if len(self.ide_estab_lot) > 24:
			raise EsocialInvalido(f"ideEstabLot aceita no máximo 24 ocorrências, recebido {len(self.ide_estab_lot)}")


@dataclass(frozen=True)
class DmDev:
	"""Grupo `dmDev` — o "demonstrativo de valores devidos" de uma categoria de
	trabalhador no período. `cod_categ` é a categoria do eSocial (tabela de domínio
	própria — ex. 101 empregado geral; enumeração completa não modelada nesta rodada,
	só o formato de 3 dígitos é validado).

	**Fora de escopo, deliberadamente**: `infoPerAnt`/`ideADC` — remuneração de
	período anterior por acordo/convenção coletiva com efeito retroativo, um grupo
	raro com sua própria árvore aninhada (`idePeriodo`, análoga a `infoPerApur`); a
	mesma decisão de não modelar sem fonte tão verificada quanto o resto."""

	ide_dm_dev: str
	cod_categ: int
	info_per_apur: InfoPerApur | None = None

	def __post_init__(self):
		if not (1 <= len(self.ide_dm_dev) <= 30):
			raise EsocialInvalido(f"ideDmDev deve ter entre 1 e 30 caracteres, recebido {self.ide_dm_dev!r}")

		if not (100 <= self.cod_categ <= 999):
			raise EsocialInvalido(f"codCateg deve ter exatamente 3 dígitos, recebido {self.cod_categ}")


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
