# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Monta `IdentificacaoEcf`/`DadosCadastrais` (`contabil/ecf_bloco_0.py`) a partir de
`Company`/`Address` — mesmo espírito de `integracao/certificado_a1.py`: dado que já
existe cadastrado no ERPNext não deveria ser digitado de novo por quem chama uma função
de montagem de arquivo fiscal.

Por que existe — lembrete direto do usuário: "não esqueça das configurações"
------------------------------------------------------------------------------------------
`ecf_bloco_0.montar_0000`/`montar_0030` são funções puras (não tocam Frappe) — corretas
para testar, mas exigiriam de quem chama datilografar CNPJ, nome, CNAE, endereço de novo,
mesmo esses dados já existindo em `Company`/`Address`. Este módulo fecha essa lacuna do
lado do Frappe, mesma disciplina já aplicada ao certificado A1.

Dois campos novos em `Company`/`Address` (`setup/custom_fields.py`)
------------------------------------------------------------------------------
- `Company.br_natureza_juridica` — não existia; `COD_NAT` do registro `0030` não tem de
  onde vir sem ele. Texto livre (código da tabela de Natureza Jurídica da Receita), mesmo
  padrão de `cnae_principal`.
- `Address.bairro` — **achado real**: o `Address` nativo do ERPNext não tem campo de
  bairro. Não é lacuna nova desta investigação — `xBairro` já era exigido pelo endereço
  da NF-e (`fiscal/documento/elementos_nfe.json`) e nunca tinha campo para vir. O `0030`
  da ECF expõe a mesma lacuna pré-existente; corrigida aqui porque apareceu de novo, não
  porque a ECF a criou.

O que continua **não** vindo de `Company`/`Address` — nível de confiança do
`ecf_bloco_0.md` se mantém
------------------------------------------------------------------------------------------
`indicador_situacao_inicio_periodo`, `tipo_ecf`, `retificadora`, `codigo_versao_leiaute`
continuam parâmetros explícitos de `montar_identificacao_0000` — são decisões por
declaração (varia a cada ECF entregue, não é dado cadastral estável da empresa), não
campo de cadastro. Mesmo raciocínio de `cnpj_emitente` entrar no construtor de
`TransporteSefaz` (estável) enquanto `protocolo`/`justificativa` entram na chamada
(mudam a cada operação) — aqui o cadastro é estável, o período/situação da declaração não.

Sem teste dedicado — depende do Frappe (mesma disciplina de `certificado_a1.py`)
------------------------------------------------------------------------------------------
`frappe.get_doc`/`frappe.db.get_value` só funcionam dentro de um site real.
"""

from datetime import date

import frappe

from erpnext_brasil.contabil.ecf_bloco_0 import DadosCadastrais, IdentificacaoEcf

__all__ = ["montar_dados_cadastrais_0030", "montar_identificacao_0000"]


def montar_identificacao_0000(
	company: str,
	data_inicio: date,
	data_fim: date,
	codigo_versao_leiaute: str,
	indicador_situacao_inicio_periodo: str,
	tipo_ecf: str,
	retificadora: str = "0",
	numero_recibo_anterior: str = "",
) -> IdentificacaoEcf:
	"""Monta `IdentificacaoEcf` lendo `tax_id` (CNPJ) e `company_name` de `Company` —
	o resto continua parâmetro explícito (ver docstring do módulo: são dados da
	declaração, não do cadastro)."""
	empresa = frappe.get_doc("Company", company)

	return IdentificacaoEcf(
		cnpj=empresa.tax_id,
		nome_empresarial=empresa.company_name,
		data_inicio=data_inicio,
		data_fim=data_fim,
		codigo_versao_leiaute=codigo_versao_leiaute,
		indicador_situacao_inicio_periodo=indicador_situacao_inicio_periodo,
		tipo_ecf=tipo_ecf,
		retificadora=retificadora,
		numero_recibo_anterior=numero_recibo_anterior,
	)


def montar_dados_cadastrais_0030(company: str, address: str) -> DadosCadastrais:
	"""Monta `DadosCadastrais` lendo `br_natureza_juridica`/`cnae_principal` de
	`Company` e o endereço de `Address` (`address_line1`/`address_line2`/`bairro`/
	`state`/`codigo_municipio_ibge`/`pincode`/`phone`/`email_id`).

	`address` é passado explicitamente, não resolvido a partir de `Company` sozinho —
	`Company` não tem um endereço "principal" único e sem ambiguidade no ERPNext
	nativo (pode ter vários `Address` vinculados); quem chama decide qual é o
	endereço fiscal, mesma disciplina de `cte_extracao.referencia_cte_do_documento_frete`
	não adivinhar qual `Purchase Invoice` é a fatura de frete.
	"""
	empresa = frappe.get_doc("Company", company)
	endereco = frappe.get_doc("Address", address)

	# Achado real, não corrigido aqui (fora de escopo deste incremento): o `Address`
	# nativo do ERPNext não separa "número" de `address_line1` — só `bairro`
	# (adicionado agora) foi tratado, por ser exigido pelo `0030`/NF-e. `numero` vem
	# vazio até essa segunda lacuna ser fechada à parte.
	return DadosCadastrais(
		natureza_juridica=empresa.get("br_natureza_juridica") or "",
		cnae_fiscal=empresa.get("cnae_principal") or "",
		endereco=endereco.address_line1 or "",
		numero="",
		complemento=endereco.address_line2 or "",
		bairro=endereco.get("bairro") or "",
		uf=endereco.state or "",
		codigo_municipio=endereco.get("codigo_municipio_ibge") or "",
		cep=endereco.pincode or "",
		telefone=endereco.phone or "",
		email=endereco.email_id or "",
	)
