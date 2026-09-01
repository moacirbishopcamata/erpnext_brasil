# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Chave de acesso da NF-e: montagem, dígito verificador e leitura.

A mudança que quebra implementações antigas
-------------------------------------------
A chave **deixou de ser 44 dígitos**. O XSD oficial (`tiposBasico_v4.00.xsd`, tipo
`TChNFe`) define o padrão como::

    [0-9]{6}[0-9A-Z]{12}[0-9]{26}

Isto é: 6 dígitos, depois **12 posições alfanuméricas**, depois 26 dígitos. O CNPJ
alfanumérico propaga para dentro da chave, e qualquer validação escrita como `^\\d{44}$`
passa a rejeitar chave legítima. Só as 12 posições da raiz/ordem do CNPJ aceitam letras;
os dois dígitos verificadores do CNPJ, dentro da chave, continuam numéricos — daí o
recorte 6 / 12 / 26.

Layout das 44 posições
----------------------
========  ========  ====  ==============================================
Campo     Posições  Tam.  Conteúdo
========  ========  ====  ==============================================
cUF          1–2      2   Código da UF (IBGE)
AAMM         3–6      4   Ano e mês da emissão
CNPJ        7–20     14   CNPJ do emitente (12 alfanuméricas + 2 dígitos)
mod        21–22      2   Modelo: 55 (NF-e) ou 65 (NFC-e)
serie      23–25      3   Série
nNF        26–34      9   Número da nota
tpEmis        35      1   Forma de emissão
cNF        36–43      8   Código numérico aleatório
cDV           44      1   Dígito verificador
========  ========  ====  ==============================================

O dígito verificador é módulo 11 sobre as 43 primeiras posições, com pesos 2 a 9
ciclando da direita para a esquerda, e a mesma conversão do CNPJ alfanumérico:
``valor = ord(c) - 48``. É retrocompatível — chave puramente numérica bate pelo caminho
de sempre.

