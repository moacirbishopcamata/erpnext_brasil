# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""ECF: Bloco 0 (Abertura, Identificação e Referências) — núcleo mínimo.

Por que só o núcleo mínimo, não o Bloco 0 inteiro
------------------------------------------------------------------------------
Confirmado em `documentacao.senior.com.br/.../bloco-0.htm` (mesmo padrão de confiança já
aceito para os Blocos J/K): o Bloco 0 tem oito registros — `0000` (abertura do arquivo),
`0001` (abertura do bloco), `0010`/`0020`/`0021` (parâmetros de tributação — juntos, mais
de 40 indicadores regulatórios: Refis, SCP, operações com o exterior, participação em
consórcios/coligadas, e uma dezena de programas de incentivo fiscal como Repes/Recap/
Padis/Reidi/Recine/Reporto/Repetro), `0030` (dados cadastrais), `0035` (identificação de
SCP), `0930` (identificação dos signatários), `0990` (encerramento).

**Deliberadamente fora deste incremento**: `0010`/`0020`/`0021` — cada um dos seus ~44
indicadores é uma pergunta de sim/não sobre a situação regulatória real da empresa
(é optante do Refis? tem SCP? opera com o exterior? está habilitada num programa de
incentivo específico?). Nenhum desses tem valor padrão seguro — "não" errado é uma
declaração fiscal incorreta tanto quanto "sim" errado, e este projeto não tem, em
lugar nenhum, o cadastro que responderia essas perguntas de verdade. Preencher com
qualquer valor aqui seria inventar dado que este módulo não tem como verificar — pior
que não implementar. `0035` (SCP, Sociedade em Conta de Participação) e `0930`
(signatário/contador com registro CRC) também ficam de fora: nenhum conceito
correspondente existe no projeto ainda.

Implementado: `0000`, `0001`, `0030`, `0990`
------------------------------------------------------------------------------
`0000` e `0030` são identificação — dados que o projeto já tem em `Company`/`Address`
(CNPJ, nome empresarial, CNAE, endereço), não pergunta regulatória de sim/não. Mesmo
assim, **os campos de `0000` que são indicadores/enumerações (`IND_SIT_INI_PER`,
`SIT_ESPECIAL`, `RETIFICADORA`, `TIP_ECF`, `COD_SCP`) não têm seus valores catalogados
aqui** — a fonte lista os nomes dos campos, não o significado de cada código, e este
projeto não tem outro módulo SPED com um campo idêntico para conferir por precedente
interno (achado verificado: `RETIFICADORA`/`TIP_ECF`/`IND_SIT_INI_PER` não aparecem em
nenhum outro módulo `contabil/`). Por isso esses campos são parâmetros de texto livre,
sem enumeração/validação — quem chama informa o valor certo, verificado contra o Manual
de Orientação do Contribuinte da ECF antes de gerar um arquivo real.

Funções puras: nenhuma dependência do Frappe.

Fonte: `documentacao.senior.com.br/goup/5.10.3/menu_controladoria/sped/contabil-fiscal-ecf/
bloco-0.htm`, consultada em 2026-09-03.
"""

from dataclasses import dataclass
from datetime import date

__all__ = ["DadosCadastrais", "IdentificacaoEcf", "montar_0000", "montar_0001", "montar_0030", "montar_0990"]


@dataclass(frozen=True)
class IdentificacaoEcf:
	"""Dados de `0000` — abertura do arquivo e identificação do contribuinte.

	`indicador_situacao_inicio_periodo`, `situacao_especial`, `retificadora`,
	`tipo_ecf` e `codigo_scp` são texto livre, não validados — ver docstring do
	módulo sobre por que este módulo não cataloga o significado de cada código.
	"""

	cnpj: str
	nome_empresarial: str
	data_inicio: date
	data_fim: date
	codigo_versao_leiaute: str
	indicador_situacao_inicio_periodo: str
	tipo_ecf: str
	retificadora: str = "0"
	numero_recibo_anterior: str = ""
	situacao_especial: str = ""
	data_situacao_especial: date | None = None
	patrimonio_remanescente_cisao: str = ""
	codigo_scp: str = ""


@dataclass(frozen=True)
class DadosCadastrais:
	"""Dados de `0030` — cadastro complementar (endereço, CNAE, contato)."""

	natureza_juridica: str
	cnae_fiscal: str
	endereco: str
	numero: str
	bairro: str
	uf: str
	codigo_municipio: str
	cep: str
	complemento: str = ""
	telefone: str = ""
	email: str = ""


def montar_0000(identificacao: IdentificacaoEcf) -> dict:
	"""Monta o registro `0000` — abertura do arquivo digital da ECF."""
	return {
		"REG": "0000",
		"NOME_ESC": "ECF",
		"COD_VER": identificacao.codigo_versao_leiaute,
		"CNPJ": identificacao.cnpj,
		"NOME": identificacao.nome_empresarial,
		"IND_SIT_INI_PER": identificacao.indicador_situacao_inicio_periodo,
		"SIT_ESPECIAL": identificacao.situacao_especial,
		"PAT_REMAN_CIS": identificacao.patrimonio_remanescente_cisao,
		"DT_SIT_ESP": identificacao.data_situacao_especial,
		"DT_INI": identificacao.data_inicio,
		"DT_FIN": identificacao.data_fim,
		"RETIFICADORA": identificacao.retificadora,
		"NUM_REC": identificacao.numero_recibo_anterior,
		"TIP_ECF": identificacao.tipo_ecf,
		"COD_SCP": identificacao.codigo_scp,
	}


def montar_0001(tem_dados: bool) -> dict:
	"""Monta o registro `0001` — abertura do Bloco 0, mesma convenção de
	`ecf_bloco_j.montar_j001`/`ecf_bloco_k.montar_k001`."""
	return {"REG": "0001", "IND_DAD": "0" if tem_dados else "1"}


def montar_0030(dados: DadosCadastrais) -> dict:
	"""Monta o registro `0030` — dados cadastrais complementares."""
	return {
		"REG": "0030",
		"COD_NAT": dados.natureza_juridica,
		"CNAE_FISCAL": dados.cnae_fiscal,
		"ENDERECO": dados.endereco,
		"NUM": dados.numero,
		"COMPL": dados.complemento,
		"BAIRRO": dados.bairro,
		"UF": dados.uf,
		"COD_MUN": dados.codigo_municipio,
		"CEP": dados.cep,
		"NUM_TEL": dados.telefone,
		"EMAIL": dados.email,
	}


def montar_0990(quantidade_linhas: int) -> dict:
	"""Monta `0990` — encerramento do Bloco 0, com a contagem de linhas do próprio
	bloco (mesma convenção de `montar_j990`/`montar_k990`)."""
	return {"REG": "0990", "QTD_LIN_0": str(quantidade_linhas)}
