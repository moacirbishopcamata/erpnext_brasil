app_name = "erpnext_brasil"
app_title = "ERPNext Brasil"
app_publisher = "ERPNext Brasil contributors"
app_description = "Localização fiscal brasileira para o ERPNext"
app_email = "-"
app_license = "MIT"

required_apps = ["frappe/erpnext"]

# Transições/animações discretas do Desk (identidade visual) — só opacity/transform
# (aceleradas por GPU, sem reflow de layout) e um único listener de evento, para não
# pesar no desempenho do sistema. Ver `docs/desk-transicoes.md`.
app_include_css = "/assets/erpnext_brasil/css/desk_transitions.css"
app_include_js = "/assets/erpnext_brasil/js/desk_transitions.js"

# `doctype_js` em vez de `app_include_js` para o botão de emissão: ele só faz sentido num
# DocType, e carregar em toda página do Desk seria peso morto em 99% das telas.
doctype_js = {
	"Sales Invoice": "public/js/emissao_nfe.js",
	# A entrada fica no `Purchase Invoice` porque é ali que a nota do fornecedor vira
	# escrituração. O botão só aparece em rascunho: depois do submit o documento já foi
	# escriturado com o que tem.
	"Purchase Invoice": "public/js/entrada_nfe.js",
}

# `doctype_list_js` e não `doctype_js`: o `Arquivo SPED` é o **resultado** da geração, não
# a entrada dela. Um botão no formulário só existiria depois de o registro existir, o que
# é tarde demais — a lista é onde se está quando se quer um arquivo novo.
doctype_list_js = {"Arquivo SPED": "public/js/geracao_efd_list.js"}

# O bloco fiscal roda sem RH nenhum instalado — `hrms` não é obrigatório. Este hook só
# tem efeito quando `hrms` também está instalado: é ele quem lê `regional_overrides`
# (via `hrms.allow_regional`), erpnext_brasil não precisa verificar a presença dele
# aqui. Ver `docs/rh-estado-hrms.md` e `integracao/folha.py`.
regional_overrides = {
	"Brazil": {
		"hrms.payroll.doctype.salary_slip.salary_slip.apply_regional_deductions": (
			"erpnext_brasil.integracao.folha.apply_regional_deductions"
		),
	}
}

after_install = "erpnext_brasil.setup.install.after_install"
after_migrate = "erpnext_brasil.setup.install.after_migrate"

# A validação é ligada em `validate` (não em `on_submit`) para que o erro apareça
# enquanto o usuário ainda está no formulário, não depois de submeter.
doc_events = {
	"Company": {
		"validate": [
			"erpnext_brasil.integracao.party.validar_tax_id",
			"erpnext_brasil.integracao.party.validar_ie",
		]
	},
	"Customer": {
		"validate": [
			"erpnext_brasil.integracao.party.validar_tax_id",
			"erpnext_brasil.integracao.party.validar_ie",
		]
	},
	"Supplier": {
		"validate": [
			"erpnext_brasil.integracao.party.validar_tax_id",
			"erpnext_brasil.integracao.party.validar_ie",
		]
	},
	"Address": {"validate": "erpnext_brasil.integracao.party.validar_codigo_municipio"},
	"Item": {"validate": "erpnext_brasil.integracao.party.validar_ncm"},
	# O livro fiscal do ativo é conferido em `validate` porque as duas configurações que
	# ele recusa — método sobre saldo residual e rateio diário — são **válidas** no
	# ERPNext e produzem números plausíveis. O erro não aparece no primeiro período; sem
	# esta guarda, apareceria só na fiscalização. Ver `integracao/depreciacao_ativo.py`.
	"Asset": {"validate": "erpnext_brasil.integracao.depreciacao_ativo.validar_livro_fiscal"},
}

# A apuração roda em `validate` para que o usuário veja os impostos enquanto ainda pode
# corrigir o documento — em `on_submit` seria tarde. A sugestão de CFOP roda junto
# nesses quatro (documentos com apuração fiscal completa) e também em Pedidos/
# Subcontratação, que não têm apuração (documento interno, sem chave de acesso) mas
# ainda se beneficiam de saber qual CFOP usar quando virarem NF-e depois.
for _doctype in (
	"Sales Invoice",
	"Delivery Note",
	"Purchase Invoice",
	"Purchase Receipt",
):
	doc_events[_doctype] = {
		"validate": [
			# A classificação é conferida antes: não faz sentido apurar impostos de um
			# item cuja combinação de CST e cClassTrib a SEFAZ recusaria.
			"erpnext_brasil.integracao.validacao_fiscal.validar_classificacao_dos_itens",
			"erpnext_brasil.integracao.documento.apurar_impostos",
			"erpnext_brasil.integracao.cfop_sugestao.sugerir_cfop_compra_venda",
			# Depois do CFOP, nunca antes: a natureza é sugerida a partir do código que a
			# linha acima acabou de determinar.
			"erpnext_brasil.integracao.natureza_sugestao.sugerir_natureza_operacao",
			"erpnext_brasil.integracao.chave_acesso_documento.validar_chave_acesso",
		],
		# Em `on_submit`, não em `validate`: o aviso de ambiente de teste só faz sentido
		# quando o documento é efetivado. Em `validate` ele apareceria a cada gravação
		# de rascunho, e alerta repetido é alerta ignorado.
		"on_submit": ["erpnext_brasil.integracao.alerta_fiscal.avisar_ambiente_de_homologacao"],
	}

for _doctype in ("Sales Order", "Purchase Order"):
	doc_events[_doctype] = {"validate": ["erpnext_brasil.integracao.cfop_sugestao.sugerir_cfop_compra_venda"]}

for _doctype in ("Subcontracting Order", "Subcontracting Receipt"):
	doc_events[_doctype] = {
		"validate": ["erpnext_brasil.integracao.cfop_sugestao.sugerir_cfop_subcontratacao"]
	}

# Diário, não horário: o certificado A1 vale um ano, e a regra de aviso
# (`fiscal/documento/validade_certificado.py`) raciocina em dias — verificar de hora em
# hora repetiria o mesmo alerta 24 vezes no dia do marco.
scheduler_events = {
	"daily": [
		"erpnext_brasil.integracao.alerta_certificado.verificar_validade_dos_certificados",
		# Módulo diferente do de cima de propósito: é alerta de risco fiscal, não de
		# certificado. Mesma frequência porque as duas respondem à mesma pergunta —
		# "o que vai parar de funcionar em breve?".
		"erpnext_brasil.integracao.alerta_fiscal.verificar_transicao_da_reforma",
	]
}
