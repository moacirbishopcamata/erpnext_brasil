# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Leitura de etiqueta GS1 — o código que carrega GTIN, lote, validade e série num só bipe.

Por que existe
--------------
O `erpnext.stock.utils.scan_barcode` busca o valor **inteiro** que foi lido em quatro
cadastros (`Item Barcode`, `Serial No`, `Batch`, `Warehouse`). Isso funciona para um EAN-13
simples e **falha em silêncio** para uma etiqueta GS1-128, que não é um identificador: é uma
*cadeia de elementos*, vários dados concatenados. Nenhum cadastro tem aquele texto inteiro,
e o estoquista vê "não encontrado" sem saber por quê.

E é justamente a etiqueta GS1 que carrega o que a NF-e precisa: `nLote`, `dFab` e `dVal` do
grupo `rastro` estão **na etiqueta**, impressas pelo fabricante. Sem ler, o operador
redigita — e redigitação de lote é onde a rastreabilidade se perde.

Como a cadeia se lê (GS1 General Specifications)
-------------------------------------------------------
Cada elemento começa com um **Application Identifier** (AI) de 2 a 4 dígitos, seguido do
dado. O problema é saber onde um elemento termina, e a resposta tem duas metades:

1. **AI de comprimento predefinido** — o dado tem tamanho fixo e o próximo elemento começa
   logo em seguida, sem separador. São os marcados com `*` no dicionário oficial.
2. **AI de comprimento variável** — o dado vai até um separador **FNC1**, que na
   transmissão do leitor chega como o caractere **GS (ASCII 29, `\\x1d`)**, ou até o fim da
   cadeia se for o último elemento.

⚠️ **Confundir as duas metades produz lixo plausível, não erro.** Um leitor que trate `01`
como variável engoliria o lote junto do GTIN; um que trate `10` como fixo cortaria o lote no
meio. Os dois devolvem string, e nenhum reclama.

Fonte: **GS1 Barcode Syntax Dictionary**, publicado pela GS1 AISBL, baixado e lido
localmente. A tabela abaixo é transcrição dele, não memória:

```
00  *  N18    SSCC          01  *  N14    GTIN        02  *  N14  CONTENT
10     X..20  BATCH/LOT     11  *  N6     PROD DATE   13   *  N6   PACK DATE
15  *  N6     BEST BEFORE   17  *  N6     USE BY      21      X..20  SERIAL
30     N..8   VAR. COUNT    37     N..8   COUNT
```

O `*` é literalmente o sinal do dicionário para *"Pre-defined length AI not requiring FNC1
separator"*.

⚠️ O dia `00`, e por que se lê como último dia do mês
--------------------------------------------------------------
O linter das datas no dicionário oficial chama-se **`yymmd0`** — o `0` final não é enfeite:
significa que o **dia pode vir `00`**, indicando que o fabricante não quis especificar o
dia.

Este módulo resolve `00` para o **último dia do mês**, e a escolha tem um lado seguro: numa
data de validade, ler `250600` como 1º/06 venceria o produto trinta dias antes da hora — e
descartar mercadoria boa é o erro caro. O último dia é a leitura conservadora.

📌 **Fonte a reconferir:** a GS1 publicou o GSCN 21-040 encerrando o uso de `00` para
produtos de saúde regulados a partir de janeiro de 2025. O texto do GSCN **não pôde ser
lido** (o servidor da GS1 devolve 403 para download direto), então a data-limite e o escopo
exato estão registrados de segunda mão. Etiquetas legadas com `00` continuam em circulação
de qualquer forma, e é por isso que aceitá-las não é opcional.

O que **não** está aqui, declarado
-----------------------------------------
- **Dígito verificador do GTIN.** `fiscal/validators.py` já faz módulo 10 para EAN; validar
  de novo aqui criaria duas verdades sobre o mesmo dígito.
- **AI que este app não usa** — peso, dimensão, preço, destino. O dicionário tem mais de 100;
  transcrever todos sem uso seria carregar tabela que ninguém verifica.
- **Componente composto (CC-A/CC-B) como símbolo.** O *composite component* é uma questão de
  **simbologia**: o leitor entrega o conteúdo dele concatenado à cadeia do símbolo linear,
  com os mesmos AI. Do lado do dado — que é o lado deste módulo — não há diferença, e é por
  isso que ler composto não exige código a mais.

