# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""QR Code da NFC-e (modelo 65) — grupo `infNFeSupl`.

Por que é um módulo à parte
------------------------------
`infNFeSupl` é informação suplementar do documento — não afeta a assinatura digital
(entra na árvore *depois* de assinar `infNFe`) e só existe para NFC-e, nunca para NF-e
(modelo 55). Confirmado na estrutura do grupo: `infNFeSupl` tem só dois campos,
`qrCode` (a URL completa impressa no DANFCe, com no mínimo 100 caracteres) e `urlChave`
(a URL de consulta pela chave, no mínimo 21 caracteres) — e fica entre `</infNFe>` e
`<Signature>` na árvore de `NFe`.

O algoritmo do QR Code (confirmado, com ressalva de escopo)
-----------------------------------------------------------------
Só a **emissão on-line** (`tpEmis` diferente de `9`) está implementada aqui — é o caso
majoritário. A emissão em contingência offline (`tpEmis = 9`) usa uma sequência diferente
(dia da emissão, valor total, hash do digest em vez do digest inteiro) e fica como
trabalho futuro declarado, não escondido.

Para o caso on-line, o algoritmo foi confirmado em duas fontes independentes que batem
exatamente:

1. **Código-fonte** de `nfephp-org/sped-nfe` (`src/Factories/QRCode.php`, método
   `get200()`), lido diretamente: `$ver = $versao / 100` (com `$versao=200`, dá `2`, não
   `"2.00"` — divisão inteira do PHP quando o resultado é exato); `$cscId = (int)$idToken`
   (sem zero à esquerda); a sequência é `"{chave}|{ver}|{tpAmb}|{cscId}"`, o hash é
   `SHA-1(sequência + CSC)` em **hexadecimal maiúsculo**, e a URL final é
   `{base}?p={sequência}|{hash}`.
2. **Um exemplo real publicado** (ambiente de produção): `.../nfce/qrcode?p=
   28170800156225000131650110000151341562040824|2|1|1|DC6AE2C2B9A992BE59679AC365E29922DE6B7511`
   — bate campo a campo com o algoritmo do código-fonte: `2` (versão, não `2.00`), `1`
   (ambiente produção), `1` (`cscId` sem zero à esquerda, confirmado explicitamente por
   fonte separada: "identificador CSC... sem os zeros não significativos"), hash de 40
   caracteres hexadecimais maiúsculos.

Essa dupla confirmação é o padrão de verificação deste app quando o Portal Nacional da
NF-e está inacessível às ferramentas de busca (como aconteceu aqui) — nunca uma fonte
secundária isolada.

O que fica de fora, declarado
----------------------------------
- **Emissão em contingência (`tpEmis = 9`)**: sequência diferente, não implementada.
- **Tabela de URL de consulta por UF** (`webConsultaNFCe`): cada UF tem seu próprio
  domínio de consulta pública da NFC-e (distinto dos webservices de autorização já
  mapeados em `autorizadores_sefaz.py`) — este módulo recebe a URL base já pronta de
  quem chama, não a deriva. Levantar essa tabela é trabalho futuro declarado.
- **QR Code "versão 3" (NT 2025.001)**: uma atualização recente troca o esquema de
  contingência específico para assinatura criptográfica em vez de hash com CSC — fora do
  escopo desta primeira implementação (só a versão 2, vigente e majoritária).

