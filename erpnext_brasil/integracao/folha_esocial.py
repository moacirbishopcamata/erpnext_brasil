# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Lê um `Salary Slip` e produz o evento S-1200 — a ponte que faltava.

O que faltava
--------------------
`folha/esocial_s1200.py` monta a árvore do evento, e `transmissao_lote_esocial` a transmite.
Entre os dois havia um vazio: **nada lia a folha do ERPNext**. Este módulo é a ponte, e com
ela o eSocial deixa de depender de alguém montar dataclasses à mão.

Por que a rubrica é o centro de tudo
-------------------------------------------
O S-1200 declara cada verba por `codRubr`, e esse código vem da **tabela de rubricas do
próprio empregador** (evento S-1010) — não existe tabela nacional a consultar. Um
`Salary Component` sem código não tem como virar linha de `itensRemun`.

⚠️ E isso **falha alto**, não é ignorado. Pular a linha produziria um evento com remuneração
a menos: aceito pelo eSocial, e errado — a diferença viraria divergência entre a folha e o
que foi declarado, descoberta meses depois. Melhor recusar dizendo qual componente falta.

O que **não** entra no evento
------------------------------------
- **Componente estatístico** (`statistical_component`) — existe só para cálculo interno do
  ERPNext, não representa verba paga.
- **Componente marcado como fora do total** (`do_not_include_in_total`) — pela mesma razão.
- **Valor zero** entra normalmente: o eSocial espera o valor apurado do período, e omitir a
  linha esconderia o cálculo em vez de mostrar "apurado como zero" (mesma regra de
  `linhas_de_inss_irrf`).

Ganhos e descontos, uma lista só
---------------------------------------
`itensRemun` não separa provento de desconto — o **código da rubrica** é que diz o que cada
linha é. Por isso `earnings` e `deductions` do `Salary Slip` viram uma lista única, na ordem
em que estão: separá-las aqui inventaria uma estrutura que o leiaute não tem.

Estado de verificação: camada Frappe, **não** exercitada contra bench real.
"""

from decimal import Decimal

import frappe
from frappe import _

from erpnext_brasil.folha.esocial_s1200 import (
	DmDev,
	IdeEmpregador,
	IdeEstabLot,
	IdeEvento,
	IdeTrabalhador,
	InfoComplem,
	InfoPerApur,
	ItemRemuneracao,
	RemunPerApur,
)

__all__ = [
	"CAMPOS_DO_EMPREGADO",
	"TIPO_INSCRICAO_CNPJ",
	"evento_do_holerite",
	"itens_do_holerite",
]

TIPO_INSCRICAO_CNPJ = 1
"""`tpInsc` do empregador pessoa jurídica.

O leiaute admite 4 (CPF) para o empregador doméstico; este módulo trata a `Company` do
ERPNext, que é sempre pessoa jurídica no uso normal — e assumir CNPJ é declarado aqui em
vez de escondido num literal no meio do código.
"""

CAMPOS_DO_EMPREGADO = (
	"employee_name",
	"employee_number",
	"date_of_birth",
	"br_cpf",
	"br_nis",
	"br_cod_categoria",
	"br_cod_cbo",
	"br_cod_lotacao",
)
"""O que se lê do `Employee`.

