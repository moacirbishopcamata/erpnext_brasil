# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Transferência entre estabelecimentos do mesmo titular: não é venda, e não é isenta.

⚠️ A regra mudou, e o que "todo mundo sabe" está desatualizado
----------------------------------------------------------------------
Durante décadas a transferência entre estabelecimentos do mesmo dono foi tratada como
operação tributada normal — destacava ICMS, e a discussão sobre isso chegou ao STF. Com a
**ADC 49** o Supremo declarou que não há fato gerador: mercadoria que troca de
estabelecimento **sem trocar de titular** não sofre circulação jurídica.

A **LC 204/2023** levou isso para a Lei Kandir (art. 12, § 4º), e depois da derrubada do
veto ao § 5º o CONFAZ celebrou o **Convênio ICMS 109/2024**, que revogou o 178/2023 e vale
desde **1º/11/2024**.

Resultado prático, e é contraintuitivo: **não incide o imposto, mas o crédito é
transferido — obrigatoriamente**. Quem lê "não incide" e conclui "então não põe nada na
nota" perde o crédito da mercadoria; quem lê "é como uma venda" e destaca imposto tributa
o que a lei diz não ser fato gerador. As duas leituras erram, em direções opostas.

Os dois caminhos que a lei oferece
-----------------------------------------
| Caminho | Base | O que acontece |
|---|---|---|
| **Regra** (cláusulas 1ª a 4ª) | LC 87/96, art. 12, § 4º | não incide; o crédito das operações anteriores é **transferido** ao destino |
| **Equiparação** (cláusula 6ª) | LC 87/96, art. 12, § 5º | por opção do contribuinte, a transferência é equiparada a operação tributada **para todos os fins** |

A opção pela equiparação é **anual e irretratável**, registrada até 31 de dezembro para
valer no ano seguinte. Não é uma escolha por nota: por isso ela é um parâmetro de quem
chama, não uma decisão deste módulo.

Como o crédito é transferido (cláusulas 3ª e 4ª)
--------------------------------------------------------
A cada remessa, consignando o valor **na própria NF-e, no campo do destaque do imposto**.
O valor é o imposto apropriado nas operações anteriores, **limitado** à aplicação das
alíquotas interestaduais sobre uma destas bases:

I. o valor médio da entrada em estoque;
II. o custo de produção;
III. os custos de produção, para mercadoria não industrializada.

Este módulo calcula o limite e aplica; **qual das três bases usar é do contribuinte**, e
inventar essa escolha seria decidir contabilidade alheia.

O que **não** está aqui, declarado
-----------------------------------------
- **Transferência dentro do mesmo estado.** O Convênio 109/24 trata das remessas
  **interestaduais** — a cláusula quinta manda observar as regras da operação
  interestadual. A transferência interna fica com a legislação do estado (no nosso caso, o
  RICMS de Rondônia), e escrever uma regra nacional para ela seria invenção.
- **A escrituração do crédito.** A cláusula segunda manda lançar a débito no registro de
  saídas do remetente e a crédito no de entradas do destinatário — é EFD, e está nas
  pendências de `docs/sped-fiscal.md`.
- **O cálculo da operação equiparada.** Quando o contribuinte optou pela equiparação, o
  imposto é o de uma operação tributada comum, e isso já existe em `impostos/icms.py`.
  Duplicá-lo aqui criaria duas contas de ICMS.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from decimal import Decimal

from erpnext_brasil.fiscal.impostos.icms import arredondar
from erpnext_brasil.fiscal.validators import limpar

__all__ = [
	"BASES_DA_CLAUSULA_QUARTA",
	"BASE_CUSTO_DE_PRODUCAO",
	"BASE_CUSTO_DO_NAO_INDUSTRIALIZADO",
	"BASE_VALOR_MEDIO_DE_ENTRADA",
	"TAMANHO_DA_RAIZ",
	"CreditoTransferido",
	"TransferenciaInvalida",
	"mesmo_titular",
	"transferir_credito",
]

ZERO = Decimal("0.00")

BASE_VALOR_MEDIO_DE_ENTRADA = "valor medio de entrada em estoque"
BASE_CUSTO_DE_PRODUCAO = "custo de producao"
BASE_CUSTO_DO_NAO_INDUSTRIALIZADO = "custo do nao industrializado"

BASES_DA_CLAUSULA_QUARTA = (
	BASE_VALOR_MEDIO_DE_ENTRADA,
	BASE_CUSTO_DE_PRODUCAO,
	BASE_CUSTO_DO_NAO_INDUSTRIALIZADO,
)
"""Os incisos I, II e III da cláusula quarta, nesta ordem.

Declarados como dado porque a escolha é do contribuinte e precisa ser **registrada** — uma
transferência cujo limite foi calculado sobre custo de produção e outra sobre valor médio
de entrada não se explicam sozinhas depois.
"""


class TransferenciaInvalida(ValueError):
	"""Parâmetro que não descreve uma transferência apurável."""


