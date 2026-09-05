# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Bloco K do EFD-ICMS/IPI — controle da produção e do estoque.

O núcleo do bloco: `K001` (abertura), `K010` (tipo de leiaute), `K100` (período),
`K200` (estoque escriturado), `K220` (movimentação interna), `K230`/`K235` (produção e
insumos consumidos) e `K990` (encerramento).

Achado 1: "quantidade" tem precisão diferente **dentro do mesmo bloco**
--------------------------------------------------------------------------------
| Registro | Campo | Decimais |
|---|---|---|
| `K200` | `QTD` | **3** |
| `K220` | `QTD_ORI`, `QTD_DEST` | **6** |
| `K230` | `QTD_ENC` | **6** |
| `K235` | `QTD` | **6** |

O mesmo conceito — quantidade de mercadoria, na mesma unidade de controle de estoque do
`0200` — declarado com precisão diferente em registros irmãos, no mesmo bloco. Um saldo
de estoque em `K200` tem três casas; o consumo que o produziu, em `K235`, tem seis.

Isso importa porque o guia manda o `K200` ser **derivado** dos apontamentos:

    Estoque final = estoque inicial + entradas/produção/movimentação interna
                                    − saídas/consumo/movimentação interna

Somar valores de seis casas e gravar em três é arredondamento, não truncamento — e fazê-lo
sem perceber produz um saldo que não fecha com a movimentação por diferenças de centésimo
de milésimo. `arredondar_quantidade` existe para tornar a conversão explícita e única.

Achado 2: cada registro aceita um conjunto **diferente** de tipos de item
----------------------------------------------------------------------------------
Nenhum deles aceita "qualquer item do `0200`":

| Registro | Tipos aceitos (`TIPO_ITEM` do `0200`) |
|---|---|
| `K200` | 00, 01, 02, 03, 04, 05, **06**, 10 |
| `K220` | 00, 01, 02, 03, 04, 05, 10 |
| `K230` | **só 03 e 04** (produto em processo e acabado) |
| `K235` | 00, 01, 02, 03, 04, 05, 10 |

O **produto intermediário (tipo 06)** é a exceção que explica o resto: ele **tem saldo**
em estoque (`K200`) mas seu consumo **não é escriturado** em `K235`. O guia diz por quê —
o Fisco deduz a quantidade consumida por diferença:

> "Quantidade consumida = estoque inicial (K200) + entrada (C170) − saída (C100/NF-e −
> Devolução) − estoque final (K200)."

Escriturar o consumo do tipo 06 em `K235` não é "informação a mais": é informação que o
leiaute não prevê, e o PVA rejeita.

Achado 3: `COD_INS_SUBST` existe no leiaute e **não deve ser preenchido**
----------------------------------------------------------------------------------
O campo 05 do `K235` traz, na própria descrição oficial, "**A partir de 01/01/2022 não
preencher**". É um campo que continua no leiaute (a posição não pode sumir sem quebrar
todo arquivo já gerado) mas cuja regra de negócio acabou.

Implementá-lo como parâmetro normal seria oferecer ao usuário uma forma de gerar arquivo
recusado. Aqui ele sai **sempre vazio**, e a razão fica registrada — porque a próxima
pessoa que ler o leiaute vai achar que faltou implementar.

O `K010` decide o que é obrigatório abaixo
--------------------------------------------------
Desde 2023 o contribuinte escolhe o leiaute, e a escolha muda quais registros são
exigidos. `K235` (insumos consumidos) é **obrigatório no completo e dispensado no
simplificado** — a diferença mais cara da tabela, porque é o registro de maior volume.

Este módulo expõe a escolha em `TIPOS_DE_LEIAUTE` e a consequência em
`REGISTROS_DISPENSADOS_NO_SIMPLIFICADO`, mas **não decide** por quem chama: a opção é do
contribuinte, condicionada ao Ajuste SINIEF 02/09, e depende de fatos que este módulo não
conhece.

Onde a perda de estoque aparece — e onde não aparece
-------------------------------------------------------------
O Bloco K **não tem registro de perda**. Uma quebra, um vencimento ou um furto não viram
lançamento próprio: reduzem o saldo declarado no `K200`, e o estorno de crédito que a
perda dispara (ver `contabil/perdas.py`) é um ajuste de apuração no `E111`, cujo código
vem da tabela da UF — que este projeto documenta como não modelada.

