# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Estrutura de grupos do plano de contas brasileiro, e sua amarração aos tributos.

Por que grupos, não uma codificação completa
----------------------------------------------
Diferente do setor público (PCASP, uniforme e obrigatório por lei para todos os entes),
**não existe um plano de contas único obrigatório para empresas privadas no Brasil**. A
Lei 6.404/1976 (Lei das S.A., aplicada às demais sociedades por remissão do Código Civil)
não prescreve códigos de conta — prescreve **grupos de classificação**, e cada empresa
codifica dentro deles como quiser. Modelar aqui uma "conta 1.1.1.01.001" inventada seria
apostar num nível de detalhe que a lei não fixa e que este app não tem autoridade para
decidir por conta de terceiros.

O que este módulo modela, então, são os **grupos exigidos por lei** (Art. 178 — balanço;
Art. 187 — demonstração do resultado) mais as contas de tributo que a camada fiscal deste
app já sabe calcular (`fiscal/impostos/`) — a "amarração aos tributos" citada no roteiro.
Uma empresa real substitui/estende as folhas, mas os grupos e a posição dos tributos
dentro deles não mudam, porque vêm da lei, não de escolha de projeto.

Fonte primária inacessível às ferramentas de busca no momento da implementação
--------------------------------------------------------------------------------
`planalto.gov.br` (fonte oficial da Lei 6.404/1976) não respondeu às tentativas de
acesso. O texto dos Art. 178 e 187 usado aqui foi confirmado em duas fontes secundárias
independentes que reproduzem a lei na íntegra, dizendo isso explicitamente por ser
exatamente a situação que a política deste projeto pede para não esconder.

Art. 178 — grupos do balanço
------------------------------
- **Ativo**: `Ativo Circulante` e `Ativo Não Circulante` (subdividido em `Ativo
  Realizável a Longo Prazo`, `Investimentos`, `Imobilizado`, `Intangível`);
- **Passivo**: `Passivo Circulante`, `Passivo Não Circulante` e `Patrimônio Líquido`
  (subdividido em `Capital Social`, `Reservas de Capital`, `Ajustes de Avaliação
  Patrimonial`, `Reservas de Lucros`, `Ações em Tesouraria`, `Prejuízos Acumulados`).

Art. 187 — estrutura da demonstração do resultado (DRE)
----------------------------------------------------------
Receita bruta → deduções (abatimentos, impostos) → receita líquida → custo → lucro
bruto → despesas (vendas, financeiras, gerais/administrativas, outras operacionais) →
resultado antes do IR → participações → resultado líquido. `Receita Líquida` e `Lucro
Bruto` são **subtotais calculados**, não contas para lançamento — por isso não aparecem
como folha na árvore abaixo, só os grupos que recebem lançamento direto.

Onde os tributos entram
--------------------------
Cada tributo que `fiscal/impostos/` já calcula (`ICMS`, `IPI`, `PIS`, `COFINS`, `ISS`,
`IBS`, `CBS` — ver `ibs_cbs.py`/`icms.py`/`ipi.py`/`pis_cofins.py`; `IRRF`, `CSRF`,
`INSS` — ver `retencoes.py`) ganha conta em um destes três lugares, nunca inventado:

- **`Deduções da Receita Bruta`** (Ativo não — é grupo de `Income`, ver Art. 187, I):
  ICMS/PIS/COFINS/ISS/IBS/CBS destacados na venda, que reduzem a receita bruta;
- **`Obrigações Tributárias`** (dentro de `Passivo Circulante`): a contrapartida do
  destaque acima, o que a empresa deve à Fazenda;
- **`Impostos a Recuperar`** (dentro de `Ativo Circulante`): crédito de ICMS/IPI/PIS/
  COFINS na compra, quando o regime permite recuperar (`pis_cofins.py` já distingue
  cumulativo/não-cumulativo);
