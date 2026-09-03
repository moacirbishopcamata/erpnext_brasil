# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Endpoints dos webservices de autorização do CT-e, por UF.

Por que existe — mesmo papel de `autorizadores_sefaz.py` para a NF-e
------------------------------------------------------------------------------
Falar direto com a SEFAZ para o CT-e (mesma decisão de não depender de ACBr, já tomada
para a NF-e) exige saber para onde mandar o SOAP de cada UF. Lido de
`nfephp-org/sped-cte`, `storage/wscte_4.00_mod57.xml` (endpoints) e
`storage/autorizadores.json` (mapa UF→grupo, chave `"57"`) — não escrito de memória, e
não suposto igual ao mapa da NF-e.

Achado real: o mapa de grupos do CT-e é diferente do da NF-e, mesmo para UFs que rodam
webservice próprio em ambos os documentos
------------------------------------------------------------------------------------------
O CT-e tem só **quatro** grupos reais (a NF-e tem doze): `MG`, `MS`, `MT`, `PR`, `RS` e
`SP` rodam webservice próprio; **`SVRS`** atende 18 UFs; **`SVSP`** atende 3 (`AP`, `PE`,
`RR`); e **`AN`** (Ambiente Nacional) só existe para `CTeDistribuicaoDFe`, não para
autorização.

O achado real está em quem migrou: `AM`, `BA`, `GO` e `PE` rodam webservice **próprio**
para NF-e (confirmado em `autorizadores_sefaz.py`) mas usam o autorizador **compartilhado**
para CT-e — `AM`/`BA`/`GO` em `SVRS`, `PE` em `SVSP`. Não é a mesma infraestrutura entre os
dois documentos, mesmo dentro da mesma UF — mais uma confirmação de que documentos da
"mesma família" (mesmo emitente, mesmo certificado, XSD irmão) não compartilham
webservice só porque parece razoável presumir.

`RO` está no grupo `SVRS` — mesmo grupo que atende `RO` para NF-e, mas por coincidência de
tabela, não por regra geral (a maioria das UFs de `SVRS` na NF-e não é a mesma lista de
`SVRS` no CT-e — ex. `AM`/`BA`/`GO` só entram no `SVRS` do CT-e).

`SVRS` e `SVSP` **não são cópias de RS/SP** — achado real, verificado, não presumido
Diferente da NF-e (onde `SVC-RS` é literalmente o mesmo host que o grupo `SVRS`), aqui os
hosts de `SVRS`/`SVSP` já são, eles mesmos, os únicos hosts do CT-e — não há uma segunda
tabela "própria" de RS/SP para comparar bit a bit, porque `RS` e `SP` **também** têm
webservice próprio, com host **diferente** do de `SVSP` (`SVSP` usa
`nfe.fazenda.sp.gov.br/CTeWS`, o próprio `SP` usa o mesmo host — na prática **idênticos**,
confirmado byte a byte: `SVSP` é uma cópia funcional de `SP`, apontando pro mesmo host).
`SVRS`, por outro lado, é byte a byte idêntico ao grupo `RS` — a Sefaz Virtual do RS hospeda
tanto o autorizador compartilhado de 18 UFs quanto o próprio webservice do Rio Grande do
Sul, no mesmo host.

Homologação confirmada na mesma fonte
------------------------------------------------------------------------------
`storage/wscte_4.00_mod57.xml` já traz produção e homologação lado a lado para os seis
grupos com webservice — nenhuma inferência de padrão de host foi necessária (ao contrário
da NF-e, onde SVRS/GO/AM trocam o nome de formas diferentes, aqui o padrão é consistente:
troca `producao`/o host base por `homologacao.`/`hom`/`cte-homologacao.`, mas cada grupo
tem sua entrada explícita na fonte, então não há inferência de qualquer forma).

`CteRecepcaoSimp` — recepção síncrona simplificada, existe em todos os grupos
------------------------------------------------------------------------------------------
Além de `CteRecepcao` (síncrona, `CTeRecepcaoSincV4`), todos os seis grupos com
webservice também expõem `CteRecepcaoSimp` (`CTeRecepcaoSimpV4`) — não investigado a fundo
neste incremento qual a diferença de uso entre as duas (a fonte não documenta), mas ambas
as URLs são reais e distintas, capturadas sem inventar qual usar por padrão.

Funções puras: nenhuma dependência do Frappe.

