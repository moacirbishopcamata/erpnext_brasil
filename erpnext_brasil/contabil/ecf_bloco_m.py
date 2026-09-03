# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""ECF: Bloco M (e-LALUR e e-LACS, Parte A e B) — abertura/encerramento apenas.

Ver `docs/ecf-blocos-l-m-n.md` para o dimensionamento completo. Resumo do achado que
limitou este incremento a só abertura/encerramento: o Bloco M inteiro (treze
registros, `M010` a `M510`) implementa o mecanismo de **controle de Parte B do
LALUR/LACS** — contas de controle fiscal que carregam diferença entre resultado
contábil e tributável de um período para o outro (adições/exclusões temporárias,
compensação de prejuízo fiscal, tributação diferida com `IND_LAN_ANT`). Este projeto
**não tem, em lugar nenhum, esse conceito** — nenhuma "conta de controle fiscal" com
saldo que atravessa períodos e se concilia com lançamentos contábeis específicos
(`M310`/`M360` ligam entradas do LALUR a lançamentos reais via `NUM_LCTO`/`COD_CTA`).
Implementar qualquer registro de conteúdo do Bloco M exigiria desenhar esse domínio do
zero — não é uma fatia de reuso de algo que já existe, como foi possível para os
Blocos J/K.

Funções puras: nenhuma dependência do Frappe.

Fonte: `documentacao.senior.com.br/goup/5.10.3/menu_controladoria/sped/contabil-fiscal-ecf/
bloco-m.htm`, consultada em 2026-09-03.
"""

__all__ = ["montar_m001", "montar_m990"]


def montar_m001(tem_dados: bool) -> dict:
	"""Monta o registro `M001` — abertura do Bloco M, mesma convenção dos demais blocos."""
	return {"REG": "M001", "IND_DAD": "0" if tem_dados else "1"}


def montar_m990(quantidade_linhas: int) -> dict:
	"""Monta `M990` — encerramento do Bloco M."""
	return {"REG": "M990", "QTD_LIN": str(quantidade_linhas)}
