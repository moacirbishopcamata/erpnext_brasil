# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Os arquivos PEM do TLS mútuo, com ciclo de vida próprio.

Por que existe
--------------------
`requests` exige o certificado cliente em **arquivo**, não em memória — e um certificado
A1 chega como PKCS#12. Alguém tem de escrever a chave privada em disco, e depois apagá-la.

Isso vivia dentro do `TransporteSefaz`, e ficou bem enquanto só a SEFAZ falava TLS mútuo. O
eSocial fala o mesmo protocolo com outro contexto (`ContextoEsocial`), e a alternativa a
extrair era **copiar o ciclo de vida de uma chave privada em disco** — exatamente o que a
docstring de `contexto_sefaz.py` proíbe, e pelo motivo certo: duas cópias, dois lugares
onde esquecer o `cleanup` vaza a chave até o processo morrer.

O que este módulo garante
--------------------------------
- **Os dois arquivos somem juntos.** Um diretório temporário próprio, não dois
  `NamedTemporaryFile` soltos: cert e chave nascem e morrem no mesmo `cleanup`, e o nome
  não colide com outra instância no mesmo processo.
- **A chave sai sem senha** (`NoEncryption`), porque é isso que o `requests` sabe ler — e é
  por isso que ela não pode sobreviver à chamada.
- **Preparar duas vezes não cria dois diretórios.** `preparar()` é idempotente.

⚠️ Quem usa é responsável por `fechar()`. As duas classes de transporte o fazem por
`__exit__`; usá-las fora de um `with` e esquecer o `fechar()` deixa a chave privada em
disco pelo resto da vida do processo.

Funções puras não — este módulo escreve arquivo. Mas não depende do Frappe.
"""

import tempfile
from pathlib import Path

__all__ = ["ArquivosTls"]


class ArquivosTls:
	"""Escreve cert e chave em PEM num diretório temporário, e os apaga junto."""

	def __init__(self, chave, certificado):
		"""`chave` e `certificado` são os objetos da `cryptography` já carregados do
		PKCS#12 — este módulo não abre o `.pfx`, para não ter a senha em mais um lugar."""
		self._chave = chave
		self._certificado = certificado
		self._diretorio = None
		self._cert = None
		self._arquivo_chave = None

	def preparar(self) -> None:
		"""Escreve os dois arquivos. Idempotente: chamar de novo não recria nada."""
		if self._diretorio is not None:
			return

		from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

		self._diretorio = tempfile.TemporaryDirectory(prefix="erpnext_brasil_tls_")
		base = Path(self._diretorio.name)

		self._cert = base / "cert.pem"
		self._cert.write_bytes(self._certificado.public_bytes(Encoding.PEM))

		self._arquivo_chave = base / "chave.pem"
		self._arquivo_chave.write_bytes(
			self._chave.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
		)

	def fechar(self) -> None:
		"""Apaga o diretório e os dois arquivos. Idempotente."""
		if self._diretorio is not None:
			self._diretorio.cleanup()
			self._diretorio = None
			self._cert = None
			self._arquivo_chave = None

	@property
	def cert(self) -> Path:
		"""Caminho do certificado em PEM. Prepara se ainda não foi preparado."""
		self.preparar()

		return self._cert

	@property
	def chave(self) -> Path:
		"""Caminho da chave privada em PEM, **sem senha** — ver a docstring do módulo."""
		self.preparar()

		return self._arquivo_chave

	@property
	def preparados(self) -> bool:
		return self._diretorio is not None
