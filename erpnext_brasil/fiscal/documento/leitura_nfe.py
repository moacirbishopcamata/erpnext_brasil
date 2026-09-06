# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Lê o XML de uma NF-e recebida e devolve o que ela diz.

Por que existe
--------------------
Toda entrada de mercadoria no Brasil vem acompanhada do XML da NF-e do fornecedor. Sem
leitura, a alternativa é digitar — e digitar uma chave de 44 dígitos, o NCM e o CFOP de
cada item é onde nasce erro de escrituração, que só aparece meses depois, na EFD.

O app sabia **montar** NF-e desde sempre (`fiscal/documento/nfe.py`) e não sabia **ler** uma.
Interpretar retorno da SEFAZ já havia (`resposta_sefaz.py`, `evento.py`), mas retorno é
outra coisa: são dezenas de elementos, não uma nota inteira com itens.

⚠️ Corrigindo o que `docs/tropicalizacao-por-area.md` dizia
------------------------------------------------------------------
A primeira versão daquele documento afirmava que "o caminho já existe para o CT-e
(`integracao/cte_extracao.py`)". **Não existe**: aquele módulo percorre `Shipment` →
`Delivery Note` → `br_chave_acesso`, ou seja, lê **DocTypes do site**, não XML. Não havia
precedente de parser de documento fiscal recebido; este é o primeiro.

Os nomes dos elementos não foram escritos de memória
-----------------------------------------------------------
Todos os 43 usados aqui foram conferidos contra `elementos_nfe.json`, o inventário de
elementos do leiaute que o projeto já mantinha. Escrever `qCom` como `qtdCom` produziria
uma leitura que devolve zero em silêncio — e zero é um número plausível.

Quantidade comercial × tributável
----------------------------------------
`qCom`/`uCom`/`vUnCom` (comercial) e `qTrib`/`uTrib`/`vUnTrib` (tributável) **podem
diferir**, e diferem sempre que a unidade de venda não é a de tributação — caixa com 12
unidades, saca de 60 kg. Este módulo lê **as duas**, porque escolher uma seria decidir por
quem chama: a entrada de estoque quer a comercial, a escrituração fiscal quer a tributável.

Um leitor que devolvesse só `qCom` faria o estoque bater e o SPED não — e ninguém
perceberia até a validação do PVA.

O que este módulo **não** faz
-----------------------------------
- **Não valida a assinatura.** Ler não é confiar: conferir assinatura exige a cadeia de
  certificados da ICP-Brasil e é operação à parte.
- **Não decide se a nota vale.** Presença de `protNFe` diz que houve autorização no XML
  recebido; se ela foi cancelada depois, só a consulta à SEFAZ responde
  (`transporte_sefaz.consultar`).
- **Não lê impostos por item.** ICMS, IPI, PIS e Cofins de cada item vivem em grupos com
  nome variável por CST (`ICMS00`, `ICMS20`, `ICMSSN101`…), e tratá-los exige o mapa de
  tributação inteiro — frente própria, não um parâmetro a mais aqui. Os totais são lidos.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from erpnext_brasil.fiscal.documento.chave_acesso import validar_chave

__all__ = [
	"ItemLido",
	"NfeIlegivel",
	"NotaLida",
	"ParteLida",
	"TotaisLidos",
	"ler_nfe",
]

ZERO = Decimal("0")


class NfeIlegivel(ValueError):
	"""O XML não é uma NF-e que se possa aproveitar."""


@dataclass(frozen=True)
class ParteLida:
	"""Emitente ou destinatário, como o XML os declara."""

	nome: str = ""
	cnpj: str = ""
	cpf: str = ""
	inscricao_estadual: str = ""
	uf: str = ""

	@property
	def documento(self) -> str:
		"""CNPJ ou CPF — o que houver. Pessoa física não tem CNPJ, e o grupo é uma escolha
		entre os dois no próprio leiaute."""
		return self.cnpj or self.cpf


