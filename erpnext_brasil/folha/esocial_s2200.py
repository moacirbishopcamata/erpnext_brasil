# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""eSocial S-2200 (evtAdmissao): Admissão de Trabalhador.

Segunda fatia não periódica do eSocial modelada neste projeto (depois de S-1010) —
pré-requisito lógico de qualquer S-1200: não existe folha de um trabalhador que
nunca foi admitido.

Confiança desigual por campo, registrada explicitamente
------------------------------------------------------------
Diferente do S-1010 (quatro tabelas de incidência inteiramente enumeradas no XSD),
o S-2200 tem muito mais domínios que são tabelas nacionais grandes referenciadas de
fora (sexo, raça/cor, grau de instrução, regime trabalhista, natureza de atividade,
categoria do trabalhador, tipo de salário) — não confirmadas nesta rodada, só o
formato (inteiro, faixa de dígito) é validado para elas. Dois campos, em contraste,
têm enumeração **literal e citada com a tag XSD** confirmada nesta rodada:
`tpAdmissao` (1 a 7, com a descrição de cada valor) e `indAdmissao` (1 a 3) — esses
dois são validados contra a enumeração real, os demais não. `tpRegPrev` foi citado
como enumerado `[1,2,3,4]` por uma fonte que não reproduziu a tag XSD literal (ao
contrário de `tpAdmissao`/`indAdmissao`) — tratado aqui com confiança intermediária:
validado contra a faixa, mas sem a mesma certeza dos outros dois.

`ideEvento` deste evento não é o do S-1200 (confirmado, não suposto)
------------------------------------------------------------------------------
Lido diretamente em `tipos.xsd` (`T_ideEvento_trab_admissao`): `indRetif`,
`nrRecibo`, `tpAmb`, `procEmi`, `verProc` — **sem** `perApur`/`indApuracao` (fazem
sentido só em evento periódico, S-2200 não é um). Por isso este módulo define seu
próprio `IdeEvento`, não reaproveita `esocial_s1200.IdeEvento`. Uma diferença extra
notada: `procEmi` aqui é `TS_procEmi_sem_8` — o próprio nome do tipo indica que o
valor `8` é excluído do domínio válido *neste evento específico*, diferente do
`procEmi` genérico (dígito 0-9 livre) usado no S-1200.

O que fica de fora, deliberadamente
------------------------------------------
- **`infoEstatutario`** (o outro lado do `choice` de `infoRegimeTrab`, para
  servidor estatutário) — só `infoCeletista` (regime CLT) é modelado.
- **Endereço, dependentes, dados bancários, aviso prévio, contrato por prazo
  determinado, condições de trabalho especiais** — grupos adicionais do evento real
  que não foram lidos nesta rodada.
- **As tabelas nacionais** de sexo/raça-cor/grau de instrução/regime
  trabalhista/natureza de atividade/categoria/tipo de salário — aceitas por formato,
  não por enumeração (ver acima).

Fonte do XSD: mesma família já usada no resto do bloco eSocial
------------------------------------------------------------------------
`github.com/nfephp-org/sped-esocial`, `schemes/v_S_01_03_00/evtAdmissao.xsd` e
`tipos.xsd` — não a fonte primária oficial.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

__all__ = [
	"INDICADOR_ADMISSAO_ACAO_FISCAL",
	"INDICADOR_ADMISSAO_DECISAO_JUDICIAL",
	"INDICADOR_ADMISSAO_NORMAL",
	"TIPO_ADMISSAO_ADMISSAO",
	"TIPO_ADMISSAO_MUDANCA_CPF",
	"TIPO_ADMISSAO_TRANSFERENCIA_CONSORCIO",
	"TIPO_ADMISSAO_TRANSFERENCIA_DOMESTICO",
	"TIPO_ADMISSAO_TRANSFERENCIA_EMPRESA_INAPTA",
	"TIPO_ADMISSAO_TRANSFERENCIA_GRUPO_ECONOMICO",
	"TIPO_ADMISSAO_TRANSFERENCIA_SUCESSAO_FUSAO",
	"EsocialS2200Invalido",
	"IdeEvento",
	"InfoCeletista",
	"InfoContrato",
	"Trabalhador",
	"Vinculo",
]

