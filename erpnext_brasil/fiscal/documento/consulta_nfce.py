# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""URL de consulta do QR Code da NFC-e, por UF.

Por que é uma tabela separada de `autorizadores_sefaz.py`
------------------------------------------------------------
A consulta do QR Code (`webConsultaNFCe`) é uma **página pública**, sem autenticação,
para o consumidor conferir a nota pelo celular — infraestrutura completamente diferente
dos webservices SOAP de autorização já mapeados em `autorizadores_sefaz.py`. Prova disso:
cada uma das 27 UFs mantém sua **própria** página de consulta, mesmo as que delegam a
autorização ao SVRS (RO, por exemplo, autoriza via SVRS mas consulta o QR Code em
`nfce.sefin.ro.gov.br`, domínio próprio) — não há como derivar uma tabela pela outra.

Confirmado em duas fontes independentes para RO (prioridade de verificação deste
projeto): a tabela de configuração de `nfephp-org/sped-nfe`
(`storage/wsnfe_4.00_mod65.xml`) e a Cartilha de Orientações NFC-e da própria
SEFIN-RO — batem exatamente
(`http://www.nfce.sefin.ro.gov.br/consultanfce/consulta.jsp`). As demais 26 UFs vêm só
da primeira fonte — mesmo padrão de confiança já usado para os autorizadores de
NF-e (a tabela reproduziu exatamente o que já estava confirmado antes, o que dá
confiança na correção do arquivo como um todo).

O que este módulo NÃO resolve
----------------------------------
`urlChave` (a URL de consulta por chave, distinta do QR Code — para RO,
`www.sefin.ro.gov.br/nfce/consulta`, domínio e caminho diferentes do QR Code) não tem
tabela própria aqui: só foi confirmada para RO. `qrcode_nfce.montar_infnfesupl` continua
recebendo `url_consulta_chave` como parâmetro de quem chama — automatizar isso para as
27 UFs é trabalho futuro declarado, não coberto por este módulo.

