# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Endpoints dos webservices de autorização da NF-e, por UF.

Por que isso existe
--------------------
Falar direto com a SEFAZ — em vez de por ACBrLib ou por um provedor — significa saber
para onde mandar o SOAP de cada UF. A maioria dos estados **não roda webservice
próprio**: delega a um "autorizador" compartilhado. Inventar essa distribuição seria
apostar o documento inteiro numa suposição; por isso ela foi lida do Portal Nacional da
NF-e (`webServices.aspx`), não escrita de memória.

Os três grupos
--------------
- **Webservice próprio** — 10 UFs rodam a própria infraestrutura: AM, BA, GO, MG, MS,
  MT, PE, PR, RS, SP.
- **SVAN** (Sefaz Virtual do Ambiente Nacional) — hoje só **MA**.
- **SVRS** (Sefaz Virtual do Rio Grande do Sul) — as 16 UFs restantes, **incluindo RO**:
  AC, AL, AP, CE, DF, ES, PA, PB, PI, RJ, RN, RO, RR, SC, SE, TO.

RO está no grupo SVRS confirmado na fonte — é o autorizador usado neste app para
Rondônia, prioridade de verificação declarada pelo usuário.

O que **não** está confirmado, e por isso não é adivinhado
------------------------------------------------------------
- **Homologação.** A página lista só produção. Não existe padrão confiável de nome de
  host para derivar homologação (alguns trocam `nfe.` por `homologacao.nfe.`, outros
  não seguem esse padrão) — `endpoint(..., ambiente="homologacao")` levanta
  `NotImplementedError` em vez de arriscar uma URL errada.
- **`NfeConsultaCadastro` para 11 das 16 UFs do grupo SVRS.** A fonte diz explicitamente
  que só AC, ES, RN, PB e SC usam o CadConsultaCadastro do SVRS; as outras 11 — RO
  entre elas — não têm esse serviço confirmado por esta página. `endpoint()` devolve
  `None` para essas combinações, e quem chama precisa decidir o que fazer (a consulta
  de cadastro não é usada na emissão em si).

Funções puras: nenhuma dependência do Frappe.

