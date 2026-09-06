# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Identificadores da NFS-e nacional: o da DPS (45) e o da própria NFS-e (53).

Primeira peça do bloco NFS-e — ver `docs/nfse-estado.md` para o dimensionamento inteiro e
por que esta foi a fatia escolhida para começar.

Fonte
--------
Esquemas XSD oficiais do Sistema Nacional NFS-e, versão **1.01 de 09/02/2026**, baixados de
`gov.br/nfse` e lidos localmente — `tiposSimples_v1.01.xsd`, tipos `TSIdDPS`, `TSIdNFSe`,
`TSSerieDPS`, `TSNumDPS`, `TSNNFSe` e `TSCodMunIBGE`. Nada aqui vem de blog nem de memória.

⚠️ Isto **não** é a chave de acesso da NF-e
--------------------------------------------------
Parece, e não é. A chave da NF-e tem 44 dígitos, prefixo `NFe`, e o DV calculado por módulo
11. A NFS-e tem **50** dígitos com prefixo `NFS` (53 no total), campos diferentes, e um DV
cujo algoritmo **o XSD não define**. Reaproveitar o cálculo da NF-e aqui seria a analogia
entre documentos irmãos que este projeto já pagou caro para não repetir.

Composição, literal da documentação do XSD
-------------------------------------------------
```text
DPS   "DPS" + Cód.Mun(7) + Tipo Insc.(1) + Insc. Federal(14) + Série(5) + Núm.(15)   = 45
NFS-e "NFS" + Cód.Mun(7) + Amb.Ger(1) + Tipo Insc.(1) + Insc. Federal(14)
                         + Nº NFS-e(13) + AnoMês(4) + Cód.Num(9) + DV(1)             = 53
```

A **inscrição federal ocupa 14 posições nos dois**, e o XSD diz como preencher quando é
CPF: *"CPF completar com 000 à esquerda"*. Não é zero-fill genérico até 14 — é o CPF de 11
dígitos com três zeros na frente, que dá no mesmo número de posições mas por uma regra
declarada, não por coincidência.

⚠️ Achado: o XSD tem um `pattern` que nenhum validador estrito aceitaria
------------------------------------------------------------------------------
`TSSerieDPS` traz `pattern value="^0{0,4}\\d{1,5}$"`. Em XML Schema, **`^` e `$` não são
âncoras**: a expressão já é implicitamente ancorada, e os dois viram **caracteres
literais**. Lido ao pé da letra, esse padrão exigiria uma série escrita como `^00001$`.

Não é estilo do arquivo: em 1843 linhas de `tiposSimples_v1.01.xsd`, é o **único** pattern
com `^` — todos os demais, inclusive o `TSNumDPS` logo ao lado, são escritos sem âncora.
Trata-se, quase certamente, de expressão copiada de uma linguagem de regex que usa âncoras.

Decisão deste módulo: aplicar a intenção (`0{0,4}\\d{1,5}`, ou seja, de 1 a 5 dígitos com
zeros à esquerda admitidos) e **não** os dois caracteres literais. Registrar em vez de
silenciar, porque quem comparar este código com o XSD vai estranhar — e a explicação tem
de estar aqui, não na cabeça de quem escreveu.

O que este módulo **não** faz
-----------------------------------
- **Não calcula o dígito verificador da NFS-e.** O XSD declara a posição do DV e **não
  declara o algoritmo**; nenhuma fonte primária consultada o descreve. Assumir módulo 11
  porque a NF-e usa módulo 11 é exatamente o erro que a nota acima descreve. Enquanto não
  houver fonte, `montar_identificador_nfse` **exige** o DV de quem chama — que o obtém da
  própria NFS-e devolvida pela Sefin.
- **Não valida o código do município** contra a tabela do IBGE (é o `ANEXO_A` oficial,
  ainda não incorporado), nem o CNPJ/CPF em si — para isso já existe
  `fiscal/validators.py`.

Funções puras: nenhuma dependência do Frappe.
"""

import re
from dataclasses import dataclass

__all__ = [
	"PREFIXO_DPS",
	"PREFIXO_NFSE",
	"TAMANHO_DPS",
	"TAMANHO_NFSE",
	"TIPOS_INSCRICAO",
	"IdentificadorInvalido",
	"IdentificadorNfse",
	"ler_identificador_dps",
	"montar_identificador_dps",
	"montar_identificador_nfse",
]

PREFIXO_DPS = "DPS"
PREFIXO_NFSE = "NFS"

TAMANHO_DPS = 42
"""Dígitos do identificador da DPS, sem o prefixo. Com ele, 45 — `TSIdDPS`."""

TAMANHO_NFSE = 50
"""Dígitos do identificador da NFS-e, sem o prefixo. Com ele, 53 — `TSIdNFSe`."""

TIPO_INSCRICAO_CPF = "1"
TIPO_INSCRICAO_CNPJ = "2"

TIPOS_INSCRICAO = (TIPO_INSCRICAO_CPF, TIPO_INSCRICAO_CNPJ)
"""Domínio do campo de 1 posição.

