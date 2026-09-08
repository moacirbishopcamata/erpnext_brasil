# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Liga a depreciação fiscal brasileira ao `Asset` do ERPNext — sem inventar campo nenhum.

O débito que este módulo paga
------------------------------------
`contabil/depreciacao.py` nasceu no commit anterior com o cálculo completo e **nada num
site o chamava** — o mesmo formato de gap que a emissão de NF-e teve antes de
`emissao_nfe.py`. Declarar o débito e pagá-lo em seguida é a disciplina de
`docs/gaps.md`; deixá-lo acumular seria o oposto.

Por que não se criou campo customizado
---------------------------------------------
Porque o ERPNext já tem a estrutura certa, e ela é melhor do que qualquer coisa que se
inventasse aqui:

- **`Asset Finance Book`** é tabela filha de `Asset`: um ativo pode ter **vários livros**,
  cada um com o seu método, taxa e cronograma. É exatamente a separação entre depreciação
  contábil e fiscal que o art. 321 do RIR pressupõe — e que, sem ela, obrigaria a escolher
  uma das duas.
- **`Asset Shift Factor`** guarda `shift_name` + `shift_factor`: é onde os coeficientes do
  art. 323 cabem sem violência.
- **`available_for_use_date`** do `Asset` é, literalmente, a data em que o bem foi *"posto
  em serviço"* do art. 317, § 2º.

Criar `br_taxa_depreciacao` ao lado de `rate_of_depreciation` produziria duas verdades
sobre a mesma taxa — o erro que já se evitou em `Bank Account` com o número da conta.

⚠️ Os dois padrões do ERPNext que a lei brasileira não admite
--------------------------------------------------------------------
São os dois que `validar_livro_fiscal` recusa, e ambos passam despercebidos porque
**produzem números plausíveis**:

1. **`depreciation_method` diferente de "Straight Line".** *Written Down Value* e *Double
   Declining Balance* aplicam a taxa sobre o saldo residual; o art. 319 manda aplicá-la
   sobre o **custo de aquisição**. A primeira quota é igual nos dois — a diferença só
   aparece do segundo período em diante.
2. **`daily_prorata_based` marcado.** O art. 319, § 2º **dispensa** o ajuste para bens
   postos em funcionamento ou baixados no curso do mês. Ratear por dias deduz a menos, e a
   diferença atravessa a vida inteira do bem.

Nenhum dos dois levanta erro no ERPNext: são configurações válidas para outros países.

Estado de verificação
----------------------------
Exercitado em site **v16 real** (`tests_bench/test_depreciacao_ativo.py`, seis casos): as
duas recusas disparam ao gravar um `Asset`, a configuração correta passa, e um segundo livro
com método diferente **não** é conferido — que é o ponto, porque o método contábil pode
legitimamente ser outro.

Os dois primeiros testes cobrem o que nenhuma suíte pura alcança: `instalar_livro_fiscal` e
`instalar_turnos` rodam no `after_migrate`, e uma falha ali não apareceria em teste algum —
o `Finance Book` simplesmente não existiria. Os três turnos são relidos do banco e
comparados com `COEFICIENTE_POR_TURNOS`, para que o número da lei não ganhe uma terceira
cópia.
"""

import frappe
from frappe import _

from erpnext_brasil.contabil.depreciacao import COEFICIENTE_POR_TURNOS, TAXAS_ANUAIS

__all__ = [
	"LIVRO_FISCAL",
	"METODO_EXIGIDO",
	"TURNOS_POR_NOME",
	"aplicar_taxa_fiscal",
	"instalar_livro_fiscal",
	"instalar_turnos",
	"validar_livro_fiscal",
]

LIVRO_FISCAL = "Fiscal (Brasil)"
"""Nome do `Finance Book` que carrega a depreciação da lei brasileira.

Livro **à parte** do contábil de propósito: o art. 321 do RIR trata os dois como números
distintos, e é da diferença entre eles que nasce a exclusão no Lalur. Fundi-los apagaria a
própria informação que o Lalur precisa.
"""

METODO_EXIGIDO = "Straight Line"
"""O único método compatível com o art. 319 — ver a docstring do módulo."""

TURNOS_POR_NOME = {
	"1 Turno (8h)": 1,
	"2 Turnos (16h)": 2,
	"3 Turnos (24h)": 3,
}
"""Nomes dos `Asset Shift Factor` criados por este app, e os turnos que representam.

