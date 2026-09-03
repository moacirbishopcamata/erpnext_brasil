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

`urlChave`: consulta por chave, tabela própria (22 de 27 UFs confirmadas)
------------------------------------------------------------------------------
A URL de consulta por chave (`urlChave` do XML, distinta do QR Code — para RO,
`www.nfce.sefin.ro.gov.br`, só o domínio, sem o caminho `/consultanfce/consulta.jsp`
que a URL do QR Code tem: infraestruturas realmente distintas, mesmo quando a mesma UF
aparece nas duas) tem tabela própria: **fonte oficial do ENCAT**
("Desenvolvedor" → "URL por UF utilizada para consulta chave",
`nfce.encat.org/desenvolvedor/url-por-uf-utilizada-para-consulta-chave/`) — o mesmo
recurso que a rejeição 878 ("Endereço do site da UF da Consulta por chave de acesso
diverge do previsto") referencia como fonte de verdade, confirmado via busca cruzada
independente ao investigar essa rejeição.

**22 das 27 UFs confirmadas em produção**; Ceará só tem homologação confirmada na
própria fonte (não erro de leitura — a tabela do ENCAT genuinamente não lista produção
para CE); Goiás, Minas Gerais, Pernambuco e Santa Catarina **não aparecem na tabela do
ENCAT em nenhum ambiente** — ausência real na fonte primária deste dado, não
esquecimento nem falha de busca. `url_chave()` levanta erro explícito para essas
combinações em vez de inventar ou reaproveitar a URL do QR Code (que é uma
infraestrutura diferente, ver acima).

Funções puras: nenhuma dependência do Frappe.
"""

__all__ = ["URL_CHAVE_POR_UF", "URL_QRCODE_POR_UF", "UfDesconhecida", "url_chave", "url_qrcode"]


class UfDesconhecida(ValueError):
	"""Reaproveitada por `url_qrcode` e `url_chave` — cada uma indexa numa tabela
	diferente (infraestruturas distintas, ver docstring do módulo), mas o erro de "UF
	nem sequer confirmada nesta tabela" é o mesmo tipo de problema nas duas."""

	def __init__(self, uf: str, tabela: str = "consulta da NFC-e"):
		super().__init__(f"UF {uf!r} não consta na tabela de {tabela}")


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


# Consulta por chave (`urlChave`), por UF — fonte: ENCAT, "URL por UF utilizada para
# consulta chave" (nfce.encat.org/desenvolvedor/url-por-uf-utilizada-para-consulta-chave/),
# consultado em 2026-08-30. GO, MG, PE, SC ausentes de propósito (não constam na fonte,
# nenhum ambiente); CE só tem homologação confirmada — ver docstring do módulo.
URL_CHAVE_POR_UF = {
	"AC": {
		"producao": "http://www.sefaznet.ac.gov.br/nfce/consulta",
		"homologacao": "http://hml.sefaznet.ac.gov.br/nfce/consulta",
	},
	"AL": {
		"producao": "http://nfce.sefaz.al.gov.br/consultaNFCe.htm",
		"homologacao": "http://nfce.sefaz.al.gov.br/consultaNFCe.htm",
	},
	"AP": {
		"producao": "https://www.sefaz.ap.gov.br/sate/seg/SEGf_AcessarFuncao.jsp?cdFuncao=FIS_1261",
		"homologacao": "https://www.sefaz.ap.gov.br/sate1/seg/SEGf_AcessarFuncao.jsp?cdFuncao=FIS_1261",
	},
	"AM": {
		"producao": "https://sistemas.sefaz.am.gov.br/nfceweb/formConsulta.do",
		"homologacao": "http://homnfce.sefaz.am.gov.br/nfceweb/formConsulta.do",
	},
	"BA": {
		"producao": "https://nfe.sefaz.ba.gov.br/servicos/nfce/default.aspx",
		"homologacao": "http://hnfe.sefaz.ba.gov.br/servicos/nfce/default.aspx",
	},
	"CE": {"homologacao": "http://nfceh.sefaz.ce.gov.br/pages/consultaNota.jsf"},
	"DF": {
		"producao": "http://dec.fazenda.df.gov.br/NFCE/",
		"homologacao": "http://dec.fazenda.df.gov.br/NFCE/",
	},
	"ES": {
		"producao": "http://app.sefaz.es.gov.br/ConsultaNFCe",
		"homologacao": "http://homologacao.sefaz.es.gov.br/ConsultaNFCe",
	},
	"MA": {
		"producao": "http://www.nfce.sefaz.ma.gov.br/portal/consultaNFe.do?method=preFilterCupom&",
		"homologacao": "http://www.hom.nfce.sefaz.ma.gov.br/portal/consultarNFCe.jsp",
	},
	"MT": {
		"producao": "http://www.sefaz.mt.gov.br/nfce/consultanfce",
		"homologacao": "http://homologacao.sefaz.mt.gov.br/nfce/consultanfce",
	},
	"MS": {"producao": "http://www.dfe.ms.gov.br/nfce", "homologacao": "http://www.dfe.ms.gov.br/nfce"},
	"PA": {
		"producao": "https://appnfc.sefa.pa.gov.br/portal/view/consultas/nfce/consultanfce.seam",
		"homologacao": "https://appnfc.sefa.pa.gov.br/portal-homologacao/view/consultas/nfce/consultanfce.seam",
	},
	"PB": {
		"producao": "https://www.receita.pb.gov.br/nfce",
		"homologacao": "http://www.receita.pb.gov.br/nfcehom",
	},
	"PR": {"producao": "http://www.fazenda.pr.gov.br", "homologacao": "http://www.fazenda.pr.gov.br"},
	"PI": {
		"producao": "http://webas.sefaz.pi.gov.br/nfceweb/consultarNFCe.jsf",
		"homologacao": "http://webas.sefaz.pi.gov.br/nfceweb-homologacao/consultarNFCe.jsf",
	},
	"RJ": {
		"producao": "https://www.nfce.fazenda.rj.gov.br/consulta",
		"homologacao": "https://www.nfce.fazenda.rj.gov.br/consulta",
	},
	"RN": {
		"producao": "http://nfce.set.rn.gov.br/consultarNFCe.aspx",
		"homologacao": "http://nfce.set.rn.gov.br/consultarNFCe.aspx",
	},
	"RS": {
		"producao": "https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx",
		"homologacao": "https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx",
	},
	"RO": {"producao": "http://www.nfce.sefin.ro.gov.br", "homologacao": "http://www.nfce.sefin.ro.gov.br"},
	"RR": {
		"producao": "https://www.sefaz.rr.gov.br/nfce/servlet/wp_consulta_nfce",
		"homologacao": "http://200.174.88.103:8080/nfce/servlet/wp_consulta_nfce",
	},
	"SP": {
		"producao": "https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica",
		"homologacao": "https://www.homologacao.nfce.fazenda.sp.gov.br/NFCeConsultaPublica",
	},
	"SE": {
		"producao": "http://www.nfce.se.gov.br/portal/portalNoticias.jsp",
		"homologacao": "http://www.hom.nfe.se.gov.br/portal/portalNoticias.jsp",
	},
	"TO": {
		"producao": "http://apps.sefaz.to.gov.br/portal-nfce/consultarNFCe.jsf",
		"homologacao": "http://apps.sefaz.to.gov.br/portal-nfce-homologacao/consultarNFCe.jsf",
	},
	# GO, MG, PE, SC deliberadamente ausentes — não constam na fonte ENCAT.
}


def url_chave(uf: str, ambiente: str = "producao") -> str:
	"""Devolve a URL de consulta por chave de acesso (`urlChave` do XML da NFC-e).

	Levanta `UfDesconhecida` para UF fora da tabela inteira (nunca confirmada em nenhum
	ambiente — GO, MG, PE, SC hoje) e `NotImplementedError` para UF conhecida mas sem
	este ambiente específico confirmado (CE em produção) — nunca reaproveita a URL do
	QR Code como substituto, porque é infraestrutura diferente (ver docstring do
	módulo).
	"""
	sigla = (uf or "").strip().upper()

	if ambiente not in ("producao", "homologacao"):
		raise ValueError(f"Ambiente deve ser 'producao' ou 'homologacao', recebido {ambiente!r}")

	if sigla not in URL_CHAVE_POR_UF:
		raise UfDesconhecida(uf, "consulta por chave da NFC-e")

	tabela = URL_CHAVE_POR_UF[sigla]

	if ambiente not in tabela:
		raise NotImplementedError(
			f"URL de consulta por chave não confirmada para {sigla!r} em ambiente {ambiente!r} "
			"— não é para inferir da URL do QR Code, é infraestrutura diferente"
		)

	return tabela[ambiente]


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
		raise UfDesconhecida(uf, "consulta de QR Code da NFC-e")

	return URL_QRCODE_POR_UF[sigla][ambiente]
