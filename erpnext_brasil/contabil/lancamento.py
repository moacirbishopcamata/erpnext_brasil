# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Lançamentos automáticos de uma venda, a partir da apuração já calculada.

Fecha o segundo item do roteiro contábil ("lançamentos automáticos por operação") sobre
o primeiro (`plano_de_contas.py`): aqui a apuração de tributos (`fiscal/impostos/
apuracao.py`) vira um conjunto de partidas dobradas — cada uma referenciando uma conta
de `plano_de_contas.ARVORE`, nunca um nome inventado.

Por que o IPI não vira "Dedução da Receita" como ICMS/PIS/COFINS
--------------------------------------------------------------------
Diferença legal real, não escolha de projeto. Duas normas distintas tratam de
"receita bruta" com objetivos diferentes:

- **Lei 6.404/1976, Art. 187, I** (contábil/societária): a DRE mostra receita bruta e
  suas **deduções** — impostos, abatimentos. Todo tributo destacado por dentro do preço
  entraria aqui.
- **Decreto-Lei 1.598/1977, Art. 12, § 4º, I** (redação da Lei 12.973/2014, tributário):
  "Na receita bruta não se incluem os tributos não cumulativos cobrados, destacadamente,
  do comprador (...) pelo vendedor (...) na condição de **mero depositário**." O IPI é o
  exemplo clássico deste dispositivo (junto do ICMS-ST) — o vendedor industrial só
  repassa o valor ao Fisco, nunca o reconhece como próprio nem por um instante.

Consequência prática: IPI nunca toca a conta de Receita nem como dedução — vai direto
`Clientes → IPI a Recolher`, por fora da receita desde o lançamento inicial. ICMS, PIS,
COFINS e ISS **entram** na receita bruta e saem por dedução, porque a exclusão do
DL 1.598 não os alcança (regime distinto do IPI/ICMS-ST).

IBS/CBS: modelagem provisória, declarada como tal
----------------------------------------------------
Este módulo trata IBS/CBS como dedução da receita (mesmo tratamento do ICMS que
substituem) — mas a contabilização de IBS/CBS **ainda é debate aberto** entre
contadores e tributaristas: há quem defenda que devem seguir o racional do IPI (nunca
tocar receita), não o do ICMS. A reforma tributária é recente demais (fase de teste
2026-2033, ver `fiscal/impostos/ibs_cbs.py`) para haver pronunciamento contábil (CPC)
consolidado. Escolhido o tratamento tipo-ICMS aqui **por ser o mais conservador e
reversível** (é mais fácil migrar uma dedução existente para "não integra receita" no
futuro do que descobrir depois que anos de receita bruta foram subestimados) — revisar
quando o CPC ou a Receita Federal se pronunciarem.

**Valor simbólico até 2027 — sem lançamento de passivo fictício.** Em 2026 (o
`ANO_TESTE` de `ibs_cbs.py`), IBS/CBS somam só 1% (0,9% CBS + 0,1% IBS) e a apuração é
**meramente informativa**: o XML exige os campos, mas não existe recolhimento algum —
"calculado" e "devido" deixaram de ser a mesma coisa (`ResultadoIBSCBS.informativo`,
ver `docs/reforma-tributaria.md`). Lançar `IBS a Recolher`/`CBS a Recolher` nesse
período registraria uma dívida com o Fisco que nunca vai ser paga — superestimando
passivo por um valor que é simbólico, não real. Por isso, enquanto `informativo=True`,
este módulo **não gera as partidas de dedução/passivo de IBS/CBS**: o valor, que já
compõe o total da nota, permanece dentro de `Receita Bruta de Vendas e Serviços` como
receita ordinária, sem reclassificação nenhuma. A partir de 2027 (CBS plena, PIS/COFINS
extintos), `informativo` vira `False` e as partidas voltam a ser geradas normalmente.

Fora de escopo desta primeira versão
----------------------------------------
- **ISS**: `fiscal/impostos/apuracao.py` não calcula ISS (é tributo de serviço,
  `apuracao.py` cobre mercadoria) — sem apuração, sem lançamento automático ainda.
- **Imposto Seletivo**: se `ItemFiscal.imposto_seletivo` for diferente de zero em
  qualquer item, `gerar_lancamentos_venda` levanta `LancamentoInvalido` em vez de gerar
  um lançamento desbalanceado silenciosamente — não há conta própria em
  `plano_de_contas.py` para isso ainda.