@dataclass(frozen=True)
class ItemLido:
	"""Uma linha da nota.

	`quantidade`/`unidade`/`valor_unitario` são os **comerciais**; os tributáveis vêm nos
	campos com sufixo `_tributavel`. Ver a nota no topo do módulo sobre por que os dois.
	"""

	numero: int
	codigo: str = ""
	descricao: str = ""
	ncm: str = ""
	cfop: str = ""
	cest: str = ""
	ean: str = ""
	unidade: str = ""
	quantidade: Decimal = ZERO
	valor_unitario: Decimal = ZERO
	valor_total: Decimal = ZERO
	unidade_tributavel: str = ""
	quantidade_tributavel: Decimal = ZERO
	valor_unitario_tributavel: Decimal = ZERO


@dataclass(frozen=True)
class TotaisLidos:
	"""O grupo `ICMSTot`, que é onde a nota declara os seus totais."""

	valor_produtos: Decimal = ZERO
	valor_nota: Decimal = ZERO
	valor_icms: Decimal = ZERO
	valor_ipi: Decimal = ZERO
	valor_frete: Decimal = ZERO
	valor_seguro: Decimal = ZERO
	valor_desconto: Decimal = ZERO
	valor_outras_despesas: Decimal = ZERO


@dataclass(frozen=True)
class NotaLida:
	"""Uma NF-e recebida, reduzida ao que serve para dar entrada e escriturar."""

	chave_acesso: str
	numero: str = ""
	serie: str = ""
	modelo: str = ""
	data_emissao: str = ""
	natureza_operacao: str = ""
	emitente: ParteLida = field(default_factory=ParteLida)
	destinatario: ParteLida = field(default_factory=ParteLida)
	itens: tuple[ItemLido, ...] = ()
	totais: TotaisLidos = field(default_factory=TotaisLidos)
	protocolo: str = ""

	@property
	def tem_protocolo(self) -> bool:
		"""Havia protocolo de autorização **no XML recebido**.

		Não é o mesmo que "a nota vale hoje": um cancelamento posterior não aparece aqui.
		Quem precisa da situação atual consulta a SEFAZ.
		"""
		return bool(self.protocolo)


def _decimal(texto: str | None) -> Decimal:
	"""Converte para `Decimal` direto da string — nunca passando por `float`.

	`Decimal(float("0.1"))` traz o erro de representação binária junto, e três dessas somas
	já deslocam um centavo. Em nota fiscal, um centavo de diferença é divergência de
	escrituração.
	"""
	if not texto:
		return ZERO

	try:
		return Decimal(texto.strip())
	except (InvalidOperation, ValueError) as e:
		raise NfeIlegivel(f"valor numérico ilegível no XML: {texto!r}") from e


def _filho(no, nome: str):
	# `local-name()` via `.xpath()`, não `.find()`: o namespace da NF-e é declarado sem
	# prefixo, e `.find()` só entende o subconjunto de caminho do ElementTree, sem
	# predicado de função. Mesma disciplina de `resposta_sefaz.py`.
	encontrados = no.xpath(f"*[local-name()='{nome}']")

	return encontrados[0] if encontrados else None


def _texto(no, nome: str) -> str:
	if no is None:
		return ""

	elemento = _filho(no, nome)

	return elemento.text.strip() if elemento is not None and elemento.text else ""


def _parte(grupo, prefixo_endereco: str) -> ParteLida:
	if grupo is None:
		return ParteLida()

	return ParteLida(
		nome=_texto(grupo, "xNome"),
		cnpj=_texto(grupo, "CNPJ"),
		cpf=_texto(grupo, "CPF"),
		inscricao_estadual=_texto(grupo, "IE"),
		uf=_texto(_filho(grupo, prefixo_endereco), "UF"),
	)


