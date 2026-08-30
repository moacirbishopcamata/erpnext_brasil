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

NFC-e (modelo 65) não é a mesma infraestrutura que NF-e, na maioria dos grupos
------------------------------------------------------------------------------------
Descoberto ao verificar o QR Code da NFC-e: a maioria dos grupos com webservice próprio
(AM, GO, MG, MS, MT, PR, RS, SP) e o **próprio SVRS** — o grupo de RO — rodam a NFC-e em
**host separado** da NF-e (tipicamente subdomínio `nfce.` em vez de `nfe.`; RO/SVRS:
`nfce.svrs.rs.gov.br`, não `nfe.svrs.rs.gov.br`). Usar o endpoint de NF-e para transmitir
uma NFC-e nesses grupos manda a requisição para o host errado.

Confirmado na mesma fonte já usada para o resto da tabela
(`storage/wsnfe_4.00_mod65.xml`, o arquivo de configuração específico de NFC-e da mesma
biblioteca) — reproduzido em `ENDPOINTS_NFCE`/`ENDPOINTS_NFCE_HOMOLOGACAO`, com `modelo`
como parâmetro novo de `endpoint()` (default `"55"`, compatível com todo código existente
que não passa esse argumento).

**BA, PE e o grupo SVAN (MA) não têm bloco próprio no arquivo de configuração de NFC-e** —
ausência confirmada, não esquecimento: esses três reúsam o mesmo endpoint de NF-e para os
dois modelos (não têm infraestrutura separada). `endpoint(..., modelo="65")` cai para a
tabela de NF-e automaticamente nesses casos, sem precisar de entrada duplicada.

Contingência SVC-AN/SVC-RS — exclusiva de NF-e (modelo 55), nunca de NFC-e
--------------------------------------------------------------------------
Quando a SEFAZ autorizadora do próprio estado está fora do ar mas o emitente tem
internet, a NF-e pode ser emitida via um dos dois "Sistemas Virtuais de Contingência"
nacionais: **SVC-AN** (`tpEmis=6`, Ambiente Nacional, hospedado em `sefazvirtual.
fazenda.gov.br`) ou **SVC-RS** (`tpEmis=7`, hospedado na própria infraestrutura do RS).
Confirmado que **isso não existe para NFC-e**: a contingência de NFC-e é sempre offline
(`tpEmis=9`, ver `qrcode_nfce.py`), exceto em SP, que exige SAT/EPEC-NFCe — não há SVC de
NFC-e em lugar nenhum. Isso resolve, ao contrário do que a implementação do QR Code havia
deixado como pendência (`docs/nfce-qrcode.md`), que a premissa de "diferença de
transporte de contingência para NFC-e" estava errada: não existe SVC para modelo 65, o
transporte de NFC-e não muda por contingência (o documento é que muda, `tpEmis=9`).

`SVC-RS` é a mesma infraestrutura física do grupo `SVRS` — confirmado byte a byte, os
seis serviços têm URL idêntica em produção e homologação — não coincidência: a
Sefaz Virtual do RS hospeda tanto o autorizador compartilhado de 16 UFs (`SVRS`) quanto o
serviço nacional de contingência (`SVC-RS`), então `ENDPOINTS[_SVCRS]` é literalmente
`ENDPOINTS[_SVRS]` (mesmo dict, não cópia). `SVC-AN` roda em host de fato separado
(`sefazvirtual.fazenda.gov.br`) e tem tabela própria.

Qual UF cai em qual SVC não é escolha livre do emitente — é fixo por UF (a fonte lista
qual "serviço atende" cada estado). As 19 UFs de `SVC-AN` são as 16 do grupo `SVRS` mais
MG, RS e SP (três dos dez estados com webservice próprio) — faz sentido: uma UF não pode
cair de volta na própria infraestrutura que já usa como autorizador principal. As 8 UFs
de `SVC-RS` são os sete estados com webservice próprio restantes (AM, BA, GO, MS, MT, PE,
PR) mais o único integrante do grupo SVAN (MA). 19 + 8 = 27, sem sobreposição — a mesma
checagem de consistência interna que corrobora a tabela de homologação, aplicada aqui.

