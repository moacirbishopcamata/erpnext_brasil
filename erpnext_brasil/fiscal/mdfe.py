# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""MDF-e (Manifesto Eletrônico de Documentos Fiscais, modelo 58): montagem de grupos do XML.

Por que existe
--------------
Primeira peça de código do MDF-e, depois do levantamento em `docs/mdfe-estado.md` — só possível
depois que o CT-e passou a existir neste projeto (o MDF-e referencia CT-e/NF-e por chave, nunca
os substitui). Escopo deliberadamente estreito, mesmo padrão do primeiro incremento do CT-e:
só `infDoc`, a peça mais barata e mais próxima de já estar pronta.

Reuso deliberado, e a diferença de forma que o obrigou a não ser cópia direta
------------------------------------------------------------------------------
`montar_infdoc` reusa `fiscal.documento.chave_acesso.ler_chave` — a mesma função usada por
`fiscal.cte.montar_infnfe` — porque o layout de 44 posições é idêntico entre NF-e, CT-e e MDF-e
(confirmado, não suposto: `chave_acesso.MODELOS` já tem `"57"`/`"58"` mapeados desde este
incremento). Mas a **forma** do grupo diverge: `infDoc/infNFe` do CT-e é uma lista plana; o
`infDoc` do MDF-e organiza as referências **por município de descarregamento** (confirmado no
XSD, `infDoc/infMunDescarga/{infCTe,infNFe}`) — cada `infMunDescarga` carrega `cMunDescarga`,
`xMunDescarga` e as chaves de CT-e/NF-e daquele município. Copiar a forma do CT-e sem verificar
teria produzido uma lista plana onde o layout exige agrupamento.

`infMDFeTransp` (referência a outro MDF-e — sub-manifesto de transferência multimodal) não foi
implementado ainda: caso menos comum, fora do escopo deste primeiro incremento.

`assinar_mdfe` reusa `fiscal.documento.assinatura.py` inteiro, sem alteração — mesma disciplina
de `fiscal.cte.assinar_cte`: verificar antes de reaproveitar, nunca supor por "mesma família de
documento" (o `modal` e o `procEmi` do `ide` já divergiram entre CT-e e MDF-e nesta mesma
investigação, ver `docs/mdfe-estado.md` — a assinatura poderia ter divergido também). Duas
confirmações, mesmo padrão do CT-e:

- XSD: `infMDFe/@Id`, padrão `MDFe[0-9]{44}` (`mdfeTiposBasico_v3.00.xsd`, linha 1230) — mesma
  convenção `<prefixo><chave>`.
- Código de produção: `signMDFe()` de `nfephp-org/sped-mdfe` (`src/Common/Tools.php`) chama
  `Signer::sign` com `$this->algorithm`, cujo valor padrão na própria classe é
  `OPENSSL_ALGO_SHA1` — o mesmo algoritmo já confirmado para o CT-e (`docs/cte-assinatura.md`).

`montar_ide`/`montar_mdfe` orquestram — o papel que `fiscal.cte.montar_ide`/`montar_cte` cumprem
para o CT-e. Lição aplicada desde o início desta vez (não depois, como no CT-e): `montar_ide`
já nasce recebendo `chave` como parâmetro obrigatório e extraindo `cDV` dela via `ler_chave`
(nunca `chave[-1]` cru), com a mesma pré-condição de Design by Contract — a chave decomposta
precisa ser de MDF-e (`modelo == "58"`) — em vez de ser corrigido depois de um bug passar
despercebido (ver `docs/cte-orquestracao.md`, seção "Correção: `cDV` estava ausente").

Os 21 campos de `ide` foram lidos e ordenados por leitura direta do XSD
(`mdfeTiposBasico_v3.00.xsd`, linhas 17–232, ver `docs/mdfe-estado.md`), não por analogia com o
CT-e — `modal`/`procEmi` já divergiram entre os dois documentos nesta mesma investigação.

`montar_tot`/`montar_lacres` fecham os dois grupos restantes mais simples de `infMDFe` (linhas
1017–1099). `tot` é o totalizador da carga: `vCarga` (valor), `cUnid` (`"01"` KG / `"02"` TON —
só duas opções, confirmadas) e `qCarga` (peso bruto) são obrigatórios; `qCTe`/`qNFe`/`qMDFe`
(quantidade de cada tipo de documento vinculado) são opcionais — o XSD não obriga nenhum dos
três, então nenhum é exigido aqui (quem monta decide o que informar, coerente com o documento
poder vincular só CT-e, só NF-e, ou os dois). `lacres` é uma lista simples e opcional de números
de lacre — sem estrutura interna além do próprio número, por isso vira uma lista de strings, não
uma dataclass.

