# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Monta `Identificacao`/`Participante`/`Item` (`contabil/efd_bloco_0.py`) a partir de
`Company`/`Address`/`Customer`/`Supplier`/`Item` — mesma disciplina de
`integracao/ecf_dados_empresa.py` e `integracao/certificado_a1.py`.

Por que existe — lembrete direto do usuário: "não esqueça das configurações"
------------------------------------------------------------------------------------------
Os módulos do EFD (`efd_bloco_0`, `efd_bloco_c`, `efd_bloco_9`, ...) são funções puras:
corretas para testar sem bench, mas exigiriam de quem chama datilografar CNPJ, nome,
inscrição estadual, código IBGE, NCM de novo — dados que já estão cadastrados no
ERPNext. Este módulo fecha essa lacuna do lado do Frappe.

Campos novos que a EFD exigiu (`setup/custom_fields.py`)
--------------------------------------------------------------
Nenhum destes existia; sem eles o registro correspondente não tem de onde vir:

- **`Company.br_efd_perfil`** (`IND_PERFIL` do `0000`) — A, B ou C. Não é escolha da
  empresa: a SEFAZ do estado define, e o perfil decide quais registros o arquivo precisa
  conter. Por isso é cadastro, não parâmetro de chamada.
- **`Company.br_efd_atividade`** (`IND_ATIV` do `0000`) — industrial/equiparado ou
  outros.
- **`Company.br_efd_versao_leiaute`** (`COD_VER` do `0000`) — vale a versão vigente na
  data final da escrituração, e muda com o tempo; constante no código envelheceria em
  silêncio.
- **`Company.suframa`** (`SUFRAMA` do `0000`) — **achado real**: `Customer`/`Supplier`
  já tinham o campo (`_campos_de_parte`), a `Company` não. A EFD o exige de quem é
  inscrito, e o `0150` já o exigia do participante — a lacuna era só do lado da própria
  empresa.
- **`Item.br_efd_tipo_item`** (`TIPO_ITEM` do `0200`, obrigatório) — **sem equivalente
  nativo**. `producao_propria` e `finalidade_compra`, que este projeto já tinha,
  respondem a outra pergunta (qual CFOP usar), não a esta classificação de estoque do
  Fisco: um item pode ser de produção própria e ser "04 - Produto Acabado" ou "05 -
  Subproduto", e a compra para industrialização pode virar "01 - Matéria-Prima", "02 -
  Embalagem" ou "10 - Outros insumos". Reaproveitar um pelo outro erraria.
- **`Item.br_efd_codigo_genero`** (`COD_GEN`) e **`Item.br_ex_ipi`** (`EX_IPI`).

As opções do Select de `br_efd_tipo_item` saem da **mesma tabela** que
`efd_bloco_0.TIPOS_ITEM` usa para validar o registro — se fossem duas listas escritas
separadamente, um valor aceito na tela seria recusado na montagem do arquivo, e ninguém
descobriria até o Fisco recusar.

O Select guarda `"código - descrição"`, o registro quer só o código
--------------------------------------------------------------------------
Convenção já usada em `ORIGENS_MERCADORIA`: a tela mostra `"04 - Produto Acabado"`
(legível), e `_codigo_do_select` extrai o `"04"` na fronteira. A extração fica aqui, num
lugar só, em vez de cada chamador fatiar a string do seu jeito.

O que continua **não** vindo do cadastro
-----------------------------------------------
`data_inicial`/`data_final` (o período escriturado) e `finalidade` (arquivo original ou
substituto) continuam parâmetros explícitos: são decisões de cada entrega, não dado
cadastral estável — mesmo raciocínio de `ecf_dados_empresa.montar_identificacao_0000`.

