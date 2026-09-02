# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Endpoints do webservice de autorização do MDF-e — único, nacional.

Achado real: MDF-e não tem grupos por UF — é um único webservice nacional
------------------------------------------------------------------------------------------
Diferente da NF-e (12 grupos) e do CT-e (4 grupos — ver `autorizadores_cte.py`), o MDF-e
tem **um único** autorizador para as 27 UFs (mais `"AN"`): todas mapeiam para o mesmo
grupo, hospedado na infraestrutura da Sefaz Virtual do RS (`svrs.rs.gov.br`) — confirmado
em `nfephp-org/sped-mdfe`, `storage/autorizadores.json` (chave `"58"`, todas as 27 UFs com
o mesmo valor `"RS"`) e `storage/wsmdfe_3.00.xml` (uma única entrada `<UF><sigla>RS</sigla>`
com todos os serviços). Faz sentido pela própria natureza do documento: o MDF-e representa
uma viagem que tipicamente cruza fronteiras estaduais, então nacionalizar o autorizador
evita a UF de origem do emitente decidir sozinha para onde a informação de uma viagem
interestadual vai.

Por isso este módulo não precisa de um mapa UF→grupo como `autorizadores_sefaz.py`/
`autorizadores_cte.py` — `endpoint()` ignora a UF por completo (aceita o parâmetro só
para manter a mesma assinatura dos módulos irmãos, e por clareza de chamada — quem lê o
código vê que UF nenhuma foi esquecida, foi conscientemente descartada).

Funções puras: nenhuma dependência do Frappe.

Fontes: `nfephp-org/sped-mdfe`, `storage/wsmdfe_3.00.xml` e `storage/autorizadores.json`
(chave `"58"`) — consultados em 2026-09-03.
"""

__all__ = ["ENDPOINTS", "ENDPOINTS_HOMOLOGACAO", "endpoint"]

ENDPOINTS_HOMOLOGACAO = {
	"MDFeRecepcao": "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFerecepcao/MDFeRecepcao.asmx",
	"MDFeRecepcaoSinc": "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeRecepcaoSinc/MDFeRecepcaoSinc.asmx",
	"MDFeRetRecepcao": "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeRetRecepcao/MDFeRetRecepcao.asmx",
	"MDFeRecepcaoEvento": "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeRecepcaoEvento/MDFeRecepcaoEvento.asmx",
	"MDFeConsulta": "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeConsulta/MDFeConsulta.asmx",
	"MDFeStatusServico": "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeStatusServico/MDFeStatusServico.asmx",
	"MDFeConsNaoEnc": "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeConsNaoEnc/MDFeConsNaoEnc.asmx",
	"MDFeDistribuicaoDFe": "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeDistribuicaoDFe/MDFeDistribuicaoDFe.asmx",
}

ENDPOINTS = {
	"MDFeRecepcao": "https://mdfe.svrs.rs.gov.br/ws/MDFeRecepcao/MDFeRecepcao.asmx",
	"MDFeRecepcaoSinc": "https://mdfe.svrs.rs.gov.br/ws/MDFeRecepcaoSinc/MDFeRecepcaoSinc.asmx",
	"MDFeRetRecepcao": "https://mdfe.svrs.rs.gov.br/ws/MDFeRetRecepcao/MDFeRetRecepcao.asmx",
	"MDFeRecepcaoEvento": "https://mdfe.svrs.rs.gov.br/ws/MDFeRecepcaoEvento/MDFeRecepcaoEvento.asmx",
	"MDFeConsulta": "https://mdfe.svrs.rs.gov.br/ws/MDFeConsulta/MDFeConsulta.asmx",
	"MDFeStatusServico": "https://mdfe.svrs.rs.gov.br/ws/MDFeStatusServico/MDFeStatusServico.asmx",
	"MDFeConsNaoEnc": "https://mdfe.svrs.rs.gov.br/ws/MDFeConsNaoEnc/MDFeConsNaoEnc.asmx",
	"MDFeDistribuicaoDFe": "https://mdfe.svrs.rs.gov.br/ws/MDFeDistribuicaoDFe/MDFeDistribuicaoDFe.asmx",
}


def endpoint(uf: str, servico: str, ambiente: str = "producao") -> str | None:
	"""Devolve a URL do webservice de MDF-e para `servico`/`ambiente` — `uf` é
	ignorada por completo (ver docstring do módulo: MDF-e tem um único autorizador
	nacional, não um mapa por UF), mantida como parâmetro só para uniformidade com
	`autorizadores_sefaz.endpoint`/`autorizadores_cte.endpoint`.
	"""
	if ambiente not in ("producao", "homologacao"):
		raise ValueError(f"Ambiente deve ser 'producao' ou 'homologacao', recebido {ambiente!r}")

	tabela = ENDPOINTS_HOMOLOGACAO if ambiente == "homologacao" else ENDPOINTS

	return tabela.get(servico)