`montar_emit`/`montar_seg`/`montar_prod_pred` fecham os três últimos grupos de `infMDFe`
verificados neste levantamento (`emit` linhas 233–293, `seg` linhas 760–862, `prodPred` linhas
863–938). Achado real: `emit`, diferente do emitente da NF-e (sempre CNPJ, pessoa jurídica),
aceita **CNPJ ou CPF** — o próprio XSD documenta que a série 920-969 é reservada para "emitente
pessoa física com inscrição estadual", cobrindo o transportador autônomo. `montar_emit` reusa
`validar_cpf_cnpj`, mesma escolha exclusiva de `fiscal.cte.montar_toma4`. `seg` (seguro da
carga) é opcional e repetível — cada item tem `respSeg` (1-emitente/2-contratante, com CNPJ/CPF
só quando é o contratante), dados da seguradora e apólice/averbações, todos opcionais dentro do
grupo. `prodPred` classifica o produto predominante por `tpCarga` (12 categorias da Resolução
ANTT 5.849/2019, incluindo variantes "perigosa" de granel/frigorificada/conteinerizada/geral) —
`infLotacao` (carga lotação com localização de carregamento) não foi implementado, estrutura
aninhada mais rara, fora de escopo deste incremento.

`montar_infmodal`/`montar_infmdfe` fecham o orquestrador de nível mais alto: até este ponto,
cada grupo de `infMDFe` (`ide`, `emit`, `infDoc`, `seg`, `prodPred`, `tot`, `lacres`) era montado
separadamente, sem nada que os juntasse num único `infMDFe`. Achado real sobre `infModal`
(linhas 294–325): é um ponto de extensão `xs:any` — o schema não descreve o conteúdo do modal
diretamente, delega a um dos arquivos `mdfeModal*_v3.00.xsd` (só o rodoviário está implementado,
`fiscal.mdfe_rodoviario.montar_rodo`), e exige o atributo `versaoModal` (padrão "3.NN", ex.
`"3.00"`). `montar_infmodal` recebe o conteúdo do modal já pronto (`{"rodo":
...}`) e só valida/anexa a versão — não sabe montar nenhum modal específico, mesma composição de
`montar_ide` recebendo o tomador pronto no CT-e.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from erpnext_brasil.fiscal.documento.assinatura import Assinador, montar_signature
from erpnext_brasil.fiscal.documento.chave_acesso import ChaveInvalida, ler_chave
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.validators import validar_cnpj, validar_cpf_cnpj

_PADRAO_VERSAO_MODAL = re.compile(r"^3\.(0[0-9]|[1-9][0-9])$")

__all__ = [
	"AMBIENTE_HOMOLOGACAO",
	"AMBIENTE_PRODUCAO",
	"EMITENTE_PRESTADOR_CTE_GLOBALIZADO",
	"EMITENTE_PRESTADOR_SERVICO",
	"EMITENTE_TRANSPORTADOR_CARGA_PROPRIA",
	"MODAL_AEREO",
	"MODAL_AQUAVIARIO",
	"MODAL_FERROVIARIO",
	"MODAL_RODOVIARIO",
	"NAMESPACE_MDFE",
	"PROCESSO_EMISSAO_APLICATIVO_CONTRIBUINTE",
	"PROCESSO_EMISSAO_PAA",
	"RESPONSAVEL_SEGURO_CONTRATANTE",
	"RESPONSAVEL_SEGURO_EMITENTE",
	"TIPO_CARGA_CONTEINERIZADA",
	"TIPO_CARGA_FRIGORIFICADA",
	"TIPO_CARGA_GERAL",
	"TIPO_CARGA_GRANEL_LIQUIDO",
	"TIPO_CARGA_GRANEL_PRESSURIZADA",
	"TIPO_CARGA_GRANEL_SOLIDO",
	"TIPO_CARGA_NEOGRANEL",
	"TIPO_CARGA_PERIGOSA_CARGA_GERAL",
	"TIPO_CARGA_PERIGOSA_CONTEINERIZADA",
	"TIPO_CARGA_PERIGOSA_FRIGORIFICADA",
	"TIPO_CARGA_PERIGOSA_GRANEL_LIQUIDO",
	"TIPO_CARGA_PERIGOSA_GRANEL_SOLIDO",
	"TRANSPORTADOR_CTC",
	"TRANSPORTADOR_ETC",
	"TRANSPORTADOR_TAC",
	"UNIDADE_PESO_KG",
	"UNIDADE_PESO_TON",
	"Emitente",
	"IdentificacaoMdfe",
	"MdfeInvalido",
	"MunicipioCarrega",
	"MunicipioDescarga",
	"Seguro",
	"assinar_mdfe",
	"montar_emit",
	"montar_ide",
	"montar_infdoc",
	"montar_infmdfe",
	"montar_infmodal",
	"montar_lacres",
	"montar_mdfe",
	"montar_prod_pred",
	"montar_seg",
	"montar_tot",
]

