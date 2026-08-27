# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Assinatura local com certificado A1, usando `lxml` e `cryptography`.

Dependências
------------
As duas já vêm com o frappe — não há nada novo a instalar num bench. Foi por isso que se
optou por elas em vez de `signxml`: o perfil da NF-e é estreito o bastante para não
justificar mais uma dependência num bench compartilhado por vários apps.

Os imports ficam **dentro das funções**, e não no topo, para que o módulo possa ser
importado num ambiente sem essas bibliotecas — a suíte de testes verifica a estrutura da
assinatura sem precisar delas instaladas.

O que este módulo faz e o que não faz
-------------------------------------
Faz: canonicaliza, calcula digest, assina com a chave privada e extrai o certificado.
Não faz: monta XML de assinatura (isso é `fiscal/documento/assinatura.py`) nem decide
quando assinar (isso é o agregado). Uma responsabilidade, um motivo de mudança.

Segurança
---------
A senha do certificado nunca é registrada em log nem incorporada a mensagem de erro.
Falha de senha e certificado corrompido produzem mensagens distintas, porque a ação do
usuário é diferente em cada caso.
"""

import base64
from datetime import datetime, timezone

from erpnext_brasil.fiscal.documento.assinatura import (
	AssinaturaInvalida,
	CertificadoExpirado,
	MaterialAssinatura,
)

__all__ = ["AssinadorLocal", "carregar_certificado"]


def carregar_certificado(pfx: bytes, senha: str):
	"""Abre um certificado A1 (.pfx / PKCS#12) e devolve (chave privada, certificado).

	Verifica a validade na abertura: certificado vencido produz assinatura tecnicamente
	correta e documento rejeitado, e descobrir isso na SEFAZ é pior que descobrir aqui.
	"""
	try:
		from cryptography.hazmat.primitives.serialization import pkcs12
	except ImportError as e:  # pragma: no cover - depende do ambiente
		raise AssinaturaInvalida(
			"A biblioteca 'cryptography' é necessária para assinar. Ela acompanha o "
			"frappe; se este erro aparece, o ambiente está incompleto."
		) from e

	if not pfx:
		raise AssinaturaInvalida("Arquivo de certificado vazio")

	try:
		chave, certificado, _ = pkcs12.load_key_and_certificates(
			pfx, (senha or "").encode("utf-8")
		)
	except ValueError as e:
		# A biblioteca não distingue senha errada de arquivo corrompido; a mensagem
		# cobre os dois sem afirmar qual é, porque afirmar errado desorienta.
		raise AssinaturaInvalida(
			"Não foi possível abrir o certificado: senha incorreta ou arquivo inválido"
		) from e

	if chave is None or certificado is None:
		raise AssinaturaInvalida(
			"O arquivo não contém chave privada e certificado — verifique se é um A1 (.pfx)"
		)

	agora = datetime.now(timezone.utc)

	# `not_valid_after_utc` existe nas versões recentes; o atributo antigo é ingênuo
	# quanto a fuso e comparar com ele levantaria TypeError.
	expira = getattr(certificado, "not_valid_after_utc", None)
	inicia = getattr(certificado, "not_valid_before_utc", None)

	if expira is not None and expira < agora:
		raise CertificadoExpirado(
			f"O certificado venceu em {expira:%d/%m/%Y}. É preciso renová-lo — "
			"documento assinado com certificado vencido é rejeitado."
		)

	if inicia is not None and inicia > agora:
		raise CertificadoExpirado(
			f"O certificado só passa a valer em {inicia:%d/%m/%Y}."
		)

	return chave, certificado


class AssinadorLocal:
	"""Assina com a chave privada carregada em memória.

	Implementa a porta `Assinador`. O certificado é aberto uma vez, na construção: abrir
	a cada assinatura desperdiçaria trabalho e multiplicaria o número de vezes que a
	senha circula.
	"""

	def __init__(self, pfx: bytes, senha: str):
		self._chave, self._certificado = carregar_certificado(pfx, senha)

	def assinar(self, xml: bytes, id_elemento: str) -> MaterialAssinatura:
		"""Canonicaliza, calcula o digest e assina, no perfil que a SEFAZ exige."""
		from cryptography.hazmat.primitives import hashes
		from cryptography.hazmat.primitives.asymmetric import padding
		from cryptography.hazmat.primitives.serialization import Encoding
		from lxml import etree

		from erpnext_brasil.fiscal.documento.assinatura import montar_signed_info

		raiz = etree.fromstring(xml)
		alvo = self._localizar(raiz, id_elemento)

		# C14N 1.0 sem comentários — exclusive=False é o que o perfil da NF-e pede.
		canonicalizado = etree.tostring(alvo, method="c14n", exclusive=False, with_comments=False)

		digest = self._digest(canonicalizado, hashes)

		# O que se assina é o SignedInfo canonicalizado, não o documento.
		signed_info = montar_signed_info(id_elemento, digest)
		xml_signed_info = self._signed_info_xml(signed_info, etree)

		assinatura = self._chave.sign(xml_signed_info, padding.PKCS1v15(), hashes.SHA1())

		return MaterialAssinatura(
			digest=digest,
			assinatura=base64.b64encode(assinatura).decode("ascii"),
			certificado=base64.b64encode(
				self._certificado.public_bytes(Encoding.DER)
			).decode("ascii"),
		)

	@staticmethod
	def _digest(conteudo: bytes, hashes) -> str:
		from cryptography.hazmat.primitives.hashes import Hash

		calculo = Hash(hashes.SHA1())
		calculo.update(conteudo)

		return base64.b64encode(calculo.finalize()).decode("ascii")

	@staticmethod
	def _localizar(raiz, id_elemento: str):
		"""Encontra o elemento pelo atributo `Id`, como a `Reference` o resolverá."""
		for elemento in raiz.iter():
			if elemento.get("Id") == id_elemento:
				return elemento

		raise AssinaturaInvalida(
			f"Não há elemento com Id {id_elemento!r} no XML: a Reference da assinatura "
			"não teria como resolver"
		)

	@staticmethod
	def _signed_info_xml(signed_info: dict, etree) -> bytes:
		"""Serializa o SignedInfo e o canonicaliza, que é o que de fato se assina."""
		from erpnext_brasil.fiscal.documento.serializacao import para_xml

		texto = para_xml(signed_info, namespace="http://www.w3.org/2000/09/xmldsig#")
		elemento = etree.fromstring(texto.encode("utf-8"))

		return etree.tostring(elemento, method="c14n", exclusive=False, with_comments=False)