- **`Impostos Retidos a Compensar`**/**`Obrigações por Retenção de Terceiros`**: IRRF/
  CSRF/INSS/ISS retidos na fonte — ativo quando o **cliente** retém da empresa, passivo
  quando a **empresa** retém de um fornecedor (`retencoes.py` calcula os dois lados).

`Simples Nacional a Recolher` é a exceção: substitui ICMS/IPI/PIS/COFINS/ISS/IRPJ/CSLL
por uma guia única (DAS) — por isso entra sozinho em `Obrigações Tributárias`, não junto
dos tributos individuais (mesma exclusão mútua que `pis_cofins.py` já documenta: "empresas
do Simples Nacional não destacam PIS/COFINS").

Funções puras: nenhuma dependência do Frappe. Ainda não plugado em nenhum doctype — ver
`docs/plano-de-contas.md` para o obstáculo de integração já identificado (o seletor de
plano de contas do ERPNext varre uma pasta fixa dentro do próprio app `erpnext`, não um
hook — outro app não consegue registrar um template ali sem sobrescrever método).
"""

from dataclasses import dataclass, field

__all__ = [
	"ROOT_TYPE_ATIVO",
	"ROOT_TYPE_DESPESA",
	"ROOT_TYPE_PASSIVO",
	"ROOT_TYPE_PATRIMONIO_LIQUIDO",
	"ROOT_TYPE_RECEITA",
	"TRIBUTOS_CONHECIDOS",
	"ARVORE",
	"Conta",
	"PlanoDeContasInvalido",
	"contas_do_tributo",
	"listar_nomes",
	"validar_arvore",
]

# `root_type` do doctype `Account` do ERPNext (`accounts_settings`/`account.json`) — os
# cinco valores fixos que o framework aceita, citados aqui só para nomear por extenso.
ROOT_TYPE_ATIVO = "Asset"
ROOT_TYPE_PASSIVO = "Liability"
ROOT_TYPE_PATRIMONIO_LIQUIDO = "Equity"
ROOT_TYPE_RECEITA = "Income"
ROOT_TYPE_DESPESA = "Expense"

# Identificadores de tributo já em uso em `fiscal/impostos/retencoes.py` (`tributo=`) e
# implícitos nos módulos de cálculo (`icms.py`, `ipi.py`, `pis_cofins.py`, `ibs_cbs.py`).
# Mantido aqui como allowlist — se um novo tributo ganhar conta, precisa entrar nesta
# lista primeiro, nunca só aparecer solto numa `Conta`.
TRIBUTOS_CONHECIDOS = frozenset(
	{"ICMS", "IPI", "PIS", "COFINS", "ISS", "IBS", "CBS", "IRRF", "CSRF", "INSS"}
)


class PlanoDeContasInvalido(ValueError):
	"""Estrutura da árvore viola uma invariante — nome duplicado ou tributo desconhecido."""


@dataclass(frozen=True)
class Conta:
	"""Um nó do plano de contas: grupo (tem `filhas`) ou conta de lançamento (não tem).

	`tipo` é o `account_type` do ERPNext (`"Tax"`, `"Fixed Asset"`, `"Bank"`, ...) —
	vazio quando a conta não precisa de comportamento especial. `tributo`, quando
	preenchido, precisa estar em `TRIBUTOS_CONHECIDOS` (verificado por `validar_arvore`,
	não confiado ao chamador).
	"""

	nome: str
	tipo: str = ""
	tributo: str = ""
	filhas: tuple["Conta", ...] = field(default_factory=tuple)

	@property
	def eh_grupo(self) -> bool:
		return bool(self.filhas)


def _grupo(nome: str, *filhas: Conta) -> Conta:
	return Conta(nome, filhas=filhas)


def _tributo(nome: str, tributo: str, tipo: str = "Tax") -> Conta:
	return Conta(nome, tipo=tipo, tributo=tributo)


# --------------------------------------------------------------------------------------
# ATIVO — Art. 178, § 1º
# --------------------------------------------------------------------------------------
_ATIVO = _grupo(
	"Ativo",
	_grupo(
		"Ativo Circulante",
		Conta("Disponibilidades"),
		_grupo(
			"Impostos a Recuperar",
			_tributo("ICMS a Recuperar", "ICMS"),
			_tributo("IPI a Recuperar", "IPI"),
			_tributo("PIS a Recuperar", "PIS"),
			_tributo("COFINS a Recuperar", "COFINS"),
		),
		_grupo(
			"Impostos Retidos a Compensar",
			_tributo("IRRF Retido a Compensar", "IRRF"),
			_tributo("CSRF Retido a Compensar", "CSRF"),
			_tributo("INSS Retido a Compensar", "INSS"),
			_tributo("ISS Retido a Compensar", "ISS"),
		),
		Conta("Estoques", tipo="Stock"),
	),
	_grupo(
		"Ativo Não Circulante",
		Conta("Ativo Realizável a Longo Prazo"),
		Conta("Investimentos"),
		Conta("Imobilizado", tipo="Fixed Asset"),
		Conta("Intangível"),
	),
)

# --------------------------------------------------------------------------------------
# PASSIVO — Art. 178, § 2º
# --------------------------------------------------------------------------------------
_PASSIVO = _grupo(
	"Passivo",
	_grupo(
		"Passivo Circulante",
		_grupo(
			"Obrigações Tributárias",
			_tributo("ICMS a Recolher", "ICMS"),
			_tributo("IPI a Recolher", "IPI"),
			_tributo("PIS a Recolher", "PIS"),
			_tributo("COFINS a Recolher", "COFINS"),
			_tributo("ISS a Recolher", "ISS"),
			_tributo("IBS a Recolher", "IBS"),
			_tributo("CBS a Recolher", "CBS"),
			# Substitui os seis tributos acima para quem opta pelo Simples Nacional —
			# não convive com eles na mesma apuração (ver docstring do módulo).
			Conta("Simples Nacional a Recolher", tipo="Tax"),
		),
		_grupo(
			"Obrigações por Retenção de Terceiros",
			_tributo("IRRF a Recolher", "IRRF"),
			_tributo("CSRF a Recolher", "CSRF"),
			_tributo("INSS a Recolher", "INSS"),
		),
		Conta("Fornecedores"),
	),
	Conta("Passivo Não Circulante"),
	_grupo(
		"Patrimônio Líquido",
		Conta("Capital Social"),
		Conta("Reservas de Capital"),
		Conta("Ajustes de Avaliação Patrimonial"),
		Conta("Reservas de Lucros"),
		Conta("Ações em Tesouraria"),
		Conta("Prejuízos Acumulados"),
	),
)

# --------------------------------------------------------------------------------------
# RECEITA — Art. 187, I e II (Receita Líquida é subtotal calculado, não conta própria)
# --------------------------------------------------------------------------------------
_RECEITA = _grupo(
	"Receita",
	Conta("Receita Bruta de Vendas e Serviços"),
	_grupo(
		"Deduções da Receita Bruta",
		_tributo("ICMS sobre Vendas", "ICMS"),
		_tributo("PIS sobre Vendas", "PIS"),
		_tributo("COFINS sobre Vendas", "COFINS"),
		_tributo("ISS sobre Serviços", "ISS"),
		_tributo("IBS sobre Vendas", "IBS"),
		_tributo("CBS sobre Vendas", "CBS"),
		Conta("Abatimentos e Devoluções"),
	),
)

# --------------------------------------------------------------------------------------
# DESPESA — Art. 187, II e III (Lucro Bruto é subtotal calculado, não conta própria)
# --------------------------------------------------------------------------------------
_DESPESA = _grupo(
	"Despesa",
	Conta("Custo das Mercadorias e Serviços Vendidos", tipo="Cost of Goods Sold"),
	Conta("Despesas com Vendas"),
	Conta("Despesas Gerais e Administrativas"),
	Conta("Despesas Financeiras"),
	Conta("Outras Despesas Operacionais"),
)

# Árvore completa: (root_type, raiz) — mesma ordem do Art. 178 (ativo, passivo) seguida
# das duas colunas da DRE (receita, despesa).
ARVORE: tuple[tuple[str, Conta], ...] = (
	(ROOT_TYPE_ATIVO, _ATIVO),
	(ROOT_TYPE_PASSIVO, _PASSIVO),
	(ROOT_TYPE_RECEITA, _RECEITA),
	(ROOT_TYPE_DESPESA, _DESPESA),
)


def _percorrer(conta: Conta):
	yield conta
	for filha in conta.filhas:
		yield from _percorrer(filha)


def listar_nomes(arvore: tuple[tuple[str, Conta], ...] = ARVORE) -> list[str]:
	"""Todos os nomes de conta da árvore, em ordem de percurso (raiz antes das filhas)."""
	nomes = []

	for _root_type, raiz in arvore:
		for conta in _percorrer(raiz):
			nomes.append(conta.nome)

	return nomes


def contas_do_tributo(tributo: str, arvore: tuple[tuple[str, Conta], ...] = ARVORE) -> list[Conta]:
	"""Todas as contas amarradas a um tributo (a recolher, a recuperar, retido...).

	Devolve lista vazia para tributo desconhecido ou sem conta — nunca levanta: quem
	precisa garantir que o tributo existe usa `validar_arvore`, não este atalho.
	"""
	return [
		conta
		for _root_type, raiz in arvore
		for conta in _percorrer(raiz)
		if conta.tributo == tributo
	]


def validar_arvore(arvore: tuple[tuple[str, Conta], ...] = ARVORE) -> None:
	"""Invariantes da árvore: nome único, tributo sempre em `TRIBUTOS_CONHECIDOS`.

	Chamado pelos testes, não em tempo de import — a árvore módulo-level já é a
	confiável (`ARVORE`); isto existe para validar variações e regressão futura.
	"""
	nomes = listar_nomes(arvore)
	duplicados = {nome for nome in nomes if nomes.count(nome) > 1}

	if duplicados:
		raise PlanoDeContasInvalido(f"Nome de conta duplicado: {sorted(duplicados)}")

	for _root_type, raiz in arvore:
		for conta in _percorrer(raiz):
			if conta.tributo and conta.tributo not in TRIBUTOS_CONHECIDOS:
				raise PlanoDeContasInvalido(
					f"Conta {conta.nome!r} referencia tributo desconhecido {conta.tributo!r} "
					"— adicione-o a TRIBUTOS_CONHECIDOS primeiro"
				)
