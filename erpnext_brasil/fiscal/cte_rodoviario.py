# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""CT-e: modal rodoviário (`infModal/rodo`) — RNTRC e ordens de coleta.

Por que existe
--------------
Confirmado por leitura direta do XSD (`cteModalRodoviario_v4.00.xsd`, `nfephp-org/sped-cte`,
102 linhas — arquivo pequeno o suficiente para ler inteiro, sem risco de truncamento) que o
modal rodoviário do CT-e é bem menor do que se poderia supor por analogia com o MDF-e: **não**
carrega identificação de veículo nem de motorista aqui — isso é responsabilidade do MDF-e, o
documento que identifica o veículo/motorista/rota de uma viagem específica, que pode agrupar
várias prestações de CT-e. O modal rodoviário do CT-e carrega só:

- `RNTRC` (obrigatório) — Registro Nacional de Transportadores Rodoviários de Carga, o cadastro
  do transportador na ANTT.
- `occ` (opcional, até 10) — Ordens de Coleta associadas, cada uma com série/número/data de
  emissão e os dados de quem emitiu a ordem.

A pegadinha do RNTRC, verificada no XSD, não suposta
------------------------------------------------------------------------------
`TRNTRC` não é só uma sequência de dígitos: é `[0-9]{8}|ISENTO` — oito dígitos **ou** a palavra
literal `ISENTO`, usada por quem transporta com frota própria e por isso está dispensado do
registro na ANTT. Tratar `ISENTO` como formato inválido (ex. validar só `\\d{8}`) rejeitaria uma
transportadora legítima; tratar qualquer string de 8 caracteres como válida aceitaria lixo. A
validação aqui cobre as duas pontas.

Escopo: só `RNTRC` e a passagem adiante de `occ` — não os campos internos de `occ`
------------------------------------------------------------------------------------------
`occ` é aceito como lista de dicionários já montados pelo chamador (não validados campo a campo
aqui) — modelar `emiOcc` por completo (CNPJ, IE, UF, telefone de quem emitiu a ordem de coleta)
fica para quando houver um caso de uso real de ordem de coleta, não especulativamente.
"""

__all__ = ["RNTRC_ISENTO", "RntrcInvalido", "montar_rodo", "validar_rntrc"]

RNTRC_ISENTO = "ISENTO"


class RntrcInvalido(ValueError):
	"""RNTRC que não é nem 8 dígitos nem a palavra `ISENTO`."""


def validar_rntrc(rntrc: str) -> str:
	"""Valida o RNTRC contra o padrão do XSD (`[0-9]{8}|ISENTO`) e devolve normalizado."""
	valor = (rntrc or "").strip().upper()

	if valor == RNTRC_ISENTO:
		return valor

	if not (valor.isdigit() and len(valor) == 8):
		raise RntrcInvalido(f"RNTRC deve ter 8 dígitos ou ser a palavra {RNTRC_ISENTO!r}, recebido {rntrc!r}")

	return valor


def montar_rodo(rntrc: str, ordens_coleta: list[dict] | None = None) -> dict:
	"""Monta o grupo `infModal/rodo`."""
	grupo = {"RNTRC": validar_rntrc(rntrc)}

	if ordens_coleta:
		grupo["occ"] = list(ordens_coleta)

	return grupo
