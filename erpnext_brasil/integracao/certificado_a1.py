# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Lê o certificado A1 e o ambiente SEFAZ configurados na `Company`, para alimentar
`integracao.transporte_sefaz.TransporteSefaz`.

Por que existe — pedido direto do usuário: "certificados tipo A1 devem ser configuráveis"
------------------------------------------------------------------------------------------
`TransporteSefaz.__init__` já aceita o certificado como bytes crus (`pfx: bytes`) e a
senha como texto — nunca exigiu caminho de arquivo (`_preparar_arquivos_tls` escreve os
PEM derivados num diretório temporário só depois de já ter o certificado em memória).
O que faltava era o lado do ERPNext: de onde esses bytes/senha vêm. Antes deste módulo,
não existia nenhum jeito de configurar isso pela interface — quem quisesse transmitir de
verdade precisaria escrever código Python passando o `.pfx` na mão.

Os campos (`setup/custom_fields.py`, `Company`): `br_certificado_a1` (`Attach`, o arquivo
`.pfx`/`.p12`), `br_senha_certificado_a1` (`Password`, criptografada pelo próprio Frappe
— nunca em texto puro no banco), `br_ambiente_sefaz` (`Select`, "Produção"/"Homologação",
**padrão "Homologação"** — nunca produção por padrão de fábrica, para não arriscar
transmitir de verdade por engano).

Por que não existe um lugar melhor que `Company` para isso
------------------------------------------------------------------------------
O certificado A1 é emitido **por CNPJ** — é literalmente a identidade digital daquele
CNPJ perante a Receita/SEFAZ. `Company` já é o cadastro que carrega o CNPJ (`tax_id`) e o
resto dos dados fiscais deste app (`regime_tributario`, `inscricao_estadual`, `chave_pix`)
— colocar o certificado num doctype de configuração separado duplicaria a amarração
"qual CNPJ" que `Company` já resolve sozinho, sem ganho nenhum.

Outras "chaves"/URLs de terceiro — deliberadamente **não** movidas para configurações
------------------------------------------------------------------------------------------
Levantamento feito antes de implementar (não suposto): os únicos outros dados externos
hardcoded no projeto são as **tabelas de autorizador por UF**
(`fiscal/documento/autorizadores_sefaz.py`/`autorizadores_cte.py`/`autorizadores_mdfe.py`)
— URLs oficiais do SEFAZ de cada UF, lidas do Portal Nacional/`nfephp-org` e verificadas
campo a campo. Essas **não** viram campo configurável: são infraestrutura fixa definida
pelo governo, não um segredo do usuário — torná-las editáveis pela UI trocaria uma tabela
verificada por um campo de texto livre que um erro de digitação deixaria enviando
declaração fiscal para lugar nenhum, sem ganho nenhum de flexibilidade real (a UF de cada
`Company`/documento já decide automaticamente qual endpoint usar). Nenhuma outra chave de
API, token ou URL de validação de terceiro foi encontrada hardcoded no projeto.

Sem teste dedicado — depende do Frappe (mesma disciplina de `integracao/party.py`)
------------------------------------------------------------------------------------------
Ler `Attach`/`Password` e decidir ambiente exige `frappe.get_doc`/`get_password`, que só
funcionam dentro de um site real — não testável sem bench, mesmo padrão já aplicado a
todo o resto de `integracao/`.
"""

import frappe

__all__ = ["CertificadoA1Ausente", "ambiente_sefaz_da_empresa", "carregar_certificado_da_empresa"]


class CertificadoA1Ausente(ValueError):
	"""A `Company` não tem certificado A1 configurado (arquivo ou senha faltando)."""


def carregar_certificado_da_empresa(company: str) -> tuple[bytes, str]:
	"""Devolve `(pfx_bytes, senha)` prontos para `TransporteSefaz(pfx, senha, ...)`.

	Levanta `CertificadoA1Ausente` (nunca devolve certificado parcial) quando falta o
	arquivo, a senha, ou os dois — falhar alto aqui é melhor que `TransporteSefaz`
	tentar abrir um PKCS#12 vazio e devolver um erro de criptografia sem contexto.
	"""
	empresa = frappe.get_doc("Company", company)

	if not empresa.get("br_certificado_a1"):
		raise CertificadoA1Ausente(
			f"Company {company!r} não tem certificado A1 anexado (campo br_certificado_a1)"
		)

	senha = empresa.get_password("br_senha_certificado_a1", raise_exception=False)

	if not senha:
		raise CertificadoA1Ausente(
			f"Company {company!r} tem certificado A1 anexado, mas não tem a senha configurada "
			"(campo br_senha_certificado_a1)"
		)

	arquivo = frappe.get_doc(
		"File",
		{
			"file_url": empresa.br_certificado_a1,
			"attached_to_doctype": "Company",
			"attached_to_name": company,
		},
	)

	return _bytes_do_arquivo(arquivo), senha


def _bytes_do_arquivo(arquivo) -> bytes:
	"""Os bytes **crus** do `.pfx` — nunca `File.get_content()`.

	`get_content()` (frappe 16) lê o arquivo e tenta decodificá-lo como texto em
	`FILE_ENCODING_OPTIONS = ("utf-8-sig", "utf-8", "windows-1250", "windows-1252")`; como
	`windows-1250` aceita quase qualquer byte, um PKCS#12 volta como `str` mojibake em vez de
	`bytes`, e o `cryptography` recusa. Achado em `tests_bench/test_certificado_a1.py` rodando
	no site Postgres em 2026-09-17 (`'…˙' != b'…\xff'`) — o defeito é do lado do arquivo,
	não do banco, e valeria igual em MariaDB. Um certificado é binário por definição: lê-se em
	`rb` pelo caminho que o próprio `File` resolve.
	"""
	with open(arquivo.get_full_path(), "rb") as conteudo:
		return conteudo.read()


def ambiente_sefaz_da_empresa(company: str) -> str:
	"""Devolve `"producao"` ou `"homologacao"` (valores que `TransporteSefaz`/
	`autorizadores_*.endpoint` esperam), lendo `br_ambiente_sefaz` da `Company`.

	Sem valor configurado, ou qualquer valor diferente de `"Produção"`, resolve para
	`"homologacao"` — o padrão seguro (ver docstring do módulo: nunca produção por
	omissão)."""
	valor = frappe.db.get_value("Company", company, "br_ambiente_sefaz")

	return "producao" if valor == "Produção" else "homologacao"