**Fonte secundária, não o Portal Nacional** (inacessível às ferramentas de busca no
momento): `nfephp-org/sped-nfe`'s `docs/Contingency.md`, texto explicativo (não tabela de
configuração de máquina) — dizendo isso explicitamente porque é o mesmo padrão de
transparência de fonte usado no resto deste módulo. A consistência interna (27 UFs,
zero sobreposição, e os endpoints SVC-AN/SVC-RS batendo exatamente com o padrão de nome
dos outros grupos) é o que dá confiança, não uma segunda fonte independente para a lista
UF→grupo especificamente — reconferir se houver dúvida antes de operar em contingência.

Funções puras: nenhuma dependência do Frappe.

Fontes: Portal Nacional da NF-e, `webServices.aspx` (produção, todas as UFs) — consultado
em 2026-08-24; `nfephp-org/sped-nfe`, `storage/wsnfe_4.00_mod55.xml` (homologação dos 12
grupos, e confirmação cruzada da produção), `storage/wsnfe_4.00_mod65.xml` (endpoints
próprios de NFC-e) e as páginas oficiais de PR e SP (terceira checagem) — consultados
em 2026-08-29; `docs/Contingency.md` (endpoints e mapa UF→SVC-AN/SVC-RS) — consultado em
2026-08-29.
"""

__all__ = [
	"AUTORIZADOR_POR_UF",
	"ENDPOINTS",
	"ENDPOINTS_HOMOLOGACAO",
	"ENDPOINTS_NFCE",
	"ENDPOINTS_NFCE_HOMOLOGACAO",
	"OPERACAO_SOAP",
	"UF_CONTINGENCIA_SVC",
	"UFS_COM_CONSULTA_CADASTRO_NO_SVRS",
	"AutorizadorDesconhecido",
	"endpoint",
]

_PROPRIO = "PROPRIO"
_SVAN = "SVAN"
_SVRS = "SVRS"
_SVCAN = "SVCAN"
_SVCRS = "SVCRS"

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

# Qual SVC (Sistema Virtual de Contingência nacional) cada UF usa quando a própria
# autorizadora está fora do ar — só para NF-e (modelo 55), ver docstring do módulo.
# Fonte: nfephp-org/sped-nfe, docs/Contingency.md.
UF_CONTINGENCIA_SVC = {
	# SVC-AN: as 16 UFs do grupo SVRS + 3 dos 10 estados com webservice próprio.
	"AC": _SVCAN, "AL": _SVCAN, "AP": _SVCAN, "CE": _SVCAN, "DF": _SVCAN, "ES": _SVCAN,
	"MG": _SVCAN, "PA": _SVCAN, "PB": _SVCAN, "PI": _SVCAN, "RJ": _SVCAN, "RN": _SVCAN,
	"RO": _SVCAN, "RR": _SVCAN, "RS": _SVCAN, "SC": _SVCAN, "SE": _SVCAN, "SP": _SVCAN,
	"TO": _SVCAN,
	# SVC-RS: os 7 estados restantes com webservice próprio + a única UF do grupo SVAN.
	"AM": _SVCRS, "BA": _SVCRS, "GO": _SVCRS, "MA": _SVCRS, "MS": _SVCRS, "MT": _SVCRS,
	"PE": _SVCRS, "PR": _SVCRS,
}  # fmt: skip

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
	_SVCAN: {
		"NFeAutorizacao": "https://www.sefazvirtual.fazenda.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://www.sefazvirtual.fazenda.gov.br/NFeRetAutorizacao4/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx",
		"NfeStatusServico": "https://www.sefazvirtual.fazenda.gov.br/NFeStatusServico4/NFeStatusServico4.asmx",
		"NfeInutilizacao": "https://www.sefazvirtual.fazenda.gov.br/NFeInutilizacao4/NFeInutilizacao4.asmx",
		"RecepcaoEvento": "https://www.sefazvirtual.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx",
		# CadConsultaCadastro não consta para SVC-AN nesta fonte — mesma ausência do SVAN.
	},
}

# SVC-RS é a mesma infraestrutura física do SVRS — confirmado byte a byte, os seis
# serviços têm URL idêntica em produção e homologação (ver docstring do módulo). Mesmo
# dict, não cópia: se a URL do SVRS mudar, o SVC-RS muda junto, porque é o mesmo host.
ENDPOINTS[_SVCRS] = ENDPOINTS[_SVRS]

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
	_SVCAN: {
		"NFeAutorizacao": "https://hom.sefazvirtual.fazenda.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://hom.sefazvirtual.fazenda.gov.br/NFeRetAutorizacao4/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://hom.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx",
		"NfeStatusServico": "https://hom.sefazvirtual.fazenda.gov.br/NFeStatusServico4/NFeStatusServico4.asmx",
		"NfeInutilizacao": "https://hom.sefazvirtual.fazenda.gov.br/NFeInutilizacao4/NFeInutilizacao4.asmx",
		"RecepcaoEvento": "https://hom.sefazvirtual.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx",
	},
}

# Mesmo motivo do bloco de produção: SVC-RS é literalmente a infraestrutura do SVRS.
ENDPOINTS_HOMOLOGACAO[_SVCRS] = ENDPOINTS_HOMOLOGACAO[_SVRS]

# Endpoints próprios de NFC-e (modelo 65) — só os grupos que têm host separado de NF-e,
# confirmados em `storage/wsnfe_4.00_mod65.xml`. BA, PE e SVAN não aparecem aqui de
# propósito: não têm bloco próprio nessa fonte, reúsam o endpoint de NF-e (ver docstring
# do módulo). `NfeConsultaCadastro` não consta — é serviço de consulta cadastral,
# agnóstico a modelo de documento, resolvido sempre pela tabela de NF-e.
ENDPOINTS_NFCE = {
	"AM": {
		"NFeAutorizacao": "https://nfce.sefaz.am.gov.br/nfce-services/services/NfeAutorizacao4",
		"NFeRetAutorizacao": "https://nfce.sefaz.am.gov.br/nfce-services/services/NfeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://nfce.sefaz.am.gov.br/nfce-services/services/NfeConsulta4",
		"NfeStatusServico": "https://nfce.sefaz.am.gov.br/nfce-services/services/NfeStatusServico4",
		"NfeInutilizacao": "https://nfce.sefaz.am.gov.br/nfce-services/services/NfeInutilizacao4",
		"RecepcaoEvento": "https://nfce.sefaz.am.gov.br/nfce-services/services/RecepcaoEvento4",
	},
	# GO usa o mesmo host/caminho da NF-e (não separou infraestrutura por modelo) — só
	# sem o sufixo "?wsdl" que a tabela de NF-e tem, confirmado byte a byte na fonte.
	"GO": {
		"NFeAutorizacao": "https://nfe.sefaz.go.gov.br/nfe/services/NFeAutorizacao4",
		"NFeRetAutorizacao": "https://nfe.sefaz.go.gov.br/nfe/services/NFeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://nfe.sefaz.go.gov.br/nfe/services/NFeConsultaProtocolo4",
		"NfeStatusServico": "https://nfe.sefaz.go.gov.br/nfe/services/NFeStatusServico4",
		"NfeInutilizacao": "https://nfe.sefaz.go.gov.br/nfe/services/NFeInutilizacao4",
		"RecepcaoEvento": "https://nfe.sefaz.go.gov.br/nfe/services/NFeRecepcaoEvento4",
	},
	"MG": {
		"NFeAutorizacao": "https://nfce.fazenda.mg.gov.br/nfce/services/NFeAutorizacao4",
		"NFeRetAutorizacao": "https://nfce.fazenda.mg.gov.br/nfce/services/NFeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://nfce.fazenda.mg.gov.br/nfce/services/NFeConsultaProtocolo4",
		"NfeStatusServico": "https://nfce.fazenda.mg.gov.br/nfce/services/NFeStatusServico4",
		"NfeInutilizacao": "https://nfce.fazenda.mg.gov.br/nfce/services/NFeInutilizacao4",
		"RecepcaoEvento": "https://nfce.fazenda.mg.gov.br/nfce/services/NFeRecepcaoEvento4",
	},
	"MS": {
		"NFeAutorizacao": "https://nfce.sefaz.ms.gov.br/ws/NFeAutorizacao4",
		"NFeRetAutorizacao": "https://nfce.sefaz.ms.gov.br/ws/NFeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://nfce.sefaz.ms.gov.br/ws/NFeConsultaProtocolo4",
		"NfeStatusServico": "https://nfce.sefaz.ms.gov.br/ws/NFeStatusServico4",
		"NfeInutilizacao": "https://nfce.sefaz.ms.gov.br/ws/NFeInutilizacao4",
		"RecepcaoEvento": "https://nfce.sefaz.ms.gov.br/ws/NFeRecepcaoEvento4",
	},
	"MT": {
		"NFeAutorizacao": "https://nfce.sefaz.mt.gov.br/nfcews/services/NfeAutorizacao4",
		"NFeRetAutorizacao": "https://nfce.sefaz.mt.gov.br/nfcews/services/NfeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://nfce.sefaz.mt.gov.br/nfcews/services/NfeConsulta4",
		"NfeStatusServico": "https://nfce.sefaz.mt.gov.br/nfcews/services/NfeStatusServico4",
		"NfeInutilizacao": "https://nfce.sefaz.mt.gov.br/nfcews/services/NfeInutilizacao4",
		"RecepcaoEvento": "https://nfce.sefaz.mt.gov.br/nfcews/services/RecepcaoEvento4",
	},
	"PR": {
		"NFeAutorizacao": "https://nfce.sefa.pr.gov.br/nfce/NFeAutorizacao4",
		"NFeRetAutorizacao": "https://nfce.sefa.pr.gov.br/nfce/NFeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://nfce.sefa.pr.gov.br/nfce/NFeConsultaProtocolo4",
		"NfeStatusServico": "https://nfce.sefa.pr.gov.br/nfce/NFeStatusServico4",
		"NfeInutilizacao": "https://nfce.sefa.pr.gov.br/nfce/NFeInutilizacao4",
		"RecepcaoEvento": "https://nfce.sefa.pr.gov.br/nfce/NFeRecepcaoEvento4",
	},
	"RS": {
		"NFeAutorizacao": "https://nfce.sefazrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://nfce.sefazrs.rs.gov.br/ws/NfeRetAutorizacao/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://nfce.sefazrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx",
		"NfeStatusServico": "https://nfce.sefazrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx",
		"NfeInutilizacao": "https://nfce.sefazrs.rs.gov.br/ws/nfeinutilizacao/nfeinutilizacao4.asmx",
		"RecepcaoEvento": "https://nfce.sefazrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
	},
	"SP": {
		"NFeAutorizacao": "https://nfce.fazenda.sp.gov.br/ws/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://nfce.fazenda.sp.gov.br/ws/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://nfce.fazenda.sp.gov.br/ws/NFeConsultaProtocolo4.asmx",
		"NfeStatusServico": "https://nfce.fazenda.sp.gov.br/ws/NFeStatusServico4.asmx",
		"NfeInutilizacao": "https://nfce.fazenda.sp.gov.br/ws/NFeInutilizacao4.asmx",
		"RecepcaoEvento": "https://nfce.fazenda.sp.gov.br/ws/NFeRecepcaoEvento4.asmx",
	},
	# SVRS — o grupo de RO. Confirma a suspeita que motivou levantar esta tabela: host
	# `nfce.svrs.rs.gov.br`, diferente de `nfe.svrs.rs.gov.br` usado para NF-e.
	_SVRS: {
		"NFeAutorizacao": "https://nfce.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://nfce.svrs.rs.gov.br/ws/NfeRetAutorizacao/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://nfce.svrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx",
		"NfeStatusServico": "https://nfce.svrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx",
		"NfeInutilizacao": "https://nfce.svrs.rs.gov.br/ws/nfeinutilizacao/nfeinutilizacao4.asmx",
		"RecepcaoEvento": "https://nfce.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
	},
}

ENDPOINTS_NFCE_HOMOLOGACAO = {
	"AM": {
		"NFeAutorizacao": "https://homnfce.sefaz.am.gov.br/nfce-services/services/NfeAutorizacao4",
		"NFeRetAutorizacao": "https://homnfce.sefaz.am.gov.br/nfce-services/services/NfeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://homnfce.sefaz.am.gov.br/nfce-services/services/NfeConsulta4",
		"NfeStatusServico": "https://homnfce.sefaz.am.gov.br/nfce-services/services/NfeStatusServico4",
		"NfeInutilizacao": "https://homnfce.sefaz.am.gov.br/nfce-services/services/NfeInutilizacao4",
		"RecepcaoEvento": "https://homnfce.sefaz.am.gov.br/nfce-services/services/RecepcaoEvento4",
	},
	"GO": {
		"NFeAutorizacao": "https://homolog.sefaz.go.gov.br/nfe/services/NFeAutorizacao4",
		"NFeRetAutorizacao": "https://homolog.sefaz.go.gov.br/nfe/services/NFeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://homolog.sefaz.go.gov.br/nfe/services/NFeConsultaProtocolo4",
		"NfeStatusServico": "https://homolog.sefaz.go.gov.br/nfe/services/NFeStatusServico4",
		"NfeInutilizacao": "https://homolog.sefaz.go.gov.br/nfe/services/NFeInutilizacao4",
		"RecepcaoEvento": "https://homolog.sefaz.go.gov.br/nfe/services/NFeRecepcaoEvento4",
	},
	"MG": {
		"NFeAutorizacao": "https://hnfce.fazenda.mg.gov.br/nfce/services/NFeAutorizacao4",
		"NFeRetAutorizacao": "https://hnfce.fazenda.mg.gov.br/nfce/services/NFeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://hnfce.fazenda.mg.gov.br/nfce/services/NFeConsultaProtocolo4",
		"NfeStatusServico": "https://hnfce.fazenda.mg.gov.br/nfce/services/NFeStatusServico4",
		"NfeInutilizacao": "https://hnfce.fazenda.mg.gov.br/nfce/services/NFeInutilizacao4",
		"RecepcaoEvento": "https://hnfce.fazenda.mg.gov.br/nfce/services/NFeRecepcaoEvento4",
	},
	"MS": {
		"NFeAutorizacao": "https://hom.nfce.sefaz.ms.gov.br/ws/NFeAutorizacao4",
		"NFeRetAutorizacao": "https://hom.nfce.sefaz.ms.gov.br/ws/NFeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://hom.nfce.sefaz.ms.gov.br/ws/NFeConsultaProtocolo4",
		"NfeStatusServico": "https://hom.nfce.sefaz.ms.gov.br/ws/NFeStatusServico4",
		"NfeInutilizacao": "https://hom.nfce.sefaz.ms.gov.br/ws/NFeInutilizacao4",
		"RecepcaoEvento": "https://hom.nfce.sefaz.ms.gov.br/ws/NFeRecepcaoEvento4",
	},
	"MT": {
		"NFeAutorizacao": "https://homologacao.sefaz.mt.gov.br/nfcews/services/NfeAutorizacao4",
		"NFeRetAutorizacao": "https://homologacao.sefaz.mt.gov.br/nfcews/services/NfeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://homologacao.sefaz.mt.gov.br/nfcews/services/NfeConsulta4",
		"NfeStatusServico": "https://homologacao.sefaz.mt.gov.br/nfcews/services/NfeStatusServico4",
		"NfeInutilizacao": "https://homologacao.sefaz.mt.gov.br/nfcews/services/NfeInutilizacao4",
		"RecepcaoEvento": "https://homologacao.sefaz.mt.gov.br/nfcews/services/RecepcaoEvento4",
	},
	"PR": {
		"NFeAutorizacao": "https://homologacao.nfce.sefa.pr.gov.br/nfce/NFeAutorizacao4",
		"NFeRetAutorizacao": "https://homologacao.nfce.sefa.pr.gov.br/nfce/NFeRetAutorizacao4",
		"NfeConsultaProtocolo": "https://homologacao.nfce.sefa.pr.gov.br/nfce/NFeConsultaProtocolo4",
		"NfeStatusServico": "https://homologacao.nfce.sefa.pr.gov.br/nfce/NFeStatusServico4",
		"NfeInutilizacao": "https://homologacao.nfce.sefa.pr.gov.br/nfce/NFeInutilizacao4",
		"RecepcaoEvento": "https://homologacao.nfce.sefa.pr.gov.br/nfce/NFeRecepcaoEvento4",
	},
	"RS": {
		"NFeAutorizacao": "https://nfce-homologacao.sefazrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://nfce-homologacao.sefazrs.rs.gov.br/ws/NfeRetAutorizacao/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://nfce-homologacao.sefazrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx",
		"NfeStatusServico": "https://nfce-homologacao.sefazrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx",
		"NfeInutilizacao": "https://nfce-homologacao.sefazrs.rs.gov.br/ws/nfeinutilizacao/nfeinutilizacao4.asmx",
		"RecepcaoEvento": "https://nfce-homologacao.sefazrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
	},
	"SP": {
		"NFeAutorizacao": "https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeConsultaProtocolo4.asmx",
		"NfeStatusServico": "https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeStatusServico4.asmx",
		"NfeInutilizacao": "https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeInutilizacao4.asmx",
		"RecepcaoEvento": "https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeRecepcaoEvento4.asmx",
	},
	_SVRS: {
		"NFeAutorizacao": "https://nfce-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
		"NFeRetAutorizacao": "https://nfce-homologacao.svrs.rs.gov.br/ws/NfeRetAutorizacao/NFeRetAutorizacao4.asmx",
		"NfeConsultaProtocolo": "https://nfce-homologacao.svrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx",
		"NfeStatusServico": "https://nfce-homologacao.svrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx",
		"NfeInutilizacao": "https://nfce-homologacao.svrs.rs.gov.br/ws/nfeinutilizacao/nfeinutilizacao4.asmx",
		"RecepcaoEvento": "https://nfce-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
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


def endpoint(
	uf: str, servico: str, ambiente: str = "producao", modelo: str = "55", contingencia: bool = False
) -> str | None:
	"""Devolve a URL do webservice, ou `None` quando o serviço não está confirmado
	para a combinação UF/grupo (nunca uma URL inventada).

	`modelo="65"` (NFC-e) usa a tabela própria (`ENDPOINTS_NFCE*`) quando o grupo tem
	infraestrutura separada da NF-e; cai para a tabela de NF-e automaticamente nos
	grupos sem bloco próprio (BA, PE, SVAN — ver docstring do módulo). `modelo="55"` é o
	padrão, compatível com todo código que já chamava `endpoint()` sem esse argumento.

	`NfeConsultaCadastro` nunca usa a tabela de NFC-e — é serviço de consulta cadastral,
	agnóstico a modelo de documento.

	`contingencia=True` resolve para o SVC (SVC-AN ou SVC-RS) da UF em vez do autorizador
	normal — pré-condição: só existe para `modelo="55"` (levanta `ValueError` se
	`modelo="65"`, ver docstring do módulo sobre por que NFC-e nunca usa SVC).

	Grupo sem homologação confirmada levanta `NotImplementedError`: não existe padrão de
	host confiável para derivar homologação por inferência.
	"""
	sigla = (uf or "").strip().upper()

	if ambiente not in ("producao", "homologacao"):
		raise ValueError(f"Ambiente deve ser 'producao' ou 'homologacao', recebido {ambiente!r}")

	if modelo not in ("55", "65"):
		raise ValueError(f"Modelo deve ser '55' (NF-e) ou '65' (NFC-e), recebido {modelo!r}")

	if contingencia and modelo != "55":
		raise ValueError("Contingência SVC-AN/SVC-RS é exclusiva de NF-e (modelo 55), nunca de NFC-e")

	if contingencia:
		chave = UF_CONTINGENCIA_SVC.get(sigla)

		if chave is None:
			raise AutorizadorDesconhecido(f"UF {uf!r} não consta na tabela de contingência SVC")

		if ambiente == "homologacao":
			return ENDPOINTS_HOMOLOGACAO[chave].get(servico)

		return ENDPOINTS[chave].get(servico)

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

	tabela_producao, tabela_homologacao = ENDPOINTS, ENDPOINTS_HOMOLOGACAO
	if modelo == "65" and servico != "NfeConsultaCadastro" and chave in ENDPOINTS_NFCE:
		tabela_producao, tabela_homologacao = ENDPOINTS_NFCE, ENDPOINTS_NFCE_HOMOLOGACAO

	if ambiente == "homologacao":
		if chave not in tabela_homologacao:
			raise NotImplementedError(
				f"Homologação não está confirmada para o grupo {chave!r} nesta tabela — "
				"precisa ser levantada antes de uso, não derivada por padrão de nome"
			)

		return tabela_homologacao[chave].get(servico)

	return tabela_producao[chave].get(servico)
