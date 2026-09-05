# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Mapeia um documento do ERPNext para a árvore da NF-e.

Fecha metade do gap 1.3 de `docs/gaps.md`: a cadeia de emissão inteira existia — montagem,
certificado, assinatura, transporte, DocType de persistência — e **nada ligava um
documento a ela**. Faltava exatamente esta camada: ler um `Sales Invoice` e produzir o que
`fiscal/documento/nfe.montar_nfe` espera.

Não calcula imposto: reaproveita a mesma apuração
---------------------------------------------------------
`documento.apurar_impostos` já roda no `validate` e grava os valores nos campos `br_*`.
Aqui a apuração é **recalculada** pelas mesmas funções (`mapeamento.item_fiscal_de_linha`
e `operacao_de_documento`), não lida dos campos gravados. Parece desperdício e não é:

- `montar_imposto_item` precisa do objeto `ApuracaoItem` inteiro, não dos dez números
  soltos — reconstruí-lo a partir dos campos seria uma segunda tradução, com sua própria
  chance de divergir;
- recalcular da mesma fonte garante que o XML transmitido e os valores exibidos na tela
  descrevem a mesma operação. Divergirem seria pior que qualquer custo de CPU.

O que este módulo **se recusa** a inventar
--------------------------------------------------
Falha alto em vez de escolher por conta própria:

- **`transp` e `pag`** são obrigatórios no XSD, e `montar_infnfe` já recusa sem eles.
  "Sem transporte" (`modFrete="9"`) e "sem pagamento a destacar" (`tPag="90"`) são
  **afirmações sobre a operação**, não padrões razoáveis de assumir — vêm de quem chama.
- **Natureza da operação, NCM, CFOP, CST do ICMS, endereço, indicador de IE**: sem eles
  não há documento. Cada ausência levanta `DadosInsuficientes` dizendo qual campo falta e
  **em qual cadastro** — mensagem que manda a pessoa ao lugar certo, não "erro ao emitir".

O **CST do ICMS** entrou nessa lista em 2026-09-05, e vale registrar como: `montar_imposto_item`
recebe o CST por parâmetro e **recusa** o que não sabe montar. A primeira versão deste
módulo não o passava, e a emissão teria falhado no primeiro clique — com `ImpostoInvalido`
no meio da montagem, depois de o usuário confirmar. Não havia campo nenhum guardando o
CST; `br_cst_icms` foi criado junto, como `Select` restrito a
`imposto_item.CST_ICMS_SUPORTADOS`, para que a recusa vire uma opção que não existe na
tela em vez de erro em tempo de execução.

Já o **código numérico** (`cNF`) é sorteado aqui, e isso não é inventar dado de negócio: o
leiaute pede um número cuja única regra é não repetir o `nNF` nem ter todos os dígitos
iguais (rejeição 897, regra B03-10). É ruído por definição — pedi-lo ao usuário seria
transferir uma exigência de formato a quem não tem como responder.

O indicador de IE é traduzido, não repassado
----------------------------------------------------
`br_indicador_ie` guarda texto legível ("Contribuinte ICMS"), porque é o que o usuário
escolhe numa tela. O `indIEDest` do leiaute é `"1"`/`"2"`/`"9"`. `INDICADOR_IE_POR_ROTULO`
faz a ponte, e há teste garantindo que ela cobre exatamente as opções que
`setup/custom_fields.INDICADORES_IE` oferece — se alguém acrescentar uma opção na tela sem
mapeá-la aqui, o teste falha em vez de a emissão quebrar no cliente.

