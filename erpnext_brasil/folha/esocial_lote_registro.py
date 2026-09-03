# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Regras do registro de um lote do eSocial — puras, sem DocType nem Frappe.

Segundo DocType do app, pela mesma razão do primeiro (`transmissao_registro.py`): existe
dado com vida própria que não é atributo de nenhum documento do ERPNext.

Aqui, porém, a falta de persistência não era só perda de histórico — era **perda
funcional**. O eSocial responde `cdResposta=203` ("lote já recebido, em fila") quando
ainda não terminou de processar, e a resposta definitiva só se obtém consultando depois,
com o `protocoloEnvio`. `transmissao_esocial.enviar_lote` faz esse polling dentro da
mesma chamada, mas se ele esgotar as tentativas — e `TransporteIndisponivel` é levantado
justamente nesse caso — **o protocolo se perde**, e com ele a única forma de descobrir o
que aconteceu com aquela folha. Sem registro, o lote vira um envio que ninguém sabe se
foi aceito.

O protocolo é a chave de tudo, e por isso é validado
------------------------------------------------------------
`protocolo_e_valido` (de `esocial_consulta.py`) já conhece o formato exato —
`A.B.` + 19 dígitos, com agente e ambiente embutidos. Reaproveitado aqui em vez de
reescrito: um protocolo mal gravado é um lote que não dá para consultar de novo, que é
exatamente o problema que este registro existe para resolver.

Ambiente do eSocial ≠ ambiente da SEFAZ
----------------------------------------------
Produção **restrita**, não homologação. Já registrado em
`integracao/configuracao_fiscal.py`: são domínios distintos, e um site pode estar
homologando NF-e enquanto já opera em produção no eSocial. O registro usa o domínio do
eSocial, não o da SEFAZ.

Funções puras: nenhuma dependência do Frappe.
"""

from erpnext_brasil.folha.esocial_consulta import protocolo_e_valido
from erpnext_brasil.folha.esocial_retorno import (
	CODIGO_LOTE_JA_RECEBIDO_EM_FILA,
	CODIGOS_SUCESSO,
)

__all__ = [
	"AMBIENTES",
	"SITUACAO_EM_PROCESSAMENTO",
	"SITUACAO_ENVIADO",
	"SITUACAO_PROCESSADO",
	"SITUACAO_REJEITADO",
	"SITUACOES",
	"LoteInvalido",
	"situacao_para_codigo",
	"validar_lote",
]

SITUACAO_ENVIADO = "Enviado"
"""Transmitido, sem resposta lida ainda."""

SITUACAO_EM_PROCESSAMENTO = "Em processamento"
"""`cdResposta=203`: o eSocial recebeu e ainda não decidiu — exige nova consulta."""

SITUACAO_PROCESSADO = "Processado"
SITUACAO_REJEITADO = "Rejeitado"

SITUACOES = (
	SITUACAO_ENVIADO,
	SITUACAO_EM_PROCESSAMENTO,
	SITUACAO_PROCESSADO,
	SITUACAO_REJEITADO,
)

AMBIENTES = ("Produção restrita", "Produção")
"""Domínio do eSocial, não o da SEFAZ — ver docstring do módulo."""


class LoteInvalido(ValueError):
	"""Estado que faria o registro do lote mentir, ou que o tornaria inconsultável."""


def situacao_para_codigo(cd_resposta: int) -> str:
	"""Traduz o `cdResposta` do eSocial na situação do registro.

	Só os códigos confirmados decidem: `201`/`202` são sucesso, `203` é pendência.
	Qualquer outro é rejeição — inclusive um código desconhecido, porque "não é sucesso
	nem pendência confirmada" é, na prática, algo que precisa de atenção humana. Mesma
	disciplina de `esocial_retorno.StatusRetorno`, que nunca assume código não tabelado
	como sucesso.
	"""
	if cd_resposta in CODIGOS_SUCESSO:
		return SITUACAO_PROCESSADO

	if cd_resposta == CODIGO_LOTE_JA_RECEBIDO_EM_FILA:
		return SITUACAO_EM_PROCESSAMENTO

	return SITUACAO_REJEITADO


def validar_lote(dados: dict) -> None:
	"""Confere as invariantes de um registro de lote do eSocial."""
	situacao = (dados.get("situacao") or "").strip()
	ambiente = (dados.get("ambiente") or "").strip()
	protocolo = (dados.get("protocolo_envio") or "").strip()

	if situacao not in SITUACOES:
		raise LoteInvalido(f"situação deve ser uma de {list(SITUACOES)}, recebido {situacao!r}")

	if ambiente not in AMBIENTES:
		raise LoteInvalido(
			f"ambiente deve ser um de {list(AMBIENTES)} (domínio do eSocial, não o da "
			f"SEFAZ), recebido {ambiente!r}"
		)

	_validar_protocolo(situacao, protocolo)


def _validar_protocolo(situacao: str, protocolo: str) -> None:
	"""O protocolo é o que permite consultar de novo — sem ele, um lote em processamento
	fica inconsultável para sempre, que é o pior estado possível deste registro."""
	if situacao == SITUACAO_EM_PROCESSAMENTO and not protocolo:
		raise LoteInvalido(
			"lote em processamento exige o protocolo de envio: é a única forma de "
			"consultar o resultado depois, e sem ele o lote fica perdido"
		)

	if not protocolo:
		return

	if not protocolo_e_valido(protocolo):
		raise LoteInvalido(
			f"protocoloEnvio deve seguir o formato 'A.B.' + 19 dígitos "
			f"(ex. '1.1.0000000000000000001'), recebido {protocolo!r}"
		)
