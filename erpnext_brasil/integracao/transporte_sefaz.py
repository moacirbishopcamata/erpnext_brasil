# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Implementação de `TransporteFiscal` que fala direto com a SEFAZ.

Escopo desta versão — leia antes de estender
----------------------------------------------
Implementa `transmitir` (com o *polling* do lote assíncrono) e `consultar`.
**`cancelar` levanta `NotImplementedError`** de propósito: a estrutura completa de
`infEvento` (cancelamento) tem campos — `tpAmb`, `CNPJ`, `chNFe`, `dhEvento`,
`nSeqEvento`, `verEvento` — cuja ordem exata só o XSD do evento resolve com certeza, e
esse XSD não foi conferido ainda (não veio no pacote de leiaute principal). Só a
composição do `Id` e o miolo de `detEvento` (`descEvento`, `nProt`, `xJust`) estão
confirmados. Implementar cancelamento adivinhando a ordem dos demais campos arriscaria
rejeição silenciosa — o próprio motivo deste app existir é não arriscar isso.

TLS mútuo com certificado em memória
--------------------------------------
O certificado A1 é carregado em memória por `assinador_local.carregar_certificado`
(`cryptography`), mas o `requests` só aceita certificado de cliente como **arquivo**
(`cert=(certfile, keyfile)`) — não há suporte a certificado em memória na biblioteca
padrão de SSL do Python. A solução, e o motivo de a classe ser um *context manager*: os
arquivos PEM são escritos uma vez, em arquivo temporário, na construção, e apagados ao
fechar — nunca ficam em disco além do necessário, e não se reescreve a cada requisição.