Fonte: Portal Nacional da NF-e, `webServices.aspx`, consultado em 2026-08-24.
"""

__all__ = [
	"AUTORIZADOR_POR_UF",
	"ENDPOINTS",
	"UFS_COM_CONSULTA_CADASTRO_NO_SVRS",
	"AutorizadorDesconhecido",
	"endpoint",
]

_PROPRIO = "PROPRIO"
_SVAN = "SVAN"
_SVRS = "SVRS"

AUTORIZADOR_POR_UF = {
	# Webservice próprio.
	"AM": _PROPRIO, "BA": _PROPRIO, "GO": _PROPRIO, "MG": _PROPRIO, "MS": _PROPRIO,
	"MT": _PROPRIO, "PE": _PROPRIO, "PR": _PROPRIO, "RS": _PROPRIO, "SP": _PROPRIO,
	# SVAN.
	"MA": _SVAN,
	# SVRS — as 16 restantes. RO está aqui.
	"AC": _SVRS, "AL": _SVRS, "AP": _SVRS, "CE": _SVRS, "DF": _SVRS, "ES": _SVRS,
	"PA": _SVRS, "PB": _SVRS, "PI": _SVRS, "RJ": _SVRS, "RN": _SVRS, "RO": _SVRS,
	"RR": _SVRS, "SC": _SVRS, "SE": _SVRS, "TO": _SVRS,
}  # fmt: skip

# Das 16 UFs do grupo SVRS, só estas usam o CadConsultaCadastro do próprio SVRS.
UFS_COM_CONSULTA_CADASTRO_NO_SVRS = frozenset({"AC", "ES", "RN", "PB", "SC"})

ENDPOINTS = {
	"AM": {
		"NFeAutorizacao": "https://nfe.sefaz.am.gov.br/services2/services/NfeAutorizacao4",
		"NFeRetAutorizacao": "https://nfe.sefaz.am.gov.br/services2/services/NfeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://nfe.sefaz.am.gov.br/services2/services/NfeConsulta4",
		"NfeStatusServico": "https://nfe.sefaz.am.gov.br/services2/services/NfeStatusServico4",
		"NfeConsultaCadastro": "https://nfe.sefaz.am.gov.br/services2/services/CadConsultaCadastro4",
		"NfeInutilizacao": "https://nfe.sefaz.am.gov.br/services2/services/NfeInutilizacao4",
		"RecepcaoEvento": "https://nfe.sefaz.am.gov.br/services2/services/RecepcaoEvento4",
	},
	"BA": {
		"NFeAutorizacao": "https://nfe.sefaz.ba.gov.br/webservices/NFeAutorizacao4/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://nfe.sefaz.ba.gov.br/webservices/NFeRetAutorizacao4/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://nfe.sefaz.ba.gov.br/webservices/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx",
		"NfeStatusServico": "https://nfe.sefaz.ba.gov.br/webservices/NFeStatusServico4/NFeStatusServico4.asmx",
		"NfeConsultaCadastro": "https://nfe.sefaz.ba.gov.br/webservices/CadConsultaCadastro4/CadConsultaCadastro4.asmx",
		"NfeInutilizacao": "https://nfe.sefaz.ba.gov.br/webservices/NFeInutilizacao4/NFeInutilizacao4.asmx",
		"RecepcaoEvento": "https://nfe.sefaz.ba.gov.br/webservices/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx",
	},
	"GO": {
		"NFeAutorizacao": "https://nfe.sefaz.go.gov.br/nfe/services/NFeAutorizacao4?wsdl",
		"NFeRetAutorizacao": "https://nfe.sefaz.go.gov.br/nfe/services/NFeRetAutorizacao4?wsdl",
		"NfeConsultaProtocolo": "https://nfe.sefaz.go.gov.br/nfe/services/NFeConsultaProtocolo4?wsdl",
		"NfeStatusServico": "https://nfe.sefaz.go.gov.br/nfe/services/NFeStatusServico4?wsdl",
		"NfeConsultaCadastro": "https://nfe.sefaz.go.gov.br/nfe/services/CadConsultaCadastro4?wsdl",
		"NfeInutilizacao": "https://nfe.sefaz.go.gov.br/nfe/services/NFeInutilizacao4?wsdl",
		"RecepcaoEvento": "https://nfe.sefaz.go.gov.br/nfe/services/NFeRecepcaoEvento4?wsdl",
	},
	"MG": {
		"NFeAutorizacao": "https://nfe.fazenda.mg.gov.br/nfe2/services/NFeAutorizacao4",
		"NFeRetAutorizacao": "https://nfe.fazenda.mg.gov.br/nfe2/services/NFeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://nfe.fazenda.mg.gov.br/nfe2/services/NFeConsultaProtocolo4",
		"NfeStatusServico": "https://nfe.fazenda.mg.gov.br/nfe2/services/NFeStatusServico4",
		"NfeConsultaCadastro": "https://nfe.fazenda.mg.gov.br/nfe2/services/CadConsultaCadastro4",
		"NfeInutilizacao": "https://nfe.fazenda.mg.gov.br/nfe2/services/NFeInutilizacao4",
		"RecepcaoEvento": "https://nfe.fazenda.mg.gov.br/nfe2/services/NFeRecepcaoEvento4",
	},
	"MS": {
		"NFeAutorizacao": "https://nfe.sefaz.ms.gov.br/ws/NFeAutorizacao4",
		"NFeRetAutorizacao": "https://nfe.sefaz.ms.gov.br/ws/NFeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://nfe.sefaz.ms.gov.br/ws/NFeConsultaProtocolo4",
		"NfeStatusServico": "https://nfe.sefaz.ms.gov.br/ws/NFeStatusServico4",
		"NfeConsultaCadastro": "https://nfe.sefaz.ms.gov.br/ws/CadConsultaCadastro4",
		"NfeInutilizacao": "https://nfe.sefaz.ms.gov.br/ws/NFeInutilizacao4",
		"RecepcaoEvento": "https://nfe.sefaz.ms.gov.br/ws/NFeRecepcaoEvento4",
	},
	"MT": {
		"NFeAutorizacao": "https://nfe.sefaz.mt.gov.br/nfews/v2/services/NfeAutorizacao4?wsdl",
		"NFeRetAutorizacao": "https://nfe.sefaz.mt.gov.br/nfews/v2/services/NfeRetAutorizacao4?wsdl",
		"NfeConsultaProtocolo": "https://nfe.sefaz.mt.gov.br/nfews/v2/services/NfeConsulta4?wsdl",
		"NfeStatusServico": "https://nfe.sefaz.mt.gov.br/nfews/v2/services/NfeStatusServico4?wsdl",
		"NfeConsultaCadastro": "https://nfe.sefaz.mt.gov.br/nfews/v2/services/CadConsultaCadastro4?wsdl",
		"NfeInutilizacao": "https://nfe.sefaz.mt.gov.br/nfews/v2/services/NfeInutilizacao4?wsdl",
		"RecepcaoEvento": "https://nfe.sefaz.mt.gov.br/nfews/v2/services/RecepcaoEvento4?wsdl",
	},
	"PE": {
		"NFeAutorizacao": "https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeAutorizacao4",
		"NFeRetAutorizacao": "https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeConsultaProtocolo4",
		"NfeStatusServico": "https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeStatusServico4",
		"NfeConsultaCadastro": "https://nfe.sefaz.pe.gov.br/nfe-service/services/CadConsultaCadastro4?wsdl",
		"NfeInutilizacao": "https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeInutilizacao4",
		"RecepcaoEvento": "https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeRecepcaoEvento4",
	},
	"PR": {
		"NFeAutorizacao": "https://nfe.sefa.pr.gov.br/nfe/NFeAutorizacao4?wsdl",
		"NFeRetAutorizacao": "https://nfe.sefa.pr.gov.br/nfe/NFeRetAutorizacao4?wsdl",
		"NfeConsultaProtocolo": "https://nfe.sefa.pr.gov.br/nfe/NFeConsultaProtocolo4?wsdl",
		"NfeStatusServico": "https://nfe.sefa.pr.gov.br/nfe/NFeStatusServico4?wsdl",
		"NfeConsultaCadastro": "https://nfe.sefa.pr.gov.br/nfe/CadConsultaCadastro4?wsdl",
		"NfeInutilizacao": "https://nfe.sefa.pr.gov.br/nfe/NFeInutilizacao4?wsdl",
		"RecepcaoEvento": "https://nfe.sefa.pr.gov.br/nfe/NFeRecepcaoEvento4?wsdl",
	},
	"RS": {
		"NFeAutorizacao": "https://nfe.sefazrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://nfe.sefazrs.rs.gov.br/ws/NfeRetAutorizacao/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://nfe.sefazrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx",
		"NfeStatusServico": "https://nfe.sefazrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx",
		"NfeConsultaCadastro": "https://cad.svrs.rs.gov.br/ws/cadconsultacadastro/cadconsultacadastro4.asmx",
		"NfeInutilizacao": "https://nfe.sefazrs.rs.gov.br/ws/nfeinutilizacao/nfeinutilizacao4.asmx",
		"RecepcaoEvento": "https://nfe.sefazrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
	},
	"SP": {
		"NFeAutorizacao": "https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx",
		"NFeRetAutorizacao": "https://nfe.fazenda.sp.gov.br/ws/nferetautorizacao4.asmx",
		"NfeConsultaProtocolo": "https://nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx",
		"NfeStatusServico": "https://nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx",
		"NfeConsultaCadastro": "https://nfe.fazenda.sp.gov.br/ws/cadconsultacadastro4.asmx",
		"NfeInutilizacao": "https://nfe.fazenda.sp.gov.br/ws/nfeinutilizacao4.asmx",
		"RecepcaoEvento": "https://nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx",
	},
	_SVAN: {
		"NFeAutorizacao": "https://www.sefazvirtual.fazenda.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://www.sefazvirtual.fazenda.gov.br/NFeRetAutorizacao4/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx",
		"NfeStatusServico": "https://www.sefazvirtual.fazenda.gov.br/NFeStatusServico4/NFeStatusServico4.asmx",
		"NfeInutilizacao": "https://www.sefazvirtual.fazenda.gov.br/NFeInutilizacao4/NFeInutilizacao4.asmx",
		"RecepcaoEvento": "https://www.sefazvirtual.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx",
		# CadConsultaCadastro não consta para o grupo SVAN nesta fonte.
	},
	_SVRS: {
		"NFeAutorizacao": "https://nfe.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://nfe.svrs.rs.gov.br/ws/NfeRetAutorizacao/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://nfe.svrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx",
		"NfeStatusServico": "https://nfe.svrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx",
		"NfeInutilizacao": "https://www.sefazvirtual.fazenda.gov.br/NFeInutilizacao4/NFeInutilizacao4.asmx",
		"RecepcaoEvento": "https://www.nfe.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx",
		# Confirmado só para AC/ES/RN/PB/SC — ver UFS_COM_CONSULTA_CADASTRO_NO_SVRS.
		"NfeConsultaCadastro": "https://cad.svrs.rs.gov.br/ws/cadconsultacadastro/cadconsultacadastro4.asmx",
	},
}


class AutorizadorDesconhecido(ValueError):
	def __init__(self, mensagem: str):
		super().__init__(mensagem)


def endpoint(uf: str, servico: str, ambiente: str = "producao") -> str | None:
	"""Devolve a URL do webservice, ou `None` quando o serviço não está confirmado
	para a combinação UF/grupo (nunca uma URL inventada).

	`ambiente="homologacao"` levanta `NotImplementedError`: a fonte usada só lista
	produção, e não existe padrão de host confiável para derivar homologação.
	"""
	sigla = (uf or "").strip().upper()

	if ambiente == "homologacao":
		raise NotImplementedError(
			"Endpoints de homologação não estão confirmados nesta tabela — "
			"precisam ser levantados UF a UF antes de uso, não derivados por padrão de nome"
		)

	if ambiente != "producao":
		raise ValueError(f"Ambiente deve ser 'producao' ou 'homologacao', recebido {ambiente!r}")

	grupo = AUTORIZADOR_POR_UF.get(sigla)

	if grupo is None:
		raise AutorizadorDesconhecido(f"UF {uf!r} não consta na tabela de autorizadores")

	chave = grupo if grupo in (_SVAN, _SVRS) else sigla

	if grupo == _SVRS and servico == "NfeConsultaCadastro" and sigla not in UFS_COM_CONSULTA_CADASTRO_NO_SVRS:
		return None

	return ENDPOINTS[chave].get(servico)
