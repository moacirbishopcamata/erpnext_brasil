# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Registro I050 da ECD (Escrituração Contábil Digital) — Plano de Contas.

A ECD é o SPED Contábil: o livro Diário e o livro Razão em formato digital, obrigatório
para a maioria das empresas tributadas pelo lucro real/presumido. O bloco I é o
"livro digital" propriamente dito — I050 declara o plano de contas usado, I200/I250 (não
implementados ainda) trazem os lançamentos.

Este módulo é um conversor, não uma nova estrutura
--------------------------------------------------------
`montar_i050` converte `contabil/plano_de_contas.ARVORE` (mais a numeração de
`montar_codigos`, ver a seção "Numeração" na docstring daquele módulo — convenção deste
app, não exigência legal) no formato de linha que o I050 exige. Nenhuma conta nova é
inventada aqui — os grupos já vêm sourced de Lei 6.404/1976, Art. 178/187.

`COD_NAT`: Receita e Despesa compartilham o mesmo código
-------------------------------------------------------------
Confirmado em duas fontes consistentes: o campo `COD_NAT` (natureza da conta) tem
`"01"` Ativo, `"02"` Passivo, `"03"` Patrimônio Líquido e **`"04"` para as duas colunas
da DRE juntas** — receita e despesa não têm códigos separados neste campo (a distinção
entre elas se resolve por outro caminho na ECD, não pelo `COD_NAT`). Isso simplifica o
mapeamento: `ROOT_TYPE_RECEITA` e `ROOT_TYPE_DESPESA` caem os dois em `"04"`.

A pegadinha: Patrimônio Líquido não segue o `root_type` do pai
--------------------------------------------------------------------
`plano_de_contas.py` modela `Patrimônio Líquido` como um grupo **dentro** de `Passivo`
(mesmo `root_type`, `Liability`, do Art. 178, § 2º — ver `docs/plano-de-contas.md`) — o
ERPNext não distingue os dois por `root_type` porque não precisa (o doctype `Account`
tem outros campos para isso). A ECD, por outro lado, **exige** `COD_NAT` distinto:
`"02"` para o resto do Passivo, `"03"` só para o subgrupo Patrimônio Líquido. Por isso
este módulo não deriva `COD_NAT` só do `root_type` — rastreia se o nó (ou algum
ancestral) é `"Patrimônio Líquido"` e usa `"03"` nesse caso, `"02"` no resto do Passivo.

I051: mapeamento De-Para, não a tabela referencial em si
----------------------------------------------------------------
`I051` é obrigatório só quando o campo `COD_PLAN_REF` do registro `0000` (não modelado
neste app) está preenchido — quem opta por informar o plano de contas referencial da
RFB precisa mapear cada conta própria para o código referencial correspondente. Esse
mapeamento **não exige reproduzir a tabela da RFB inteira** (milhares de códigos) — só
o De-Para que o contribuinte já escolheu, conta a conta. Por isso `MapeamentoReferencial`
recebe `codigo_referencial` pronto de quem chama, igual a `Ajuste.codigo`/`AjusteIpi.
codigo` em `efd_icms_ipi.py`.

**`I051` não tem campo próprio para "qual conta"** — na estrutura hierárquica do
arquivo SPED, cada linha I051 é aninhada logo depois do `I050` da conta a que se refere
(a associação é por **posição no arquivo**, não por um campo `COD_CTA` dentro do
próprio I051). Como este módulo devolve dados, não a linha de texto posicional,
`montar_i051` devolve `(nome_da_conta, linha)` — quem monta o arquivo final decide onde
inserir cada linha.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass

from erpnext_brasil.contabil.plano_de_contas import (
	ARVORE,
	ROOT_TYPE_ATIVO,
	ROOT_TYPE_DESPESA,
	ROOT_TYPE_PASSIVO,
	ROOT_TYPE_RECEITA,
	Conta,
	listar_nomes,
	montar_codigos,
)

__all__ = [
	"COD_NAT_ATIVO",
	"COD_NAT_PASSIVO",
	"COD_NAT_PATRIMONIO_LIQUIDO",
	"COD_NAT_RESULTADO",
	"ContaDesconhecidaI051",
	"MapeamentoReferencial",
	"montar_i050",
	"montar_i051",
]

