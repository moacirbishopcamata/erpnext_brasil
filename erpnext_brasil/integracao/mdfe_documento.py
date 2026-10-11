# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Mapeia um `Shipment` para a árvore do MDF-e.

Tarefas 4.1 a 4.3 de `fechar-laco-cte-mdfe`: a camada entre o documento real do ERPNext e a
montagem pura de `fiscal/mdfe_montagem.py`. Irmão de `cte_documento.py`.

O que este módulo faz — e o que não faz
-----------------------------------------
Só **lê o cadastro e traduz** para `DadosMdfe`: a `Company` de `pickup_company` → emitente, os
`Delivery Note` com chave de acesso → documentos manifestados, os endereços do `Shipment` →
municípios, os campos `br_*` da viagem → veículo e motorista. Toda a regra do leiaute mora em
`fiscal/mdfe_montagem.py`, onde `tests/test_mdfe_montagem.py` a trava sem bench.

`cte_extracao.referencias_do_shipment` deixa de ser órfão aqui: é ele quem percorre `Shipment` →
`Shipment Delivery Note` → `Delivery Note` → `br_chave_acesso` e resolve o município de descarga
(`design.md`, decisão 2). `mapeamento_cte.agrupar_por_municipio_descarga` os agrupa.

De onde sai o quê
-------------------
- **Emitente**: `pickup_company`, só quando `pickup_from_type` é `Company`. O `Shipment` não tem o
  campo `company`; o manifesto é do transportador de carga própria (`tpEmit` 2), que é dono das
  NF-e que carrega — então quem despacha é a empresa de origem.
- **Município e UF de carregamento**: o endereço de coleta (`pickup_address_name`). **De
  descarga**: o endereço de entrega (`delivery_address_name`), como `referencias_do_shipment` já
  decide. A UF sai dos dois primeiros dígitos do código IBGE do município.
- **Valor da carga**: a soma de `grand_total` das linhas de `Shipment Delivery Note` **cuja nota
  tem chave de acesso**, ou seja, o valor do que o manifesto de fato referencia. O
  `value_of_goods` do `Shipment` é um campo livre que pode divergir das notas.
- **Peso**: `total_weight`, em KG.
- **RNTRC**: `Company.br_rntrc`. **Veículo e motorista**: campos `br_*_mdfe` do próprio `Shipment`.

O que **se recusa** a inventar
-------------------------------
Cada ausência levanta `MdfeInvalido` dizendo qual dado falta e **em qual cadastro**. O número é
alocado **aqui, mas só depois** de a montagem de prova validar tudo (`montar_mdfe_alocando_numero`):
a série vem de `br_serie_mdfe` da `Company` e `numero_do_documento` reaproveita o número de uma
reemissão. A data de emissão é o instante da chamada, com o fuso do sistema.

Estado de verificação: camada Frappe, **não** exercitada contra bench real até o teste de
`tests_bench/test_mdfe_documento.py` (tarefa 6.2).
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation

import frappe

from erpnext_brasil.fiscal.codigos.uf import UfDesconhecida, sigla_da_uf
from erpnext_brasil.fiscal.mdfe import Emitente, MdfeInvalido, MunicipioCarrega
from erpnext_brasil.fiscal.mdfe_montagem import DadosMdfe, montar_mdfe_alocando_numero
from erpnext_brasil.fiscal.mdfe_rodoviario import Condutor, Veiculo
from erpnext_brasil.integracao.configuracao_fiscal import agora_da_emissao, serie_padrao
from erpnext_brasil.integracao.cte_extracao import CteExtracaoInvalida, referencias_do_shipment
from erpnext_brasil.integracao.mapeamento_cte import agrupar_por_municipio_descarga
from erpnext_brasil.integracao.nfe_documento import (
	DadosInsuficientes,
	_endereco_vinculado,
	_grupo_endereco,
)
from erpnext_brasil.integracao.numeracao_fiscal import numero_do_documento
from erpnext_brasil.setup.campos_documento import RODADO_MDFE_POR_ROTULO

__all__ = ["empresa_do_shipment", "montar_mdfe_do_documento", "municipio_de_descarga"]

