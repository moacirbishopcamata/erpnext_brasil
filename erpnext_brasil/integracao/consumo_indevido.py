# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Guarda o CNPJ contra o bloqueio de consumo indevido da SEFAZ.

⚠️ A guarda é **preventiva**, e essa palavra é o desenho inteiro
---------------------------------------------------------------------
`cStat 656` bloqueia o CNPJ por uma hora, e *"se retomar a consulta antes de completar 1
hora, o tempo é zerado"*. Logo, o valor deste módulo **não** está em reagir bem à rejeição:
está em impedir que a próxima requisição saia.

Uma requisição recusada aqui **não reinicia o relógio**, porque nunca chegou à SEFAZ. Uma
requisição que passa e é rejeitada de novo empurra a liberação mais uma hora. A diferença
entre esperar uma hora e esperar para sempre é exatamente esta função rodar antes da
chamada de rede.

Por isso `garantir_liberado` levanta em vez de devolver `False`: um retorno que o chamador
pode ignorar por descuido — `if not garantir_liberado(...)` esquecido — devolveria o
comportamento antigo sem que nada acusasse.

Onde o bloqueio é guardado, e por que não em cache
--------------------------------------------------------
No DocType `Bloqueio Sefaz`, um registro por `(CNPJ, ambiente)`. Um cache com TTL de uma
hora seria mais curto de escrever e **errado**: perder a chave (Redis reiniciado, cache
limpo num deploy) liberaria a transmissão antes da hora, que é precisamente o que reinicia
a contagem. O dado tem de sobreviver ao que o sistema faz consigo mesmo.

Produção e homologação bloqueiam de forma independente — um bloqueio em teste não pode
parar a emissão real, e é por isso que o ambiente entra na chave.

O que este módulo **não** faz, declarado
-----------------------------------------------
- **Não adivinha consumo indevido.** Quem diz é a SEFAZ, no `cStat`. Uma heurística local
  ("consultei demais") criaria bloqueio que a SEFAZ não impôs, parando emissão legítima.
- **Não desbloqueia à mão.** O desbloqueio é automático ao completar a hora. Um botão
  "liberar agora" seria um botão de estender o bloqueio, e é a razão de o registro ser
  somente leitura no Desk.
- **Não repete a requisição depois.** Reenfileirar automaticamente para daqui a uma hora
  seria conveniente e perigoso: se o motivo do consumo indevido persistir, o app volta a
  bater e o ciclo recomeça. Quem retoma é uma pessoa que viu a mensagem.

⚠️ Gravar o bloqueio é o que **não** pode falhar
------------------------------------------------------
`company` é obrigatório no DocType — a restrição por empresa exige, e sem ela um usuário
veria o bloqueio de outra empresa. Mas campo obrigatório num registro de segurança cria um
risco próprio: se a gravação falhar, o CNPJ fica bloqueado na SEFAZ **e o app não sabe**, e
a próxima transmissão estende a hora.

Por isso a persistência é envolvida: falhou, registra alto em `Error Log` e devolve
`False`, em vez de derrubar o caminho da resposta. Trocar um problema por outro maior seria
deixar a exceção subir.

Estado de verificação
----------------------------
Exercitado em site **v16 real**: `cStat 100` não bloqueia, `656` bloqueia, a guarda passa a
recusar com `BloqueadoPorConsumoIndevido`, o outro ambiente segue liberado, e `liberado_em`
sai derivado com uma hora exata de diferença.