A reclassificação de produto não conforme é caso diferente e **tem** registro: vai para o
`K220` (troca de código) ou para o `K260` (reprocessamento com o mesmo código). Confundir
perda com reclassificação é o erro natural aqui, e são coisas distintas: uma some do
estoque, a outra muda de código dentro dele.

Fora de escopo, declarado
--------------------------------
- **`K210`/`K215` (desmontagem), `K250`/`K255` (industrialização por terceiros),
  `K260`/`K265` (reprocessamento), `K270`/`K275`/`K280` (correção de apontamento) e
  `K290`-`K302` (produção conjunta).** São o restante do bloco; nenhum é dispensado por
  ser difícil — cada um pede seu próprio incremento verificado, e vários são dispensados
  no leiaute simplificado.
- **A obrigatoriedade do bloco por CNAE/UF e por porte.** É regra de *quem entrega*, não
  de *como montar*.
- **A vinculação `K230` ↔ `K235` por ordem de produção.** O encadeamento existe no
  leiaute (nível 3 e 4), mas amarrar consumo a produção depende do modelo de `Work Order`
  do ERPNext, e é trabalho da camada de integração.

Fonte: Guia Prático EFD-ICMS/IPI versão 3.2.1 (28/10/2025), páginas 264-273, baixado de
`sped.rfb.gov.br` e lido localmente.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido

__all__ = [
	"DECIMAIS_MOVIMENTACAO",
	"DECIMAIS_SALDO",
	"REGISTROS_DISPENSADOS_NO_SIMPLIFICADO",
	"TIPOS_DE_LEIAUTE",
	"TIPOS_EM_K200",
	"TIPOS_EM_K220",
	"TIPOS_EM_K230",
	"TIPOS_EM_K235",
	"EstoqueEscriturado",
	"InsumoConsumido",
	"ItemProduzido",
	"MovimentacaoInterna",
	"arredondar_quantidade",
	"montar_bloco_k",
	"montar_k001",
	"montar_k010",
	"montar_k100",
	"montar_k200",
	"montar_k220",
	"montar_k230",
	"montar_k235",
	"montar_k990",
	"validar_tipo_do_item",
]

ZERO = Decimal("0")

DECIMAIS_SALDO = 3
"""Casas decimais do `QTD` do `K200` — ver achado 1 na docstring do módulo."""

DECIMAIS_MOVIMENTACAO = 6
"""Casas decimais dos `QTD*` do `K220`, `K230` e `K235` — o dobro do saldo."""

LEIAUTE_SIMPLIFICADO = "0"
LEIAUTE_COMPLETO = "1"
LEIAUTE_SO_SALDOS = "2"

TIPOS_DE_LEIAUTE = {
	LEIAUTE_SIMPLIFICADO: "Leiaute simplificado",
	LEIAUTE_COMPLETO: "Leiaute completo",
	LEIAUTE_SO_SALDOS: "Leiaute restrito aos saldos de estoque",
}

REGISTROS_DISPENSADOS_NO_SIMPLIFICADO = frozenset(
	{"K210", "K215", "K235", "K255", "K260", "K265", "K275", "K292", "K302"}
)
"""O que o leiaute simplificado desobriga. `K235` é o de maior volume — ver docstring."""

ESTOQUE_PROPRIO = "0"
ESTOQUE_PROPRIO_COM_TERCEIRO = "1"
ESTOQUE_DE_TERCEIRO = "2"

IND_EST_VALIDOS = frozenset({ESTOQUE_PROPRIO, ESTOQUE_PROPRIO_COM_TERCEIRO, ESTOQUE_DE_TERCEIRO})

_EXIGEM_PARTICIPANTE = frozenset({ESTOQUE_PROPRIO_COM_TERCEIRO, ESTOQUE_DE_TERCEIRO})

TIPO_PRODUTO_INTERMEDIARIO = "06"
"""Tem saldo no `K200` e consumo **não escriturado** no `K235` — ver achado 2."""

TIPOS_EM_K200 = frozenset({"00", "01", "02", "03", "04", "05", TIPO_PRODUTO_INTERMEDIARIO, "10"})
TIPOS_EM_K220 = frozenset({"00", "01", "02", "03", "04", "05", "10"})
TIPOS_EM_K230 = frozenset({"03", "04"})
TIPOS_EM_K235 = frozenset({"00", "01", "02", "03", "04", "05", "10"})


