# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Eventos do MDF-e: cancelamento (`tpEvento` 110111, `evCancMDFe`), encerramento
(`tpEvento` 110112, `evEncMDFe`), inclusão de condutor (`tpEvento` 110114,
`evIncCondutorMDFe`), inclusão de DF-e (`tpEvento` 110115, `evIncDFeMDFe`) e confirmação
do serviço de transporte (`tpEvento` 110117, `evConfirmaServMDFe`).

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

Inclusão de DF-e (`tpEvento` 110115) — nome do arquivo diverge do nome do elemento
------------------------------------------------------------------------------------------
Verificado em `evInclusaoDFeMDFe_v3.00.xsd` (81 linhas, lido inteiro). **Achado real**: o
arquivo se chama `evInclusaoDFeMDFe_v3.00.xsd`, mas o elemento raiz que ele declara é
`evIncDFeMDFe` — nome do arquivo e nome do elemento **não coincidem** (mesma classe de
achado já vista antes neste projeto, ex. `cteTiposBasico_v4.00.xsd` do CT-e, onde o nome
do arquivo também não refletia seu conteúdo). Permite acrescentar uma NF-e ao manifesto
depois de já autorizado — `descEvento` tem as duas grafias já vistas em outros eventos
(`"Inclusão DF-e"`/`"Inclusao DF-e"`); `cMunCarrega`/`xMunCarrega` (município de
carregamento, um só, fora da lista); `infDoc` (lista, `maxOccurs="unbounded"`) — cada item
tem `cMunDescarga`/`xMunDescarga` (um município de descarregamento) e **um único**
`chNFe` (tipo `TChNFe`, não uma lista de chaves nem um grupo `infCTe`/`infNFe` como o
`infDoc` da orquestração principal do MDF-e, `fiscal.mdfe.montar_infdoc`) — **achado
real**: este evento só permite incluir NF-e, nunca CT-e, diferente do `infDoc` do
MDF-e completo (que aceita os dois). `chNFe` é validado com `ler_chave`, recusando
qualquer chave que não seja modelo 55 — mesma defesa em profundidade já aplicada em
outros pontos do projeto (`fiscal.cte.montar_infnfe`, `_montar_inf_entrega_nfe` do
CT-e).

Confirmação do serviço de transporte (`tpEvento` 110117) — o mais simples até agora
------------------------------------------------------------------------------------------
Verificado em `evConfirmaServMDFe_v3.00.xsd` (34 linhas, lido inteiro): `descEvento` (as
duas grafias já vistas em outros eventos) e só `nProt` — nenhum outro campo. `tpEvento` é
`"110117"`, não `"110116"` (esse número pertence ao pagamento da operação, ver abaixo) —
a ordem alfabética dos arquivos não reflete a ordem numérica dos códigos (`evConfirmaServ`
vem antes de `evPagtoOper` no alfabeto, mas `110117` é maior que `110116`) — mais um
lembrete de não presumir sequência a partir de nomes de arquivo.

Pagamento da operação de transporte (`tpEvento` 110116, `evPagtoOperMDFe`) — o evento mais
complexo do MDF-e
------------------------------------------------------------------------------------------
Verificado em `evPagtoOperMDFe_v3.00.xsd` (289 linhas, lido inteiro). `infViagens`
(quantidade e número da viagem, ambos `[0-9]{5}`) e `infPag` (lista, um item por
responsável pelo pagamento): `xNome` opcional, `(CPF|CNPJ|idEstrangeiro)` — três formas de
identificar o responsável, não duas como o resto do projeto; `Comp` (lista de componentes
do frete: `01` Vale Pedágio, `02` Impostos, `03` Despesas, `04` Frete, `99` Outros, cada um
com `vComp` e `xComp` opcional); `vContrato`; `indPag` (`0` à vista / `1` a prazo);
`vAdiant` opcional (documentado "usar apenas em pagamento à Prazo" — regra de negócio
aplicada aqui, não só decorativa); `indAntecipaAdiant` opcional (enumeração de um valor
só); `infPrazo` opcional (lista de parcelas: `nParcela`, `dVenc`, `vParcela`, "informar
somente se indPag for à Prazo" — mesma regra aplicada); `tpAntecip` opcional (`0` não
permite / `1` permite / `2` permite mediante confirmação); e `infBanc`, um `xs:choice`
entre três formas de receber o pagamento: banco+agência, CNPJ de instituição de pagamento
eletrônico do frete (`CNPJIPEF`), ou chave PIX.

