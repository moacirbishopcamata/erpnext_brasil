# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Tradução entre documentos de transporte do ERPNext e `infDoc` do MDF-e/CT-e.

A costura, e por que ela ainda para antes de tocar o Frappe de verdade
------------------------------------------------------------------------------
Mesmo papel de `integracao/mapeamento.py` para a apuração fiscal: um lado é dado já
extraído do ERPNext (dicionários simples), o outro é a árvore de dataclasses que
`fiscal/mdfe.py` exige (`MunicipioDescarga`). Esta é a costura — testável sem bench.

Achado real que limitou o escopo deste incremento: o ERPNext ainda **não tem** nenhum
campo que guarde a chave de acesso da NF-e emitida. A camada de transmissão de NF-e
(`integracao/transporte_sefaz.py`/`autorizacao_sefaz.py`) já existe e devolve o
resultado da autorização, mas não está ligada a nenhum `doc_event` que persista a
chave — confirmado por grep em `hooks.py`, não suposto. Sem esse campo, uma função que
lesse "a chave de acesso do Delivery Note" estaria lendo algo que não existe ainda.

Por isso este módulo modela só a **tradução genérica**: recebe uma lista de referências
já resolvidas (chave + dados do município de descarga), agrupa por município — o
formato que `fiscal.mdfe.MunicipioDescarga`/`montar_infdoc` exigem (`docs/mdfe-infdoc.md`:
"o infDoc do MDF-e organiza as referências por município de descarregamento, não é
lista plana"). Extrair essas referências de doctypes reais do ERPNext (`Shipment` →
`Shipment Delivery Note` → `Delivery Note` → a chave, quando o campo existir) é a
próxima peça, deliberadamente não implementada aqui.

Nada aqui importa `frappe`.
"""

from erpnext_brasil.fiscal.mdfe import MunicipioDescarga

__all__ = ["ReferenciaDocumentoFiscal", "agrupar_por_municipio_descarga"]


class ReferenciaDocumentoFiscal(dict):
	"""Um dicionário com o formato esperado: `chave` (str), `municipio_codigo` (str),
	`municipio_nome` (str), e `modelo` (`"55"` para NF-e ou `"57"` para CT-e — decide
	se a chave entra em `chaves_nfe` ou `chaves_cte` do `MunicipioDescarga`).

	Subclasse de `dict` só para nomear o formato — não adiciona validação; quem monta
	a chave de acesso (`fiscal.documento.chave_acesso.ler_chave`) já valida o
	formato/dígito verificador antes de `montar_infdoc` aceitar a referência."""


def agrupar_por_municipio_descarga(
	referencias: list[ReferenciaDocumentoFiscal],
) -> list[MunicipioDescarga]:
	"""Agrupa referências de documentos fiscais por município de descarga, na ordem
	de primeira aparição — não ordena por código, preserva a ordem em que os
	documentos chegaram (mesma disciplina de `montar_infdoc` preservar a ordem dos
	municípios que recebe, testada em `test_varios_municipios_preserva_ordem`).
	"""
	municipios: dict[tuple[str, str], dict[str, list[str]]] = {}
	ordem: list[tuple[str, str]] = []

	for referencia in referencias:
		chave_municipio = (referencia["municipio_codigo"], referencia["municipio_nome"])

		if chave_municipio not in municipios:
			municipios[chave_municipio] = {"chaves_cte": [], "chaves_nfe": []}
			ordem.append(chave_municipio)

		if referencia["modelo"] == "57":
			municipios[chave_municipio]["chaves_cte"].append(referencia["chave"])
		else:
			municipios[chave_municipio]["chaves_nfe"].append(referencia["chave"])

	return [
		MunicipioDescarga(
			codigo=codigo,
			nome=nome,
			chaves_cte=municipios[(codigo, nome)]["chaves_cte"],
			chaves_nfe=municipios[(codigo, nome)]["chaves_nfe"],
		)
		for codigo, nome in ordem
	]