def arredondar_quantidade(quantidade: Decimal, casas: int) -> Decimal:
	"""Arredonda uma quantidade para as casas que o registro de destino declara.

	Existe porque a conversão entre as seis casas da movimentação e as três do saldo é
	**arredondamento, não truncamento**, e fazê-la implicitamente em cada chamada é como
	um saldo passa a não fechar com a movimentação que o produziu.
	"""
	if not isinstance(quantidade, Decimal):
		raise EfdInvalido(f"quantidade deve ser Decimal, recebido {type(quantidade).__name__}")

	return quantidade.quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)


def _validar_quantidade(nome: str, valor: Decimal, *, positiva: bool = True) -> None:
	if not isinstance(valor, Decimal):
		raise EfdInvalido(f"{nome} deve ser Decimal, recebido {type(valor).__name__}")

	if valor < ZERO:
		raise EfdInvalido(f"{nome} não admite quantidade negativa, recebido {valor}")

	if positiva and valor == ZERO:
		raise EfdInvalido(f"{nome} deve ser maior que zero, recebido {valor}")


def _validar_codigo(nome: str, valor: str) -> None:
	if not valor:
		raise EfdInvalido(f"{nome} não pode ser vazio — é ele que liga o registro ao 0200")


def validar_tipo_do_item(tipo: str, tipos_aceitos: frozenset[str], registro: str) -> None:
	"""Confere o `TIPO_ITEM` do `0200` contra o que **aquele** registro aceita.

	Recebe o conjunto em vez de decidir pelo nome do registro porque o ponto é justamente
	que os conjuntos são diferentes: um `if registro == ...` esconderia a diferença que
	esta função existe para tornar visível.
	"""
	if tipo not in tipos_aceitos:
		raise EfdInvalido(
			f"{registro} não aceita item do tipo {tipo!r}; tipos válidos: {sorted(tipos_aceitos)}"
			+ (
				f" — o tipo {TIPO_PRODUTO_INTERMEDIARIO!r} (produto intermediário) tem saldo no "
				"K200 mas seu consumo não é escriturado, o Fisco o deduz por diferença"
				if tipo == TIPO_PRODUTO_INTERMEDIARIO
				else ""
			)
		)


@dataclass(frozen=True)
class EstoqueEscriturado:
	"""Uma linha do `K200` — o saldo de um item na data final do período.

	`quantidade` tem **três** casas decimais, ao contrário de tudo o mais neste bloco.
	"""

	data_estoque: date
	codigo_item: str
	quantidade: Decimal
	indicador_estoque: str = ESTOQUE_PROPRIO
	codigo_participante: str = ""

	def __post_init__(self) -> None:
		_validar_codigo("COD_ITEM", self.codigo_item)

		# Saldo zero é legítimo: o guia diz que informá-lo é desnecessário, não proibido.
		_validar_quantidade("QTD", self.quantidade, positiva=False)

		if self.indicador_estoque not in IND_EST_VALIDOS:
			raise EfdInvalido(
				f"IND_EST deve ser um de {sorted(IND_EST_VALIDOS)}, recebido {self.indicador_estoque!r}"
			)

		if self.indicador_estoque in _EXIGEM_PARTICIPANTE and not self.codigo_participante:
			raise EfdInvalido(
				f"IND_EST {self.indicador_estoque!r} (estoque em poder ou de propriedade de "
				"terceiro) exige COD_PART"
			)


@dataclass(frozen=True)
class MovimentacaoInterna:
	"""Uma linha do `K220` — a troca de um item por outro dentro do próprio estoque.

	As duas quantidades são independentes: reclassificar 100 kg de um código em 98 kg de
	outro é movimentação legítima (o guia dá a reclassificação por controle de qualidade
	como exemplo). Por isso não há checagem de igualdade entre elas.
	"""

	data_movimentacao: date
	codigo_item_origem: str
	codigo_item_destino: str
	quantidade_origem: Decimal
	quantidade_destino: Decimal

	def __post_init__(self) -> None:
		_validar_codigo("COD_ITEM_ORI", self.codigo_item_origem)
		_validar_codigo("COD_ITEM_DEST", self.codigo_item_destino)

		if self.codigo_item_origem == self.codigo_item_destino:
			raise EfdInvalido(
				"COD_ITEM_DEST deve ser diferente de COD_ITEM_ORI — movimentar um item para ele "
				"mesmo não é movimentação; se o código não muda, o registro é o K260 "
				"(reprocessamento), não o K220"
			)

		_validar_quantidade("QTD_ORI", self.quantidade_origem)
		_validar_quantidade("QTD_DEST", self.quantidade_destino)


