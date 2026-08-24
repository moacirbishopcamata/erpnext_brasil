# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Validação de Inscrição Estadual por unidade federativa.

Não existe "o" algoritmo de IE: cada UF define o seu, e as diferenças não são
cosméticas — variam o comprimento, o prefixo obrigatório, os pesos, o módulo
(10, 11 ou 9) e o tratamento do resto. Este módulo implementa as 27 regras sobre
um pequeno motor comum, isolando em funções próprias apenas as UFs genuinamente
irregulares (SP, MG, BA, PE, AP, GO, RO, TO).

Como em `validators`, aqui não se importa `frappe`: são funções puras.

Viés deliberado a favor do falso positivo
-----------------------------------------
Uma IE **inválida aceita** é detectada depois, pela SEFAZ, na emissão. Uma IE
**válida rejeitada** trava o cadastro de um cliente real e não tem contorno
dentro do sistema. Os custos são assimétricos, então:

- UF desconhecida ou fora das 27 -> aceita (não há regra a aplicar);
- o valor "ISENTO" -> aceito, é o que a legislação manda informar para não
  contribuinte inscrito como isento.

O que este módulo garante é a consistência aritmética do dígito verificador,
não a existência do cadastro — só a SEFAZ responde por isso.
"""

from collections.abc import Callable

from erpnext_brasil.fiscal.validators import ValidacaoFiscalError, limpar

__all__ = ["UFS_SUPORTADAS", "validar_inscricao_estadual"]

ISENTO = "ISENTO"


# --------------------------------------------------------------------------------------
# Motor comum
# --------------------------------------------------------------------------------------


def _soma(digitos: str, pesos: tuple[int, ...]) -> int:
	"""Soma ponderada. Exige que pesos e dígitos tenham o mesmo tamanho.

	O `strict=True` é proposital: um desalinhamento entre pesos e base é erro de
	programação, e falhar alto aqui é melhor que devolver um DV silenciosamente errado.
	"""
	return sum(int(d) * p for d, p in zip(digitos, pesos, strict=True))


def _dv_modulo_11(soma: int) -> int:
	"""Regra dominante: resto 0 ou 1 produz dígito 0, caso contrário 11 - resto."""
	resto = soma % 11

	return 0 if resto < 2 else 11 - resto


def _dv_modulo_11_subtraindo_10(soma: int) -> int:
	"""Variante de PE e RO: quando 11 - resto passa de 9, subtrai-se 10."""
	dv = 11 - (soma % 11)

	return dv - 10 if dv > 9 else dv


def _dv_modulo_10(soma: int) -> int:
	resto = soma % 10

	return 0 if resto == 0 else 10 - resto


def _dv_vezes_10(soma: int) -> int:
	"""Variante de AL e RN: multiplica a soma por 10 antes do módulo."""
	dv = (soma * 10) % 11

	return 0 if dv == 10 else dv


def _pesos_decrescentes(inicio: int, quantidade: int) -> tuple[int, ...]:
	"""Pesos que decrescem de `inicio` até 2, o padrão da maioria das UFs."""
	return tuple(range(inicio, inicio - quantidade, -1))


def _regra_simples(
	comprimento: int,
	pesos: tuple[int, ...],
	prefixos: tuple[str, ...] = (),
	dv: Callable[[int], int] = _dv_modulo_11,
) -> Callable[[str], bool]:
	"""Constrói a validação de uma UF com um único dígito verificador no fim."""

	def validar(ie: str) -> bool:
		if len(ie) != comprimento:
			return False

		if prefixos and not ie.startswith(prefixos):
			return False

		base, informado = ie[:-1], ie[-1]

		return str(dv(_soma(base, pesos))) == informado

	return validar


def _regra_dois_digitos(
	comprimento: int,
	pesos_dv1: tuple[int, ...],
	pesos_dv2: tuple[int, ...],
	prefixos: tuple[str, ...] = (),
	dv: Callable[[int], int] = _dv_modulo_11,
) -> Callable[[str], bool]:
	"""Constrói a validação de uma UF com dois dígitos verificadores no fim."""

	def validar(ie: str) -> bool:
		if len(ie) != comprimento:
			return False

		if prefixos and not ie.startswith(prefixos):
			return False

		base = ie[: comprimento - 2]

		dv1 = dv(_soma(base, pesos_dv1))
		dv2 = dv(_soma(base + str(dv1), pesos_dv2))

		return ie[-2:] == f"{dv1}{dv2}"

	return validar


# --------------------------------------------------------------------------------------
# UFs irregulares
# --------------------------------------------------------------------------------------


def _validar_sp(ie: str) -> bool:
	"""São Paulo: dígitos em posições não terminais, e formato próprio de produtor rural.

	Indústria/comércio tem 12 dígitos com DV na 9ª e na 12ª posição — não no fim,
	o que quebra qualquer motor genérico. Produtor rural começa com P.
	"""
	if ie.startswith("P"):
		corpo = ie[1:]

		if len(corpo) != 12 or not corpo.isdigit():
			return False

		# Só a 9ª posição é verificada; as três últimas são o número do estabelecimento.
		soma = _soma(corpo[:8], (1, 3, 4, 5, 6, 7, 8, 10))

		return str((soma % 11) % 10) == corpo[8]

	if len(ie) != 12 or not ie.isdigit():
		return False

	soma1 = _soma(ie[:8], (1, 3, 4, 5, 6, 7, 8, 10))

	if str((soma1 % 11) % 10) != ie[8]:
		return False

	soma2 = _soma(ie[:11], (3, 2, 10, 9, 8, 7, 6, 5, 4, 3, 2))

	return str((soma2 % 11) % 10) == ie[11]


def _validar_mg(ie: str) -> bool:
	"""Minas Gerais: primeiro dígito por módulo 10 com zero interposto.

	Insere-se um "0" logo após o código do município (3 primeiros dígitos), e a soma
	usa os *algarismos* de cada produto, não o produto — daí o desdobramento abaixo.
	"""
	if len(ie) != 13 or not ie.isdigit():
		return False

	base = ie[:3] + "0" + ie[3:11]

	soma = 0
	for i, caractere in enumerate(base):
		produto = int(caractere) * (1 if i % 2 == 0 else 2)
		soma += produto // 10 + produto % 10

	dezena = soma if soma % 10 == 0 else (soma // 10 + 1) * 10

	if str(dezena - soma) != ie[11]:
		return False

	soma2 = _soma(ie[:12], (3, 2, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2))

	return str(_dv_modulo_11(soma2)) == ie[12]


def _validar_ba(ie: str) -> bool:
	"""Bahia: o módulo (10 ou 11) depende do primeiro dígito, e o 2º DV é calculado antes.

	Aceita 8 e 9 dígitos; no formato de 9 quem decide o módulo é o segundo dígito.
	"""
	if len(ie) not in (8, 9) or not ie.isdigit():
		return False

	decisor = ie[0] if len(ie) == 8 else ie[1]
	dv = _dv_modulo_10 if decisor in "0123458" else _dv_modulo_11

	base = ie[:-2]
	tamanho = len(base)

	# O último dígito sai primeiro; o penúltimo o consome.
	dv2 = dv(_soma(base, _pesos_decrescentes(tamanho + 1, tamanho)))
	dv1 = dv(_soma(base + str(dv2), _pesos_decrescentes(tamanho + 2, tamanho + 1)))

	return ie[-2:] == f"{dv1}{dv2}"


def _validar_ap(ie: str) -> bool:
	"""Amapá: soma recebe um acréscimo fixo que varia por faixa de inscrição."""
	if len(ie) != 9 or not ie.isdigit() or not ie.startswith("03"):
		return False

	numero = int(ie[:8])

	if 3000001 <= numero <= 3017000:
		acrescimo, dv_quando_11 = 5, 0
	elif 3017001 <= numero <= 3019022:
		acrescimo, dv_quando_11 = 9, 1
	else:
		acrescimo, dv_quando_11 = 0, 0

	soma = acrescimo + _soma(ie[:8], _pesos_decrescentes(9, 8))
	dv = 11 - (soma % 11)

	if dv == 10:
		dv = 0
	elif dv == 11:
		dv = dv_quando_11

	return str(dv) == ie[8]


def _validar_go(ie: str) -> bool:
	"""Goiás: resto 1 só produz dígito 1 dentro de uma faixa histórica específica."""
	if len(ie) != 9 or not ie.isdigit() or not ie.startswith(("10", "11", "15")):
		return False

	soma = _soma(ie[:8], _pesos_decrescentes(9, 8))
	resto = soma % 11
	numero = int(ie[:8])

	if resto == 0:
		dv = 0
	elif resto == 1:
		dv = 1 if 10103105 <= numero <= 10119997 else 0
	else:
		dv = 11 - resto

	return str(dv) == ie[8]


def _validar_am(ie: str) -> bool:
	"""Amazonas: soma menor que 11 usa a subtração direta, sem passar pelo módulo."""
	if len(ie) != 9 or not ie.isdigit():
		return False

	soma = _soma(ie[:8], _pesos_decrescentes(9, 8))
	dv = 11 - soma if soma < 11 else _dv_modulo_11(soma)

	return str(dv if dv < 10 else 0) == ie[8]


def _validar_to(ie: str) -> bool:
	"""Tocantins: no formato de 11 dígitos, o tipo (3ª e 4ª posições) sai do cálculo."""
	if not ie.isdigit():
		return False

	if len(ie) == 11:
		if ie[2:4] not in ("01", "02", "03", "99"):
			return False

		base = ie[:2] + ie[4:10]
		informado = ie[10]
	elif len(ie) == 9:
		base, informado = ie[:8], ie[8]
	else:
		return False

	return str(_dv_modulo_11(_soma(base, _pesos_decrescentes(9, len(base))))) == informado


def _validar_rr(ie: str) -> bool:
	"""Roraima: único caso de módulo 9, com pesos crescentes."""
	if len(ie) != 9 or not ie.isdigit() or not ie.startswith("24"):
		return False

	soma = _soma(ie[:8], tuple(range(1, 9)))

	return str(soma % 9) == ie[8]


# --------------------------------------------------------------------------------------
# Mapa das 27 unidades federativas
# --------------------------------------------------------------------------------------

_PADRAO_9 = _pesos_decrescentes(9, 8)

_REGRAS: dict[str, Callable[[str], bool]] = {
	"AC": _regra_dois_digitos(
		13,
		(4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
		(5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
		prefixos=("01",),
	),
	"AL": _regra_simples(9, _PADRAO_9, prefixos=("24",), dv=_dv_vezes_10),
	"AM": _validar_am,
	"AP": _validar_ap,
	"BA": _validar_ba,
	"CE": _regra_simples(9, _PADRAO_9),
	"DF": _regra_dois_digitos(
		13,
		(4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
		(5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2),
		prefixos=("07",),
	),
	"ES": _regra_simples(9, _PADRAO_9),
	"GO": _validar_go,
	"MA": _regra_simples(9, _PADRAO_9, prefixos=("12",)),
	"MG": _validar_mg,
	"MS": _regra_simples(9, _PADRAO_9, prefixos=("28",)),
	"MT": _regra_simples(11, (3, 2, 9, 8, 7, 6, 5, 4, 3, 2)),
	"PA": _regra_simples(9, _PADRAO_9, prefixos=("15",)),
	"PB": _regra_simples(9, _PADRAO_9),
	"PE": _regra_dois_digitos(
		9,
		(8, 7, 6, 5, 4, 3, 2),
		(9, 8, 7, 6, 5, 4, 3, 2),
		dv=_dv_modulo_11_subtraindo_10,
	),
	"PI": _regra_simples(9, _PADRAO_9),
	"PR": _regra_dois_digitos(10, (3, 2, 7, 6, 5, 4, 3, 2), (4, 3, 2, 7, 6, 5, 4, 3, 2)),
	"RJ": _regra_simples(8, (2, 7, 6, 5, 4, 3, 2)),
	"RN": _regra_simples(9, _PADRAO_9, prefixos=("20",), dv=_dv_vezes_10),
	"RO": _regra_simples(
		14, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2), dv=_dv_modulo_11_subtraindo_10
	),
	"RR": _validar_rr,
	"RS": _regra_simples(10, (2, 9, 8, 7, 6, 5, 4, 3, 2)),
	"SC": _regra_simples(9, _PADRAO_9),
	"SE": _regra_simples(9, _PADRAO_9),
	"SP": _validar_sp,
	"TO": _validar_to,
}

UFS_SUPORTADAS = frozenset(_REGRAS)


def _validar_rn_10(ie: str) -> bool:
	"""RN admite também o formato de 10 dígitos, tratado à parte do mapa."""
	soma = _soma(ie[:9], _pesos_decrescentes(10, 9))

	return str(_dv_vezes_10(soma)) == ie[9]


def validar_inscricao_estadual(valor: str | None, uf: str | None) -> str:
	"""Valida a IE para a UF informada e devolve-a limpa (ou "ISENTO").

	Levanta ValidacaoFiscalError quando o dígito verificador não confere. UF ausente
	ou fora das 27 não é erro: sem regra aplicável, o valor passa como está.
	"""
	if not valor:
		raise ValidacaoFiscalError("Inscrição Estadual não informada", valor)

	bruto = str(valor).strip().upper()

	if limpar(bruto) == ISENTO:
		return ISENTO

	ie = limpar(bruto)

	if not ie:
		raise ValidacaoFiscalError("Inscrição Estadual não informada", valor)

	sigla = (uf or "").strip().upper()

	if sigla not in _REGRAS:
		# Sem regra conhecida, rejeitar seria pior que aceitar: veja o cabeçalho.
		return ie

	# SP é a única que admite letra (produtor rural começa com P).
	if sigla != "SP" and not ie.isdigit():
		raise ValidacaoFiscalError(f"Inscrição Estadual de {sigla} deve conter apenas dígitos", valor)

	valida = _REGRAS[sigla](ie)

	if not valida and sigla == "RN" and len(ie) == 10:
		valida = _validar_rn_10(ie)

	if not valida:
		raise ValidacaoFiscalError(f"Inscrição Estadual inválida para {sigla}", valor)

	return ie
