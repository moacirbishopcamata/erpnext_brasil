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

O algoritmo do QR Code — on-line e contingência offline
------------------------------------------------------------
Cobertos os dois casos: **emissão on-line** (`tpEmis` diferente de `9`, majoritário) e
**contingência offline** (`tpEmis = 9`) — usada quando o emitente não consegue contato
com a SEFAZ no momento da venda e autoriza depois.

**Contingência offline desatualizada desde 01/09/2025** (NT 2025.001): a partir dessa
data, a SEFAZ passou a exigir QR Code "versão 3" (assinatura criptográfica, sem CSC)
especificamente para esse cenário — `montar_qrcode_offline` ainda implementa a versão 2
(hash com CSC), porque o algoritmo de assinatura da versão 3 não foi confirmado em
nenhuma fonte acessível até agora (ver o aviso na docstring da função e `docs/
nfce-qrcode.md`). Emissão on-line não é afetada pela NT — `montar_qrcode_online`
continua vigente sem ressalva.

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

A sequência da contingência offline (`chave|versão|ambiente|dia|valor|digHex|cscId`,
mesmo hash SHA-1+CSC) veio da mesma leitura do código-fonte. A pegadinha de
`digHex`: **não** é o digest decodificado — é a string base64 do `DigestValue`
(exatamente como aparece no XML da assinatura) com **cada caractere ASCII** convertido
para 2 dígitos hexadecimais (`str2Hex`, lido literalmente: `sprintf("%02x", ord($c))`
por caractere). Decodificar o base64 antes produziria um `digHex` diferente e o hash não
bateria com o que a SEFAZ calcula — exatamente o tipo de detalhe que só aparece lendo o
código-fonte, não a descrição em prosa.

O que fica de fora, declarado
----------------------------------
- **Tabela de URL de consulta por UF** (`webConsultaNFCe`): resolvida à parte, em
  `consulta_nfce.py` — este módulo continua recebendo a URL base já pronta de quem
  chama, não a deriva sozinho.
- **QR Code "versão 3" (NT 2025.001)**: uma atualização recente troca o esquema de
  contingência específico para assinatura criptográfica em vez de hash com CSC — fora do
  escopo desta implementação (só a versão 2, vigente e majoritária).

