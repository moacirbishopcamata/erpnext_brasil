# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Bloco 0 do EFD-ICMS/IPI — abertura, identificação e cadastros.

Sem este bloco não existe arquivo EFD: os registros de apuração já implementados
(E110/E210/E310, ver `efd_icms_ipi.py`/`efd_icms_st.py`/`efd_icms_difal.py`) são o
conteúdo, e o Bloco 0 é quem identifica a entidade, o período, o perfil e os cadastros
que os demais blocos referenciam por código (participante, unidade, item).

Registros cobertos: `0000` (abertura/identificação), `0001` (abertura do bloco),
`0150` (participantes), `0190` (unidades de medida), `0200` (itens) e `0990`
(encerramento).

Achado real: `IND_MOV` do `0001` é o **inverso** do `IND_MOV_ST` do `E210`
--------------------------------------------------------------------------------------
Mesmo prefixo de nome, semântica oposta — o tipo de detalhe que produz um arquivo
aceito pelo validador e errado no conteúdo:

| Campo | `0` significa | `1` significa |
|---|---|---|
| `0001.IND_MOV` (abertura de bloco) | bloco **com** dados | bloco **sem** dados |
| `E210.IND_MOV_ST` (apuração da ST) | **sem** operações | **com** operações |

Por isso `montar_0001` recebe `tem_dados: bool` e faz a conversão, em vez de aceitar a
string crua — a mesma proteção que `ecf_bloco_0.montar_0001` já aplicava ao `IND_DAD`
da ECF (que segue a convenção do `0001`, não a do `E210`).

Achado real: o Guia Prático de 2013 está desatualizado no `0200`
------------------------------------------------------------------------
O layout foi lido do Guia Prático oficial versão 2.0.13 (cópia publicada pela SEFAZ-SP,
PDF baixado e lido localmente com `pdftotext`, não resumido por ferramenta). Conferindo
contra fonte secundária atual antes de implementar, apareceu uma diferença real: o
`0200` ganhou um **13º campo, `CEST`** (Código Especificador da Substituição
Tributária), introduzido na versão 2.0.20 do guia e válido a partir de 01/01/2017 —
posterior ao PDF lido. Implementado com os 13 campos. O `0000` foi conferido do mesmo
jeito e **continua com 15 campos**, sem mudança.

Isso reforça a disciplina já registrada no projeto: fonte oficial não basta se for de
uma versão antiga; cruzar com uma fonte atual é o que pega o campo novo.

Escopo: os seis registros acima, não o bloco inteiro
------------------------------------------------------------
Ficam de fora, deliberadamente, registros que dependem de cadastro que este projeto não
modela ou de regime específico: `0005` (dados complementares — endereço/contato do
declarante), `0100` (contabilista), `0175` (alteração da tabela de participantes),
`0205` (alteração do item), `0206` (código ANP de combustível), `0210` (consumo
específico padronizado), `0220` (fatores de conversão de unidade), `0300`/`0305` (bens
do CIAP), `0400` (natureza da operação), `0450` (informação complementar do documento),
`0460` (observações do lançamento fiscal), `0500` (plano de contas), `0600` (centros de
custo). Cada um é um cadastro próprio; entrar neles sem um consumidor real seria montar
estrutura sem uso — o mesmo critério aplicado aos blocos da ECF.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from decimal import Decimal

from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido

__all__ = [
	"ATIVIDADE_INDUSTRIAL",
	"ATIVIDADE_OUTROS",
	"FINALIDADE_ORIGINAL",
	"FINALIDADE_SUBSTITUTO",
	"PERFIS",
	"TIPOS_ITEM",
	"Identificacao",
	"Item",
	"Participante",
	"montar_0000",
	"montar_0001",
	"montar_0150",
	"montar_0190",
	"montar_0200",
	"montar_0990",
]

FINALIDADE_ORIGINAL = "0"
FINALIDADE_SUBSTITUTO = "1"

_FINALIDADES = frozenset({FINALIDADE_ORIGINAL, FINALIDADE_SUBSTITUTO})

PERFIS = frozenset({"A", "B", "C"})

ATIVIDADE_INDUSTRIAL = "0"
"""`IND_ATIV` = industrial ou equiparado a industrial."""

ATIVIDADE_OUTROS = "1"

_ATIVIDADES = frozenset({ATIVIDADE_INDUSTRIAL, ATIVIDADE_OUTROS})

# Tabela do campo 07 do 0200, transcrita do layout oficial.
TIPOS_ITEM = {
	"00": "Mercadoria para Revenda",
	"01": "Matéria-Prima",
	"02": "Embalagem",
	"03": "Produto em Processo",
	"04": "Produto Acabado",
	"05": "Subproduto",
	"06": "Produto Intermediário",
	"07": "Material de Uso e Consumo",
	"08": "Ativo Imobilizado",
	"09": "Serviços",
	"10": "Outros insumos",
	"99": "Outras",
}