@dataclass(frozen=True)
class CreditoTransferido:
	"""O crédito que segue na NF-e, e a conta que o justifica.

	Guardar `limite` e `credito_apropriado` lado a lado é o ponto: quando o crédito
	apropriado supera o limite, a diferença **fica no remetente** — e quem vê só o valor
	transferido não sabe que sobrou crédito para trás.
	"""

	credito_transferido: Decimal
	limite: Decimal
	credito_apropriado: Decimal
	base_utilizada: str

	@property
	def limitado(self) -> bool:
		"""O crédito apropriado bateu no teto da cláusula quarta."""
		return self.credito_apropriado > self.limite

	@property
	def credito_retido_na_origem(self) -> Decimal:
		"""O que não coube no limite e permanece no estabelecimento remetente."""
		return self.credito_apropriado - self.credito_transferido


def transferir_credito(
	valor_da_base: Decimal,
	aliquota_interestadual: Decimal,
	credito_apropriado: Decimal,
	base_utilizada: str = BASE_VALOR_MEDIO_DE_ENTRADA,
	equiparado: bool = False,
) -> CreditoTransferido:
	"""Apura o crédito a consignar na NF-e da transferência interestadual.

	`equiparado=True` **levanta**, e de propósito: quem optou pela cláusula sexta não
	transfere crédito, tributa a operação como qualquer outra. Devolver um número aqui
	daria ao optante uma segunda conta de ICMS, paralela à correta.
	"""
	if equiparado:
		raise TransferenciaInvalida(
			"o contribuinte optou pela equiparação da cláusula sexta: a transferência é "
			"operação tributada para todos os fins, e o imposto sai de `impostos/icms.py` — "
			"não há crédito a transferir"
		)

	if base_utilizada not in BASES_DA_CLAUSULA_QUARTA:
		raise TransferenciaInvalida(
			f"base deve ser uma das da cláusula quarta {list(BASES_DA_CLAUSULA_QUARTA)}, "
			f"recebida {base_utilizada!r}"
		)

	for nome, valor in (
		("valor_da_base", valor_da_base),
		("aliquota_interestadual", aliquota_interestadual),
		("credito_apropriado", credito_apropriado),
	):
		if not isinstance(valor, Decimal):
			raise TransferenciaInvalida(f"{nome} deve ser Decimal, recebido {type(valor).__name__}")

	if valor_da_base <= ZERO:
		raise TransferenciaInvalida(
			f"a base precisa ser positiva, recebida {valor_da_base} — transferência sem base "
			"não tem limite a calcular"
		)

	if not (ZERO < aliquota_interestadual < Decimal(1)):
		raise TransferenciaInvalida(
			f"alíquota deve ser fração entre 0 e 1, recebida {aliquota_interestadual} — 12% é 0.12, não 12"
		)

	if credito_apropriado < ZERO:
		raise TransferenciaInvalida(
			f"crédito apropriado não pode ser negativo, recebido {credito_apropriado}"
		)

	limite = arredondar(valor_da_base * aliquota_interestadual)

	return CreditoTransferido(
		credito_transferido=min(arredondar(credito_apropriado), limite),
		limite=limite,
		credito_apropriado=arredondar(credito_apropriado),
		base_utilizada=base_utilizada,
	)


TAMANHO_DA_RAIZ = 8
"""Os caracteres iniciais do CNPJ que identificam o **titular**.

O CNPJ tem três partes: raiz (8), ordem do estabelecimento (4) e dígitos verificadores (2).
Dois estabelecimentos do mesmo dono compartilham a raiz e diferem na ordem — `0001` é a
matriz, `0002` em diante são filiais.

Oito, e não doze: comparar até a ordem faria dois estabelecimentos **nunca** serem do mesmo
titular, e a função devolveria `False` sempre.
"""


def mesmo_titular(cnpj_origem: str | None, cnpj_destino: str | None) -> bool:
	"""Os dois estabelecimentos pertencem ao mesmo titular?

	⚠️ **É esta pergunta que separa transferência de venda.** Duas empresas do mesmo grupo
	econômico, com raízes de CNPJ diferentes, fazem entre si uma **venda** normal — com
	incidência, com destaque de imposto. A não incidência do art. 12, § 4º vale só para o
	**mesmo titular**, e tratar grupo econômico como titular único deixaria de tributar uma
	operação tributável.

	`False` quando qualquer um dos dois é vazio ou curto demais: sem os dois CNPJ não se
	pode **afirmar** que é transferência, e a resposta segura é a que tributa. Degradar para
	"venda" mantém o comportamento anterior do app; degradar para "transferência" faria o
	imposto sumir por falta de cadastro.

	Aceita CNPJ alfanumérico: `limpar` preserva letras.
	"""
	raiz_origem = limpar(cnpj_origem)[:TAMANHO_DA_RAIZ]
	raiz_destino = limpar(cnpj_destino)[:TAMANHO_DA_RAIZ]

	if len(raiz_origem) < TAMANHO_DA_RAIZ or len(raiz_destino) < TAMANHO_DA_RAIZ:
		return False

	return raiz_origem == raiz_destino