**Achado real**: `idEstrangeiro` tem uma restrição inconsistente no próprio XSD —
`minLength=2`/`maxLength=20` combinados com um `xs:pattern`
(`([!-ÿ]{0}|[!-ÿ]{5,20})?`) que na prática aceita string **vazia** ou de 5 a 20
caracteres — nunca de 2 a 4, apesar do `minLength` declarado dizer "2". Este módulo valida
pelo `minLength`/`maxLength` documentados (2-20), não pelo padrão degenerado, e registra a
inconsistência aqui em vez de reproduzi-la silenciosamente.

Alteração do pagamento do serviço (`tpEvento` 110118, `evAlteracaoPagtoServMDFe`) — reuso
direto do `infPag` do pagamento da operação
------------------------------------------------------------------------------------------
Verificado em `evAlteracaoPagtoServMDFe_v3.00.xsd` (257 linhas, lido inteiro). **Achado
real de reuso, confirmado, não especulativo**: o `infPag` deste evento é
**estruturalmente idêntico**, campo a campo, ao `infPag` do pagamento da operação — a
única diferença de forma entre os dois eventos é que este **não tem** `infViagens` (faz
sentido: alterar o pagamento de uma operação já registrada não precisa repetir a
contagem de viagens). Por isso `ComponentePagamento`/`InfoBancaria`/`InfoPagamento` e as
funções `montar_componente_pagamento`/`montar_inf_banc`/`montar_inf_pag` são
compartilhadas entre os dois eventos — só a montagem do `evento` em si (com/sem
`infViagens`, `tpEvento`/`descEvento` diferentes) muda.

Reuso: `EventoInvalido`/`assinar_evento` de `evento.py`, sem alteração
------------------------------------------------------------------------------
Ambos já eram genéricos (não hardcodam `NAMESPACE_NFE`, só leem o que o dicionário
`evento` já tem) — reaproveitados direto, mesmo padrão já usado para o CT-e.