# tpAdmissao — enumeração citada literalmente do XSD (com xs:enumeration/xs:documentation).
TIPO_ADMISSAO_ADMISSAO = 1
TIPO_ADMISSAO_TRANSFERENCIA_GRUPO_ECONOMICO = 2
TIPO_ADMISSAO_TRANSFERENCIA_CONSORCIO = 3
TIPO_ADMISSAO_TRANSFERENCIA_SUCESSAO_FUSAO = 4
TIPO_ADMISSAO_TRANSFERENCIA_DOMESTICO = 5
TIPO_ADMISSAO_MUDANCA_CPF = 6
TIPO_ADMISSAO_TRANSFERENCIA_EMPRESA_INAPTA = 7

_TIPOS_ADMISSAO_VALIDOS = frozenset(range(1, 8))

# indAdmissao — mesma confiança de tpAdmissao (enumeração literal do XSD).
INDICADOR_ADMISSAO_NORMAL = 1
INDICADOR_ADMISSAO_ACAO_FISCAL = 2
INDICADOR_ADMISSAO_DECISAO_JUDICIAL = 3

_INDICADORES_ADMISSAO_VALIDOS = frozenset({1, 2, 3})

# tpRegPrev — confiança intermediária, ver docstring do módulo.
_TIPOS_REGIME_PREVIDENCIARIO_VALIDOS = frozenset({1, 2, 3, 4})


class EsocialS2200Invalido(ValueError):
	"""Dado que impede a montagem do evento — campo fora do padrão do XSD."""


def _validar_digito_unico(valor: int, campo: str) -> None:
	if not (0 <= valor <= 9):
		raise EsocialS2200Invalido(f"{campo} deve ser um dígito único (0-9), recebido {valor}")


@dataclass(frozen=True)
class IdeEvento:
	"""`ideEvento` do S-2200 (`T_ideEvento_trab_admissao`, lido em `tipos.xsd`) —
	sem `perApur`/`indApuracao` (evento não periódico). `proc_emi` aqui exclui o
	valor `8` (`TS_procEmi_sem_8`), diferente do `procEmi` livre do S-1200."""

	ind_retif: int
	proc_emi: int
	ver_proc: str
	tp_amb: int
	nr_recibo: str | None = None

	def __post_init__(self):
		if self.ind_retif not in (1, 2):
			raise EsocialS2200Invalido(
				f"indRetif deve ser 1 (original) ou 2 (retificação), recebido {self.ind_retif}"
			)

		if self.ind_retif == 2 and not self.nr_recibo:
			raise EsocialS2200Invalido("nrRecibo é obrigatório quando indRetif=2 (retificação)")

		if self.tp_amb not in (1, 2):
			raise EsocialS2200Invalido(
				f"tpAmb deve ser 1 (Produção) ou 2 (Produção Restrita), recebido {self.tp_amb}"
			)

		_validar_digito_unico(self.proc_emi, "procEmi")

		if self.proc_emi == 8:
			raise EsocialS2200Invalido("procEmi não aceita o valor 8 neste evento (TS_procEmi_sem_8)")

		if not (1 <= len(self.ver_proc) <= 20):
			raise EsocialS2200Invalido(
				f"verProc deve ter entre 1 e 20 caracteres, recebido {self.ver_proc!r}"
			)


@dataclass(frozen=True)
class Trabalhador:
	"""`trabalhador` — dados cadastrais básicos. `sexo`/`raca_cor`/`grau_instr` são
	tabelas nacionais não trazidas para este projeto — aceitas como dígito único
	sem validar contra o domínio real."""

	cpf_trab: str
	nm_trab: str
	sexo: int
	raca_cor: int
	grau_instr: int

	def __post_init__(self):
		if not self.cpf_trab.isdigit() or len(self.cpf_trab) != 11:
			raise EsocialS2200Invalido(
				f"cpfTrab deve ter exatamente 11 dígitos numéricos, recebido {self.cpf_trab!r}"
			)

		if not self.nm_trab.strip():
			raise EsocialS2200Invalido("nmTrab não pode ser vazio")

		_validar_digito_unico(self.sexo, "sexo")
		_validar_digito_unico(self.raca_cor, "racaCor")
		_validar_digito_unico(self.grau_instr, "grauInstr")