NAMESPACE_MDFE = "http://www.portalfiscal.inf.br/mdfe"

# `tpEmit` — confirmado em `ide/tpEmit` (linha 37).
EMITENTE_PRESTADOR_SERVICO = "1"
EMITENTE_TRANSPORTADOR_CARGA_PROPRIA = "2"
EMITENTE_PRESTADOR_CTE_GLOBALIZADO = "3"

# `tpTransp` — confirmado em `ide/tpTransp` (linha 47), opcional.
TRANSPORTADOR_ETC = "1"
TRANSPORTADOR_TAC = "2"
TRANSPORTADOR_CTC = "3"

# `modal` do MDF-e — confirmado em `ide/modal` (linha 100). **Diverge do `modal` do CT-e**
# (`"01"`–`"06"`, com Dutoviário/Multimodal) — aqui é `"1"`–`"4"`, sem zero à esquerda, sem
# Dutoviário nem Multimodal. Ver `docs/mdfe-estado.md`.
MODAL_RODOVIARIO = "1"
MODAL_AEREO = "2"
MODAL_AQUAVIARIO = "3"
MODAL_FERROVIARIO = "4"

# `procEmi` — confirmado em `ide/procEmi` (linha 128). **Diverge do `procEmi` do CT-e**
# (`"0"`/`"3"`) — aqui é `"0"`/`"4"` (aplicativo do contribuinte / Provedor de Assinatura e
# Autorização - PAA).
PROCESSO_EMISSAO_APLICATIVO_CONTRIBUINTE = "0"
PROCESSO_EMISSAO_PAA = "4"

AMBIENTE_PRODUCAO = "1"
AMBIENTE_HOMOLOGACAO = "2"

# `cUnid` de `tot` — confirmado em `tot/cUnid` (linha 1059): só duas opções, peso Bruto da
# carga em quilos ou toneladas.
UNIDADE_PESO_KG = "01"
UNIDADE_PESO_TON = "02"

_UNIDADES_PESO_VALIDAS = {UNIDADE_PESO_KG, UNIDADE_PESO_TON}

# `respSeg` de `seg/infResp` — confirmado em `seg/infResp/respSeg` (linha 772).
RESPONSAVEL_SEGURO_EMITENTE = "1"
RESPONSAVEL_SEGURO_CONTRATANTE = "2"

_RESPONSAVEIS_SEGURO_VALIDOS = {RESPONSAVEL_SEGURO_EMITENTE, RESPONSAVEL_SEGURO_CONTRATANTE}

# `tpCarga` de `prodPred` — confirmado em `prodPred/tpCarga` (linha 870), Resolução ANTT
# nº 5.849/2019.
TIPO_CARGA_GRANEL_SOLIDO = "01"
TIPO_CARGA_GRANEL_LIQUIDO = "02"
TIPO_CARGA_FRIGORIFICADA = "03"
TIPO_CARGA_CONTEINERIZADA = "04"
TIPO_CARGA_GERAL = "05"
TIPO_CARGA_NEOGRANEL = "06"
TIPO_CARGA_PERIGOSA_GRANEL_SOLIDO = "07"
TIPO_CARGA_PERIGOSA_GRANEL_LIQUIDO = "08"
TIPO_CARGA_PERIGOSA_FRIGORIFICADA = "09"
TIPO_CARGA_PERIGOSA_CONTEINERIZADA = "10"
TIPO_CARGA_PERIGOSA_CARGA_GERAL = "11"
TIPO_CARGA_GRANEL_PRESSURIZADA = "12"

