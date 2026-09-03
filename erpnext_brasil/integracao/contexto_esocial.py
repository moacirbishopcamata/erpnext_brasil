# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Objeto de valor: em qual ambiente do eSocial, com qual TLS já preparado.

Mesmo raciocínio de `contexto_sefaz.ContextoSefaz` (ver aquele módulo para a
justificativa completa) — a diferença real, não cosmética: o eSocial não tem UF
(`esocial_lote.endpoint` já confirmou um único endpoint nacional por
ambiente/serviço, ao contrário da SEFAZ), então este objeto não carrega `uf`.
`ambiente` aqui é o inteiro de `esocial_s1200.AMBIENTE_PRODUCAO`/
`AMBIENTE_PRODUCAO_RESTRITA` — um domínio diferente do `"producao"`/`"homologacao"`
string da SEFAZ, não um decalque.

Imutável (`frozen`) pela mesma razão de `ContextoSefaz`: representa um TLS já
preparado para esta sessão por `TransporteEsocial`; os módulos de transmissão só
recebem e usam, nunca constroem um `ContextoEsocial` sozinhos.
"""

from dataclasses import dataclass
from pathlib import Path

__all__ = ["ContextoEsocial"]


@dataclass(frozen=True)
class ContextoEsocial:
	"""`sessao_http` é injetável (padrão `requests.Session()`) — mesma razão de
	`ContextoSefaz.sessao_http`: testa a orquestração inteira sem rede."""

	ambiente: int
	sessao_http: object
	arquivo_cert: Path
	arquivo_chave: Path
