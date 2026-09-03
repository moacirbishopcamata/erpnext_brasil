# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Envio de aviso aos responsáveis fiscais — o mecanismo, sem nenhuma regra de negócio.

Extraído de `alerta_certificado.py` quando um segundo alerta (a virada de fase da
reforma tributária) passou a precisar do mesmo envio. Deixar a função onde estava
obrigaria `alerta_fiscal.py` a importar de um módulo chamado "alerta_certificado" para
falar de reforma tributária — acoplamento por acaso histórico, não por responsabilidade.

**Fatorar, nunca enxugar**: o segundo consumidor é o que justifica extrair. Antes dele,
a função morava junto do único uso, que era o certo naquele momento.

Este módulo não sabe *quando* avisar — só *como*. Cada regra de quando mora no seu
módulo puro (`fiscal/documento/validade_certificado.py`,
`fiscal/impostos/transicao_reforma.py`), testável sem bench.
"""

import frappe
from frappe import _

__all__ = ["PAPEIS_RESPONSAVEIS", "notificar_responsaveis"]

PAPEIS_RESPONSAVEIS = ("Accounts Manager", "System Manager")
"""Ordem de preferência. O fallback existe porque um site pequeno pode não ter a função
financeira separada, e alerta sem destinatário é alerta que não existe."""


def _destinatarios() -> list[str]:
	"""Usuários **ativos** do primeiro papel que tiver alguém.

	Não soma os papéis: se há um responsável financeiro, o administrador não precisa
	receber o mesmo aviso — notificar todo mundo por precaução é como um alerta perde
	relevância.
	"""
	for papel in PAPEIS_RESPONSAVEIS:
		usuarios = frappe.get_all(
			"Has Role",
			filters={"role": papel, "parenttype": "User"},
			pluck="parent",
		)

		ativos = [usuario for usuario in set(usuarios) if frappe.db.get_value("User", usuario, "enabled")]

		if ativos:
			return sorted(ativos)

	return []


def notificar_responsaveis(company: str, assunto: str, texto: str) -> int:
	"""Cria uma notificação por destinatário e devolve quantas foram criadas.

	Zero destinatários não é silêncio: o caso é registrado no log de erro, porque um
	aviso que não chega a ninguém é um problema de configuração que alguém precisa ver.
	"""
	destinatarios = _destinatarios()

	if not destinatarios:
		frappe.log_error(
			title="Alerta fiscal sem destinatário",
			message=(
				f"Havia um aviso a dar sobre {company} ({assunto}), mas nenhum usuário "
				f"ativo tem os papéis {list(PAPEIS_RESPONSAVEIS)} — o alerta não chegaria "
				"a ninguém."
			),
		)
		return 0

	for usuario in destinatarios:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": _(assunto),
				"email_content": texto,
				"for_user": usuario,
				"type": "Alert",
				"document_type": "Company",
				"document_name": company,
			}
		).insert(ignore_permissions=True)

	return len(destinatarios)
