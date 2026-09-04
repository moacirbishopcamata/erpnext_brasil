# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Bloco H do EFD-ICMS/IPI — inventário.

O bloco onde o estoque vira declaração. `H001` (abertura), `H005` (totais do
inventário), `H010` (cada item), `H020` (complemento de ICMS), `H030` (complemento de
ST) e `H990` (encerramento).

O achado que liga este bloco ao custo de aquisição: `VL_ITEM` ≠ `VL_ITEM_IR`
--------------------------------------------------------------------------------------------
O `H010` tem **dois valores para o mesmo item**, e a diferença entre eles é exatamente a
regra que `contabil/custo_aquisicao.py` implementa. O Guia Prático diz, no campo 11:

> "o valor do ICMS recuperável mediante crédito na escrita fiscal do adquirente ... não
> integra o custo de aquisição para efeito do Imposto de Renda. O montante desse imposto
> ... deve ser excluído do valor dos estoques para efeito do imposto de renda.
> Tratamento idêntico deve ser aplicado ao PIS-Pasep e à Cofins não cumulativos ...
> Observe-se, porém, que **as legislações do IPI e do ICMS não contemplam essas
> exclusões**."

Ou seja: `VL_ITEM` (campo 06, ótica ICMS/IPI) **inclui** o tributo recuperável;
`VL_ITEM_IR` (campo 11, ótica do IR) **exclui**. O mesmo item, no mesmo arquivo, no mesmo
dia, com dois valores legítimos e diferentes — e informar o mesmo número nos dois é o
erro natural de quem não sabe que a diferença existe.

`custo_de_aquisicao` já produz os dois lados: `custo` é o valor para o IR (créditos fora)
e `custo + creditos` é o valor pela ótica do ICMS/IPI. Há teste de costura provando que
os dois módulos concordam — a mesma nota vista pelas duas legislações.

Este módulo **não deduz** um do outro: quem chama informa os dois, porque a exclusão
depende de recuperabilidade, que depende de regime e destinação (ver docstring de
`custo_aquisicao.py`). O que ele faz é aceitar que sejam diferentes sem tratar isso como
erro, o que já é mais do que a maioria dos sistemas faz.

Nunca assumir por analogia: `H001` aceita `[0,1]`, `E001` aceita **só `[0]`**
-------------------------------------------------------------------------------------------
Registro de abertura de bloco parece o mesmo em todo bloco, e não é. O `H001` admite
`IND_MOV = 1` (bloco sem dados — quem não escritura inventário no período informa só
`H001` e `H990`). O `E001` tem **"Valor Válido: [0]"**: o bloco de apuração do ICMS nunca
pode ser declarado vazio, porque `E100`/`E110` são sempre obrigatórios.

Copiar a validação de um para o outro produziria um arquivo aceito pelo montador e
rejeitado pelo PVA. Por isso `montar_e001` (em `efd_icms_ipi.py`) não recebe `bool`
nenhum, enquanto `montar_h001` recebe.

As validações cruzadas que o guia impõe, e que falham alto aqui
--------------------------------------------------------------------------
- **`VL_INV` = soma dos `VL_ITEM`.** É a pós-condição do bloco: um total que não bate com
  as partes é o tipo de erro que passa despercebido até a rejeição.
- **`VL_INV = 0` proíbe `H010`.** "Atribuir valor Zero ao inventário significa escriturar
  sem estoque" — item com valor zerado é contradição, não caso de borda.
- **`IND_PROP` 1 ou 2 exige `COD_PART`.** Item em posse de terceiro sem dizer de quem é
  informação pela metade.
- **`H020` só existe com `MOT_INV` de 02 a 05**; **`H030` só com `MOT_INV = 06`**, e é
  obrigatório nesse caso. São exclusivos entre si — não é coincidência, são as duas
  situações especiais do inventário (mudança de tributação e ST).

Fora de escopo, declarado
--------------------------------
- **Quais itens entram no inventário.** Depende do que a empresa tem em estoque na data;
  é a camada de integração que lê o saldo do ERPNext, não este módulo.
- **A obrigação de fevereiro.** O guia manda repetir na EFD de fevereiro o inventário de
  31/12 apresentado em dezembro ou janeiro, e o PVA adverte se faltar. É regra de
  *quando* entregar, não de *como* montar — pertence a `prontidao_fiscal.py`, junto com
  os demais alertas de prazo, e está registrada lá.