Funções puras: nenhuma dependência do Frappe.
"""

import re
from dataclasses import dataclass, field

from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave, validar_chave
from erpnext_brasil.fiscal.documento.evento import EventoInvalido, assinar_evento
from erpnext_brasil.fiscal.mdfe import NAMESPACE_MDFE
from erpnext_brasil.fiscal.mdfe_rodoviario import Condutor, MdfeRodoviarioInvalido, montar_condutor
from erpnext_brasil.fiscal.validators import validar_cnpj, validar_cpf

__all__ = [
	"INDICADOR_ANTECIPA_ADIANTAMENTO",
	"INDICADOR_ENCERRAMENTO_POR_TERCEIRO",
	"INDICADOR_PAGAMENTO_A_PRAZO",
	"INDICADOR_PAGAMENTO_A_VISTA",
	"JUSTIFICATIVA_MAXIMA_MDFE",
	"JUSTIFICATIVA_MINIMA_MDFE",
	"TIPO_ANTECIPACAO_NAO_PERMITE",
	"TIPO_ANTECIPACAO_PERMITE",
	"TIPO_ANTECIPACAO_PERMITE_COM_CONFIRMACAO",
	"TIPO_COMPONENTE_DESPESAS",
	"TIPO_COMPONENTE_FRETE",
	"TIPO_COMPONENTE_IMPOSTOS",
	"TIPO_COMPONENTE_OUTROS",
	"TIPO_COMPONENTE_VALE_PEDAGIO",
	"TIPO_EVENTO_ALTERACAO_PAGAMENTO_SERVICO_MDFE",
	"TIPO_EVENTO_CANCELAMENTO_MDFE",
	"TIPO_EVENTO_CONFIRMACAO_SERVICO_MDFE",
	"TIPO_EVENTO_ENCERRAMENTO_MDFE",
	"TIPO_EVENTO_INCLUSAO_CONDUTOR_MDFE",
	"TIPO_EVENTO_INCLUSAO_DFE_MDFE",
	"TIPO_EVENTO_PAGAMENTO_OPERACAO_MDFE",
	"ComponentePagamento",
	"Condutor",
	"DocumentoIncluido",
	"EventoInvalido",
	"InfoBancaria",
	"InfoPagamento",
	"ParcelaPagamento",
	"assinar_evento",
	"montar_componente_pagamento",
	"montar_condutor",
	"montar_env_evento_mdfe",
	"montar_evento_alteracao_pagamento_servico_mdfe",
	"montar_evento_cancelamento_mdfe",
	"montar_evento_confirmacao_servico_mdfe",
	"montar_evento_encerramento_mdfe",
	"montar_evento_inclusao_condutor_mdfe",
	"montar_evento_inclusao_dfe_mdfe",
	"montar_evento_pagamento_operacao_mdfe",
	"montar_inf_banc",
	"montar_inf_pag",
]

TIPO_EVENTO_CANCELAMENTO_MDFE = "110111"
TIPO_EVENTO_ENCERRAMENTO_MDFE = "110112"
TIPO_EVENTO_INCLUSAO_CONDUTOR_MDFE = "110114"
TIPO_EVENTO_INCLUSAO_DFE_MDFE = "110115"
TIPO_EVENTO_PAGAMENTO_OPERACAO_MDFE = "110116"
TIPO_EVENTO_CONFIRMACAO_SERVICO_MDFE = "110117"
TIPO_EVENTO_ALTERACAO_PAGAMENTO_SERVICO_MDFE = "110118"

TIPO_COMPONENTE_VALE_PEDAGIO = "01"
TIPO_COMPONENTE_IMPOSTOS = "02"
TIPO_COMPONENTE_DESPESAS = "03"
TIPO_COMPONENTE_FRETE = "04"
TIPO_COMPONENTE_OUTROS = "99"

_COMPONENTES_PAGAMENTO_VALIDOS = {
	TIPO_COMPONENTE_VALE_PEDAGIO,
	TIPO_COMPONENTE_IMPOSTOS,
	TIPO_COMPONENTE_DESPESAS,
	TIPO_COMPONENTE_FRETE,
	TIPO_COMPONENTE_OUTROS,
}

INDICADOR_PAGAMENTO_A_VISTA = "0"
INDICADOR_PAGAMENTO_A_PRAZO = "1"
_INDICADORES_PAGAMENTO_VALIDOS = {INDICADOR_PAGAMENTO_A_VISTA, INDICADOR_PAGAMENTO_A_PRAZO}

INDICADOR_ANTECIPA_ADIANTAMENTO = "1"

TIPO_ANTECIPACAO_NAO_PERMITE = "0"
TIPO_ANTECIPACAO_PERMITE = "1"
TIPO_ANTECIPACAO_PERMITE_COM_CONFIRMACAO = "2"
_TIPOS_ANTECIPACAO_VALIDOS = {
	TIPO_ANTECIPACAO_NAO_PERMITE,
	TIPO_ANTECIPACAO_PERMITE,
	TIPO_ANTECIPACAO_PERMITE_COM_CONFIRMACAO,
}
_VERSAO_LEIAUTE_MDFE = "3.00"

# `TJust` do MDF-e — numericamente igual ao do CT-e, mas verificado à parte (tipo
# diferente, de schema diferente) — ver docstring do módulo.
JUSTIFICATIVA_MINIMA_MDFE = 15
JUSTIFICATIVA_MAXIMA_MDFE = 255

# `TCodUfIBGE_EX` — as 27 UFs brasileiras mais "99" para Exterior (ver docstring do
# módulo). Confirmado em `tiposGeralMDFe_v3.00.xsd`.
_UFS_VALIDAS_ENCERRAMENTO_MDFE = {
	"11",
	"12",
	"13",
	"14",
	"15",
	"16",
	"17",
	"21",
	"22",
	"23",
	"24",
	"25",
	"26",
	"27",
	"28",
	"29",
	"31",
	"32",
	"33",
	"35",
	"41",
	"42",
	"43",
	"50",
	"51",
	"52",
	"53",
	"99",
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


@dataclass(frozen=True)
class DocumentoIncluido:
	"""Um item de `infDoc` do evento — um único município de descarregamento e uma
	única NF-e (nunca CT-e, ver docstring do módulo)."""

	codigo_municipio_descarga: str
	nome_municipio_descarga: str
	chave_nfe: str

	def __post_init__(self):
		if not (2 <= len(self.nome_municipio_descarga) <= 60):
			raise EventoInvalido(
				f"xMunDescarga deve ter de 2 a 60 caracteres, recebido {self.nome_municipio_descarga!r}",
				"nome_municipio_descarga",
			)


def _montar_doc_incluido(documento: DocumentoIncluido) -> dict:
	decomposta = ler_chave(documento.chave_nfe)

	if decomposta.modelo != "55":
		raise EventoInvalido(
			f"infDoc só aceita chave de NF-e (modelo 55), recebida chave de modelo "
			f"{decomposta.modelo} ({decomposta.documento})",
			"chave_nfe",
		)

	return {
		"cMunDescarga": documento.codigo_municipio_descarga,
		"xMunDescarga": documento.nome_municipio_descarga,
		"chNFe": decomposta.valor,
	}


def montar_evento_inclusao_dfe_mdfe(
	chave_acesso: str,
	protocolo: str,
	codigo_municipio_carrega: str,
	nome_municipio_carrega: str,
	documentos: list[DocumentoIncluido],
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) da inclusão de DF-e do MDF-e —
	acrescenta NF-e ao manifesto já autorizado.

	`documentos` é a lista de `infDoc` — cada item referencia uma única NF-e (nunca
	CT-e, ver docstring do módulo), validada via `ler_chave` e recusada se não for
	modelo 55, mesma defesa em profundidade já aplicada em outros pontos do projeto.
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	protocolo_limpo = (protocolo or "").strip()

	if not protocolo_limpo:
		raise EventoInvalido("O protocolo da autorização é obrigatório", "protocolo")

	if not (2 <= len(nome_municipio_carrega or "") <= 60):
		raise EventoInvalido(
			f"xMunCarrega deve ter de 2 a 60 caracteres, recebido {nome_municipio_carrega!r}",
			"nome_municipio_carrega",
		)

	if not documentos:
		raise EventoInvalido("infDoc precisa de ao menos um documento", "documentos")

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	inf_evento = {
		"@Id": _formatar_id_mdfe(chave, TIPO_EVENTO_INCLUSAO_DFE_MDFE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chMDFe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_INCLUSAO_DFE_MDFE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": {
			"@versaoEvento": _VERSAO_LEIAUTE_MDFE,
			"descEvento": "Inclusão DF-e",
			"nProt": protocolo_limpo,
			"cMunCarrega": codigo_municipio_carrega,
			"xMunCarrega": nome_municipio_carrega,
			"infDoc": [_montar_doc_incluido(d) for d in documentos],
		},
	}

	return {"evento": {"@xmlns": NAMESPACE_MDFE, "@versao": _VERSAO_LEIAUTE_MDFE, "infEvento": inf_evento}}


def montar_evento_confirmacao_servico_mdfe(
	chave_acesso: str,
	protocolo: str,
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) da confirmação do serviço de
	transporte do MDF-e — o mais simples da frente até agora, só `nProt`."""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	protocolo_limpo = (protocolo or "").strip()

	if not protocolo_limpo:
		raise EventoInvalido("O protocolo da autorização é obrigatório", "protocolo")

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	inf_evento = {
		"@Id": _formatar_id_mdfe(chave, TIPO_EVENTO_CONFIRMACAO_SERVICO_MDFE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chMDFe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_CONFIRMACAO_SERVICO_MDFE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": {
			"@versaoEvento": _VERSAO_LEIAUTE_MDFE,
			"descEvento": "Confirmação Serviço Transporte",
			"nProt": protocolo_limpo,
		},
	}

	return {"evento": {"@xmlns": NAMESPACE_MDFE, "@versao": _VERSAO_LEIAUTE_MDFE, "infEvento": inf_evento}}


