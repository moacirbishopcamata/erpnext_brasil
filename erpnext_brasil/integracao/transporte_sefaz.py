# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Implementação de `TransporteFiscal` que fala direto com a SEFAZ.

`transmitir`/`consultar` (incluindo o polling de `NFeRetAutorizacao`) vivem em
`autorizacao_sefaz.py`; `cancelar`/`corrigir` em `eventos_sefaz.py`; `inutilizar` em
`inutilizacao_sefaz.py` — todos extraídos daqui só por tamanho de arquivo
(`test_arquitetura.py` limita módulo de integração a 320 linhas), fatorados por
responsabilidade real (autorização, evento, inutilização são três operações SEFAZ
distintas), nunca por prosa enxugada para caber no limite. Esta classe é o único ponto
que implementa `TransporteFiscal`; os três módulos extraídos são funções livres que
recebem um `ContextoSefaz` (ver `contexto_sefaz.py`) montado aqui.

`cancelar` e `corrigir` usam `NFeRecepcaoEvento4` — estrutura de `infEvento` de cada um
confirmada no pacote de esquemas do evento correspondente (Portal Nacional da NF-e),
separado do pacote de leiaute principal. Ver `fiscal/documento/evento.py` para a ordem
dos campos, a pegadinha do `@Id` e por que o sucesso de cada evento é decidido por
`tpEvento`, não por um único conjunto de `cStat`.

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

from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave
from erpnext_brasil.fiscal.documento.porta import RespostaTransmissao, ResultadoConsulta, ResultadoInutilizacao
from erpnext_brasil.integracao.assinador_local import AssinadorLocal, carregar_certificado
from erpnext_brasil.integracao.autorizacao_sefaz import consultar_situacao, enviar_autorizacao
from erpnext_brasil.integracao.contexto_sefaz import ContextoSefaz
from erpnext_brasil.integracao.eventos_sefaz import TransporteIndisponivel, enviar_evento

__all__ = ["TransporteIndisponivel", "TransporteSefaz"]


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

	def _contexto(self) -> ContextoSefaz:
		"""Monta o `ContextoSefaz` desta chamada — TLS já preparado, sessão já aberta.
		`TransporteSefaz` é o único ponto que constrói um `ContextoSefaz`; os módulos
		extraídos (`autorizacao_sefaz`, `eventos_sefaz`, `inutilizacao_sefaz`) só o
		recebem pronto."""
		self._preparar_arquivos_tls()

		return ContextoSefaz(
			uf=self._uf,
			ambiente=self._ambiente,
			sessao_http=self._sessao_http(),
			arquivo_cert=self._arquivo_cert,
			arquivo_chave=self._arquivo_chave,
		)

	def transmitir(self, documento: dict) -> RespostaTransmissao:
		"""Envia `documento` (a árvore `NFe` já assinada) e resolve até um estado final.

		Delega a `autorizacao_sefaz.enviar_autorizacao` — modelo (`"55"`/`"65"`) é lido
		lá dentro de `ide.mod`, não passado por parâmetro à parte: uma só fonte, sem
		risco de documento e parâmetro divergirem.
		"""
		return enviar_autorizacao(
			documento,
			self._contexto(),
			dormir=self._dormir,
			tentativas_consulta_recibo=self._tentativas_consulta_recibo,
			intervalo_consulta_recibo=self._intervalo_consulta_recibo,
		)

	def consultar(self, chave_acesso: str) -> ResultadoConsulta:
		"""Delega a `autorizacao_sefaz.consultar_situacao` — modelo lido da própria
		chave (posições 21-22), mesma razão de `transmitir`."""
		return consultar_situacao(chave_acesso, self._contexto())

	def _enviar_evento(self, evento: dict, chave_acesso: str, protocolo_padrao: str = "") -> RespostaTransmissao:
		"""Delega a `eventos_sefaz.enviar_evento` (extraído por tamanho de arquivo).
		Modelo lido da chave, mesma razão de `transmitir`."""
		return enviar_evento(
			evento,
			self._contexto(),
			chave_acesso=chave_acesso,
			modelo=ler_chave(chave_acesso).modelo,
			assinador=self._assinador,
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

	def inutilizar(
		self,
		ano: str,
		cnpj: str,
		modelo: str,
		serie: str,
		numero_inicial: str,
		numero_final: str,
		justificativa: str,
	) -> ResultadoInutilizacao:
		"""Inutiliza uma faixa de numeração via `NFeInutilizacao4`. Não é evento, não vai
		em lote — requisição única, resposta única (ver `inutilizacao_sefaz.py`)."""
		from erpnext_brasil.fiscal.documento.inutilizacao import CODIGO_UF_POR_SIGLA
		from erpnext_brasil.integracao.inutilizacao_sefaz import enviar_inutilizacao

		cuf = CODIGO_UF_POR_SIGLA.get(self._uf)

		if cuf is None:
			raise TransporteIndisponivel(f"UF {self._uf!r} sem código IBGE conhecido para inutilização")

		return enviar_inutilizacao(
			self._contexto(),
			cuf=cuf,
			ano=ano,
			cnpj=cnpj,
			modelo=modelo,
			serie=serie,
			numero_inicial=numero_inicial,
			numero_final=numero_final,
			justificativa=justificativa,
			assinador=self._assinador,
		)
