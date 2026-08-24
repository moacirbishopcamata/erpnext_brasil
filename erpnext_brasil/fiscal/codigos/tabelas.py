# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Tabelas normativas de códigos fiscais brasileiros.

O que está aqui e o que não está
--------------------------------
Só entram as tabelas **pequenas e estáveis**, fixadas pelo Manual de Orientação do
Contribuinte da NF-e e pelos leiautes da EFD: origem da mercadoria, CST de ICMS, CSOSN,
CST de IPI e CST de PIS/COFINS. São dezenas de entradas cada, mudam raramente, e
embarcá-las evita que todo mundo redigite as mesmas listas.

**NCM, CFOP e a lista de serviços da LC 116 ficam de fora de propósito.** NCM tem cerca
de dez mil posições e é atualizada pela Camex várias vezes por ano; CFOP passa de
seiscentos códigos. Uma cópia embarcada dessas tabelas envelhece em silêncio — o app
seguiria afirmando que um NCM extinto é válido. Para elas o caminho é importar da fonte
oficial, em `importar.py`, que é também o desenho que o próprio ERPNext adota ao aceitar
genericode em vez de embutir listas.

Estas estruturas são dados puros: nenhuma dependência do Frappe, testáveis sem bench.
"""

__all__ = ["TABELAS", "Tabela", "opcoes_select"]

from dataclasses import dataclass


@dataclass(frozen=True)
class Tabela:
	"""Uma tabela de códigos pronta para virar um Code List.

	`nome` é o identificador do Code List (o DocType usa autoname "prompt", então o
	nome é escolhido por nós e precisa ser estável entre versões — mudá-lo criaria
	uma lista nova em vez de atualizar a existente).
	"""

	nome: str
	titulo: str
	descricao: str
	publicador: str
	codigos: dict[str, str]


ORIGEM_MERCADORIA = Tabela(
	nome="Origem da Mercadoria",
	titulo="Origem da Mercadoria (NF-e, Tabela A)",
	descricao="Origem da mercadoria ou serviço; compõe o CST de ICMS junto com a tributação.",
	publicador="ENCAT / Manual de Orientação do Contribuinte",
	codigos={
		"0": "Nacional, exceto as indicadas nos códigos 3, 4, 5 e 8",
		"1": "Estrangeira - Importação direta, exceto a indicada no código 6",
		"2": "Estrangeira - Adquirida no mercado interno, exceto a indicada no código 7",
		"3": "Nacional, mercadoria ou bem com conteúdo de importação superior a 40% e igual ou inferior a 70%",
		"4": "Nacional, cuja produção tenha sido feita em conformidade com os processos produtivos básicos",
		"5": "Nacional, mercadoria ou bem com conteúdo de importação inferior ou igual a 40%",
		"6": "Estrangeira - Importação direta, sem similar nacional, constante em lista da CAMEX",
		"7": "Estrangeira - Adquirida no mercado interno, sem similar nacional, constante em lista da CAMEX",
		"8": "Nacional, mercadoria ou bem com conteúdo de importação superior a 70%",
	},
)

CST_ICMS = Tabela(
	nome="CST ICMS",
	titulo="Código de Situação Tributária do ICMS (NF-e, Tabela B)",
	descricao="Tributação pelo ICMS. Usado por empresas do Regime Normal; o Simples Nacional usa CSOSN.",
	publicador="ENCAT / Manual de Orientação do Contribuinte",
	codigos={
		"00": "Tributada integralmente",
		"10": "Tributada e com cobrança do ICMS por substituição tributária",
		"20": "Com redução de base de cálculo",
		"30": "Isenta ou não tributada e com cobrança do ICMS por substituição tributária",
		"40": "Isenta",
		"41": "Não tributada",
		"50": "Suspensão",
		"51": "Diferimento",
		"60": "ICMS cobrado anteriormente por substituição tributária",
		"70": "Com redução de base de cálculo e cobrança do ICMS por substituição tributária",
		"90": "Outras",
	},
)

CSOSN = Tabela(
	nome="CSOSN",
	titulo="Código de Situação da Operação no Simples Nacional",
	descricao="Substitui o CST de ICMS nas empresas optantes pelo Simples Nacional (CRT 1 e 2).",
	publicador="ENCAT / Manual de Orientação do Contribuinte",
	codigos={
		"101": "Tributada pelo Simples Nacional com permissão de crédito",
		"102": "Tributada pelo Simples Nacional sem permissão de crédito",
		"103": "Isenção do ICMS no Simples Nacional para faixa de receita bruta",
		"201": "Tributada pelo Simples Nacional com permissão de crédito e com cobrança do ICMS por substituição tributária",
		"202": "Tributada pelo Simples Nacional sem permissão de crédito e com cobrança do ICMS por substituição tributária",
		"203": "Isenção do ICMS no Simples Nacional para faixa de receita bruta e com cobrança do ICMS por substituição tributária",
		"300": "Imune",
		"400": "Não tributada pelo Simples Nacional",
		"500": "ICMS cobrado anteriormente por substituição tributária ou por antecipação",
		"900": "Outros",
	},
)

CST_IPI = Tabela(
	nome="CST IPI",
	titulo="Código de Situação Tributária do IPI",
	descricao="Códigos 00 a 49 aplicam-se a entradas; 50 a 99, a saídas.",
	publicador="Receita Federal / Leiaute da NF-e",
	codigos={
		"00": "Entrada com recuperação de crédito",
		"01": "Entrada tributada com alíquota zero",
		"02": "Entrada isenta",
		"03": "Entrada não tributada",
		"04": "Entrada imune",
		"05": "Entrada com suspensão",
		"49": "Outras entradas",
		"50": "Saída tributada",
		"51": "Saída tributada com alíquota zero",
		"52": "Saída isenta",
		"53": "Saída não tributada",
		"54": "Saída imune",
		"55": "Saída com suspensão",
		"99": "Outras saídas",
	},
)

CST_PIS_COFINS = Tabela(
	nome="CST PIS COFINS",
	titulo="Código de Situação Tributária do PIS e da COFINS",
	descricao="Tabelas 4.3.3 e 4.3.4 da EFD-Contribuições; a mesma lista serve às duas contribuições.",
	publicador="Receita Federal / EFD-Contribuições",
	codigos={
		"01": "Operação tributável com alíquota básica",
		"02": "Operação tributável com alíquota diferenciada",
		"03": "Operação tributável com alíquota por unidade de medida de produto",
		"04": "Operação tributável monofásica - revenda a alíquota zero",
		"05": "Operação tributável por substituição tributária",
		"06": "Operação tributável a alíquota zero",
		"07": "Operação isenta da contribuição",
		"08": "Operação sem incidência da contribuição",
		"09": "Operação com suspensão da contribuição",
		"49": "Outras operações de saída",
		"50": "Operação com direito a crédito - vinculada exclusivamente a receita tributada no mercado interno",
		"51": "Operação com direito a crédito - vinculada exclusivamente a receita não tributada no mercado interno",
		"52": "Operação com direito a crédito - vinculada exclusivamente a receita de exportação",
		"53": "Operação com direito a crédito - vinculada a receitas tributadas e não tributadas no mercado interno",
		"54": "Operação com direito a crédito - vinculada a receitas tributadas no mercado interno e de exportação",
		"55": "Operação com direito a crédito - vinculada a receitas não tributadas no mercado interno e de exportação",
		"56": "Operação com direito a crédito - vinculada a receitas tributadas e não tributadas no mercado interno e de exportação",
		"60": "Crédito presumido - aquisição vinculada exclusivamente a receita tributada no mercado interno",
		"61": "Crédito presumido - aquisição vinculada exclusivamente a receita não tributada no mercado interno",
		"62": "Crédito presumido - aquisição vinculada exclusivamente a receita de exportação",
		"63": "Crédito presumido - aquisição vinculada a receitas tributadas e não tributadas no mercado interno",
		"64": "Crédito presumido - aquisição vinculada a receitas tributadas no mercado interno e de exportação",
		"65": "Crédito presumido - aquisição vinculada a receitas não tributadas no mercado interno e de exportação",
		"66": "Crédito presumido - aquisição vinculada a receitas tributadas e não tributadas no mercado interno e de exportação",
		"67": "Crédito presumido - outras operações",
		"70": "Operação de aquisição sem direito a crédito",
		"71": "Operação de aquisição com isenção",
		"72": "Operação de aquisição com suspensão",
		"73": "Operação de aquisição a alíquota zero",
		"74": "Operação de aquisição sem incidência da contribuição",
		"75": "Operação de aquisição por substituição tributária",
		"98": "Outras operações de entrada",
		"99": "Outras operações",
	},
)

TABELAS: tuple[Tabela, ...] = (
	ORIGEM_MERCADORIA,
	CST_ICMS,
	CSOSN,
	CST_IPI,
	CST_PIS_COFINS,
)


def opcoes_select(tabela: Tabela) -> str:
	"""Renderiza a tabela como `options` de um campo Select do Frappe.

	Existe para que um campo Select e o Code List correspondente nunca divirjam: os
	dois saem da mesma fonte. A primeira linha em branco preserva o comportamento do
	Frappe de permitir valor vazio.
	"""
	return "\n".join(["", *(f"{codigo} - {titulo}" for codigo, titulo in tabela.codigos.items())])
