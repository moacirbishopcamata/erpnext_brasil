# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""MDF-e: a árvore `MDFe` completa a partir de dados já extraídos — sem `frappe`.

Irmão de `fiscal/cte_montagem.py`, pelo mesmo motivo: `integracao/mdfe_documento.py` lê o cadastro
(`Shipment`, `Company`, `Delivery Note`, `Address`) e precisa importar `frappe`, então a suíte pura
não o alcança. A regra de montagem — que grupo vem depois de qual, o que se recusa — não depende de
banco e mora aqui, onde `tests/test_mdfe_montagem.py` a trava. A camada Frappe vira só tradução:
cadastro → `DadosMdfe`.

Costura, não regra nova
-----------------------
Todos os grupos já tinham montador testado (`fiscal/mdfe.py`, `fiscal/mdfe_rodoviario.py`). O que
faltava era quem os **encadeasse** a partir de um documento — o mesmo buraco que `cte_montagem`
fechou para o CT-e. Este módulo só compõe: `ide` + `emit` + `infModal` + `infDoc` + `tot`, nessa
ordem (`montar_infmdfe`), com a chave de acesso derivada uma vez e usada em `cDV` e no `Id`.

O que se recusa
---------------
Cada recusa é um `MdfeInvalido` cujo `campo` e mensagem **nomeiam o dado faltante**:

- sem município de descarga com documento fiscal — o manifesto sem carga não manifesta nada;
- sem município de carregamento, UF de início/fim, RNTRC, veículo de tração ou condutor;
- valor e peso da carga não positivos (`tot` exige os dois);
- emitente com CPF: a chave de acesso leva **CNPJ** (posições 7-20), então um MDF-e de
  transportador autônomo pessoa física não pode ser numerado por este caminho;
- data de emissão sem fuso — o XSD recusa `dhEmi` sem deslocamento;
- modal que não seja o rodoviário: só ele está implementado.

Escolhas que não vêm do XSD, e por isso ficam declaradas
--------------------------------------------------------
- `tpEmit` padrão `2` (transportador de carga própria): é o caso em que o emitente do MDF-e é dono
  das NF-e que carrega, o único que a origem `Shipment` → `Delivery Note` cobre
  (`design.md`, decisão 2). `tpEmit` 1 exigiria CT-e que não vêm de lugar nenhum.
- `infCIOT` não é montado: `montar_rodo` só produz `infANTT/RNTRC`. O CIOT é opcional no leiaute e
  exigi-lo aqui seria inventar um campo do cadastro.
- O código numérico (`cMDF`) é sorteado por `sortear_codigo_numerico`; a regra do MDF-e **não foi
  conferida** contra o MOC (a da NF-e é pelo menos tão estrita).
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from erpnext_brasil.fiscal.codigos.uf import UfDesconhecida, codigo_da_uf
from erpnext_brasil.fiscal.cte_rodoviario import RntrcInvalido
from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.fiscal.documento.nfe import sortear_codigo_numerico
from erpnext_brasil.fiscal.documento.numeracao import NumeracaoInvalida, validar_numero
from erpnext_brasil.fiscal.mdfe import (
	AMBIENTE_HOMOLOGACAO,
	EMITENTE_TRANSPORTADOR_CARGA_PROPRIA,
	MODAL_RODOVIARIO,
	UNIDADE_PESO_KG,
	Emitente,
	IdentificacaoMdfe,
	MdfeInvalido,
	MunicipioCarrega,
	MunicipioDescarga,
	montar_emit,
	montar_ide,
	montar_infdoc,
	montar_infmdfe,
	montar_infmodal,
	montar_mdfe,
	montar_tot,
)
from erpnext_brasil.fiscal.mdfe_rodoviario import MdfeRodoviarioInvalido, Veiculo, montar_rodo

__all__ = [
	"VERSAO_MODAL",
	"DadosMdfe",
	"montar_mdfe_alocando_numero",
	"montar_mdfe_de_dados",
]

