# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Assinatura digital do XML da NF-e — o perfil XMLDSig que a SEFAZ exige.

Por que Python nativo
---------------------
Foi aqui que a localização brasileira anterior do ERPNext morreu: o último commit dela
chama-se ``feat: adiciona API debug_xml para investigar canonicalização``. Em Pascal, em
2005, canonicalização C14N era trabalho pesado — o que justificou o ACBr existir.

Em Python, não é. `lxml` implementa C14N nativamente e `cryptography` faz RSA e PKCS#12.
As duas **já são dependências do frappe**, então não há dependência nova a introduzir. O
que este módulo escreve não é criptografia: é a montagem de um envelope XMLDSig num
perfil fixo e estreito.

O perfil da NF-e
----------------
A SEFAZ não aceita XMLDSig genérico. O perfil é fechado:

- assinatura **enveloped** (fica dentro do próprio elemento assinado);
- canonicalização **C14N 1.0 sem comentários**;
- digest **SHA-1** e assinatura **RSA-SHA1** — obsoletos em geral, mas é o que o layout
  manda, e trocar por SHA-256 gera rejeição;
- `Reference URI` aponta para o `Id` do elemento (`#NFe<chave>`);
- o certificado vai embutido em `X509Certificate`.

Separação de responsabilidades
------------------------------
A **estrutura** do envelope (funções puras, testáveis sem nenhuma biblioteca) fica aqui.
A **criptografia** fica atrás do `Protocol` `Assinador`, com implementação em
`integracao/assinador_local.py`. É a mesma inversão de `TransporteFiscal`: permite trocar
assinatura local por HSM ou serviço remoto sem tocar na regra.
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

# URIs fixadas pelo perfil da NF-e. Não são configuráveis de propósito: trocar qualquer
# uma delas produz documento que a SEFAZ recusa.
ALGORITMO_C14N = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
ALGORITMO_ASSINATURA = "http://www.w3.org/2000/09/xmldsig#rsa-sha1"
ALGORITMO_DIGEST = "http://www.w3.org/2000/09/xmldsig#sha1"
ALGORITMO_TRANSFORMACAO = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"

NAMESPACE_DSIG = "http://www.w3.org/2000/09/xmldsig#"


class AssinaturaInvalida(ValueError):
	"""Dado que impediria a assinatura ou a tornaria inválida."""


class CertificadoExpirado(AssinaturaInvalida):
	"""Certificado fora do período de validade.

	Erro próprio porque a ação do usuário é diferente: não é corrigir o documento, é
	renovar o certificado — e a mensagem precisa dizer isso.
	"""


@dataclass(frozen=True)
class MaterialAssinatura:
	"""O que a criptografia produziu, pronto para montar o envelope."""

	digest: str
	"""Digest SHA-1 do elemento assinado, em base64."""

	assinatura: str
	"""Assinatura RSA-SHA1 do SignedInfo canonicalizado, em base64."""

	certificado: str
	"""Certificado X.509 em base64, sem cabeçalho PEM nem quebras de linha."""


@runtime_checkable
class Assinador(Protocol):
	"""Porta de assinatura — local, HSM ou serviço remoto.

	Interface pequena: uma operação. Quem assina não precisa saber montar XML, e quem
	monta XML não precisa saber de chave privada.
	"""

	def assinar(self, xml: bytes, id_elemento: str) -> MaterialAssinatura:
		"""Assina o elemento identificado e devolve digest, assinatura e certificado."""
		...


def referencia_do_id(id_elemento: str) -> str:
	"""Monta a URI da `Reference` a partir do `Id` do elemento.

	O `Id` da NF-e já vem com o prefixo `NFe`; a URI é ele precedido de `#`. Passar a
	chave crua aqui produziria referência que não resolve, e a SEFAZ rejeita com
	"digest value inválido" — mensagem que não aponta para a causa.
	"""
	identificador = (id_elemento or "").strip()

	if not identificador:
		raise AssinaturaInvalida("O elemento a assinar precisa de um Id")

	if identificador.startswith("#"):
		raise AssinaturaInvalida(
			f"Informe o Id sem o prefixo '#', recebido {id_elemento!r}"
		)

	return f"#{identificador}"


def montar_signed_info(id_elemento: str, digest: str) -> dict:
	"""Monta o bloco `SignedInfo` — o que efetivamente é assinado.

	A ordem dos elementos é a do padrão XMLDSig e **não** é livre: canonicalização e
	assinatura dependem dela, e trocar dois irmãos de lugar invalida a assinatura sem
	gerar erro de schema.
	"""
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
	"""Monta o elemento `Signature` completo, pronto para anexar ao documento.

	A assinatura da NF-e é **enveloped**: o elemento vai dentro do `NFe`, como irmão de
	`infNFe`, nunca fora.
	"""
	if not (material.assinatura or "").strip():
		raise AssinaturaInvalida("A assinatura não pode ser vazia")

	if not (material.certificado or "").strip():
		raise AssinaturaInvalida(
			"O certificado precisa acompanhar a assinatura: sem ele a SEFAZ não tem como "
			"validar quem assinou"
		)

	return {
		"Signature": {
			"@xmlns": NAMESPACE_DSIG,
			**montar_signed_info(id_elemento, material.digest),
			"SignatureValue": material.assinatura,
			"KeyInfo": {"X509Data": {"X509Certificate": material.certificado}},
		}
	}
