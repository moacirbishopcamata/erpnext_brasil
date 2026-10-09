# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""O que aconteceu com cada número de uma série fiscal — lido de `Transmissao Fiscal`.

Dois consumidores: o relatório `Lacunas de Numeracao` e a ação de inutilizar faixa. Ficam aqui, juntos, para que
os dois enxerguem os mesmos números fechados — se divergissem, o relatório apontaria como candidato um número que
a ação recusaria (ou o contrário).

O número vem da **chave de acesso**: a transmissão não tem campo próprio para ele.
"""

import frappe

from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave
from erpnext_brasil.fiscal.relatorio_numeracao import DESFECHOS_QUE_FECHAM

__all__ = ["faixas_inutilizadas", "numeros_fechados", "situacoes_por_numero"]


def situacoes_por_numero(company: str, modelo: str, serie: str) -> dict[int, set[str]]:
	"""`{número: {situações}}` das autorizações da série. Chave ilegível não entra: o `DocType` já valida a chave."""
	registros = frappe.get_all(
		"Transmissao Fiscal",
		filters={"company": company, "tipo": "Autorização", "chave_acesso": ["is", "set"]},
		fields=["chave_acesso", "situacao"],
		limit_page_length=0,
	)
	resultado: dict[int, set[str]] = {}

	for registro in registros:
		try:
			chave = ler_chave(registro.chave_acesso)
		except ValueError:
			continue

		if chave.modelo == modelo and int(chave.serie) == int(serie):
			resultado.setdefault(int(chave.numero), set()).add(registro.situacao)

	return resultado


def faixas_inutilizadas(numeracao: str) -> tuple[tuple[int, int], ...]:
	"""Faixas que a SEFAZ aceitou inutilizar nesta série (`Numeracao Fiscal`)."""
	registros = frappe.get_all(
		"Transmissao Fiscal",
		filters={
			"documento_tipo": "Numeracao Fiscal",
			"documento": numeracao,
			"tipo": "Inutilização",
			"situacao": "Autorizado",
		},
		fields=["numero_inicial", "numero_final"],
		limit_page_length=0,
	)

	return tuple((r.numero_inicial, r.numero_final) for r in registros)


def numeros_fechados(company: str, modelo: str, serie: str, numeracao: str) -> set[int]:
	"""Números que já têm desfecho (autorizado, denegado, cancelado) ou já foram inutilizados."""
	fechados = {
		numero
		for numero, situacoes in situacoes_por_numero(company, modelo, serie).items()
		if situacoes & DESFECHOS_QUE_FECHAM
	}

	for inicio, fim in faixas_inutilizadas(numeracao):
		fechados.update(range(inicio, fim + 1))

	return fechados