VERSAO_MODAL = "3.00"
"""`versaoModal` do `infModal` do MDF-e 3.00."""

NUMERO_DE_PROVA = "1"
"""Número descartável da montagem de prova — só prova que os dados valem, nunca vai a documento."""

_CAMPOS_DO_ENDERECO = ("xLgr", "nro", "xBairro", "cMun", "xMun", "CEP", "UF")


@dataclass(frozen=True)
class DadosMdfe:
	"""Tudo o que a montagem precisa, já extraído do cadastro — nada aqui conhece o Frappe."""

	emitente: Emitente
	serie: str
	emissao: datetime
	uf_inicio: str
	"""Sigla da UF de início da viagem (`UFIni`)."""
	uf_fim: str
	"""Sigla da UF de fim da viagem (`UFFim`)."""
	municipios_carrega: list[MunicipioCarrega]
	municipios_descarga: list[MunicipioDescarga]
	rntrc: str
	veiculo_tracao: Veiculo
	valor_carga: Decimal
	peso_carga: Decimal
	veiculos_reboque: list[Veiculo] = field(default_factory=list)
	unidade_peso: str = UNIDADE_PESO_KG
	tipo_emitente: str = EMITENTE_TRANSPORTADOR_CARGA_PROPRIA
	ambiente: str = AMBIENTE_HOMOLOGACAO
	modal: str = MODAL_RODOVIARIO


def _exigir_endereco(emitente: Emitente) -> None:
	faltando = [campo for campo in _CAMPOS_DO_ENDERECO if not str(emitente.endereco.get(campo) or "").strip()]

	if faltando:
		raise MdfeInvalido(
			f"o endereço do emitente não tem {', '.join(faltando)} — cadastre no endereço da empresa",
			"emitente",
		)


def _documentos(municipios: list[MunicipioDescarga]) -> tuple[int, int]:
	return (
		sum(len(m.chaves_cte) for m in municipios),
		sum(len(m.chaves_nfe) for m in municipios),
	)


def _validar_carga(dados: DadosMdfe) -> tuple[int, int]:
	if not dados.municipios_descarga:
		raise MdfeInvalido(
			"não há município de descarga: nenhum documento fiscal a manifestar — emita a NF-e da "
			"entrega antes do MDF-e",
			"municipios_descarga",
		)

	for municipio in dados.municipios_descarga:
		if not (municipio.chaves_cte or municipio.chaves_nfe):
			raise MdfeInvalido(
				f"o município de descarga {municipio.nome!r} não tem documento fiscal", "municipios_descarga"
			)

	if dados.valor_carga <= 0:
		raise MdfeInvalido("o valor da carga (vCarga) precisa ser maior que zero", "valor_carga")

	if dados.peso_carga <= 0:
		raise MdfeInvalido("o peso da carga (qCarga) precisa ser maior que zero", "peso_carga")

	return _documentos(dados.municipios_descarga)


def _modal_rodoviario(dados: DadosMdfe) -> dict:
	try:
		conteudo = {"rodo": montar_rodo(dados.rntrc, dados.veiculo_tracao, dados.veiculos_reboque)}
	except RntrcInvalido as e:
		raise MdfeInvalido(f"RNTRC: {e}", "rntrc") from e
	except MdfeRodoviarioInvalido as e:
		raise MdfeInvalido(str(e), "veiculo_tracao") from e

	return montar_infmodal(VERSAO_MODAL, conteudo)


def _identificacao(dados: DadosMdfe, numero: str, codigo_numerico: str) -> IdentificacaoMdfe:
	try:
		uf = codigo_da_uf(str(dados.emitente.endereco.get("UF") or ""))
		codigo_da_uf(dados.uf_inicio)
		codigo_da_uf(dados.uf_fim)
	except UfDesconhecida as e:
		raise MdfeInvalido(f"UF desconhecida: {e}", "uf") from e

	return IdentificacaoMdfe(
		uf=uf,
		tipo_emitente=dados.tipo_emitente,
		serie=dados.serie,
		numero=numero,
		codigo_numerico=codigo_numerico,
		modal=dados.modal,
		emissao=dados.emissao,
		uf_inicio=dados.uf_inicio,
		uf_fim=dados.uf_fim,
		municipios_carrega=dados.municipios_carrega,
		ambiente=dados.ambiente,
	)