@dataclass(frozen=True)
class ComponentePagamento:
	"""Um item de `Comp` — um componente do frete (vale-pedágio, impostos, despesas,
	frete, outros). `descricao` (`xComp`) é opcional no XSD mesmo para `tipo="99"`
	(Outros) — este módulo não inventa uma exigência que o schema não faz."""

	tipo: str
	valor: str
	descricao: str | None = None

	def __post_init__(self):
		if self.tipo not in _COMPONENTES_PAGAMENTO_VALIDOS:
			raise EventoInvalido(
				f"tpComp deve ser um de {sorted(_COMPONENTES_PAGAMENTO_VALIDOS)}, recebido {self.tipo!r}",
				"tipo",
			)


def montar_componente_pagamento(componente: ComponentePagamento) -> dict:
	item: dict = {"tpComp": componente.tipo, "vComp": str(componente.valor)}

	if componente.descricao is not None:
		item["xComp"] = componente.descricao

	return item


@dataclass(frozen=True)
class ParcelaPagamento:
	"""Um item de `infPrazo` — só informado quando o pagamento é a prazo (ver
	`InfoPagamento.__post_init__`)."""

	numero: int
	data_vencimento: str
	valor: str

	def __post_init__(self):
		if not (1 <= self.numero <= 999):
			raise EventoInvalido(f"nParcela deve estar entre 1 e 999, recebido {self.numero}", "numero")