_TIPOS_CARGA_VALIDOS = {
	TIPO_CARGA_GRANEL_SOLIDO,
	TIPO_CARGA_GRANEL_LIQUIDO,
	TIPO_CARGA_FRIGORIFICADA,
	TIPO_CARGA_CONTEINERIZADA,
	TIPO_CARGA_GERAL,
	TIPO_CARGA_NEOGRANEL,
	TIPO_CARGA_PERIGOSA_GRANEL_SOLIDO,
	TIPO_CARGA_PERIGOSA_GRANEL_LIQUIDO,
	TIPO_CARGA_PERIGOSA_FRIGORIFICADA,
	TIPO_CARGA_PERIGOSA_CONTEINERIZADA,
	TIPO_CARGA_PERIGOSA_CARGA_GERAL,
	TIPO_CARGA_GRANEL_PRESSURIZADA,
}

_EMITENTES_VALIDOS = {
	EMITENTE_PRESTADOR_SERVICO,
	EMITENTE_TRANSPORTADOR_CARGA_PROPRIA,
	EMITENTE_PRESTADOR_CTE_GLOBALIZADO,
}
_TRANSPORTADORES_VALIDOS = {TRANSPORTADOR_ETC, TRANSPORTADOR_TAC, TRANSPORTADOR_CTC}
_MODAIS_VALIDOS = {MODAL_RODOVIARIO, MODAL_AEREO, MODAL_AQUAVIARIO, MODAL_FERROVIARIO}
_PROCESSOS_EMISSAO_VALIDOS = {PROCESSO_EMISSAO_APLICATIVO_CONTRIBUINTE, PROCESSO_EMISSAO_PAA}
_TIPOS_EMISSAO_VALIDOS = {"1", "2", "3"}


class MdfeInvalido(ValueError):
	"""Dado que impediria a autorização do MDF-e."""

	def __init__(self, mensagem: str, campo: str = ""):
		super().__init__(mensagem)
		self.campo = campo


@dataclass(frozen=True)
class MunicipioCarrega:
	"""Um município de carregamento — `ide/infMunCarrega` (até 50, ao menos um é obrigatório)."""

	codigo: str
	"""`cMunCarrega` — código IBGE."""
	nome: str
	"""`xMunCarrega`."""


@dataclass(frozen=True)
class IdentificacaoMdfe:
	"""Dados que identificam o documento — origem do grupo `ide`.

	Campos confirmados por leitura direta do XSD (`mdfeTiposBasico_v3.00.xsd`, linhas
	17–232), na ordem exata do `xs:sequence`. Bem mais enxuto que o `ide` do CT-e/NF-e:
	sem `CFOP` nem `natOp` — o MDF-e não é uma operação tributável, é um manifesto.
	"""

	uf: str
	"""`cUF` — código IBGE, não a sigla."""
	tipo_emitente: str
	serie: str
	numero: str
	codigo_numerico: str
	"""`cMDF` — 8 dígitos, mesmo padrão de `cCT`/`cNF`."""
	modal: str
	emissao: datetime
	uf_inicio: str
	uf_fim: str
	municipios_carrega: list[MunicipioCarrega]
	"""`infMunCarrega` — até 50, ao menos um é obrigatório (sem `minOccurs="0"` no XSD)."""
	tipo_transportador: str = ""
	ufs_percurso: list[str] = field(default_factory=list)
	"""`infPercurso/UFPer` — opcional, até 25. Não repetir `uf_inicio`/`uf_fim`."""
	dh_inicio_viagem: datetime | None = None
	canal_verde: bool = False
	carrega_posterior: bool = False
	tipo_emissao: str = "1"
	processo_emissao: str = PROCESSO_EMISSAO_APLICATIVO_CONTRIBUINTE
	versao_processo: str = "1.0.0"
	ambiente: str = AMBIENTE_HOMOLOGACAO
	"""1 = produção, 2 = homologação — mesmo padrão-seguro de `cte.IdentificacaoCte`."""

	def validar(self) -> None:
		if self.tipo_emitente not in _EMITENTES_VALIDOS:
			raise MdfeInvalido(
				f"tipo_emitente deve ser um de {sorted(_EMITENTES_VALIDOS)}, recebido {self.tipo_emitente!r}",
				"tipo_emitente",
			)

		if self.tipo_transportador and self.tipo_transportador not in _TRANSPORTADORES_VALIDOS:
			raise MdfeInvalido(
				f"tipo_transportador deve ser um de {sorted(_TRANSPORTADORES_VALIDOS)}, "
				f"recebido {self.tipo_transportador!r}",
				"tipo_transportador",
			)

		if self.modal not in _MODAIS_VALIDOS:
			raise MdfeInvalido(
				f"modal deve ser um de {sorted(_MODAIS_VALIDOS)}, recebido {self.modal!r}", "modal"
			)

		if self.tipo_emissao not in _TIPOS_EMISSAO_VALIDOS:
			raise MdfeInvalido(
				f"tipo_emissao deve ser um de {sorted(_TIPOS_EMISSAO_VALIDOS)}, "
				f"recebido {self.tipo_emissao!r}",
				"tipo_emissao",
			)

		if self.processo_emissao not in _PROCESSOS_EMISSAO_VALIDOS:
			raise MdfeInvalido(
				f"processo_emissao deve ser um de {sorted(_PROCESSOS_EMISSAO_VALIDOS)}, "
				f"recebido {self.processo_emissao!r}",
				"processo_emissao",
			)

		if not self.municipios_carrega:
			raise MdfeInvalido(
				"infMunCarrega precisa de ao menos um município (XSD: minOccurs=1)",
				"municipios_carrega",
			)


