# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Natureza da operação — o campo `natOp` da NF-e e do CT-e.

O que o leiaute exige, lido do XSD oficial
--------------------------------------------------
`leiauteNFe_v4.00.xsd`, elemento `natOp`, lido localmente:

```xml
<xs:element name="natOp">
  <xs:documentation>Descrição da Natureza da Operação</xs:documentation>
  <xs:restriction base="TString">
    <xs:minLength value="1"/>
    <xs:maxLength value="60"/>
```

**Sessenta caracteres.** O projeto validava só contra vazio — uma natureza mais longa
passava na montagem e voltava rejeitada pela SEFAZ, depois de assinar e transmitir. É o
tipo de erro que só aparece no pior momento, e o projeto já tinha precedente de validar
tamanho (`JUSTIFICATIVA_CONTINGENCIA_MAXIMA`).

Por que as descrições padrão são **do projeto**, não "oficiais"
----------------------------------------------------------------------
`natOp` é **texto livre** no leiaute: o XSD pede uma descrição, não um código de tabela.
Não existe obrigação de reproduzir a redação oficial do CFOP.

Isso importa porque a fonte oficial não está disponível com confiança. A página do CONFAZ
cujo endereço termina em `cfop_cvsn_70_vigente` foi baixada e lida localmente durante a
varredura de gaps de 2026-09-04, e **todas as redações nela expiram em 31.05.22** —
existem o Ajuste SINIEF 03/22 e o 03/24 depois disso, espalhados por outras URLs.

Diante disso havia duas saídas ruins e uma boa:

- copiar a redação expirada e chamá-la de oficial (falso);
- não oferecer sugestão nenhuma (deixa o usuário digitando à mão o que o sistema já sabe);
- **oferecer uma descrição própria, curta e correta, declarada como padrão do projeto.**

`NATUREZAS_PADRAO` é a terceira. São frases descritivas que dizem o que a operação é,
dentro dos 60 caracteres, para os mesmos CFOPs que `fiscal/cfop.py` determina. Quem
precisar da redação oficial do seu estado troca o texto — é campo livre, e a sugestão
nunca sobrescreve o que o usuário gravou.

Relação com `fiscal/cfop.py`
------------------------------------
As chaves são exatamente os 20 códigos que `cfop.py` sabe determinar. Não é coincidência
nem cópia: há teste que falha se um módulo passar a cobrir um código que o outro não
cobre. Os dois respondem à mesma pergunta — "que operação é esta?" — em formatos
diferentes, e divergir seria dizer duas coisas sobre o mesmo documento.

Funções puras: nenhuma dependência do Frappe.
"""

__all__ = [
	"NATUREZAS_PADRAO",
	"TAMANHO_MAXIMO",
	"TAMANHO_MINIMO",
	"NaturezaInvalida",
	"natureza_do_cfop",
	"validar_natureza",
]

TAMANHO_MINIMO = 1
TAMANHO_MAXIMO = 60
"""`minLength`/`maxLength` do elemento `natOp` no `leiauteNFe_v4.00.xsd` oficial."""

NATUREZAS_PADRAO = {
	# Compra — entrada
	"1101": "Compra para industrializacao ou producao rural",
	"2101": "Compra para industrializacao ou producao rural",
	"1102": "Compra para comercializacao",
	"2102": "Compra para comercializacao",
	# Venda — saída
	"5101": "Venda de producao do estabelecimento",
	"6101": "Venda de producao do estabelecimento",
	"5102": "Venda de mercadoria adquirida de terceiros",
	"6102": "Venda de mercadoria adquirida de terceiros",
	# Devolução de venda — entrada
	"1201": "Devolucao de venda de producao do estabelecimento",
	"2201": "Devolucao de venda de producao do estabelecimento",
	"1202": "Devolucao de venda de mercadoria de terceiros",
	"2202": "Devolucao de venda de mercadoria de terceiros",
	# Devolução de compra — saída
	"5201": "Devolucao de compra para industrializacao",
	"6201": "Devolucao de compra para industrializacao",
	"5202": "Devolucao de compra para comercializacao",
	"6202": "Devolucao de compra para comercializacao",
	# Industrialização por encomenda
	"5901": "Remessa para industrializacao por encomenda",
	"6901": "Remessa para industrializacao por encomenda",
	"1901": "Entrada para industrializacao por encomenda",
	"2901": "Entrada para industrializacao por encomenda",
	"1902": "Retorno de mercadoria remetida para industrializacao",
	"2902": "Retorno de mercadoria remetida para industrializacao",
	"5902": "Retorno de mercadoria utilizada na industrializacao",
	"6902": "Retorno de mercadoria utilizada na industrializacao",
}
"""Descrição padrão **deste projeto** por CFOP — não a redação oficial do CONFAZ.

Sem acento de propósito: `natOp` atravessa serialização, assinatura e transmissão, e há
histórico de rejeição por caractere fora do repertório em campo livre. Texto ASCII curto
é a escolha conservadora; quem quiser acentuação troca o texto, que é campo livre.
"""


class NaturezaInvalida(ValueError):
	"""Descrição que o leiaute não aceita."""


def validar_natureza(texto: str) -> str:
	"""Normaliza e confere a natureza contra as restrições do XSD.

	Colapsa espaço em branco antes de medir: uma descrição com quebra de linha ou espaço
	duplo mede diferente do que aparenta, e o limite de 60 é medido pela SEFAZ no texto
	que ela recebe, não no que o usuário digitou.
	"""
	limpo = " ".join((texto or "").split())

	if len(limpo) < TAMANHO_MINIMO:
		raise NaturezaInvalida("A natureza da operação é obrigatória e não pode ser vazia")

	if len(limpo) > TAMANHO_MAXIMO:
		raise NaturezaInvalida(
			f"A natureza da operação tem no máximo {TAMANHO_MAXIMO} caracteres "
			f"(leiauteNFe_v4.00.xsd), recebidos {len(limpo)}: {limpo!r}"
		)

	return limpo


def natureza_do_cfop(cfop: str) -> str:
	"""A descrição padrão do projeto para um CFOP, ou `""` quando não há.

	Devolve string vazia em vez de levantar erro, e é deliberado: não ter sugestão é
	normal — a tabela de CFOP tem centenas de códigos e este módulo cobre os vinte que
	`fiscal/cfop.py` determina. Quem chama trata a ausência preenchendo à mão, não como
	falha.
	"""
	return NATUREZAS_PADRAO.get((cfop or "").strip(), "")
