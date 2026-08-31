# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Monta o evento eSocial assinado — a orquestração que `esocial_serializacao.py`
deixou de propósito para outro módulo.

A ordem, e por que não dá para assinar antes de serializar
------------------------------------------------------------------
Assinar exige bytes já existentes para canonicalizar e calcular o digest — não dá
para assinar a árvore de dicionário diretamente, só o XML que ela produz. A sequência
é sempre a mesma, para qualquer evento do eSocial:

1. Serializa a árvore **sem** `Signature` (`para_xml(arvore)`).
2. Assina esses bytes (`Assinador.assinar`), usando o `Id` do elemento do evento como
   referência.
3. Mescla o `Signature` resultante (`montar_signature`) como **irmão** do elemento do
   evento, dentro da mesma raiz `eSocial` — nunca dentro dele, a assinatura eSocial
   também é enveloped mas irmã do elemento assinado, não filha (mesma estrutura já
   confirmada para a NF-e em `fiscal/documento/assinatura.py`).
4. Serializa a árvore completa de novo — desta vez com a assinatura dentro.

Por que este módulo continua puro, apesar de "assinar"
------------------------------------------------------------------
`montar_evento_assinado` não importa `cryptography` nem `lxml`, nem sabe que
`AssinadorLocalEsocial` existe — recebe um `Assinador` (o `Protocol` de
`esocial_assinatura.py`) já pronto, por injeção de dependência. Isso permite testar a
orquestração inteira com um assinador falso (sem gerar certificado nenhum) e deixar
só `integracao/assinador_esocial.py` com a dependência de criptografia de verdade —
mesma separação de portas/adaptadores já usada para a NF-e
(`fiscal/documento/assinatura.Assinador` × `integracao/assinador_local.AssinadorLocal`).

Genérico, não específico do S-1200
------------------------------------------
Recebe a árvore já pronta (de `esocial_serializacao.montar_evt_remun` ou de qualquer
outro evento futuro) — não sabe nada sobre `evtRemun`/`ideEvento`/etc. Serve para
qualquer evento do eSocial cuja árvore siga o padrão `{"eSocial": {"@xmlns": ...,
"<elementoDoEvento>": {"@Id": ..., ...}}}`.

Funções puras: nenhuma dependência do Frappe, nenhuma biblioteca de criptografia
(o parâmetro `assinador` é a única porta de saída).
"""

from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.folha.esocial_assinatura import Assinador, AssinaturaInvalida, montar_signature

__all__ = ["montar_evento_assinado"]


def montar_evento_assinado(arvore: dict, id_evento: str, assinador: Assinador) -> str:
	"""Serializa `arvore`, assina e devolve o XML final já com `Signature`.

	`arvore` é o dicionário de `eSocial > <elementoDoEvento>` sem assinatura —
	produzido por algo como `esocial_serializacao.montar_evt_remun`. `id_evento` é o
	mesmo `Id` usado como atributo do elemento do evento dentro dessa árvore; se os
	dois não baterem, o `assinador` não encontra o elemento e levanta
	`AssinaturaInvalida` (comportamento de `AssinadorLocalEsocial`, não deste
	módulo — aqui só se propaga o erro).
	"""
	raiz_nome = _nome_da_raiz(arvore)
	conteudo_raiz = arvore[raiz_nome]

	xml_sem_assinatura = para_xml(arvore)
	material = assinador.assinar(xml_sem_assinatura.encode("utf-8"), id_evento)

	arvore_assinada = {raiz_nome: {**conteudo_raiz, **montar_signature(id_evento, material)}}

	return para_xml(arvore_assinada)


def _nome_da_raiz(arvore: dict) -> str:
	nomes = [chave for chave in arvore if not chave.startswith("@")]

	if len(nomes) != 1:
		raise AssinaturaInvalida(
			f"A árvore precisa de exatamente um elemento raiz, encontrados {len(nomes)}: {nomes}"
		)

	return nomes[0]
