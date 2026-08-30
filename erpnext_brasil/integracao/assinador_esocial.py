# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Assinatura local do eSocial com certificado A1 — mesma técnica de
`assinador_local.py` (NF-e), hash diferente.

Por que não é `AssinadorLocal` com um parâmetro a mais
------------------------------------------------------------
`AssinadorLocal` (NF-e) tem `hashes.SHA1()` cravado em dois lugares (o digest do
elemento e a assinatura RSA do `SignedInfo`) — é um perfil fechado, documentado como
tal, e mexer nele para aceitar outro hash arriscaria uma regressão silenciosa numa
classe já testada e usada em produção fiscal. `AssinadorLocalEsocial` é uma classe
irmã, não uma generalização da primeira — mesmo raciocínio de `esocial_lote.py` não
reaproveitar `esocial_s1200.IdeEmpregador` quando o XSD realmente é outro.

O que é reaproveitado, e por quê
------------------------------------
- `carregar_certificado` (de `assinador_local.py`): abrir um PKCS#12 e checar
  validade não depende de qual hash vai assinar depois — mesmo código, sem
  duplicação.
- `para_xml` (de `fiscal/documento/serializacao.py`): serialização dict→XML é
  genérica, não específica da NF-e, apesar de morar sob `fiscal/documento/` — reusar
  evita duplicar ~150 linhas de escaping/CDATA já testadas.
- **Não** reaproveitado: `montar_signed_info`/`MaterialAssinatura`/`AssinaturaInvalida`
  da NF-e — vêm de `folha/esocial_assinatura.py`, o perfil SHA-256 (ver docstring
  daquele módulo para a divergência completa).

Dependências, imports tardios e segurança: mesma disciplina de `assinador_local.py`
(ver aquele módulo para a justificativa completa) — não repetida aqui.
"""

import base64

from erpnext_brasil.folha.esocial_assinatura import AssinaturaInvalida, MaterialAssinatura, montar_signed_info
from erpnext_brasil.integracao.assinador_local import carregar_certificado

__all__ = ["AssinadorLocalEsocial", "carregar_certificado"]


class AssinadorLocalEsocial:
	"""Assina eventos do eSocial com a chave privada carregada em memória.

	Implementa a porta `folha.esocial_assinatura.Assinador`. Estrutura idêntica a
	`AssinadorLocal`, hash SHA-256 em vez de SHA-1 nos dois pontos que importam:
	o digest do elemento e a assinatura RSA do `SignedInfo`.
	"""

	def __init__(self, pfx: bytes, senha: str):
		self._chave, self._certificado = carregar_certificado(pfx, senha)

	def assinar(self, xml: bytes, id_elemento: str) -> MaterialAssinatura:
		from cryptography.hazmat.primitives import hashes
		from cryptography.hazmat.primitives.asymmetric import padding
		from cryptography.hazmat.primitives.serialization import Encoding
		from lxml import etree

		raiz = etree.fromstring(xml)
		alvo = self._localizar(raiz, id_elemento)

		# C14N 1.0 sem comentários, não exclusive — mesma canonicalização da NF-e,
		# confirmado como igual entre os dois perfis (ver esocial_assinatura.py).
		canonicalizado = etree.tostring(alvo, method="c14n", exclusive=False, with_comments=False)

		digest = self._digest(canonicalizado, hashes)

		signed_info = montar_signed_info(id_elemento, digest)
		xml_signed_info = self._signed_info_xml(signed_info, etree)

		assinatura = self._chave.sign(xml_signed_info, padding.PKCS1v15(), hashes.SHA256())

		return MaterialAssinatura(
			digest=digest,
			assinatura=base64.b64encode(assinatura).decode("ascii"),
			certificado=base64.b64encode(self._certificado.public_bytes(Encoding.DER)).decode("ascii"),
		)

	@staticmethod
	def _digest(conteudo: bytes, hashes) -> str:
		from cryptography.hazmat.primitives.hashes import Hash

		calculo = Hash(hashes.SHA256())
		calculo.update(conteudo)

		return base64.b64encode(calculo.finalize()).decode("ascii")

	@staticmethod
	def _localizar(raiz, id_elemento: str):
		for elemento in raiz.iter():
			if elemento.get("Id") == id_elemento:
				return elemento

		raise AssinaturaInvalida(
			f"Não há elemento com Id {id_elemento!r} no XML: a Reference da assinatura "
			"não teria como resolver"
		)

	@staticmethod
	def _signed_info_xml(signed_info: dict, etree) -> bytes:
		from erpnext_brasil.fiscal.documento.serializacao import para_xml

		texto = para_xml(signed_info, namespace="http://www.w3.org/2000/09/xmldsig#")
		elemento = etree.fromstring(texto.encode("utf-8"))

		return etree.tostring(elemento, method="c14n", exclusive=False, with_comments=False)
