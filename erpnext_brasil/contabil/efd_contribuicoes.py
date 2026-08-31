# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""EFD-Contribuições: registros M200/M210 (PIS/Pasep) e M600/M610 (Cofins).

Bloco M — apuração das contribuições, não o EFD-Contribuições inteiro
------------------------------------------------------------------------------
Item citado como fora de escopo desde as primeiras sessões deste projeto. Este
módulo cobre só a apuração final do Bloco M — os registros que consolidam o que já
foi apurado por item/documento em outro lugar (blocos A/C/D/F, não modelados aqui,
mesma disciplina de `efd_icms_ipi.py` não modelar os blocos C/H, só o E110/E520 de
apuração).

PIS e Cofins têm o mesmo layout, confirmado, não só "parecido"
------------------------------------------------------------------------------
Diferente de outras "semelhanças" que se revelaram falsas neste projeto (S-2200 ×
S-1200 no bloco eSocial, por exemplo), aqui a fonte confirma que M600 usa
exatamente a mesma numeração de campo que M200 (a documentação do M600 cita
"Campos 02 e 09", os mesmos números do M200) e M610 tem a mesma estrutura do M210,
trocando só `_BC_PIS`/`ALIQ_PIS`/`ALIQ_PIS_QUANT` por
`_BC_COFINS`/`ALIQ_COFINS`/`ALIQ_COFINS_QUANT`. Por isso `DetalhamentoContribuicao`
e `ConsolidacaoContribuicao` são compartilhados entre as duas funções de cada par —
uma reformulação genuína, não uma coincidência de nome.

Layout vigente: fatos geradores a partir de 01/01/2019
------------------------------------------------------------------
O M210/M610 tem uma versão anterior (até 31/12/2018) com campos em ordem diferente
(sem a separação `VL_AJUS_ACRES_BC_PIS`/`VL_AJUS_REDUC_BC_PIS` da base antes/depois
de ajuste) — não modelada aqui, só o layout vigente.

`COD_CONT` não é validado contra domínio
------------------------------------------------
Referencia a "Tabela 4.3.5 — Código da Contribuição Social", uma tabela nacional de
códigos por situação/alíquota que não foi trazida para este projeto (mesma
disciplina de `esocial_s2200.py` não enumerar tabelas nacionais grandes) — aceito
como string, só o formato é conferido.

Fórmulas, citadas literalmente pela fonte (não recalculadas por suposição)
------------------------------------------------------------------------------------------
M210/M610: `VL_BC_CONT_AJUS = VL_BC_CONT + VL_AJUS_ACRES_BC − VL_AJUS_REDUC_BC`;
`VL_CONT_PER = VL_CONT_APUR + VL_AJUS_ACRES − VL_AJUS_REDUC − VL_CONT_DIFER +
VL_CONT_DIFER_ANT`.

M200/M600: `VL_TOT_CONT_NC_DEV = VL_TOT_CONT_NC_PER − VL_TOT_CRED_DESC −
VL_TOT_CRED_DESC_ANT`; `VL_CONT_NC_REC = VL_TOT_CONT_NC_DEV − VL_RET_NC −
VL_OUT_DED_NC`; `VL_CONT_CUM_REC = VL_TOT_CONT_CUM_PER − VL_RET_CUM −
VL_OUT_DED_CUM`; `VL_TOT_CONT_REC = VL_CONT_NC_REC + VL_CONT_CUM_REC`.

Fonte: `vriconsulting.com.br`, especializado em SPED — mesma fonte já usada em
`efd_icms_ipi.py`, cruzada por independência de conteúdo entre os quatro registros
(M200/M210/M600/M610 lidos em páginas separadas, concordância confirma a leitura),
não o Guia Prático oficial (`sped.rfb.gov.br`) lido diretamente.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from decimal import Decimal

__all__ = [
	"ConsolidacaoContribuicao",
	"DetalhamentoContribuicao",
	"EfdContribuicoesInvalido",
	"montar_m200",
	"montar_m210",
	"montar_m600",
	"montar_m610",
]

ZERO = Decimal("0.00")


class EfdContribuicoesInvalido(ValueError):
	"""Dado que impede a montagem do registro — campo fora do formato exigido."""


@dataclass(frozen=True)
class DetalhamentoContribuicao:
	"""Dados de entrada de `montar_m210`/`montar_m610` — compartilhados entre PIS e
	Cofins porque o layout é o mesmo (ver docstring do módulo). `aliquota`/
	`quant_bc`/`aliquota_quant` são os três campos opcionais de apuração por
	alíquota (percentual) ou por quantidade (regime específico, cigarros/combustíveis)
	— mutuamente aplicáveis conforme o regime, não validados como exclusivos aqui."""

	cod_cont: str
	vl_rec_brt: Decimal
	vl_bc_cont: Decimal
	vl_ajus_acres_bc: Decimal = ZERO
	vl_ajus_reduc_bc: Decimal = ZERO
	aliquota: Decimal | None = None
	quant_bc: Decimal | None = None
	aliquota_quant: Decimal | None = None
	vl_cont_apur: Decimal = ZERO
	vl_ajus_acres: Decimal = ZERO
	vl_ajus_reduc: Decimal = ZERO
	vl_cont_difer: Decimal = ZERO
	vl_cont_difer_ant: Decimal = ZERO

	def __post_init__(self):
		if not (1 <= len(self.cod_cont) <= 2):
			raise EfdContribuicoesInvalido(f"codCont deve ter até 2 caracteres, recebido {self.cod_cont!r}")