Os rótulos são deste projeto; os **fatores** vêm de `COEFICIENTE_POR_TURNOS`, que por sua
vez cita o art. 323. Nenhum número é digitado aqui: repetir 1,5 num segundo lugar é como
duas tabelas de UF divergirem.
"""


def instalar_turnos() -> None:
	"""Cria os `Asset Shift Factor` do art. 323, se ainda não existirem.

	Idempotente, e **não sobrescreve** o que já está lá: se alguém ajustou um fator, foi
	decisão de quem administra o site — e reescrevê-la a cada `migrate` é o tipo de
	silêncio que este projeto trata como pior que erro.
	"""
	for nome, turnos in TURNOS_POR_NOME.items():
		if frappe.db.exists("Asset Shift Factor", nome):
			continue

		frappe.get_doc(
			{
				"doctype": "Asset Shift Factor",
				"shift_name": nome,
				"shift_factor": float(COEFICIENTE_POR_TURNOS[turnos]),
				"default": 1 if turnos == 1 else 0,
			}
		).insert(ignore_permissions=True)


def instalar_livro_fiscal() -> None:
	"""Cria o `Finance Book` fiscal, se ainda não existir. Idempotente."""
	if frappe.db.exists("Finance Book", LIVRO_FISCAL):
		return

	frappe.get_doc({"doctype": "Finance Book", "finance_book_name": LIVRO_FISCAL}).insert(
		ignore_permissions=True
	)


def aplicar_taxa_fiscal(asset: str, especie: str) -> dict:
	"""Acrescenta (ou atualiza) a linha do livro fiscal de um `Asset`, pela espécie do bem.

	`especie` é uma chave de `TAXAS_ANUAIS` — o núcleo do Anexo III da IN 1.700/2017.

	A data de início vem de `available_for_use_date`, e não de `purchase_date`: o art. 317,
	§ 2º manda depreciar a partir de quando o bem é *"instalado, posto em serviço ou em
	condições de produzir"*. Comprar não é usar, e a diferença entre as duas datas é dedução
	tomada antes da hora.

	Devolve o que ficou gravado, para quem chamou conferir.
	"""
	taxa_e_vida = TAXAS_ANUAIS.get(especie)

	if taxa_e_vida is None:
		frappe.throw(
			_("Espécie {0} não está no núcleo do Anexo III. Conhecidas: {1}.").format(
				especie, ", ".join(sorted(TAXAS_ANUAIS))
			)
		)

	taxa, vida_util_anos = taxa_e_vida

	doc = frappe.get_doc("Asset", asset)
	doc.check_permission("write")

	if not doc.get("available_for_use_date"):
		frappe.throw(
			_(
				"O ativo {0} não tem data de disponibilidade para uso. A depreciação fiscal "
				"começa quando o bem é posto em serviço, não quando é comprado (RIR/2018, "
				"art. 317, § 2º)."
			).format(asset)
		)

	linha = None

	for existente in doc.get("finance_books") or []:
		if existente.finance_book == LIVRO_FISCAL:
			linha = existente
			break

	if linha is None:
		linha = doc.append("finance_books", {"finance_book": LIVRO_FISCAL})

	linha.depreciation_method = METODO_EXIGIDO
	linha.rate_of_depreciation = float(taxa)
	# Frequência em meses: a quota é mensal (art. 319, § 2º), e o número de parcelas é a
	# vida útil em anos vezes doze. Derivado da mesma tupla do Anexo III, para que taxa e
	# prazo não possam divergir.
	linha.frequency_of_depreciation = 1
	linha.total_number_of_depreciations = vida_util_anos * 12
	linha.depreciation_start_date = doc.available_for_use_date
	# O § 2º dispensa o ajuste para bens postos em funcionamento no curso do mês — ver a
	# docstring do módulo sobre por que marcar isto deduziria a menos.
	linha.daily_prorata_based = 0

	doc.save()

	return {
		"asset": asset,
		"livro": LIVRO_FISCAL,
		"taxa": float(taxa),
		"parcelas": vida_util_anos * 12,
		"inicio": str(doc.available_for_use_date),
	}


def validar_livro_fiscal(doc, method=None) -> None:
	"""Recusa, no `validate` do `Asset`, as duas configurações que a lei não admite.

	Ligado por `doc_events` — roda sobre **qualquer** `Asset`, inclusive os que alguém
	configurou à mão. Só olha a linha do livro fiscal: os demais livros são do contador, e
	o método contábil pode legitimamente ser outro.

	Falha alto em vez de avisar. Um aviso amarelo sobre método de depreciação seria clicado
	sem ler, e o erro que ele evita **não aparece no primeiro período** — aparece do segundo
	em diante, quando ninguém mais está olhando a configuração.
	"""
	for linha in doc.get("finance_books") or []:
		if linha.finance_book != LIVRO_FISCAL:
			continue

		if linha.depreciation_method != METODO_EXIGIDO:
			frappe.throw(
				_(
					"O livro {0} exige o método {1}: o art. 319 do RIR/2018 manda aplicar a "
					"taxa sobre o custo de aquisição, e não sobre o saldo residual. "
					"Recebido: {2}."
				).format(LIVRO_FISCAL, METODO_EXIGIDO, linha.depreciation_method or _("vazio"))
			)

		if linha.get("daily_prorata_based"):
			frappe.throw(
				_(
					"O livro {0} não usa rateio diário: o art. 319, § 2º dispensa o ajuste "
					"para bens postos em funcionamento ou baixados no curso do mês."
				).format(LIVRO_FISCAL)
			)