def montar_parcela_pagamento(parcela: ParcelaPagamento) -> dict:
	return {
		"nParcela": f"{parcela.numero:03d}",
		"dVenc": parcela.data_vencimento,
		"vParcela": str(parcela.valor),
	}


@dataclass(frozen=True)
class InfoBancaria:
	"""`infBanc` — `xs:choice` entre três formas de receber o pagamento: banco+agência,
	CNPJ de instituição de pagamento eletrônico do frete (`CNPJIPEF`), ou chave PIX.
	Exatamente uma das três deve ser informada."""

	codigo_banco: str | None = None
	codigo_agencia: str | None = None
	cnpj_ipef: str | None = None
	chave_pix: str | None = None

	def __post_init__(self):
		variantes = [
			bool(self.codigo_banco or self.codigo_agencia),
			bool(self.cnpj_ipef),
			bool(self.chave_pix),
		]

		if sum(variantes) != 1:
			raise EventoInvalido(
				"infBanc exige exatamente uma forma: banco+agência, CNPJIPEF ou PIX",
				"informacao_bancaria",
			)

		if bool(self.codigo_banco) != bool(self.codigo_agencia):
			raise EventoInvalido(
				"codigo_banco e codigo_agencia devem ser informados juntos", "informacao_bancaria"
			)


def montar_inf_banc(info: InfoBancaria) -> dict:
	if info.codigo_banco:
		if not (3 <= len(info.codigo_banco) <= 5):
			raise EventoInvalido(
				f"codBanco deve ter de 3 a 5 caracteres, recebido {info.codigo_banco!r}",
				"codigo_banco",
			)

		if not (1 <= len(info.codigo_agencia) <= 10):
			raise EventoInvalido(
				f"codAgencia deve ter de 1 a 10 caracteres, recebido {info.codigo_agencia!r}",
				"codigo_agencia",
			)

		return {"infBanc": {"codBanco": info.codigo_banco, "codAgencia": info.codigo_agencia}}

	if info.cnpj_ipef:
		try:
			cnpj = validar_cnpj(info.cnpj_ipef)
		except ValueError as e:
			raise EventoInvalido(f"CNPJIPEF inválido: {e}", "cnpj_ipef") from e

		return {"infBanc": {"CNPJIPEF": cnpj}}

	if not (2 <= len(info.chave_pix) <= 60):
		raise EventoInvalido(f"PIX deve ter de 2 a 60 caracteres, recebido {info.chave_pix!r}", "chave_pix")

	return {"infBanc": {"PIX": info.chave_pix}}