@dataclass(frozen=True)
class ItemProduzido:
	"""Uma linha do `K230` — a produção acabada, com ou sem ordem de produção.

	Sem ordem de produção, os três campos de OP ficam vazios e `quantidade` **tem** de ser
	maior que zero. Com ordem ainda não concluída, `data_fim` fica vazia e a quantidade
	pode ser zero: é o apontamento de produção em elaboração, que existe para pendurar o
	consumo de insumos do `K235`.
	"""

	codigo_item: str
	quantidade: Decimal
	data_inicio_op: date | None = None
	data_fim_op: date | None = None
	codigo_ordem_producao: str = ""

	def __post_init__(self) -> None:
		_validar_codigo("COD_ITEM", self.codigo_item)
		_validar_quantidade("QTD_ENC", self.quantidade, positiva=False)

		tem_op = bool(self.codigo_ordem_producao)

		if (tem_op or self.data_fim_op) and not self.data_inicio_op:
			raise EfdInvalido(
				"DT_INI_OP é obrigatório quando há COD_DOC_OP ou DT_FIN_OP — uma ordem de "
				"produção sem data de início não pode ser posicionada em nenhum período"
			)

		if self.data_inicio_op and not tem_op:
			raise EfdInvalido("COD_DOC_OP é obrigatório quando informado DT_INI_OP")

		if self.data_fim_op and self.data_inicio_op and self.data_fim_op < self.data_inicio_op:
			raise EfdInvalido(
				f"DT_FIN_OP ({self.data_fim_op}) é anterior a DT_INI_OP ({self.data_inicio_op}): "
				"a ordem de produção não pode terminar antes de começar"
			)

		if not tem_op and self.quantidade == ZERO:
			raise EfdInvalido(
				"QTD_ENC deve ser maior que zero sem ordem de produção — produção zero só é "
				"válida em OP não concluída, que é o que sustenta o consumo apontado no K235"
			)


@dataclass(frozen=True)
class InsumoConsumido:
	"""Uma linha do `K235` — o insumo que saiu do estoque para o produto do `K230`.

	Não tem `codigo_insumo_substituido`: o campo existe no leiaute e o guia manda **não
	preencher** desde 01/01/2022 (ver achado 3). Sai sempre vazio.
	"""

	data_saida: date
	codigo_item: str
	quantidade: Decimal

	def __post_init__(self) -> None:
		_validar_codigo("COD_ITEM", self.codigo_item)
		_validar_quantidade("QTD", self.quantidade, positiva=False)


def montar_k001(tem_dados: bool) -> dict:
	"""Abertura do Bloco K. `IND_MOV` aceita `[0,1]` — este bloco **pode** ser vazio, ao
	contrário do `E001` (ver `efd_icms_ipi.montar_e001`)."""
	return {"REG": "K001", "IND_MOV": "0" if tem_dados else "1"}


def montar_k010(tipo_de_leiaute: str) -> dict:
	"""Tipo de leiaute adotado — registro `K010`, obrigatório desde 2023 sempre que o
	`K001` indicar bloco com dados.

	A escolha é do contribuinte e muda quais registros são obrigatórios abaixo; este
	módulo a registra, não a decide.
	"""
	if tipo_de_leiaute not in TIPOS_DE_LEIAUTE:
		raise EfdInvalido(
			f"IND_TP_LEIAUTE deve ser um de {sorted(TIPOS_DE_LEIAUTE)}, recebido {tipo_de_leiaute!r}"
		)

	return {"REG": "K010", "IND_TP_LEIAUTE": tipo_de_leiaute}


def montar_k100(data_inicial: date, data_final: date) -> dict:
	"""Período de apuração do ICMS/IPI — registro `K100`, 3 campos.

	"Prevalecendo os períodos mais curtos": quem apura ICMS e IPI em periodicidades
	diferentes usa a menor, e declara um `K100` por período.
	"""
	for nome, valor in (("DT_INI", data_inicial), ("DT_FIN", data_final)):
		if not isinstance(valor, date):
			raise EfdInvalido(f"{nome} deve ser date, recebido {type(valor).__name__}")

	if data_inicial > data_final:
		raise EfdInvalido(
			f"DT_INI ({data_inicial}) é posterior a DT_FIN ({data_final}): "
			"o período de apuração não pode terminar antes de começar"
		)

	return {"REG": "K100", "DT_INI": data_inicial, "DT_FIN": data_final}


