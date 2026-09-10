# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Códigos numéricos das recusas deste app — o que a máquina lê.

A regra
-------
**Código (número) para máquinas, mensagem para usuários.** As duas coisas juntas em toda
recusa: o número para quem trata, o texto em pt-BR para quem lê.

Por que o número, e não só a mensagem
---------------------------------------------
- A mensagem é **traduzível**. Quem tratar o erro comparando texto quebra na primeira
  melhoria de redação — e não percebe: a comparação simplesmente deixa de casar, o caminho
  alternativo some, e nada acusa.
- A classe de exceção **não atravessa a fronteira HTTP**. O JS do Desk recebe a mensagem,
  não o tipo. Do lado do cliente, tipo não existe; número existe.
- Registro, log e suporte precisam de algo curto e citável. "Erro 1002" se procura num
  histórico; um parágrafo em português, não.

⚠️ Por que começam em 1000
---------------------------------
Para **não colidir com o `cStat` da SEFAZ**, que tem três dígitos e significado normativo
(`100` autorizado, `137` nenhum documento localizado, `656` consumo indevido). Um código
nosso na faixa de três dígitos mandaria alguém procurar na tabela do Fisco e concluir que a
SEFAZ recusou algo que ela nunca viu.

**Onde já existe código oficial, ele é o código.** Não se inventa um número paralelo para o
que a SEFAZ ou o eSocial já numeraram — ver `SEFAZ_BLOQUEADO_POR_CONSUMO_INDEVIDO`, que
existe para a **nossa** recusa preventiva, e não para a rejeição da SEFAZ (essa é `656`, e é
citada na mensagem como tal).

Estabilidade
------------
Código publicado **não muda de significado**. Reaproveitar um número para outra condição é
pior que não ter número: quem tratava a condição antiga passa a tratar a nova sem saber.
Condição que deixa de existir tem o código aposentado, nunca reciclado.

Sem dependência do Frappe: é dado, e a suíte de costura o lê sem bench.
"""

__all__ = [
	"CADASTRO_CODIGO_DE_MUNICIPIO_INVALIDO",
	"CADASTRO_CPF_CNPJ_INVALIDO",
	"CADASTRO_INSCRICAO_ESTADUAL_INVALIDA",
	"CADASTRO_NCM_INVALIDO",
	"DOCUMENTO_APURACAO_IMPOSSIVEL",
	"DOCUMENTO_CHAVE_DE_ACESSO_INVALIDA",
	"DOCUMENTO_CLASSIFICACAO_INCOMPATIVEL",
	"ESTOQUE_PERDA_EM_FINALIDADE_INCOMPATIVEL",
	"ESTOQUE_PERDA_SEM_VALOR",
	"ESTOQUE_SOBRA_CLASSIFICADA_COMO_PERDA",
	"PRIMEIRO_CODIGO",
	"SEFAZ_BLOQUEADO_POR_CONSUMO_INDEVIDO",
	"TODOS",
	"formatar",
]

PRIMEIRO_CODIGO = 1000
"""O piso da faixa. Abaixo dele é território do `cStat` — ver a nota do módulo."""

# As centenas agrupam por assunto, e o agrupamento é para quem lê o log, não para o código:
# `11xx` cadastro, `12xx` documento fiscal, `10xx` estoque e SEFAZ. Um número solto não diz
# de onde veio; `1102` já situa quem procura antes mesmo de abrir a tabela.

# -------------------------------------------------------------------------------- cadastro
CADASTRO_CPF_CNPJ_INVALIDO = 1101
"""`tax_id` que não passa no dígito verificador, em Company, Customer ou Supplier."""

CADASTRO_INSCRICAO_ESTADUAL_INVALIDA = 1102
"""IE que não fecha pelo algoritmo da UF do endereço."""

CADASTRO_CODIGO_DE_MUNICIPIO_INVALIDO = 1103
"""Código IBGE do município fora dos 7 dígitos."""

CADASTRO_NCM_INVALIDO = 1104
"""NCM fora dos 8 dígitos."""

# -------------------------------------------------------------------------------- documento
DOCUMENTO_CHAVE_DE_ACESSO_INVALIDA = 1201
"""Chave de 44 posições com layout ou dígito verificador errado.

