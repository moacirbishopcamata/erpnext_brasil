# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Transmite um `Lote eSocial` do site e grava o que voltou.

Fecha o maior órfão que a varredura de 2026-09-06 encontrou. A cadeia do eSocial estava
inteira — montagem, assinatura, lote, SOAP, retorno, seis eventos modelados — e **nenhum
método `@frappe.whitelist()` a acionava**. Para quem usa o sistema, o app não transmitia
eSocial.

O que este módulo faz, e o que não faz
---------------------------------------------
Ele **transmite um lote que já existe**, com os eventos já montados e assinados, gravados
no DocType. Não monta eventos a partir da folha — isso é `integracao/folha.py` mais os
montadores de `folha/`, e é outra fronteira.

A divisão importa: montar um S-1200 exige ler `Salary Slip`, rubricas e cadastro; transmitir
exige certificado e rede. Juntar as duas coisas num método faria um erro de cadastro e uma
queda de rede parecerem a mesma falha.

⚠️ Por que a situação não é lida do retorno cru
--------------------------------------------------------
O eSocial responde em **dois níveis**, e confundi-los é o erro clássico deste protocolo:

- o `cdResposta` do **lote** diz se o lote foi recebido e processado;
- cada **evento** tem o seu próprio recibo e os seus próprios erros.

Um lote pode voltar processado com sucesso e conter eventos rejeitados. Gravar só o status
do lote diria que deu tudo certo quando metade da folha foi recusada — por isso cada evento
vira uma linha de `Evento do Lote eSocial`, com o seu XML de retorno.

O registro é gravado em todos os desfechos
-------------------------------------------------
Como em `emissao_nfe` e `eventos_nfe`, e pela mesma razão: rejeição é resultado, não erro de
programa. Quem transmitiu precisa poder ler o que o eSocial respondeu.

Estado de verificação: camada Frappe, **não** exercitada contra bench real nem contra o
ambiente de produção restrita.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

from erpnext_brasil.integracao.certificado_a1 import carregar_certificado_da_empresa
from erpnext_brasil.integracao.configuracao_fiscal import ambiente_esocial_da_empresa
from erpnext_brasil.integracao.transporte_esocial import TransporteEsocial

__all__ = ["SITUACAO_POR_DESFECHO", "consultar_lote_esocial", "transmitir_lote_esocial"]

SITUACAO_PROCESSADO = "Processado"
SITUACAO_REJEITADO = "Rejeitado"
SITUACAO_EM_PROCESSAMENTO = "Em processamento"

SITUACAO_POR_DESFECHO = {
	True: SITUACAO_PROCESSADO,
	False: SITUACAO_REJEITADO,
}
"""Sucesso do **lote** → rótulo do `Select` de `Lote eSocial`.

Note que "Processado" fala do lote, não dos eventos: um lote processado pode conter evento
rejeitado, e é a tabela filha que conta essa parte.
"""


def _gravar_retorno(lote, resultado) -> None:
	"""Copia o retorno para o DocType — o do lote e o de cada evento.

	`db_set` não serve aqui: a tabela filha precisa de `save()` para persistir as linhas,
	e gravar cabeçalho por um caminho e filhas por outro deixaria os dois fora de sincronia
	se algo falhasse no meio.
	"""
	lote.situacao = SITUACAO_POR_DESFECHO.get(resultado.status.sucesso, SITUACAO_REJEITADO)
	lote.codigo_resposta = resultado.status.cd_resposta
	lote.descricao_resposta = resultado.status.desc_resposta
	lote.processado_em = now_datetime()

	if resultado.dados_recepcao is not None:
		lote.protocolo_envio = resultado.dados_recepcao.protocolo_envio

	# As linhas antigas são substituídas: uma reconsulta do mesmo lote traz o retorno
	# atualizado, e acumular versões faria a tabela crescer com histórico que ninguém pediu.
	lote.set("eventos", [])

	for evento in resultado.eventos:
		lote.append(
			"eventos",
			{
				"id_evento": evento.id_evento,
				"tipo_evento": getattr(evento, "tipo_evento", "") or "",
				"xml_retorno": getattr(evento, "xml", "") or "",
			},
		)

	lote.save(ignore_permissions=True)


@frappe.whitelist()
def transmitir_lote_esocial(name: str) -> dict:
	"""Envia ao eSocial o lote `name`, já montado e assinado, e grava o retorno.

	Devolve `{"situacao", "protocolo", "codigo", "descricao", "eventos"}`.

	Falha alto quando o lote não tem XML: transmitir vazio consumiria uma tentativa e
	voltaria com erro que não diz o que houve.
	"""
	lote = frappe.get_doc("Lote eSocial", name)
	lote.check_permission("submit")

	xml = (lote.get("xml_enviado") or "").strip()

	if not xml:
		frappe.throw(_("O lote {0} não tem XML montado — não há o que transmitir.").format(name))

	pfx, senha = carregar_certificado_da_empresa(lote.company)
	ambiente = ambiente_esocial_da_empresa(lote.company)

	with TransporteEsocial(pfx=pfx, senha=senha, ambiente=ambiente) as transporte:
		resultado = transporte.enviar(xml)

	_gravar_retorno(lote, resultado)

	if not resultado.status.sucesso:
		frappe.throw(
			_("O eSocial recusou o lote ({0}): {1}.").format(
				resultado.status.cd_resposta, resultado.status.desc_resposta
			)
		)

	return {
		"situacao": lote.situacao,
		"protocolo": lote.protocolo_envio,
		"codigo": resultado.status.cd_resposta,
		"descricao": resultado.status.desc_resposta,
		"eventos": len(resultado.eventos),
	}


@frappe.whitelist()
def consultar_lote_esocial(name: str) -> dict:
	"""Reconsulta o processamento de um lote já enviado, sem reenviá-lo.

	Existe porque o envio pode terminar em "Em processamento": o eSocial aceita o lote e
	responde que ainda não terminou. Reenviar nesse estado **duplicaria os eventos** — a
	consulta é o caminho certo, e por isso é um método à parte, não um retry escondido
	dentro do envio.
	"""
	lote = frappe.get_doc("Lote eSocial", name)
	lote.check_permission("read")

	protocolo = (lote.get("protocolo_envio") or "").strip()

	if not protocolo:
		frappe.throw(_("O lote {0} não tem protocolo de envio — não foi transmitido ainda.").format(name))

	pfx, senha = carregar_certificado_da_empresa(lote.company)
	ambiente = ambiente_esocial_da_empresa(lote.company)

	with TransporteEsocial(pfx=pfx, senha=senha, ambiente=ambiente) as transporte:
		resultado = transporte.consultar(protocolo)

	lote.tentativas_de_consulta = (lote.get("tentativas_de_consulta") or 0) + 1
	_gravar_retorno(lote, resultado)

	return {
		"situacao": lote.situacao,
		"protocolo": protocolo,
		"codigo": resultado.status.cd_resposta,
		"descricao": resultado.status.desc_resposta,
		"eventos": len(resultado.eventos),
	}