# Tabela de natureza da conta (COD_NAT) do registro I050 — confirmada em fonte técnica
# especializada, corroborada por busca cruzada (ver docs/ecd.md). Só os quatro códigos
# que este app usa; "05" (compensação) e "09" (outras) não têm grupo correspondente em
# plano_de_contas.py hoje.
COD_NAT_ATIVO = "01"
COD_NAT_PASSIVO = "02"
COD_NAT_PATRIMONIO_LIQUIDO = "03"
COD_NAT_RESULTADO = "04"

_COD_NAT_POR_ROOT_TYPE = {
	ROOT_TYPE_ATIVO: COD_NAT_ATIVO,
	ROOT_TYPE_PASSIVO: COD_NAT_PASSIVO,
	ROOT_TYPE_RECEITA: COD_NAT_RESULTADO,
	ROOT_TYPE_DESPESA: COD_NAT_RESULTADO,
}

_NOME_PATRIMONIO_LIQUIDO = "Patrimônio Líquido"


class ContaDesconhecidaI051(ValueError):
	"""`MapeamentoReferencial` referencia uma conta que não existe em `plano_de_contas.ARVORE`."""


@dataclass(frozen=True)
class MapeamentoReferencial:
	"""Um De-Para conta própria → código do plano de contas referencial da RFB.

	`conta` é o nome, mesmo vocabulário de `plano_de_contas.ARVORE` — usado só para
	`montar_i051` saber onde a linha resultante precisa ser aninhada (ver docstring do
	módulo), não é um campo do próprio registro I051.
	"""

	conta: str
	codigo_referencial: str
	centro_custo: str = ""


def montar_i051(
	mapeamentos: list[MapeamentoReferencial], arvore: tuple[tuple[str, Conta], ...] = ARVORE
) -> list[tuple[str, dict]]:
	"""`(nome_da_conta, linha_I051)` por mapeamento — a linha precisa ser inserida logo
	depois do `I050` daquela conta no arquivo final (aninhamento por posição, não por
	campo, ver docstring do módulo)."""
	nomes_validos = set(listar_nomes(arvore))

	pares: list[tuple[str, dict]] = []

	for mapeamento in mapeamentos:
		if mapeamento.conta not in nomes_validos:
			raise ContaDesconhecidaI051(f"Conta {mapeamento.conta!r} não existe em plano_de_contas.ARVORE")

		pares.append(
			(
				mapeamento.conta,
				{
					"REG": "I051",
					"COD_CCUS": mapeamento.centro_custo,
					"COD_CTA_REF": mapeamento.codigo_referencial,
				},
			)
		)

	return pares


def montar_i050(data_alteracao: str, arvore: tuple[tuple[str, Conta], ...] = ARVORE) -> list[dict]:
	"""Uma linha de campos por conta da árvore, na ordem oficial do registro I050.

	`data_alteracao` é o `DT_ALT` (data de inclusão/alteração da conta no plano) — vem
	de fora porque este módulo não decide sozinho "hoje" (a mesma razão de
	`ativar_contingencia_svc` receber `desde` como parâmetro em vez de usar
	`datetime.now()` direto: torna a função determinística e testável sem mockar tempo).
	"""
	codigos = montar_codigos(arvore)
	linhas: list[dict] = []

	def _percorrer(conta: Conta, root_type: str, dentro_do_pl: bool, codigo_pai: str | None) -> None:
		dentro_do_pl_aqui = dentro_do_pl or conta.nome == _NOME_PATRIMONIO_LIQUIDO
		cod_nat = COD_NAT_PATRIMONIO_LIQUIDO if dentro_do_pl_aqui else _COD_NAT_POR_ROOT_TYPE[root_type]
		codigo = codigos[conta.nome]

		linhas.append(
			{
				"REG": "I050",
				"DT_ALT": data_alteracao,
				"COD_NAT": cod_nat,
				"IND_CTA": "S" if conta.eh_grupo else "A",
				"NIVEL": codigo.count(".") + 1,
				"COD_CTA": codigo,
				"COD_CTA_SUP": codigo_pai or "",
				"CTA": conta.nome,
			}
		)

		for filha in conta.filhas:
			_percorrer(filha, root_type, dentro_do_pl_aqui, codigo)

	for root_type, raiz in arvore:
		_percorrer(raiz, root_type, False, None)

	return linhas