Funções puras: nenhuma dependência do Frappe.
"""

import calendar
from dataclasses import dataclass
from datetime import date

__all__ = [
	"AI_DE_TAMANHO_FIXO",
	"AI_VARIAVEIS",
	"SEPARADOR",
	"EtiquetaGs1",
	"Gs1Invalido",
	"ler_gs1",
	"parece_gs1",
]

SEPARADOR = "\x1d"
"""O FNC1 como o leitor o transmite: **GS, ASCII 29**.

Alguns leitores são configurados para mandar outro caractere no lugar. Normalizar isso é
configuração de equipamento, não de software — inventar um segundo separador aqui aceitaria
etiqueta malformada como se fosse boa.
"""

AI_DE_TAMANHO_FIXO = {
	"00": 18,  # SSCC
	"01": 14,  # GTIN
	"02": 14,  # CONTENT — GTIN dos itens contidos
	"11": 6,  # PROD DATE
	"13": 6,  # PACK DATE
	"15": 6,  # BEST BEFORE
	"17": 6,  # USE BY / EXPIRY
}
"""AI marcados com `*` no dicionário GS1: comprimento predefinido, **sem** separador.

O valor é o tamanho do **dado**, sem o AI.
"""

AI_VARIAVEIS = {
	"10": 20,  # BATCH/LOT
	"21": 20,  # SERIAL
	"30": 8,  # VAR. COUNT
	"37": 8,  # COUNT
}
"""AI de comprimento variável, e o **máximo** que o dicionário admite para cada um.

O máximo não delimita o campo — quem delimita é o separador. Serve para recusar uma cadeia
malformada em que o separador faltou, em vez de engolir o resto da etiqueta como se fosse
lote.
"""

_PREFIXOS_DE_SIMBOLOGIA = ("]C1", "]e0", "]d2", "]Q3", "]J1")
"""Identificadores de simbologia que alguns leitores antepõem à cadeia.