- **Inventário mensal do CNAE 4681-8/01 e 4681-8/02** (combustíveis) — mesma categoria:
  regra de periodicidade, não de leiaute.

Fonte: Guia Prático EFD-ICMS/IPI versão 3.2.1 (28/10/2025), páginas 260-264, baixado de
`sped.rfb.gov.br` e lido localmente.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido

__all__ = [
	"IND_PROP_VALIDOS",
	"MOTIVOS_INVENTARIO",
	"MOTIVOS_QUE_EXIGEM_H020",
	"ItemInventario",
	"montar_h001",
	"montar_h005",
	"montar_h010",
	"montar_h020",
	"montar_h030",
	"montar_h990",
]

ZERO = Decimal("0.00")

MOTIVO_FINAL_DO_PERIODO = "01"
MOTIVO_MUDANCA_DE_TRIBUTACAO = "02"
MOTIVO_BAIXA_CADASTRAL = "03"
MOTIVO_ALTERACAO_DE_REGIME = "04"
MOTIVO_DETERMINACAO_DO_FISCO = "05"
MOTIVO_SUBSTITUICAO_TRIBUTARIA = "06"

MOTIVOS_INVENTARIO = {
	MOTIVO_FINAL_DO_PERIODO: "No final do período",
	MOTIVO_MUDANCA_DE_TRIBUTACAO: "Na mudança de forma de tributação da mercadoria (ICMS)",
	MOTIVO_BAIXA_CADASTRAL: "Na solicitação da baixa cadastral, paralisação temporária e outras situações",
	MOTIVO_ALTERACAO_DE_REGIME: "Na alteração de regime de pagamento — condição do contribuinte",
	MOTIVO_DETERMINACAO_DO_FISCO: "Por determinação dos fiscos",
	MOTIVO_SUBSTITUICAO_TRIBUTARIA: "Para controle das mercadorias sujeitas ao regime de substituição tributária",
}

MOTIVOS_QUE_EXIGEM_H020 = (
	MOTIVO_MUDANCA_DE_TRIBUTACAO,
	MOTIVO_BAIXA_CADASTRAL,
	MOTIVO_ALTERACAO_DE_REGIME,
	MOTIVO_DETERMINACAO_DO_FISCO,
)
"""`H020` é preenchido quando `MOT_INV` vai de "02" a "05" — nem antes, nem no "06"."""

PROPRIEDADE_DO_INFORMANTE = "0"
PROPRIEDADE_DO_INFORMANTE_COM_TERCEIRO = "1"
PROPRIEDADE_DE_TERCEIRO = "2"

IND_PROP_VALIDOS = frozenset(
	{
		PROPRIEDADE_DO_INFORMANTE,
		PROPRIEDADE_DO_INFORMANTE_COM_TERCEIRO,
		PROPRIEDADE_DE_TERCEIRO,
	}
)

_EXIGEM_PARTICIPANTE = frozenset({PROPRIEDADE_DO_INFORMANTE_COM_TERCEIRO, PROPRIEDADE_DE_TERCEIRO})


