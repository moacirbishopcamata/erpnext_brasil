# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""MDF-e: modal rodoviário (`infModal/rodo`) — veículo e motorista.

Por que existe, e o espelho invertido do CT-e
------------------------------------------------------------------------------
Confirmado em `docs/mdfe-estado.md`: o modal rodoviário do MDF-e é o **oposto** do CT-e
(`fiscal/cte_rodoviario.py`) — é aqui, não lá, que veículo e motorista são identificados,
porque é o MDF-e que representa a viagem física (pode agrupar várias prestações de CT-e), não o
CT-e (que é só o contrato de uma prestação). Confirmado por leitura direta do XSD
(`mdfeModalRodoviario_v3.00.xsd`, `nfephp-org/sped-mdfe`).

`RNTRC` reaproveitado, o resto não
------------------------------------------------------------------------------
O tipo `TRNTRC` (`[0-9]{8}|ISENTO`) é o mesmo do CT-e — confirmado, o XSD usa `type="TRNTRC"`
nos dois documentos. `validar_rntrc`/`RntrcInvalido` são importados de `cte_rodoviario.py`, não
reimplementados. O resto do grupo (veículo, motorista) não tem equivalente no CT-e para
reaproveitar — é conteúdo genuinamente novo deste módulo.

Escopo: veículo de tração, motorista e reboques — não `infCIOT`/`valePed`
------------------------------------------------------------------------------------------
`infANTT/infCIOT` (Código Identificador da Operação de Transporte) e `infANTT/valePed`
(vale-pedágio obrigatório) existem no XSD mas não foram implementados — são obrigações
acessórias específicas de operação de frete rodoviário terceirizado, com fornecedores/
responsáveis próprios, fora do escopo deste primeiro incremento de modal.