- **CMV/baixa de estoque**: exige custo do produto vendido, dado que `ApuracaoDocumento`
  não carrega (só preço de venda e tributos). Fica para quando o módulo de estoque
  entrar no escopo.
- **Compras** (crédito de tributo recuperável): pedem o valor total da nota de entrada,
  não só a apuração de tributo — módulo próprio quando chegar a vez.

`Lancamento` é sempre duas pontas — `LancamentoMultiplo` cobre rateio
-------------------------------------------------------------------------
`Lancamento` (venda/compra acima) modela sempre um débito e um crédito do mesmo valor —
suficiente para tudo que `gerar_lancamentos_venda`/`gerar_lancamentos_compra` produzem,
mas não para um rateio de verdade (uma despesa dividida entre três centros de custo, um
recebimento que quita duas contas a receber diferentes de uma vez). `LancamentoMultiplo`
cobre esse caso: uma lista de débitos e uma de créditos (`Partida`, cada uma com sua
conta e valor), com a única invariante que de fato importa em partida dobrada — soma dos
débitos igual à soma dos créditos — verificada na construção (`__post_init__`), não
confiada a quem monta a lista.

Não substitui `Lancamento` — os dois convivem: a maioria das operações deste app tem
duas pontas e continua usando o tipo mais simples; `LancamentoMultiplo` existe para o
caso que genuinamente precisa de mais.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.apuracao import ApuracaoDocumento

__all__ = [
	"TRIBUTOS_RECUPERAVEIS",
	"Lancamento",
	"LancamentoInvalido",
	"LancamentoMultiplo",
	"Partida",
	"gerar_lancamentos_compra",
	"gerar_lancamentos_venda",
]

ZERO = Decimal("0.00")


class LancamentoInvalido(ValueError):
	"""A apuração recebida tem um dado que este módulo ainda não sabe lançar."""


# Tributos com conta "a Recuperar" em plano_de_contas.py — só estes podem aparecer em
# `creditos_tributarios` de `gerar_lancamentos_compra`.
TRIBUTOS_RECUPERAVEIS = frozenset({"ICMS", "IPI", "PIS", "COFINS"})


@dataclass(frozen=True)
class Lancamento:
	"""Uma partida: `valor` sai de `conta_credito` e entra em `conta_debito`.

	Nomes de conta são os de `plano_de_contas.py` — este módulo não valida contra a
	árvore em tempo de execução (isso é responsabilidade de quem grava o lançamento de
	verdade, que já vai ter as contas resolvidas), mas todo nome usado aqui tem uma
	conta correspondente coberta por teste dedicado.
	"""

	conta_debito: str
	conta_credito: str
	valor: Decimal
	historico: str


@dataclass(frozen=True)
class Partida:
	"""Uma ponta de `LancamentoMultiplo` — uma conta, um valor, sem indicar débito ou
	crédito (isso é decidido por em qual das duas listas — `debitos` ou `creditos` — a
	partida está, nunca por um campo próprio que pudesse divergir da lista que a contém)."""

	conta: str
	valor: Decimal

	def __post_init__(self) -> None:
		if self.valor <= ZERO:
			raise LancamentoInvalido(f"valor da partida deve ser positivo, recebido {self.valor}")


@dataclass(frozen=True)
class LancamentoMultiplo:
	"""Um lançamento com rateio — mais de uma conta do lado do débito e/ou do crédito.

	A única invariante que partida dobrada exige de fato: soma dos débitos igual à soma
	dos créditos. Verificada aqui, na construção — não confiada a quem monta as duas
	listas (a mesma disciplina de `ApuracaoPeriodo`/`Ajuste`: a invariante vive no
	`__post_init__`, não em uma função de validação que alguém pode esquecer de chamar).
	"""

	debitos: tuple[Partida, ...]
	creditos: tuple[Partida, ...]
	historico: str

	def __post_init__(self) -> None:
		if not self.debitos or not self.creditos:
			raise LancamentoInvalido("LancamentoMultiplo precisa de ao menos uma partida de cada lado")

		total_debitos = sum((p.valor for p in self.debitos), ZERO)
		total_creditos = sum((p.valor for p in self.creditos), ZERO)

		if total_debitos != total_creditos:
			raise LancamentoInvalido(
				f"Soma dos débitos ({total_debitos}) diferente da soma dos créditos "
				f"({total_creditos}) — partida dobrada exige os dois lados iguais"
			)

	@property
	def valor_total(self) -> Decimal:
		"""O valor que circula no lançamento — mesmo total dos dois lados, por
		construção (ver `__post_init__`)."""
		return sum((p.valor for p in self.debitos), ZERO)