@dataclass(frozen=True)
class MunicipioDescarga:
	"""Um município de descarregamento e os documentos fiscais nele entregues."""

	codigo: str
	"""`cMunDescarga` — código IBGE."""
	nome: str
	"""`xMunDescarga`."""
	chaves_cte: list[str] = field(default_factory=list)
	chaves_nfe: list[str] = field(default_factory=list)


def _montar_referencias(
	chaves: list[str], modelo_esperado: str, campo_chave: str, nome_grupo: str
) -> list[dict]:
	"""Valida e monta uma lista de referências por chave — mesma lógica de
	`fiscal.cte.montar_infnfe`, parametrizada pelo modelo e pelo nome do campo/grupo
	porque `infCTe`/`chCTe` e `infNFe`/`chNFe` só diferem nisso."""
	referencias = []

	for chave in chaves:
		decomposta = ler_chave(chave)

		if decomposta.modelo != modelo_esperado:
			raise ChaveInvalida(
				f"{nome_grupo} só aceita chave de modelo {modelo_esperado}, "
				f"recebida chave de modelo {decomposta.modelo} ({decomposta.documento})",
				chave,
			)

		referencias.append({campo_chave: decomposta.valor})

	return referencias


def montar_infdoc(municipios: list[MunicipioDescarga]) -> dict:
	"""Monta `infDoc`, agrupado por município de descarregamento.

	Cada `MunicipioDescarga` vira um item de `infMunDescarga`, com `infCTe`/`infNFe`
	presentes só quando há chaves daquele tipo — sem grupo vazio.
	"""
	if not municipios:
		raise ValueError("infDoc precisa de ao menos um município de descarregamento (XSD: minOccurs=1)")

	infmun = []

	for municipio in municipios:
		item: dict = {"cMunDescarga": municipio.codigo, "xMunDescarga": municipio.nome}

		if municipio.chaves_cte:
			item["infCTe"] = _montar_referencias(municipio.chaves_cte, "57", "chCTe", "infDoc/infCTe")

		if municipio.chaves_nfe:
			item["infNFe"] = _montar_referencias(municipio.chaves_nfe, "55", "chNFe", "infDoc/infNFe")

		infmun.append(item)

	return {"infDoc": {"infMunDescarga": infmun}}


