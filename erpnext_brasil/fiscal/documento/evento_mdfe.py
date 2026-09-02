# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Eventos do MDF-e: cancelamento (`tpEvento` 110111, `evCancMDFe`), encerramento
(`tpEvento` 110112, `evEncMDFe`) e inclusão de condutor (`tpEvento` 110114,
`evIncCondutorMDFe`).

Por que existe
--------------
Primeira peça da frente de eventos do MDF-e, aberta depois que os onze eventos do CT-e
foram concluídos (ver `docs/cte-estado.md`). Mesmo espírito de `evento_cte.py`: verificado
campo a campo contra o XSD literal (`evCancMDFe_v3.00.xsd`, 38 linhas — lido inteiro — e
`eventoMDFeTiposBasico_v3.00.xsd`, 300 linhas — lido inteiro —, ambos de
`nfephp-org/sped-mdfe`, `schemes/PL_MDFe_300b`), não suposto por analogia com o CT-e —
mesma lição já repetida várias vezes nesta frente (`modal`, `procEmi` divergiram entre
CT-e/MDF-e; aqui, ao contrário, a estrutura do evento em si **converge**.

Estrutura de `TEvento` do MDF-e — converge com a do CT-e, diverge da NF-e
------------------------------------------------------------------------------------------
`infEvento`: `cOrgao`, `tpAmb`, `(CNPJ|CPF)`, `chMDFe`, `dhEvento`, `tpEvento`,
`nSeqEvento`, `detEvento` (com `@versaoEvento` como **atributo**, não elemento
`verEvento`), mais `infSolicNFF`/`infPAA` opcionais (não usados por este módulo). No nível
do `evento` inteiro, `@versao` (`TVerEvento`, padrão fixo `"3\\.00"` — a versão do leiaute
do MDF-e, `_VERSAO_LEIAUTE_MDFE`). Isso é **idêntico ao CT-e** (que também usa
`@versaoEvento` em `detEvento`, sem `verEvento`) e diferente da NF-e (que tem `verEvento`
como elemento próprio, fixo em `"1.00"`, independente da versão do leiaute).

`tpEvento` do cancelamento é `"110111"` — **o mesmo número** usado pelo cancelamento da
NF-e e do CT-e. Confirmado, não coincidência aparente: os três documentos reaproveitam a
mesma faixa de código para o mesmo tipo de evento (cancelamento), mesmo cada um tendo seu
próprio XSD e — como a frente do CT-e mostrou — outros eventos com códigos exclusivos.

`TJust` do MDF-e é 15-255 — igual ao do CT-e, verificado à parte (não suposto)
------------------------------------------------------------------------------------------
`tiposGeralMDFe_v3.00.xsd` define `TJust` como `minLength=15, maxLength=255` —
numericamente igual ao `TJust` do CT-e (`JUSTIFICATIVA_MAXIMA_CTE`), mas são tipos
**diferentes**, de schemas diferentes: uma coincidência de valor confirmada por leitura
direta, não presumida porque "é a mesma família de documentos" (a lição que motivou
verificar cada documento individualmente, desde o início desta frente). Por isso este
módulo declara `JUSTIFICATIVA_MINIMA_MDFE`/`JUSTIFICATIVA_MAXIMA_MDFE` próprios, em vez de
importar as constantes do CT-e.

`@Id` — a mesma composição do CT-e, mas o schema aceita **dois** larguras de `nSeqEvento`
------------------------------------------------------------------------------------------
O padrão confirmado em `eventoMDFeTiposBasico_v3.00.xsd` é
`ID[0-9]{12}[A-Z0-9]{12}[0-9]{28}|ID[0-9]{12}[A-Z0-9]{12}[0-9]{29}` — a primeira vista
parece divergir da regra documentada ("ID + tpEvento + chave + nSeqEvento"), mas bate
exatamente: `TChMDFe` (a chave) já é `[0-9]{6}[A-Z0-9]{12}[0-9]{26}` (suporte ao CNPJ
alfanumérico, mesmo tratamento de `fiscal/documento/chave_acesso.py`) — somando os 6
dígitos do `tpEvento` aos 6 primeiros da chave dá exatamente os `[0-9]{12}` do início do
padrão, o `[A-Z0-9]{12}` do meio é a raiz alfanumérica do CNPJ dentro da própria chave, e
o `[0-9]{28}`/`[0-9]{29}` final é o resto da chave (26 dígitos) mais `nSeqEvento` — que
pode ter **2 ou 3 dígitos** (52 ou 53 de comprimento total). Diferente do CT-e (onde só a
largura de 3 dígitos é válida no XSD), o MDF-e tolera as duas — este módulo grava sempre
com **3 dígitos**, a convenção mais recente, mesma escolha já feita para o CT-e.

Encerramento (`tpEvento` 110112, `evEncMDFe`) — fecha a viagem do MDF-e
------------------------------------------------------------------------------
Verificado em `evEncMDFe_v3.00.xsd` (59 linhas, lido inteiro): `descEvento` fixo
("Encerramento"), `nProt`, `dtEnc` (data do encerramento, `TData` — só data, sem hora,
diferente de `dhEvento` do `infEvento`), `cUF` (UF de encerramento), `cMun` (código IBGE
do município de encerramento, `TCodMunIBGE`, `[0-9]{7}`) e `indEncPorTerceiro` (opcional,
enumeração de um único valor `"1"` — informado só quando quem encerra é um transportador
terceiro, diferente do emitente do MDF-e).

**Achado real**: `cUF` usa o tipo `TCodUfIBGE_EX` — **não** o `TCodUfIBGE` simples. A
própria documentação do tipo diz "Tipo Código da UF da tabela do IBGE **+ 99 para
Exterior**" — confirmado na enumeração (27 códigos de UF brasileira mais `"99"`). Faz
sentido para encerramento: uma viagem pode terminar fora do Brasil (ex. Mercosul). Este
módulo valida `codigo_uf` contra essa lista estendida (`_UFS_VALIDAS_ENCERRAMENTO_MDFE`,
28 valores), não contra uma tabela de 27 UFs só.

Inclusão de condutor (`tpEvento` 110114, `evIncCondutorMDFe`) — reuso direto de
`fiscal.mdfe_rodoviario.Condutor`
------------------------------------------------------------------------------------------
Verificado em `evIncCondutorMDFe_v3.00.xsd` (49 linhas, lido inteiro): `descEvento` fixo
(**única grafia**, sem acento — `"Inclusao Condutor"`, diferente de outros eventos desta
frente que oferecem variante acentuada) e um único grupo `condutor` (não lista — só
`xNome`, 2-60 caracteres, e `CPF`). **Achado real de reuso**: essa é exatamente a mesma
forma de `condutor` já modelada em `fiscal.mdfe_rodoviario.Condutor`/`montar_condutor`
(usada dentro de `veicTracao`) — reaproveitados diretamente aqui, sem duplicar a
validação de CPF.

Reuso: `EventoInvalido`/`assinar_evento` de `evento.py`, sem alteração
------------------------------------------------------------------------------
Ambos já eram genéricos (não hardcodam `NAMESPACE_NFE`, só leem o que o dicionário
`evento` já tem) — reaproveitados direto, mesmo padrão já usado para o CT-e.

Funções puras: nenhuma dependência do Frappe.
"""

import re

from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave, validar_chave
from erpnext_brasil.fiscal.documento.evento import EventoInvalido, assinar_evento
from erpnext_brasil.fiscal.mdfe import NAMESPACE_MDFE
from erpnext_brasil.fiscal.mdfe_rodoviario import Condutor, MdfeRodoviarioInvalido, montar_condutor
from erpnext_brasil.fiscal.validators import validar_cnpj

__all__ = [
	"INDICADOR_ENCERRAMENTO_POR_TERCEIRO",
	"JUSTIFICATIVA_MAXIMA_MDFE",
	"JUSTIFICATIVA_MINIMA_MDFE",
	"TIPO_EVENTO_CANCELAMENTO_MDFE",
	"TIPO_EVENTO_ENCERRAMENTO_MDFE",
	"TIPO_EVENTO_INCLUSAO_CONDUTOR_MDFE",
	"Condutor",
	"EventoInvalido",
	"assinar_evento",
	"montar_condutor",
	"montar_env_evento_mdfe",
	"montar_evento_cancelamento_mdfe",
	"montar_evento_encerramento_mdfe",
	"montar_evento_inclusao_condutor_mdfe",
]

TIPO_EVENTO_CANCELAMENTO_MDFE = "110111"
TIPO_EVENTO_ENCERRAMENTO_MDFE = "110112"
TIPO_EVENTO_INCLUSAO_CONDUTOR_MDFE = "110114"
_VERSAO_LEIAUTE_MDFE = "3.00"

# `TJust` do MDF-e — numericamente igual ao do CT-e, mas verificado à parte (tipo
# diferente, de schema diferente) — ver docstring do módulo.
JUSTIFICATIVA_MINIMA_MDFE = 15
JUSTIFICATIVA_MAXIMA_MDFE = 255

# `TCodUfIBGE_EX` — as 27 UFs brasileiras mais "99" para Exterior (ver docstring do
# módulo). Confirmado em `tiposGeralMDFe_v3.00.xsd`.
_UFS_VALIDAS_ENCERRAMENTO_MDFE = {
	"11", "12", "13", "14", "15", "16", "17", "21", "22", "23", "24", "25", "26", "27",
	"28", "29", "31", "32", "33", "35", "41", "42", "43", "50", "51", "52", "53", "99",
}

INDICADOR_ENCERRAMENTO_POR_TERCEIRO = "1"

_PADRAO_CODIGO_MUNICIPIO = re.compile(r"^[0-9]{7}$")


def _formatar_id_mdfe(chave: str, tipo_evento: str, numero_sequencia: int) -> str:
	"""`"ID" + tpEvento + chave(44) + nSeqEvento(3, com zero à esquerda)` — o schema do
	MDF-e tolera também 2 dígitos, mas este módulo sempre grava com 3, mesma convenção
	já usada para o CT-e (ver docstring do módulo)."""
	return f"ID{tipo_evento}{chave}{numero_sequencia:03d}"


def montar_evento_cancelamento_mdfe(
	chave_acesso: str,
	protocolo: str,
	justificativa: str,
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) do cancelamento do MDF-e.

	Mesma costura de `evento_cte.montar_evento_cancelamento_cte`, com `chMDFe` no lugar
	de `chCTe`/`chNFe` e limites próprios de justificativa (numericamente iguais aos do
	CT-e, mas verificados à parte — ver docstring do módulo).
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	texto_justificativa = (justificativa or "").strip()

	if not (JUSTIFICATIVA_MINIMA_MDFE <= len(texto_justificativa) <= JUSTIFICATIVA_MAXIMA_MDFE):
		raise EventoInvalido(
			f"A justificativa deve ter de {JUSTIFICATIVA_MINIMA_MDFE} a "
			f"{JUSTIFICATIVA_MAXIMA_MDFE} caracteres, recebidos {len(texto_justificativa)}",
			"justificativa",
		)

	protocolo_limpo = (protocolo or "").strip()

	if not protocolo_limpo:
		raise EventoInvalido("O protocolo da autorização é obrigatório para cancelar", "protocolo")

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	inf_evento = {
		"@Id": _formatar_id_mdfe(chave, TIPO_EVENTO_CANCELAMENTO_MDFE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chMDFe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_CANCELAMENTO_MDFE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": {
			"@versaoEvento": _VERSAO_LEIAUTE_MDFE,
			"descEvento": "Cancelamento",
			"nProt": protocolo_limpo,
			"xJust": texto_justificativa,
		},
	}

	return {"evento": {"@xmlns": NAMESPACE_MDFE, "@versao": _VERSAO_LEIAUTE_MDFE, "infEvento": inf_evento}}


def montar_evento_encerramento_mdfe(
	chave_acesso: str,
	protocolo: str,
	data_encerramento: str,
	codigo_uf: str,
	codigo_municipio: str,
	cnpj_autor: str,
	data_evento: str,
	encerrado_por_terceiro: bool = False,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) do encerramento do MDF-e — fecha a
	viagem.

	`codigo_uf` é validado contra `TCodUfIBGE_EX` (27 UFs + `"99"` Exterior), não a
	tabela normal de 27 UFs — ver docstring do módulo. `encerrado_por_terceiro` só
	grava `indEncPorTerceiro` quando `True` (o XSD só define o valor `"1"`; a ausência
	do campo já significa "não é terceiro", não há um `"0"` explícito).
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	protocolo_limpo = (protocolo or "").strip()

	if not protocolo_limpo:
		raise EventoInvalido("O protocolo da autorização é obrigatório", "protocolo")

	if codigo_uf not in _UFS_VALIDAS_ENCERRAMENTO_MDFE:
		raise EventoInvalido(
			f"cUF deve ser uma UF válida ou '99' (Exterior), recebido {codigo_uf!r}", "codigo_uf"
		)

	if not _PADRAO_CODIGO_MUNICIPIO.match(codigo_municipio or ""):
		raise EventoInvalido(
			f"cMun deve ter 7 dígitos (código IBGE), recebido {codigo_municipio!r}",
			"codigo_municipio",
		)

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	det_evento: dict = {
		"@versaoEvento": _VERSAO_LEIAUTE_MDFE,
		"descEvento": "Encerramento",
		"nProt": protocolo_limpo,
		"dtEnc": data_encerramento,
		"cUF": codigo_uf,
		"cMun": codigo_municipio,
	}

	if encerrado_por_terceiro:
		det_evento["indEncPorTerceiro"] = INDICADOR_ENCERRAMENTO_POR_TERCEIRO

	inf_evento = {
		"@Id": _formatar_id_mdfe(chave, TIPO_EVENTO_ENCERRAMENTO_MDFE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chMDFe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_ENCERRAMENTO_MDFE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": det_evento,
	}

	return {"evento": {"@xmlns": NAMESPACE_MDFE, "@versao": _VERSAO_LEIAUTE_MDFE, "infEvento": inf_evento}}


def montar_evento_inclusao_condutor_mdfe(
	chave_acesso: str,
	condutor: Condutor,
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) da inclusão de condutor do MDF-e.

	`condutor` reaproveita `fiscal.mdfe_rodoviario.Condutor`/`montar_condutor` — mesma
	forma exata (`xNome`/`CPF`) já usada dentro de `veicTracao` (ver docstring do
	módulo). O XSD só aceita **um** condutor por evento (não uma lista) — para incluir
	mais de um, é preciso um evento por condutor.
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	try:
		grupo_condutor = montar_condutor(condutor)
	except MdfeRodoviarioInvalido as e:
		raise EventoInvalido(str(e), "condutor") from e

	inf_evento = {
		"@Id": _formatar_id_mdfe(chave, TIPO_EVENTO_INCLUSAO_CONDUTOR_MDFE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chMDFe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_INCLUSAO_CONDUTOR_MDFE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": {
			"@versaoEvento": _VERSAO_LEIAUTE_MDFE,
			"descEvento": "Inclusao Condutor",
			"condutor": grupo_condutor,
		},
	}

	return {"evento": {"@xmlns": NAMESPACE_MDFE, "@versao": _VERSAO_LEIAUTE_MDFE, "infEvento": inf_evento}}


def montar_env_evento_mdfe(eventos: list[dict], id_lote: str) -> dict:
	"""Monta `envEvento` do MDF-e — mesma disciplina de `evento.montar_env_evento`
	(até 20 eventos por lote), com o namespace do MDF-e."""
	if not eventos:
		raise EventoInvalido("O lote de eventos precisa de ao menos um evento", "eventos")

	if len(eventos) > 20:
		raise EventoInvalido(
			f"Um lote de eventos admite no máximo 20, recebidos {len(eventos)}", "eventos"
		)

	if not (id_lote or "").strip():
		raise EventoInvalido("idLote é obrigatório", "id_lote")

	return {
		"envEvento": {
			"@xmlns": NAMESPACE_MDFE,
			"@versao": _VERSAO_LEIAUTE_MDFE,
			"idLote": id_lote.strip(),
			"evento": [e["evento"] for e in eventos],
		}
	}
