# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Inutiliza uma faixa de numeração de uma série e **grava o resultado** em `Transmissao Fiscal`.

`TransporteSefaz.inutilizar` já enviava o pedido; faltava quem o chamasse e transformasse a resposta em registro. Sem o
registro, o relatório `Lacunas de Numeracao` não tinha como saber que a faixa foi inutilizada.

O documento da transmissão é a **série** (`Numeracao Fiscal`), não uma nota: inutilizar é declarar que números
daquela série não foram usados, e não existe documento nem chave (`transmissao_registro`).

Falha antes de gastar a chamada: faixa acima do contador, ou com número que já tem desfecho, é recusada aqui
(`validar_faixa_a_inutilizar`). Rejeição da SEFAZ é gravada **e commitada** antes de virar erro — `throw` desfaz a
transação, e a rejeição ficaria sem rastro (mesma disciplina de `eventos_cte._concluir`).

Estado de verificação: o envio real depende de certificado A1 e homologação; o bench exercita tudo com transporte
falso (`tests_bench/test_inutilizacao_fiscal.py`).
"""

from datetime import datetime
from functools import partial

import frappe
from frappe import _

from erpnext_brasil.fiscal.documento.inutilizacao import InutilizacaoInvalida, validar_faixa_a_inutilizar
from erpnext_brasil.fiscal.documento.transmissao_registro import (
	SITUACAO_AUTORIZADO,
	SITUACAO_REJEITADO,
	TIPO_INUTILIZACAO,
)
from erpnext_brasil.integracao.certificado_a1 import (
	ambiente_sefaz_da_empresa,
	carregar_certificado_da_empresa,
)
from erpnext_brasil.integracao.consumo_indevido import garantir_liberado, registrar_resposta
from erpnext_brasil.integracao.emissao_nfe import AMBIENTE_POR_CHAVE
from erpnext_brasil.integracao.nfe_documento import emitente_da_empresa
from erpnext_brasil.integracao.serie_fiscal import numeros_fechados
from erpnext_brasil.integracao.transporte_sefaz import TransporteSefaz

__all__ = ["inutilizar_faixa"]


def _emissor(company: str) -> tuple[str, str]:
	"""`(CNPJ, UF)` do emitente — o mesmo cadastro que a NF-e usa."""
	emitente, endereco = emitente_da_empresa(company)

	return emitente.cnpj, endereco["UF"]


def _transporte(company: str, ambiente: str, cnpj: str, uf: str) -> TransporteSefaz:
	pfx, senha = carregar_certificado_da_empresa(company)

	return TransporteSefaz(
		pfx=pfx,
		senha=senha,
		uf=uf,
		cnpj_emitente=cnpj,
		ambiente=ambiente,
		guarda=garantir_liberado,
		registrador=partial(registrar_resposta, company=company),
	)


@frappe.whitelist()
def inutilizar_faixa(numeracao: str, numero_inicial: int, numero_final: int, justificativa: str) -> dict:
	"""Inutiliza `numero_inicial`–`numero_final` da série `numeracao` (`Numeracao Fiscal`).

	Devolve `{"situacao", "protocolo", "registro"}`. A justificativa (15 a 255 caracteres) é validada pelo domínio
	puro (`montar_inutilizacao`).
	"""
	serie = frappe.get_doc("Numeracao Fiscal", numeracao)
	serie.check_permission("write")

	inicio, fim = int(numero_inicial), int(numero_final)

	try:
		validar_faixa_a_inutilizar(
			inicio,
			fim,
			int(serie.ultimo_numero or 0),
			numeros_fechados(serie.company, serie.modelo, serie.serie, serie.name),
		)
	except InutilizacaoInvalida as erro:
		frappe.throw(str(erro))

	ambiente = ambiente_sefaz_da_empresa(serie.company)
	cnpj, uf = _emissor(serie.company)

	try:
		with _transporte(serie.company, ambiente, cnpj, uf) as transporte:
			resposta = transporte.inutilizar(
				ano=datetime.now().astimezone().strftime("%y"),
				cnpj=cnpj,
				modelo=serie.modelo,
				serie=serie.serie,
				numero_inicial=str(inicio),
				numero_final=str(fim),
				justificativa=justificativa,
			)
	except InutilizacaoInvalida as erro:
		frappe.throw(str(erro))

	situacao = SITUACAO_AUTORIZADO if resposta.homologada else SITUACAO_REJEITADO
	registro = frappe.get_doc(
		{
			"doctype": "Transmissao Fiscal",
			"documento_tipo": "Numeracao Fiscal",
			"documento": serie.name,
			"tipo": TIPO_INUTILIZACAO,
			"ambiente": AMBIENTE_POR_CHAVE[ambiente],
			"company": serie.company,
			"situacao": situacao,
			"codigo_status": resposta.codigo,
			"mensagem": resposta.mensagem,
			"protocolo": resposta.protocolo,
			"numero_inicial": inicio,
			"numero_final": fim,
			"justificativa": justificativa,
		}
	)
	registro.insert(ignore_permissions=True)

	if not resposta.homologada:
		frappe.db.commit()
		frappe.throw(
			_("A SEFAZ recusou a inutilização ({0}): {1}. Detalhes no registro {2}.").format(
				resposta.codigo, resposta.mensagem, registro.name
			)
		)

	return {"situacao": situacao, "protocolo": resposta.protocolo, "registro": registro.name}