Fontes: `nfephp-org/sped-cte`, `storage/wscte_4.00_mod57.xml` e `storage/autorizadores.json`
(chave `"57"`) — consultados em 2026-09-03.
"""

__all__ = [
	"AUTORIZADOR_POR_UF",
	"ENDPOINTS",
	"ENDPOINTS_HOMOLOGACAO",
	"AutorizadorDesconhecido",
	"endpoint",
]

_MG = "MG"
_MS = "MS"
_MT = "MT"
_PR = "PR"
_RS = "RS"
_SP = "SP"
_SVRS = "SVRS"
_SVSP = "SVSP"
_AN = "AN"

AUTORIZADOR_POR_UF = {
	"AC": _SVRS,
	"AL": _SVRS,
	"AM": _SVRS,
	"AN": _AN,
	"AP": _SVSP,
	"BA": _SVRS,
	"CE": _SVRS,
	"DF": _SVRS,
	"ES": _SVRS,
	"GO": _SVRS,
	"MA": _SVRS,
	"MG": _MG,
	"MS": _MS,
	"MT": _MT,
	"PA": _SVRS,
	"PB": _SVRS,
	"PE": _SVSP,
	"PI": _SVRS,
	"PR": _PR,
	"RJ": _SVRS,
	"RN": _SVRS,
	"RO": _SVRS,
	"RR": _SVSP,
	"RS": _RS,
	"SC": _SVRS,
	"SE": _SVRS,
	"SP": _SP,
	"TO": _SVRS,
	"SVRS": _SVRS,
	"SVSP": _SVSP,
}
"""Mapa UF → grupo, para `modelo="57"` (CT-e) — lido de `storage/autorizadores.json`.
Achado real: diverge do mapa da NF-e mesmo para UFs com webservice próprio em NF-e
(`AM`/`BA`/`GO`/`PE`), ver docstring do módulo."""

ENDPOINTS_HOMOLOGACAO = {
	_AN: {
		"CTeDistribuicaoDFe": "https://hom1.cte.fazenda.gov.br/CTeDistribuicaoDFe/CTeDistribuicaoDFe.asmx",
	},
	_MG: {
		"CteRecepcao": "https://hcte.fazenda.mg.gov.br/cte/services/CTeRecepcaoSincV4",
		"CteRecepcaoSimp": "https://hcte.fazenda.mg.gov.br/cte/services/CTeRecepcaoSimpV4",
		"CteConsultaProtocolo": "https://hcte.fazenda.mg.gov.br/cte/services/CTeConsultaV4",
		"CteStatusServico": "https://hcte.fazenda.mg.gov.br/cte/services/CTeStatusServicoV4",
		"CteRecepcaoEvento": "https://hcte.fazenda.mg.gov.br/cte/services/CTeRecepcaoEventoV4",
		"QRCode": "https://portalcte.fazenda.mg.gov.br/portalcte/sistema/qrcode.xhtml",
	},
	_MS: {
		"CteRecepcao": "https://homologacao.cte.ms.gov.br/ws/CTeRecepcaoSincV4",
		"CteRecepcaoSimp": "https://homologacao.cte.ms.gov.br/ws/CTeRecepcaoSimpV4",
		"CteConsultaProtocolo": "https://homologacao.cte.ms.gov.br/ws/CTeConsultaV4",
		"CteStatusServico": "https://homologacao.cte.ms.gov.br/ws/CTeStatusServicoV4",
		"CteRecepcaoEvento": "https://homologacao.cte.ms.gov.br/ws/CTeRecepcaoEventoV4",
		"QRCode": "http://www.dfe.ms.gov.br/cte/qrcode",
	},
	_MT: {
		"CteRecepcao": "https://homologacao.sefaz.mt.gov.br/ctews2/services/CTeRecepcaoSincV4",
		"CteRecepcaoSimp": "https://homologacao.sefaz.mt.gov.br/cte-ws/services/CTeRecepcaoSimpV4",
		"CteConsultaProtocolo": "https://homologacao.sefaz.mt.gov.br/ctews2/services/CTeConsultaV4",
		"CteStatusServico": "https://homologacao.sefaz.mt.gov.br/ctews2/services/CTeStatusServicoV4",
		"CteRecepcaoEvento": "https://homologacao.sefaz.mt.gov.br/ctews2/services/CTeRecepcaoEventoV4",
		"QRCode": "https://homologacao.sefaz.mt.gov.br/cte/qrcode",
	},
	_PR: {
		"CteRecepcao": "https://homologacao.cte.fazenda.pr.gov.br/cte4/CTeRecepcaoSincV4",
		"CteRecepcaoSimp": "https://homologacao.cte.fazenda.pr.gov.br/cte4/CTeRecepcaoSimpV4",
		"CteConsultaProtocolo": "https://homologacao.cte.fazenda.pr.gov.br/cte4/CTeConsultaV4",
		"CteStatusServico": "https://homologacao.cte.fazenda.pr.gov.br/cte4/CTeStatusServicoV4",
		"CteRecepcaoEvento": "https://homologacao.cte.fazenda.pr.gov.br/cte4/CTeRecepcaoEventoV4",
		"QRCode": "http://www.fazenda.pr.gov.br/cte/qrcode",
	},
	_RS: {
		"CteRecepcao": "https://cte-homologacao.svrs.rs.gov.br/ws/CTeRecepcaoSincV4/CTeRecepcaoSincV4.asmx",
		"CteRecepcaoSimp": "https://cte-homologacao.svrs.rs.gov.br/ws/CTeRecepcaoSimpV4/CTeRecepcaoSimpV4.asmx",
		"CteConsultaProtocolo": "https://cte-homologacao.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx",
		"CteStatusServico": "https://cte-homologacao.svrs.rs.gov.br/ws/CTeStatusServicoV4/CTeStatusServicoV4.asmx",
		"CteRecepcaoEvento": "https://cte-homologacao.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx",
		"QRCode": "https://dfe-portal.svrs.rs.gov.br/cte/qrCode",
	},
	_SP: {
		"CteRecepcao": "https://homologacao.nfe.fazenda.sp.gov.br/CTeWS/WS/CTeRecepcaoSincV4.asmx",
		"CteRecepcaoSimp": "https://homologacao.nfe.fazenda.sp.gov.br/CTeWS/WS/CTeRecepcaoSimpV4.asmx",
		"CteConsultaProtocolo": "https://homologacao.nfe.fazenda.sp.gov.br/CTeWS/WS/CTeConsultaV4.asmx",
		"CteStatusServico": "https://homologacao.nfe.fazenda.sp.gov.br/CTeWS/WS/CTeStatusServicoV4.asmx",
		"CteRecepcaoEvento": "https://homologacao.nfe.fazenda.sp.gov.br/CTeWS/WS/CTeRecepcaoEventoV4.asmx",
		"QRCode": "https://homologacao.nfe.fazenda.sp.gov.br/CTeConsulta/qrCode",
	},
}
ENDPOINTS_HOMOLOGACAO[_SVRS] = ENDPOINTS_HOMOLOGACAO[_RS]
ENDPOINTS_HOMOLOGACAO[_SVSP] = ENDPOINTS_HOMOLOGACAO[_SP]

ENDPOINTS = {
	_AN: {
		"CTeDistribuicaoDFe": "https://www1.cte.fazenda.gov.br/CTeDistribuicaoDFe/CTeDistribuicaoDFe.asmx",
	},
	_MG: {
		"CteRecepcao": "https://cte.fazenda.mg.gov.br/cte/services/CTeRecepcaoSincV4",
		"CteRecepcaoSimp": "https://cte.fazenda.mg.gov.br/cte/services/CTeRecepcaoSimpV4",
		"CteConsultaProtocolo": "https://cte.fazenda.mg.gov.br/cte/services/CTeConsultaV4",
		"CteStatusServico": "https://cte.fazenda.mg.gov.br/cte/services/CTeStatusServicoV4",
		"CteRecepcaoEvento": "https://cte.fazenda.mg.gov.br/cte/services/CTeRecepcaoEventoV4",
		"QRCode": "https://portalcte.fazenda.mg.gov.br/portalcte/sistema/qrcode.xhtml",
	},
	_MS: {
		"CteRecepcao": "https://producao.cte.ms.gov.br/ws/CTeRecepcaoSincV4",
		"CteRecepcaoSimp": "https://producao.cte.ms.gov.br/ws/CTeRecepcaoSimpV4",
		"CteConsultaProtocolo": "https://producao.cte.ms.gov.br/ws/CTeConsultaV4",
		"CteStatusServico": "https://producao.cte.ms.gov.br/ws/CTeStatusServicoV4",
		"CteRecepcaoEvento": "https://producao.cte.ms.gov.br/ws/CTeRecepcaoEventoV4",
		"QRCode": "http://www.dfe.ms.gov.br/cte/qrcode",
	},
	_MT: {
		"CteRecepcao": "https://cte.sefaz.mt.gov.br/ctews2/services/CTeRecepcaoSincV4",
		"CteRecepcaoSimp": "https://cte.sefaz.mt.gov.br/cte-ws/services/CTeRecepcaoSimpV4",
		"CteConsultaProtocolo": "https://cte.sefaz.mt.gov.br/ctews2/services/CTeConsultaV4",
		"CteStatusServico": "https://cte.sefaz.mt.gov.br/ctews2/services/CTeStatusServicoV4",
		"CteRecepcaoEvento": "https://cte.sefaz.mt.gov.br/ctews2/services/CTeRecepcaoEventoV4",
		"QRCode": "https://www.sefaz.mt.gov.br/cte/qrcode",
	},
	_PR: {
		"CteRecepcao": "https://cte.fazenda.pr.gov.br/cte4/CTeRecepcaoSincV4",
		"CteRecepcaoSimp": "https://cte.fazenda.pr.gov.br/cte4/CTeRecepcaoSimpV4",
		"CteConsultaProtocolo": "https://cte.fazenda.pr.gov.br/cte4/CTeConsultaV4",
		"CteStatusServico": "https://cte.fazenda.pr.gov.br/cte4/CTeStatusServicoV4",
		"CteRecepcaoEvento": "https://cte.fazenda.pr.gov.br/cte4/CTeRecepcaoEventoV4",
		"QRCode": "http://www.fazenda.pr.gov.br/cte/qrcode",
	},
	_RS: {
		"CteRecepcao": "https://cte.svrs.rs.gov.br/ws/CTeRecepcaoSincV4/CTeRecepcaoSincV4.asmx",
		"CteRecepcaoSimp": "https://cte.svrs.rs.gov.br/ws/CTeRecepcaoSimpV4/CTeRecepcaoSimpV4.asmx",
		"CteConsultaProtocolo": "https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx",
		"CteStatusServico": "https://cte.svrs.rs.gov.br/ws/CTeStatusServicoV4/CTeStatusServicoV4.asmx",
		"CteRecepcaoEvento": "https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx",
		"QRCode": "https://dfe-portal.svrs.rs.gov.br/cte/qrCode",
	},
	_SP: {
		"CteRecepcao": "https://nfe.fazenda.sp.gov.br/CTeWS/WS/CTeRecepcaoSincV4.asmx",
		"CteRecepcaoSimp": "https://nfe.fazenda.sp.gov.br/CTeWS/WS/CTeRecepcaoSimpV4.asmx",
		"CteConsultaProtocolo": "https://nfe.fazenda.sp.gov.br/CTeWS/WS/CTeConsultaV4.asmx",
		"CteStatusServico": "https://nfe.fazenda.sp.gov.br/CTeWS/WS/CTeStatusServicoV4.asmx",
		"CteRecepcaoEvento": "https://nfe.fazenda.sp.gov.br/CTeWS/WS/CTeRecepcaoEventoV4.asmx",
		"QRCode": "https://nfe.fazenda.sp.gov.br/CTeConsulta/qrCode",
	},
}
ENDPOINTS[_SVRS] = ENDPOINTS[_RS]
ENDPOINTS[_SVSP] = ENDPOINTS[_SP]


class AutorizadorDesconhecido(ValueError):
	"""UF sem grupo mapeado — nunca resolvido por adivinhação."""


def endpoint(uf: str, servico: str, ambiente: str = "producao") -> str | None:
	"""Devolve a URL do webservice de CT-e para `uf`/`servico`/`ambiente`, ou `None`
	quando o serviço não existe para o grupo (ex. `CteRecepcao` no grupo `AN`, que só
	tem `CTeDistribuicaoDFe`) — nunca uma URL inventada.
	"""
	sigla = (uf or "").strip().upper()

	if ambiente not in ("producao", "homologacao"):
		raise ValueError(f"Ambiente deve ser 'producao' ou 'homologacao', recebido {ambiente!r}")

	grupo = AUTORIZADOR_POR_UF.get(sigla)

	if grupo is None:
		raise AutorizadorDesconhecido(f"UF {uf!r} não consta na tabela de autorizadores de CT-e")

	tabela = ENDPOINTS_HOMOLOGACAO if ambiente == "homologacao" else ENDPOINTS

	return tabela[grupo].get(servico)