@dataclass(frozen=True)
class InfoPagamento:
	"""Um item de `infPag` — quem paga o frete e como. `(cpf|cnpj|id_estrangeiro)` é um
	`xs:choice`: exatamente um dos três identifica o responsável (achado real: o MDF-e
	aceita responsável estrangeiro, diferente da maioria dos grupos deste projeto, que
	só alternam entre CPF e CNPJ).
	"""

	componentes: list[ComponentePagamento]
	valor_contrato: str
	indicador_pagamento: str
	informacao_bancaria: InfoBancaria
	nome: str | None = None
	cpf: str | None = None
	cnpj: str | None = None
	id_estrangeiro: str | None = None
	valor_adiantamento: str | None = None
	antecipa_adiantamento: bool = False
	parcelas: list[ParcelaPagamento] = field(default_factory=list)
	tipo_antecipacao: str | None = None

	def __post_init__(self):
		if not self.componentes:
			raise EventoInvalido("Comp precisa de ao menos um componente", "componentes")

		if self.indicador_pagamento not in _INDICADORES_PAGAMENTO_VALIDOS:
			raise EventoInvalido(
				f"indPag deve ser um de {sorted(_INDICADORES_PAGAMENTO_VALIDOS)}, "
				f"recebido {self.indicador_pagamento!r}",
				"indicador_pagamento",
			)

		identificadores = [bool(self.cpf), bool(self.cnpj), bool(self.id_estrangeiro)]

		if sum(identificadores) != 1:
			raise EventoInvalido("informe exatamente um entre cpf, cnpj e id_estrangeiro", "cpf")

		a_prazo = self.indicador_pagamento == INDICADOR_PAGAMENTO_A_PRAZO

		if self.valor_adiantamento is not None and not a_prazo:
			raise EventoInvalido("vAdiant só é usado em pagamento à Prazo (indPag=1)", "valor_adiantamento")

		if self.parcelas and not a_prazo:
			raise EventoInvalido("infPrazo só é informado em pagamento à Prazo (indPag=1)", "parcelas")

		if self.tipo_antecipacao is not None and self.tipo_antecipacao not in _TIPOS_ANTECIPACAO_VALIDOS:
			raise EventoInvalido(
				f"tpAntecip deve ser um de {sorted(_TIPOS_ANTECIPACAO_VALIDOS)}, "
				f"recebido {self.tipo_antecipacao!r}",
				"tipo_antecipacao",
			)

		if self.id_estrangeiro is not None and not (2 <= len(self.id_estrangeiro) <= 20):
			raise EventoInvalido(
				f"idEstrangeiro deve ter de 2 a 20 caracteres, recebido {self.id_estrangeiro!r}",
				"id_estrangeiro",
			)


def montar_inf_pag(pagamento: InfoPagamento) -> dict:
	grupo: dict = {}

	if pagamento.nome is not None:
		if not (2 <= len(pagamento.nome) <= 60):
			raise EventoInvalido(f"xNome deve ter de 2 a 60 caracteres, recebido {pagamento.nome!r}", "nome")

		grupo["xNome"] = pagamento.nome

	if pagamento.cpf is not None:
		try:
			grupo["CPF"] = validar_cpf(pagamento.cpf)
		except ValueError as e:
			raise EventoInvalido(f"CPF do responsável pelo pagamento inválido: {e}", "cpf") from e
	elif pagamento.cnpj is not None:
		try:
			grupo["CNPJ"] = validar_cnpj(pagamento.cnpj)
		except ValueError as e:
			raise EventoInvalido(f"CNPJ do responsável pelo pagamento inválido: {e}", "cnpj") from e
	else:
		grupo["idEstrangeiro"] = pagamento.id_estrangeiro

	grupo["Comp"] = [montar_componente_pagamento(c) for c in pagamento.componentes]
	grupo["vContrato"] = str(pagamento.valor_contrato)
	grupo["indPag"] = pagamento.indicador_pagamento

	if pagamento.valor_adiantamento is not None:
		grupo["vAdiant"] = str(pagamento.valor_adiantamento)

	if pagamento.antecipa_adiantamento:
		grupo["indAntecipaAdiant"] = INDICADOR_ANTECIPA_ADIANTAMENTO

	if pagamento.parcelas:
		grupo["infPrazo"] = [montar_parcela_pagamento(p) for p in pagamento.parcelas]

	if pagamento.tipo_antecipacao is not None:
		grupo["tpAntecip"] = pagamento.tipo_antecipacao

	grupo.update(montar_inf_banc(pagamento.informacao_bancaria))

	return grupo


