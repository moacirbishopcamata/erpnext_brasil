# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Monta o `ContextoEsocial` e fala com o eSocial — o elo que faltava na cadeia.

O órfão que este módulo resolve
--------------------------------------
A varredura de costura de 2026-09-06 encontrou `assinador_esocial` e
`transmissao_esocial` alcançados **só por teste**. Juntos diziam o que a NF-e dizia antes
de `emissao_nfe.py`: o eSocial tinha domínio completo — montagem, lote, assinatura, SOAP,
retorno, S-1000/S-1010/S-1200/S-1299/S-2200/S-2299 — e **não era acionável de um site**.

A causa era estrutural, não esquecimento: `ContextoEsocial` exige os arquivos PEM do TLS
mútuo, e **nada em produção os construía**. O único `ContextoEsocial(...)` do repositório
estava num arquivo de teste.

`TransporteEsocial` é para o eSocial o que `TransporteSefaz` é para a NF-e: o **único**
ponto que monta o contexto, e o dono do ciclo de vida do certificado.

Por que não herda de `TransporteSefaz`
---------------------------------------------
Porque não é a mesma coisa com parâmetros diferentes. Muda o contexto (`ContextoEsocial`
não tem UF), muda a assinatura (SHA-256 contra SHA-1), muda o protocolo (lote assíncrono
com consulta obrigatória, contra recibo da SEFAZ) e mudam os endpoints. O que os dois
**de fato** compartilham — escrever a chave privada em disco e apagá-la — foi extraído para
`tls_certificado.ArquivosTls`, e é só isso que se reaproveita.

Herdar para reusar código, e não comportamento, é o antipadrão que a composição resolve.

⚠️ A senha do certificado não fica neste objeto
-------------------------------------------------------
Ela é usada uma vez, ao abrir o PKCS#12, e não é guardada em atributo. O que sobra em
memória são a chave e o certificado já carregados — e em disco, só enquanto o `with` durar.
"""

import time

from erpnext_brasil.integracao.assinador_esocial import AssinadorLocalEsocial, carregar_certificado
from erpnext_brasil.integracao.contexto_esocial import ContextoEsocial
from erpnext_brasil.integracao.tls_certificado import ArquivosTls
from erpnext_brasil.integracao.transmissao_esocial import consultar_lote, enviar_lote

__all__ = ["TransporteEsocial"]


class TransporteEsocial:
	"""Fala com o eSocial por SOAP, com TLS mútuo do certificado A1 da empresa."""

	def __init__(
		self,
		pfx: bytes,
		senha: str,
		ambiente: int,
		sessao=None,
		dormir=None,
		tentativas_consulta: int = 5,
		intervalo_consulta: float = 5.0,
	):
		"""`ambiente` é o inteiro do leiaute (1 produção, 2 produção restrita), não o
		rótulo do DocType: quem traduz é quem chama, e o transporte fala a língua do
		leiaute."""
		self._chave, self._certificado = carregar_certificado(pfx, senha)
		# Segunda leitura do mesmo pfx, como em `TransporteSefaz`: o assinador assina os
		# eventos (SHA-256), e a chave acima vira os PEM do TLS. Usos distintos.
		self._assinador = AssinadorLocalEsocial(pfx, senha)
		self._ambiente = ambiente
		self._sessao = sessao
		self._dormir = dormir or time.sleep
		self._tentativas_consulta = tentativas_consulta
		self._intervalo_consulta = intervalo_consulta
		self._tls = ArquivosTls(self._chave, self._certificado)

	def __enter__(self) -> "TransporteEsocial":
		self._tls.preparar()

		return self

	def __exit__(self, *_exc) -> None:
		self.fechar()

	def fechar(self) -> None:
		"""Apaga os PEM. Chamado por `__exit__`; fora de um `with`, é obrigação de quem
		usa — a chave privada não deve sobreviver à chamada."""
		self._tls.fechar()

	@property
	def assinador(self) -> AssinadorLocalEsocial:
		"""O assinador dos eventos.

		Exposto porque a montagem do evento acontece **antes** do envio e precisa dele:
		`esocial_montagem.montar_evento_assinado` assina cada evento, e só então
		`esocial_lote.montar_xml_lote` os envelopa. Criar um segundo assinador do mesmo
		`.pfx` significaria pedir a senha outra vez.
		"""
		return self._assinador

	def _sessao_http(self):
		if self._sessao is not None:
			return self._sessao

		import requests

		self._sessao = requests.Session()

		return self._sessao

	def _contexto(self) -> ContextoEsocial:
		"""Monta o `ContextoEsocial` desta chamada.

		Este é o **único** ponto do app que constrói um: `transmissao_esocial` só o
		recebe pronto, pela mesma razão que `autorizacao_sefaz` recebe o `ContextoSefaz`.
		"""
		self._tls.preparar()

		return ContextoEsocial(
			ambiente=self._ambiente,
			sessao_http=self._sessao_http(),
			arquivo_cert=self._tls.cert,
			arquivo_chave=self._tls.chave,
		)

	def enviar(self, xml_lote_assinado: str):
		"""Envia o lote e resolve até um estado final.

		Devolve `RetornoProcessamentoLote` — nunca o `RetornoEnvioLote` cru: a resposta
		imediata do eSocial só confirma a recepção, e o resultado por evento vem da
		consulta. Quem trata isso é `transmissao_esocial.enviar_lote`.
		"""
		return enviar_lote(
			xml_lote_assinado,
			self._contexto(),
			dormir=self._dormir,
			tentativas_consulta=self._tentativas_consulta,
			intervalo_consulta=self._intervalo_consulta,
		)

	def consultar(self, protocolo_envio: str):
		"""Consulta o processamento de um lote já enviado, sem reenviá-lo."""
		return consultar_lote(protocolo_envio, self._contexto())
