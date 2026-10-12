# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""CPF e CNS (Cartão Nacional de Saúde): validação pelo dígito verificador.

Fonte e confiança
-----------------
- CPF: módulo 11 sobre os nove primeiros dígitos e depois sobre os dez primeiros. Algoritmo público e estável.
- CNS: 15 dígitos. O definitivo começa em 1 ou 2 (derivado do PIS) e o provisório em 7, 8 ou 9. Nos dois casos
  a soma dos 15 dígitos ponderados de 15 a 1 é múltipla de 11 — é o que `cns_valido` confere. A regra de
  derivação do definitivo é a divulgada em material do DATASUS e de secretarias; **o documento oficial do
  DATASUS não foi lido**, então a validação aqui é só a aritmética do dígito, não a existência do cartão.
"""

__all__ = ["cns_valido", "cpf_valido", "somente_digitos"]


def somente_digitos(texto: str) -> str:
	return "".join(c for c in texto if c.isdigit())


def _dv_cpf(base: str) -> int:
	soma = sum(int(d) * peso for d, peso in zip(base, range(len(base) + 1, 1, -1), strict=True))
	resto = (soma * 10) % 11

	return 0 if resto == 10 else resto


def cpf_valido(texto: str) -> bool:
	cpf = somente_digitos(texto)

	if len(cpf) != 11 or len(set(cpf)) == 1:
		return False

	return int(cpf[9]) == _dv_cpf(cpf[:9]) and int(cpf[10]) == _dv_cpf(cpf[:10])


def cns_valido(texto: str) -> bool:
	cns = somente_digitos(texto)

	if len(cns) != 15 or cns[0] not in "12789":
		return False

	soma = sum(int(d) * peso for d, peso in zip(cns, range(15, 0, -1), strict=True))

	return soma % 11 == 0