def _item(det) -> ItemLido:
	prod = _filho(det, "prod")

	# `nItem` é **atributo** de `det`, não elemento filho — procurá-lo como filho
	# devolveria vazio e numeraria todos os itens como 0.
	numero = det.get("nItem") or "0"

	return ItemLido(
		numero=int(numero) if numero.isdigit() else 0,
		codigo=_texto(prod, "cProd"),
		descricao=_texto(prod, "xProd"),
		ncm=_texto(prod, "NCM"),
		cfop=_texto(prod, "CFOP"),
		cest=_texto(prod, "CEST"),
		ean=_texto(prod, "cEAN"),
		unidade=_texto(prod, "uCom"),
		quantidade=_decimal(_texto(prod, "qCom")),
		valor_unitario=_decimal(_texto(prod, "vUnCom")),
		valor_total=_decimal(_texto(prod, "vProd")),
		unidade_tributavel=_texto(prod, "uTrib"),
		quantidade_tributavel=_decimal(_texto(prod, "qTrib")),
		valor_unitario_tributavel=_decimal(_texto(prod, "vUnTrib")),
	)


def _totais(inf_nfe) -> TotaisLidos:
	icms_tot = _filho(_filho(inf_nfe, "total"), "ICMSTot")

	if icms_tot is None:
		return TotaisLidos()

	return TotaisLidos(
		valor_produtos=_decimal(_texto(icms_tot, "vProd")),
		valor_nota=_decimal(_texto(icms_tot, "vNF")),
		valor_icms=_decimal(_texto(icms_tot, "vICMS")),
		valor_ipi=_decimal(_texto(icms_tot, "vIPI")),
		valor_frete=_decimal(_texto(icms_tot, "vFrete")),
		valor_seguro=_decimal(_texto(icms_tot, "vSeg")),
		valor_desconto=_decimal(_texto(icms_tot, "vDesc")),
		valor_outras_despesas=_decimal(_texto(icms_tot, "vOutro")),
	)


def ler_nfe(xml: str | bytes) -> NotaLida:
	"""Lê um `nfeProc` (nota mais protocolo) ou uma `NFe` solta.

	Aceita os dois porque os dois circulam: o fornecedor manda o `nfeProc`, mas sistemas
	intermediários às vezes repassam só a `NFe`. Recusar a segunda forçaria o usuário a
	editar XML à mão.

	A chave é lida do `@Id` do `infNFe` e **conferida** por `validar_chave` — inclusive o
	dígito verificador. Um XML truncado ou adulterado no meio do caminho falha aqui, e não
	depois, quando a chave errada já tiver sido gravada num `Purchase Invoice`.
	"""
	from lxml import etree

	bruto = xml.encode("utf-8") if isinstance(xml, str) else xml

	try:
		raiz = etree.fromstring(bruto)
	except etree.XMLSyntaxError as e:
		raise NfeIlegivel(f"XML inválido: {e}") from e

	encontrados = raiz.xpath(".//*[local-name()='infNFe']")

	if not encontrados:
		raise NfeIlegivel("XML sem grupo infNFe — não é uma NF-e reconhecível")

	inf_nfe = encontrados[0]

	identificador = inf_nfe.get("Id") or ""
	chave = validar_chave(identificador.removeprefix("NFe"))

	ide = _filho(inf_nfe, "ide")

	protocolos = raiz.xpath(".//*[local-name()='infProt']")
	protocolo = _texto(protocolos[0], "nProt") if protocolos else ""

	return NotaLida(
		chave_acesso=chave,
		numero=_texto(ide, "nNF"),
		serie=_texto(ide, "serie"),
		modelo=_texto(ide, "mod"),
		data_emissao=_texto(ide, "dhEmi"),
		natureza_operacao=_texto(ide, "natOp"),
		emitente=_parte(_filho(inf_nfe, "emit"), "enderEmit"),
		destinatario=_parte(_filho(inf_nfe, "dest"), "enderDest"),
		itens=tuple(_item(det) for det in inf_nfe.xpath("*[local-name()='det']")),
		totais=_totais(inf_nfe),
		protocolo=protocolo,
	)
