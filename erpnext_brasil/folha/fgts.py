# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""FGTS: Fundo de Garantia do Tempo de Serviço.

Terceiro cálculo do bloco RH, depois de `inss.py` e `irrf.py`. Diferença estrutural
importante em relação aos dois anteriores: FGTS **não é desconto do empregado** — é
um depósito que o empregador faz, por fora do salário líquido, numa conta vinculada
do trabalhador. Não aparece como dedução na folha; aparece como obrigação do
empregador, com naturalmente outro lançamento contábil (`contabil/lancamento.py` não
tem ainda uma função dedicada a isto — é um item futuro, não implementado aqui).

Dois cálculos, duas fontes na mesma lei
------------------------------------------
- **Depósito mensal** (Lei 8.036/1990, Art. 15): 8% da remuneração mensal do
  trabalhador — 2% para o aprendiz, ressalva do Art. 15 (regulamentada pelo Art. 24,
  parágrafo único, do Decreto 5.598/2005, sobre o contrato de aprendizagem).
- **Multa rescisória** (Lei 8.036/1990, Art. 18, §1º e §2º; e Art. 484-A da CLT,
  incluído pela Lei 13.467/2017 — reforma trabalhista): incide sobre o total de
  depósitos feitos durante o contrato (não sobre o "saldo" — a lei fala em "montante
  de todos os depósitos... atualizados monetariamente e acrescidos dos respectivos
  juros", uma base histórica acumulada, que este módulo recebe pronta do chamador,
  nunca recalcula a partir do zero). Percentual depende do motivo do desligamento:
  dispensa sem justa causa → 40%; rescisão por acordo (Art. 484-A CLT) → 20% (metade
  da multa cheia); culpa recíproca ou força maior, reconhecida pela Justiça do
  Trabalho (Art. 18 §2º da Lei 8.036/90) → 20%; justa causa, pedido de demissão ou
  término de contrato por prazo determinado → sem multa.

O que este módulo deliberadamente não faz
------------------------------------------------
- **Não calcula o prazo de recolhimento.** O vencimento mensal (dia 20 do mês
  subsequente, antecipado para o dia útil anterior quando cai em dia não útil, desde
  a migração para o FGTS Digital em 2024) depende de um calendário de feriados
  nacionais que este projeto não modela em nenhum outro módulo — mesma disciplina de
  `boleto.py` não inferir o `campo_livre`: dado que exige uma tabela externa que não
  existe aqui fica com o chamador.
- **Não decide o percentual de saque da conta vinculada** (80% em caso de acordo,
  regras de saque-aniversário) — isso é direito de saque do trabalhador, não
  obrigação de depósito/multa do empregador, categoria de regra diferente da que
  este módulo cobre.
- **Não soma FGTS sobre 13º salário/férias separadamente** — quem chama já deve
  incluir esses valores na `remuneracao` do mês em que são pagos, mesma disciplina
  de `irrf.calcular_irrf` receber a base já pronta.

Funções puras: nenhuma dependência do Frappe.
"""

from decimal import ROUND_HALF_UP, Decimal

__all__ = [
	"ALIQUOTA_APRENDIZ",
	"ALIQUOTA_PADRAO",
	"ALIQUOTA_MULTA_POR_MOTIVO",
	"FGTSInvalido",
	"calcular_deposito_mensal",
	"calcular_multa_rescisoria",
]

# Lei 8.036/1990, Art. 15.
ALIQUOTA_PADRAO = Decimal("0.08")

# Lei 8.036/1990, Art. 15, ressalva ao aprendiz — regulamentada pelo Decreto
# 5.598/2005, Art. 24, parágrafo único.
ALIQUOTA_APRENDIZ = Decimal("0.02")

# Lei 8.036/1990, Art. 18, §1º e §2º; Art. 484-A da CLT (Lei 13.467/2017).
# "Sem multa" não é ausência de regra — é o percentual correto para esses motivos.
ALIQUOTA_MULTA_POR_MOTIVO = {
	"sem_justa_causa": Decimal("0.40"),
	"acordo": Decimal("0.20"),
	"culpa_reciproca_ou_forca_maior": Decimal("0.20"),
	"justa_causa": Decimal("0.00"),
	"pedido_de_demissao": Decimal("0.00"),
	"termino_de_contrato_determinado": Decimal("0.00"),
}


class FGTSInvalido(ValueError):
	"""Dado que impede o cálculo — valor negativo, ou motivo de desligamento não
	reconhecido (nunca assumido como "sem multa" por omissão)."""


def _arredondar(valor: Decimal) -> Decimal:
	return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_deposito_mensal(remuneracao: Decimal, *, aprendiz: bool = False) -> Decimal:
	"""Depósito mensal do FGTS — 8% da remuneração, ou 2% se `aprendiz=True`
	(contrato de aprendizagem, Decreto 5.598/2005)."""
	if remuneracao < Decimal("0"):
		raise FGTSInvalido(f"remuneracao não pode ser negativa, recebida {remuneracao}")

	aliquota = ALIQUOTA_APRENDIZ if aprendiz else ALIQUOTA_PADRAO

	return _arredondar(remuneracao * aliquota)


def calcular_multa_rescisoria(total_depositado: Decimal, motivo: str) -> Decimal:
	"""Multa rescisória sobre o total histórico de depósitos do contrato (não um
	saldo atual) — o percentual depende do motivo do desligamento, nunca um valor
	fixo. `motivo` fora de `ALIQUOTA_MULTA_POR_MOTIVO` levanta erro: a ausência de
	multa para justa causa/pedido de demissão é uma decisão explícita da tabela, não
	o comportamento padrão para qualquer string desconhecida."""
	if total_depositado < Decimal("0"):
		raise FGTSInvalido(f"total_depositado não pode ser negativo, recebido {total_depositado}")

	if motivo not in ALIQUOTA_MULTA_POR_MOTIVO:
		raise FGTSInvalido(
			f"Motivo de desligamento {motivo!r} não reconhecido — motivos válidos: "
			f"{sorted(ALIQUOTA_MULTA_POR_MOTIVO)}."
		)

	return _arredondar(total_depositado * ALIQUOTA_MULTA_POR_MOTIVO[motivo])
