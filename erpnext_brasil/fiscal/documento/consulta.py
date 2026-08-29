# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Requisições de consulta: situação de uma NF-e e recibo de lote assíncrono.

Estruturas pequenas e sem ambiguidade de ordem — ao contrário do envelope de evento
(cancelamento), que tem campos demais para arriscar sem o XSD à vista, estas duas têm só
dois ou três filhos e foram confirmadas em exemplo literal de fonte técnica.

Funções puras: nenhuma dependência do Frappe.
"""

from erpnext_brasil.fiscal.documento.chave_acesso import validar_chave
from erpnext_brasil.fiscal.documento.nfe import NAMESPACE_NFE

__all__ = ["montar_cons_reci_nfe", "montar_cons_sit_nfe"]


def montar_cons_sit_nfe(chave_acesso: str, ambiente: str = "2") -> dict:
	"""`consSitNFe` — consulta a situação de uma NF-e já transmitida, por chave.

	`xServ` é sempre o literal `"CONSULTAR"`: é o único valor válido para este serviço,
	não um parâmetro de negócio.
	"""
	chave = validar_chave(chave_acesso)

	return {
		"consSitNFe": {
			"@xmlns": NAMESPACE_NFE,
			"@versao": "4.00",
			"tpAmb": ambiente,
			"xServ": "CONSULTAR",
			"chNFe": chave,
		}
	}


def montar_cons_reci_nfe(numero_recibo: str, ambiente: str = "2") -> dict:
	"""`consReciNFe` — consulta o resultado de um lote que respondeu `103` (pendente),
	usando o número de recibo devolvido naquela primeira resposta."""
	recibo = (numero_recibo or "").strip()

	if not recibo:
		raise ValueError("Número de recibo é obrigatório para consultar o lote")

	return {"consReciNFe": {"@xmlns": NAMESPACE_NFE, "@versao": "4.00", "tpAmb": ambiente, "nRec": recibo}}