def _somar_pis_cofins(apuracao: ApuracaoDocumento) -> tuple[Decimal, Decimal]:
	total_pis = sum((item.pis_cofins.pis for item in apuracao.itens), ZERO)
	total_cofins = sum((item.pis_cofins.cofins for item in apuracao.itens), ZERO)

	return total_pis, total_cofins


def gerar_lancamentos_venda(apuracao: ApuracaoDocumento, *, historico: str = "Venda") -> list[Lancamento]:
	"""Gera as partidas de uma venda já apurada.

	Pós-condição verificada antes de devolver: soma dos débitos == soma dos créditos —
	nunca confiado por construção, sempre conferido (mesma disciplina de Design by
	Contract já aplicada em `qrcode_nfce.py`: postcondição é `assert`, não só comentário).
	"""
	total_is = sum((item.item.imposto_seletivo for item in apuracao.itens), ZERO)

	if total_is != ZERO:
		raise LancamentoInvalido(
			"Imposto Seletivo diferente de zero: este módulo ainda não tem conta nem "
			"regra de lançamento para ele (ver docstring, seção 'Fora de escopo')"
		)

	total_pis, total_cofins = _somar_pis_cofins(apuracao)

	# "Calculado" e "devido" não são a mesma coisa durante a fase de teste da reforma
	# (2026, ver docs/reforma-tributaria.md): `informativo=True` quer dizer que a SEFAZ
	# exige o campo no XML, mas não existe recolhimento algum — nenhum débito real com o
	# Fisco nasce disso. Lançar "IBS/CBS a Recolher" nesse período registraria um
	# passivo que nunca vai ser pago, superestimando obrigação; o valor, se compõe o
	# total da nota, fica como receita ordinária mesmo, não como tributo destacado.
	# Verificado por item (não assumido uniforme) — um documento não deveria misturar
	# item informativo com item de recolhimento real, e se misturar é melhor falhar alto
	# do que decidir sozinho qual dos dois vale para o documento inteiro.
	sinalizadores_informativo = {item.ibs_cbs.informativo for item in apuracao.itens}

	if len(sinalizadores_informativo) > 1:
		raise LancamentoInvalido(
			"Itens do documento divergem sobre IBS/CBS ser informativo (teste) ou "
			"devido (recolhimento real) — não há uma única regra de lançamento válida "
			"para o documento inteiro"
		)

	ibs_cbs_informativo = sinalizadores_informativo == {True}

	receita_reconhecida = apuracao.total_produtos + apuracao.total_ibs + apuracao.total_cbs

	lancamentos = [
		Lancamento(
			conta_debito="Clientes",
			conta_credito="Receita Bruta de Vendas e Serviços",
			valor=receita_reconhecida,
			historico=historico,
		),
	]

	if apuracao.total_ipi:
		# Não passa pela receita — DL 1.598/1977, Art. 12, § 4º, I (ver docstring).
		lancamentos.append(
			Lancamento(
				conta_debito="Clientes",
				conta_credito="IPI a Recolher",
				valor=apuracao.total_ipi,
				historico=historico,
			)
		)

	deducoes = [
		("ICMS sobre Vendas", "ICMS a Recolher", apuracao.total_icms),
		("PIS sobre Vendas", "PIS a Recolher", total_pis),
		("COFINS sobre Vendas", "COFINS a Recolher", total_cofins),
	]

	if not ibs_cbs_informativo:
		deducoes.append(("IBS sobre Vendas", "IBS a Recolher", apuracao.total_ibs))
		deducoes.append(("CBS sobre Vendas", "CBS a Recolher", apuracao.total_cbs))

	for conta_debito, conta_credito, valor in deducoes:
		if valor:
			lancamentos.append(
				Lancamento(conta_debito=conta_debito, conta_credito=conta_credito, valor=valor, historico=historico)
			)

	# Pós-condição: o que entra em Clientes (débito) é exatamente o total do documento
	# (Imposto Seletivo à parte, já barrado acima) — receita reconhecida mais o IPI que
	# passa direto por fora dela. Cada `Lancamento` já é balanceado por construção (um
	# valor, um débito, um crédito); o que precisa de verificação é que a composição do
	# conjunto não perdeu nem inventou centavo em relação à apuração de origem.
	debito_clientes = sum((l.valor for l in lancamentos if l.conta_debito == "Clientes"), ZERO)

	assert debito_clientes == apuracao.total_documento - total_is, (
		"Débito em Clientes não fecha com o total do documento — receita reconhecida "
		"mais IPI deveria esgotar o total_documento (sem Imposto Seletivo, já barrado)"
	)

	return lancamentos


