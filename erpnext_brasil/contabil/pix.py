# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Pix: payload BR Code ("Pix Copia e Cola"), TLV + CRC16.

Por que existe
--------------
`payments` (o app de gateways de pagamento do ecossistema Frappe) tem PayPal,
Stripe, Razorpay, Braintree, Mpesa, Paytm, Paymob, GoCardless — **nenhum Pix**
(conferido no código-fonte do app, não suposto). Este módulo cobre a parte que é
matemática pura, sem rede: montar a string de "Pix Copia e Cola"/QR Code estático
que qualquer app de pagamento pode gerar sem precisar de credencial de banco nem
API de PSP — mesma categoria de `boleto.py` (código de barras/linha digitável são
cálculo puro; registrar o título no banco é integração à parte, não coberta aqui).

O padrão é EMV® QRCPS-MPM, "tropicalizado" pelo Banco Central (BR Code)
------------------------------------------------------------------------------------------
Estrutura TLV (Tag-Length-Value): cada campo é `<ID de 2 dígitos><tamanho de 2
dígitos><valor>`. O Pix usa esse padrão internacional (EMVCo) com campos
específicos do Banco Central — o "Manual de Padrões para Iniciação do Pix"
(`bcb.gov.br`) é a fonte primária, mas o PDF publicado é digitalizado/comprimido
de um jeito que as ferramentas de busca não conseguiram extrair nesta rodada
(mesma limitação já vista repetidas vezes neste projeto para fontes `gov.br`
grandes) — os campos abaixo vêm de busca agregada e de um projeto open-source de
geração de QR Code Pix, cruzados entre si, não da leitura direta do manual oficial.

CRC16: confirmado contra o vetor de teste padrão universal, não contra um exemplo isolado
------------------------------------------------------------------------------------------------------
O algoritmo é CRC-16/CCITT-FALSE (polinômio `0x1021`, valor inicial `0xFFFF`, sem
XOR final). Uma primeira tentativa de validar contra um payload de exemplo
completo (de um artigo de terceiro) **não bateu** — o CRC do artigo não confere
com o cálculo, sinal de erro de transcrição na fonte, não no algoritmo. Verificado
em vez disso contra o **vetor de teste padrão universal desta variante de CRC**
(`CRC16-CCITT-FALSE("123456789") == 0x29B1`), citado por praticamente toda
implementação de referência da família CRC-16 — uma fonte mais forte que um
exemplo isolado de blog, porque não depende de nenhuma fonte específica de Pix
ter transcrito certo.

Campos cobertos, e o que fica de fora
------------------------------------------
Cobertos: `00` (Payload Format Indicator, fixo), `01` (Point of Initiation Method
— estático `11`/dinâmico `12`), `26` (Merchant Account Information: GUI +
chave Pix), `52` (Merchant Category Code, fixo `0000` — não classificado), `53`
(Transaction Currency, fixo `986` = BRL), `54` (Transaction Amount, opcional —
Pix sem valor fixo omite o campo), `58` (Country Code, fixo `BR`), `59`
(Merchant Name, até 25 caracteres), `60` (Merchant City, até 15 caracteres), `62`
(Additional Data Field Template — só o `txid`), `63` (CRC16).

**Fora de escopo, deliberadamente**: Pix dinâmico com endpoint de cobrança
(subcampo `25` de `62`, que aponta para uma API — exige backend de PSP, não é
cálculo puro), QR Code como imagem (só a string do payload, não o desenho do
QR — geração de imagem é biblioteca externa, fora do padrão deste projeto de não
introduzir dependência nova sem necessidade), validação de chave Pix contra o
DICT (Diretório de Identificadores de Contas Transacionais — exige consulta ao
Banco Central em tempo real, não é cálculo local).

Sanitização de texto: só ASCII, sem acento
------------------------------------------------
O padrão EMV MPM exige texto sem acentuação nos campos de nome/cidade — este
módulo remove diacríticos (`á`→`a`) via normalização Unicode antes de truncar no
tamanho máximo do campo, para não gerar um payload que a maioria dos leitores de
QR Code Pix rejeitaria silenciosamente.