def montar_ide(identificacao: IdentificacaoMdfe, chave: str) -> dict:
	"""Monta o grupo `ide`, na ordem exata do XSD.

	Recebe `chave` para extrair `cDV` — mesma disciplina de `fiscal.cte.montar_ide` (que
	só ganhou essa disciplina depois de um bug, ver `docs/cte-orquestracao.md`; aqui já
	nasce correta). Pré-condição de Design by Contract: a chave decomposta precisa ser
	de MDF-e (`modelo == "58"`) — sem essa checagem, uma chave de CT-e ou NF-e passada
	por engano produziria um `ide` com `cDV` "correto" mas de outro documento.
	"""
	identificacao.validar()

	chave_decomposta = ler_chave(chave)

	if chave_decomposta.modelo != "58":
		raise MdfeInvalido(
			f"ide/cDV precisa de uma chave de MDF-e (modelo 58), recebida chave de modelo "
			f"{chave_decomposta.modelo} ({chave_decomposta.documento})",
			"chave",
		)

	grupo: dict = {
		"cUF": identificacao.uf,
		"tpAmb": identificacao.ambiente,
		"tpEmit": identificacao.tipo_emitente,
	}

	if identificacao.tipo_transportador:
		grupo["tpTransp"] = identificacao.tipo_transportador

	grupo.update(
		{
			"mod": "58",
			"serie": str(identificacao.serie).lstrip("0") or "0",
			"nMDF": str(identificacao.numero).lstrip("0") or "0",
			"cMDF": str(identificacao.codigo_numerico).rjust(8, "0"),
			"cDV": chave_decomposta.dv,
			"modal": identificacao.modal,
			"dhEmi": identificacao.emissao.isoformat(),
			"tpEmis": identificacao.tipo_emissao,
			"procEmi": identificacao.processo_emissao,
			"verProc": identificacao.versao_processo,
			"UFIni": identificacao.uf_inicio,
			"UFFim": identificacao.uf_fim,
			"infMunCarrega": [
				{"cMunCarrega": m.codigo, "xMunCarrega": m.nome} for m in identificacao.municipios_carrega
			],
		}
	)

	if identificacao.ufs_percurso:
		grupo["infPercurso"] = [{"UFPer": uf} for uf in identificacao.ufs_percurso]

	if identificacao.dh_inicio_viagem is not None:
		grupo["dhIniViagem"] = identificacao.dh_inicio_viagem.isoformat()

	if identificacao.canal_verde:
		grupo["indCanalVerde"] = "1"

	if identificacao.carrega_posterior:
		grupo["indCarregaPosterior"] = "1"

	return grupo


def montar_mdfe(infmdfe: dict, chave: str) -> dict:
	"""Envolve `infMDFe` na raiz `MDFe`, com o namespace do leiaute e o `Id` derivado.

	Mesma disciplina de `fiscal.cte.montar_cte`/`fiscal.documento.nfe.montar_nfe`: o `Id`
	é `"MDFe" + chave`, nunca informado em paralelo — não há como divergir do que a
	chave realmente é.
	"""
	return {
		"MDFe": {
			"@xmlns": NAMESPACE_MDFE,
			"infMDFe": {**infmdfe, "@Id": f"MDFe{chave}"},
		}
	}


def montar_tot(
	valor_carga: Decimal,
	unidade_peso: str,
	peso_carga: Decimal,
	quantidade_cte: int | None = None,
	quantidade_nfe: int | None = None,
	quantidade_mdfe: int | None = None,
) -> dict:
	"""Monta o grupo `tot` — totalizadores da carga transportada.

	`valor_carga`, `unidade_peso` e `peso_carga` são obrigatórios no XSD; as três
	quantidades (`qCTe`/`qNFe`/`qMDFe`) são opcionais — o layout não exige nenhuma
	delas, coerente com um MDF-e poder vincular só CT-e, só NF-e, ou os dois.
	"""
	if unidade_peso not in _UNIDADES_PESO_VALIDAS:
		raise MdfeInvalido(
			f"unidade_peso deve ser um de {sorted(_UNIDADES_PESO_VALIDAS)}, recebido {unidade_peso!r}",
			"unidade_peso",
		)

	grupo: dict = {}

	if quantidade_cte is not None:
		grupo["qCTe"] = str(quantidade_cte)

	if quantidade_nfe is not None:
		grupo["qNFe"] = str(quantidade_nfe)

	if quantidade_mdfe is not None:
		grupo["qMDFe"] = str(quantidade_mdfe)

	grupo["vCarga"] = str(valor_carga)
	grupo["cUnid"] = unidade_peso
	grupo["qCarga"] = str(peso_carga)

	return {"tot": grupo}