Sem teste dedicado — depende do Frappe (mesma disciplina dos módulos irmãos); a
cobertura real fica em `tests_bench/`, quando houver.
"""

import frappe

from erpnext_brasil.contabil.efd_bloco_0 import (
	ATIVIDADE_INDUSTRIAL,
	ATIVIDADE_OUTROS,
	FINALIDADE_ORIGINAL,
	Identificacao,
	Item,
	Participante,
)

__all__ = [
	"montar_identificacao_0000",
	"montar_item_0200",
	"montar_participante_0150",
]

_CODIGO_PAIS_BRASIL = "01058"
"""Código do Brasil na tabela de países do SPED (item 3.2.1), que segue os códigos do
BACEN. Usado como padrão para participante sem país informado — o caso esmagadoramente
majoritário; participante estrangeiro exige o código explícito de quem chama."""


def _codigo_do_select(valor: str) -> str:
	"""Extrai o código de um valor de Select no formato `"código - descrição"`.

	Devolve string vazia quando o campo está em branco — ausência de configuração é
	estado normal (o registro é que vai recusar, com mensagem própria), não erro desta
	função.
	"""
	if not valor:
		return ""

	return valor.split(" - ", 1)[0].strip()


def montar_identificacao_0000(
	company: str,
	address: str,
	data_inicial: str,
	data_final: str,
	finalidade: str = FINALIDADE_ORIGINAL,
) -> Identificacao:
	"""Monta `Identificacao` (registro `0000`) lendo `Company` e o `Address` fiscal.

	`address` é passado explicitamente, não deduzido: a `Company` pode ter vários
	`Address` vinculados e o ERPNext nativo não tem um "endereço fiscal" único sem
	ambiguidade — quem chama decide, mesma disciplina de
	`ecf_dados_empresa.montar_dados_cadastrais_0030`.
	"""
	empresa = frappe.get_doc("Company", company)
	endereco = frappe.get_doc("Address", address)

	atividade = (
		ATIVIDADE_INDUSTRIAL
		if (empresa.get("br_efd_atividade") or "").startswith("Industrial")
		else ATIVIDADE_OUTROS
	)

	return Identificacao(
		codigo_versao=empresa.get("br_efd_versao_leiaute") or "",
		finalidade=finalidade,
		data_inicial=data_inicial,
		data_final=data_final,
		nome=empresa.company_name,
		cnpj=empresa.tax_id or "",
		uf=endereco.get("state") or "",
		inscricao_estadual=empresa.get("inscricao_estadual") or "",
		codigo_municipio=endereco.get("codigo_municipio_ibge") or "",
		inscricao_municipal=empresa.get("inscricao_municipal") or "",
		suframa=empresa.get("suframa") or "",
		perfil=empresa.get("br_efd_perfil") or "",
		atividade=atividade,
	)


def montar_participante_0150(doctype: str, nome: str, address: str = "") -> Participante:
	"""Monta `Participante` (registro `0150`) a partir de um `Customer` ou `Supplier`.

	    `address` é opcional: sem ele, os campos de endereço saem vazios — que é o
	    comportamento correto, já que `END`/`NUM`/`COMPL`/`BAIRRO` são "obrigatórios quando
	    houver" no layout, não obrigatórios sempre.

	O CPF/CNPJ vem de `tax_id` (campo nativo, onde este projeto sempre o guarda) e é
	    classificado pelo comprimento: 14 dígitos é CNPJ, 11 é CPF. Sem `tax_id`, os dois
	    campos ficam vazios — participante estrangeiro é caso válido no layout.
	"""
	if doctype not in ("Customer", "Supplier"):
		raise ValueError(f"participante do 0150 é Customer ou Supplier, recebido {doctype!r}")

	parte = frappe.get_doc(doctype, nome)

	documento = "".join(c for c in (parte.get("tax_id") or "") if c.isdigit())
	cnpj = documento if len(documento) == 14 else ""
	cpf = documento if len(documento) == 11 else ""

	endereco = frappe.get_doc("Address", address) if address else None

	return Participante(
		codigo=parte.name,
		nome=parte.get("customer_name") or parte.get("supplier_name") or parte.name,
		codigo_pais=_CODIGO_PAIS_BRASIL,
		cnpj=cnpj,
		cpf=cpf,
		inscricao_estadual=parte.get("inscricao_estadual") or "",
		codigo_municipio=(endereco.get("codigo_municipio_ibge") or "") if endereco else "",
		suframa=parte.get("suframa") or "",
		endereco=(endereco.get("address_line1") or "") if endereco else "",
		numero=(endereco.get("numero_endereco") or "") if endereco else "",
		complemento=(endereco.get("address_line2") or "") if endereco else "",
		bairro=(endereco.get("bairro") or "") if endereco else "",
	)


def montar_item_0200(item_code: str) -> Item:
	"""Monta `Item` (registro `0200`) a partir do `Item` do ERPNext.

	`UNID_INV` sai de `stock_uom` (a unidade de estoque nativa) — é exatamente o que o
	campo pede ("unidade de medida utilizada na quantificação de estoques"), e a mesma
	unidade tem de aparecer num registro `0190` do arquivo.
	"""
	item = frappe.get_doc("Item", item_code)

	return Item(
		codigo=item.name,
		descricao=item.item_name or item.name,
		unidade_inventario=item.stock_uom or "",
		tipo=_codigo_do_select(item.get("br_efd_tipo_item") or ""),
		codigo_ncm=item.get("ncm") or "",
		ex_ipi=item.get("br_ex_ipi") or "",
		codigo_genero=item.get("br_efd_codigo_genero") or "",
		codigo_lista_servico=item.get("codigo_servico_lc116") or "",
		cest=item.get("cest") or "",
	)
