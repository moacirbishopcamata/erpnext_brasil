# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Converte a árvore de dicionários em XML.

Onde isto se encaixa
--------------------
Todo o app produz **dicionários** com os nomes oficiais das tags, para que o mesmo dado
sirva a qualquer transporte — INI do ACBrLib, JSON da ACBr API, XML da assinatura local.
Este módulo é a ponta que fecha o caminho do XML.

Regras da conversão
-------------------
- chave iniciada por ``@`` vira **atributo**; as demais viram elemento;
- ``@xmlns`` vira a declaração de namespace do elemento;
- lista vira **elementos irmãos repetidos** com o mesmo nome (é assim que `det` e
  `Transform` aparecem no layout);
- valor ``None`` é **omitido** — tag vazia é rejeição, não omissão;
- a **ordem de inserção** do dicionário é preservada, e isso não é detalhe: canonicalização
  e assinatura dependem dela, e o XSD da NF-e usa `xs:sequence`, que é ordenado.

Sem dependências: usa só a biblioteca padrão, e por isso é testável em qualquer ambiente.
Para ler ou canonicalizar XML, use `lxml` na camada de integração — aqui só se escreve.
"""

from xml.sax.saxutils import escape

__all__ = ["ErroSerializacao", "para_xml"]

# Escapes de valor de atributo exigidos pela canonicalização C14N. `quoteattr` da
# biblioteca padrão resolveria as aspas trocando o delimitador para apóstrofo, o que é XML
# válido mas **não** é a forma canônica — e este XML vai ser assinado. Sair já no formato
# canônico evita depender da normalização acontecer depois.
_ESCAPES_ATRIBUTO = {
	"&": "&amp;",
	"<": "&lt;",
	'"': "&quot;",
	"\t": "&#x9;",
	"\n": "&#xA;",
	"\r": "&#xD;",
}


def _atributo(valor) -> str:
	"""Escapa o valor e o delimita com aspas duplas, como a forma canônica exige."""
	texto = str(valor)

	for caractere, substituto in _ESCAPES_ATRIBUTO.items():
		texto = texto.replace(caractere, substituto)

	return f'"{texto}"'


class ErroSerializacao(ValueError):
	"""Estrutura que não pode ser convertida em XML."""


def _texto(valor) -> str:
	"""Converte o valor em texto, escapando o que o XML exige.

	`Decimal` e `int` viram texto pela representação natural — nunca por `float`, que
	introduziria notação científica e casas espúrias num campo monetário.
	"""
	if isinstance(valor, bool):
		# Precede o teste de int: em Python, bool é int, e `True` viraria "1" sem aviso.
		raise ErroSerializacao(
			"Booleano não tem representação definida no layout: converta para o código "
			"esperado ('0'/'1' ou 'S'/'N') antes de serializar"
		)

	if isinstance(valor, float):
		raise ErroSerializacao(
			"float não deve ser serializado em documento fiscal: use Decimal ou o texto "
			"já formatado, porque float traz erro de arredondamento e notação científica"
		)

	return escape(str(valor))


def _abertura(nome: str, atributos: dict) -> str:
	if not atributos:
		return f"<{nome}>"

	partes = " ".join(f"{chave}={_atributo(valor)}" for chave, valor in atributos.items())

	return f"<{nome} {partes}>"


def _elemento(nome: str, conteudo) -> str:
	if conteudo is None:
		return ""

	if isinstance(conteudo, list):
		# Lista vira irmãos repetidos, não um elemento contendo os itens.
		return "".join(_elemento(nome, item) for item in conteudo)

	if not isinstance(conteudo, dict):
		return f"<{nome}>{_texto(conteudo)}</{nome}>"

	atributos = {}
	filhos = []

	for chave, valor in conteudo.items():
		if chave.startswith("@"):
			if valor is None:
				continue

			atributos["xmlns" if chave == "@xmlns" else chave[1:]] = valor
		else:
			filhos.append(_elemento(chave, valor))

	interno = "".join(filhos)

	if not interno and not atributos:
		# Elemento sem conteúdo nem atributo não deveria existir no documento.
		return ""

	return f"{_abertura(nome, atributos)}{interno}</{nome}>"


def para_xml(arvore: dict, namespace: str | None = None, declaracao: bool = False) -> str:
	"""Serializa a árvore. Exige um único elemento raiz, como todo XML.

	`namespace` é acrescentado à raiz quando ela ainda não declarar um — conveniência para
	quem monta a árvore sem se preocupar com isso.
	"""
	if not isinstance(arvore, dict):
		raise ErroSerializacao("A raiz precisa ser um dicionário")

	nomes = [chave for chave in arvore if not chave.startswith("@")]

	if len(nomes) != 1:
		raise ErroSerializacao(
			f"O XML precisa de exatamente um elemento raiz, encontrados {len(nomes)}: "
			f"{nomes}"
		)

	nome = nomes[0]
	conteudo = arvore[nome]

	if namespace and isinstance(conteudo, dict) and "@xmlns" not in conteudo:
		conteudo = {"@xmlns": namespace, **conteudo}

	corpo = _elemento(nome, conteudo)

	if not corpo:
		raise ErroSerializacao(f"O elemento raiz {nome!r} ficou vazio")

	prefixo = '<?xml version="1.0" encoding="UTF-8"?>' if declaracao else ""

	return prefixo + corpo
