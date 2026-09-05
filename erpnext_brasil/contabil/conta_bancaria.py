# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Os dados bancários que a cobrança brasileira exige, validados antes de virarem boleto.

Por que existe
--------------------
`boleto.montar_codigo_barras` recebe um `campo_livre` de 25 posições já pronto e valida só
o tamanho. Quem monta esse campo precisa de agência, conta, carteira e convênio — e é aí
que os erros entram, porque cada um tem tamanho próprio, alguns admitem vazio e outros não,
e a pontuação que o usuário digita (`1234-5`, `12.345-6`) não pertence ao arquivo.

Validar no momento de montar seria tarde: o boleto sairia gerado, o banco o aceitaria, e o
cliente não conseguiria pagar. Um dígito verificador no lugar errado não produz erro em
lugar nenhum do caminho — produz um título que ninguém quita.

O que este módulo **não** faz
-----------------------------------
- **Não monta o campo livre.** Ele é específico de cada banco, e cada layout exige a
  especificação da instituição. Deduzir por analogia entre bancos é exatamente o erro que
  este projeto trata como o mais caro — ver `docs/tropicalizacao-por-area.md`.
- **Não valida o dígito verificador.** Cada banco usa a sua regra (módulo 10, módulo 11 com
  bases diferentes), e conferir com a regra errada rejeitaria conta boa.
- **Não conhece a tabela COMPE.** Confere que são três dígitos; qual banco é cada código
  não é conhecimento que caiba aqui.

Funções puras: nenhuma dependência do Frappe.
"""

import re
from dataclasses import dataclass

__all__ = [
	"TAMANHOS",
	"ContaBancaria",
	"DadosBancariosInvalidos",
	"montar_conta_bancaria",
	"somente_digitos",
]

TAMANHOS = {
	"codigo_banco": 3,
	"agencia": 5,
	"agencia_dv": 1,
	"conta": 12,
	"conta_dv": 1,
	"carteira": 3,
	"convenio": 20,
}
"""Tamanho **máximo** de cada campo, em dígitos.

Máximo, não exato: agência de quatro dígitos existe, e conta varia muito entre bancos. O
que não varia é o teto — passar dele significa que o dado está errado ou veio com algo
grudado, e é isso que se pega aqui.
"""

_OBRIGATORIOS = ("codigo_banco", "agencia", "conta")
"""Sem estes três não existe cobrança.

`carteira` e `convenio` ficam de fora porque dependem do contrato com o banco, e
`agencia_dv`/`conta_dv` porque nem toda instituição os usa — exigir um dígito que o banco
não emite obrigaria o usuário a inventar um.
"""


class DadosBancariosInvalidos(ValueError):
	"""Dado que produziria um boleto que ninguém consegue pagar."""

	def __init__(self, mensagem: str, campo: str = ""):
		super().__init__(mensagem)
		self.campo = campo


def somente_digitos(valor: str | None) -> str:
	"""Remove tudo que não é dígito.

	O usuário digita `1234-5` ou `12.345-6`; o arquivo bancário não tem pontuação. Fazer
	essa limpeza aqui, e não em cada montador, é o que evita que um banco a faça e outro
	esqueça.
	"""
	return re.sub(r"\D", "", valor or "")


@dataclass(frozen=True)
class ContaBancaria:
	"""Conta de cobrança já limpa e conferida.

	Imutável de propósito: uma vez validada, é o que vai para o arquivo. Quem precisar de
	outra monta outra.
	"""

	codigo_banco: str
	agencia: str
	conta: str
	agencia_dv: str = ""
	conta_dv: str = ""
	carteira: str = ""
	convenio: str = ""

	@property
	def agencia_formatada(self) -> str:
		"""Como se escreve para um humano conferir: `1234-5`, ou `1234` sem dígito."""
		return f"{self.agencia}-{self.agencia_dv}" if self.agencia_dv else self.agencia

	@property
	def conta_formatada(self) -> str:
		return f"{self.conta}-{self.conta_dv}" if self.conta_dv else self.conta


def montar_conta_bancaria(
	codigo_banco: str,
	agencia: str,
	conta: str,
	agencia_dv: str = "",
	conta_dv: str = "",
	carteira: str = "",
	convenio: str = "",
) -> ContaBancaria:
	"""Limpa, confere e devolve a conta — ou falha alto dizendo **qual** campo está errado.

	A mensagem cita o campo porque quem vê o erro está numa tela de cadastro com sete
	caixas parecidas; "dados bancários inválidos" mandaria o usuário conferir todas.
	"""
	valores = {
		"codigo_banco": somente_digitos(codigo_banco),
		"agencia": somente_digitos(agencia),
		"conta": somente_digitos(conta),
		"agencia_dv": somente_digitos(agencia_dv),
		"conta_dv": somente_digitos(conta_dv),
		"carteira": somente_digitos(carteira),
		"convenio": somente_digitos(convenio),
	}

	for campo in _OBRIGATORIOS:
		if not valores[campo]:
			raise DadosBancariosInvalidos(f"{campo} é obrigatório para emitir cobrança", campo)

	for campo, limite in TAMANHOS.items():
		if len(valores[campo]) > limite:
			raise DadosBancariosInvalidos(
				f"{campo} admite no máximo {limite} dígitos, recebidos {len(valores[campo])}",
				campo,
			)

	# O COMPE é o único de tamanho exato: são as três primeiras posições do código de
	# barras, e um código de dois dígitos deslocaria o resto do boleto inteiro.
	if len(valores["codigo_banco"]) != TAMANHOS["codigo_banco"]:
		raise DadosBancariosInvalidos(
			f"codigo_banco deve ter exatamente {TAMANHOS['codigo_banco']} dígitos, "
			f"recebido {valores['codigo_banco']!r}",
			"codigo_banco",
		)

	return ContaBancaria(**valores)
