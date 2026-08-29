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

Homologação — confirmada para os três grupos
------------------------------------------------
O Portal Nacional lista apenas produção. A homologação (SVRS e, depois, os outros 11
grupos: própria UF × 10 + SVAN) foi confirmada numa segunda fonte independente: a tabela
de configuração da `nfephp-org/sped-nfe` (`storage/wsnfe_4.00_mod55.xml`), a biblioteca
PHP mais usada no Brasil para isso. Essa tabela também **reproduz exatamente** os
endpoints de produção já extraídos do Portal para todos os grupos conferidos — o que dá
confiança na correção do arquivo, não só na sua popularidade. PR e SP tiveram uma
terceira checagem, direto na página oficial de cada estado
(`sped.fazenda.pr.gov.br`, `fazenda.sp.gov.br`), e bateram campo a campo.

Não existe padrão confiável de nome de host entre grupos — SVRS troca `nfe.` por
`nfe-homologacao.`, GO usa host completamente diferente (`homolog.sefaz.go.gov.br` vs.
`nfe.sefaz.go.gov.br`), AM usa `homnfe.` (sem hífen nem "homologacao" por extenso) — é
por isso que os 12 grupos foram confirmados um a um, nunca por inferência de padrão de
nome. `NfeConsultaCadastro` de AM e SVAN ficou de fora da homologação de propósito: a
mesma fonte lista o elemento do serviço mas sem nenhuma URL dentro dele, tanto em
homologação quanto em produção — ausência real na fonte, não esquecimento.

- **`NfeConsultaCadastro` para 11 das 16 UFs do grupo SVRS.** A fonte diz explicitamente
  que só AC, ES, RN, PB e SC usam o CadConsultaCadastro do SVRS; as outras 11 — RO
  entre elas — não têm esse serviço confirmado por esta página. `endpoint()` devolve
  `None` para essas combinações, e quem chama precisa decidir o que fazer (a consulta
  de cadastro não é usada na emissão em si).

Funções puras: nenhuma dependência do Frappe.

