# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Ajudantes das suítes de costura — o que se repetia em quatro arquivos.

Por que existe
--------------------
Asserção de **ausência** é a ferramenta certa para travar uma decisão negativa: "este
módulo não cria itens", "não usa `db_set`", "não herda do transporte da SEFAZ". E ela tem
uma armadilha que já apareceu **quatro vezes** neste projeto:

> a docstring que explica *por que não se faz X* contém a palavra X — e reprova o próprio
> teste que a defende.

O remédio é medir só o que executa. Estava copiado em `test_costura_cliente`,
`test_entrada_nfe` e `test_depreciacao_ativo`; na quarta cópia virou este módulo.

⚠️ **Não é módulo de teste**: não define `TestCase` nenhum. Vive em `tests/` porque é dali
que se usa, e porque não tem serventia para o app em produção.
"""

import ast
import re

__all__ = ["sem_comentarios_js", "sem_docstrings"]


def sem_docstrings(fonte: str) -> str:
	"""O fonte Python sem docstrings, preservando código e mensagens ao usuário.

	Remove **só** expressões-string soltas — que é o que uma docstring é. Uma string
	passada a `_()` ou a `frappe.throw` continua visível, e deve mesmo: ela é parte do
	comportamento, não da explicação.

	Preserva a numeração original das linhas ao apagá-las, para que um trecho medido aqui
	possa ser comparado com o fonte real sem deslocamento.
	"""
	arvore = ast.parse(fonte)
	proibidas: set[int] = set()

	for no in ast.walk(arvore):
		if isinstance(no, ast.Expr) and isinstance(no.value, ast.Constant):
			if isinstance(no.value.value, str):
				proibidas.update(range(no.lineno, (no.end_lineno or no.lineno) + 1))

	return "\n".join(
		linha for numero, linha in enumerate(fonte.splitlines(), start=1) if numero not in proibidas
	)


def sem_comentarios_js(fonte: str) -> str:
	"""O JavaScript sem `//` nem `/* */`.

	Mesma finalidade de `sem_docstrings`, do outro lado da costura: os comentários deste
	projeto citam o que **não** se deve usar, e uma asserção de ausência sobre o texto
	inteiro reprovaria a explicação junto com o erro que ela previne.
	"""
	sem_bloco = re.sub(r"/\*.*?\*/", "", fonte, flags=re.S)

	return re.sub(r"//.*", "", sem_bloco)