`prop` (proprietário do veículo, só preenchido quando não é o próprio emitente) também não foi
implementado — caso menos comum (frota própria é a maioria), fica para quando houver demanda
real.
"""

from dataclasses import dataclass, field

from erpnext_brasil.fiscal.cte_rodoviario import RntrcInvalido, validar_rntrc
from erpnext_brasil.fiscal.validators import validar_cpf

__all__ = [
	"CARROCERIA_ABERTA",
	"CARROCERIA_FECHADA_BAU",
	"CARROCERIA_GRANELEIRA",
	"CARROCERIA_NAO_APLICAVEL",
	"CARROCERIA_PORTA_CONTAINER",
	"CARROCERIA_SIDER",
	"RODADO_CAVALO_MECANICO",
	"RODADO_OUTROS",
	"RODADO_TOCO",
	"RODADO_TRUCK",
	"RODADO_UTILITARIO",
	"RODADO_VAN",
	"Condutor",
	"MdfeRodoviarioInvalido",
	"RntrcInvalido",
	"Veiculo",
	"montar_condutor",
	"montar_rodo",
	"montar_veiculo_reboque",
	"montar_veiculo_tracao",
]

# `tpRod` — confirmado em `veicTracao/tpRod` (só existe para o veículo de tração, o reboque
# não tem "tipo de rodado" próprio).
RODADO_TRUCK = "01"
RODADO_TOCO = "02"
RODADO_CAVALO_MECANICO = "03"
RODADO_VAN = "04"
RODADO_UTILITARIO = "05"
RODADO_OUTROS = "06"

# `tpCar` — confirmado em `veicTracao/tpCar` e `veicReboque/tpCar` (existe nos dois).
CARROCERIA_NAO_APLICAVEL = "00"
CARROCERIA_ABERTA = "01"
CARROCERIA_FECHADA_BAU = "02"
CARROCERIA_GRANELEIRA = "03"
CARROCERIA_PORTA_CONTAINER = "04"
CARROCERIA_SIDER = "05"

_RODADOS_VALIDOS = {
	RODADO_TRUCK, RODADO_TOCO, RODADO_CAVALO_MECANICO,
	RODADO_VAN, RODADO_UTILITARIO, RODADO_OUTROS,
}
_CARROCERIAS_VALIDAS = {
	CARROCERIA_NAO_APLICAVEL, CARROCERIA_ABERTA, CARROCERIA_FECHADA_BAU,
	CARROCERIA_PORTA_CONTAINER, CARROCERIA_GRANELEIRA, CARROCERIA_SIDER,
}


class MdfeRodoviarioInvalido(ValueError):
	"""Dado do modal rodoviário do MDF-e que impediria a autorização do documento."""


@dataclass(frozen=True)
class Condutor:
	"""`condutor` — só nome e CPF, o grupo mais simples do modal."""

	nome: str
	cpf: str


@dataclass(frozen=True)
class Veiculo:
	"""Dados compartilhados por `veicTracao` e `veicReboque`.

	`tipo_rodado` e `condutores` só se aplicam ao veículo de tração — `montar_veiculo_tracao`
	os exige, `montar_veiculo_reboque` os ignora (o XSD não tem esses campos em `veicReboque`).
	"""

	placa: str
	tara: str
	codigo_interno: str = ""
	renavam: str = ""
	capacidade_kg: str = ""
	capacidade_m3: str = ""
	tipo_carroceria: str = ""
	uf_licenciamento: str = ""
	tipo_rodado: str = ""
	condutores: list[Condutor] = field(default_factory=list)


def _validar_tara(tara: str) -> str:
	valor = (tara or "").strip()

	if not (valor == "0" or (valor.isdigit() and valor[0] != "0")):
		raise MdfeRodoviarioInvalido(
			f"tara deve ser '0' ou um número sem zero à esquerda, recebido {tara!r}"
		)

	return valor


def montar_condutor(condutor: Condutor) -> dict:
	"""Monta um item de `condutor` — reusa `validar_cpf`, mesma validação usada em todo o app."""
	try:
		cpf = validar_cpf(condutor.cpf)
	except ValueError as e:
		raise MdfeRodoviarioInvalido(f"CPF do condutor inválido: {e}") from e

	return {"xNome": condutor.nome.strip(), "CPF": cpf}


def montar_veiculo_tracao(veiculo: Veiculo) -> dict:
	"""Monta `veicTracao` — exige `tipo_rodado` e ao menos um condutor, únicos campos que
	`veicReboque` não tem."""
	if veiculo.tipo_rodado not in _RODADOS_VALIDOS:
		raise MdfeRodoviarioInvalido(
			f"tipo_rodado deve ser um de {sorted(_RODADOS_VALIDOS)}, recebido {veiculo.tipo_rodado!r}"
		)

	if not veiculo.condutores:
		raise MdfeRodoviarioInvalido("veicTracao precisa de ao menos um condutor")

	grupo = _montar_campos_comuns(veiculo)
	grupo["condutor"] = [montar_condutor(c) for c in veiculo.condutores]
	grupo["tpRod"] = veiculo.tipo_rodado

	if veiculo.tipo_carroceria:
		if veiculo.tipo_carroceria not in _CARROCERIAS_VALIDAS:
			raise MdfeRodoviarioInvalido(
				f"tipo_carroceria deve ser um de {sorted(_CARROCERIAS_VALIDAS)}, "
				f"recebido {veiculo.tipo_carroceria!r}"
			)

		grupo["tpCar"] = veiculo.tipo_carroceria

	if veiculo.uf_licenciamento:
		grupo["UF"] = veiculo.uf_licenciamento

	return grupo


def montar_veiculo_reboque(veiculo: Veiculo) -> dict:
	"""Monta um item de `veicReboque` — sem `tpRod`/`condutor`, que só existem em `veicTracao`."""
	grupo = _montar_campos_comuns(veiculo)

	if veiculo.tipo_carroceria:
		if veiculo.tipo_carroceria not in _CARROCERIAS_VALIDAS:
			raise MdfeRodoviarioInvalido(
				f"tipo_carroceria deve ser um de {sorted(_CARROCERIAS_VALIDAS)}, "
				f"recebido {veiculo.tipo_carroceria!r}"
			)

		grupo["tpCar"] = veiculo.tipo_carroceria

	if veiculo.uf_licenciamento:
		grupo["UF"] = veiculo.uf_licenciamento

	return grupo


def _montar_campos_comuns(veiculo: Veiculo) -> dict:
	grupo: dict = {}

	if veiculo.codigo_interno:
		grupo["cInt"] = veiculo.codigo_interno

	if not veiculo.placa.strip():
		raise MdfeRodoviarioInvalido("Veículo precisa de placa")

	grupo["placa"] = veiculo.placa.strip().upper()

	if veiculo.renavam:
		grupo["RENAVAM"] = veiculo.renavam

	grupo["tara"] = _validar_tara(veiculo.tara)

	if veiculo.capacidade_kg:
		grupo["capKG"] = veiculo.capacidade_kg

	if veiculo.capacidade_m3:
		grupo["capM3"] = veiculo.capacidade_m3

	return grupo


def montar_rodo(rntrc: str, veiculo_tracao: Veiculo, veiculos_reboque: list[Veiculo] | None = None) -> dict:
	"""Monta o grupo `infModal/rodo` do MDF-e — `infANTT/RNTRC`, `veicTracao` e, opcionalmente,
	`veicReboque` (até 3, ver XSD)."""
	grupo: dict = {"infANTT": {"RNTRC": validar_rntrc(rntrc)}}
	grupo["veicTracao"] = montar_veiculo_tracao(veiculo_tracao)

	if veiculos_reboque:
		grupo["veicReboque"] = [montar_veiculo_reboque(v) for v in veiculos_reboque]

	return grupo
