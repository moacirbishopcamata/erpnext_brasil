# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Converte a árvore de dataclasses do S-1200 (`esocial_s1200.py`) na árvore de
dicionário que `fiscal/documento/serializacao.para_xml` sabe transformar em XML.

Onde isto se encaixa
--------------------
Mesmo papel de `fiscal/documento/nfe.py::montar_nfe` para a NF-e: o agregado de
negócio (dataclasses imutáveis, já validados no `__post_init__`) de um lado,
`para_xml` (genérico, sem saber nada de eSocial) do outro — este módulo é a ponte.
Reaproveita `para_xml` de propósito (é serialização dict→XML genérica, não específica
da NF-e, apesar de onde mora — mesma decisão já tomada em
`integracao/assinador_esocial.py`), em vez de escrever outro serializador do zero.

O que este módulo NÃO faz
--------------------------------
Monta a árvore **sem assinatura** — não chama `AssinadorLocalEsocial` nem
`folha/esocial_assinatura.py`. Assinar exige primeiro serializar (para ter os bytes
que o assinador canonicaliza), depois mesclar o `Signature` resultante de volta na
árvore como irmão de `evtRemun`, e só então serializar de novo, desta vez o
documento completo e assinado. Essa orquestração cabe na camada de integração,
quando o envio de verdade for implementado — este módulo só entrega a árvore de
negócio pronta para o primeiro desses dois `para_xml`.

Namespace do evento
--------------------------
`NAMESPACE_EVT_REMUN` veio de um resultado de busca que citava literalmente
`"http://www.esocial.gov.br/schema/evt/evtRemun/v_S_01_03_00:TS_qtdRubr"` — o
namespace do tipo `TS_qtdRubr` do XSD, que carrega o namespace do evento em si. Não
é uma leitura direta da declaração `targetNamespace` do XSD — mesma cautela de fonte
já registrada para o resto do módulo eSocial deste projeto.

A pegadinha do namespace, aplicada aqui
------------------------------------------------
`docs/rh-esocial-assinatura.md` já registrou que o XML do eSocial deve conter
**apenas** o namespace do evento no atributo `xmlns` da raiz — `para_xml` já tem esse
comportamento (só declara namespace na raiz, quando ainda não há um; não introduz
`xsi`/`xsd` em lugar nenhum), então não é preciso nenhum cuidado extra aqui além de
não acrescentar esses atributos manualmente.

Funções puras: nenhuma dependência do Frappe, nenhuma biblioteca de criptografia.
"""

from erpnext_brasil.folha.esocial_s1200 import (
	DmDev,
	IdeEmpregador,
	IdeEstabLot,
	IdeEvento,
	IdeTrabalhador,
	InfoComplem,
	InfoPerApur,
	ItemRemuneracao,
	RemunPerApur,
)

__all__ = ["NAMESPACE_EVT_REMUN", "montar_evt_remun"]

NAMESPACE_EVT_REMUN = "http://www.esocial.gov.br/schema/evt/evtRemun/v_S_01_03_00"


def _dict_ide_evento(ide_evento: IdeEvento) -> dict:
	return {
		"indRetif": ide_evento.ind_retif,
		"nrRecibo": ide_evento.nr_recibo,
		"indApuracao": ide_evento.ind_apuracao,
		"perApur": ide_evento.per_apur,
		"tpAmb": ide_evento.tp_amb,
		"procEmi": ide_evento.proc_emi,
		"verProc": ide_evento.ver_proc,
	}


def _dict_ide_empregador(ide_empregador: IdeEmpregador) -> dict:
	return {"tpInsc": ide_empregador.tp_insc, "nrInsc": ide_empregador.nr_insc}


def _dict_info_complem(info_complem: InfoComplem) -> dict:
	return {
		"nmTrab": info_complem.nm_trab,
		"dtNascto": info_complem.dt_nascto,
		"codCBO": info_complem.cod_cbo,
		"natAtividade": info_complem.nat_atividade,
		"qtdDiasTrab": info_complem.qtd_dias_trab,
	}


def _dict_ide_trabalhador(ide_trabalhador: IdeTrabalhador) -> dict:
	return {
		"cpfTrab": ide_trabalhador.cpf_trab,
		"nisTrab": ide_trabalhador.nis_trab,
		"infoComplem": (
			_dict_info_complem(ide_trabalhador.info_complem) if ide_trabalhador.info_complem else None
		),
	}


def _dict_item_remuneracao(item: ItemRemuneracao) -> dict:
	return {
		"codRubr": item.cod_rubr,
		"ideTabRubr": item.ide_tab_rubr,
		"qtdRubr": item.qtd_rubr,
		"fatorRubr": item.fator_rubr,
		"vrUnit": item.vr_unit,
		"vrRubr": item.vr_rubr,
	}


def _dict_remun_per_apur(remun: RemunPerApur) -> dict:
	return {
		"matricula": remun.matricula,
		"indSimples": remun.ind_simples,
		"itensRemun": [_dict_item_remuneracao(item) for item in remun.itens_remun],
	}


def _dict_ide_estab_lot(estab_lot: IdeEstabLot) -> dict:
	return {
		"tpInsc": estab_lot.tp_insc,
		"nrInsc": estab_lot.nr_insc,
		"codLotacao": estab_lot.cod_lotacao,
		"qtdDiasAv": estab_lot.qtd_dias_av,
		"remunPerApur": [_dict_remun_per_apur(remun) for remun in estab_lot.remun_per_apur],
	}


def _dict_info_per_apur(info_per_apur: InfoPerApur) -> dict:
	return {"ideEstabLot": [_dict_ide_estab_lot(estab_lot) for estab_lot in info_per_apur.ide_estab_lot]}


def _dict_dm_dev(dm_dev: DmDev) -> dict:
	return {
		"ideDmDev": dm_dev.ide_dm_dev,
		"codCateg": dm_dev.cod_categ,
		"infoPerApur": _dict_info_per_apur(dm_dev.info_per_apur) if dm_dev.info_per_apur else None,
	}


def montar_evt_remun(
	id_evento: str,
	ide_evento: IdeEvento,
	ide_empregador: IdeEmpregador,
	ide_trabalhador: IdeTrabalhador,
	dm_dev: tuple[DmDev, ...],
) -> dict:
	"""Monta a árvore `eSocial > evtRemun` pronta para `para_xml` — sem assinatura
	(ver docstring do módulo). `id_evento` é o atributo `Id` do elemento `evtRemun`;
	este módulo não o gera (o formato de 36 caracteres citado em
	`docs/rh-estado-esocial.md` não foi implementado nesta rodada), recebe pronto.
	"""
	return {
		"eSocial": {
			"@xmlns": NAMESPACE_EVT_REMUN,
			"evtRemun": {
				"@Id": id_evento,
				"ideEvento": _dict_ide_evento(ide_evento),
				"ideEmpregador": _dict_ide_empregador(ide_empregador),
				"ideTrabalhador": _dict_ide_trabalhador(ide_trabalhador),
				"dmDev": [_dict_dm_dev(item) for item in dm_dev],
			},
		}
	}