Funções puras: nenhuma dependência do Frappe.
"""

import re
from dataclasses import dataclass

from erpnext_brasil.fiscal.validators import limpar

__all__ = [
	"MODELOS",
	"ChaveAcesso",
	"ChaveInvalida",
	"calcular_dv",
	"formatar",
	"ler_chave",
	"montar_chave",
	"validar_chave",
]

# Padrão do tipo TChNFe, lido do XSD oficial.
_PADRAO = re.compile(r"^[0-9]{6}[0-9A-Z]{12}[0-9]{26}$")

MODELOS = {"55": "NF-e", "65": "NFC-e", "57": "CT-e", "58": "MDF-e"}
"""Nomes exibidos por `ChaveAcesso.documento`. "57"/"58" confirmados em `ide/mod` do CT-e e
do MDF-e (`docs/cte-estado.md`/`docs/mdfe-estado.md`) — o layout de 44 posições da chave é o
mesmo entre os quatro documentos, só o dígito de modelo muda."""

_TAMANHO = 44
_SEM_DV = 43


class ChaveInvalida(ValueError):
	"""Chave de acesso que não satisfaz o layout ou o dígito verificador."""

	def __init__(self, mensagem: str, valor: str | None = None):
		super().__init__(mensagem)
		self.valor = valor


def _valor_do_caractere(c: str) -> int:
	"""Mesma conversão do CNPJ alfanumérico: dígitos valem 0-9, letras 17-42."""
	return ord(c) - 48


def calcular_dv(base: str) -> str:
	"""Dígito verificador das 43 primeiras posições (módulo 11, pesos 2 a 9).

	Pré-condição verificada: a base precisa ter exatamente 43 caracteres. Calcular sobre
	comprimento errado devolveria um dígito plausível e errado, que só apareceria na
	rejeição da SEFAZ.
	"""
	base = (base or "").strip().upper()

	if len(base) != _SEM_DV:
		raise ChaveInvalida(
			f"O dígito verificador é calculado sobre {_SEM_DV} posições, recebidas {len(base)}",
			base,
		)

	soma = 0

	# Pesos ciclam de 2 a 9, da direita para a esquerda.
	for posicao, caractere in enumerate(reversed(base)):
		soma += _valor_do_caractere(caractere) * (posicao % 8 + 2)

	resto = soma % 11

	return "0" if resto < 2 else str(11 - resto)


def montar_chave(
	uf: str,
	ano_mes: str,
	cnpj: str,
	modelo: str,
	serie: str,
	numero: str,
	tipo_emissao: str,
	codigo_numerico: str,
) -> str:
	"""Monta a chave completa, com o dígito verificador calculado.

	Cada campo é normalizado para o tamanho do layout — zeros à esquerda são a causa
	mais comum de chave inválida, porque planilha e banco os removem.
	"""
	campos = (
		(uf, 2, "UF"),
		(ano_mes, 4, "ano/mês"),
		(limpar(cnpj), 14, "CNPJ"),
		(modelo, 2, "modelo"),
		(serie, 3, "série"),
		(numero, 9, "número"),
		(tipo_emissao, 1, "tipo de emissão"),
		(codigo_numerico, 8, "código numérico"),
	)

	partes = []

	for valor, tamanho, nome in campos:
		texto = str(valor or "").strip().upper()

		if len(texto) > tamanho:
			raise ChaveInvalida(
				f"O campo {nome} tem {len(texto)} caracteres e o layout admite {tamanho}", texto
			)

		partes.append(texto.rjust(tamanho, "0"))

	base = "".join(partes)

	return base + calcular_dv(base)


def validar_chave(chave: str) -> str:
	"""Valida layout e dígito verificador; devolve a chave limpa.

	Aceita a chave com ou sem separadores, porque é assim que ela circula — colada de
	um DANFE, de um e-mail ou de uma planilha.
	"""
	limpa = limpar(chave)

	if not limpa:
		raise ChaveInvalida("Chave de acesso não informada", chave)

	if len(limpa) != _TAMANHO:
		raise ChaveInvalida(
			f"A chave de acesso tem {_TAMANHO} caracteres, recebidos {len(limpa)}", chave
		)

	if not _PADRAO.match(limpa):
		raise ChaveInvalida(
			"A chave de acesso só admite letras nas 12 posições da raiz do CNPJ "
			"(posições 7 a 18); o restante é numérico",
			chave,
		)

	esperado = calcular_dv(limpa[:_SEM_DV])

	if limpa[-1] != esperado:
		raise ChaveInvalida(
			f"Dígito verificador da chave não confere: esperado {esperado}, recebido {limpa[-1]}",
			chave,
		)

	return limpa


@dataclass(frozen=True)
class ChaveAcesso:
	"""A chave decomposta nos campos que a formam."""

	uf: str
	ano_mes: str
	cnpj: str
	modelo: str
	serie: str
	numero: str
	tipo_emissao: str
	codigo_numerico: str
	dv: str

	@property
	def valor(self) -> str:
		return (
			f"{self.uf}{self.ano_mes}{self.cnpj}{self.modelo}{self.serie}"
			f"{self.numero}{self.tipo_emissao}{self.codigo_numerico}{self.dv}"
		)

	@property
	def documento(self) -> str:
		"""Nome do modelo — NF-e ou NFC-e — ou o código quando desconhecido."""
		return MODELOS.get(self.modelo, self.modelo)

	@property
	def cnpj_alfanumerico(self) -> bool:
		return not self.cnpj.isdigit()


def ler_chave(chave: str) -> ChaveAcesso:
	"""Valida e decompõe a chave nos campos do layout."""
	limpa = validar_chave(chave)

	return ChaveAcesso(
		uf=limpa[0:2],
		ano_mes=limpa[2:6],
		cnpj=limpa[6:20],
		modelo=limpa[20:22],
		serie=limpa[22:25],
		numero=limpa[25:34],
		tipo_emissao=limpa[34:35],
		codigo_numerico=limpa[35:43],
		dv=limpa[43:44],
	)


def formatar(chave: str, grupo: int = 4) -> str:
	"""Agrupa a chave para leitura humana, como aparece no DANFE."""
	limpa = limpar(chave)

	return " ".join(limpa[i : i + grupo] for i in range(0, len(limpa), grupo))
