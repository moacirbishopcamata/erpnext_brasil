# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Compatibilidade entre CST, cClassTrib e os grupos do XML.

O problema
----------
CST e cClassTrib não são campos independentes: cada cClassTrib **pertence** a um CST, e
cada CST determina estritamente quais grupos do XML podem aparecer no item. A legenda da
tabela oficial é binária — **0 = não é permitido, 1 = exige** —, então informar um grupo
a mais é tão inválido quanto omitir um obrigatório.

Nada disso é derivável do cálculo: são combinações de cadastro. E o custo de errar não é
imposto errado, é **documento rejeitado** — a nota simplesmente não existe. Barrar no
salvamento, com mensagem que diz o que fazer, é muito mais barato que descobrir na
transmissão.

Também se valida a **aplicabilidade por documento**: dos 164 cClassTrib da tabela, só 96
valem para NF-e. Usar um de NFS-e numa NF-e é rejeição garantida.

Funções puras: recebem os registros já lidos e devolvem problemas. Nenhuma dependência
do Frappe — quem transforma isso em `frappe.throw` é a camada de integração.
"""

from dataclasses import dataclass

from erpnext_brasil.fiscal.codigos.classificacao import (
	ClassificacaoTributaria,
	CstIbsCbs,
	formato_valido_cclasstrib,
	formato_valido_cst,
)
from erpnext_brasil.fiscal.codigos.repositorio import RepositorioClassificacao

__all__ = [
	"GRUPOS_DO_XML",
	"Incompatibilidade",
	"problemas_dos_itens",
	"validar_classificacao",
	"validar_com_repositorio",
	"validar_grupos_informados",
]

# Indicador da tabela oficial -> nome do grupo no XML da NF-e.
GRUPOS_DO_XML = {
	"ind_gIBSCBS": "gIBSCBS",
	"ind_gIBSCBSMono": "gIBSCBSMono",
	"ind_gRed": "gRed",
	"ind_gDif": "gDif",
	"ind_gTransfCred": "gTransfCred",
	"ind_gCredPresIBSZFM": "gCredPresIBSZFM",
	"ind_gAjusteCompet": "gAjusteCompet",
}


@dataclass(frozen=True)
class Incompatibilidade:
	"""Um problema encontrado, com o texto pronto para o usuário.

	Carrega `campo` para que a camada de UI possa apontar onde está o erro, em vez de
	só exibir uma mensagem solta.
	"""

	campo: str
	mensagem: str


def validar_classificacao(
	cst: str,
	cclasstrib: str,
	tabela_cst: dict[str, CstIbsCbs],
	tabela_cclasstrib: dict[str, ClassificacaoTributaria],
	documento: str = "indNFe",
) -> list[Incompatibilidade]:
	"""Confere CST e cClassTrib entre si e contra o tipo de documento.

	Devolve **todos** os problemas encontrados, não só o primeiro: quem está corrigindo
	um cadastro prefere ver a lista inteira a descobrir um erro por vez.

	Tabela vazia não gera falso positivo — se os códigos ainda não foram importados, não
	há como afirmar que a combinação é inválida, e acusar seria pior que silenciar.
	"""
	problemas: list[Incompatibilidade] = []

	if not formato_valido_cst(cst):
		problemas.append(
			Incompatibilidade(
				"cst",
				f"CST do IBS/CBS deve ter 3 dígitos, recebido {cst!r}. "
				"Zero à esquerda costuma se perder em planilha.",
			)
		)

	if not formato_valido_cclasstrib(cclasstrib):
		problemas.append(
			Incompatibilidade(
				"cclasstrib",
				f"cClassTrib deve ter 6 dígitos, recebido {cclasstrib!r}.",
			)
		)

	if problemas:
		return problemas

	if tabela_cst and cst not in tabela_cst:
		problemas.append(
			Incompatibilidade("cst", f"CST {cst} não consta na Tabela de Classificação Tributária.")
		)

	if not tabela_cclasstrib:
		return problemas

	registro = tabela_cclasstrib.get(cclasstrib)

	if registro is None:
		problemas.append(
			Incompatibilidade(
				"cclasstrib",
				f"cClassTrib {cclasstrib} não consta na Tabela de Classificação Tributária. "
				"Importe a versão vigente publicada no Portal da NF-e.",
			)
		)

		return problemas

	if registro.cst and registro.cst != cst:
		problemas.append(
			Incompatibilidade(
				"cclasstrib",
				f"cClassTrib {cclasstrib} pertence ao CST {registro.cst}, mas foi informado "
				f"o CST {cst}. Os dois campos precisam concordar.",
			)
		)

	if registro.documentos and not registro.vale_para(documento):
		aceitos = sorted(nome for nome, valor in registro.documentos.items() if valor == "1")
		onde = ", ".join(aceitos) if aceitos else "nenhum documento"

		problemas.append(
			Incompatibilidade(
				"cclasstrib",
				f"cClassTrib {cclasstrib} não é aceito em {documento}. Vale para: {onde}.",
			)
		)

	return problemas


def validar_com_repositorio(
	cst: str,
	cclasstrib: str,
	repositorio: RepositorioClassificacao,
	documento: str = "indNFe",
) -> list[Incompatibilidade]:
	"""Mesma validação, obtendo as tabelas de um repositório.

	É a forma que a integração usa: a regra depende da **interface**, não de onde os
	códigos moram. Trocar Code List por XLSX ou por cache não toca nesta função.
	"""
	return validar_classificacao(
		cst,
		cclasstrib,
		repositorio.cst(),
		repositorio.classificacoes(),
		documento,
	)


def problemas_dos_itens(
	itens: list[dict],
	repositorio: RepositorioClassificacao,
	documento: str = "indNFe",
) -> list[str]:
	"""Confere os itens de um documento e devolve as mensagens já numeradas.

	Vive na camada pura, e não na integração, porque decidir *quais* itens conferir e
	*como* reportar é regra fiscal — não persistência. Como o idioma-fonte do projeto é
	português, não há tradução a aplicar aqui, e a função fica livre do framework.

	Item sem nenhuma classificação é ignorado de propósito: a obrigatoriedade pertence à
	montagem do documento fiscal, quando já se sabe que ele será transmitido. Exigir aqui
	impediria de salvar um rascunho.
	"""
	mensagens = []

	for indice, linha in enumerate(itens, start=1):
		cst = (linha.get("br_cst_ibs_cbs") or "").strip()
		cclasstrib = (linha.get("br_cclasstrib") or "").strip()

		if not cst and not cclasstrib:
			continue

		numero = linha.get("idx") or indice

		for problema in validar_com_repositorio(cst, cclasstrib, repositorio, documento):
			mensagens.append(f"Item {numero}: {problema.mensagem}")

	return mensagens


def validar_grupos_informados(
	cst: str,
	grupos_informados: set[str],
	tabela_cst: dict[str, CstIbsCbs],
) -> list[Incompatibilidade]:
	"""Confere os grupos do XML contra o que o CST admite.

	A legenda oficial é binária: 0 é **vedado**, 1 é **exigido**. Não existe estado
	opcional, então tanto o grupo faltando quanto o grupo sobrando são erro — e o
	segundo é o que se comete "por segurança", informando o que não foi pedido.
	"""
	registro = tabela_cst.get(cst)

	if registro is None or not registro.indicadores:
		return []

	problemas: list[Incompatibilidade] = []

	for indicador, grupo in GRUPOS_DO_XML.items():
		if indicador not in registro.indicadores:
			continue

		informado = grupo in grupos_informados

		if registro.exige(indicador) and not informado:
			problemas.append(
				Incompatibilidade(
					"grupos",
					f"O CST {cst} exige o grupo {grupo}, que não foi informado.",
				)
			)
		elif registro.proibe(indicador) and informado:
			problemas.append(
				Incompatibilidade(
					"grupos",
					f"O CST {cst} não permite o grupo {grupo}, que foi informado. "
					"Informar grupo não pedido também é rejeição.",
				)
			)

	return problemas