@dataclass(frozen=True)
class ItemInventario:
	"""Um item do estoque na data do inventário — o registro `H010`, 11 campos.

	`valor_item_ir` é opcional e **deliberadamente não é derivado** de `valor_item`: a
	exclusão do tributo recuperável depende de regime e destinação, que este módulo não
	conhece (ver docstring do módulo). Quando não informado, o campo sai vazio, que é o
	que o leiaute permite para quem não escritura pelo IR.
	"""

	codigo_item: str
	unidade: str
	quantidade: Decimal
	valor_unitario: Decimal
	valor_item: Decimal
	indicador_propriedade: str = PROPRIEDADE_DO_INFORMANTE
	codigo_participante: str = ""
	texto_complementar: str = ""
	codigo_conta: str = ""
	valor_item_ir: Decimal | None = None

	def __post_init__(self) -> None:
		if not self.codigo_item:
			raise EfdInvalido("COD_ITEM não pode ser vazio — é ele que liga o H010 ao registro 0200")

		if not self.unidade:
			raise EfdInvalido("UNID não pode ser vazia — deve constar no campo UNID_INV do registro 0200")

		if self.indicador_propriedade not in IND_PROP_VALIDOS:
			raise EfdInvalido(
				f"IND_PROP deve ser um de {sorted(IND_PROP_VALIDOS)}, recebido {self.indicador_propriedade!r}"
			)

		if self.indicador_propriedade in _EXIGEM_PARTICIPANTE and not self.codigo_participante:
			raise EfdInvalido(
				f"IND_PROP {self.indicador_propriedade!r} (item em posse ou propriedade de terceiro) "
				"exige COD_PART — item de terceiro sem dizer de quem é informação pela metade"
			)

		for nome, valor in (
			("QTD", self.quantidade),
			("VL_UNIT", self.valor_unitario),
			("VL_ITEM", self.valor_item),
		):
			if not isinstance(valor, Decimal):
				raise EfdInvalido(f"{nome} deve ser Decimal, recebido {type(valor).__name__}")

			if valor < ZERO:
				raise EfdInvalido(f"{nome} não pode ser negativo, recebido {valor}")

		if self.valor_item_ir is not None:
			if not isinstance(self.valor_item_ir, Decimal):
				raise EfdInvalido(
					f"VL_ITEM_IR deve ser Decimal, recebido {type(self.valor_item_ir).__name__}"
				)

			if self.valor_item_ir < ZERO:
				raise EfdInvalido(f"VL_ITEM_IR não pode ser negativo, recebido {self.valor_item_ir}")


def montar_h001(tem_dados: bool) -> dict:
	"""Abertura do Bloco H.

	Recebe `bool` porque este bloco **pode** ser vazio (`IND_MOV = 1`, quem não escritura
	inventário no período). O `E001` não pode — ver docstring do módulo sobre por que os
	dois registros de abertura não são intercambiáveis.
	"""
	return {"REG": "H001", "IND_MOV": "0" if tem_dados else "1"}


def montar_h005(data_inventario: date, valor_total: Decimal, motivo: str) -> dict:
	"""Totais do inventário — registro `H005`, 4 campos.

	`MOT_INV` (campo 04) é obrigatório: foi acrescentado ao leiaute e é o que decide se
	haverá `H020` ou `H030` abaixo deste registro.
	"""
	if not isinstance(data_inventario, date):
		raise EfdInvalido(f"DT_INV deve ser date, recebido {type(data_inventario).__name__}")

	if not isinstance(valor_total, Decimal):
		raise EfdInvalido(f"VL_INV deve ser Decimal, recebido {type(valor_total).__name__}")

	if valor_total < ZERO:
		raise EfdInvalido(f"VL_INV não pode ser negativo, recebido {valor_total}")

	if motivo not in MOTIVOS_INVENTARIO:
		raise EfdInvalido(f"MOT_INV deve ser um de {sorted(MOTIVOS_INVENTARIO)}, recebido {motivo!r}")

	return {
		"REG": "H005",
		"DT_INV": data_inventario,
		"VL_INV": valor_total,
		"MOT_INV": motivo,
	}


def montar_h010(item: ItemInventario) -> dict:
	"""Campos do registro `H010`, na ordem oficial — 11 campos."""
	return {
		"REG": "H010",
		"COD_ITEM": item.codigo_item,
		"UNID": item.unidade,
		"QTD": item.quantidade,
		"VL_UNIT": item.valor_unitario,
		"VL_ITEM": item.valor_item,
		"IND_PROP": item.indicador_propriedade,
		"COD_PART": item.codigo_participante,
		"TXT_COMPL": item.texto_complementar,
		"COD_CTA": item.codigo_conta,
		"VL_ITEM_IR": item.valor_item_ir,
	}


def montar_h020(cst_icms: str, base_calculo: Decimal, valor_icms: Decimal) -> dict:
	"""Complemento de ICMS do item — registro `H020`, 4 campos.

	Base e valor são **unitários**, não do total do item: o guia diz "informar a base de
	cálculo aplicável ao item (valor unitário)". Confundir com o total é erro silencioso,
	porque nada no formato distingue os dois.
	"""
	if len(cst_icms) != 3 or not cst_icms.isdigit():
		raise EfdInvalido(f"CST_ICMS deve ter 3 dígitos, recebido {cst_icms!r}")

	for nome, valor in (("BC_ICMS", base_calculo), ("VL_ICMS", valor_icms)):
		if not isinstance(valor, Decimal):
			raise EfdInvalido(f"{nome} deve ser Decimal, recebido {type(valor).__name__}")

	return {
		"REG": "H020",
		"CST_ICMS": cst_icms,
		"BC_ICMS": base_calculo,
		"VL_ICMS": valor_icms,
	}