def montar_evento_pagamento_operacao_mdfe(
	chave_acesso: str,
	protocolo: str,
	quantidade_viagens: str,
	numero_viagem: str,
	pagamentos: list[InfoPagamento],
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) do pagamento da operação de
	transporte do MDF-e — o evento mais complexo desta frente (ver docstring do
	módulo)."""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	protocolo_limpo = (protocolo or "").strip()

	if not protocolo_limpo:
		raise EventoInvalido("O protocolo da autorização é obrigatório", "protocolo")

	if not re.match(r"^[0-9]{5}$", quantidade_viagens or ""):
		raise EventoInvalido(
			f"qtdViagens deve ter 5 dígitos, recebido {quantidade_viagens!r}", "quantidade_viagens"
		)

	if not re.match(r"^[0-9]{5}$", numero_viagem or ""):
		raise EventoInvalido(f"nroViagem deve ter 5 dígitos, recebido {numero_viagem!r}", "numero_viagem")

	if not pagamentos:
		raise EventoInvalido("infPag precisa de ao menos um pagamento", "pagamentos")

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	inf_evento = {
		"@Id": _formatar_id_mdfe(chave, TIPO_EVENTO_PAGAMENTO_OPERACAO_MDFE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chMDFe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_PAGAMENTO_OPERACAO_MDFE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": {
			"@versaoEvento": _VERSAO_LEIAUTE_MDFE,
			"descEvento": "Pagamento Operação MDF-e",
			"nProt": protocolo_limpo,
			"infViagens": {"qtdViagens": quantidade_viagens, "nroViagem": numero_viagem},
			"infPag": [montar_inf_pag(p) for p in pagamentos],
		},
	}

	return {"evento": {"@xmlns": NAMESPACE_MDFE, "@versao": _VERSAO_LEIAUTE_MDFE, "infEvento": inf_evento}}


def montar_evento_alteracao_pagamento_servico_mdfe(
	chave_acesso: str,
	protocolo: str,
	pagamentos: list[InfoPagamento],
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) da alteração do pagamento do
	serviço do MDF-e.

	`infPag` reaproveita exatamente a mesma forma/validação do pagamento da operação
	(`InfoPagamento`/`montar_inf_pag`) — achado real confirmado por leitura do XSD, não
	suposição (ver docstring do módulo). A única diferença é que este evento **não**
	tem `infViagens`.
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	protocolo_limpo = (protocolo or "").strip()

	if not protocolo_limpo:
		raise EventoInvalido("O protocolo da autorização é obrigatório", "protocolo")

	if not pagamentos:
		raise EventoInvalido("infPag precisa de ao menos um pagamento", "pagamentos")

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	inf_evento = {
		"@Id": _formatar_id_mdfe(chave, TIPO_EVENTO_ALTERACAO_PAGAMENTO_SERVICO_MDFE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chMDFe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_ALTERACAO_PAGAMENTO_SERVICO_MDFE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": {
			"@versaoEvento": _VERSAO_LEIAUTE_MDFE,
			"descEvento": "Alteração Pagamento Serviço MDFe",
			"nProt": protocolo_limpo,
			"infPag": [montar_inf_pag(p) for p in pagamentos],
		},
	}

	return {"evento": {"@xmlns": NAMESPACE_MDFE, "@versao": _VERSAO_LEIAUTE_MDFE, "infEvento": inf_evento}}


def montar_env_evento_mdfe(eventos: list[dict], id_lote: str) -> dict:
	"""Monta `envEvento` do MDF-e — mesma disciplina de `evento.montar_env_evento`
	(até 20 eventos por lote), com o namespace do MDF-e."""
	if not eventos:
		raise EventoInvalido("O lote de eventos precisa de ao menos um evento", "eventos")

	if len(eventos) > 20:
		raise EventoInvalido(f"Um lote de eventos admite no máximo 20, recebidos {len(eventos)}", "eventos")

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