Estado de verificação: camada Frappe, ainda **não** exercitada contra bench real — é a
lacuna registrada em `docs/gaps.md`, seção 2.
"""

import frappe

from erpnext_brasil.fiscal.codigos.uf import codigo_da_uf
from erpnext_brasil.fiscal.documento.imposto_item import montar_imposto_item
from erpnext_brasil.fiscal.documento.nfe import (
	DESTINO_INTERESTADUAL,
	DESTINO_INTERNA,
	MODELO_NFE,
	Destinatario,
	Emitente,
	Identificacao,
	montar_infnfe,
	montar_nfe,
	sortear_codigo_numerico,
)
from erpnext_brasil.fiscal.documento.produto import montar_icmstot, montar_prod
from erpnext_brasil.fiscal.impostos.apuracao import apurar_documento
from erpnext_brasil.integracao.mapeamento import item_fiscal_de_linha, operacao_de_documento
from erpnext_brasil.integracao.rastreabilidade import montar_rastro_da_linha
from erpnext_brasil.setup.custom_fields import CRT_POR_REGIME, INDICADOR_IE_POR_ROTULO

__all__ = ["DadosInsuficientes", "montar_nfe_do_documento"]


# Campos do cabeçalho que a apuração consome — a mesma lista de `documento.apurar_impostos`.
_CAMPOS_DO_CABECALHO = (
	"br_indicador_ie",
	"br_destinado_a_revenda",
	"br_regime_pis_cofins",
	"br_ano_competencia",
	"br_excluir_icms_pis_cofins",
	"posting_date",
	"transaction_date",
)


class DadosInsuficientes(ValueError):
	"""O documento não tem o que a NF-e exige — nunca preenchido por suposição."""


def _exigir(valor, campo: str, onde: str) -> str:
	texto = str(valor or "").strip()

	if not texto:
		raise DadosInsuficientes(f"{campo} é obrigatório na NF-e e está vazio em {onde}")

	return texto


def _endereco_vinculado(doctype: str, nome: str) -> dict:
	"""O `Address` ligado à parte, como `dict`. Vazio quando não há."""
	ligacao = frappe.get_all(
		"Dynamic Link",
		filters={"link_doctype": doctype, "link_name": nome},
		fields=["parent"],
		limit=1,
		parent_doctype="Address",
	)

	if not ligacao:
		return {}

	return frappe.get_cached_doc("Address", ligacao[0].parent).as_dict()


def _grupo_endereco(endereco: dict, onde: str) -> dict:
	"""O sub-grupo `enderEmit`/`enderDest`, com as tags do leiaute.

	`Emitente.endereco` e `Destinatario.endereco` são `dict` repassados direto ao XML —
	montá-los é responsabilidade de quem conhece o cadastro, que é esta camada.
	"""
	return {
		"xLgr": _exigir(endereco.get("address_line1"), "logradouro", onde),
		"nro": _exigir(endereco.get("numero_endereco"), "número do endereço", onde),
		"xBairro": _exigir(endereco.get("bairro"), "bairro", onde),
		"cMun": _exigir(endereco.get("codigo_municipio_ibge"), "código IBGE do município", onde),
		"xMun": _exigir(endereco.get("city"), "município", onde),
		"UF": _exigir(endereco.get("state"), "UF", onde),
		"CEP": _exigir(endereco.get("pincode"), "CEP", onde).replace("-", ""),
	}


def _emitente(company: str) -> tuple[Emitente, dict]:
	"""O emitente e seu endereço já montado — o endereço volta junto porque o `cUF` e o
	`cMunFG` do `ide` saem dele, e relê-lo seria abrir espaço para divergir."""
	empresa = frappe.get_cached_doc("Company", company)
	onde = f"endereço da Company {company}"
	endereco = _grupo_endereco(_endereco_vinculado("Company", company), onde)

	emitente = Emitente(
		cnpj=_exigir(empresa.get("tax_id"), "CNPJ do emitente", f"Company {company}"),
		nome=_exigir(empresa.get("company_name"), "razão social", f"Company {company}"),
		inscricao_estadual=_exigir(
			empresa.get("inscricao_estadual"), "inscrição estadual", f"Company {company}"
		),
		regime_tributario=_regime_tributario(empresa, company),
		endereco=endereco,
	)

	return emitente, endereco


def _regime_tributario(empresa, company: str) -> str:
	rotulo = _exigir(empresa.get("regime_tributario"), "regime tributário", f"Company {company}")
	crt = CRT_POR_REGIME.get(rotulo)

	if not crt:
		raise DadosInsuficientes(
			f"regime tributário {rotulo!r} da Company {company} não tem CRT correspondente; "
			f"esperado um de {sorted(CRT_POR_REGIME)}"
		)

	return crt


def _destinatario(doc) -> Destinatario:
	cliente = _exigir(doc.get("customer"), "cliente", f"{doc.doctype} {doc.name}")
	parte = frappe.get_cached_doc("Customer", cliente)
	rotulo = _exigir(doc.get("br_indicador_ie"), "indicador de IE", f"{doc.doctype} {doc.name}")
	indicador = INDICADOR_IE_POR_ROTULO.get(rotulo)

	if not indicador:
		raise DadosInsuficientes(
			f"indicador de IE {rotulo!r} não tem indIEDest correspondente; "
			f"esperado um de {sorted(INDICADOR_IE_POR_ROTULO)}"
		)

	documento = "".join(c for c in str(parte.get("tax_id") or "") if c.isalnum())

	return Destinatario(
		nome=_exigir(parte.get("customer_name"), "nome do destinatário", f"Customer {cliente}"),
		indicador_ie=indicador,
		cnpj_cpf=_exigir(documento, "CNPJ/CPF do destinatário", f"Customer {cliente}"),
		inscricao_estadual=str(parte.get("inscricao_estadual") or "").strip(),
		endereco=_grupo_endereco(_endereco_vinculado("Customer", cliente), f"endereço do Customer {cliente}"),
	)


def _identificacao(doc, endereco_emitente: dict, serie: str, ambiente: str) -> Identificacao:
	"""O grupo `ide`. `cUF` e `cMunFG` saem do endereço do **emitente** — é onde o fato
	gerador ocorre, não onde o destinatário está."""
	uf_emitente = endereco_emitente["UF"]
	uf_destino = _grupo_endereco(
		_endereco_vinculado("Customer", doc.get("customer")), "endereço do destinatário"
	)["UF"]

	numero = _exigir(doc.get("br_numero_nfe"), "número da NF-e", f"{doc.doctype} {doc.name}")

	return Identificacao(
		uf=codigo_da_uf(uf_emitente),
		municipio_fato_gerador=endereco_emitente["cMun"],
		natureza_operacao=_exigir(
			doc.get("br_natureza_operacao"), "natureza da operação", f"{doc.doctype} {doc.name}"
		),
		serie=serie,
		numero=numero,
		codigo_numerico=sortear_codigo_numerico(numero),
		emissao=frappe.utils.get_datetime(doc.get("posting_date")),
		destino=DESTINO_INTERNA if uf_destino == uf_emitente else DESTINO_INTERESTADUAL,
		modelo=MODELO_NFE,
		ambiente="1" if ambiente == "producao" else "2",
	)


def _itens(doc):
	"""Os itens e as apurações, na mesma ordem — devolvidos juntos porque `montar_icmstot`
	precisa dos dois e emparelhá-los de novo lá fora abriria espaço para desalinhar."""
	cabecalho = {campo: doc.get(campo) for campo in _CAMPOS_DO_CABECALHO}
	operacao = operacao_de_documento(cabecalho)
	apuracao = apurar_documento([item_fiscal_de_linha(linha.as_dict()) for linha in doc.items], operacao)

	itens = []
	produtos = []

	for linha, resultado in zip(doc.items, apuracao.itens, strict=True):
		item = frappe.get_cached_doc("Item", linha.item_code)
		onde = f"Item {linha.item_code}"

		prod = montar_prod(
			codigo=linha.item_code,
			descricao=_exigir(linha.get("description") or item.get("item_name"), "descrição", onde),
			ncm=_exigir(item.get("ncm"), "NCM", onde),
			cfop=_exigir(linha.get("br_cfop_sugerido"), "CFOP", f"linha do {onde}"),
			unidade=_exigir(linha.get("uom") or item.get("stock_uom"), "unidade", onde),
			quantidade=linha.get("qty"),
			valor_unitario=linha.get("rate"),
			valor_total=linha.get("amount"),
			cest=str(item.get("cest") or "").strip(),
			# Rastreabilidade: `montar_rastro_da_linha` devolve lista vazia quando a linha
			# não tem lote, que é o caso da maioria dos produtos. Passar a lista vazia é o
			# mesmo que não passar — `montar_prod` omite o grupo, e ausência de rastro não
			# é erro, é a norma.
			lotes=montar_rastro_da_linha(linha),
		)

		produtos.append(prod)
		# Sem `@nItem`: `montar_infnfe` numera os itens na ordem em que os recebe. Numerar
		# aqui também criaria duas fontes para o mesmo dado — e a de lá venceria em
		# silêncio, escondendo qualquer divergência.
		itens.append(
			{
				"prod": prod,
				"imposto": montar_imposto_item(
					resultado,
					cst_icms=_exigir(linha.get("br_cst_icms"), "CST do ICMS", f"linha do {onde}"),
				),
			}
		)

	return itens, produtos, apuracao


def montar_nfe_do_documento(doc, serie: str, ambiente: str, transp: dict, pag: dict, cobr=None) -> dict:
	"""A árvore `NFe` completa e **ainda não assinada**, a partir de um documento.

	`transp` e `pag` vêm de quem chama porque descrevem fatos da operação que este módulo
	não tem como saber — ver docstring do módulo.
	"""
	if not doc.get("items"):
		raise DadosInsuficientes(f"{doc.doctype} {doc.name} não tem itens")

	emitente, endereco_emitente = _emitente(_exigir(doc.get("company"), "empresa", doc.name))
	itens, produtos, apuracao = _itens(doc)

	return montar_nfe(
		montar_infnfe(
			identificacao=_identificacao(doc, endereco_emitente, serie, ambiente),
			emitente=emitente,
			destinatario=_destinatario(doc),
			itens=itens,
			totais=montar_icmstot(apuracao.itens, produtos),
			transp=transp,
			pag=pag,
			cobr=cobr,
		)
	)
