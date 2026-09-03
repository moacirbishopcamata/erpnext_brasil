# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Alerta diário de vencimento do certificado A1.

Fecha um buraco real de operação: o A1 vale um ano e, quando vence, a emissão
simplesmente para. `assinador_local.carregar_certificado` já recusa certificado vencido
— mas na hora de emitir, que é o pior momento possível para descobrir. Esta tarefa
agendada avisa antes.

A regra de **quando** avisar não está aqui
--------------------------------------------------
Está em `fiscal/documento/validade_certificado.py`, puro e testado sem bench: marcos em
30, 15 e 7 dias (um aviso em cada), aviso diário nos últimos 3 dias e depois de vencido.
Aqui fica só o que exige o Frappe — varrer as empresas, abrir o certificado, criar a
notificação.

Por que a leitura da validade não usa `carregar_certificado`
--------------------------------------------------------------------
Porque aquela função **recusa** certificado vencido, e o alerta precisa justamente
conseguir abrir o vencido para informar o caso mais urgente. Daí
`assinador_local.expiracao_do_certificado`, que abre sem julgar (as duas compartilham
`_abrir_pkcs12`, então não há leitura duplicada do formato).

Falha de uma empresa não derruba as outras
--------------------------------------------------
Num site multiempresa, senha errada ou arquivo corrompido em **uma** Company não pode
impedir o alerta das demais — a exceção é registrada no log e a varredura continua. Uma
tarefa agendada que morre no primeiro erro deixa de avisar exatamente quem depende dela.

Quem recebe o aviso
--------------------------
Usuários com o papel "Accounts Manager" (quem cuida da emissão fiscal), com fallback
para "System Manager" quando ninguém tem aquele papel — um site pequeno pode não ter a
função separada, e um alerta sem destinatário é um alerta que não existe.
"""

from datetime import date

import frappe

from erpnext_brasil.fiscal.documento.validade_certificado import avaliar_validade, mensagem
from erpnext_brasil.integracao.notificacao import notificar_responsaveis

__all__ = ["verificar_validade_dos_certificados"]


def _empresas_com_certificado() -> list[str]:
	return frappe.get_all(
		"Company",
		filters={"br_certificado_a1": ["is", "set"]},
		pluck="name",
	)


def verificar_validade_dos_certificados(hoje: date | None = None) -> list[dict]:
	"""Varre as empresas com certificado configurado e notifica as que precisam.

	`hoje` é injetável para teste; em produção o agendador chama sem argumento.
	Devolve o que foi avaliado (empresa, dias restantes, se notificou) — útil para
	inspecionar a execução no console do bench sem ler o log.
	"""
	from erpnext_brasil.integracao.assinador_local import expiracao_do_certificado
	from erpnext_brasil.integracao.certificado_a1 import carregar_certificado_da_empresa

	hoje = hoje or date.today()
	resultado = []

	for company in _empresas_com_certificado():
		try:
			pfx, senha = carregar_certificado_da_empresa(company)
			expira = expiracao_do_certificado(pfx, senha)
		except Exception as e:
			# Amplo de propósito: senha errada, arquivo corrompido, anexo removido —
			# qualquer uma delas em UMA empresa não pode calar o alerta das outras num
			# site multiempresa. Registra e segue.
			frappe.log_error(
				title=f"Alerta de certificado A1: {company}",
				message=f"Não foi possível ler o certificado de {company}: {e}",
			)
			continue

		if expira is None:
			continue

		avaliacao = avaliar_validade(expira.date(), hoje)

		if avaliacao.deve_alertar:
			notificar_responsaveis(
				company,
				f"Certificado digital A1 — {company}",
				mensagem(avaliacao, company, expira.date()),
			)

		resultado.append(
			{
				"empresa": company,
				"expira_em": expira.date().isoformat(),
				"dias_restantes": avaliacao.dias_restantes,
				"notificou": avaliacao.deve_alertar,
			}
		)

	return resultado
