# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Converte a árvore de dicionários do formato orientado a XML para JSON.

O problema
----------
Todo o app constrói a árvore do documento com a convenção de `serializacao.py`: chave
iniciada por `@` é **atributo** (`@Id`, `@versao`, `@xCampo`). Isso existe porque XML
distingue atributo de elemento filho, e a árvore precisa carregar essa distinção para
`para_xml` produzir o documento certo.

JSON não tem essa distinção. Confirmado no exemplo oficial da especificação da ACBr API
(`NfePedidoEmissao`): o mesmo dado que em XML é o atributo `xCampo` de `obsCont`
aparece no JSON como `{"xCampo": "...", "xTexto": "..."}` — chave comum, sem prefixo.
Enviar a árvore com `@xCampo` para uma API JSON produziria um campo que ela não
reconhece.

Este módulo faz essa tradução: acompanha a mesma árvore, mas descarta o prefixo `@` de
cada chave, sem reordenar nem reinterpretar valor.

O que **não** está confirmado
------------------------------
A especificação confirma o tratamento de atributos "de negócio" como `xCampo`. Não
confirma explicitamente o que a API espera para os atributos de infraestrutura do XML —
`@versao` e `@Id` de `infNFe`, `@xmlns` da raiz. É plausível que a API os ignore (ela
provavelmente gera a chave de acesso e o `Id` do lado dela, já que a assinatura também
é responsabilidade dela nesse caminho). `remover_atributos_infraestrutura=True` (padrão)
descarta esses três antes de enviar; desligar a opção preserva-os como chave comum,
para o caso de precisarem ser confirmados como campo aceito pela API.

Funções puras: nenhuma dependência do Frappe.
"""

__all__ = ["ATRIBUTOS_DE_INFRAESTRUTURA", "para_json"]

# Atributos que existem apenas para servir a serialização XML — não são dado de negócio,
# e o tratamento deles pela ACBr API não está confirmado na especificação.
ATRIBUTOS_DE_INFRAESTRUTURA = ("@versao", "@Id", "@xmlns", "@nItem")


def _chave_json(chave: str) -> str:
	return chave[1:] if chave.startswith("@") else chave


def para_json(arvore, remover_atributos_infraestrutura: bool = True):
	"""Converte recursivamente, descartando o prefixo `@` das chaves de atributo.

	Listas são percorridas item a item; valores que não são dict/list retornam como
	vieram — a tradução é só de forma de chave, nunca de conteúdo.
	"""
	if isinstance(arvore, dict):
		resultado = {}

		for chave, valor in arvore.items():
			if remover_atributos_infraestrutura and chave in ATRIBUTOS_DE_INFRAESTRUTURA:
				continue

			resultado[_chave_json(chave)] = para_json(valor, remover_atributos_infraestrutura)

		return resultado

	if isinstance(arvore, list):
		return [para_json(item, remover_atributos_infraestrutura) for item in arvore]

	return arvore