Injeção de dependência
------------------------
`sessao` (cliente HTTP) e `dormir` (para o intervalo entre tentativas de consulta) são
parâmetros injetáveis, com padrão `requests.Session()` e `time.sleep` respectivamente —
mesma disciplina de `RepositorioClassificacao`/`Assinador`: permite testar a
orquestração inteira (resolução de endpoint, envelope, mapeamento de resposta) sem rede
e sem esperar de verdade entre tentativas.
"""

import tempfile
import time
from pathlib import Path

from erpnext_brasil.fiscal.documento.autorizadores_sefaz import endpoint
from erpnext_brasil.fiscal.documento.consulta import montar_cons_reci_nfe, montar_cons_sit_nfe
from erpnext_brasil.fiscal.documento.porta import Autorizacao, RespostaTransmissao, ResultadoConsulta
from erpnext_brasil.fiscal.documento.resposta_sefaz import RetornoAutorizacao, interpretar_autorizacao
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.documento.soap import extrair_resultado, montar_envelope
from erpnext_brasil.integracao.assinador_local import carregar_certificado

__all__ = ["TransporteIndisponivel", "TransporteSefaz"]


class TransporteIndisponivel(RuntimeError):
	"""A SEFAZ não respondeu de forma decidida dentro do que este adaptador tenta."""


def _mapear_resultado(resultado: RetornoAutorizacao) -> RespostaTransmissao:
	"""Traduz a leitura pura da resposta (`RetornoAutorizacao`) para o formato que a
	porta `TransporteFiscal` exige (`RespostaTransmissao`). Nunca é chamada com um
	resultado ainda `pendente` — quem chama resolve o polling antes."""
	if resultado.denegado:
		return RespostaTransmissao(
			codigo=resultado.cstat_nfe or "", mensagem=resultado.motivo_nfe or "", denegado=True
		)

	if resultado.autorizado:
		from datetime import datetime

		recebido_em = (
			datetime.fromisoformat(resultado.data_recebimento)
			if resultado.data_recebimento
			else datetime.now().astimezone()
		)

		return RespostaTransmissao(
			codigo=resultado.cstat_nfe,
			mensagem=resultado.motivo_nfe or "",
			autorizacao=Autorizacao(
				protocolo=resultado.protocolo,
				recebido_em=recebido_em,
				chave_acesso=resultado.chave_conferida or "",
			),
		)

	return RespostaTransmissao(
		codigo=resultado.cstat_nfe or resultado.cstat_lote, mensagem=resultado.motivo_nfe or resultado.motivo_lote
	)


class TransporteSefaz:
	"""Implementa `TransporteFiscal` falando SOAP direto com o autorizador da UF."""

	def __init__(
		self,
		pfx: bytes,
		senha: str,
		uf: str,
		ambiente: str = "producao",
		sessao=None,
		dormir=None,
		tentativas_consulta_recibo: int = 5,
		intervalo_consulta_recibo: float = 5.0,
	):
		self._chave, self._certificado = carregar_certificado(pfx, senha)
		self._uf = uf
		self._ambiente = ambiente
		self._tp_amb = "1" if ambiente == "producao" else "2"
		self._sessao = sessao
		self._dormir = dormir or time.sleep
		self._tentativas_consulta_recibo = tentativas_consulta_recibo
		self._intervalo_consulta_recibo = intervalo_consulta_recibo
		self._diretorio_temp = None
		self._arquivo_cert = None
		self._arquivo_chave = None

	def __enter__(self) -> "TransporteSefaz":
		self._preparar_arquivos_tls()

		return self

	def __exit__(self, *_exc) -> None:
		self.fechar()

	def fechar(self) -> None:
		"""Remove os arquivos temporários do certificado. Chamado por `__exit__`, e
		também deve ser chamado explicitamente se a classe não for usada como `with`."""
		if self._diretorio_temp is not None:
			self._diretorio_temp.cleanup()
			self._diretorio_temp = None

	def _preparar_arquivos_tls(self) -> None:
		if self._diretorio_temp is not None:
			return

		from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

		# Diretório próprio, não `NamedTemporaryFile` solto: garante que os dois arquivos
		# (cert e chave) somem juntos, e que o nome não colide com outra instância.
		self._diretorio_temp = tempfile.TemporaryDirectory(prefix="erpnext_brasil_tls_")
		base = Path(self._diretorio_temp.name)

		self._arquivo_cert = base / "cert.pem"
		self._arquivo_cert.write_bytes(self._certificado.public_bytes(Encoding.PEM))

		self._arquivo_chave = base / "chave.pem"
		self._arquivo_chave.write_bytes(
			self._chave.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
		)

	def _sessao_http(self):
		if self._sessao is not None:
			return self._sessao

		import requests

		self._sessao = requests.Session()

		return self._sessao

	def _enviar(self, servico: str, arvore: dict) -> RetornoAutorizacao:
		self._preparar_arquivos_tls()

		url = endpoint(self._uf, servico, ambiente=self._ambiente)

		if not url:
			raise TransporteIndisponivel(
				f"Não há endpoint confirmado para {servico!r} na UF {self._uf!r} "
				f"(ambiente {self._ambiente!r})"
			)

		xml_interno = para_xml(arvore)
		envelope = montar_envelope(servico, xml_interno)

		resposta = self._sessao_http().post(
			url,
			data=envelope.encode("utf-8"),
			headers={"Content-Type": "application/soap+xml; charset=utf-8"},
			cert=(str(self._arquivo_cert), str(self._arquivo_chave)),
			timeout=30,
		)
		resposta.raise_for_status()

		return interpretar_autorizacao(extrair_resultado(resposta.content))

	def _resolver_pendencia(self, resultado: RetornoAutorizacao) -> RetornoAutorizacao:
		"""Consulta o recibo até o lote sair do estado `pendente`, ou desiste."""
		if not resultado.pendente:
			return resultado

		if not resultado.numero_recibo:
			raise TransporteIndisponivel(
				"Lote pendente sem número de recibo — não há como consultar o resultado depois"
			)

		for _ in range(self._tentativas_consulta_recibo):
			self._dormir(self._intervalo_consulta_recibo)

			resultado = self._enviar(
				"NFeRetAutorizacao", montar_cons_reci_nfe(resultado.numero_recibo, self._tp_amb)
			)

			if not resultado.pendente:
				return resultado

		raise TransporteIndisponivel(
			f"Lote continuou pendente após {self._tentativas_consulta_recibo} consultas — "
			"a SEFAZ não decidiu a tempo, não é rejeição nem autorização"
		)

	def transmitir(self, documento: dict) -> RespostaTransmissao:
		"""Envia `documento` (a árvore `NFe` já assinada) e resolve até um estado final.

		`documento` é a árvore de `montar_nfe`/`assinar_nfe` — este método serializa e
		envelopa, não recebe XML pronto: mantém a mesma fronteira que todo o resto do
		app usa entre árvore de dicionário e string.
		"""
		resultado = self._enviar("NFeAutorizacao", documento)
		resultado = self._resolver_pendencia(resultado)

		return _mapear_resultado(resultado)

	def consultar(self, chave_acesso: str) -> ResultadoConsulta:
		resultado = self._enviar(
			"NfeConsultaProtocolo", montar_cons_sit_nfe(chave_acesso, self._tp_amb)
		)

		return ResultadoConsulta(
			codigo=resultado.cstat_nfe or resultado.cstat_lote,
			mensagem=resultado.motivo_nfe or resultado.motivo_lote,
			estado_sefaz=resultado.cstat_nfe or resultado.cstat_lote,
		)

	def cancelar(self, chave_acesso: str, justificativa: str) -> RespostaTransmissao:
		raise NotImplementedError(
			"Cancelamento ainda não implementado: a ordem completa dos campos de "
			"infEvento não está confirmada contra o XSD do evento — ver docstring do "
			"módulo. Implementar aqui exigiria adivinhar, o que este app não faz."
		)
