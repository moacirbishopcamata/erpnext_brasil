# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Validação de identificadores fiscais brasileiros.

Este módulo é deliberadamente livre de dependências do Frappe: são funções puras,
testáveis sem bench, sem site e sem banco. O acoplamento com o ERPNext acontece em
`erpnext_brasil.integracao.party`, que traduz o resultado destas funções em `frappe.throw`.

CNPJ alfanumérico
-----------------
A partir de julho de 2026 (IN RFB 2.229/2024) o CNPJ passou a admitir letras nas
12 posições da raiz/ordem; os 2 dígitos verificadores continuam numéricos. O cálculo
do DV é o mesmo módulo 11 de sempre, mudando apenas a conversão do caractere em valor:
`valor = ord(c) - 48`, o que preserva 0-9 (48-57 -> 0-9) e mapeia A-Z para 17-42.

CNPJs puramente numéricos emitidos antes da mudança continuam válidos e passam pelo
mesmo caminho de código — não existe validador "legado" separado.
"""

import re

__all__ = [
	"ValidacaoFiscalError",
	"formatar_cnpj",
	"formatar_cpf",
	"limpar",
	"validar_cnpj",
	"validar_cpf",
	"validar_cpf_cnpj",
]


class ValidacaoFiscalError(ValueError):
	"""Erro de validação de um identificador fiscal.

	Carrega o valor recebido para que a camada de apresentação possa citá-lo na
	mensagem sem precisar reconstruí-lo.
	"""

	def __init__(self, mensagem: str, valor: str | None = None):
		super().__init__(mensagem)
		self.valor = valor


# Caracteres aceitos na raiz de um CNPJ alfanumérico: dígitos e letras maiúsculas.
_CNPJ_BASE_PERMITIDA = re.compile(r"^[0-9A-Z]{12}$")
_SOMENTE_DIGITOS = re.compile(r"^[0-9]+$")

# A especificação descreve os pesos como "2 a 9, da direita para a esquerda, reiniciando
# em 2 ao passar de 9". As tuplas abaixo são esse mesmo ciclo já escrito da esquerda para
# a direita, que é a ordem em que os caracteres são percorridos:
#
#   posição (da direita):  12 11 10  9  8  7  6  5  4  3  2  1
#   peso:                   5  4  3  2  9  8  7  6  5  4  3  2
#
# Não "corrija" para uma sequência crescente: a leitura é da direita, a iteração é da
# esquerda, e as duas só coincidem depois dessa inversão.
_PESOS_CNPJ_DV1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_PESOS_CNPJ_DV2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def limpar(valor: str | None) -> str:
	"""Remove máscara (pontos, barras, hífens, espaços) e normaliza para maiúsculas.

	Não valida nada: só devolve o identificador cru para as demais funções.
	"""
	if not valor:
		return ""

	return re.sub(r"[^0-9A-Za-z]", "", str(valor)).upper()


def _valor_do_caractere(c: str) -> int:
	"""Converte um caractere da base do CNPJ em seu valor numérico (ord - 48)."""
	return ord(c) - 48


def _digito_modulo_11(valores: list[int], pesos: tuple[int, ...]) -> int:
	soma = sum(v * p for v, p in zip(valores, pesos, strict=True))
	resto = soma % 11

	return 0 if resto < 2 else 11 - resto


def validar_cnpj(valor: str | None) -> str:
	"""Valida um CNPJ numérico ou alfanumérico e devolve-o limpo (14 caracteres).

	Levanta ValidacaoFiscalError quando o valor não é um CNPJ válido.
	"""
	cnpj = limpar(valor)

	if not cnpj:
		raise ValidacaoFiscalError("CNPJ não informado", valor)

	if len(cnpj) != 14:
		raise ValidacaoFiscalError(f"CNPJ deve ter 14 caracteres, recebido {len(cnpj)}", valor)

	base, dv_informado = cnpj[:12], cnpj[12:]

	if not _CNPJ_BASE_PERMITIDA.match(base):
		raise ValidacaoFiscalError(
			"CNPJ só admite dígitos e letras maiúsculas nas 12 primeiras posições", valor
		)

	if not _SOMENTE_DIGITOS.match(dv_informado):
		raise ValidacaoFiscalError("Os dois dígitos verificadores do CNPJ devem ser numéricos", valor)

	# Divergência deliberada da implementação de referência da Receita (dv.py), que é um
	# calculador de DV puro e aceita "00000000000000" — a soma zera, o resto é 0 e os dois
	# dígitos saem 0, satisfazendo o módulo 11 por acidente aritmético.
	#
	# Aqui a base toda-igual é rejeitada **apenas quando numérica**: 00000000000000 e
	# 11111111111111 são valores-lixo consagrados, e deixá-los entrar suja o cadastro
	# fiscal. Já uma base alfanumérica toda igual não tem essa convenção contra si, e
	# rejeitá-la arriscaria travar uma inscrição legítima — por isso passa.
	if len(set(base)) == 1 and base.isdigit():
		raise ValidacaoFiscalError("CNPJ com todos os dígitos iguais é inválido", valor)

	valores = [_valor_do_caractere(c) for c in base]

	dv1 = _digito_modulo_11(valores, _PESOS_CNPJ_DV1)
	dv2 = _digito_modulo_11([*valores, dv1], _PESOS_CNPJ_DV2)

	if dv_informado != f"{dv1}{dv2}":
		raise ValidacaoFiscalError("Dígito verificador do CNPJ não confere", valor)

	return cnpj


def validar_cpf(valor: str | None) -> str:
	"""Valida um CPF e devolve-o limpo (11 dígitos)."""
	cpf = limpar(valor)

	if not cpf:
		raise ValidacaoFiscalError("CPF não informado", valor)

	if not _SOMENTE_DIGITOS.match(cpf):
		raise ValidacaoFiscalError("CPF deve conter apenas dígitos", valor)

	if len(cpf) != 11:
		raise ValidacaoFiscalError(f"CPF deve ter 11 dígitos, recebido {len(cpf)}", valor)

	if len(set(cpf)) == 1:
		raise ValidacaoFiscalError("CPF com todos os dígitos iguais é inválido", valor)

	digitos = [int(c) for c in cpf[:9]]

	dv1 = _digito_modulo_11(digitos, tuple(range(10, 1, -1)))
	dv2 = _digito_modulo_11([*digitos, dv1], tuple(range(11, 1, -1)))

	if cpf[9:] != f"{dv1}{dv2}":
		raise ValidacaoFiscalError("Dígito verificador do CPF não confere", valor)

	return cpf


def validar_cpf_cnpj(valor: str | None) -> str:
	"""Valida CPF ou CNPJ decidindo pelo comprimento do valor limpo."""
	limpo = limpar(valor)

	if len(limpo) == 11:
		return validar_cpf(valor)

	if len(limpo) == 14:
		return validar_cnpj(valor)

	raise ValidacaoFiscalError(
		f"Identificador deve ter 11 (CPF) ou 14 (CNPJ) caracteres, recebido {len(limpo)}", valor
	)


def formatar_cnpj(valor: str | None) -> str:
	"""Devolve o CNPJ com máscara 00.000.000/0000-00 (funciona com letras)."""
	c = limpar(valor)

	if len(c) != 14:
		return c

	return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def formatar_cpf(valor: str | None) -> str:
	"""Devolve o CPF com máscara 000.000.000-00."""
	c = limpar(valor)

	if len(c) != 11:
		return c

	return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"