Funções puras: nenhuma dependência do Frappe, nenhuma chamada de rede.
"""

import unicodedata
from decimal import Decimal

__all__ = [
	"CODIGO_PAIS",
	"GUI_PIX",
	"MOEDA_REAL",
	"PONTO_INICIACAO_DINAMICO",
	"PONTO_INICIACAO_ESTATICO",
	"PixInvalido",
	"montar_payload",
]

GUI_PIX = "br.gov.bcb.pix"
MOEDA_REAL = "986"
CODIGO_PAIS = "BR"

PONTO_INICIACAO_ESTATICO = "11"
PONTO_INICIACAO_DINAMICO = "12"

_TAMANHO_MAXIMO_NOME = 25
_TAMANHO_MAXIMO_CIDADE = 15
_TAMANHO_MAXIMO_TXID = 25
_TXID_PADRAO = "***"  # usado quando não há txid — confirmado pela fonte agregada.


class PixInvalido(ValueError):
	"""Dado que impede a montagem do payload."""


def _tlv(id_campo: str, valor: str) -> str:
	return f"{id_campo}{len(valor):02d}{valor}"


def _sanitizar(texto: str, tamanho_maximo: int, campo: str) -> str:
	"""Remove diacríticos (o padrão EMV MPM só aceita ASCII) e trunca."""
	if not texto or not texto.strip():
		raise PixInvalido(f"{campo} não pode ser vazio")

	sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")

	return sem_acento.strip()[:tamanho_maximo]


def _crc16_ccitt_false(dados: bytes) -> str:
	"""CRC-16/CCITT-FALSE — polinômio `0x1021`, inicial `0xFFFF`, sem XOR final.
	Confirmado contra o vetor de teste padrão da variante (ver docstring do
	módulo), não contra um payload Pix de exemplo isolado."""
	crc = 0xFFFF

	for byte in dados:
		crc ^= byte << 8

		for _ in range(8):
			if crc & 0x8000:
				crc = ((crc << 1) ^ 0x1021) & 0xFFFF
			else:
				crc = (crc << 1) & 0xFFFF

	return format(crc, "04X")


def montar_payload(
	chave_pix: str,
	nome_recebedor: str,
	cidade_recebedor: str,
	valor: Decimal | None = None,
	txid: str = _TXID_PADRAO,
	dinamico: bool = False,
) -> str:
	"""Monta o payload Pix ("Copia e Cola") — a mesma string que um QR Code Pix
	estático codifica.

	`chave_pix` não é validada quanto ao formato (CPF/CNPJ/e-mail/telefone/chave
	aleatória são formatos muito diferentes entre si, e a validação de CPF/CNPJ já
	existe em `fiscal/validators` — reaproveitar aqui exigiria decidir qual dos
	cinco formatos está sendo passado, decisão de quem chama, não deste módulo).
	`valor`, quando informado, é `Decimal` (convenção deste projeto) e vira texto
	com ponto decimal (não vírgula) — formato exigido pelo campo `54`, diferente
	do resto do bloco contábil brasileiro (que usa vírgula no SPED).
	"""
	if valor is not None and valor <= Decimal("0"):
		raise PixInvalido(f"valor, quando informado, deve ser maior que zero, recebido {valor}")

	if not chave_pix or not chave_pix.strip():
		raise PixInvalido("chave_pix não pode ser vazia")

	nome = _sanitizar(nome_recebedor, _TAMANHO_MAXIMO_NOME, "nome_recebedor")
	cidade = _sanitizar(cidade_recebedor, _TAMANHO_MAXIMO_CIDADE, "cidade_recebedor")
	txid_limpo = (txid or _TXID_PADRAO).strip()[:_TAMANHO_MAXIMO_TXID]

	conta = _tlv("00", GUI_PIX) + _tlv("01", chave_pix.strip())

	campos = [
		_tlv("00", "01"),
		_tlv("01", PONTO_INICIACAO_DINAMICO if dinamico else PONTO_INICIACAO_ESTATICO),
		_tlv("26", conta),
		_tlv("52", "0000"),
		_tlv("53", MOEDA_REAL),
	]

	if valor is not None:
		campos.append(_tlv("54", str(valor.quantize(Decimal("0.01")))))

	campos += [
		_tlv("58", CODIGO_PAIS),
		_tlv("59", nome),
		_tlv("60", cidade),
		_tlv("62", _tlv("05", txid_limpo)),
	]

	payload_sem_crc = "".join(campos) + "6304"
	crc = _crc16_ccitt_false(payload_sem_crc.encode("utf-8"))

	return payload_sem_crc + crc