Funções puras: nenhuma dependência do Frappe.
"""

__all__ = ["URL_QRCODE_POR_UF", "UfDesconhecida", "url_qrcode"]


class UfDesconhecida(ValueError):
	def __init__(self, uf: str):
		super().__init__(f"UF {uf!r} não consta na tabela de consulta de QR Code da NFC-e")


# Produção e homologação, por UF. Confirmado em `nfephp-org/sped-nfe`,
# `storage/wsnfe_4.00_mod65.xml` — RO cross-verificado contra a Cartilha de Orientações
# NFC-e da SEFIN-RO (bate exatamente). Consultado em 2026-08-29.
URL_QRCODE_POR_UF = {
	"AC": {
		"producao": "http://www.sefaznet.ac.gov.br/nfce/qrcode",
		"homologacao": "http://www.hml.sefaznet.ac.gov.br/nfce/qrcode",
	},
	"AL": {
		"producao": "http://nfce.sefaz.al.gov.br/QRCode/consultarNFCe.jsp",
		"homologacao": "http://nfce.sefaz.al.gov.br/QRCode/consultarNFCe.jsp",
	},
	"AM": {
		"producao": "https://sistemas.sefaz.am.gov.br/nfceweb/consultarNFCe.jsp",
		"homologacao": "https://sistemas.sefaz.am.gov.br/nfceweb-hom/consultarNFCe.jsp",
	},
	"AP": {
		"producao": "https://www.sefaz.ap.gov.br/nfce/nfcep.php",
		"homologacao": "https://www.sefaz.ap.gov.br/nfcehml/nfce.php",
	},
	"BA": {
		"producao": "http://nfe.sefaz.ba.gov.br/servicos/nfce/qrcode.aspx",
		"homologacao": "http://hnfe.sefaz.ba.gov.br/servicos/nfce/qrcode.aspx",
	},
	"CE": {
		"producao": "http://nfce.sefaz.ce.gov.br/pages/ShowNFCe.html",
		"homologacao": "http://nfceh.sefaz.ce.gov.br/pages/ShowNFCe.html",
	},
	"DF": {
		"producao": "http://www.fazenda.df.gov.br/nfce/qrcode",
		"homologacao": "http://dec.fazenda.df.gov.br/ConsultarNFCe.aspx",
	},
	"ES": {
		"producao": "http://app.sefaz.es.gov.br/ConsultaNFCe/qrcode.aspx",
		"homologacao": "http://homologacao.sefaz.es.gov.br/ConsultaNFCe/qrcode.aspx",
	},
	"GO": {
		"producao": "https://nfeweb.sefaz.go.gov.br/nfeweb/sites/nfce/danfeNFCe",
		"homologacao": "https://nfewebhomolog.sefaz.go.gov.br/nfeweb/sites/nfce/danfeNFCe",
	},
	"MA": {
		"producao": "http://www.nfce.sefaz.ma.gov.br/portal/consultarNFCe.jsp",
		"homologacao": "http://www.hom.nfce.sefaz.ma.gov.br/portal/consultarNFCe.jsp",
	},
	"MG": {
		"producao": "https://portalsped.fazenda.mg.gov.br/portalnfce/sistema/qrcode.xhtml",
		"homologacao": "https://portalsped.fazenda.mg.gov.br/portalnfce/sistema/qrcode.xhtml",
	},
	"MS": {
		"producao": "http://www.dfe.ms.gov.br/nfce/qrcode",
		"homologacao": "http://www.dfe.ms.gov.br/nfce/qrcode",
	},
	"MT": {
		"producao": "http://www.sefaz.mt.gov.br/nfce/consultanfce",
		"homologacao": "http://homologacao.sefaz.mt.gov.br/nfce/consultanfce",
	},
	"PA": {
		"producao": "https://appnfc.sefa.pa.gov.br/portal/view/consultas/nfce/nfceForm.seam",
		"homologacao": "https://appnfc.sefa.pa.gov.br/portal-homologacao/view/consultas/nfce/nfceForm.seam",
	},
	"PB": {
		"producao": "http://www.sefaz.pb.gov.br/nfce",
		"homologacao": "http://www.sefaz.pb.gov.br/nfcehom",
	},
	"PE": {
		"producao": "http://nfce.sefaz.pe.gov.br/nfce/consulta",
		"homologacao": "http://nfcehomolog.sefaz.pe.gov.br/nfce/consulta",
	},
	"PI": {
		"producao": "http://www.sefaz.pi.gov.br/nfce/qrcode",
		"homologacao": "http://www.sefaz.pi.gov.br/nfce/qrcode",
	},
	"PR": {
		"producao": "http://www.fazenda.pr.gov.br/nfce/qrcode",
		"homologacao": "http://www.fazenda.pr.gov.br/nfce/qrcode",
	},
	"RJ": {
		"producao": "https://consultadfe.fazenda.rj.gov.br/consultaNFCe/QRCode",
		"homologacao": "http://www4.fazenda.rj.gov.br/consultaNFCe/QRCode",
	},
	"RN": {
		"producao": "http://nfce.set.rn.gov.br/consultarNFCe.aspx",
		"homologacao": "http://hom.nfce.set.rn.gov.br/consultarNFCe.aspx",
	},
	# Confirmado contra a Cartilha de Orientações NFC-e da própria SEFIN-RO (segunda
	# fonte independente) — mesma URL em produção e homologação.
	"RO": {
		"producao": "http://www.nfce.sefin.ro.gov.br/consultanfce/consulta.jsp",
		"homologacao": "http://www.nfce.sefin.ro.gov.br/consultanfce/consulta.jsp",
	},
	"RR": {
		"producao": "https://www.sefaz.rr.gov.br/servlet/qrcode",
		"homologacao": "http://200.174.88.103:8080/nfce/servlet/qrcode",
	},
	"RS": {
		"producao": "https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx",
		"homologacao": "https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx",
	},
	"SC": {
		"producao": "https://sat.sef.sc.gov.br/nfce/consulta",
		"homologacao": "https://hom.sat.sef.sc.gov.br/nfce/consulta",
	},
	"SE": {
		"producao": "http://www.nfce.se.gov.br/nfce/qrcode",
		"homologacao": "http://www.hom.nfe.se.gov.br/nfce/qrcode",
	},
	"SP": {
		"producao": "https://www.nfce.fazenda.sp.gov.br/qrcode",
		"homologacao": "https://www.homologacao.nfce.fazenda.sp.gov.br/qrcode",
	},
	"TO": {
		"producao": "http://www.sefaz.to.gov.br/nfce/qrcode",
		"homologacao": "http://homologacao.sefaz.to.gov.br/nfce/qrcode",
	},
}


def url_qrcode(uf: str, ambiente: str = "producao") -> str:
	"""Devolve a URL base de consulta do QR Code para a UF e o ambiente.

	`ambiente` é `"producao"` ou `"homologacao"` — mesma convenção do resto do app
	(`autorizadores_sefaz.endpoint`). Levanta `UfDesconhecida` para UF fora da tabela e
	`ValueError` para ambiente inválido — nunca devolve `None` nem inventa host, porque
	a URL do QR Code impressa numa nota real não tem "modo degradado".
	"""
	sigla = (uf or "").strip().upper()

	if ambiente not in ("producao", "homologacao"):
		raise ValueError(f"Ambiente deve ser 'producao' ou 'homologacao', recebido {ambiente!r}")

	if sigla not in URL_QRCODE_POR_UF:
		raise UfDesconhecida(uf)

	return URL_QRCODE_POR_UF[sigla][ambiente]