⚠️ Os rótulos **não** vêm do XSD, que declara o campo apenas como um dígito. Vêm do uso
consolidado do leiaute (1 = CPF, 2 = CNPJ) e por isso são tratados aqui como convenção
adotada, não como regra verificada — este módulo confere o **tamanho** da inscrição contra
o tipo informado, que é a parte que o XSD sustenta.
"""

_SERIE = re.compile(r"0{0,4}\d{1,5}\Z")
"""A intenção de `TSSerieDPS`, sem os `^`/`$` literais — ver a nota no topo do módulo."""

_NUMERO_DPS = re.compile(r"[1-9][0-9]{0,14}\Z")
"""`TSNumDPS`: até 15 dígitos. Aplicado ao número **sem** o enchimento posicional."""

_NUMERO_NFSE = re.compile(r"[1-9][0-9]{0,12}\Z")
"""`TSNNFSe`: até 13 dígitos — mais curto que o da DPS. Dois documentos, dois limites."""

_MUNICIPIO = re.compile(r"[0-9]{7}\Z")
"""`TSCodMunIBGE`: exatamente 7 dígitos."""

_TAMANHO_POR_TIPO = {TIPO_INSCRICAO_CPF: 11, TIPO_INSCRICAO_CNPJ: 14}


class IdentificadorInvalido(ValueError):
	"""Dado que produziria um identificador que a Sefin recusa."""

	def __init__(self, mensagem: str, campo: str = ""):
		super().__init__(mensagem)
		self.campo = campo


@dataclass(frozen=True)
class IdentificadorNfse:
	"""Um identificador de DPS decomposto nos campos do leiaute."""

	codigo_municipio: str
	tipo_inscricao: str
	inscricao_federal: str
	serie: str
	numero: str


def _exigir(condicao: bool, mensagem: str, campo: str) -> None:
	if not condicao:
		raise IdentificadorInvalido(mensagem, campo)


def _inscricao_em_14(inscricao: str, tipo_inscricao: str) -> str:
	"""Normaliza a inscrição federal para as 14 posições do identificador.

	O XSD é explícito quanto ao CPF: *"CPF completar com 000 à esquerda"*. Os três zeros não
	são enchimento arbitrário — são a regra declarada, e é por isso que a conferência aqui é
	do **tamanho por tipo**, não de um `rjust(14)` que aceitaria qualquer coisa curta.
	"""
	digitos = re.sub(r"\D", "", inscricao or "")
	esperado = _TAMANHO_POR_TIPO.get(tipo_inscricao)

	_exigir(
		esperado is not None,
		f"tipo de inscrição deve ser um de {TIPOS_INSCRICAO}, recebido {tipo_inscricao!r}",
		"tipo_inscricao",
	)
	_exigir(
		len(digitos) == esperado,
		f"inscrição do tipo {tipo_inscricao} deve ter {esperado} dígitos, recebidos {len(digitos)}",
		"inscricao_federal",
	)

	return digitos.rjust(14, "0")


def _numero_sem_enchimento(numero: str, largura: int, padrao: re.Pattern, rotulo: str) -> str:
	"""Tira os zeros de enchimento posicional e confere o número contra o leiaute.

	Existe por causa de um ciclo que não fechava: `ler_identificador_dps` devolve os campos
	**como estão no identificador** — posicionais, com zeros à esquerda —, e remontar a
	partir deles falhava, porque `TSNumDPS` recusa número começado em zero. Montar → ler →
	montar tem de dar no mesmo identificador; se não dá, um dos dois lados mente.

	A leitura certa é que os zeros à esquerda são **enchimento da posição**, não parte do
	número: o `nDPS` do XML é `[1-9][0-9]{0,14}`, e o identificador o carrega preenchido até
	a largura. Tirá-los antes de validar é reconhecer isso — a mesma disciplina de
	`chave_acesso.montar_chave`, que normaliza porque planilha e banco comem zeros.

	O que **não** se aceita é um número que seja só zeros: ali não há enchimento a tirar, e
	o documento não teria número nenhum.
	"""
	digitos = (numero or "").strip()

	_exigir(digitos.isdigit(), f"{rotulo} deve conter apenas dígitos, recebido {numero!r}", "numero")

	essencial = digitos.lstrip("0")

	_exigir(bool(essencial), f"{rotulo} não pode ser zero", "numero")
	_exigir(
		bool(padrao.fullmatch(essencial)),
		f"{rotulo} admite de 1 a {largura} dígitos, recebido {numero!r}",
		"numero",
	)

	return essencial.rjust(largura, "0")


def montar_identificador_dps(
	codigo_municipio: str,
	tipo_inscricao: str,
	inscricao_federal: str,
	serie: str,
	numero: str,
) -> str:
	"""Monta o `Id` da DPS — o valor do atributo `Id` de `infDPS`, com o prefixo `DPS`.

	Série e número são normalizados com zeros à esquerda para as larguras do leiaute (5 e
	15). Zeros à esquerda são a causa mais comum de identificador recusado, porque planilha
	e banco os removem — mesma razão de `chave_acesso.montar_chave` normalizar.
	"""
	_exigir(
		bool(_MUNICIPIO.fullmatch(codigo_municipio or "")),
		f"código do município deve ter 7 dígitos, recebido {codigo_municipio!r}",
		"codigo_municipio",
	)

	inscricao = _inscricao_em_14(inscricao_federal, tipo_inscricao)

	serie_limpa = (serie or "").strip()
	_exigir(
		bool(_SERIE.fullmatch(serie_limpa)),
		f"série da DPS admite de 1 a 5 dígitos, recebida {serie!r}",
		"serie",
	)

	numero_posicional = _numero_sem_enchimento(numero, 15, _NUMERO_DPS, "número da DPS")

	corpo = f"{codigo_municipio}{tipo_inscricao}{inscricao}{serie_limpa.rjust(5, '0')}{numero_posicional}"

	# Pós-condição: o leiaute é posicional, e um campo fora de largura desloca todos os
	# seguintes sem que nada mais acuse. Falhar aqui é falhar antes de transmitir.
	_exigir(
		len(corpo) == TAMANHO_DPS,
		f"identificador montado com {len(corpo)} dígitos, esperados {TAMANHO_DPS}",
		"",
	)

	return f"{PREFIXO_DPS}{corpo}"


def montar_identificador_nfse(
	codigo_municipio: str,
	ambiente_gerador: str,
	tipo_inscricao: str,
	inscricao_federal: str,
	numero: str,
	ano_mes: str,
	codigo_numerico: str,
	digito_verificador: str,
) -> str:
	"""Monta o `Id` da NFS-e, com o prefixo `NFS`.

	    ⚠️ **O dígito verificador é exigido, não calculado.** O XSD declara a posição e não o
	    algoritmo, e nenhuma fonte primária consultada o descreve — ver a docstring do módulo.
	    Quem chama o obtém da NFS-e devolvida pela Sefin.

	Serve, portanto, para **remontar e conferir** um identificador recebido, não para
	inventar um: quem gera NFS-e é a Sefin, não o contribuinte.
	"""
	_exigir(
		bool(_MUNICIPIO.fullmatch(codigo_municipio or "")),
		f"código do município deve ter 7 dígitos, recebido {codigo_municipio!r}",
		"codigo_municipio",
	)
	_exigir(
		len(ambiente_gerador or "") == 1 and ambiente_gerador.isdigit(),
		f"ambiente gerador deve ter 1 dígito, recebido {ambiente_gerador!r}",
		"ambiente_gerador",
	)

	inscricao = _inscricao_em_14(inscricao_federal, tipo_inscricao)

	numero_posicional = _numero_sem_enchimento(numero, 13, _NUMERO_NFSE, "número da NFS-e")

	_exigir(
		len(ano_mes or "") == 4 and ano_mes.isdigit(),
		f"ano/mês deve ter 4 dígitos (AAMM), recebido {ano_mes!r}",
		"ano_mes",
	)
	_exigir(
		len(codigo_numerico or "") == 9 and codigo_numerico.isdigit(),
		f"código numérico deve ter 9 dígitos, recebido {codigo_numerico!r}",
		"codigo_numerico",
	)
	_exigir(
		len(digito_verificador or "") == 1 and digito_verificador.isdigit(),
		f"dígito verificador deve ter 1 dígito, recebido {digito_verificador!r}",
		"digito_verificador",
	)

	corpo = (
		f"{codigo_municipio}{ambiente_gerador}{tipo_inscricao}{inscricao}"
		f"{numero_posicional}{ano_mes}{codigo_numerico}{digito_verificador}"
	)

	_exigir(
		len(corpo) == TAMANHO_NFSE,
		f"identificador montado com {len(corpo)} dígitos, esperados {TAMANHO_NFSE}",
		"",
	)

	return f"{PREFIXO_NFSE}{corpo}"


def ler_identificador_dps(identificador: str) -> IdentificadorNfse:
	"""Decompõe um `Id` de DPS nos campos do leiaute.

	Aceita com ou sem o prefixo `DPS`: quem lê um XML recebe com prefixo, quem lê um
	relatório costuma receber sem.
	"""
	texto = (identificador or "").strip().upper()
	corpo = texto.removeprefix(PREFIXO_DPS)

	_exigir(
		len(corpo) == TAMANHO_DPS and corpo.isdigit(),
		f"identificador de DPS deve ter {TAMANHO_DPS} dígitos, recebido {identificador!r}",
		"identificador",
	)

	return IdentificadorNfse(
		codigo_municipio=corpo[0:7],
		tipo_inscricao=corpo[7:8],
		inscricao_federal=corpo[8:22],
		serie=corpo[22:27],
		numero=corpo[27:42],
	)
