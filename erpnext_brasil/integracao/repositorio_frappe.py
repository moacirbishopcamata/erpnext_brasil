# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Implementação Frappe da porta de leitura das tabelas de classificação.

Responsabilidade única: **buscar** os códigos. Não valida, não decide — quem faz isso é
`fiscal/codigos/compatibilidade.py`, que depende só da interface e não sabe que este
módulo existe.

Resiliência: tudo aqui degrada. Code List ausente devolve vazio, metadado ilegível vira
dicionário vazio. A validação a jusante trata vazio como "não posso afirmar invalidez" —
nunca como "está errado". Travar o usuário por causa de uma tabela que ele ainda não
importou seria pior que não validar.
"""

import json

import frappe

from erpnext_brasil.fiscal.codigos.classificacao import (
	CLASSIFICACAO_TRIBUTARIA,
	CST_IBS_CBS,
	ClassificacaoTributaria,
	CstIbsCbs,
)

__all__ = ["RepositorioFrappe", "repositorio_da_requisicao"]

_CACHE = "_erpnext_brasil_repositorio"


class RepositorioFrappe:
	"""Lê CST e cClassTrib dos Code List importados.

	Carrega sob demanda e uma vez só por instância: a validação roda por item, e reler o
	Code List inteiro a cada linha de uma nota com cem itens seriam cem consultas para o
	mesmo dado.
	"""

	def __init__(self):
		self._cst: dict[str, CstIbsCbs] | None = None
		self._classificacoes: dict[str, ClassificacaoTributaria] | None = None

	def cst(self) -> dict[str, CstIbsCbs]:
		if self._cst is None:
			self._cst = {
				codigo: CstIbsCbs(
					codigo=codigo,
					descricao=titulo,
					indicadores=extra.get("indicadores", {}),
				)
				for codigo, titulo, extra in self._linhas(CST_IBS_CBS)
			}

		return self._cst

	def classificacoes(self) -> dict[str, ClassificacaoTributaria]:
		if self._classificacoes is None:
			self._classificacoes = {
				codigo: ClassificacaoTributaria(
					codigo=codigo,
					cst=extra.get("cst", ""),
					nome=titulo,
					descricao="",
					tipo_aliquota=extra.get("tipo_aliquota", ""),
					reducao_ibs=extra.get("pRedIBS", "0"),
					reducao_cbs=extra.get("pRedCBS", "0"),
					documentos=extra.get("documentos", {}),
				)
				for codigo, titulo, extra in self._linhas(CLASSIFICACAO_TRIBUTARIA)
			}

		return self._classificacoes

	def _linhas(self, code_list: str):
		if not frappe.db.exists("Code List", code_list):
			# Tabela ainda não importada: estado normal de instalação nova.
			return

		for linha in frappe.get_all(
			"Common Code",
			filters={"code_list": code_list},
			fields=["common_code", "title", "additional_data"],
		):
			yield linha.common_code, linha.title or "", self._extra(linha.additional_data)

	@staticmethod
	def _extra(bruto) -> dict:
		"""Metadado ilegível não derruba o salvamento.

		Sem ele a validação apenas deixa de conferir a amarração ao CST e a
		aplicabilidade por documento — degradação, não erro. O código em si continua
		sendo verificado.
		"""
		if not bruto:
			return {}

		try:
			dados = json.loads(bruto)
		except (ValueError, TypeError):
			return {}

		return dados if isinstance(dados, dict) else {}


def repositorio_da_requisicao() -> RepositorioFrappe:
	"""Uma instância por requisição, para que o cache interno valha entre os itens."""
	repositorio = getattr(frappe.local, _CACHE, None)

	if repositorio is None:
		repositorio = RepositorioFrappe()
		setattr(frappe.local, _CACHE, repositorio)

	return repositorio