Os três primeiros são nativos do ERPNext — não se criou campo novo para eles, pela mesma
razão que não se criou `br_conta` no `Bank Account`: seria segunda verdade sobre o mesmo
dado.
"""


def _exigir(valor, mensagem: str):
	if not valor:
		frappe.throw(mensagem)

	return valor


def itens_do_holerite(holerite) -> tuple[ItemRemuneracao, ...]:
	"""As linhas de `itensRemun` de um `Salary Slip`.

	Ganhos e descontos numa lista só — ver docstring do módulo. Componente sem código de
	rubrica **recusa a montagem**, dizendo qual é.
	"""
	itens: list[ItemRemuneracao] = []

	for linha in list(holerite.get("earnings") or []) + list(holerite.get("deductions") or []):
		if linha.get("statistical_component") or linha.get("do_not_include_in_total"):
			continue

		componente = linha.get("salary_component")
		codigo = frappe.db.get_value("Salary Component", componente, "br_cod_rubrica")

		if not codigo:
			frappe.throw(
				_(
					"O componente salarial {0} não tem código de rubrica do eSocial. "
					"Preencha-o com o código da tabela S-1010 do empregador — sem ele a "
					"verba não pode ser declarada."
				).format(componente)
			)

		itens.append(
			ItemRemuneracao(
				cod_rubr=codigo,
				# `Decimal(str(...))`: o `amount` vem do Frappe como `float`, e
				# `Decimal(float)` traria o erro de representação binária junto. Passar
				# por `str` preserva o número que o usuário vê na tela.
				vr_rubr=Decimal(str(linha.get("amount") or 0)),
				ide_tab_rubr=frappe.db.get_value("Salary Component", componente, "br_ide_tab_rubr") or None,
			)
		)

	if not itens:
		frappe.throw(_("O holerite {0} não tem nenhuma verba declarável.").format(holerite.name))

	return tuple(itens)


def _empregado(nome: str) -> dict:
	dados = frappe.db.get_value("Employee", nome, list(CAMPOS_DO_EMPREGADO), as_dict=True)

	if not dados:
		frappe.throw(_("Empregado {0} não encontrado.").format(nome))

	return dados


def _periodo_de_apuracao(holerite) -> str:
	"""`perApur` no formato `AAAA-MM`, derivado de `start_date`.

	Do início, não do fim: um holerite que atravessa o mês pertence à competência em que
	**começou**, e usar `end_date` deslocaria a folha inteira de um mês num período que
	feche no dia 1º.
	"""
	inicio = _exigir(
		holerite.get("start_date"), _("O holerite {0} não tem data inicial.").format(holerite.name)
	)

	return str(inicio)[:7]


def evento_do_holerite(
	holerite_nome: str,
	id_evento: str,
	ambiente: int,
	ver_proc: str,
	proc_emi: int = 1,
) -> dict:
	"""Monta a árvore do S-1200 a partir de um `Salary Slip`.

	`id_evento` vem de `folha/esocial_id.py` — não é gerado aqui, porque a regra de formação
	é do leiaute e já está no domínio puro.

	Devolve a árvore pronta para `esocial_montagem.montar_evento_assinado`.
	"""
	holerite = frappe.get_doc("Salary Slip", holerite_nome)
	holerite.check_permission("read")

	empregado = _empregado(holerite.employee)
	cnpj = _exigir(
		frappe.db.get_value("Company", holerite.company, "tax_id"),
		_("A empresa {0} não tem CNPJ preenchido.").format(holerite.company),
	)

	cpf = _exigir(
		empregado.get("br_cpf"),
		_("O empregado {0} não tem CPF — o S-1200 o exige.").format(holerite.employee),
	)
	categoria = _exigir(
		empregado.get("br_cod_categoria"),
		_("O empregado {0} não tem categoria do eSocial (codCateg).").format(holerite.employee),
	)
	lotacao = _exigir(
		empregado.get("br_cod_lotacao"),
		_("O empregado {0} não tem código de lotação tributária.").format(holerite.employee),
	)

	itens = itens_do_holerite(holerite)

	# `infoComplem` só é montado quando há CBO: o grupo é opcional, e um `codCBO` vazio
	# dentro dele seria pior que a ausência do grupo inteiro.
	complemento = None

	if empregado.get("br_cod_cbo") and empregado.get("date_of_birth"):
		complemento = InfoComplem(
			nm_trab=empregado.get("employee_name") or "",
			dt_nascto=empregado["date_of_birth"],
			cod_cbo=empregado["br_cod_cbo"],
		)

	from erpnext_brasil.folha.esocial_s1200 import montar_evento_s1200

	return montar_evento_s1200(
		id_evento=id_evento,
		ide_evento=IdeEvento(
			ind_retif=1,
			ind_apuracao=1,
			per_apur=_periodo_de_apuracao(holerite),
			tp_amb=ambiente,
			proc_emi=proc_emi,
			ver_proc=ver_proc,
		),
		ide_empregador=IdeEmpregador(tp_insc=TIPO_INSCRICAO_CNPJ, nr_insc=_digitos(cnpj)),
		ide_trabalhador=IdeTrabalhador(
			cpf_trab=_digitos(cpf),
			nis_trab=_digitos(empregado.get("br_nis")) or None,
			info_complem=complemento,
		),
		dm_dev=(
			DmDev(
				# O nome do holerite é o identificador do demonstrativo: é único no site e
				# rastreia o evento de volta ao documento que o originou, que é o que
				# alguém precisa quando o eSocial rejeita.
				ide_dm_dev=holerite.name,
				cod_categ=int(categoria),
				info_per_apur=InfoPerApur(
					ide_estab_lot=(
						IdeEstabLot(
							tp_insc=TIPO_INSCRICAO_CNPJ,
							nr_insc=_digitos(cnpj),
							cod_lotacao=lotacao,
							remun_per_apur=(
								RemunPerApur(
									itens_remun=itens,
									matricula=empregado.get("employee_number") or None,
								),
							),
						),
					)
				),
			),
		),
	)


def _digitos(valor: str | None) -> str:
	import re

	return re.sub(r"\D", "", valor or "")