def montar_lacres(numeros: list[str]) -> dict:
	"""Monta `lacres` — lista opcional de números de lacre, sem estrutura interna além
	do próprio número (por isso uma lista de strings, não uma dataclass). Devolve `{}`
	quando vazia — `lacres` tem `minOccurs="0"` no XSD, sem grupo vazio no documento."""
	if not numeros:
		return {}

	return {"lacres": [{"nLacre": n} for n in numeros]}


def assinar_mdfe(mdfe: dict, assinador: Assinador) -> dict:
	"""Assina o documento e devolve a árvore completa, com `Signature` anexado.

	Mesma costura de `fiscal.cte.assinar_cte`/`fiscal.documento.nfe.assinar_nfe`: serializa a
	árvore (com o `Id` já aplicado em `infMDFe`), assina, e monta o envelope `Signature` como
	irmão de `infMDFe` dentro de `MDFe`. Recebe `mdfe`, não `infmdfe`, pelo mesmo motivo dos
	outros dois: o digest tem que ser calculado sobre a árvore com o namespace já aplicado.
	"""
	id_elemento = mdfe["MDFe"]["infMDFe"]["@Id"]
	xml = para_xml(mdfe).encode("utf-8")

	material = assinador.assinar(xml, id_elemento)
	signature = montar_signature(id_elemento, material)

	return {"MDFe": {**mdfe["MDFe"], **signature}}


@dataclass(frozen=True)
class Emitente:
	"""Quem emite o MDF-e — CNPJ **ou** CPF, diferente da NF-e (sempre CNPJ)."""

	cnpj_cpf: str
	nome: str
	endereco: dict
	inscricao_estadual: str = ""
	nome_fantasia: str = ""


def montar_emit(emitente: Emitente) -> dict:
	"""Monta o grupo `emit`.

	CNPJ/CPF são escolha exclusiva no XSD (mesma validação de
	`fiscal.cte.montar_toma4`) — o emitente pode ser pessoa jurídica ou o transportador
	autônomo pessoa física (série 920-969, confirmado na documentação do próprio campo).
	`enderEmit` é obrigatório (sem `minOccurs="0"` no XSD).
	"""
	try:
		documento = validar_cpf_cnpj(emitente.cnpj_cpf)
	except ValueError as e:
		raise MdfeInvalido(f"CPF/CNPJ do emitente inválido: {e}", "cnpj_cpf") from e

	if not emitente.nome.strip():
		raise MdfeInvalido("Emitente precisa de nome", "nome")

	if not emitente.endereco:
		raise MdfeInvalido("Emitente precisa de endereço (enderEmit é obrigatório no XSD)", "endereco")

	grupo: dict = {}
	grupo["CNPJ" if len(documento) == 14 else "CPF"] = documento

	if emitente.inscricao_estadual.strip():
		grupo["IE"] = emitente.inscricao_estadual.strip()

	grupo["xNome"] = emitente.nome.strip()

	if emitente.nome_fantasia.strip():
		grupo["xFant"] = emitente.nome_fantasia.strip()

	grupo["enderEmit"] = dict(emitente.endereco)

	return {"emit": grupo}


@dataclass(frozen=True)
class Seguro:
	"""Um item de `seg` — seguro da carga transportada, tudo opcional dentro do grupo."""

	responsavel: str
	cnpj_cpf_responsavel: str = ""
	"""Só se aplica quando `responsavel == RESPONSAVEL_SEGURO_CONTRATANTE` (o XSD marca
	CNPJ/CPF como obrigatório só nesse caso; aqui fica opcional e o chamador decide)."""
	seguradora_nome: str = ""
	seguradora_cnpj: str = ""
	numero_apolice: str = ""
	numeros_averbacao: list[str] = field(default_factory=list)