@dataclass(frozen=True)
class Vinculo:
	"""`vinculo` — `tp_reg_prev` validado contra a faixa `1-4` (confiança
	intermediária, ver docstring do módulo); `tp_reg_trab` (regime CLT/estatutário)
	é tabela nacional não enumerada aqui. `cad_ini`: "S" (cadastramento inicial,
	vínculo já existente antes da obrigatoriedade) ou "N" (admissão de verdade)."""

	matricula: str
	tp_reg_trab: int
	tp_reg_prev: int
	cad_ini: str

	def __post_init__(self):
		if not (1 <= len(self.matricula) <= 30):
			raise EsocialS2200Invalido(
				f"matricula deve ter entre 1 e 30 caracteres, recebido {self.matricula!r}"
			)

		_validar_digito_unico(self.tp_reg_trab, "tpRegTrab")

		if self.tp_reg_prev not in _TIPOS_REGIME_PREVIDENCIARIO_VALIDOS:
			raise EsocialS2200Invalido(f"tpRegPrev deve ser 1, 2, 3 ou 4, recebido {self.tp_reg_prev}")

		if self.cad_ini not in ("S", "N"):
			raise EsocialS2200Invalido(f"cadIni deve ser 'S' ou 'N', recebido {self.cad_ini!r}")


@dataclass(frozen=True)
class InfoCeletista:
	"""`infoCeletista` (metade CLT do `choice` de `infoRegimeTrab` — a outra
	metade, `infoEstatutario`, não é modelada, ver docstring do módulo).

	`tp_admissao`/`ind_admissao` são os dois campos com enumeração literal
	confirmada nesta rodada — validados contra o domínio real, não só o formato.
	"""

	dt_adm: date
	tp_admissao: int
	ind_admissao: int
	cnpj_sind_categ_prof: str
	tp_reg_jor: int | None = None
	nat_atividade: int | None = None

	def __post_init__(self):
		if self.tp_admissao not in _TIPOS_ADMISSAO_VALIDOS:
			raise EsocialS2200Invalido(f"tpAdmissao deve estar entre 1 e 7, recebido {self.tp_admissao}")

		if self.ind_admissao not in _INDICADORES_ADMISSAO_VALIDOS:
			raise EsocialS2200Invalido(f"indAdmissao deve ser 1, 2 ou 3, recebido {self.ind_admissao}")

		if not self.cnpj_sind_categ_prof.isdigit() or len(self.cnpj_sind_categ_prof) != 14:
			raise EsocialS2200Invalido(
				f"cnpjSindCategProf deve ter exatamente 14 dígitos numéricos, "
				f"recebido {self.cnpj_sind_categ_prof!r}"
			)

		if self.tp_reg_jor is not None:
			_validar_digito_unico(self.tp_reg_jor, "tpRegJor")

		if self.nat_atividade is not None:
			_validar_digito_unico(self.nat_atividade, "natAtividade")


@dataclass(frozen=True)
class InfoContrato:
	"""`infoContrato` — `cod_categ`/`unid_sal_fixo`/`tp_salario` são tabelas
	nacionais não enumeradas aqui, aceitas só por formato (mesma disciplina de
	`esocial_s1200.DmDev.cod_categ`, aliás a mesma tabela de categoria)."""

	cod_categ: int
	nm_cargo: str
	valor_salario: Decimal
	unid_sal_fixo: int
	tp_salario: int

	def __post_init__(self):
		if not (100 <= self.cod_categ <= 999):
			raise EsocialS2200Invalido(f"codCateg deve ter exatamente 3 dígitos, recebido {self.cod_categ}")

		if not (1 <= len(self.nm_cargo) <= 100):
			raise EsocialS2200Invalido(
				f"nmCargo deve ter entre 1 e 100 caracteres, recebido {self.nm_cargo!r}"
			)

		if self.valor_salario < Decimal("0"):
			raise EsocialS2200Invalido(
				f"valor do salário não pode ser negativo, recebido {self.valor_salario}"
			)

		_validar_digito_unico(self.unid_sal_fixo, "unidSalFixo")
		_validar_digito_unico(self.tp_salario, "tpSalario")
