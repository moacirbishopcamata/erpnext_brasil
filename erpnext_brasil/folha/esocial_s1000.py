# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""eSocial S-1000 (evtInfoEmpregador): Informações do Empregador/Contribuinte/Órgão Público.

A peça de configuração que faltava antes do S-1010 fazer sentido
------------------------------------------------------------------------
`docs/rh-estado-esocial.md` registrava este evento como pendência desde a
implementação do S-1010 ("a peça de configuração que faltava para o S-1200 fazer
sentido" citava o S-1010 supondo o cadastro do empregador já feito — mas o próprio
cadastro do empregador nunca tinha sido modelado). O S-1000 é logicamente anterior a
qualquer outro evento do empregador: é o que declara a classificação tributária do
contribuinte perante o eSocial, ponto de partida de todo o resto.

`ideEvento` deste evento é o mais simples de todos já modelados (achado real)
--------------------------------------------------------------------------------------------
Lido diretamente em `tipos.xsd` (`T_ideEvento_exclusao` — o nome do tipo vem de ter
sido introduzido para eventos com semântica de operação, não de "este evento é uma
exclusão"): só `tpAmb`/`procEmi`/`verProc`, **sem** `indRetif`/`nrRecibo`. Isso faz
sentido pela mesma razão do S-1010: eventos de tabela não têm "retificação" no
sentido do S-2200/S-1200 — a correção é uma nova operação `alteracao`/`exclusao`
sobre o período de validade, não uma re-emissão do mesmo evento. Por isso este
módulo não reaproveita `esocial_s1010.IdeRubrica` nem cria paralelo a
`esocial_s2200.IdeEvento` (que tem `indRetif`) — é genuinamente mais simples.

A operação (`inclusao`/`alteracao`/`exclusao`) é um `xs:choice` real no XSD
------------------------------------------------------------------------------------
Confirmado diretamente (`evtInfoEmpregador.xsd`): as três operações são mutuamente
exclusivas, cada uma com seu próprio `idePeriodo` (`T_idePeriodo`: `iniValid`
obrigatório, `fimValid` opcional, ambos "AAAA-MM"). Só `inclusao`/`alteracao`
carregam `infoCadastro`; `exclusao` é só `idePeriodo`. Modelado como três funções de
montagem separadas (`montar_inclusao`/`montar_alteracao`/`montar_exclusao`), mesma
disciplina de não forçar uma função genérica sobre um `choice` real do domínio.

O que este módulo cobre, e o que fica de fora
--------------------------------------------------
Cobre `ideEmpregador` (`tpInsc`/`nrInsc`) e os campos de `infoCadastro` mais comuns:
`classTrib` (Tabela 08, código de 2 dígitos, formato livre — catálogo RFB não
verificado, mesma decisão já tomada para os "código+valor" da ECF), `indCoop`,
`indConstr`, `indDesFolha`, `indOpcCP`, `indPorte`, `indOptRegEletron`, `cnpjEFR`,
`dtTrans11096`, `indTribFolhaPisPasep`, `indPertIRRF` — todos com enumeração literal
confirmada no XSD (exceto `classTrib`, que é só um padrão de 2 dígitos sem tabela
enumerada na definição do tipo). Fora de escopo, deliberadamente:

- **`dadosIsencao`** — grupo condicional só para `classTrib=80` (entidades imunes/
  isentas), com CEBAS/portaria/lei de concessão — regime raro, tabela de dados
  próprios que este projeto não tem cadastro para preencher.
- **`novaValidade`** (alteração do próprio período de validade dentro de uma
  `alteracao`) — variante rara do fluxo de alteração, mesma decisão já tomada para o
  campo homônimo do S-1010.
- **`infoOrgInternacional`** — exclusivo de organismos internacionais/instituições
  extraterritoriais (natureza jurídica grupo [5]), fora do domínio deste projeto.
- As regras de dependência cruzada citadas no XSD (ex.: `indCoop` só pode ser
  diferente de 0 se a natureza jurídica for 214-3; `cnpjEFR` obrigatório só para
  Administração Pública) não são verificadas aqui — dependem da tabela de natureza
  jurídica do declarante (`Company.br_natureza_juridica`, já modelado para a ECF),
  cruzamento que fica para a camada de integração, não para a função pura de
  montagem.

Fonte do XSD: mesma família já usada no resto do bloco eSocial
------------------------------------------------------------------------
`github.com/nfephp-org/sped-esocial`, `schemes/v_S_01_03_00/evtInfoEmpregador.xsd` e
`tipos.xsd` — não a fonte primária oficial, mesma advertência já registrada para os
outros módulos.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass

__all__ = [
	"INDICADOR_CONSTRUTORA_NAO",
	"INDICADOR_CONSTRUTORA_SIM",
	"INDICADOR_COOPERATIVA_NAO",
	"INDICADOR_COOPERATIVA_OUTRAS",
	"INDICADOR_COOPERATIVA_PRODUCAO",
	"INDICADOR_COOPERATIVA_TRABALHO",
	"INDICADOR_DESONERACAO_EMPRESA",
	"INDICADOR_DESONERACAO_MUNICIPIO",
	"INDICADOR_DESONERACAO_NAO_APLICAVEL",
	"TIPO_INSCRICAO_CNPJ",
	"TIPO_INSCRICAO_CPF",
	"EsocialS1000Invalido",
	"IdeEmpregador",
	"IdeEvento",
	"IdePeriodo",
	"InfoCadastro",
]

TIPO_INSCRICAO_CNPJ = 1
TIPO_INSCRICAO_CPF = 2

# indCoop — enumeração literal do XSD (TS_indCoop).
INDICADOR_COOPERATIVA_NAO = 0
INDICADOR_COOPERATIVA_TRABALHO = 1
INDICADOR_COOPERATIVA_PRODUCAO = 2
INDICADOR_COOPERATIVA_OUTRAS = 3

_INDICADORES_COOPERATIVA_VALIDOS = frozenset({0, 1, 2, 3})

# indConstr — enumeração literal do XSD (TS_indConstr).
INDICADOR_CONSTRUTORA_NAO = 0
INDICADOR_CONSTRUTORA_SIM = 1

_INDICADORES_CONSTRUTORA_VALIDOS = frozenset({0, 1})

# indDesFolha — enumeração literal do XSD (evtInfoEmpregador.xsd, campo local).
INDICADOR_DESONERACAO_NAO_APLICAVEL = 0
INDICADOR_DESONERACAO_EMPRESA = 1
INDICADOR_DESONERACAO_MUNICIPIO = 2

_INDICADORES_DESONERACAO_VALIDOS = frozenset({0, 1, 2})


class EsocialS1000Invalido(ValueError):
	"""Dado que impede a montagem do evento — campo fora do padrão do XSD."""


@dataclass(frozen=True)
class IdeEvento:
	"""`ideEvento` do S-1000 (`T_ideEvento_exclusao`, lido em `tipos.xsd`) — só
	`tpAmb`/`procEmi`/`verProc`, sem `indRetif`/`nrRecibo` (ver docstring do
	módulo). `tp_amb` restrito a produção/produção restrita, mesmo recorte já
	aplicado nos demais eventos deste projeto (exclui o valor 7, uso interno)."""

	tp_amb: int
	proc_emi: int
	ver_proc: str

	def __post_init__(self):
		if self.tp_amb not in (1, 2):
			raise EsocialS1000Invalido(
				f"tpAmb deve ser 1 (produção) ou 2 (produção restrita), recebido {self.tp_amb}"
			)

		if not (0 <= self.proc_emi <= 9):
			raise EsocialS1000Invalido(f"procEmi deve ser um dígito único (0-9), recebido {self.proc_emi}")

		if not (1 <= len(self.ver_proc) <= 20):
			raise EsocialS1000Invalido(
				f"verProc deve ter entre 1 e 20 caracteres, recebido {self.ver_proc!r}"
			)


@dataclass(frozen=True)
class IdeEmpregador:
	"""`ideEmpregador` — identifica o contribuinte pelo tipo/número de inscrição."""

	tp_insc: int
	nr_insc: str

	def __post_init__(self):
		if self.tp_insc not in (TIPO_INSCRICAO_CNPJ, TIPO_INSCRICAO_CPF):
			raise EsocialS1000Invalido(f"tpInsc deve ser 1 (CNPJ) ou 2 (CPF), recebido {self.tp_insc}")

		if not self.nr_insc:
			raise EsocialS1000Invalido("nrInsc não pode ser vazio")


@dataclass(frozen=True)
class IdePeriodo:
	"""`T_idePeriodo` — período de validade das informações, "AAAA-MM"."""

	ini_valid: str
	fim_valid: str | None = None

	def __post_init__(self):
		if len(self.ini_valid) != 7:
			raise EsocialS1000Invalido(
				f"iniValid deve ter 7 caracteres (formato AAAA-MM), recebido {self.ini_valid!r}"
			)

		if self.fim_valid is not None and len(self.fim_valid) != 7:
			raise EsocialS1000Invalido(
				f"fimValid deve ter 7 caracteres (formato AAAA-MM), recebido {self.fim_valid!r}"
			)


@dataclass(frozen=True)
class InfoCadastro:
	"""`infoCadastro` — detalhamento das informações do empregador.

	`classTrib` é aceito como código de 2 dígitos sem validar contra a Tabela 08
	da RFB (catálogo não verificado) — mesma decisão já tomada para os registros
	"código+valor" da ECF. As regras de dependência cruzada com a natureza
	jurídica do declarante (ex.: `indCoop` só pode ser não-zero para natureza
	214-3) não são verificadas aqui — ver docstring do módulo."""

	class_trib: str
	ind_des_folha: int
	ind_opt_reg_eletron: int
	ind_coop: int | None = None
	ind_constr: int | None = None
	ind_opc_cp: int | None = None
	ind_porte: str | None = None
	cnpj_efr: str | None = None
	dt_trans_11096: str | None = None
	ind_trib_folha_pis_pasep: str | None = None
	ind_pert_irrf: str | None = None

	def __post_init__(self):
		if len(self.class_trib) != 2 or not self.class_trib.isdigit():
			raise EsocialS1000Invalido(f"classTrib deve ter 2 dígitos, recebido {self.class_trib!r}")

		if self.ind_des_folha not in _INDICADORES_DESONERACAO_VALIDOS:
			raise EsocialS1000Invalido(f"indDesFolha deve ser 0, 1 ou 2, recebido {self.ind_des_folha}")

		if self.ind_opt_reg_eletron not in (0, 1):
			raise EsocialS1000Invalido(
				f"indOptRegEletron deve ser 0 ou 1, recebido {self.ind_opt_reg_eletron}"
			)

		if self.ind_coop is not None and self.ind_coop not in _INDICADORES_COOPERATIVA_VALIDOS:
			raise EsocialS1000Invalido(f"indCoop deve ser 0, 1, 2 ou 3, recebido {self.ind_coop}")

		if self.ind_constr is not None and self.ind_constr not in _INDICADORES_CONSTRUTORA_VALIDOS:
			raise EsocialS1000Invalido(f"indConstr deve ser 0 ou 1, recebido {self.ind_constr}")

		if self.ind_opc_cp is not None and self.ind_opc_cp not in (1, 2):
			raise EsocialS1000Invalido(f"indOpcCP deve ser 1 ou 2, recebido {self.ind_opc_cp}")

		if self.ind_porte is not None and self.ind_porte != "S":
			raise EsocialS1000Invalido(
				f"indPorte só aceita 'S' quando preenchido, recebido {self.ind_porte!r}"
			)

		if self.cnpj_efr is not None and len(self.cnpj_efr) != 14:
			raise EsocialS1000Invalido(f"cnpjEFR deve ter 14 caracteres, recebido {self.cnpj_efr!r}")

		if self.ind_trib_folha_pis_pasep is not None and self.ind_trib_folha_pis_pasep != "S":
			raise EsocialS1000Invalido(
				f"indTribFolhaPisPasep só aceita 'S' quando preenchido, recebido {self.ind_trib_folha_pis_pasep!r}"
			)

		if self.ind_pert_irrf is not None and self.ind_pert_irrf != "S":
			raise EsocialS1000Invalido(
				f"indPertIRRF só aceita 'S' quando preenchido, recebido {self.ind_pert_irrf!r}"
			)


def montar_inclusao(ide_periodo: IdePeriodo, info_cadastro: InfoCadastro | None = None) -> dict:
	"""Monta o grupo `inclusao` — `infoCadastro` opcional no XSD, mas na prática
	sempre presente numa inclusão real (só é opcional para permitir o caso raro
	de `procEmi=8`, fora de escopo deste projeto)."""

	corpo: dict = {"idePeriodo": {"iniValid": ide_periodo.ini_valid}}
	if ide_periodo.fim_valid is not None:
		corpo["idePeriodo"]["fimValid"] = ide_periodo.fim_valid
	if info_cadastro is not None:
		corpo["infoCadastro"] = _montar_info_cadastro(info_cadastro)
	return {"inclusao": corpo}


def montar_alteracao(
	ide_periodo: IdePeriodo,
	info_cadastro: InfoCadastro | None = None,
	nova_validade: IdePeriodo | None = None,
) -> dict:
	"""Monta o grupo `alteracao` — `novaValidade` deliberadamente fora de escopo
	na função de conveniência, mas aceito quando o chamador o fornece."""

	corpo: dict = {"idePeriodo": {"iniValid": ide_periodo.ini_valid}}
	if ide_periodo.fim_valid is not None:
		corpo["idePeriodo"]["fimValid"] = ide_periodo.fim_valid
	if info_cadastro is not None:
		corpo["infoCadastro"] = _montar_info_cadastro(info_cadastro)
	if nova_validade is not None:
		nova: dict = {"iniValid": nova_validade.ini_valid}
		if nova_validade.fim_valid is not None:
			nova["fimValid"] = nova_validade.fim_valid
		corpo["novaValidade"] = nova
	return {"alteracao": corpo}


def montar_exclusao(ide_periodo: IdePeriodo) -> dict:
	"""Monta o grupo `exclusao` — só `idePeriodo`, sem `infoCadastro` (o XSD não
	permite: a exclusão remove o registro do período indicado, não o substitui)."""

	corpo: dict = {"idePeriodo": {"iniValid": ide_periodo.ini_valid}}
	if ide_periodo.fim_valid is not None:
		corpo["idePeriodo"]["fimValid"] = ide_periodo.fim_valid
	return {"exclusao": corpo}


def _montar_info_cadastro(info_cadastro: InfoCadastro) -> dict:
	corpo: dict = {"classTrib": info_cadastro.class_trib}
	if info_cadastro.ind_coop is not None:
		corpo["indCoop"] = info_cadastro.ind_coop
	if info_cadastro.ind_constr is not None:
		corpo["indConstr"] = info_cadastro.ind_constr
	corpo["indDesFolha"] = info_cadastro.ind_des_folha
	if info_cadastro.ind_opc_cp is not None:
		corpo["indOpcCP"] = info_cadastro.ind_opc_cp
	if info_cadastro.ind_porte is not None:
		corpo["indPorte"] = info_cadastro.ind_porte
	corpo["indOptRegEletron"] = info_cadastro.ind_opt_reg_eletron
	if info_cadastro.cnpj_efr is not None:
		corpo["cnpjEFR"] = info_cadastro.cnpj_efr
	if info_cadastro.dt_trans_11096 is not None:
		corpo["dtTrans11096"] = info_cadastro.dt_trans_11096
	if info_cadastro.ind_trib_folha_pis_pasep is not None:
		corpo["indTribFolhaPisPasep"] = info_cadastro.ind_trib_folha_pis_pasep
	if info_cadastro.ind_pert_irrf is not None:
		corpo["indPertIRRF"] = info_cadastro.ind_pert_irrf
	return corpo


def montar_evento_s1000(
	id_evento: str,
	ide_evento: IdeEvento,
	ide_empregador: IdeEmpregador,
	info_empregador: dict,
) -> dict:
	"""Monta o evento `evtInfoEmpregador` completo — `info_empregador` é o dict
	produzido por `montar_inclusao`/`montar_alteracao`/`montar_exclusao` (o
	`xs:choice` real do XSD, ver docstring do módulo)."""

	return {
		"eSocial": {
			"evtInfoEmpregador": {
				"Id": id_evento,
				"ideEvento": {
					"tpAmb": ide_evento.tp_amb,
					"procEmi": ide_evento.proc_emi,
					"verProc": ide_evento.ver_proc,
				},
				"ideEmpregador": {
					"tpInsc": ide_empregador.tp_insc,
					"nrInsc": ide_empregador.nr_insc,
				},
				"infoEmpregador": info_empregador,
			}
		}
	}
