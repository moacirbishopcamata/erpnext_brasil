# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""eSocial: consulta de processamento de lote (`consultaLoteEventos`).

Resolve o gap que `docs/rh-esocial-soap.md` tinha deixado explícito: o wrapper SOAP
`<consulta>` (`esocial_soap.py`) tem um nome, mas o conteúdo XML por dentro dele —
`ConsultaLoteEventos-v1_0_0.xsd` — não tinha sido lido. Lido agora: é só um campo,
`protocoloEnvio`, com formato documentado no próprio XSD.

Formato de `protocoloEnvio`, confirmado (não mais um "não confirmado nesta rodada")
------------------------------------------------------------------------------------------
`A.B.NNNNNNNNNNNNNNNNNNN` — 23 caracteres, três partes separadas por ponto:

- `A` (1 dígito): agente processador — `1` = Serpro, `2` = Caixa.
- `B` (1 dígito): ambiente — `1` = Produção, `2` = Pré-produção (dados reais),
  `3` = Pré-produção (dados fictícios), `6` = Homologação, `7` = Validação,
  `8` = Testes, `9` = Desenvolvimento. Note que **não** é o mesmo domínio de
  `esocial_s1200.AMBIENTE_PRODUCAO`/`AMBIENTE_PRODUCAO_RESTRITA` (dois valores) —
  o protocolo tem um domínio de ambiente próprio, mais granular, específico da
  infraestrutura de quem processou o lote.
- `N` (19 dígitos): sequencial.

Isso também resolve, retroativamente, a ressalva que `esocial_retorno.
DadosRecepcaoLote` tinha registrado ("formato exato... não confirmado") — atualizado
para validar o formato completo em vez de só o tamanho máximo.

Funções puras: nenhuma dependência do Frappe.
"""

import re

__all__ = [
	"AGENTE_CAIXA",
	"AGENTE_SERPRO",
	"AMBIENTE_DESENVOLVIMENTO",
	"AMBIENTE_HOMOLOGACAO",
	"AMBIENTE_PRE_PRODUCAO_FICTICIO",
	"AMBIENTE_PRE_PRODUCAO_REAL",
	"AMBIENTE_PRODUCAO_PROTOCOLO",
	"AMBIENTE_TESTES",
	"AMBIENTE_VALIDACAO",
	"PADRAO_PROTOCOLO_ENVIO",
	"ConsultaLoteInvalida",
	"montar_consulta_lote_eventos",
	"protocolo_e_valido",
]

AGENTE_SERPRO = 1
AGENTE_CAIXA = 2

# Domínio de ambiente do PROTOCOLO — mais granular que
# esocial_s1200.AMBIENTE_PRODUCAO/AMBIENTE_PRODUCAO_RESTRITA (só 2 valores), não o
# mesmo conceito apesar do nome parecido.
AMBIENTE_PRODUCAO_PROTOCOLO = 1
AMBIENTE_PRE_PRODUCAO_REAL = 2
AMBIENTE_PRE_PRODUCAO_FICTICIO = 3
AMBIENTE_HOMOLOGACAO = 6
AMBIENTE_VALIDACAO = 7
AMBIENTE_TESTES = 8
AMBIENTE_DESENVOLVIMENTO = 9

# "A.B." + 19 dígitos sequenciais — confirmado contra o XSD (ConsultaLoteEventos-v1_0_0.xsd)
# e o exemplo literal que ele documenta ("1.1.0000000000000000001").
PADRAO_PROTOCOLO_ENVIO = re.compile(r"^\d\.\d\.\d{19}$")


class ConsultaLoteInvalida(ValueError):
	"""Dado que impede a montagem da consulta — protocolo fora do formato."""


def protocolo_e_valido(protocolo_envio: str) -> bool:
	"""Confere só o formato (`A.B.` + 19 dígitos) — não valida se `A`/`B` são
	valores conhecidos do domínio (agente/ambiente), só a forma geral."""
	return bool(PADRAO_PROTOCOLO_ENVIO.match(protocolo_envio or ""))


def montar_consulta_lote_eventos(protocolo_envio: str) -> dict:
	"""Monta a árvore `eSocial > consultaLoteEventos > protocoloEnvio` — o conteúdo
	que vai dentro do wrapper `<consulta>` de `esocial_soap.montar_envelope`."""
	if not protocolo_e_valido(protocolo_envio):
		raise ConsultaLoteInvalida(
			f"protocoloEnvio deve seguir o formato 'A.B.' + 19 dígitos "
			f"(ex. '1.1.0000000000000000001'), recebido {protocolo_envio!r}"
		)

	return {"eSocial": {"consultaLoteEventos": {"protocoloEnvio": protocolo_envio}}}
