# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A porta de transmissão: o contrato que mantém o transporte trocável.

Por que uma porta
-----------------
Existem pelo menos três transportes plausíveis para a NF-e — ACBrLib local via `ctypes`,
ACBr API por HTTP, provedor comercial — e a escolha depende de custo por documento,
de onde fica o certificado A1 e de quem assume a contingência da SEFAZ. Nenhuma dessas
respostas é do domínio fiscal.

O documento conversa com esta interface, nunca com um fornecedor. Assim a escolha do
transporte fica adiável e reversível, e duas empresas na mesma instalação podem usar
transportes diferentes.

Isso não é preciosismo: o projeto de localização brasileira anterior morreu justamente
por acoplar o documento à assinatura local que não conseguiu fazer funcionar. Quem amarra
o documento a um transporte aposta o sistema inteiro naquele transporte dar certo.

O que a porta **não** faz
-------------------------
Não decide estado. O adaptador devolve o que a SEFAZ respondeu; quem transiciona é o
agregado em `estado.py`, aplicando suas guardas. Um adaptador que mudasse o estado
sozinho reintroduziria o problema que o agregado existe para evitar.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

__all__ = [
	"Autorizacao",
	"RespostaTransmissao",
	"ResultadoConsulta",
	"TransporteFiscal",
	"aplicar_resposta",
]

from erpnext_brasil.fiscal.documento.estado import DocumentoFiscal, Protocolo


@dataclass(frozen=True)
class Autorizacao:
	"""Autorização concedida, com o protocolo que a prova."""

	protocolo: str
	recebido_em: datetime
	chave_acesso: str = ""
	xml_autorizado: str = ""


@dataclass(frozen=True)
class RespostaTransmissao:
	"""O que a SEFAZ respondeu — dado, não decisão.

	`codigo` e `mensagem` vêm cru do retorno; `autorizacao` só existe quando houve
	autorização de fato.
	"""

	codigo: str
	mensagem: str
	autorizacao: Autorizacao | None = None
	denegado: bool = False
	bruto: dict = field(default_factory=dict)

	@property
	def autorizada(self) -> bool:
		return self.autorizacao is not None


@dataclass(frozen=True)
class ResultadoConsulta:
	codigo: str
	mensagem: str
	estado_sefaz: str = ""


@runtime_checkable
class TransporteFiscal(Protocol):
	"""Contrato mínimo de um transporte de documento fiscal.

	Deliberadamente pequeno: cobre o que o ERPNext precisa, não as 221 operações que uma
	API de documentos fiscais pode expor. Superfície menor é adaptador mais fácil de
	escrever e de substituir.
	"""

	def transmitir(self, documento: dict) -> RespostaTransmissao:
		"""Envia o documento e devolve o que a SEFAZ respondeu."""
		...

	def consultar(self, chave_acesso: str) -> ResultadoConsulta:
		"""Consulta a situação de um documento já transmitido."""
		...

	def cancelar(self, chave_acesso: str, protocolo: str, justificativa: str) -> RespostaTransmissao:
		"""Solicita o cancelamento (evento 110111).

		`protocolo` é o número da autorização original — o schema do evento de
		cancelamento exige `nProt` (a SEFAZ precisa saber qual autorização está sendo
		cancelada, não só qual chave). Descoberto ao implementar o adaptador real: a
		primeira versão desta porta não previa esse parâmetro."""
		...

	def corrigir(self, chave_acesso: str, texto_correcao: str) -> RespostaTransmissao:
		"""Solicita a carta de correção (evento 110110).

		Diferente de `cancelar`, não recebe `protocolo` — o schema da CC-e não exige o
		protocolo da autorização, só a chave e o texto da correção. `texto_correcao` já
		deve trazer o histórico de correções anteriores, se houver — a porta não sabe
		nem guarda esse histórico, é responsabilidade de quem chama (mesma fronteira que
		o resto deste app usa entre "monta o documento" e "decide o conteúdo dele")."""
		...


def aplicar_resposta(documento: DocumentoFiscal, resposta: RespostaTransmissao) -> None:
	"""Traduz a resposta do transporte na transição correspondente do agregado.

	É aqui que a costura crítica se fecha: o protocolo devolvido pela SEFAZ vira estado
	persistido do documento. Se esta função não for chamada — ou falhar em silêncio —
	existe nota autorizada no fisco e rascunho no sistema.

	A ordem das verificações importa: **denegação antes de autorização**, porque denegado
	é final e não deve ser confundido com rejeição comum.
	"""
	if resposta.denegado:
		documento.denegar(resposta.mensagem or f"Denegado pela SEFAZ (código {resposta.codigo})")

		return

	if resposta.autorizada:
		autorizacao = resposta.autorizacao
		documento.autorizar(
			Protocolo(
				numero=autorizacao.protocolo,
				recebido_em=autorizacao.recebido_em,
				chave_acesso=autorizacao.chave_acesso,
			)
		)

		return

	documento.rejeitar(resposta.mensagem or f"Rejeitado pela SEFAZ (código {resposta.codigo})")