`]C1` é GS1-128; `]e0`, GS1 DataBar; `]d2`, GS1 DataMatrix; `]Q3`, GS1 QR. Não fazem parte
do dado — deixá-los passar faria o primeiro AI ser lido como `]C`.
"""


class Gs1Invalido(ValueError):
	"""Cadeia que não é uma etiqueta GS1 legível."""


@dataclass(frozen=True)
class EtiquetaGs1:
	"""O que uma etiqueta carrega, já separado.

	Todos os campos são opcionais porque a etiqueta é montada pelo fabricante: um item sem
	controle de lote traz só o GTIN, e um palete traz SSCC sem GTIN. Exigir combinação
	recusaria etiqueta válida.
	"""

	gtin: str | None = None
	lote: str | None = None
	serie: str | None = None
	fabricacao: date | None = None
	validade: date | None = None
	quantidade: int | None = None
	sscc: str | None = None
	elementos: dict[str, str] = None  # type: ignore[assignment]

	@property
	def gtin_sem_enchimento(self) -> str | None:
		"""O GTIN sem os zeros de preenchimento à esquerda.

		⚠️ **É o que faz a busca no `Item Barcode` funcionar.** O AI (01) é sempre GTIN-14,
		com zeros à esquerda; o cadastro do item quase sempre guarda o EAN-13 impresso na
		caixa. Procurar os 14 dígitos crus não acha nada, e o estoquista conclui que o item
		não está cadastrado.
		"""
		if not self.gtin:
			return None

		return self.gtin.lstrip("0") or "0"


def parece_gs1(codigo: str) -> bool:
	"""A cadeia tem cara de etiqueta GS1?

	Serve para decidir **se vale tentar** — um EAN-13 solto não é GS1 e deve seguir pelo
	caminho normal do ERPNext. Conservador de propósito: prefere devolver `False` e deixar o
	caminho antigo funcionar a assumir GS1 e falhar num código simples.
	"""
	if not codigo:
		return False

	limpo = _sem_prefixo_de_simbologia(codigo.strip())

	if SEPARADOR in limpo:
		return True

	# Um EAN-13/GTIN-14 puro tem 13 ou 14 dígitos e nenhum AI antes.
	if limpo.isdigit() and len(limpo) in (8, 12, 13, 14):
		return False

	return limpo[:2] in AI_DE_TAMANHO_FIXO or limpo[:2] in AI_VARIAVEIS


def _sem_prefixo_de_simbologia(codigo: str) -> str:
	for prefixo in _PREFIXOS_DE_SIMBOLOGIA:
		if codigo.startswith(prefixo):
			return codigo[len(prefixo) :]

	return codigo


def _data_gs1(bruto: str) -> date:
	"""`YYMMDD` para `date`, com o dia `00` virando o último dia do mês.

	O século vem da janela da especificação: o ano de dois dígitos é lido no intervalo de
	-50 a +49 anos em torno do ano corrente. Fixar "20xx" quebraria em 2050.
	"""
	if len(bruto) != 6 or not bruto.isdigit():
		raise Gs1Invalido(f"data GS1 deve ter 6 dígitos (YYMMDD), recebido {bruto!r}")

	ano_curto, mes, dia = int(bruto[:2]), int(bruto[2:4]), int(bruto[4:])

	if not 1 <= mes <= 12:
		raise Gs1Invalido(f"mês inválido em {bruto!r}")

	seculo = date.today().year // 100 * 100
	ano = seculo + ano_curto

	if ano - date.today().year >= 50:
		ano -= 100
	elif date.today().year - ano > 50:
		ano += 100

	ultimo = calendar.monthrange(ano, mes)[1]

	if dia == 0:
		return date(ano, mes, ultimo)

	if dia > ultimo:
		raise Gs1Invalido(f"dia {dia} não existe no mês {mes}/{ano}")

	return date(ano, mes, dia)


def _proximo_ai(cadeia: str) -> str:
	ai = cadeia[:2]

	if ai not in AI_DE_TAMANHO_FIXO and ai not in AI_VARIAVEIS:
		raise Gs1Invalido(
			f"AI {ai!r} não é tratado por este módulo — a etiqueta pode ser válida e trazer um "
			"identificador que o app não usa; ver a lista declarada na docstring"
		)

	return ai


def ler_gs1(codigo: str) -> EtiquetaGs1:
	"""Separa a cadeia de elementos numa `EtiquetaGs1`.

	Levanta `Gs1Invalido` para cadeia malformada — **nunca** devolve um resultado parcial
	calado: lote cortado ao meio é pior que leitura recusada, porque entra no estoque e
	depois na nota.
	"""
	if not codigo or not codigo.strip():
		raise Gs1Invalido("cadeia vazia")

	cadeia = _sem_prefixo_de_simbologia(codigo.strip())
	elementos: dict[str, str] = {}

	while cadeia:
		ai = _proximo_ai(cadeia)
		resto = cadeia[2:]

		if ai in AI_DE_TAMANHO_FIXO:
			tamanho = AI_DE_TAMANHO_FIXO[ai]

			if len(resto) < tamanho:
				raise Gs1Invalido(
					f"AI {ai} exige {tamanho} caracteres e a cadeia tem {len(resto)} — etiqueta truncada"
				)

			valor, cadeia = resto[:tamanho], resto[tamanho:]

			# Um separador logo depois de um AI fixo é redundante, mas leitores o emitem.
			cadeia = cadeia.removeprefix(SEPARADOR)
		else:
			valor, _, cadeia = resto.partition(SEPARADOR)

			if len(valor) > AI_VARIAVEIS[ai]:
				raise Gs1Invalido(
					f"AI {ai} admite no máximo {AI_VARIAVEIS[ai]} caracteres e veio com "
					f"{len(valor)} — provável separador FNC1 ausente entre os elementos"
				)

		if not valor:
			raise Gs1Invalido(f"AI {ai} veio sem dado")

		if ai in elementos:
			raise Gs1Invalido(f"AI {ai} repetido na mesma etiqueta")

		elementos[ai] = valor

	if not elementos:
		raise Gs1Invalido("nenhum elemento reconhecido")

	return EtiquetaGs1(
		gtin=elementos.get("01") or elementos.get("02"),
		lote=elementos.get("10"),
		serie=elementos.get("21"),
		fabricacao=_data_gs1(elementos["11"]) if "11" in elementos else None,
		validade=_data_gs1(elementos["17"]) if "17" in elementos else None,
		quantidade=int(elementos["30"]) if "30" in elementos else None,
		sscc=elementos.get("00"),
		elementos=elementos,
	)
