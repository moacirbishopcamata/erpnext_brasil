# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Implementação de `TransporteFiscal` que fala direto com a SEFAZ.

`cancelar` e `corrigir` (carta de correção) usam `NFeRecepcaoEvento4` — estrutura de
`infEvento` de cada um confirmada no pacote de esquemas do evento correspondente (Portal
Nacional da NF-e), separado do pacote de leiaute principal. Ver `fiscal/documento/
evento.py` para a ordem dos campos, a pegadinha do `@Id` e por que o sucesso de cada
evento é decidido por `tpEvento`, não por um único conjunto de `cStat`.

TLS mútuo com certificado em memória: `assinador_local.carregar_certificado`
(`cryptography`) carrega o A1 em memória, mas o `requests` só aceita certificado de
cliente como **arquivo** — sem suporte a certificado em memória na biblioteca padrão de
SSL do Python. Por isso a classe é *context manager*: os PEM são escritos uma vez em
diretório temporário na construção, e apagados ao fechar.

Injeção de dependência: `sessao` (cliente HTTP) e `dormir` (intervalo entre consultas)
são injetáveis, com padrão `requests.Session()`/`time.sleep` — mesma disciplina de
`RepositorioClassificacao`/`Assinador`, testa a orquestração inteira sem rede.
"""

import tempfile
import time
from datetime import datetime
from pathlib import Path

from erpnext_brasil.fiscal.documento.autorizadores_sefaz import endpoint
from erpnext_brasil.fiscal.documento.consulta import montar_cons_reci_nfe, montar_cons_sit_nfe
from erpnext_brasil.fiscal.documento.porta import Autorizacao, RespostaTransmissao, ResultadoConsulta
from erpnext_brasil.fiscal.documento.resposta_sefaz import RetornoAutorizacao, interpretar_autorizacao
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.documento.soap import extrair_resultado, montar_envelope
from erpnext_brasil.integracao.assinador_local import AssinadorLocal, carregar_certificado
from erpnext_brasil.integracao.eventos_sefaz import TransporteIndisponivel, enviar_evento

__all__ = ["TransporteIndisponivel", "TransporteSefaz"]


def _mapear_resultado(resultado: RetornoAutorizacao) -> RespostaTransmissao:
	"""Traduz a leitura pura da resposta (`RetornoAutorizacao`) para o formato que a
	porta `TransporteFiscal` exige (`RespostaTransmissao`). Nunca é chamada com um
	resultado ainda `pendente` — quem chama resolve o polling antes."""
	if resultado.denegado:
		return RespostaTransmissao(
			codigo=resultado.cstat_nfe or "", mensagem=resultado.motivo_nfe or "", denegado=True
		)

	if resultado.autorizado:
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
		cnpj_emitente: str,
		ambiente: str = "producao",
		sessao=None,
		dormir=None,
		tentativas_consulta_recibo: int = 5,
		intervalo_consulta_recibo: float = 5.0,
	):
		"""`cnpj_emitente` é configuração do adaptador, não dado por chamada: é "quem
		está autenticado por este certificado", estável entre `transmitir`/`cancelar` —
		diferente de `protocolo`/`justificativa`, que mudam a cada cancelamento. Por
		isso entra aqui e não na porta `TransporteFiscal.cancelar`."""
		self._chave, self._certificado = carregar_certificado(pfx, senha)
		# Segunda leitura do mesmo pfx: `_assinador` assina eventos; `_chave`/
		# `_certificado` acima viram os arquivos PEM do TLS mútuo — usos distintos.
		self._assinador = AssinadorLocal(pfx, senha)
		self._uf = uf
		self._cnpj_emitente = cnpj_emitente
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

	def _enviar_evento(self, evento: dict, chave_acesso: str, protocolo_padrao: str = "") -> RespostaTransmissao:
		"""Prepara TLS/sessão e delega a `eventos_sefaz.enviar_evento` (extraído por
		tamanho de arquivo, não por responsabilidade — ver o módulo)."""
		self._preparar_arquivos_tls()

		return enviar_evento(
			evento,
			uf=self._uf,
			ambiente=self._ambiente,
			chave_acesso=chave_acesso,
			assinador=self._assinador,
			sessao_http=self._sessao_http(),
			arquivo_cert=self._arquivo_cert,
			arquivo_chave=self._arquivo_chave,
			protocolo_padrao=protocolo_padrao,
		)

	def cancelar(self, chave_acesso: str, protocolo: str, justificativa: str) -> RespostaTransmissao:
		"""Envia o evento de cancelamento (110111) via `NFeRecepcaoEvento4`."""
		from erpnext_brasil.fiscal.documento.evento import montar_evento_cancelamento

		evento = montar_evento_cancelamento(
			chave_acesso=chave_acesso,
			protocolo=protocolo,
			justificativa=justificativa,
			cnpj_autor=self._cnpj_emitente,
			data_evento=datetime.now().astimezone().isoformat(timespec="seconds"),
		)

		return self._enviar_evento(evento, chave_acesso, protocolo_padrao=protocolo)

	def corrigir(self, chave_acesso: str, texto_correcao: str) -> RespostaTransmissao:
		"""Envia a carta de correção (110110) via `NFeRecepcaoEvento4`.

		Não muda o estado do `DocumentoFiscal` — uma CC-e não autoriza nem cancela nada,
		só emenda o texto de um documento já autorizado; `aplicar_resposta` não se aplica
		ao retorno deste método.
		"""
		from erpnext_brasil.fiscal.documento.evento import montar_evento_correcao

		evento = montar_evento_correcao(
			chave_acesso=chave_acesso,
			texto_correcao=texto_correcao,
			cnpj_autor=self._cnpj_emitente,
			data_evento=datetime.now().astimezone().isoformat(timespec="seconds"),
		)

		return self._enviar_evento(evento, chave_acesso)