def montar_k200(estoque: EstoqueEscriturado) -> dict:
	"""Campos do registro `K200`, na ordem oficial — 6 campos.

	A quantidade é arredondada para as **três** casas do saldo, e é aqui que a diferença
	de precisão do bloco fica contida em um lugar só.
	"""
	return {
		"REG": "K200",
		"DT_EST": estoque.data_estoque,
		"COD_ITEM": estoque.codigo_item,
		"QTD": arredondar_quantidade(estoque.quantidade, DECIMAIS_SALDO),
		"IND_EST": estoque.indicador_estoque,
		"COD_PART": estoque.codigo_participante,
	}


def montar_k220(movimentacao: MovimentacaoInterna) -> dict:
	"""Campos do registro `K220`, na ordem oficial — 6 campos."""
	return {
		"REG": "K220",
		"DT_MOV": movimentacao.data_movimentacao,
		"COD_ITEM_ORI": movimentacao.codigo_item_origem,
		"COD_ITEM_DEST": movimentacao.codigo_item_destino,
		"QTD_ORI": arredondar_quantidade(movimentacao.quantidade_origem, DECIMAIS_MOVIMENTACAO),
		"QTD_DEST": arredondar_quantidade(movimentacao.quantidade_destino, DECIMAIS_MOVIMENTACAO),
	}


def montar_k230(item: ItemProduzido) -> dict:
	"""Campos do registro `K230`, na ordem oficial — 6 campos.

	`DT_FIN_OP` em branco é informação, não omissão: significa ordem de produção ainda em
	elaboração no encerramento do período.
	"""
	return {
		"REG": "K230",
		"DT_INI_OP": item.data_inicio_op,
		"DT_FIN_OP": item.data_fim_op,
		"COD_DOC_OP": item.codigo_ordem_producao,
		"COD_ITEM": item.codigo_item,
		"QTD_ENC": arredondar_quantidade(item.quantidade, DECIMAIS_MOVIMENTACAO),
	}


def montar_k235(insumo: InsumoConsumido) -> dict:
	"""Campos do registro `K235`, na ordem oficial — 5 campos.

	`COD_INS_SUBST` sai sempre vazio: o guia manda não preenchê-lo desde 01/01/2022, e a
	posição permanece no leiaute (ver achado 3 na docstring do módulo).
	"""
	return {
		"REG": "K235",
		"DT_SAIDA": insumo.data_saida,
		"COD_ITEM": insumo.codigo_item,
		"QTD": arredondar_quantidade(insumo.quantidade, DECIMAIS_MOVIMENTACAO),
		"COD_INS_SUBST": "",
	}


def montar_k990(quantidade_linhas: int) -> dict:
	"""Encerramento do Bloco K, contando também a abertura e ele próprio."""
	if quantidade_linhas < 2:
		raise EfdInvalido(
			f"o Bloco K tem no mínimo duas linhas (K001 e o próprio K990), recebido {quantidade_linhas}"
		)

	return {"REG": "K990", "QTD_LIN_K": str(quantidade_linhas)}


def montar_bloco_k(
	data_inicial: date,
	data_final: date,
	estoques: list[EstoqueEscriturado],
	tipo_de_leiaute: str = LEIAUTE_COMPLETO,
) -> list[dict]:
	"""O bloco K com o recorte de saldos: `K001`/`K010`/`K100`/`K200`.../`K990`.

	Cobre o caso do contribuinte que declara estoque escriturado sem apontar produção —
	inclusive o leiaute "2 - restrito aos saldos de estoque", para o qual este é o bloco
	inteiro. Produção (`K230`/`K235`) e movimentação (`K220`) são montadas registro a
	registro por quem conhece o encadeamento com a ordem de produção.

	`DT_EST` de cada `K200` é conferido contra `DT_FIN` do `K100`, como o guia exige: um
	saldo com data diferente da do período não é saldo daquele período.
	"""
	if not estoques:
		return [montar_k001(tem_dados=False), montar_k990(2)]

	fora_do_periodo = [e.codigo_item for e in estoques if e.data_estoque != data_final]

	if fora_do_periodo:
		raise EfdInvalido(
			f"DT_EST deve ser igual a DT_FIN do K100 ({data_final}); itens fora do período: {fora_do_periodo}"
		)

	linhas = [
		montar_k001(tem_dados=True),
		montar_k010(tipo_de_leiaute),
		montar_k100(data_inicial, data_final),
		*(montar_k200(estoque) for estoque in estoques),
	]

	return [*linhas, montar_k990(len(linhas) + 1)]