@dataclass(frozen=True)
class Identificacao:
	"""Os dados do registro `0000` — quem escritura, de quando, com qual perfil.

	`cnpj`/`cpf` são mutuamente exclusivos (a entidade é PJ **ou** PF), e o layout
	acrescenta uma regra cruzada real: se o `CPF` for informado, `IND_ATIV` tem de ser
	`1` (Outros) — pessoa física não é estabelecimento industrial para efeito da EFD.
	Ambas são checadas aqui, não deixadas para o validador do Fisco recusar depois.
	"""

	codigo_versao: str
	data_inicial: str
	data_final: str
	nome: str
	uf: str
	inscricao_estadual: str
	codigo_municipio: str
	perfil: str
	atividade: str
	finalidade: str = FINALIDADE_ORIGINAL
	cnpj: str = ""
	cpf: str = ""
	inscricao_municipal: str = ""
	suframa: str = ""

	def __post_init__(self) -> None:
		if self.finalidade not in _FINALIDADES:
			raise EfdInvalido(
				f"COD_FIN deve ser {FINALIDADE_ORIGINAL!r} (original) ou "
				f"{FINALIDADE_SUBSTITUTO!r} (substituto), recebido {self.finalidade!r}"
			)

		if bool(self.cnpj) == bool(self.cpf):
			raise EfdInvalido("informe CNPJ ou CPF da entidade, exatamente um dos dois")

		if self.perfil not in PERFIS:
			raise EfdInvalido(f"IND_PERFIL deve ser um de {sorted(PERFIS)}, recebido {self.perfil!r}")

		if self.atividade not in _ATIVIDADES:
			raise EfdInvalido(
				f"IND_ATIV deve ser {ATIVIDADE_INDUSTRIAL!r} (industrial) ou "
				f"{ATIVIDADE_OUTROS!r} (outros), recebido {self.atividade!r}"
			)

		if self.cpf and self.atividade != ATIVIDADE_OUTROS:
			raise EfdInvalido(
				"entidade identificada por CPF exige IND_ATIV = "
				f"{ATIVIDADE_OUTROS!r} (regra do próprio layout), recebido {self.atividade!r}"
			)

		if len(self.uf) != 2 or not self.uf.isalpha():
			raise EfdInvalido(f"UF deve ter 2 letras, recebido {self.uf!r}")

		if len(self.codigo_municipio) != 7 or not self.codigo_municipio.isdigit():
			raise EfdInvalido(f"COD_MUN deve ter 7 dígitos (tabela IBGE), recebido {self.codigo_municipio!r}")

		if not self.nome:
			raise EfdInvalido("NOME não pode ser vazio")


@dataclass(frozen=True)
class Participante:
	"""Uma linha do `0150` — cliente, fornecedor ou transportador referenciado pelos
	documentos fiscais dos blocos C/D através de `COD_PART`.

	Diferente do `0000`, aqui CNPJ e CPF são os dois "obrigatórios quando houver" — o
	layout não exige um dos dois (há participante estrangeiro, identificado só por
	`COD_PAIS`), então este tipo **não** replica a exclusividade do `Identificacao`.
	Exigir aqui inventaria uma regra que o layout não tem.
	"""

	codigo: str
	nome: str
	codigo_pais: str
	cnpj: str = ""
	cpf: str = ""
	inscricao_estadual: str = ""
	codigo_municipio: str = ""
	suframa: str = ""
	endereco: str = ""
	numero: str = ""
	complemento: str = ""
	bairro: str = ""

	def __post_init__(self) -> None:
		if not self.codigo:
			raise EfdInvalido("COD_PART não pode ser vazio — é a chave que os blocos C/D referenciam")

		if not self.nome:
			raise EfdInvalido("NOME do participante não pode ser vazio")

		if not self.codigo_pais:
			raise EfdInvalido("COD_PAIS não pode ser vazio")

		if self.cnpj and self.cpf:
			raise EfdInvalido("participante não pode ter CNPJ e CPF ao mesmo tempo")