Fontes: Portal Nacional da NF-e, `webServices.aspx` (produção, todas as UFs) — consultado
em 2026-08-24; `nfephp-org/sped-nfe`, `storage/wsnfe_4.00_mod55.xml` (homologação dos 12
grupos, e confirmação cruzada da produção) e as páginas oficiais de PR e SP (terceira
checagem) — consultados em 2026-08-29.
"""

__all__ = [
	"AUTORIZADOR_POR_UF",
	"ENDPOINTS",
	"ENDPOINTS_HOMOLOGACAO",
	"OPERACAO_SOAP",
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

# Homologação: os 11 grupos que faltavam (própria UF × 10 + SVAN) foram confirmados
# depois — mesma fonte de corroboração já usada para SVRS (`nfephp-org/sped-nfe`,
# `storage/wsnfe_4.00_mod55.xml`), com PR e SP checados de novo contra a página oficial
# de cada estado (`sped.fazenda.pr.gov.br`, `fazenda.sp.gov.br`) e batendo exatamente —
# a mesma dupla verificação que já tinha dado confiança ao SVRS. `NfeConsultaCadastro`
# de AM e SVAN ficou de fora de propósito: a mesma fonte lista o elemento mas sem URL
# nele, em homologação e produção — ausência real na fonte, não esquecimento.
ENDPOINTS_HOMOLOGACAO = {
	"AM": {
		"NFeAutorizacao": "https://homnfe.sefaz.am.gov.br/services2/services/NfeAutorizacao4",
		"NFeRetAutorizacao": "https://homnfe.sefaz.am.gov.br/services2/services/NfeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://homnfe.sefaz.am.gov.br/services2/services/NfeConsulta4",
		"NfeStatusServico": "https://homnfe.sefaz.am.gov.br/services2/services/NfeStatusServico4",
		"NfeInutilizacao": "https://homnfe.sefaz.am.gov.br/services2/services/NfeInutilizacao4",
		"RecepcaoEvento": "https://homnfe.sefaz.am.gov.br/services2/services/RecepcaoEvento4",
	},
	"BA": {
		"NFeAutorizacao": "https://hnfe.sefaz.ba.gov.br/webservices/NFeAutorizacao4/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://hnfe.sefaz.ba.gov.br/webservices/NFeRetAutorizacao4/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://hnfe.sefaz.ba.gov.br/webservices/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx",
		"NfeStatusServico": "https://hnfe.sefaz.ba.gov.br/webservices/NFeStatusServico4/NFeStatusServico4.asmx",
		"NfeConsultaCadastro": "https://hnfe.sefaz.ba.gov.br/webservices/CadConsultaCadastro4/CadConsultaCadastro4.asmx",
		"NfeInutilizacao": "https://hnfe.sefaz.ba.gov.br/webservices/NFeInutilizacao4/NFeInutilizacao4.asmx",
		"RecepcaoEvento": "https://hnfe.sefaz.ba.gov.br/webservices/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx",
	},
	"GO": {
		"NFeAutorizacao": "https://homolog.sefaz.go.gov.br/nfe/services/NFeAutorizacao4",
		"NFeRetAutorizacao": "https://homolog.sefaz.go.gov.br/nfe/services/NFeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://homolog.sefaz.go.gov.br/nfe/services/NFeConsultaProtocolo4",
		"NfeStatusServico": "https://homolog.sefaz.go.gov.br/nfe/services/NFeStatusServico4",
		"NfeConsultaCadastro": "https://homolog.sefaz.go.gov.br/nfe/services/CadConsultaCadastro4",
		"NfeInutilizacao": "https://homolog.sefaz.go.gov.br/nfe/services/NFeInutilizacao4",
		"RecepcaoEvento": "https://homolog.sefaz.go.gov.br/nfe/services/NFeRecepcaoEvento4",
	},
	"MG": {
		"NFeAutorizacao": "https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeAutorizacao4",
		"NFeRetAutorizacao": "https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeConsultaProtocolo4",
		"NfeStatusServico": "https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeStatusServico4",
		"NfeConsultaCadastro": "https://hnfe.fazenda.mg.gov.br/nfe2/services/CadConsultaCadastro4",
		"NfeInutilizacao": "https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeInutilizacao4",
		"RecepcaoEvento": "https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeRecepcaoEvento4",
	},
	"MS": {
		"NFeAutorizacao": "https://hom.nfe.sefaz.ms.gov.br/ws/NFeAutorizacao4",
		"NFeRetAutorizacao": "https://hom.nfe.sefaz.ms.gov.br/ws/NFeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://hom.nfe.sefaz.ms.gov.br/ws/NFeConsultaProtocolo4",
		"NfeStatusServico": "https://hom.nfe.sefaz.ms.gov.br/ws/NFeStatusServico4",
		"NfeConsultaCadastro": "https://hom.nfe.sefaz.ms.gov.br/ws/CadConsultaCadastro4",
		"NfeInutilizacao": "https://hom.nfe.sefaz.ms.gov.br/ws/NFeInutilizacao4",
		"RecepcaoEvento": "https://hom.nfe.sefaz.ms.gov.br/ws/NFeRecepcaoEvento4",
	},
	"MT": {
		"NFeAutorizacao": "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NfeAutorizacao4",
		"NFeRetAutorizacao": "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NfeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NfeConsulta4",
		"NfeStatusServico": "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NfeStatusServico4",
		"NfeConsultaCadastro": "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/CadConsultaCadastro4",
		"NfeInutilizacao": "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NfeInutilizacao4",
		"RecepcaoEvento": "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/RecepcaoEvento4",
	},
	"PE": {
		"NFeAutorizacao": "https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeAutorizacao4",
		"NFeRetAutorizacao": "https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeConsultaProtocolo4",
		"NfeStatusServico": "https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeStatusServico4",
		"NfeConsultaCadastro": "https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/CadConsultaCadastro4",
		"NfeInutilizacao": "https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeInutilizacao4",
		"RecepcaoEvento": "https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeRecepcaoEvento4",
	},
	# PR conferido de novo contra sped.fazenda.pr.gov.br (página oficial "Endereços dos
	# ambientes de homologação e produção — Versão 4.00") — bateu campo a campo.
	"PR": {
		"NFeAutorizacao": "https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeAutorizacao4?wsdl",
		"NFeRetAutorizacao": "https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeRetAutorizacao4?wsdl",
		"NfeConsultaProtocolo": "https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeConsultaProtocolo4?wsdl",
		"NfeStatusServico": "https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeStatusServico4?wsdl",
		"NfeConsultaCadastro": "https://homologacao.nfe.sefa.pr.gov.br/nfe/CadConsultaCadastro4?wsdl",
		"NfeInutilizacao": "https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeInutilizacao4?wsdl",
		"RecepcaoEvento": "https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeRecepcaoEvento4?wsdl",
	},
	"RS": {
		"NFeAutorizacao": "https://nfe-homologacao.sefazrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://nfe-homologacao.sefazrs.rs.gov.br/ws/NfeRetAutorizacao/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://nfe-homologacao.sefazrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx",
		"NfeStatusServico": "https://nfe-homologacao.sefazrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx",
		"NfeConsultaCadastro": "https://cad.svrs.rs.gov.br/ws/cadconsultacadastro/cadconsultacadastro4.asmx",
		"NfeInutilizacao": "https://nfe-homologacao.sefazrs.rs.gov.br/ws/nfeinutilizacao/nfeinutilizacao4.asmx",
		"RecepcaoEvento": "https://nfe-homologacao.sefazrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
	},
	# SP conferido de novo contra fazenda.sp.gov.br/nfe/url_webservices.asp — bateu.
	"SP": {
		"NFeAutorizacao": "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx",
		"NFeRetAutorizacao": "https://homologacao.nfe.fazenda.sp.gov.br/ws/nferetautorizacao4.asmx",
		"NfeConsultaProtocolo": "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx",
		"NfeStatusServico": "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx",
		"NfeConsultaCadastro": "https://homologacao.nfe.fazenda.sp.gov.br/ws/cadconsultacadastro4.asmx",
		"NfeInutilizacao": "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeinutilizacao4.asmx",
		"RecepcaoEvento": "https://homologacao.nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx",
	},
	_SVAN: {
		"NFeAutorizacao": "https://hom.sefazvirtual.fazenda.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://hom.sefazvirtual.fazenda.gov.br/NFeRetAutorizacao4/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://hom.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx",
		"NfeStatusServico": "https://hom.sefazvirtual.fazenda.gov.br/NFeStatusServico4/NFeStatusServico4.asmx",
		"NfeInutilizacao": "https://hom.sefazvirtual.fazenda.gov.br/NFeInutilizacao4/NFeInutilizacao4.asmx",
		"RecepcaoEvento": "https://hom.sefazvirtual.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx",
	},
	_SVRS: {
		"NFeAutorizacao": "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeRetAutorizacao/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx",
		"NfeStatusServico": "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx",
		"NfeInutilizacao": "https://nfe-homologacao.svrs.rs.gov.br/ws/nfeinutilizacao/nfeinutilizacao4.asmx",
		"RecepcaoEvento": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
		"NfeConsultaCadastro": "https://cad-homologacao.svrs.rs.gov.br/ws/cadconsultacadastro/cadconsultacadastro4.asmx",
	},
}

# Operação SOAP de cada serviço — usada para montar o namespace de `nfeDadosMsg`
# (`http://www.portalfiscal.inf.br/nfe/wsdl/<operacao>`). Confirmado em
# `nfephp-org/sped-nfe`, `storage/wsnfe_4.00_mod55.xml` (atributo `operation`).
OPERACAO_SOAP = {
	"NFeAutorizacao": "NFeAutorizacao4",
	"NFeRetAutorizacao": "NFeRetAutorizacao4",
	"NfeConsultaProtocolo": "NFeConsultaProtocolo4",
	"NfeStatusServico": "NFeStatusServico4",
	"NfeInutilizacao": "NFeInutilizacao4",
	# Versão 1.00, não 4.00: é a versão do schema do evento, não do layout da NF-e.
	"RecepcaoEvento": "NFeRecepcaoEvento4",
	"NfeConsultaCadastro": "CadConsultaCadastro4",
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

	if ambiente not in ("producao", "homologacao"):
		raise ValueError(f"Ambiente deve ser 'producao' ou 'homologacao', recebido {ambiente!r}")

	grupo = AUTORIZADOR_POR_UF.get(sigla)

	if grupo is None:
		raise AutorizadorDesconhecido(f"UF {uf!r} não consta na tabela de autorizadores")

	if (
		grupo == _SVRS
		and servico == "NfeConsultaCadastro"
		and sigla not in UFS_COM_CONSULTA_CADASTRO_NO_SVRS
	):
		return None

	chave = grupo if grupo in (_SVAN, _SVRS) else sigla

	if ambiente == "homologacao":
		if chave not in ENDPOINTS_HOMOLOGACAO:
			raise NotImplementedError(
				f"Homologação não está confirmada para o grupo {chave!r} nesta tabela — "
				"precisa ser levantada antes de uso, não derivada por padrão de nome"
			)

		return ENDPOINTS_HOMOLOGACAO[chave].get(servico)

	return ENDPOINTS[chave].get(servico)
