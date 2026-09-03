# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Alertas de risco fiscal ao usuário, no momento em que ainda dá para corrigir.

Auditoria pedida pelo usuário ("verifique se há outras funcionalidades precisando de
alertas"), depois do alerta de vencimento do certificado A1
(`integracao/alerta_certificado.py`). Os dois casos abaixo foram os que sobraram com
risco real **e** base já verificada no código — não dependem de nenhuma data legal que
este projeto não tenha confirmado em fonte.

1. Documento fiscal aprovado com o ambiente em Homologação
------------------------------------------------------------------
O pior tipo de falha: silenciosa e cara. Documento transmitido em homologação **não tem
valor fiscal nenhum** — a SEFAZ o autoriza, o número é consumido no ambiente de teste, e
a mercadoria circula sem documento válido. Quem esquece o ambiente em Homologação depois
de testar não recebe erro nenhum hoje.

É **aviso, não bloqueio** (`msgprint`, não `throw`): homologar é uso legítimo, e travar
o envio impediria justamente o teste que o ambiente existe para permitir. O alerta diz o
que está acontecendo e onde trocar.

2. Cadastro incompleto para gerar a EFD
------------------------------------------------
`contabil/prontidao_fiscal.py` decide o que é pendência (puro, testável sem bench);
aqui só se lê o cadastro e se apresenta o resultado. Chamável sob demanda, antes de
gerar o arquivo — a montagem para no primeiro erro, e quem tem mil itens descobriria um
problema por rodada.

O que **não** virou alerta, e por quê
--------------------------------------------
**Prazos das obrigações acessórias** (EFD, ECD, ECF, DCTFWeb, eSocial). Seria o alerta
mais óbvio de um ERP fiscal, e foi deliberadamente deixado de fora: as fontes consultadas
**divergem entre si** sobre as datas (EFD-Contribuições aparece como "dia 15" em uma e
"10º dia útil do 2º mês" em outra; ECD como "30 de junho" e como "último dia útil de
maio"), o prazo da EFD-ICMS/IPI **varia por UF**, e o site oficial da RFB continua
recusando conexão. Cravar data legal errada em código é pior que não ter o alerta: o
usuário confiaria e perderia o prazo. Registrado como pendência em
`docs/leitor-codigo-e-alertas.md`, com a divergência documentada.
"""

from datetime import date

import frappe
from frappe import _

from erpnext_brasil.contabil.prontidao_fiscal import verificar_empresa, verificar_item
from erpnext_brasil.integracao.notificacao import notificar_responsaveis

__all__ = [
	"avisar_ambiente_de_homologacao",
	"verificar_prontidao_efd",
	"verificar_transicao_da_reforma",
]

_AMBIENTE_PRODUCAO = "Produção"


def avisar_ambiente_de_homologacao(doc, method=None):
	"""Avisa, ao aprovar um documento com chave de acesso, que o ambiente não é produção.

	Só dispara quando há `br_chave_acesso` preenchida: sem chave, o documento não foi
	transmitido a lugar nenhum e o ambiente é irrelevante — avisar ali seria ruído em
	todo lançamento manual, e alerta ruidoso é alerta ignorado.
	"""
	if not doc.get("br_chave_acesso"):
		return

	company = doc.get("company")

	if not company:
		return

	ambiente = frappe.db.get_value("Company", company, "br_ambiente_sefaz")

	if ambiente == _AMBIENTE_PRODUCAO:
		return

	frappe.msgprint(
		_(
			"A empresa {0} está com o ambiente SEFAZ em <b>{1}</b>. Documento transmitido "
			"em homologação <b>não tem valor fiscal</b> — serve só para teste. Para emitir "
			"de verdade, troque em Empresa &gt; Dados Fiscais &gt; Ambiente SEFAZ."
		).format(company, ambiente or _("não configurado")),
		title=_("Ambiente de teste"),
		indicator="orange",
	)


@frappe.whitelist()
def verificar_prontidao_efd(company: str, limite_de_itens: int = 500) -> dict:
	"""Lista tudo que falta cadastrar para gerar a EFD desta empresa.

	`limite_de_itens` existe porque a varredura lê item a item: num cadastro grande, o
	usuário quer as primeiras pendências rápido, não esperar a base inteira. O retorno
	diz se houve corte, para não passar a falsa impressão de que o resto está limpo.
	"""
	dados = (
		frappe.db.get_value(
			"Company",
			company,
			["tax_id", "inscricao_estadual", "br_efd_perfil", "br_efd_atividade", "br_efd_versao_leiaute"],
			as_dict=True,
		)
		or {}
	)

	endereco = frappe.db.get_value(
		"Address",
		{"is_your_company_address": 1, "link_name": company},
		["state", "codigo_municipio_ibge"],
		as_dict=True,
	)

	if endereco:
		dados.update(endereco)

	pendencias = [_como_dict(p) for p in verificar_empresa(dados)]

	itens = frappe.get_all(
		"Item",
		filters={"disabled": 0},
		fields=["name as item_code", "stock_uom", "ncm", "br_efd_tipo_item"],
		limit=limite_de_itens + 1,
	)

	truncado = len(itens) > limite_de_itens

	for item in itens[:limite_de_itens]:
		pendencias.extend(_como_dict(p) for p in verificar_item(item))

	return {
		"empresa": company,
		"pendencias": pendencias,
		"bloqueios": sum(1 for p in pendencias if p["bloqueia"]),
		"itens_verificados": min(len(itens), limite_de_itens),
		"truncado": truncado,
	}


def verificar_transicao_da_reforma(hoje: date | None = None) -> dict:
	"""Avisa quando o ano corrente passou do único ano com alíquotas de IBS/CBS embutidas.

	Mora aqui, e não em `alerta_certificado.py`, porque é alerta de **risco fiscal** —
	nada tem a ver com certificado digital. A primeira versão ficou lá por conveniência
	(era onde o envio de notificação existia), o que era acoplamento por acaso histórico:
	corrigido extraindo o envio para `integracao/notificacao.py`, que é de quem os dois
	dependem agora.

	A regra de *quando* está em `fiscal/impostos/transicao_reforma.py`, pura e testável
	sem bench; aqui só se lê a data e se notifica.

	Notifica **uma vez por dia enquanto durar**, sem marcos como os do certificado: não
	há contagem regressiva a comunicar, e o problema não se resolve sozinho com o tempo
	— só com alguém informando as alíquotas vigentes.
	"""
	from erpnext_brasil.fiscal.impostos.transicao_reforma import avaliar_transicao

	hoje = hoje or date.today()
	situacao = avaliar_transicao(hoje.year)

	if situacao.deve_alertar:
		for company in frappe.get_all("Company", pluck="name"):
			notificar_responsaveis(
				company,
				f"Reforma tributária — alíquotas de {situacao.ano}",
				situacao.mensagem,
			)

	return {
		"ano": situacao.ano,
		"aliquotas_embutidas": situacao.aliquotas_embutidas,
		"notificou": situacao.deve_alertar,
	}


def _como_dict(pendencia) -> dict:
	return {
		"campo": pendencia.campo,
		"onde": pendencia.onde,
		"motivo": pendencia.motivo,
		"gravidade": pendencia.gravidade,
		"bloqueia": pendencia.bloqueia,
	}
