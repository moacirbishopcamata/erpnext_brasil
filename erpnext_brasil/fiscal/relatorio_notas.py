# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Consulta pura do relatório "Notas por situação e rejeição" (`proposta-de-relatorios.md`).

Recebe as linhas de `Transmissao Fiscal` já lidas (dicionários) e devolve o agrupamento — nenhuma regra fiscal e
nenhum `frappe`: o Script Report lê o banco e chama esta função, que a suíte comum testa sem bench.

Falha alto onde o silêncio daria dado errado: nada é descartado por filtro implícito. Situação ou tipo fora do
conjunto conhecido continua aparecendo (depois dos conhecidos), e a conferência conta o que um relatório de notas
não pode esconder — autorizadas sem chave de acesso.
"""

from collections import defaultdict

__all__ = ["SITUACOES", "autorizadas_sem_chave", "resumir"]

SITUACOES = ("Pendente", "Autorizado", "Rejeitado", "Denegado", "Cancelado")
"""A ordem das opções de `Transmissao Fiscal.situacao`: o relatório lista nesta ordem."""


def _posicao(situacao: str) -> int:
	return SITUACOES.index(situacao) if situacao in SITUACOES else len(SITUACOES)


def resumir(linhas: list[dict]) -> list[dict]:
	"""Agrupa por (tipo, situação, cStat): quantidade, primeira e última ocorrência e a mensagem mais recente.

	Ordem: situação (na ordem de `SITUACOES`, desconhecidas por último), depois quantidade decrescente, depois
	tipo e cStat — determinística, para o relatório não mudar de ordem entre duas leituras do mesmo dado.
	"""
	grupos: dict[tuple[str, str, str], list[dict]] = defaultdict(list)

	for linha in linhas:
		chave = (linha.get("tipo") or "", linha.get("situacao") or "", linha.get("codigo_status") or "")
		grupos[chave].append(linha)

	resumo = []

	for (tipo, situacao, codigo), itens in grupos.items():
		itens = sorted(itens, key=lambda x: str(x.get("creation") or ""))
		resumo.append(
			{
				"tipo": tipo,
				"situacao": situacao,
				"codigo_status": codigo,
				"mensagem": itens[-1].get("mensagem") or "",
				"quantidade": len(itens),
				"primeira": itens[0].get("creation"),
				"ultima": itens[-1].get("creation"),
			}
		)

	return sorted(
		resumo,
		key=lambda r: (_posicao(r["situacao"]), -r["quantidade"], r["tipo"], r["codigo_status"]),
	)


def autorizadas_sem_chave(linhas: list[dict]) -> int:
	"""Autorizações sem `chave_acesso`: o documento diz "autorizado" e não há como consultá-lo na SEFAZ."""
	return sum(
		1
		for linha in linhas
		if linha.get("situacao") == "Autorizado"
		and linha.get("tipo") == "Autorização"
		and not (linha.get("chave_acesso") or "").strip()
	)
