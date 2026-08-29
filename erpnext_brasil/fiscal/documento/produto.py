# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Grupos `prod` (produto do item) e `ICMSTot` (totais do documento).

`prod` — o que é vendido
------------------------
Descreve a mercadoria: código, descrição, NCM, CFOP, unidade, quantidade e valor. Não
contém imposto — o grupo `imposto` é irmão dele dentro de `det`.

Duas armadilhas que o layout guarda:

- **`cEAN` é obrigatório**, mas produto sem código de barras informa o literal
  ``SEM GTIN``. Deixar vazio é rejeição; inventar um EAN é pior.
- **Unidade comercial e tributável são campos distintos** (`uCom`/`qCom` e
  `uTrib`/`qTrib`). Quase sempre coincidem, e por isso quase sempre são preenchidas com o
  mesmo valor — mas quem vende em caixa e tributa em unidade precisa das duas, e o layout
  não deixa omitir.

`indTot` diz se o valor do item **compõe** o total da nota. Vale `0` em item acessório
que já está embutido em outro; o padrão é `1`.

`ICMSTot` — os totais
---------------------
Somam-se os **valores já arredondados de cada item**, nunca se recalcula sobre a base
agregada: o validador confere o total contra a soma dos itens, e recalcular produz a
rejeição de "total diverge da soma".

Todos os campos são informados, **zerados quando não houver valor** — omitir campo de
total é rejeição, não economia.

Funções puras: nenhuma dependência do Frappe.
"""

from decimal import Decimal

from erpnext_brasil.fiscal.impostos.icms import arredondar

__all__ = ["SEM_GTIN", "ProdutoInvalido", "montar_icmstot", "montar_prod"]

SEM_GTIN = "SEM GTIN"
ZERO = Decimal("0.00")


class ProdutoInvalido(ValueError):
	"""Dado do produto que impediria a autorização."""

	def __init__(self, mensagem: str, campo: str = ""):
		super().__init__(mensagem)
		self.campo = campo


def _valor(quantia) -> str:
	"""Formata valor monetário com as duas casas do layout."""
	return str(arredondar(Decimal(str(quantia or 0))))


def _quantidade(quantia) -> str:
	"""Quantidade admite quatro casas — o layout é mais preciso aqui que em valor."""
	return str(Decimal(str(quantia or 0)).quantize(Decimal("0.0001")))


def _exigir(valor, campo: str) -> str:
	texto = str(valor or "").strip()

	if not texto:
		raise ProdutoInvalido(f"O campo {campo} é obrigatório no grupo prod", campo)

	return texto


def montar_prod(
	codigo: str,
	descricao: str,
	ncm: str,
	cfop: str,
	unidade: str,
	quantidade,
	valor_unitario,
	valor_total,
	ean: str = "",
	unidade_tributavel: str = "",
	quantidade_tributavel=None,
	valor_unitario_tributavel=None,
	cest: str = "",
	frete=None,
	seguro=None,
	desconto=None,
	outras_despesas=None,
	compoe_total: bool = True,
) -> dict:
	"""Monta o grupo `prod` de um item.

	Unidade e quantidade tributáveis, quando omitidas, repetem as comerciais — que é o
	caso da esmagadora maioria dos itens. Repetir é obrigatório: o layout não admite
	omitir, e deixar o usuário preencher duas vezes o mesmo dado só produziria divergência.
	"""
	ncm_limpo = _exigir(ncm, "NCM").replace(".", "")

	if not ncm_limpo.isdigit() or len(ncm_limpo) != 8:
		raise ProdutoInvalido(f"NCM deve ter 8 dígitos, recebido {ncm!r}", "ncm")

	cfop_limpo = _exigir(cfop, "CFOP")

	if not cfop_limpo.isdigit() or len(cfop_limpo) != 4:
		raise ProdutoInvalido(f"CFOP deve ter 4 dígitos, recebido {cfop!r}", "cfop")

	grupo = {
		"cProd": _exigir(codigo, "código do produto"),
		# Produto sem código de barras informa o literal, nunca vazio.
		"cEAN": (ean or "").strip() or SEM_GTIN,
		"xProd": _exigir(descricao, "descrição do produto"),
		"NCM": ncm_limpo,
	}

	if cest:
		grupo["CEST"] = cest.strip()

	grupo["CFOP"] = cfop_limpo
	grupo["uCom"] = _exigir(unidade, "unidade comercial")
	grupo["qCom"] = _quantidade(quantidade)
	grupo["vUnCom"] = _valor(valor_unitario)
	grupo["vProd"] = _valor(valor_total)

	grupo["cEANTrib"] = grupo["cEAN"]
	grupo["uTrib"] = (unidade_tributavel or "").strip() or grupo["uCom"]
	grupo["qTrib"] = (
		_quantidade(quantidade_tributavel) if quantidade_tributavel is not None else grupo["qCom"]
	)
	grupo["vUnTrib"] = (
		_valor(valor_unitario_tributavel)
		if valor_unitario_tributavel is not None
		else grupo["vUnCom"]
	)

	# Acessórios entram apenas quando houver valor: campo zerado aqui é ruído, e o layout
	# os trata como opcionais no item (diferente do grupo de totais).
	for nome, quantia in (
		("vFrete", frete),
		("vSeg", seguro),
		("vDesc", desconto),
		("vOutro", outras_despesas),
	):
		if quantia:
			grupo[nome] = _valor(quantia)

	grupo["indTot"] = "1" if compoe_total else "0"

	return grupo


def montar_icmstot(apuracoes: list, produtos: list[dict] | None = None) -> dict:
	"""Monta `ICMSTot` a partir das apurações dos itens.

	`produtos` permite somar frete, seguro, desconto e outras despesas tal como foram
	informados no item — se recalculados aqui, divergiriam do que consta em cada `prod`.
	"""
	if not apuracoes:
		raise ProdutoInvalido("Não há itens para totalizar", "itens")

	def somar(extrair) -> Decimal:
		return sum((extrair(a) for a in apuracoes), ZERO)

	def somar_produto(campo: str) -> Decimal:
		if not produtos:
			return ZERO

		return sum((Decimal(p.get(campo, "0")) for p in produtos), ZERO)

	base_icms = somar(lambda a: a.icms.base)
	icms = somar(lambda a: a.icms.valor)
	ipi = somar(lambda a: a.ipi.valor)
	pis = somar(lambda a: a.pis_cofins.pis)
	cofins = somar(lambda a: a.pis_cofins.cofins)
	produtos_total = somar(lambda a: a.item.valor_liquido)

	frete = somar_produto("vFrete")
	seguro = somar_produto("vSeg")
	desconto = somar_produto("vDesc")
	outras = somar_produto("vOutro")

	# O ICMS é por dentro e já está no preço; PIS e COFINS também. Só o que é por fora
	# se acrescenta ao total da nota.
	total_nota = produtos_total + frete + seguro + outras - desconto + ipi

	campos = {
		"vBC": base_icms,
		"vICMS": icms,
		"vICMSDeson": ZERO,
		"vFCP": ZERO,
		"vBCST": ZERO,
		"vST": ZERO,
		"vFCPST": ZERO,
		"vFCPSTRet": ZERO,
		"vProd": produtos_total,
		"vFrete": frete,
		"vSeg": seguro,
		"vDesc": desconto,
		"vII": ZERO,
		"vIPI": ipi,
		"vIPIDevol": ZERO,
		"vPIS": pis,
		"vCOFINS": cofins,
		"vOutro": outras,
		"vNF": total_nota,
	}

	return {"ICMSTot": {nome: _valor(quantia) for nome, quantia in campos.items()}}
