# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Aloca o próximo número de documento fiscal com segurança sob concorrência.

Fecha o gap declarado em `emissao_nfe.py`: `br_numero_nfe` era lido pelo mapeador e nada
o alocava. A regra do leiaute está em `fiscal/documento/numeracao.py` (puro, testável sem
bench); aqui fica a parte que depende do banco, que é onde o problema de verdade mora.

Por que um contador próprio, e não `MAX(numero) + 1`
------------------------------------------------------------
`MAX(numero) + 1` parece resolver e é justamente o que quebra sob carga. Dois usuários
emitindo ao mesmo tempo leem o mesmo máximo, somam um e produzem **o mesmo número** — e a
SEFAZ rejeita o segundo por duplicidade, depois de assinar e transmitir. Pior: em
homologação isso passa despercebido até a primeira concorrência real em produção.

Também não serve o `naming_series` do Frappe: ele numera **documentos do ERPNext**, e a
numeração fiscal é de outra natureza — pertence à combinação empresa + modelo + série, não
ao DocType, e um mesmo `Sales Invoice` pode nunca virar NF-e.

A trava é de linha, não de tabela
------------------------------------------
`frappe.db.get_value(..., for_update=True)` emite `SELECT ... FOR UPDATE`, que trava **a
linha daquela série** até o fim da transação. Duas emissões na mesma série serializam; duas
em séries diferentes não esperam uma pela outra.

Isso exige que a alocação aconteça **dentro** da transação que grava o documento — e é por
isso que esta função não faz `commit`. Quem chama é `emissao_nfe`, dentro do request do
Frappe, que já tem transação aberta e faz commit no fim. Um `commit` aqui liberaria a trava
antes do documento existir, reabrindo a janela que a trava fechou.

O número é consumido mesmo se a SEFAZ recusar
-------------------------------------------------------
Rejeição **não** devolve o número à sequência. Isso é regra fiscal, não decisão de
implementação: a numeração é sequencial e a lacuna se justifica por inutilização de faixa
(`fiscal/documento/inutilizacao.py`), nunca reaproveitando o número. Devolver o número ao
contador produziria duas notas com o mesmo `nNF` no histórico — uma rejeitada, outra
autorizada — e é assim que se perde a rastreabilidade da série.

Estado de verificação: camada Frappe, **não** exercitada contra bench real.
"""

import frappe

from erpnext_brasil.fiscal.documento.numeracao import (
	NumeracaoInvalida,
	primeiro_numero,
	proximo_numero,
	validar_serie,
)

__all__ = ["DOCTYPE", "alocar_numero", "numero_do_documento", "ultimo_numero"]

DOCTYPE = "Numeracao Fiscal"


def _nome(company: str, modelo: str, serie: str) -> str:
	"""A chave da linha — a mesma expressão do `autoname` do DocType."""
	return f"{company}-{modelo}-{serie}"


def ultimo_numero(company: str, modelo: str, serie: str) -> int:
	"""O último número alocado, ou `0` quando a série ainda não emitiu nada.

	Leitura sem trava: serve para exibir, nunca para decidir o próximo — quem decide é
	`alocar_numero`, e ler aqui para somar um lá fora recriaria exatamente a corrida que
	este módulo existe para evitar.
	"""
	nome = _nome(company, modelo, validar_serie(serie))

	return frappe.db.get_value(DOCTYPE, nome, "ultimo_numero") or 0


def alocar_numero(company: str, modelo: str, serie: str) -> str:
	"""Consome e devolve o próximo `nNF` da série, travando a linha do contador.

	Não faz `commit`: a alocação precisa viver na mesma transação que grava o documento —
	ver docstring do módulo.
	"""
	serie = validar_serie(serie)
	nome = _nome(company, modelo, serie)

	atual = frappe.db.get_value(DOCTYPE, nome, "ultimo_numero", for_update=True)

	if atual is None:
		return _abrir_serie(company, modelo, serie, nome)

	numero = proximo_numero(atual) if atual else primeiro_numero()

	frappe.db.set_value(
		DOCTYPE,
		nome,
		{"ultimo_numero": int(numero), "alocado_em": frappe.utils.now()},
		update_modified=False,
	)

	return numero


def _abrir_serie(company: str, modelo: str, serie: str, nome: str) -> str:
	"""Cria o contador na primeira emissão da série.

	A criação pode correr com outra igual: duas emissões simultâneas numa série nova
	tentam inserir a mesma linha, e uma delas perde com erro de chave duplicada. Nesse
	caso a linha **passou a existir**, então basta alocar de novo — agora pelo caminho
	normal, que trava. Recursão de um nível só, não laço de retentativa.
	"""
	documento = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"company": company,
			"modelo": modelo,
			"serie": serie,
			"ultimo_numero": int(primeiro_numero()),
			"alocado_em": frappe.utils.now(),
		}
	)

	try:
		documento.insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		return alocar_numero(company, modelo, serie)

	return primeiro_numero()


def numero_do_documento(doc, modelo: str, serie: str, campo: str = "br_numero_nfe") -> str:
	"""O número do documento (`nNF`, `nCT`...): o já alocado, ou um novo.

	Reemitir um documento que já tem número **não** consome outro. O número pertence ao
	documento desde a primeira tentativa, inclusive quando a SEFAZ recusou — ver docstring
	do módulo sobre por que rejeição não devolve o número.

	`campo` é onde o documento guarda o número: `br_numero_nfe` por padrão (NF-e e NFC-e, que é
	o que existia), `br_numero_cte` para o CT-e. A série e o modelo escolhem o contador; o campo
	só diz onde o resultado fica — por isso é parâmetro, e não uma segunda função copiada.
	"""
	existente = (doc.get(campo) or "").strip()

	if existente:
		try:
			from erpnext_brasil.fiscal.documento.numeracao import validar_numero

			return validar_numero(existente)
		except NumeracaoInvalida as erro:
			frappe.throw(
				f"O documento {doc.name} tem um número inválido gravado em {campo}: {erro}",
				title="Número inválido",
			)

	numero = alocar_numero(doc.company, modelo, serie)
	doc.db_set(campo, numero, update_modified=False)

	return numero
