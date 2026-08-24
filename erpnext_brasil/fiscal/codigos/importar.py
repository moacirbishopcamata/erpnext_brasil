# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Importação das tabelas grandes e voláteis (NCM, CFOP, LC 116) a partir da fonte oficial.

Por que não vêm embarcadas
--------------------------
NCM tem cerca de dez mil posições e é alterada pela Camex várias vezes por ano; CFOP
passa de seiscentos códigos. Uma cópia embutida no app envelhece sem avisar — o sistema
continuaria aceitando um NCM extinto, e o erro só apareceria na rejeição da SEFAZ. Por
isso a tabela vem de um arquivo que o usuário baixa da fonte, e o app registra qual
versão foi carregada.

Duas portas de entrada
----------------------
1. **Genericode XML** — já existe no ERPNext (`Code List` tem o importador nativo, com
   mapeamento de colunas). É o caminho preferido quando a fonte publica genericode.
2. **CSV** — implementado aqui, porque as fontes brasileiras publicam CSV/XLSX, não
   genericode. Reaproveita os mesmos DocTypes; não cria estrutura paralela.

A importação é idempotente: reexecutar com o mesmo arquivo não duplica códigos.
"""

import csv
import io

import frappe
from frappe import _

# Acima disso a importação passa a rodar em fila, para não estourar o tempo do request.
LIMITE_SINCRONO = 500


def importar_csv(
	code_list: str,
	conteudo: str | bytes,
	coluna_codigo: str,
	coluna_titulo: str,
	coluna_descricao: str | None = None,
	versao: str | None = None,
	delimitador: str = ";",
) -> dict[str, int]:
	"""Carrega códigos de um CSV para dentro de um Code List.

	O delimitador padrão é ";" porque é o que as fontes oficiais brasileiras usam.
	`versao` fica registrada no Code List — sem isso não há como saber, meses depois,
	qual edição da tabela está em uso.
	"""
	if isinstance(conteudo, bytes):
		conteudo = conteudo.decode("utf-8-sig")

	leitor = csv.DictReader(io.StringIO(conteudo), delimiter=delimitador)

	if not leitor.fieldnames:
		frappe.throw(_("O arquivo não tem cabeçalho legível."), title=_("Importação inválida"))

	faltando = [
		coluna
		for coluna in (coluna_codigo, coluna_titulo, coluna_descricao)
		if coluna and coluna not in leitor.fieldnames
	]

	if faltando:
		frappe.throw(
			_("Colunas não encontradas no arquivo: {0}. Disponíveis: {1}").format(
				", ".join(faltando), ", ".join(leitor.fieldnames)
			),
			title=_("Importação inválida"),
		)

	linhas = [linha for linha in leitor if (linha.get(coluna_codigo) or "").strip()]

	_garantir_code_list(code_list, versao)

	return _gravar(code_list, linhas, coluna_codigo, coluna_titulo, coluna_descricao)


def _garantir_code_list(code_list: str, versao: str | None) -> None:
	if frappe.db.exists("Code List", code_list):
		if not versao or frappe.db.get_value("Code List", code_list, "version") == versao:
			return

		doc = frappe.get_doc("Code List", code_list)
		doc.version = versao
		doc.save(ignore_permissions=True)

		return

	doc = frappe.new_doc("Code List")
	doc.name = code_list  # autoname = "prompt"
	doc.title = code_list
	doc.version = versao
	doc.insert(ignore_permissions=True)


def _gravar(
	code_list: str,
	linhas: list[dict],
	coluna_codigo: str,
	coluna_titulo: str,
	coluna_descricao: str | None,
) -> dict[str, int]:
	"""Insere os códigos ausentes e atualiza os que mudaram de título."""
	existentes = {
		linha.common_code: linha
		for linha in frappe.get_all(
			"Common Code",
			filters={"code_list": code_list},
			fields=["name", "common_code", "title"],
		)
	}

	criados = atualizados = inalterados = 0
	total = len(linhas)

	for indice, linha in enumerate(linhas, start=1):
		codigo = (linha.get(coluna_codigo) or "").strip()
		titulo = (linha.get(coluna_titulo) or "").strip() or codigo
		descricao = (linha.get(coluna_descricao) or "").strip() if coluna_descricao else None

		atual = existentes.get(codigo)

		if atual and atual.title == titulo:
			inalterados += 1
		elif atual:
			doc = frappe.get_doc("Common Code", atual.name)
			doc.title = titulo

			if descricao:
				doc.description = descricao

			doc.save(ignore_permissions=True)
			atualizados += 1
		else:
			doc = frappe.new_doc("Common Code")
			doc.code_list = code_list
			doc.common_code = codigo
			doc.title = titulo
			doc.description = descricao
			doc.insert(ignore_permissions=True)
			criados += 1

		if total > 200 and indice % 100 == 0:
			frappe.publish_progress(indice / total * 100, title=_("Importando códigos"))

	return {
		"total": total,
		"criados": criados,
		"atualizados": atualizados,
		"inalterados": inalterados,
	}


@frappe.whitelist()
def importar_arquivo(
	code_list: str,
	file_url: str,
	coluna_codigo: str,
	coluna_titulo: str,
	coluna_descricao: str | None = None,
	versao: str | None = None,
	delimitador: str = ";",
):
	"""Ponto de entrada a partir de um arquivo já anexado ao site.

	A permissão do arquivo é conferida explicitamente: um `file_url` chega do cliente e
	não pode ser tratado como confiável só por estar dentro do site.
	"""
	frappe.only_for(("System Manager", "Accounts Manager"))

	arquivo = frappe.get_doc("File", {"file_url": file_url})
	arquivo.check_permission("read")

	# Lido uma vez só: NCM completo passa de dez mil linhas, e reler três vezes o
	# arquivo inteiro para contar linhas é desperdício puro.
	conteudo = arquivo.get_content(encodings=("utf-8-sig", "utf-8"))
	linhas_estimadas = conteudo.count("\n")

	argumentos = {
		"code_list": code_list,
		"conteudo": conteudo,
		"coluna_codigo": coluna_codigo,
		"coluna_titulo": coluna_titulo,
		"coluna_descricao": coluna_descricao,
		"versao": versao,
		"delimitador": delimitador,
	}

	if linhas_estimadas > LIMITE_SINCRONO:
		frappe.enqueue(
			"erpnext_brasil.fiscal.codigos.importar.importar_csv",
			queue="long",
			timeout=1800,
			**argumentos,
		)

		return {"enfileirado": True, "linhas_estimadas": linhas_estimadas}

	return importar_csv(**argumentos)