@dataclass(frozen=True)
class ConsolidacaoContribuicao:
	"""Dados de entrada de `montar_m200`/`montar_m600` — mesmos nomes de campo nos
	dois registros, confirmado pela fonte (ver docstring do módulo)."""

	vl_tot_cont_nc_per: Decimal = ZERO
	vl_tot_cred_desc: Decimal = ZERO
	vl_tot_cred_desc_ant: Decimal = ZERO
	vl_ret_nc: Decimal = ZERO
	vl_out_ded_nc: Decimal = ZERO
	vl_tot_cont_cum_per: Decimal = ZERO
	vl_ret_cum: Decimal = ZERO
	vl_out_ded_cum: Decimal = ZERO


def _montar_detalhamento(reg: str, sufixo_aliquota: str, d: DetalhamentoContribuicao) -> dict:
	vl_bc_cont_ajus = d.vl_bc_cont + d.vl_ajus_acres_bc - d.vl_ajus_reduc_bc
	vl_cont_per = d.vl_cont_apur + d.vl_ajus_acres - d.vl_ajus_reduc - d.vl_cont_difer + d.vl_cont_difer_ant

	return {
		"REG": reg,
		"COD_CONT": d.cod_cont,
		"VL_REC_BRT": d.vl_rec_brt,
		"VL_BC_CONT": d.vl_bc_cont,
		f"VL_AJUS_ACRES_BC_{sufixo_aliquota}": d.vl_ajus_acres_bc,
		f"VL_AJUS_REDUC_BC_{sufixo_aliquota}": d.vl_ajus_reduc_bc,
		"VL_BC_CONT_AJUS": vl_bc_cont_ajus,
		f"ALIQ_{sufixo_aliquota}": d.aliquota,
		f"QUANT_BC_{sufixo_aliquota}": d.quant_bc,
		f"ALIQ_{sufixo_aliquota}_QUANT": d.aliquota_quant,
		"VL_CONT_APUR": d.vl_cont_apur,
		"VL_AJUS_ACRES": d.vl_ajus_acres,
		"VL_AJUS_REDUC": d.vl_ajus_reduc,
		"VL_CONT_DIFER": d.vl_cont_difer,
		"VL_CONT_DIFER_ANT": d.vl_cont_difer_ant,
		"VL_CONT_PER": vl_cont_per,
	}


def montar_m210(d: DetalhamentoContribuicao) -> dict:
	"""Campos do registro M210 ("Detalhamento da Contribuição para o PIS/Pasep do
	Período"), layout vigente desde 01/01/2019, na ordem oficial."""
	return _montar_detalhamento("M210", "PIS", d)


def montar_m610(d: DetalhamentoContribuicao) -> dict:
	"""Campos do registro M610 ("Detalhamento da Contribuição para a Seguridade
	Social - Cofins do Período") — mesmo layout do M210, ver docstring do módulo."""
	return _montar_detalhamento("M610", "COFINS", d)


def _montar_consolidacao(reg: str, c: ConsolidacaoContribuicao) -> dict:
	vl_tot_cont_nc_dev = c.vl_tot_cont_nc_per - c.vl_tot_cred_desc - c.vl_tot_cred_desc_ant
	vl_cont_nc_rec = vl_tot_cont_nc_dev - c.vl_ret_nc - c.vl_out_ded_nc
	vl_cont_cum_rec = c.vl_tot_cont_cum_per - c.vl_ret_cum - c.vl_out_ded_cum
	vl_tot_cont_rec = vl_cont_nc_rec + vl_cont_cum_rec

	return {
		"REG": reg,
		"VL_TOT_CONT_NC_PER": c.vl_tot_cont_nc_per,
		"VL_TOT_CRED_DESC": c.vl_tot_cred_desc,
		"VL_TOT_CRED_DESC_ANT": c.vl_tot_cred_desc_ant,
		"VL_TOT_CONT_NC_DEV": vl_tot_cont_nc_dev,
		"VL_RET_NC": c.vl_ret_nc,
		"VL_OUT_DED_NC": c.vl_out_ded_nc,
		"VL_CONT_NC_REC": vl_cont_nc_rec,
		"VL_TOT_CONT_CUM_PER": c.vl_tot_cont_cum_per,
		"VL_RET_CUM": c.vl_ret_cum,
		"VL_OUT_DED_CUM": c.vl_out_ded_cum,
		"VL_CONT_CUM_REC": vl_cont_cum_rec,
		"VL_TOT_CONT_REC": vl_tot_cont_rec,
	}


def montar_m200(c: ConsolidacaoContribuicao) -> dict:
	"""Campos do registro M200 ("Consolidação da Contribuição para o PIS/Pasep do
	Período"), na ordem oficial."""
	return _montar_consolidacao("M200", c)


def montar_m600(c: ConsolidacaoContribuicao) -> dict:
	"""Campos do registro M600 ("Consolidação da Contribuição para a Seguridade
	Social - Cofins do Período") — mesmos nomes de campo do M200, ver docstring do
	módulo."""
	return _montar_consolidacao("M600", c)