def gerar_lancamentos_compra(
	valor_total_nota: Decimal, creditos_tributarios: dict[str, Decimal], *, historico: str = "Compra"
) -> list[Lancamento]:
	"""Gera as partidas de uma compra de mercadoria, dado o crédito já decidido.

	**Elegibilidade de crédito é decisão do chamador, não deste módulo.** Diferente da
	venda — onde a apuração (`ApuracaoDocumento`) já sabe exatamente quanto de cada
	tributo foi destacado —, o direito ao crédito na compra depende de regras de
	elegibilidade com corpo de lei próprio e complexo por tributo:

	- **ICMS**: crédito vale para mercadoria destinada a revenda/industrialização por
	  contribuinte (LC 87/1996, Art. 20), com uma lista extensa de vedações e estornos;
	- **IPI**: crédito vale para insumo de industrialização por estabelecimento
	  industrial/equiparado (RIPI, Decreto 7.212/2010);
	- **PIS/COFINS**: crédito só no regime não-cumulativo, e só sobre o que a lei chama
	  de "insumo" — definição que o STJ (REsp 1.221.170/PR, repetitivo) fixou como
	  "essencial ou relevante" à atividade, não uma lista fechada de itens.

	Inferir isso a partir de `Operacao`/`ItemFiscal` (que descrevem a **venda**, não a
	elegibilidade de crédito do **comprador**) seria apostar em regra tributária não
	verificada — o erro que este projeto existe para evitar. Por isso a assinatura pede
	`creditos_tributarios` já resolvido: o valor que a camada de negócio (que conhece a
	classificação fiscal do item e o regime do comprador) determinou ser recuperável.
	Este módulo só sabe a mecânica contábil de o que fazer com esse valor, não se ele é
	devido.

	`valor_total_nota` é o valor da nota de entrada como recebida (o que vai para
	`Fornecedores`), *antes* de qualquer crédito ser destacado — não a apuração de um
	item isolado, porque a nota pode ter itens sem direito a crédito nenhum.
	"""
	tributos_desconhecidos = set(creditos_tributarios) - TRIBUTOS_RECUPERAVEIS

	if tributos_desconhecidos:
		raise LancamentoInvalido(
			f"Tributo(s) sem conta 'a Recuperar' em plano_de_contas.py: {sorted(tributos_desconhecidos)} "
			f"— só {sorted(TRIBUTOS_RECUPERAVEIS)} têm"
		)

	total_creditos = sum(creditos_tributarios.values(), ZERO)

	if total_creditos > valor_total_nota:
		raise LancamentoInvalido(
			f"Soma dos créditos ({total_creditos}) maior que o valor da nota "
			f"({valor_total_nota}) — não há como recuperar mais tributo do que foi pago"
		)

	lancamentos = [
		Lancamento(
			conta_debito="Estoques", conta_credito="Fornecedores", valor=valor_total_nota, historico=historico
		),
	]

	for tributo, valor in creditos_tributarios.items():
		if valor:
			lancamentos.append(
				Lancamento(
					conta_debito=f"{tributo} a Recuperar",
					conta_credito="Estoques",
					valor=valor,
					historico=historico,
				)
			)

	# Pós-condição: o custo líquido que sobra em Estoques (débito inicial menos as
	# reclassificações de crédito) é sempre o valor da nota menos o que foi recuperado —
	# nunca "o que sobrou por acaso" da soma dos lançamentos.
	debito_estoques = sum((l.valor for l in lancamentos if l.conta_debito == "Estoques"), ZERO)
	credito_estoques = sum((l.valor for l in lancamentos if l.conta_credito == "Estoques"), ZERO)

	assert debito_estoques - credito_estoques == valor_total_nota - total_creditos, (
		"Custo líquido em Estoques não fecha com nota menos créditos recuperados"
	)

	return lancamentos