MODELO_MDFE = "58"
CAMPO_NUMERO = "br_numero_mdfe"


def _exigir(valor, campo: str, onde: str, nome_do_campo: str = "") -> str:
	"""O texto, ou `MdfeInvalido` nomeando o dado e o cadastro onde preenchê-lo."""
	texto = str(valor or "").strip()

	if not texto:
		raise MdfeInvalido(f"{campo} é obrigatório no MDF-e e está vazio em {onde}", nome_do_campo or campo)

	return texto


def _empresa(shipment) -> str:
	"""A empresa emitente: a de origem da coleta, quando a coleta parte de uma `Company`."""
	onde = f"Shipment {shipment.name}"

	if shipment.get("pickup_from_type") != "Company":
		raise MdfeInvalido(
			f"o MDF-e do transportador de carga própria parte de uma Company, e a coleta de {onde} é de "
			f"{shipment.get('pickup_from_type') or 'ninguém'} — ajuste 'Coletar de'",
			"pickup_from_type",
		)

	return _exigir(
		shipment.get("pickup_company"), "empresa de origem (pickup_company)", onde, "pickup_company"
	)


def empresa_do_shipment(shipment) -> str:
	"""A `Company` emitente do manifesto — o `Shipment` do core não tem `company`, e o registro fiscal exige."""
	return _empresa(shipment)


def _emitente(company: str) -> Emitente:
	empresa = frappe.get_cached_doc("Company", company)
	onde = f"Company {company}"

	try:
		endereco = _grupo_endereco(_endereco_vinculado("Company", company), f"endereço da {onde}")
	except DadosInsuficientes as erro:
		raise MdfeInvalido(str(erro), "emitente") from erro

	return Emitente(
		cnpj_cpf=_exigir(empresa.get("tax_id"), "CNPJ do emitente", onde, "cnpj_cpf"),
		nome=_exigir(empresa.get("company_name"), "razão social", onde, "nome"),
		endereco=endereco,
		inscricao_estadual=str(empresa.get("br_inscricao_estadual") or "").strip(),
	)


def _municipio(shipment, campo_endereco: str, rotulo: str) -> tuple[str, str, str]:
	"""`(código IBGE, nome, UF)` do endereço do `Shipment`. A UF sai do código — não do texto livre."""
	onde = f"Shipment {shipment.name}"
	nome_endereco = _exigir(shipment.get(campo_endereco), f"endereço de {rotulo}", onde, campo_endereco)
	endereco = frappe.get_cached_doc("Address", nome_endereco)
	onde_endereco = f"Address {nome_endereco} ({rotulo})"
	codigo = _exigir(
		endereco.get("br_codigo_municipio_ibge"), "código IBGE do município", onde_endereco, campo_endereco
	)
	nome = _exigir(endereco.get("city"), "município", onde_endereco, campo_endereco)

	try:
		uf = sigla_da_uf(codigo[:2])
	except UfDesconhecida as erro:
		raise MdfeInvalido(f"código IBGE {codigo!r} em {onde_endereco}: {erro}", campo_endereco) from erro

	return codigo, nome, uf


def municipio_de_descarga(shipment) -> tuple[str, str, str]:
	"""`(código IBGE, nome, UF)` do endereço de entrega — onde a viagem termina, e portanto onde se encerra."""
	return _municipio(shipment, "delivery_address_name", "descarga")


def _valor_manifestado(shipment) -> Decimal:
	"""Soma do que o manifesto referencia: só as notas com chave de acesso."""
	total = Decimal(0)

	for linha in shipment.get("shipment_delivery_note") or []:
		if linha.get("delivery_note") and frappe.db.get_value(
			"Delivery Note", linha.delivery_note, "br_chave_acesso"
		):
			total += Decimal(str(linha.get("grand_total") or 0))

	return total


def _peso(shipment) -> Decimal:
	try:
		return Decimal(str(shipment.get("total_weight") or 0))
	except InvalidOperation as erro:
		raise MdfeInvalido(f"peso total inválido em Shipment {shipment.name}", "peso_carga") from erro