def montar_mdfe_de_dados(
	dados: DadosMdfe, numero: str, sortear: Callable[[str], str] = sortear_codigo_numerico
) -> tuple[dict, str]:
	"""A árvore `MDFe` **não assinada** e a chave de acesso de 44 posições.

	O `numero` chega pronto — alocá-lo é da camada que conhece o banco, e esta função não consome
	nada: recusa antes de devolver qualquer árvore. Para alocar **depois** de validar, use
	`montar_mdfe_alocando_numero`. A chave é montada aqui porque `ide/cDV` e o `Id` dependem dela
	e não podem ser informados em paralelo.
	"""
	try:
		numero = validar_numero(numero)
	except NumeracaoInvalida as e:
		raise MdfeInvalido(str(e), "numero") from e

	if dados.emissao.tzinfo is None:
		raise MdfeInvalido(
			"a data de emissão (dhEmi) precisa trazer o fuso horário — o XSD recusa a data sem deslocamento",
			"emissao",
		)

	if dados.modal != MODAL_RODOVIARIO:
		raise MdfeInvalido(
			f"só o modal rodoviário ({MODAL_RODOVIARIO}) está implementado, recebido {dados.modal!r}", "modal"
		)

	_exigir_endereco(dados.emitente)
	emit = montar_emit(dados.emitente)
	cnpj = emit["emit"].get("CNPJ")

	if not cnpj:
		raise MdfeInvalido(
			"a chave de acesso do MDF-e leva o CNPJ do emitente: emitente pessoa física (CPF) não é "
			"suportado por este caminho",
			"cnpj_cpf",
		)

	quantidade_cte, quantidade_nfe = _validar_carga(dados)
	infmodal = _modal_rodoviario(dados)
	infdoc = montar_infdoc(dados.municipios_descarga)
	tot = montar_tot(
		dados.valor_carga,
		dados.unidade_peso,
		dados.peso_carga,
		quantidade_cte=quantidade_cte or None,
		quantidade_nfe=quantidade_nfe or None,
	)

	codigo = sortear(numero)
	identificacao = _identificacao(dados, numero, codigo)

	chave = montar_chave(
		uf=identificacao.uf,
		ano_mes=dados.emissao.strftime("%y%m"),
		cnpj=cnpj,
		modelo="58",
		serie=str(dados.serie),
		numero=numero,
		tipo_emissao=identificacao.tipo_emissao,
		codigo_numerico=codigo,
	)

	infmdfe = montar_infmdfe(montar_ide(identificacao, chave), emit, infmodal, infdoc, tot)

	return montar_mdfe(infmdfe, chave), chave


def montar_mdfe_alocando_numero(
	dados: DadosMdfe, alocar: Callable[[], str], sortear: Callable[[str], str] = sortear_codigo_numerico
) -> tuple[dict, str]:
	"""Como `montar_mdfe_de_dados`, mas o número só é consumido **depois** de tudo validar.

	Mesma razão do CT-e: a numeração fiscal é sequencial, e um número gasto com um manifesto que nem
	chegou a ser montado é um número perdido. A primeira montagem, com `NUMERO_DE_PROVA`, existe só
	para recusar antes de tocar na série; a segunda usa o número de verdade. Se `alocar` falhar, a
	exceção sobe daqui e nenhuma árvore é devolvida.
	"""
	montar_mdfe_de_dados(dados, NUMERO_DE_PROVA, sortear)

	return montar_mdfe_de_dados(dados, alocar(), sortear)
