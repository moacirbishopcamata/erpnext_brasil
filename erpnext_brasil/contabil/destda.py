# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""DeSTDA (Declaração de Substituição Tributária, Diferencial de Alíquota e Antecipação):
registros de abertura (Bloco 0) e de declaração de valores (Bloco G).

Por que existe, e o obstáculo que precisou de uma fonte nova
------------------------------------------------------------------------------
Registrado como bloqueado em memória (2026-08-31): diferente de todo o resto do SPED/eSocial
já coberto neste projeto, não existe projeto open-source de referência com o layout (nenhum
`nfephp-org/sped-destda`), e duas tentativas de ler o manual oficial (Ato COTEPE/ICMS 47/2015)
falharam — uma recusada pela ferramenta de busca por cautela de direitos autorais, outra por
HTTP 403. Retomado com uma fonte nova, não tentando de novo a mesma pergunta: documentação
técnica de um ERP comercial (`documentacao.senior.com.br`) que replica os registros e campos do
leiaute para a própria geração do arquivo — mesmo padrão de confiança já aceito para a tabela de
CFOP de transporte (`docs/cfop-transporte.md`) quando o texto oficial está inacessível.

Nível de confiança, declarado — mais baixo que a maioria dos módulos SPED/eSocial deste projeto
------------------------------------------------------------------------------------------
Os **códigos de registro** (`0000`, `0001`, `G001`, `G020`, `G605`, `G615`, `G625`, `0990`,
`G990`) e a **lista de campos de cada um** vêm de fonte secundária única (o texto do Ato COTEPE
não foi lido). O significado de `IND_SIT` (situação do registro G605 — DIFAL interestadual vs.
antecipação, com/sem encerramento da fase de tributação) tem corroboração de uma fonte só (uma
segunda tentativa de checagem falhou por DNS inacessível) — por isso modelado com constantes,
mas com esse nível de confiança citado aqui, não escondido.

Reuso: mesma camada de serialização do resto do SPED
------------------------------------------------------------------------------
`montar_linha`/`formatar_campo` de `contabil/sped_texto.py` são reaproveitados sem alteração —
mesmo formato pipe-delimited (`|campo|campo|`), mesma convenção de data `DDMMAAAA` e decimal com
vírgula já confirmada para EFD-ICMS/IPI e ECD. Nada de específico do DeSTDA muda o formato de
linha, só os campos de cada registro.

Escopo: núcleo mínimo de uma declaração, não o layout inteiro
------------------------------------------------------------------------------------------
Implementados: `0000` (abertura/identificação do contribuinte), `0001`/`G001` (indicadores de
abertura de bloco), `G020` (período), `G605`/`G615`/`G625` (os três registros que carregam os
valores declarados — diferencial de alíquota/antecipação por UF de origem, e substituição
tributária por UF de destino), `0990`/`G990` (encerramento de bloco, com contagem). Fora de
escopo deste incremento, documentado: `0002` (inscrições como substituto), `0005` (dados
complementares), `0030` (perfil do contribuinte — campos com nomes ambíguos na fonte disponível,
não modelados até uma fonte mais clara), `0100` (contabilista), `G600`/`G610`/`G620`
(totalizadores intermediários que os sistemas geradores calculam a partir dos registros de
detalhe — não implementados porque este módulo modela só o que o contribuinte declara, não os
totais derivados).

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

__all__ = [
	"IND_GEF_ICMS",
	"IND_GEF_ISS",
	"IND_GEF_RECALCULO",
	"IND_GEF_SEM_DADOS",
	"IND_GEF_SIMPLES_NACIONAL",
	"IND_SIT_ANTECIPACAO_COM_ENCERRAMENTO",
	"IND_SIT_ANTECIPACAO_SEM_ENCERRAMENTO",
	"IND_SIT_ANTECIPACAO_SIMPLES",
	"IND_SIT_DIFAL_INTERESTADUAL",
	"Identificacao",
	"montar_0000",
	"montar_0001",
	"montar_0990",
	"montar_g001",
	"montar_g020",
	"montar_g605",
	"montar_g615",
	"montar_g625",
	"montar_g990",
]

# `IND_GEF` de G020 — confirmado em fonte secundária (Senior).
IND_GEF_ISS = "0"
IND_GEF_ICMS = "1"
IND_GEF_SIMPLES_NACIONAL = "2"
IND_GEF_RECALCULO = "8"
IND_GEF_SEM_DADOS = "9"

# `IND_SIT` de G605 — confirmado em fonte única, ver docstring do módulo.
IND_SIT_DIFAL_INTERESTADUAL = "0"
IND_SIT_ANTECIPACAO_SIMPLES = "1"
IND_SIT_ANTECIPACAO_COM_ENCERRAMENTO = "2"
IND_SIT_ANTECIPACAO_SEM_ENCERRAMENTO = "3"


