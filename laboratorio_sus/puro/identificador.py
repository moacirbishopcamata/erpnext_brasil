# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Identificador do tubo: número opaco com dígito de conferência (Verhoeff).

O número não carrega paciente nem data: só ordem de emissão. O dígito de conferência pega leitura errada de
um dígito e a troca de dois dígitos vizinhos (propriedade do algoritmo de Verhoeff, verificada em teste).
**É escolha de projeto, não exigência de norma.** O contador que emite os números é transacional e nunca
devolve um número já emitido: isso é do repositório; a regra aqui só formata e confere.
"""

__all__ = ["IdentificadorInvalido", "conferir", "formatar", "numero_de"]

_D = (
	(0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
	(1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
	(2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
	(3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
	(4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
	(5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
	(6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
	(7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
	(8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
	(9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_P = (
	(0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
	(1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
	(5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
	(8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
	(9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
	(4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
	(2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
	(7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)
_INV = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)


class IdentificadorInvalido(ValueError):
	"""Texto que não é um identificador de tubo: tamanho errado, não numérico ou dígito de conferência errado."""


def _soma(digitos: str) -> int:
	c = 0

	for i, d in enumerate(reversed(digitos)):
		c = _D[c][_P[i % 8][int(d)]]

	return c


def _dv(numero: str) -> str:
	return str(_INV[_soma(numero + "0")])


def formatar(sequencia: int, largura: int = 9) -> str:
	"""Identificador da `sequencia` com `largura` dígitos de número mais o dígito de conferência."""
	if sequencia < 1:
		raise ValueError("a sequência do identificador começa em 1")

	numero = str(sequencia).zfill(largura)

	if len(numero) > largura:
		raise ValueError(f"a sequência {sequencia} não cabe em {largura} dígitos")

	return numero + _dv(numero)


def conferir(texto: str, largura: int = 9) -> str:
	"""Devolve o identificador normalizado, ou levanta `IdentificadorInvalido`. Nunca aproxima."""
	texto = texto.strip()

	if len(texto) != largura + 1 or not texto.isascii() or not texto.isdigit():
		raise IdentificadorInvalido(f"identificador deve ter {largura + 1} dígitos numéricos")

	if _soma(texto) != 0:
		raise IdentificadorInvalido("dígito de conferência não confere")

	return texto


def numero_de(identificador: str, largura: int = 9) -> int:
	"""A sequência embutida no identificador (sem o dígito de conferência), depois de conferi-lo."""
	return int(conferir(identificador, largura)[:-1])