Funções puras: nenhuma dependência do Frappe.
"""

import hashlib
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from erpnext_brasil.fiscal.documento.chave_acesso import validar_chave
from erpnext_brasil.fiscal.documento.serializacao import Cdata

__all__ = [
	"QRCODE_MINIMO",
	"URLCHAVE_MINIMO",
	"VERSAO_QRCODE",
	"QRCodeInvalido",
	"montar_infnfesupl",
	"montar_qrcode_offline",
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


def _validar_comuns(ambiente: str, csc_id: str, csc: str, url_base: str) -> tuple[str, str]:
	if ambiente not in ("1", "2"):
		raise QRCodeInvalido(f"ambiente deve ser '1' ou '2', recebido {ambiente!r}", "ambiente")

	csc_id_limpo = (csc_id or "").strip().lstrip("0") or "0"

	if not csc_id_limpo.isdigit():
		raise QRCodeInvalido(f"csc_id deve ser numérico, recebido {csc_id!r}", "csc_id")

	if not (csc or "").strip():
		raise QRCodeInvalido("csc (Código de Segurança do Contribuinte) é obrigatório", "csc")

	if not (url_base or "").strip():
		raise QRCodeInvalido("url_base é obrigatória", "url_base")

	return csc_id_limpo, url_base.strip()


def _montar_url(sequencia: str, csc: str, url_base: str) -> str:
	hash_qrcode = hashlib.sha1((sequencia + csc).encode("utf-8")).hexdigest().upper()

	# Pós-condição: SHA-1 em hex é sempre 40 caracteres. Falhar aqui, alto e cedo, é
	# melhor que devolver um QR Code cujo hash a SEFAZ vai rejeitar sem dizer por quê —
	# se isto um dia disparar, é hashlib se comportando diferente do esperado, não dado
	# de entrada, porque a validação de entrada já aconteceu em `_validar_comuns`.
	assert len(hash_qrcode) == 40, f"hash SHA-1 com tamanho inesperado: {len(hash_qrcode)}"

	# Mesma regra da fonte de referência: só acrescenta "?p=" se a URL ainda não o tiver
	# — não tenta ser mais esperta que isso (ex. detectar "?" de outros parâmetros).
	base = url_base if "?p=" in url_base else f"{url_base}?p="

	return f"{base}{sequencia}|{hash_qrcode}"


def montar_qrcode_online(chave_acesso: str, ambiente: str, csc_id: str, csc: str, url_base: str) -> str:
	"""Monta a URL completa do QR Code para emissão on-line (`tpEmis` != 9).

	`ambiente` é `"1"` (produção) ou `"2"` (homologação) — mesma convenção de `tpAmb` no
	resto do app. `csc_id` entra sem zero à esquerda (confirmado na fonte — ver docstring
	do módulo), mesmo que o cadastro na SEFAZ mostre com zeros. `csc` nunca aparece na URL
	final — só participa do hash, exatamente como o Código de Segurança do Contribuinte
	deve funcionar (segredo compartilhado, não dado público).
	"""
	chave = validar_chave(chave_acesso)
	csc_id_limpo, base = _validar_comuns(ambiente, csc_id, csc, url_base)

	sequencia = f"{chave}|{VERSAO_QRCODE}|{ambiente}|{csc_id_limpo}"

	return _montar_url(sequencia, csc, base)


def montar_qrcode_offline(
	chave_acesso: str,
	ambiente: str,
	csc_id: str,
	csc: str,
	url_base: str,
	data_emissao: datetime,
	valor_total: Decimal,
	digest_value: str,
) -> str:
	"""Monta a URL completa do QR Code para emissão em contingência offline
	(`tpEmis = 9`) — usada quando o emitente não consegue contato com a SEFAZ no
	momento da venda.

	**ATENÇÃO — desatualizada para uso real desde 01/09/2025.** Esta função implementa
	o QR Code "versão 2" (hash com CSC). A Nota Técnica 2025.001 tornou obrigatória, a
	partir dessa data, a "versão 3" (assinatura criptográfica) especificamente para
	contingência offline — o CSC deixou de valer nesse cenário. **Não implementado
	ainda**: não foi possível confirmar o algoritmo exato de assinatura em nenhuma fonte
	acessível (a oficial, `nfe.fazenda.gov.br`, está inacessível às ferramentas de busca)
	— ver `docs/nfce-qrcode.md`, seção "Ainda por implementar", para o registro completo
	do bloqueio. Usar esta função para uma contingência offline real hoje produz um QR
	Code que a SEFAZ pode não aceitar mais; para emissão normal (`montar_qrcode_online`),
	a versão 2 continua vigente e não é afetada.

	`digest_value` é a string base64 do `DigestValue` **exatamente como está no XML**
	assinado — este módulo converte cada caractere ASCII dela para hex (`digHex`), não
	decodifica o base64 primeiro. Ver a pegadinha explicada na docstring do módulo:
	inverter essa ordem produz um hash que não bate com o que a SEFAZ calcula.
	"""
	chave = validar_chave(chave_acesso)
	csc_id_limpo, base = _validar_comuns(ambiente, csc_id, csc, url_base)

	if not (digest_value or "").strip():
		raise QRCodeInvalido("digest_value é obrigatório", "digest_value")

	dia = f"{data_emissao.day:02d}"
	valor = str(Decimal(valor_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
	dig_hex = "".join(f"{ord(caractere):02x}" for caractere in digest_value.strip())

	sequencia = f"{chave}|{VERSAO_QRCODE}|{ambiente}|{dia}|{valor}|{dig_hex}|{csc_id_limpo}"

	return _montar_url(sequencia, csc, base)


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

	grupo = {"infNFeSupl": {"qrCode": Cdata(url_qrcode), "urlChave": url_chave}}

	# Pós-condição: a ordem exigida pelo XSD (qrCode antes de urlChave) não é um
	# acidente de como o dict foi escrito acima — checar de propósito.
	assert list(grupo["infNFeSupl"]) == ["qrCode", "urlChave"], "ordem de infNFeSupl trocada"

	return grupo


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

	# Pós-condição: infNFeSupl sempre existe no resultado, e nunca depois de Signature —
	# se Signature está presente, a ordem de inserção do dict (que decide a ordem no XML)
	# tem que refletir isso, não só "o grupo foi anexado em algum lugar".
	chaves = list(novo)
	assert "infNFeSupl" in chaves, "infNFeSupl não foi anexado"
	if "Signature" in chaves:
		assert chaves.index("infNFeSupl") < chaves.index("Signature"), (
			"infNFeSupl precisa vir antes de Signature na árvore"
		)

	return {"NFe": novo}
