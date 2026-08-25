# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Tabela de Classificação Tributária do IBS e da CBS (CST e cClassTrib).

Sem esses dois códigos o documento é rejeitado: o XSD os marca como obrigatórios no
grupo `IBSCBS` de cada item. E eles não são deriváveis do cálculo — dependem da natureza
jurídica da operação, que é dado de cadastro.

Fonte
-----
Portal Nacional da NF-e, *Documentos > Diversos*: "Tabela de Classificação Tributária do
IBS e CBS" (XLSX), publicada sob o Informe Técnico 2025.002. O arquivo traz duas
planilhas:

- **sheet1** — os CST do IBS/CBS (cerca de 21), com indicadores de quais grupos do XML
  cada um exige (`ind_gIBSCBS`, `ind_gRed`, `ind_gDif`, …);
- **sheet2** — os cClassTrib (cerca de 164), cada um amarrado a um CST, com percentual de
  redução de IBS e CBS, vigência, e **aplicabilidade por tipo de documento** (`indNFe`,
  `indNFCe`, `indNFSe`, …).

A tabela é versionada e atualizada; por isso ela é **importada**, não embarcada — mesmo
critério do NCM e do CFOP. O que fica no código é a leitura e a validação, não os dados.

Este módulo é puro: recebe as linhas já lidas e devolve registros. A gravação no Frappe
fica em `importar.py`.
"""

import re
from dataclasses import dataclass, field

__all__ = [
	"CST_IBS_CBS",
	"CLASSIFICACAO_TRIBUTARIA",
	"ClassificacaoTributaria",
	"CstIbsCbs",
	"formato_valido_cclasstrib",
	"formato_valido_cst",
	"ler_cclasstrib",
	"ler_cst",
]

# Nomes dos Code List criados a partir desta tabela.
CST_IBS_CBS = "CST IBS CBS"
CLASSIFICACAO_TRIBUTARIA = "cClassTrib"

# Formatos fixados pelo XSD (DFeTiposBasicos_v1.00.xsd): TCST = \d{3}, TcClassTrib = \d{6}.
_CST = re.compile(r"^\d{3}$")
_CCLASSTRIB = re.compile(r"^\d{6}$")


def formato_valido_cst(valor: str | None) -> bool:
	"""CST do IBS/CBS: exatamente três dígitos, conforme o tipo TCST do XSD."""
	return bool(valor and _CST.match(valor))


def formato_valido_cclasstrib(valor: str | None) -> bool:
	"""cClassTrib: exatamente seis dígitos, conforme o tipo TcClassTrib do XSD."""
	return bool(valor and _CCLASSTRIB.match(valor))


@dataclass(frozen=True)
class CstIbsCbs:
	codigo: str
	descricao: str
	indicadores: dict[str, str] = field(default_factory=dict)
	"""Quais grupos do XML este CST admite — `ind_gIBSCBS`, `ind_gRed`, `ind_gDif`, …

	A legenda da planilha oficial é binária e mais forte do que "opcional":
	**0 = não é permitido, 1 = exige**. Não há estado intermediário — o CST determina
	estritamente quais grupos podem aparecer no item, e informar um grupo com indicador
	0 é tão inválido quanto omitir um com indicador 1.
	"""

	def exige(self, grupo: str) -> bool:
		"""Indica se o grupo é exigido por este CST (indicador "1")."""
		return self.indicadores.get(grupo) == "1"

	def proibe(self, grupo: str) -> bool:
		"""Indica se o grupo é vedado por este CST (indicador "0").

		Existe como método próprio porque "não exige" e "é proibido" são a mesma coisa
		nesta tabela, e deixar isso implícito convidaria alguém a informar o grupo
		"por segurança" — produzindo rejeição.
		"""
		return self.indicadores.get(grupo) == "0"


@dataclass(frozen=True)
class ClassificacaoTributaria:
	codigo: str
	cst: str
	nome: str
	descricao: str
	tipo_aliquota: str = ""
	reducao_ibs: str = "0"
	reducao_cbs: str = "0"
	documentos: dict[str, str] = field(default_factory=dict)
	"""Aplicabilidade por documento — `indNFe`, `indNFCe`, `indNFSe`, …"""

	def vale_para(self, documento: str) -> bool:
		"""Indica se o código pode ser usado no tipo de documento (ex.: "indNFe")."""
		return self.documentos.get(documento) == "1"


def _cabecalho(linhas: list[dict]) -> dict[str, str]:
	"""Mapeia título da coluna -> letra, a partir da primeira linha.

	Ler pelo título e não pela posição é deliberado: a Receita acrescenta colunas entre
	versões da tabela, e uma leitura posicional passaria a importar a coluna errada em
	silêncio na próxima publicação.
	"""
	if not linhas:
		raise ValueError("Planilha vazia")

	return {titulo.strip(): coluna for coluna, titulo in linhas[0].items()}


def _campo(linha: dict, colunas: dict[str, str], titulo: str, padrao: str = "") -> str:
	coluna = colunas.get(titulo)

	return (linha.get(coluna, padrao) if coluna else padrao).strip()


def ler_cst(linhas: list[dict]) -> list[CstIbsCbs]:
	"""Interpreta a planilha de CST do IBS/CBS (sheet1)."""
	colunas = _cabecalho(linhas)

	if "CST-IBS/CBS" not in colunas:
		raise ValueError(
			f"Planilha não parece a de CST do IBS/CBS. Colunas encontradas: {sorted(colunas)}"
		)

	indicadores = [titulo for titulo in colunas if titulo.startswith("ind_")]
	registros = []

	for linha in linhas[1:]:
		codigo = _campo(linha, colunas, "CST-IBS/CBS")

		if not formato_valido_cst(codigo):
			continue

		registros.append(
			CstIbsCbs(
				codigo=codigo,
				descricao=_campo(linha, colunas, "Descrição CST-IBS/CBS"),
				indicadores={
					titulo.replace(" ", ""): _campo(linha, colunas, titulo) for titulo in indicadores
				},
			)
		)

	return registros


def ler_cclasstrib(linhas: list[dict]) -> list[ClassificacaoTributaria]:
	"""Interpreta a planilha de cClassTrib (sheet2)."""
	colunas = _cabecalho(linhas)

	if "cClassTrib" not in colunas:
		raise ValueError(
			f"Planilha não parece a de cClassTrib. Colunas encontradas: {sorted(colunas)}"
		)

	documentos = [titulo for titulo in colunas if titulo.startswith("ind") and "NF" in titulo]
	registros = []

	for linha in linhas[1:]:
		codigo = _campo(linha, colunas, "cClassTrib")

		if not formato_valido_cclasstrib(codigo):
			continue

		registros.append(
			ClassificacaoTributaria(
				codigo=codigo,
				cst=_campo(linha, colunas, "CST-IBS/CBS"),
				nome=_campo(linha, colunas, "Nome cClassTrib"),
				descricao=_campo(linha, colunas, "Descrição cClassTrib"),
				tipo_aliquota=_campo(linha, colunas, "Tipo de Alíquota"),
				reducao_ibs=_campo(linha, colunas, "pRedIBS", "0") or "0",
				reducao_cbs=_campo(linha, colunas, "pRedCBS", "0") or "0",
				documentos={
					titulo.replace(" ", ""): _campo(linha, colunas, titulo) for titulo in documentos
				},
			)
		)

	return registros