def _veiculo(shipment, prefixo: str, onde: str, tracao: bool) -> Veiculo:
	rotulo = "veículo de tração" if tracao else "reboque"
	placa = _exigir(shipment.get(f"br_placa{prefixo}_mdfe"), f"placa do {rotulo}", onde, "veiculo_tracao")
	tara = _exigir(shipment.get(f"br_tara{prefixo}_mdfe"), f"tara do {rotulo}", onde, "veiculo_tracao")

	if not tracao:
		return Veiculo(placa=placa, tara=tara)

	rodado = _exigir(shipment.get("br_rodado_mdfe"), "tipo de rodado", onde, "veiculo_tracao")

	if rodado not in RODADO_MDFE_POR_ROTULO:
		raise MdfeInvalido(
			f"tipo de rodado {rodado!r} em {onde} não é um dos valores {sorted(RODADO_MDFE_POR_ROTULO)}",
			"veiculo_tracao",
		)

	condutor = Condutor(
		nome=_exigir(shipment.get("br_condutor_nome_mdfe"), "nome do motorista", onde, "veiculo_tracao"),
		cpf=_exigir(shipment.get("br_condutor_cpf_mdfe"), "CPF do motorista", onde, "veiculo_tracao"),
	)

	return Veiculo(placa=placa, tara=tara, tipo_rodado=RODADO_MDFE_POR_ROTULO[rodado], condutores=[condutor])


def _dados(shipment, ambiente: str, agora: datetime | None) -> DadosMdfe:
	onde = f"Shipment {shipment.name}"
	company = _empresa(shipment)
	empresa = frappe.get_cached_doc("Company", company)
	serie = _exigir(
		serie_padrao(company, MODELO_MDFE), "série do MDF-e (br_serie_mdfe)", f"Company {company}", "serie"
	)

	codigo_carga, nome_carga, uf_inicio = _municipio(shipment, "pickup_address_name", "coleta")
	_, _, uf_fim = _municipio(shipment, "delivery_address_name", "entrega")

	try:
		municipios = agrupar_por_municipio_descarga(referencias_do_shipment(shipment))
	except CteExtracaoInvalida as erro:
		raise MdfeInvalido(str(erro), "delivery_address_name") from erro

	reboque = str(shipment.get("br_placa_reboque_mdfe") or "").strip()

	return DadosMdfe(
		emitente=_emitente(company),
		serie=serie,
		emissao=agora or agora_da_emissao(),
		ambiente="1" if ambiente == "producao" else "2",
		uf_inicio=uf_inicio,
		uf_fim=uf_fim,
		municipios_carrega=[MunicipioCarrega(codigo=codigo_carga, nome=nome_carga)],
		municipios_descarga=municipios,
		rntrc=_exigir(empresa.get("br_rntrc"), "RNTRC", f"Company {company}", "rntrc"),
		veiculo_tracao=_veiculo(shipment, "", onde, tracao=True),
		veiculos_reboque=[_veiculo(shipment, "_reboque", onde, tracao=False)] if reboque else [],
		valor_carga=_valor_manifestado(shipment),
		peso_carga=_peso(shipment),
	)


def montar_mdfe_do_documento(shipment, ambiente: str, agora: datetime | None = None) -> tuple[dict, str]:
	"""A árvore `MDFe` **não assinada** e a chave de acesso, a partir de um `Shipment`.

	A série vem de `br_serie_mdfe` da `Company` e o número é alocado aqui, **depois** de todo o
	cadastro validar — uma recusa por dado faltante nunca consome número da série. Reemitir um
	`Shipment` que já tem `br_numero_mdfe` reaproveita o número. `ambiente` é `"producao"` ou
	`"homologacao"`. Toda recusa sai como `MdfeInvalido`, com `campo` e mensagem que nomeiam o dado.
	Chamar dentro da transação do documento (a alocação não faz `commit`).
	"""
	dados = _dados(shipment, ambiente, agora)
	company = _empresa(shipment)

	return montar_mdfe_alocando_numero(
		dados,
		lambda: numero_do_documento(shipment, MODELO_MDFE, dados.serie, CAMPO_NUMERO, company=company),
	)
