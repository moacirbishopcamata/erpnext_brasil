# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Sugestão da natureza da operação a partir do CFOP já determinado.

Fecha o gap 5.1 de `docs/gaps.md`: `natOp` era obrigatório na montagem da NF-e e do CT-e,
mas **não existia campo nenhum** onde o usuário informasse o valor — e o sistema já sabia
qual era a operação, porque `cfop_sugestao` acabara de decidir o CFOP na mesma gravação.

Módulo separado de `cfop_sugestao.py`, de propósito
-----------------------------------------------------------
Os dois rodam no mesmo `validate` e o segundo consome o resultado do primeiro, o que
convida a juntá-los. São responsabilidades diferentes:

- `cfop_sugestao` escreve em **cada linha** um campo somente leitura, recalculado sempre;
- este escreve **um campo do cabeçalho** que o usuário edita e salva.

A segunda diferença é a que importa e decide o comportamento — ver abaixo.

Aqui a sugestão **não pode** sobrescrever, e em `cfop_sugestao` pode
--------------------------------------------------------------------------------
`br_cfop_sugerido` é read-only: não existe "valor escolhido pelo usuário" naquela coluna,
então recalcular a cada gravação é seguro. `br_natureza_operacao` é editável: o usuário
pode ter escrito a redação que o contador dele exige, ou a do regulamento do estado.

Recalcular por cima disso apagaria trabalho a cada save — silenciosamente, porque
`validate` roda antes de o usuário ver o resultado. Por isso este módulo **só preenche
lacuna**: campo vazio recebe sugestão, campo preenchido fica como está, sempre. É a mesma
regra que vale para qualquer pré-preenchimento a partir de cadastro — histórico manda
sobre cadastro atual, que pode ter mudado desde então.

Por que lê o CFOP da primeira linha
-------------------------------------------
A natureza é **um campo do documento** e o CFOP é **por item**. Documento com itens de
CFOP diferente (venda de produção própria e revenda na mesma nota) não tem uma natureza
única correta, e escolher a de um item seria arbitrário.

A saída: só sugere quando **todas** as linhas concordam no CFOP. Divergiu, não sugere
nada — e o usuário escreve a descrição que cobre a operação inteira, que é justamente o
caso em que o julgamento humano é necessário.

Estado de verificação: não exercitado contra bench real, como o resto de `integracao/`.
"""

from erpnext_brasil.fiscal.natureza_operacao import natureza_do_cfop

__all__ = ["sugerir_natureza_operacao"]


def sugerir_natureza_operacao(doc, method=None):
	"""`doc_event` de `validate`: preenche `br_natureza_operacao` **só quando vazio**."""
	if (doc.get("br_natureza_operacao") or "").strip():
		# O usuário já escreveu algo. Nada aqui pisa nisso — ver docstring do módulo.
		return

	cfops = {
		(linha.get("br_cfop_sugerido") or "").strip()
		for linha in doc.get("items", [])
		if (linha.get("br_cfop_sugerido") or "").strip()
	}

	if len(cfops) != 1:
		# Nenhum CFOP determinado, ou itens de naturezas diferentes na mesma nota: em
		# ambos os casos não há uma descrição única que esteja certa.
		return

	sugestao = natureza_do_cfop(cfops.pop())

	if sugestao:
		doc.br_natureza_operacao = sugestao