Inclui a URL do QR Code da NFC-e que não contenha uma chave legível — o campo aceita as
duas formas de entrada, e a recusa é a mesma.
"""

DOCUMENTO_CLASSIFICACAO_INCOMPATIVEL = 1202
"""CST e cClassTrib que a SEFAZ recusaria — inclusive o par preenchido pela metade."""

DOCUMENTO_APURACAO_IMPOSSIVEL = 1203
"""Os dados da linha não permitem calcular os tributos.

⚠️ Diferente de "imposto zero": zero é resultado válido de item sem alíquota. Este código é
para quando o cálculo **não pôde ser feito**, e confundir os dois faria alguém procurar
alíquota onde falta dado.
"""

DOCUMENTO_CONSOLIDADO_NAO_EMITE = 1204
"""Fatura consolidada do ponto de venda, que agrega cupons já emitidos.

Emitir sobre ela documentaria as mesmas operações duas vezes — uma no cupom entregue ao
consumidor, outra na nota. A recusa é da **emissão**: a fatura em si é legítima, é peça
contábil do fechamento de caixa.
"""

DOCUMENTO_CONTINGENCIA_INDISPONIVEL_PARA_PESSOA_FISICA = 1205
"""Emitente Pessoa Física tentando emitir NFC-e em contingência off-line.

O QR Code da versão 2 é rejeição 444 para CPF, e o da versão 3 — que seria o caminho dele —
não está implementado. Recusar a venda é o único dano reversível: o cupom entregue de um
documento que a SEFAZ nunca aceitará não é.
"""

# --------------------------------------------------------------------------------- estoque
ESTOQUE_PERDA_EM_FINALIDADE_INCOMPATIVEL = 1001
"""Tipo de perda num `Stock Entry` cuja finalidade não é baixa."""

ESTOQUE_SOBRA_CLASSIFICADA_COMO_PERDA = 1002
"""`Stock Reconciliation` com diferença positiva e tipo de perda preenchido."""

ESTOQUE_PERDA_SEM_VALOR = 1003
"""Perda classificada sobre baixa de valor zero."""

# ---------------------------------------------------------------------------------- SEFAZ
SEFAZ_BLOQUEADO_POR_CONSUMO_INDEVIDO = 1010
"""Recusa **preventiva** nossa, durante a janela de bloqueio.

Não confundir com o `cStat 656`, que é a rejeição da SEFAZ. Este código diz "nós impedimos a
requisição de sair"; aquele diz "a SEFAZ recusou o que saiu". São eventos diferentes, e
tratá-los como um só apagaria justamente a distinção que evita estender o bloqueio.
"""

TODOS = {
	CADASTRO_CPF_CNPJ_INVALIDO,
	CADASTRO_INSCRICAO_ESTADUAL_INVALIDA,
	CADASTRO_CODIGO_DE_MUNICIPIO_INVALIDO,
	CADASTRO_NCM_INVALIDO,
	DOCUMENTO_CHAVE_DE_ACESSO_INVALIDA,
	DOCUMENTO_CLASSIFICACAO_INCOMPATIVEL,
	DOCUMENTO_APURACAO_IMPOSSIVEL,
	DOCUMENTO_CONSOLIDADO_NAO_EMITE,
	DOCUMENTO_CONTINGENCIA_INDISPONIVEL_PARA_PESSOA_FISICA,
	ESTOQUE_PERDA_EM_FINALIDADE_INCOMPATIVEL,
	ESTOQUE_SOBRA_CLASSIFICADA_COMO_PERDA,
	ESTOQUE_PERDA_SEM_VALOR,
	SEFAZ_BLOQUEADO_POR_CONSUMO_INDEVIDO,
}
"""Todos os códigos publicados, para o teste conferir unicidade e faixa.

Conjunto, não lista: dois nomes com o mesmo número colapsariam aqui, e o teste de tamanho
acusa. Uma lista esconderia a duplicata.
"""


def formatar(codigo: int, mensagem: str) -> str:
	"""Junta código e mensagem no formato que o usuário vê e a máquina reconhece.

	O código vem **primeiro e entre colchetes** por dois motivos: fica visível numa captura
	de tela cortada, e é o começo da string — quem procurar por prefixo acha sem varrer o
	texto inteiro.

	A mensagem não é encurtada por causa do código. As duas coisas convivem: o número não
	substitui a explicação, porque quem lê a tela precisa saber **o que fazer**, e um número
	não diz isso.
	"""
	return f"[{codigo}] {mensagem}"