Foi essa execução que revelou o risco do campo obrigatório acima.
"""

import frappe
from frappe import _

from erpnext_brasil.fiscal.consumo_indevido import (
	CSTAT_CONSUMO_INDEVIDO,
	Bloqueio,
	e_consumo_indevido,
	iniciar_bloqueio,
)
from erpnext_brasil.fiscal.validators import limpar

__all__ = [
	"DOCTYPE",
	"BloqueadoPorConsumoIndevido",
	"bloqueio_ativo",
	"chave_do_bloqueio",
	"garantir_liberado",
	"registrar_resposta",
]

DOCTYPE = "Bloqueio Sefaz"


class BloqueadoPorConsumoIndevido(frappe.ValidationError):
	"""Tentativa de falar com a SEFAZ durante a janela de bloqueio.

	Classe própria, e não `frappe.throw` sem `exc=`: quem chama precisa poder distinguir
	"estou bloqueado, espere" de "a nota está errada". A primeira não deve ser repetida de
	forma alguma; a segunda, depois de corrigida.
	"""


def chave_do_bloqueio(cnpj: str, ambiente: str) -> str:
	"""`CNPJ limpo` + ambiente — o `autoname` do DocType.

	`limpar` porque o mesmo CNPJ chega com e sem máscara conforme o cadastro, e duas chaves
	para o mesmo CNPJ seriam dois bloqueios que não se enxergam: um deles liberaria a
	transmissão.
	"""
	return f"{limpar(cnpj)}::{(ambiente or '').strip().lower()}"


def bloqueio_ativo(cnpj: str, ambiente: str) -> Bloqueio | None:
	"""O bloqueio em vigor, ou `None`. Não levanta — serve para a tela perguntar."""
	inicio = frappe.db.get_value(DOCTYPE, chave_do_bloqueio(cnpj, ambiente), "bloqueado_em")

	if not inicio:
		return None

	bloqueio = Bloqueio(inicio=frappe.utils.get_datetime(inicio))

	return bloqueio if bloqueio.ativo_em(frappe.utils.now_datetime()) else None


def garantir_liberado(cnpj: str, ambiente: str) -> None:
	"""Recusa a operação enquanto o bloqueio estiver ativo. **Chamar antes da rede.**

	A mensagem diz o horário de liberação e, explicitamente, para não insistir — porque a
	reação natural de quem vê um erro de transmissão é tentar de novo, e aqui isso custa
	mais uma hora.
	"""
	bloqueio = bloqueio_ativo(cnpj, ambiente)

	if not bloqueio:
		return

	agora = frappe.utils.now_datetime()
	minutos = int(bloqueio.restante(agora).total_seconds() // 60) + 1

	frappe.throw(
		_(
			"O CNPJ {0} está bloqueado pela SEFAZ por consumo indevido (cStat {1}) no ambiente "
			"{2}. A liberação é automática em {3} — faltam cerca de {4} minuto(s).<br><br>"
			"<b>Não tente transmitir antes disso.</b> Cada tentativa dentro da janela reinicia "
			"a contagem de uma hora, e o bloqueio recomeça do zero."
		).format(
			cnpj,
			CSTAT_CONSUMO_INDEVIDO,
			ambiente,
			frappe.utils.format_datetime(bloqueio.liberado_em),
			minutos,
		),
		exc=BloqueadoPorConsumoIndevido,
		title=_("Bloqueado por consumo indevido"),
	)


def registrar_resposta(
	cnpj: str, ambiente: str, codigo_status, mensagem: str = "", company: str | None = None
) -> bool:
	"""Grava o bloqueio quando a resposta for 656. Devolve se bloqueou.

	`company` vem de quem constrói o transporte, que sabe qual é. Derivá-la do CNPJ aqui
	dependeria de o `tax_id` estar cadastrado com a mesma máscara, e um erro nisso
	impediria de **gravar o bloqueio** — o pior desfecho possível.

	Chamado **depois** de cada resposta da SEFAZ. Receber um 656 aqui significa que alguma
	requisição escapou da guarda — se nada tivesse saído, não haveria o que rejeitar —, e é
	por isso que a janela recomeça de agora e não estende a anterior.
	"""
	if not e_consumo_indevido(codigo_status):
		return False

	agora = frappe.utils.now_datetime()
	nome = chave_do_bloqueio(cnpj, ambiente)
	bloqueio = iniciar_bloqueio(agora, anterior=bloqueio_ativo(cnpj, ambiente))

	valores = {
		"company": company,
		"cnpj": limpar(cnpj),
		"ambiente": (ambiente or "").strip().lower(),
		"bloqueado_em": bloqueio.inicio,
		"codigo_status": str(codigo_status),
		"mensagem": (mensagem or "")[:500],
	}

	try:
		if frappe.db.exists(DOCTYPE, nome):
			documento = frappe.get_doc(DOCTYPE, nome)
			documento.update(valores)
			documento.save(ignore_permissions=True)
		else:
			frappe.get_doc({"doctype": DOCTYPE, "chave": nome, **valores}).insert(ignore_permissions=True)

		# `commit` explícito: a rejeição costuma vir num caminho que termina em exceção, e
		# o rollback da transação levaria o registro do bloqueio junto — deixando o app sem
		# saber que está bloqueado, que é o pior dos estados possíveis.
		frappe.db.commit()
	except Exception:
		# 🔴 Achado no bench: `company` é obrigatório (a restrição por empresa exige), e num
		# site sem `Company` cadastrada o `insert` levantava **dentro do caminho da
		# resposta** — derrubando a transmissão e, pior, deixando o bloqueio sem registro.
		#
		# Deixar a exceção subir seria trocar um problema por outro maior: quem não
		# consegue **anotar** o bloqueio volta a transmitir daqui a pouco e estende a hora.
		# Por isso aqui se registra alto no log e se devolve `False`, em vez de explodir.
		#
		# `log_error` e não `print`: é falha que ninguém vê acontecer, e precisa de trilha.
		frappe.log_error(
			title="Falha ao registrar bloqueio por consumo indevido",
			message=(
				f"CNPJ {cnpj} / ambiente {ambiente} recebeu cStat {codigo_status} e o bloqueio "
				f"NÃO pôde ser gravado. O CNPJ está bloqueado na SEFAZ por uma hora e o app "
				f"não sabe disso — transmitir de novo estende o bloqueio.\n\n"
				f"{frappe.get_traceback()}"
			),
		)

		return False

	return True