def montar_h030(
	valor_icms_operacao_propria: Decimal,
	valor_bc_icms_st: Decimal,
	valor_icms_st: Decimal,
	valor_fcp: Decimal,
) -> dict:
	"""Complemento de ST do item — registro `H030`, 5 campos, todos **médios unitários**.

	`VL_ICMS_ST` já inclui a parcela de FCP vinculada, e `VL_FCP` a repete isolada: o guia
	pede "o valor médio unitário total da parcela do ICMS ST + a parcela do FCP" no campo
	04, e a parcela do FCP sozinha no 05. Não é duplicidade, é detalhamento — e somar os
	dois seria contar o FCP duas vezes.
	"""
	campos = (
		("VL_ICMS_OP", valor_icms_operacao_propria),
		("VL_BC_ICMS_ST", valor_bc_icms_st),
		("VL_ICMS_ST", valor_icms_st),
		("VL_FCP", valor_fcp),
	)

	for nome, valor in campos:
		if not isinstance(valor, Decimal):
			raise EfdInvalido(f"{nome} deve ser Decimal, recebido {type(valor).__name__}")

		if valor < ZERO:
			raise EfdInvalido(f"{nome} não pode ser negativo, recebido {valor}")

	if valor_fcp > valor_icms_st:
		raise EfdInvalido(
			f"VL_FCP ({valor_fcp}) não pode superar VL_ICMS_ST ({valor_icms_st}): o campo 04 "
			"já contém a parcela do FCP, e o 05 a destaca de dentro dele"
		)

	return {"REG": "H030", **{nome: valor for nome, valor in campos}}


def montar_h990(quantidade_linhas: int) -> dict:
	"""Encerramento do Bloco H, com a contagem de linhas do próprio bloco.

	A contagem **inclui** os registros de abertura e encerramento — o guia diz isso
	explicitamente no `E990` e a mesma convenção vale aqui. Mínimo de duas linhas: um
	bloco sem inventário ainda tem `H001` e `H990`.
	"""
	if quantidade_linhas < 2:
		raise EfdInvalido(
			f"o Bloco H tem no mínimo duas linhas (H001 e o próprio H990), recebido {quantidade_linhas}"
		)

	return {"REG": "H990", "QTD_LIN_H": str(quantidade_linhas)}


def montar_bloco_h(
	data_inventario: date,
	itens: list[ItemInventario],
	motivo: str = MOTIVO_FINAL_DO_PERIODO,
) -> list[dict]:
	"""O bloco H inteiro, com o total conferido contra as partes.

	Existe porque as validações cruzadas do guia são **entre registros**, não dentro de
	um: `VL_INV` tem de bater com a soma dos `VL_ITEM`, e `H010` não pode existir com
	inventário zerado. Montar cada registro isoladamente e confiar que o conjunto fecha é
	exatamente como um arquivo sai errado com todas as peças individualmente corretas.

	O total **é calculado**, não recebido: pedir `VL_INV` de quem chama abriria a porta
	para um total que não bate com os itens, que é o erro que esta função existe para
	tornar impossível.
	"""
	if motivo not in MOTIVOS_INVENTARIO:
		raise EfdInvalido(f"MOT_INV deve ser um de {sorted(MOTIVOS_INVENTARIO)}, recebido {motivo!r}")

	if motivo == MOTIVO_SUBSTITUICAO_TRIBUTARIA:
		raise EfdInvalido(
			f"MOT_INV {MOTIVO_SUBSTITUICAO_TRIBUTARIA!r} exige um H030 por item, que esta função "
			"não monta — use os montadores de registro diretamente"
		)

	if not itens:
		return [montar_h001(tem_dados=False), montar_h990(2)]

	total = sum((item.valor_item for item in itens), ZERO)

	if total == ZERO:
		raise EfdInvalido(
			"inventário com valor total zero não pode ter registros H010 — "
			'"atribuir valor Zero ao inventário significa escriturar sem estoque"'
		)

	linhas = [
		montar_h001(tem_dados=True),
		montar_h005(data_inventario, total, motivo),
		*(montar_h010(item) for item in itens),
	]

	return [*linhas, montar_h990(len(linhas) + 1)]
