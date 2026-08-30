# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Assinatura digital do XML do eSocial — o perfil XMLDSig que o sistema exige.

Estrutura da assinatura, não a criptografia: mesma separação de
`fiscal/documento/assinatura.py` para a NF-e — as funções puras (testáveis sem
nenhuma biblioteca) ficam aqui; a criptografia fica atrás da porta `Assinador`, com
implementação em `integracao/assinador_esocial.py`.

O perfil do eSocial não é o perfil da NF-e — mesma canonicalização, hash diferente
------------------------------------------------------------------------------------------
Confirmado ao comparar contra `fiscal/documento/assinatura.py` (o perfil da NF-e) e
uma fonte de terceiro especializada em assinatura de eSocial
(`suporte.quarta.com.br/eSocial/AssinaturaXml.htm`):

- **Canonicalização**: a mesma — C14N 1.0 sem comentários, **não** exclusive C14N
  (a fonte é explícita: "o eSocial requer a transformação C14N", não Exclusive C14N).
  Mesma URI (`http://www.w3.org/TR/2001/REC-xml-c14n-20010315`), mesmo `exclusive=False`
  em `lxml.etree.tostring(..., method="c14n", exclusive=False)`.
- **Digest e assinatura**: **diferentes** — SHA-256, não SHA-1. Confirma o que o
  `gov.br/esocial` já tinha indicado em busca agregada anterior ("o padrão de
  assinatura do eSocial é SHA256", ver `docs/rh-estado-esocial.md`) e o que
  `esocial_s1200.py` já registrava como "não confirmado se `assinador_local.py` seria
  diretamente reaproveitável" — agora confirmado que **não é**, sem ajuste: o hash
  muda, então as URIs de `SignatureMethod`/`DigestMethod` mudam com ele.
- **URIs dos algoritmos**: `rsa-sha256`/`sha256` vivem no namespace
  `http://www.w3.org/2001/04/xmldsig-more#`/`xmlenc#`, diferente do namespace
  `http://www.w3.org/2000/09/xmldsig#` usado pelos URIs `rsa-sha1`/`sha1` da NF-e —
  não é só trocar o sufixo do mesmo namespace.

Por que classes próprias em vez de reaproveitar as da NF-e
--------------------------------------------------------------------
`fiscal.documento.assinatura.MaterialAssinatura` documenta explicitamente "Digest
SHA-1" no docstring de cada campo — reaproveitá-la aqui deixaria a documentação
mentindo sobre o próprio dado que carrega (SHA-256). Mesmo teste da virtude 1 de
Yegor Bugayenko já aplicado neste projeto: o nome tem que continuar descrevendo o que
o objeto é depois de reaproveitado, não só o que ele parece ser por semelhança de
forma.

Pegadinha de namespace, registrada para quando a serialização completa existir
------------------------------------------------------------------------------------------
A mesma fonte adverte: o XML do eSocial deve conter **apenas** o namespace do próprio
evento no atributo `xmlns` — atributos `xsi`/`xsd` soltos no elemento raiz produzem
rejeição ("Assinatura do evento inválida"), mesmo com a assinatura tecnicamente
correta. Não é responsabilidade deste módulo (que só monta o `Signature` em si), mas
fica registrado aqui para quem for montar a serialização XML completa do evento.

Funções puras: nenhuma dependência do Frappe, nenhuma biblioteca de criptografia.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

__all__ = [
	"ALGORITMO_ASSINATURA",
	"ALGORITMO_C14N",
	"ALGORITMO_DIGEST",
	"ALGORITMO_TRANSFORMACAO",
	"Assinador",
	"AssinaturaInvalida",
	"CertificadoExpirado",
	"MaterialAssinatura",
	"montar_signature",
	"montar_signed_info",
	"referencia_do_id",
]

# C14N 1.0 sem comentários — mesma URI e mesmo comportamento da NF-e, confirmado como
# igual entre os dois perfis (ver docstring do módulo).
ALGORITMO_C14N = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"

# SHA-256, não SHA-1 — o ponto real de divergência do perfil da NF-e.
ALGORITMO_ASSINATURA = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
ALGORITMO_DIGEST = "http://www.w3.org/2001/04/xmlenc#sha256"

ALGORITMO_TRANSFORMACAO = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"

NAMESPACE_DSIG = "http://www.w3.org/2000/09/xmldsig#"


class AssinaturaInvalida(ValueError):
	"""Dado que impediria a assinatura ou a tornaria inválida."""


class CertificadoExpirado(AssinaturaInvalida):
	"""Certificado fora do período de validade — ação do usuário é renovar o
	certificado, não corrigir o documento (mesma distinção da NF-e)."""


@dataclass(frozen=True)
class MaterialAssinatura:
	"""O que a criptografia produziu, pronto para montar o envelope `Signature`."""

	digest: str
	"""Digest SHA-256 do elemento assinado, em base64."""

	assinatura: str
	"""Assinatura RSA-SHA256 do SignedInfo canonicalizado, em base64."""

	certificado: str
	"""Certificado X.509 em base64, sem cabeçalho PEM nem quebras de linha."""


@runtime_checkable
class Assinador(Protocol):
	"""Porta de assinatura — local, HSM ou serviço remoto, mesma ideia da NF-e."""

	def assinar(self, xml: bytes, id_elemento: str) -> MaterialAssinatura:
		"""Assina o elemento identificado e devolve digest, assinatura e certificado."""
		...


def referencia_do_id(id_elemento: str) -> str:
	"""Monta a URI da `Reference` a partir do `Id` do elemento — mesma regra da NF-e
	(sem o prefixo `#`, que é adicionado aqui)."""
	identificador = (id_elemento or "").strip()

	if not identificador:
		raise AssinaturaInvalida("O elemento a assinar precisa de um Id")

	if identificador.startswith("#"):
		raise AssinaturaInvalida(f"Informe o Id sem o prefixo '#', recebido {id_elemento!r}")

	return f"#{identificador}"


def montar_signed_info(id_elemento: str, digest: str) -> dict:
	"""Monta o bloco `SignedInfo` — mesma estrutura da NF-e, URIs de SHA-256."""
	if not (digest or "").strip():
		raise AssinaturaInvalida("O digest não pode ser vazio")

	return {
		"SignedInfo": {
			"CanonicalizationMethod": {"@Algorithm": ALGORITMO_C14N},
			"SignatureMethod": {"@Algorithm": ALGORITMO_ASSINATURA},
			"Reference": {
				"@URI": referencia_do_id(id_elemento),
				"Transforms": {
					"Transform": [
						{"@Algorithm": ALGORITMO_TRANSFORMACAO},
						{"@Algorithm": ALGORITMO_C14N},
					]
				},
				"DigestMethod": {"@Algorithm": ALGORITMO_DIGEST},
				"DigestValue": digest,
			},
		}
	}


def montar_signature(id_elemento: str, material: MaterialAssinatura) -> dict:
	"""Monta o elemento `Signature` completo — enveloped, como na NF-e."""
	if not (material.assinatura or "").strip():
		raise AssinaturaInvalida("A assinatura não pode ser vazia")

	if not (material.certificado or "").strip():
		raise AssinaturaInvalida(
			"O certificado precisa acompanhar a assinatura: sem ele o eSocial não tem "
			"como validar quem assinou"
		)

	return {
		"Signature": {
			"@xmlns": NAMESPACE_DSIG,
			**montar_signed_info(id_elemento, material.digest),
			"SignatureValue": material.assinatura,
			"KeyInfo": {"X509Data": {"X509Certificate": material.certificado}},
		}
	}
