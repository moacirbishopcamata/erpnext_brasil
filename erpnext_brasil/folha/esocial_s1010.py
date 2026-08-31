# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""eSocial S-1010 (evtTabRubrica): Tabela de Rubricas.

A peça que faltava para o S-1200 funcionar de verdade
------------------------------------------------------------
Todo módulo do bloco S-1200 (`esocial_s1200.py`, `esocial_lote.py`) recebeu
`cod_rubr`/`ide_tab_rubr` como dado pronto de quem chama, documentando
explicitamente que "a tabela de rubricas (evento S-1010) é configuração do
empregador, este projeto não a modela". Isto modela a estrutura do **evento** que
cria essa configuração — não substitui a decisão de que os códigos em si são
próprios de cada empregador (continuam vindo de fora, aqui só a forma do evento que
os cadastra).

O que este módulo cobre, e o que fica de fora
--------------------------------------------------
Cobre `ideRubrica` e os campos confirmados de `dadosRubrica` — incluindo os quatro
códigos de incidência com enumeração real do XSD (`codIncCP`, `codIncFGTS`,
`codIncCPRP`, `codIncPisPasep`; `codIncIRRF` é só um inteiro livre, sem enum
declarada). Fora de escopo, deliberadamente:

- **`ideProcessoCP`/`ideProcessoIRRF`/`ideProcessoFGTS`/`ideProcessoPisPasep`** —
  processos judiciais que suspendem a incidência de uma rubrica, cada um com sua
  própria tabela de código de suspensão (`codSusp`) — mesma decisão de excluir
  `procJudTrab` do S-1200: grupo raro, tabela de domínio própria não modelada.
- **`novaValidade`** (alteração de vigência numa alteração de rubrica) — variante
  rara do fluxo de alteração.
- **`natRubr`** ("natureza da rubrica") é aceito como string sem validar contra a
  Tabela 3 do eSocial (centenas de códigos mantidos pela RFB/nomenclatura nacional)
  — só o formato solto é conferido, o domínio em si não foi trazido para este
  projeto.
- **Operação `exclusao`** (só `ideRubrica`, sem `dadosRubrica`) — não modelada como
  variante separada; `IdeRubrica` sozinho já serve para montá-la, mas não há uma
  função dedicada tipo `montar_exclusao_rubrica`.