@dataclass(frozen=True)
class Identificacao:
	"""Dados de `0000` — abertura do arquivo e identificação do contribuinte."""

	periodo_inicial: date
	periodo_final: date
	nome_empresarial: str
	cnpj: str
	uf: str
	inscricao_estadual: str
	codigo_municipio: str


def montar_0000(identificacao: Identificacao) -> dict:
	"""Monta o registro `0000`.

	A fonte lista mais campos depois de `SUFRAMA` (`COD_VER`, `COD_FIN`, `COD_CTD`,
	`PAIS`, `FANTASIA`, `NIRE`, `CPF`, um segundo campo vazio) — deliberadamente não
	incluídos ainda: são metadados de versão/finalidade do arquivo e dados que só se
	aplicam a casos que este primeiro incremento não cobre (contribuinte pessoa física,
	NIRE de empresa registrada na Junta Comercial). Ficam para quando o restante do
	fluxo de geração de arquivo estiver desenhado.
	"""
	return {
		"REG": "0000",
		"LFPD": "LFPD",
		"DT_INI": identificacao.periodo_inicial,
		"DT_FIN": identificacao.periodo_final,
		"NOME_EMPR": identificacao.nome_empresarial,
		"CNPJ": identificacao.cnpj,
		"UF": identificacao.uf,
		"IE": identificacao.inscricao_estadual,
		"COD_MUN": identificacao.codigo_municipio,
		"IM": "",
		"VAZIO1": "",
		"SUFRAMA": "",
	}


def montar_0001(tem_dados: bool) -> dict:
	"""Monta o registro `0001` — abertura do Bloco 0. `IND_DAD`: `"0"` com conteúdo,
	`"1"` sem conteúdo."""
	return {"REG": "0001", "IND_DAD": "0" if tem_dados else "1"}


def montar_g001(tem_dados: bool) -> dict:
	"""Monta o registro `G001` — abertura do Bloco G, mesma convenção de `IND_DAD`
	de `montar_0001`."""
	return {"REG": "G001", "IND_DAD": "0" if tem_dados else "1"}


def montar_g020(indicador: str, periodo_inicial: date, periodo_final: date) -> dict:
	"""Monta o registro `G020` — indicador de conteúdo e período da guia."""
	return {
		"REG": "G020",
		"IND_GEF": indicador,
		"DT_INI": periodo_inicial,
		"DT_FIN": periodo_final,
	}


def montar_g605(
	indicador_situacao: str,
	valor_total_notas: Decimal,
	valor_total_ajustes: Decimal,
	valor_total_declarar: Decimal,
) -> dict:
	"""Monta `G605` — diferencial de alíquota/antecipação, valores totais (não por UF).

	`valor_total_declarar` normalmente é `valor_total_notas + valor_total_ajustes`, mas
	este módulo não recalcula — recebe o valor já apurado, mesma disciplina de
	`efd_icms_ipi.py` (a apuração é responsabilidade de outro módulo, este só formata).
	"""
	return {
		"REG": "G605",
		"IND_SIT": indicador_situacao,
		"VL_TOT_ANTC_NF": valor_total_notas,
		"VL_TOT_AJ_ANTC": valor_total_ajustes,
		"VL_TOT_DA_ANTC": valor_total_declarar,
	}


def montar_g615(
	uf: str,
	valor_total_st_uf: Decimal,
	valor_total_ajuste_uf: Decimal,
	valor_total_declarar_uf: Decimal,
) -> dict:
	"""Monta `G615` — antecipação por UF de origem (venda para consumo final)."""
	return {
		"REG": "G615",
		"UF": uf,
		"VL_TOT_ST_UF_NF": valor_total_st_uf,
		"VL_TOT_AJST_UF": valor_total_ajuste_uf,
		"VL_TOT_ST_UF_DE": valor_total_declarar_uf,
	}


def montar_g625(
	uf: str,
	indicador_tipo_st: str,
	valor_total_st: Decimal,
	valor_total_ajuste: Decimal,
	valor_total_declarar: Decimal,
) -> dict:
	"""Monta `G625` — substituição tributária por UF de destino."""
	return {
		"REG": "G625",
		"UF": uf,
		"IND_TP_ST": indicador_tipo_st,
		"VL_TOT_ST_NF": valor_total_st,
		"VL_TOT_AJ_ST": valor_total_ajuste,
		"VL_TOT_DEC_ST": valor_total_declarar,
	}


def montar_0990(quantidade_linhas_bloco_0: int) -> dict:
	"""Monta `0990` — encerramento do Bloco 0, com a contagem de linhas do próprio
	bloco (incluindo o próprio `0990`, mesma convenção de contagem do SPED em geral)."""
	return {"REG": "0990", "QTD_LIN_0": str(quantidade_linhas_bloco_0)}


def montar_g990(quantidade_linhas_bloco_g: int) -> dict:
	"""Monta `G990` — encerramento do Bloco G."""
	return {"REG": "G990", "QTD_LIN_G": str(quantidade_linhas_bloco_g)}
