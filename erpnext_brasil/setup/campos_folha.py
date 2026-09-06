# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Campos que o eSocial exige e o ERPNext/hrms não têm.

Separado de `custom_fields.py` porque depende de outro app: `Salary Component` vem do
`hrms`, que é **opcional** neste projeto (o bloco fiscal roda sem RH nenhum). Misturá-los
faria a instalação fiscal depender de um app que ela não usa.

O que **não** se declarou, e por quê
-------------------------------------------
A regra é a mesma que evitou um `br_conta` no `Bank Account` e um `br_taxa_depreciacao` no
`Asset`: **não criar segunda verdade sobre o mesmo dado**.

| Dado do eSocial | De onde vem | Por que não virou campo |
|---|---|---|
| `dtNascto` | `Employee.date_of_birth` | já existe, e é o que o resto do RH usa |
| `matricula` | `Employee.employee_number` | idem — o eSocial aceita a matrícula do empregador |
| `nmTrab` | `Employee.employee_name` | idem |

Um campo novo ao lado de qualquer um desses produziria duas datas de nascimento, e a
divergência apareceria no dia em que alguém corrigisse uma e não a outra.

⚠️ O que **precisou** de campo novo
------------------------------------------
Tudo o que é vocabulário do eSocial e não existe em lugar nenhum do ERPNext: CPF, NIS,
categoria do trabalhador, CBO, lotação e — do lado da folha — o código da rubrica.

**A rubrica é a peça central.** O S-1200 declara cada verba por `codRubr`, e esse código
vem da **tabela de rubricas do próprio empregador** (evento S-1010) — não há tabela
nacional a consultar. Sem ele, um `Salary Component` não tem como virar linha de
`itensRemun`, e a folha inteira fica sem como ser declarada.
"""

__all__ = ["get_custom_fields"]

CATEGORIAS_COMUNS = "\n".join(
	[
		"",
		"101 - Empregado - Geral",
		"102 - Empregado - Trabalhador rural",
		"103 - Empregado - Aprendiz",
		"104 - Empregado - Doméstico",
		"105 - Empregado - Contrato a termo firmado nos termos da Lei 9.601/98",
		"111 - Empregado - Contrato de trabalho intermitente",
		"701 - Contribuinte individual - Autônomo em geral",
		"711 - Contribuinte individual - Diretor não empregado com FGTS",
	]
)
"""Recorte da **Tabela 01** do eSocial, não a tabela inteira.

⚠️ Declarado como recorte de propósito: a tabela oficial tem dezenas de categorias, e uma
lista fechada aqui recusaria contratações legítimas. O campo é `Data` com sugestões, não um
`Select` — quem tem categoria fora desta lista digita o código, e o eSocial valida.

Os oito acima cobrem a folha comum de uma empresa; os rótulos são abreviados para caber na
tela, e o que vale é o código de 3 dígitos antes do hífen.
"""


def get_custom_fields() -> dict[str, list[dict]]:
	"""Mapa {DocType: campos} do bloco de folha.

	`Salary Component` só existe com o `hrms` instalado — quem chama filtra os DocTypes
	ausentes antes de criar (ver `setup/install.py`).
	"""
	return {
		"Employee": [
			{
				"fieldname": "br_secao_esocial_br",
				"label": "eSocial (Brasil)",
				"fieldtype": "Section Break",
				"insert_after": "date_of_birth",
				"collapsible": 1,
			},
			{
				"fieldname": "br_cpf",
				"label": "CPF",
				"fieldtype": "Data",
				"length": 14,
				"insert_after": "br_secao_esocial_br",
				"description": (
					"Identifica o trabalhador em todo evento do eSocial (`cpfTrab`). "
					"Sem ele o S-1200 não pode ser montado."
				),
			},
			{
				"fieldname": "br_nis",
				"label": "NIS (PIS/PASEP/NIT)",
				"fieldtype": "Data",
				"length": 11,
				"insert_after": "br_cpf",
				"description": (
					"Opcional no leiaute e exigido por várias regras de negócio — preencher "
					"evita rejeição que só aparece na transmissão."
				),
			},
			{
				"fieldname": "br_cod_categoria",
				"label": "Categoria do Trabalhador",
				"fieldtype": "Data",
				"length": 3,
				"insert_after": "br_nis",
				"description": (
					"Código de 3 dígitos da Tabela 01 do eSocial (`codCateg`). "
					f"Comuns: {CATEGORIAS_COMUNS.strip().splitlines()[0]}…"
				),
			},
			{
				"fieldname": "br_coluna_esocial_br",
				"fieldtype": "Column Break",
				"insert_after": "br_cod_categoria",
			},
			{
				"fieldname": "br_cod_cbo",
				"label": "CBO",
				"fieldtype": "Data",
				"length": 6,
				"insert_after": "br_coluna_esocial_br",
				"description": (
					"Classificação Brasileira de Ocupações, 6 dígitos. Fica no `Employee` e "
					"não na `Designation` porque dois empregados com o mesmo cargo podem ter "
					"CBO diferente."
				),
			},
			{
				"fieldname": "br_cod_lotacao",
				"label": "Código da Lotação Tributária",
				"fieldtype": "Data",
				"length": 30,
				"insert_after": "br_cod_cbo",
				"description": (
					"`codLotacao` do S-1200, definido pelo empregador no evento S-1020. "
					"Não há tabela nacional: é cadastro de quem declara."
				),
			},
		],
		"Salary Component": [
			{
				"fieldname": "br_secao_esocial_br",
				"label": "eSocial (Brasil)",
				"fieldtype": "Section Break",
				"insert_after": "type",
				"collapsible": 1,
			},
			{
				"fieldname": "br_cod_rubrica",
				"label": "Código da Rubrica (eSocial)",
				"fieldtype": "Data",
				"length": 30,
				"insert_after": "br_secao_esocial_br",
				"description": (
					"`codRubr` do S-1200, da tabela de rubricas do empregador (evento S-1010). "
					"Não há tabela nacional. Componente sem código não entra no evento — e "
					"isso é recusado alto, não ignorado."
				),
			},
			{
				"fieldname": "br_ide_tab_rubr",
				"label": "Identificador da Tabela de Rubricas",
				"fieldtype": "Data",
				"length": 8,
				"insert_after": "br_cod_rubrica",
				"description": (
					"`ideTabRubr` — identifica **qual versão** da tabela de rubricas o código "
					"acima pertence. Vazio é aceito pelo leiaute."
				),
			},
		],
	}
