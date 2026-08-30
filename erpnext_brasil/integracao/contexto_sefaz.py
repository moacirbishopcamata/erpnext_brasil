# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Objeto de valor: para qual SEFAZ, em qual ambiente, com qual TLS já preparado.

`uf`/`ambiente`/sessão HTTP/arquivo de certificado/arquivo de chave sempre viajam juntos
entre `autorizacao_sefaz.py`, `eventos_sefaz.py` e `inutilizacao_sefaz.py` — não são
dado de uma chamada específica (isso é `documento`/`chave_acesso`/`evento`), são "com
quem e como estamos falando" durante toda a vida da conexão. Os três módulos repetiam os
mesmos cinco parâmetros soltos; a lista de parâmetros repetida era o próprio sinal de que
faltava este objeto (Fowler, *Replace Parameter List with Object*) — nada aqui é
impedido pelo Frappe, é módulo puro fora de qualquer `Document`.

Imutável (`frozen`): representa um TLS já preparado por `TransporteSefaz` para esta
sessão; trocar qualquer campo depois de criado significaria falar com outra SEFAZ ou
outro ambiente, não ajustar este. `TransporteSefaz` é quem monta — os módulos extraídos
só recebem e usam, nunca constroem um `ContextoSefaz` sozinhos.
"""

from dataclasses import dataclass
from pathlib import Path

__all__ = ["ContextoSefaz"]


@dataclass(frozen=True)
class ContextoSefaz:
	"""`sessao_http` é injetável (padrão `requests.Session()`) pela mesma razão de
	`RepositorioClassificacao`/`Assinador`: testa a orquestração inteira sem rede."""

	uf: str
	ambiente: str
	sessao_http: object
	arquivo_cert: Path
	arquivo_chave: Path