Funções puras: nenhuma dependência do Frappe.
"""

import hashlib

from erpnext_brasil.fiscal.documento.chave_acesso import validar_chave
from erpnext_brasil.fiscal.documento.serializacao import Cdata

__all__ = [
	"QRCODE_MINIMO",
	"URLCHAVE_MINIMO",
	"VERSAO_QRCODE",
	"QRCodeInvalido",
	"montar_infnfesupl",
	"montar_qrcode_online",
]

# Confirmado em código-fonte de referência e num exemplo real (ver docstring do módulo):
# a versão embutida na sequência é o inteiro "2", não "2.00".
VERSAO_QRCODE = "2"

QRCODE_MINIMO = 100
URLCHAVE_MINIMO = 21


class QRCodeInvalido(ValueError):
	def __init__(self, mensagem: str, campo: str = ""):
		super().__init__(mensagem)
		self.campo = campo


def montar_qrcode_online(chave_acesso: str, ambiente: str, csc_id: str, csc: str, url_base: str) -> str:
	"""Monta a URL completa do QR Code para emissão on-line (`tpEmis` != 9).

	`ambiente` é `"1"` (produção) ou `"2"` (homologação) — mesma convenção de `tpAmb` no
	resto do app. `csc_id` entra sem zero à esquerda (confirmado na fonte — ver docstring
	do módulo), mesmo que o cadastro na SEFAZ mostre com zeros. `csc` nunca aparece na URL
	final — só participa do hash, exatamente como o Código de Segurança do Contribuinte
	deve funcionar (segredo compartilhado, não dado público).
	"""
	chave = validar_chave(chave_acesso)

	if ambiente not in ("1", "2"):
		raise QRCodeInvalido(f"ambiente deve ser '1' ou '2', recebido {ambiente!r}", "ambiente")

	csc_id_limpo = (csc_id or "").strip().lstrip("0") or "0"

	if not csc_id_limpo.isdigit():
		raise QRCodeInvalido(f"csc_id deve ser numérico, recebido {csc_id!r}", "csc_id")

	if not (csc or "").strip():
		raise QRCodeInvalido("csc (Código de Segurança do Contribuinte) é obrigatório", "csc")

	if not (url_base or "").strip():
		raise QRCodeInvalido("url_base é obrigatória", "url_base")

	sequencia = f"{chave}|{VERSAO_QRCODE}|{ambiente}|{csc_id_limpo}"
	hash_qrcode = hashlib.sha1((sequencia + csc).encode("utf-8")).hexdigest().upper()

	# Mesma regra da fonte de referência: só acrescenta "?p=" se a URL ainda não o tiver
	# — não tenta ser mais esperta que isso (ex. detectar "?" de outros parâmetros).
	base = url_base.strip()
	base = base if "?p=" in base else f"{base}?p="

	return f"{base}{sequencia}|{hash_qrcode}"


def montar_infnfesupl(qrcode_url: str, url_consulta_chave: str) -> dict:
	"""Monta o grupo `infNFeSupl` — `qrCode` (CDATA) seguido de `urlChave`, essa ordem
	confirmada no XSD. Os dois têm tamanho mínimo (100 e 21 caracteres): abaixo disso não
	é uma URL de QR Code/consulta real, é sinal de algo montado errado antes de chegar
	aqui.
	"""
	url_qrcode = (qrcode_url or "").strip()
	url_chave = (url_consulta_chave or "").strip()

	if len(url_qrcode) < QRCODE_MINIMO:
		raise QRCodeInvalido(
			f"qrCode deve ter ao menos {QRCODE_MINIMO} caracteres, recebidos {len(url_qrcode)}",
			"qrcode_url",
		)

	if len(url_chave) < URLCHAVE_MINIMO:
		raise QRCodeInvalido(
			f"urlChave deve ter ao menos {URLCHAVE_MINIMO} caracteres, recebidos {len(url_chave)}",
			"url_consulta_chave",
		)

	return {"infNFeSupl": {"qrCode": Cdata(url_qrcode), "urlChave": url_chave}}


def anexar_infnfesupl(nfe_assinada: dict, inf_nfe_supl: dict) -> dict:
	"""Insere `infNFeSupl` entre `infNFe` e `Signature` na árvore já assinada.

	Não afeta a assinatura — por isso entra depois de assinar, não antes: `infNFeSupl`
	fica fora do que `assinar_nfe` cobre pela `Reference` apontar só para `infNFe`.
	"""
	raiz = nfe_assinada["NFe"]
	novo: dict = {}

	for chave, valor in raiz.items():
		if chave == "Signature":
			novo["infNFeSupl"] = inf_nfe_supl["infNFeSupl"]

		novo[chave] = valor

	if "infNFeSupl" not in novo:
		# Signature não estava presente (uso incomum, mas não impede a montagem).
		novo["infNFeSupl"] = inf_nfe_supl["infNFeSupl"]

	return {"NFe": novo}
