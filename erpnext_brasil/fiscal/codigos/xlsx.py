# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Leitor mínimo de XLSX, sem dependência externa.

Por que não `openpyxl`
----------------------
As tabelas oficiais do Portal da NF-e são publicadas em XLSX, e precisamos lê-las.
Acrescentar `openpyxl` ao app significaria mais uma dependência num bench compartilhado
por vários apps, para um uso pontual: importar uma planilha algumas vezes por ano.

Um XLSX é um ZIP com XML dentro, e a biblioteca padrão já tem `zipfile` e
`ElementTree`. O que segue lê o suficiente para tabelas de códigos: células de texto e
números, resolvendo a tabela de *shared strings*. **Não** interpreta fórmulas, datas,
estilos ou células mescladas — e não deve tentar, porque aí a dependência se justificaria.

Funções puras: nenhuma dependência do Frappe.
"""

import re
import zipfile
from xml.etree import ElementTree

__all__ = ["ler_planilha", "listar_planilhas"]

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_COLUNA = re.compile(r"[A-Z]+")


def listar_planilhas(caminho_ou_arquivo) -> list[str]:
	"""Nomes internos das planilhas, na ordem em que aparecem no pacote."""
	with zipfile.ZipFile(caminho_ou_arquivo) as z:
		return sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))


def _textos_compartilhados(z: zipfile.ZipFile) -> list[str]:
	"""Resolve `sharedStrings.xml`, onde o XLSX guarda o texto das células.

	O texto de uma célula pode vir quebrado em vários `<t>` (quando há formatação
	parcial), por isso a concatenação.
	"""
	if "xl/sharedStrings.xml" not in z.namelist():
		return []

	raiz = ElementTree.fromstring(z.read("xl/sharedStrings.xml"))

	return ["".join(t.text or "" for t in si.iter(_NS + "t")) for si in raiz.iter(_NS + "si")]


def _texto_da_celula(celula, compartilhados: list[str]) -> str:
	valor = celula.find(_NS + "v")

	if valor is not None:
		if celula.get("t") == "s":
			indice = int(valor.text)

			return compartilhados[indice] if indice < len(compartilhados) else ""

		return valor.text or ""

	embutido = celula.find(_NS + "is")

	if embutido is not None:
		return "".join(t.text or "" for t in embutido.iter(_NS + "t"))

	return ""


def ler_planilha(caminho_ou_arquivo, planilha: str = "xl/worksheets/sheet1.xml") -> list[dict]:
	"""Lê uma planilha e devolve uma lista de linhas como {coluna: texto}.

	A chave é a letra da coluna ("A", "B", "AA"), não o cabeçalho: a decisão de qual
	coluna significa o quê fica com quem chama, que é quem conhece o layout do arquivo.
	Linhas totalmente vazias são descartadas.
	"""
	with zipfile.ZipFile(caminho_ou_arquivo) as z:
		compartilhados = _textos_compartilhados(z)
		raiz = ElementTree.fromstring(z.read(planilha))

		linhas = []

		for linha in raiz.iter(_NS + "row"):
			celulas = {}

			for celula in linha.iter(_NS + "c"):
				referencia = celula.get("r") or ""
				correspondencia = _COLUNA.match(referencia)

				if not correspondencia:
					continue

				texto = _texto_da_celula(celula, compartilhados)

				if texto:
					celulas[correspondencia.group(0)] = texto

			if celulas:
				linhas.append(celulas)

		return linhas