def montar_seg(seguros: list[Seguro]) -> dict:
	"""Monta `seg` — lista opcional e repetível de seguros da carga. Devolve `{}` quando
	vazia, nunca um grupo `seg` vazio no documento (`minOccurs="0"`)."""
	if not seguros:
		return {}

	itens = []

	for seguro in seguros:
		if seguro.responsavel not in _RESPONSAVEIS_SEGURO_VALIDOS:
			raise MdfeInvalido(
				f"responsavel deve ser um de {sorted(_RESPONSAVEIS_SEGURO_VALIDOS)}, "
				f"recebido {seguro.responsavel!r}",
				"responsavel",
			)

		inf_resp: dict = {"respSeg": seguro.responsavel}

		if seguro.cnpj_cpf_responsavel:
			try:
				documento = validar_cpf_cnpj(seguro.cnpj_cpf_responsavel)
			except ValueError as e:
				raise MdfeInvalido(f"CPF/CNPJ do responsável pelo seguro inválido: {e}") from e

			inf_resp["CNPJ" if len(documento) == 14 else "CPF"] = documento

		item: dict = {"infResp": inf_resp}

		if seguro.seguradora_nome.strip():
			inf_seg: dict = {"xSeg": seguro.seguradora_nome.strip()}

			if seguro.seguradora_cnpj:
				try:
					inf_seg["CNPJ"] = validar_cnpj(seguro.seguradora_cnpj)
				except ValueError as e:
					raise MdfeInvalido(f"CNPJ da seguradora inválido: {e}") from e

			item["infSeg"] = inf_seg

		if seguro.numero_apolice.strip():
			item["nApol"] = seguro.numero_apolice.strip()

		if seguro.numeros_averbacao:
			item["nAver"] = list(seguro.numeros_averbacao)

		itens.append(item)

	return {"seg": itens}


def montar_prod_pred(tipo_carga: str, descricao: str, ean: str = "", ncm: str = "") -> dict:
	"""Monta `prodPred` — produto predominante, pelo item de maior valor financeiro
	(Resolução ANTT 5.849/2019). `infLotacao` (carga lotação com localização de
	carregamento) não é implementado — estrutura aninhada mais rara, fora de escopo."""
	if tipo_carga not in _TIPOS_CARGA_VALIDOS:
		raise MdfeInvalido(
			f"tipo_carga deve ser um de {sorted(_TIPOS_CARGA_VALIDOS)}, recebido {tipo_carga!r}",
			"tipo_carga",
		)

	if not descricao.strip():
		raise MdfeInvalido("prodPred precisa de xProd (descrição do produto)", "descricao")

	grupo: dict = {"tpCarga": tipo_carga, "xProd": descricao.strip()}

	if ean.strip():
		grupo["cEAN"] = ean.strip()

	if ncm.strip():
		grupo["NCM"] = ncm.strip()

	return {"prodPred": grupo}


def montar_infmodal(versao: str, conteudo_modal: dict) -> dict:
	"""Monta `infModal` — um `xs:any` com atributo `versaoModal` obrigatório.

	`conteudo_modal` já vem pronto (ex.: `{"rodo": montar_rodo(...)}` de
	`fiscal.mdfe_rodoviario`) — esta função só valida a versão e anexa, não sabe montar
	nenhum modal específico (só o rodoviário está implementado no projeto até agora).
	"""
	if not _PADRAO_VERSAO_MODAL.match(versao):
		raise MdfeInvalido(
			f"versaoModal deve seguir o padrão 3.NN (ex. '3.00'), recebido {versao!r}", "versao"
		)

	if not conteudo_modal:
		raise MdfeInvalido("infModal precisa do conteúdo de um modal (ex. rodo)", "conteudo_modal")

	return {"infModal": {"@versaoModal": versao, **conteudo_modal}}


def montar_infmdfe(
	ide: dict,
	emit: dict,
	infmodal: dict,
	infdoc: dict,
	tot: dict,
	seg: dict | None = None,
	prod_pred: dict | None = None,
	lacres: dict | None = None,
) -> dict:
	"""Compõe `infMDFe` a partir dos grupos já montados, na ordem exata do XSD
	(`ide`, `emit`, `infModal`, `infDoc`, `seg`, `prodPred`, `tot`, `lacres`).

	Recebe cada grupo pronto — de `montar_ide`, `montar_emit`, `montar_infmodal`,
	`montar_infdoc`, `montar_seg`, `montar_prod_pred`, `montar_tot`, `montar_lacres` —
	e só sabe a ordem em que eles entram, não como cada um é montado. `seg`/`prod_pred`/
	`lacres` são opcionais no XSD; passar `None` ou `{}` os omite do documento.
	"""
	infmdfe: dict = {"ide": ide, **emit, **infmodal, **infdoc}

	if seg:
		infmdfe.update(seg)

	if prod_pred:
		infmdfe.update(prod_pred)

	infmdfe.update(tot)

	if lacres:
		infmdfe.update(lacres)

	return infmdfe