@dataclass(frozen=True)
class Item:
	"""Uma linha do `0200` — o cadastro do item que os documentos fiscais referenciam
	por `COD_ITEM`.

	`cest` é o 13º campo, acrescentado na versão 2.0.20 do Guia Prático e válido a
	partir de 01/01/2017 (ver docstring do módulo). O layout manda **não preencher**
	quando mais de um CEST puder caber no mesmo produto — por isso é opcional aqui, e
	vazio não é erro.
	"""

	codigo: str
	descricao: str
	unidade_inventario: str
	tipo: str
	codigo_barra: str = ""
	codigo_anterior: str = ""
	codigo_ncm: str = ""
	ex_ipi: str = ""
	codigo_genero: str = ""
	codigo_lista_servico: str = ""
	aliquota_icms: Decimal | None = None
	cest: str = ""

	def __post_init__(self) -> None:
		if not self.codigo:
			raise EfdInvalido("COD_ITEM não pode ser vazio")

		if not self.descricao:
			raise EfdInvalido("DESCR_ITEM não pode ser vazio")

		if not self.unidade_inventario:
			raise EfdInvalido("UNID_INV não pode ser vazio — é o que amarra o item ao registro 0190")

		if self.tipo not in TIPOS_ITEM:
			raise EfdInvalido(f"TIPO_ITEM deve ser um de {sorted(TIPOS_ITEM)}, recebido {self.tipo!r}")

		if self.codigo_ncm and (len(self.codigo_ncm) != 8 or not self.codigo_ncm.isdigit()):
			raise EfdInvalido(f"COD_NCM deve ter 8 dígitos quando informado, recebido {self.codigo_ncm!r}")


def montar_0000(identificacao: Identificacao) -> dict:
	"""Campos do registro `0000`, na ordem oficial — 15 campos, um por arquivo."""
	return {
		"REG": "0000",
		"COD_VER": identificacao.codigo_versao,
		"COD_FIN": identificacao.finalidade,
		"DT_INI": identificacao.data_inicial,
		"DT_FIN": identificacao.data_final,
		"NOME": identificacao.nome,
		"CNPJ": identificacao.cnpj,
		"CPF": identificacao.cpf,
		"UF": identificacao.uf.upper(),
		"IE": identificacao.inscricao_estadual,
		"COD_MUN": identificacao.codigo_municipio,
		"IM": identificacao.inscricao_municipal,
		"SUFRAMA": identificacao.suframa,
		"IND_PERFIL": identificacao.perfil,
		"IND_ATIV": identificacao.atividade,
	}


def montar_0001(tem_dados: bool) -> dict:
	"""Abertura do Bloco 0. `IND_MOV` é **invertido** em relação ao `IND_MOV_ST` do
	E210 (ver docstring do módulo) — por isso recebe `bool` e converte aqui."""
	return {"REG": "0001", "IND_MOV": "0" if tem_dados else "1"}


def montar_0150(participante: Participante) -> dict:
	"""Campos do `0150` — 13 campos, vários por arquivo."""
	return {
		"REG": "0150",
		"COD_PART": participante.codigo,
		"NOME": participante.nome,
		"COD_PAIS": participante.codigo_pais,
		"CNPJ": participante.cnpj,
		"CPF": participante.cpf,
		"IE": participante.inscricao_estadual,
		"COD_MUN": participante.codigo_municipio,
		"SUFRAMA": participante.suframa,
		"END": participante.endereco,
		"NUM": participante.numero,
		"COMPL": participante.complemento,
		"BAIRRO": participante.bairro,
	}


def montar_0190(unidade: str, descricao: str) -> dict:
	"""Campos do `0190` — o registro mais simples do bloco: só a unidade e sua
	descrição. O layout exige que a unidade informada aqui exista em ao menos um outro
	registro do arquivo; essa checagem é de montagem do arquivo inteiro, não deste
	registro isolado, e por isso não é feita aqui."""
	if not unidade:
		raise EfdInvalido("UNID não pode ser vazio")

	if not descricao:
		raise EfdInvalido("DESCR da unidade não pode ser vazio")

	return {"REG": "0190", "UNID": unidade, "DESCR": descricao}


def montar_0200(item: Item) -> dict:
	"""Campos do `0200` — 13 campos, incluindo `CEST` (ver docstring do módulo)."""
	return {
		"REG": "0200",
		"COD_ITEM": item.codigo,
		"DESCR_ITEM": item.descricao,
		"COD_BARRA": item.codigo_barra,
		"COD_ANT_ITEM": item.codigo_anterior,
		"UNID_INV": item.unidade_inventario,
		"TIPO_ITEM": item.tipo,
		"COD_NCM": item.codigo_ncm,
		"EX_IPI": item.ex_ipi,
		"COD_GEN": item.codigo_genero,
		"COD_LST": item.codigo_lista_servico,
		"ALIQ_ICMS": item.aliquota_icms,
		"CEST": item.cest,
	}


def montar_0990(quantidade_linhas: int) -> dict:
	"""Encerramento do Bloco 0, com a contagem de linhas do próprio bloco — mesma
	convenção de `ecf_bloco_0.montar_0990`. A contagem **inclui** o próprio `0990`."""
	if quantidade_linhas < 2:
		raise EfdInvalido(
			f"o Bloco 0 tem no mínimo duas linhas (0000/0001 e o próprio 0990), recebido {quantidade_linhas}"
		)

	return {"REG": "0990", "QTD_LIN_0": str(quantidade_linhas)}