Códigos de incidência: tabelas de domínio confirmadas, não reinventadas
------------------------------------------------------------------------------------
`codIncCP` (24 valores), `codIncFGTS` (8 valores), `codIncCPRP` (7 valores),
`codIncPisPasep` (5 valores) — todos enumerados diretamente pelo XSD
(`evtTabRubrica.xsd`, `nfephp-org/sped-esocial`), não uma lista feita à mão. Note
que `codIncFGTS` aqui é a mesma tabela referenciada por uma regra de validação do
S-1200 já citada em `docs/rh-esocial-s1200.md` ("rubrica com codIncFGTS em [21, 93]
só pode ser usada em eventos de rescisão") — a mesma tabela nacional, vista de dois
ângulos diferentes.

Fonte do XSD: mesma família já usada no resto do bloco eSocial
------------------------------------------------------------------------------
`github.com/nfephp-org/sped-esocial`, `schemes/v_S_01_03_00/evtTabRubrica.xsd` — não
a fonte primária oficial, mesma advertência já registrada para os outros módulos.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass

__all__ = [
	"CODIGOS_INCIDENCIA_CP",
	"CODIGOS_INCIDENCIA_CPRP",
	"CODIGOS_INCIDENCIA_FGTS",
	"CODIGOS_INCIDENCIA_PIS_PASEP",
	"TIPO_RUBRICA_DESCONTO",
	"TIPO_RUBRICA_INFORMATIVA",
	"TIPO_RUBRICA_INFORMATIVA_DEDUTORA",
	"TIPO_RUBRICA_VENCIMENTO",
	"DadosRubrica",
	"EsocialS1010Invalido",
	"IdeRubrica",
]

# Confirmados diretamente no XSD (evtTabRubrica.xsd) — não uma lista feita à mão.
CODIGOS_INCIDENCIA_CP = frozenset(
	{
		"00", "01", "11", "12", "13", "14", "15", "16", "21", "22", "25", "26",
		"31", "32", "34", "35", "51", "91", "92", "93", "94", "95", "96", "97", "98",
	}
)  # fmt: skip
CODIGOS_INCIDENCIA_FGTS = frozenset({"00", "11", "12", "21", "31", "91", "92", "93"})
CODIGOS_INCIDENCIA_CPRP = frozenset({"00", "11", "12", "31", "32", "91", "92"})
CODIGOS_INCIDENCIA_PIS_PASEP = frozenset({"00", "11", "12", "91", "92"})

TIPO_RUBRICA_VENCIMENTO = 1
TIPO_RUBRICA_DESCONTO = 2
TIPO_RUBRICA_INFORMATIVA = 3
TIPO_RUBRICA_INFORMATIVA_DEDUTORA = 4

_TIPOS_RUBRICA_VALIDOS = (
	TIPO_RUBRICA_VENCIMENTO,
	TIPO_RUBRICA_DESCONTO,
	TIPO_RUBRICA_INFORMATIVA,
	TIPO_RUBRICA_INFORMATIVA_DEDUTORA,
)


class EsocialS1010Invalido(ValueError):
	"""Dado que impede a montagem do evento — campo fora do padrão do XSD."""


@dataclass(frozen=True)
class IdeRubrica:
	"""`ideRubrica` — identifica a rubrica dentro da tabela do próprio empregador.

	`cod_rubr`/`ide_tab_rubr` são exatamente o que `esocial_s1200.ItemRemuneracao`
	espera receber pronto — este evento é quem os cria/mantém."""

	cod_rubr: str
	ide_tab_rubr: str
	ini_valid: str
	fim_valid: str | None = None

	def __post_init__(self):
		if not (1 <= len(self.cod_rubr) <= 30):
			raise EsocialS1010Invalido(f"codRubr deve ter entre 1 e 30 caracteres, recebido {self.cod_rubr!r}")

		if not (1 <= len(self.ide_tab_rubr) <= 8):
			raise EsocialS1010Invalido(
				f"ideTabRubr deve ter entre 1 e 8 caracteres, recebido {self.ide_tab_rubr!r}"
			)

		if not self.ini_valid:
			raise EsocialS1010Invalido("iniValid não pode ser vazio")


@dataclass(frozen=True)
class DadosRubrica:
	"""`dadosRubrica` — a definição da rubrica em si: descrição, natureza e como ela
	incide sobre INSS/IRRF/FGTS/PIS-PASEP.

	`cod_inc_irrf` não tem enumeração no XSD (é um inteiro livre de 1 a 4 dígitos) —
	só o formato é validado, não um domínio de valores (diferente dos outros três
	códigos de incidência, que têm tabela fechada confirmada)."""

	dsc_rubr: str
	nat_rubr: str
	tp_rubr: int
	cod_inc_cp: str
	cod_inc_irrf: int
	cod_inc_fgts: str
	cod_inc_cprp: str | None = None
	cod_inc_pis_pasep: str | None = None
	teto_remun: str | None = None
	observacao: str | None = None

	def __post_init__(self):
		if not (1 <= len(self.dsc_rubr) <= 100):
			raise EsocialS1010Invalido(f"dscRubr deve ter entre 1 e 100 caracteres, recebido {self.dsc_rubr!r}")

		if not self.nat_rubr:
			raise EsocialS1010Invalido("natRubr não pode ser vazio")

		if self.tp_rubr not in _TIPOS_RUBRICA_VALIDOS:
			raise EsocialS1010Invalido(f"tpRubr deve ser 1, 2, 3 ou 4, recebido {self.tp_rubr}")

		if self.cod_inc_cp not in CODIGOS_INCIDENCIA_CP:
			raise EsocialS1010Invalido(f"codIncCP {self.cod_inc_cp!r} não está na tabela de domínio conhecida")

		if not (0 <= self.cod_inc_irrf <= 9999):
			raise EsocialS1010Invalido(f"codIncIRRF deve ter de 1 a 4 dígitos, recebido {self.cod_inc_irrf}")

		if self.cod_inc_fgts not in CODIGOS_INCIDENCIA_FGTS:
			raise EsocialS1010Invalido(f"codIncFGTS {self.cod_inc_fgts!r} não está na tabela de domínio conhecida")

		if self.cod_inc_cprp is not None and self.cod_inc_cprp not in CODIGOS_INCIDENCIA_CPRP:
			raise EsocialS1010Invalido(f"codIncCPRP {self.cod_inc_cprp!r} não está na tabela de domínio conhecida")

		if self.cod_inc_pis_pasep is not None and self.cod_inc_pis_pasep not in CODIGOS_INCIDENCIA_PIS_PASEP:
			raise EsocialS1010Invalido(
				f"codIncPisPasep {self.cod_inc_pis_pasep!r} não está na tabela de domínio conhecida"
			)

		if self.teto_remun is not None and self.teto_remun not in ("S", "N"):
			raise EsocialS1010Invalido(f"tetoRemun deve ser 'S' ou 'N', recebido {self.teto_remun!r}")
