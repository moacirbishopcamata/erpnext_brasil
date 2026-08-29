# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Grupo `transp` — modalidade de frete, transportador e volumes.

Escopo
------
Cobertos: `modFrete` (obrigatório em toda NF-e, mesmo sem transporte real — `9` é "sem
ocorrência de transporte"), o transportador (CNPJ ou CPF, mutuamente exclusivos como em
`dest`), e os volumes (`vol`).

**Fora do escopo, declarado**: `retTransp` (retenção de ICMS sobre o frete — depende de
cálculo que este app não faz), `veicTransp`/`reboque`/`vagao`/`balsa` (identificação do
veículo, relevante para transporte próprio e regimes especiais de ICMS por UF).

Funções puras: nenhuma dependência do Frappe.
"""

from erpnext_brasil.fiscal.validators import limpar, validar_cpf_cnpj

__all__ = ["MODALIDADES_FRETE", "TransporteInvalido", "montar_transp"]

# Modalidade de contratação do frete — enumeração fechada do XSD (`TModFrete`).
MODALIDADES_FRETE = {
	"0": "Contratação por conta do Remetente (CIF)",
	"1": "Contratação por conta do Destinatário/Remetente (FOB)",
	"2": "Contratação por conta de Terceiros",
	"3": "Transporte próprio por conta do Remetente",
	"4": "Transporte próprio por conta do Destinatário",
	"9": "Sem Ocorrência de Transporte",
}


class TransporteInvalido(ValueError):
	def __init__(self, mensagem: str, campo: str = ""):
		super().__init__(mensagem)
		self.campo = campo


def _transportador(cnpj_cpf: str, nome: str, ie: str, endereco: dict) -> dict:
	if not limpar(cnpj_cpf):
		raise TransporteInvalido("CNPJ ou CPF do transportador é obrigatório", "cnpj_cpf")

	try:
		documento = validar_cpf_cnpj(cnpj_cpf)
	except ValueError as e:
		raise TransporteInvalido(f"CNPJ/CPF do transportador inválido: {e}", "cnpj_cpf") from e

	grupo = {"CNPJ" if len(documento) == 14 else "CPF": documento}

	if nome:
		grupo["xNome"] = nome

	if ie:
		grupo["IE"] = ie

	# O XSD usa xEnder/xMun/UF soltos, não um sub-grupo — diferente de enderEmit/enderDest.
	if endereco:
		grupo["xEnder"] = endereco.get("xEnder", "")
		grupo["xMun"] = endereco.get("xMun", "")
		grupo["UF"] = endereco.get("UF", "")

	return grupo


def montar_transp(
	modalidade_frete: str,
	transportador_cnpj_cpf: str = "",
	transportador_nome: str = "",
	transportador_ie: str = "",
	transportador_endereco: dict | None = None,
	volumes: list[dict] | None = None,
) -> dict:
	"""Monta o grupo `transp`.

	`modalidade_frete` é sempre obrigatória — inclusive quando não há transporte a
	relatar, caso em que vale `9`.
	"""
	if modalidade_frete not in MODALIDADES_FRETE:
		raise TransporteInvalido(
			f"Modalidade de frete deve ser uma de {sorted(MODALIDADES_FRETE)}, "
			f"recebida {modalidade_frete!r}",
			"modalidade_frete",
		)

	grupo: dict = {"modFrete": modalidade_frete}

	if transportador_cnpj_cpf:
		grupo["transporta"] = _transportador(
			transportador_cnpj_cpf,
			transportador_nome,
			transportador_ie,
			transportador_endereco or {},
		)

	if volumes:
		grupo["vol"] = list(volumes)

	return {"transp": grupo}
