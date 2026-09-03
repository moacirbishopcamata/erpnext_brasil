# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Extrai a chave de acesso do que um leitor de código de barras entrega.

Por que existe: 1D e 2D entregam coisas diferentes
----------------------------------------------------------
Leitores de código de barras são, quase sempre, dispositivos HID — "digitam" o que
leram e dão Enter. O que eles digitam, porém, **não é o mesmo** dependendo do documento:

| Documento | Código impresso | O que chega no campo |
|---|---|---|
| DANFE (NF-e), DACTE (CT-e), DAMDFE (MDF-e) | 1D, Code128C | os 44 dígitos da chave |
| DANFCe (NFC-e) | 2D, QR Code | uma **URL inteira**, com a chave no meio |

Sem esta função, escanear o cupom de uma NFC-e num campo de chave de acesso cola a URL
completa e a validação recusa — o usuário conclui, erradamente, que "o leitor 2D não
funciona". O leitor funciona; é o conteúdo do QR Code que não é a chave, e sim uma URL
de consulta pública (`docs/nfce-qrcode.md`).

O formato do QR Code, e por que a chave é sempre o primeiro pedaço
--------------------------------------------------------------------------
O QR Code da NFC-e é `{url_base}?p={sequência}|{hash}`, e a sequência começa **sempre**
pela chave, nas duas variantes que o layout define:

- on-line: `chave|versão|ambiente|cscId`
- contingência off-line: `chave|versão|ambiente|dia|valor|digest|cscId`

Por isso esta função corta no primeiro `|` em vez de contar campos: a posição da chave é
estável, a quantidade de campos depois dela não. Se a contingência ganhar mais um campo
amanhã, isto continua certo.

O que **não** se faz aqui: adivinhar
-------------------------------------------
Texto que não é uma URL reconhecível nem 44 dígitos levanta erro, em vez de tentar
"achar 44 dígitos em qualquer lugar do texto". Um código de barras de produto (EAN-13),
lido por engano num campo de chave de acesso, tem de falhar alto — não ser silenciosamente
interpretado como um pedaço de chave.

A chave extraída passa por `validar_chave` (layout e dígito verificador), a mesma
validação de toda a família NF-e/CT-e/MDF-e — extrair não é confiar.

Funções puras: nenhuma dependência do Frappe.
"""

from urllib.parse import parse_qs, unquote, urlparse

from erpnext_brasil.fiscal.documento.chave_acesso import ChaveInvalida, validar_chave

__all__ = ["LeituraInvalida", "extrair_chave"]

TAMANHO_DA_CHAVE = 44

_PARAMETRO_QRCODE = "p"
"""Nome do parâmetro que carrega a sequência no QR Code da NFC-e — `?p=...`."""


class LeituraInvalida(ValueError):
	"""O texto lido não contém uma chave de acesso reconhecível."""


def _parece_url(texto: str) -> bool:
	return texto.lower().startswith(("http://", "https://")) or f"?{_PARAMETRO_QRCODE}=" in texto


def _chave_da_url(texto: str) -> str:
	"""Extrai a chave do QR Code: o parâmetro `p`, até o primeiro `|`.

	Trata `|` codificado como `%7C` — alguns leitores entregam a URL já
	percent-encoded, e cortar antes de decodificar acharia o separador errado.
	"""
	consulta = parse_qs(urlparse(texto).query)
	valores = consulta.get(_PARAMETRO_QRCODE)

	if not valores:
		# Sem query string reconhecível (ex.: o leitor entregou só o conteúdo do `p`,
		# sem o `?p=`): tenta o texto inteiro, que ainda pode ser a sequência.
		bruto = texto
	else:
		bruto = valores[0]

	sequencia = unquote(bruto)

	if f"?{_PARAMETRO_QRCODE}=" in sequencia:
		sequencia = sequencia.split(f"?{_PARAMETRO_QRCODE}=", 1)[1]

	return sequencia.split("|", 1)[0].strip()


def extrair_chave(leitura: str) -> str:
	"""Devolve a chave de acesso de 44 dígitos a partir do texto lido.

	    Aceita as três formas que aparecem na prática:

	1. os 44 dígitos crus (leitor 1D no DANFE/DACTE/DAMDFE);
	    2. a chave formatada com espaços, como é impressa por extenso no DANFE
	       (`3526 0111 2223 ...`) — copiada e colada à mão;
	    3. a URL inteira do QR Code da NFC-e (leitor 2D no DANFCe).

	    Sempre valida o resultado (layout e dígito verificador) antes de devolver.
	"""
	texto = (leitura or "").strip()

	if not texto:
		raise LeituraInvalida("nada foi lido — o campo está vazio")

	candidato = _chave_da_url(texto) if _parece_url(texto) else texto

	# Só depois de isolar o candidato é que se removem separadores: fazer isso antes
	# transformaria a URL inteira num amontoado de dígitos com a chave perdida no meio.
	digitos = "".join(caractere for caractere in candidato if caractere.isdigit())

	if len(digitos) != TAMANHO_DA_CHAVE:
		raise LeituraInvalida(
			f"a leitura não contém uma chave de {TAMANHO_DA_CHAVE} dígitos "
			f"(encontrados {len(digitos)}) — confira se o código lido é o do documento "
			"fiscal, e não um código de barras de produto"
		)

	try:
		return validar_chave(digitos)
	except ChaveInvalida as e:
		raise LeituraInvalida(f"a leitura tem 44 dígitos, mas não é uma chave válida: {e}") from e
