# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Ponto de plugue no `hrms` para as deduções estatutárias brasileiras.

`hrms.payroll.doctype.salary_slip.salary_slip.SalarySlip.apply_regional_deductions` é
decorado com `@hrms.allow_regional` e hoje é um no-op ("Hook point for region-specific
salary slip deductions.") — o hook `regional_overrides` do `hrms` (ver
`docs/rh-estado-hrms.md`) troca essa chamada por `apply_regional_deductions` deste
módulo quando `Company.country == "Brazil"`. Registrado em `hooks.py`.

Camada fina de propósito, como `integracao/documento.py`: toda a conta está em
`folha/inss.py` e `folha/irrf.py` (puras, sem Frappe, testadas); aqui só a tradução
doc↔função e a gravação nas linhas de `deductions`.

Por que só INSS e IRRF aqui, não FGTS
------------------------------------------
`apply_regional_deductions` roda sobre `self.deductions` — a tabela de **descontos do
empregado** no contracheque. FGTS não é desconto do empregado (`docs/rh-fgts.md`) — é
uma obrigação do empregador, por fora do salário líquido, sem linha correspondente
nesta tabela. Plugá-lo aqui produziria um contracheque que mostra ao empregado um
desconto que ele nunca sofre. FGTS fica de fora deste hook; sua integração (relatório
mensal de guia, ou lançamento contábil) é um passo futuro separado.

Método de cálculo do IRRF: sempre via INSS, nunca desconto simplificado
------------------------------------------------------------------------------
A escolha entre desconto simplificado e deduções legais reais (`docs/rh-irrf.md`) é
do contribuinte, e o `hrms` não expõe hoje um campo de "regime escolhido" no
`Salary Slip`. Este módulo sempre usa o INSS como dedução da base do IRRF — a opção
sempre disponível e sem escolha adicional do usuário — deixando o desconto
simplificado como uma evolução futura quando/se o `hrms` tiver onde guardar essa
escolha por funcionário.

Recomputa do zero a cada chamada
------------------------------------
`apply_regional_deductions` roda toda vez que a folha é processada (inclusive na
pré-visualização) — remove as linhas de INSS/IRRF de uma execução anterior antes de
recalcular, mesma disciplina de `integracao.documento._sincronizar_tabela_de_impostos`
reescrever só o que este app gerou, preservando o resto da tabela.

Estado de verificação: exercitado no bench (2026-10-09), sem folha completa
-----------------------------------------------------------------------------------
`tests_bench/test_folha.py` monta um `Salary Slip` real do `hrms` em memória (sem gravar), chama o método
`apply_regional_deductions` do próprio `hrms` — decorado com `allow_regional`, que procura a chave de
`regional_overrides` pelo nome `módulo.função` — e confere que INSS e IRRF entram em `deductions` com o valor da
regra pura, que recalcular não duplica e que as outras deduções ficam. **Não** exercita estrutura salarial,
funcionário e período: o holerite não é gravado nem processado de ponta a ponta. A decisão de país do `hrms` é
`System Settings.country` (`hrms.get_region`), e o módulo confere também `Company.country`.
"""

from decimal import Decimal

import frappe
from frappe import _

from erpnext_brasil.folha.inss import INSSInvalido, calcular_inss
from erpnext_brasil.folha.irrf import IRRFInvalido, calcular_irrf
from erpnext_brasil.folha.periodo import PeriodoInvalido, ano_do_periodo

# Nomes de Salary Component usados pelas linhas que este módulo gera — precisam
# existir previamente (`setup.install.criar_componentes_salariais`).
SALARY_COMPONENT_INSS = "INSS"
SALARY_COMPONENT_IRRF = "IRRF"
COMPONENTES_DESTE_MODULO = (SALARY_COMPONENT_INSS, SALARY_COMPONENT_IRRF)


def _pais_e_brasil(doc) -> bool:
	empresa = doc.get("company")

	if not empresa:
		return False

	return frappe.get_cached_value("Company", empresa, "country") == "Brazil"


def _remover_linhas_deste_modulo(doc) -> None:
	restantes = [
		linha for linha in doc.get("deductions", []) if linha.salary_component not in COMPONENTES_DESTE_MODULO
	]
	doc.set("deductions", [])

	for linha in restantes:
		doc.append("deductions", linha)


def apply_regional_deductions(doc, method=None):
	"""Adiciona INSS e IRRF às deduções do `Salary Slip` — ponto de plugue do hook
	`regional_overrides` do `hrms` para `Company.country == "Brazil"`."""
	if not _pais_e_brasil(doc):
		return

	_remover_linhas_deste_modulo(doc)

	bruto = Decimal(str(doc.get("gross_pay") or 0))

	# O ano vem do período do holerite, nunca do padrão das funções puras: com o padrão, a folha de
	# 2027 sairia com a tabela de 2026 e sem erro. Ano sem tabela (ou período sem data) recusa o holerite.
	try:
		ano = ano_do_periodo(doc.get("end_date"), doc.get("start_date"))
		inss = calcular_inss(bruto, ano=ano)
		irrf = calcular_irrf(bruto, bruto - inss, ano=ano)
	except (PeriodoInvalido, INSSInvalido, IRRFInvalido) as erro:
		frappe.throw(str(erro), title=_("Folha sem tabela de INSS e IRRF"))

	doc.append("deductions", {"salary_component": SALARY_COMPONENT_INSS, "amount": float(inss)})
	doc.append("deductions", {"salary_component": SALARY_COMPONENT_IRRF, "amount": float(irrf)})
