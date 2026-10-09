# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Inutilização de faixa de numeração de NF-e (`NfeInutilizacao4`).

Diferente de cancelamento e carta de correção
------------------------------------------------
Cancelamento e CC-e são **eventos** (`NFeRecepcaoEvento4`, grupo `TEvento`, o `evento.py`
deste pacote) — dizem respeito a uma NF-e que já existe e tem chave de acesso.
Inutilização é outra operação (`inutNFe`/`TInutNFe`, webservice próprio
`NfeInutilizacao4`), sem lote, sem `idLote`, sem `infEvento`: comunica que uma faixa de
numeração **nunca chegou a virar documento** — não há chave de acesso porque a NF-e
nunca foi emitida. Por isso vive em módulo à parte, e a porta `TransporteFiscal` expõe
`inutilizar` com uma assinatura totalmente diferente de `cancelar`/`corrigir` (sem
`chave_acesso`, com `ano`/`cnpj`/`modelo`/`serie`/faixa de números).

Estrutura confirmada em `leiauteInutNFe_v4.00.xsd` (pacote oficial da NF-e, mesmo
princípio das demais operações deste app: lida direto do XSD, nunca de memória ou blog).

A ordem confirmada de `infInut`
----------------------------------
`tpAmb, xServ, cUF, ano, CNPJ, mod, serie, nNFIni, nNFFin, xJust`

`xServ` é fixo em `"INUTILIZAR"` — único valor que o XSD aceita. `xJust` vai de 15 a 255
caracteres (`TJust`) — **não** é o mesmo teto de 256 do cancelamento nem de 1000 da CC-e;
cada operação tem seu próprio limite, confirmado em cada schema, nunca assumido por
analogia com a anterior (foi exatamente esse tipo de suposição que gerou o campo
`cMunFGISS` inventado por engano em outro módulo deste app).

A pegadinha do `@Id`
----------------------
Padrão confirmado: `ID[0-9]{41}`, e a regra (decompondo um `Id` real de exemplo) é
`"ID" + cUF(2) + ano(2) + CNPJ(14) + mod(2) + serie(3, zero à esquerda) + nNFIni(9, zero
à esquerda) + nNFFin(9, zero à esquerda)` — soma 41. Diferente da pegadinha do evento
(que é sobre duas representações do mesmo número), esta é sobre **largura fixa por zero
à esquerda** em campos que, no corpo do documento, não a levam (`TSerie`/`TNF` no XSD
não têm zero à esquerda — só o `@Id` os preenche).

CNPJ alfanumérico: confirmado e aceito desde 2026-08-29
------------------------------------------------------------------
A Nota Técnica 2026.004 (v1.01, 08/06/2026) inclui o layout de `NFeInutilizacao` entre os
atualizados para aceitar CNPJ alfanumérico (IN RFB 2.229/2024). Isto ficou como gap
deliberado enquanto o XSD atualizado não tinha sido lido diretamente — o pacote
`nfephp-org/sped-nfe` espelhava, até então, só o pacote antigo (`PL_009_V4`/`PL_010_V1`,
`TCnpj` = `[0-9]{14}`). Confirmado em 2026-08-29 no pacote **`PL_010_V1.30`** do mesmo
repositório: `tiposBasico_v4.00.xsd` já define `TCnpj` como `[0-9A-Z]{12}[0-9]{2}`, e
`leiauteInutNFe_v4.00.xsd` desse mesmo pacote referencia `CNPJ` a esse tipo — a sequência
de `infInut` não mudou (segue a mesma ordem confirmada acima). O `@Id` também não muda de
tamanho — o CNPJ continua ocupando 14 posições, só passa a aceitar letra nas 12
primeiras. `montar_inutilizacao` usa `validar_cnpj` (que já produz esse mesmo padrão)
sem nenhuma restrição adicional.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass

from erpnext_brasil.fiscal.codigos.uf import CODIGO_UF_POR_SIGLA
from erpnext_brasil.fiscal.documento.assinatura import Assinador, montar_signature
from erpnext_brasil.fiscal.documento.nfe import NAMESPACE_NFE
from erpnext_brasil.fiscal.documento.resposta_sefaz import RespostaSefazInvalida
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.validators import validar_cnpj

__all__ = [
	"CODIGOS_UF_IBGE",
	"CODIGO_SUCESSO_INUTILIZACAO",
	"CODIGO_UF_POR_SIGLA",
	"JUSTIFICATIVA_MAXIMA",
	"JUSTIFICATIVA_MINIMA",
	"MODELOS_VALIDOS",
	"VERSAO_INUTILIZACAO",
	"InutilizacaoInvalida",
	"RetornoInutilizacao",
	"assinar_inutilizacao",
	"interpretar_retorno_inutilizacao",
	"montar_inutilizacao",
	"validar_faixa_a_inutilizar",
]

VERSAO_INUTILIZACAO = "4.00"

# Os 26 estados + DF, confirmados em TCodUfIBGE (tiposBasico_v4.00.xsd).
CODIGOS_UF_IBGE = frozenset(
	{
		"11", "12", "13", "14", "15", "16", "17", "21", "22", "23", "24", "25", "26",
		"27", "28", "29", "31", "32", "33", "35", "41", "42", "43", "50", "51", "52", "53",
	}
)  # fmt: skip

# A tabela vivia aqui, com um comentário dizendo que a conversão "só é necessária aqui,
# porque só a inutilização carrega esse campo no corpo do documento". Deixou de ser verdade
# quando a montagem passou a precisar do `cUF` do `ide` — mudou-se para
# `fiscal/codigos/uf.py`, e o nome continua importável daqui por compatibilidade.

MODELOS_VALIDOS = frozenset({"55", "65"})

# TJust deste layout: 15 a 255 — diferente do cancelamento (256) e da CC-e (1000).
JUSTIFICATIVA_MINIMA = 15
JUSTIFICATIVA_MAXIMA = 255

# Único código de sucesso confirmado — sem o par lote/evento das outras operações,
# porque inutilização não é assíncrona nem passa por lote.
CODIGO_SUCESSO_INUTILIZACAO = "102"


class InutilizacaoInvalida(ValueError):
	def __init__(self, mensagem: str, campo: str = ""):
		super().__init__(mensagem)
		self.campo = campo


def _numero_ou_erro(valor: str, campo: str) -> str:
	texto = (valor or "").strip()

	if not texto.isdigit() or texto.startswith("0") or int(texto) == 0:
		raise InutilizacaoInvalida(
			f"{campo} deve ser um número positivo sem zero à esquerda, recebido {valor!r}", campo
		)

	if len(texto) > 9:
		raise InutilizacaoInvalida(f"{campo} não pode ter mais de 9 dígitos, recebido {valor!r}", campo)

	return texto


def validar_faixa_a_inutilizar(inicio: int, fim: int, ultimo_numero: int, fechados: set[int]) -> None:
	"""A faixa pedida só pode cobrir números **consumidos** e **sem desfecho que feche**.

	- acima de `ultimo_numero` seria inutilizar número que o contador ainda vai alocar;
	- em `fechados` (autorizado, denegado, cancelado ou já inutilizado) a SEFAZ recusaria — melhor recusar antes,
	  com o número que atrapalha na mensagem, do que gastar uma chamada e um registro de rejeição.
	"""
	if inicio < 1 or fim < inicio:
		raise InutilizacaoInvalida(f"faixa inválida: {inicio}-{fim}", "faixa")

	if fim > ultimo_numero:
		raise InutilizacaoInvalida(
			f"a faixa vai até {fim}, mas a série só consumiu até {ultimo_numero}: não se inutiliza número "
			"que ainda não foi alocado",
			"faixa",
		)

	ocupados = sorted(n for n in fechados if inicio <= n <= fim)

	if ocupados:
		raise InutilizacaoInvalida(
			f"a faixa {inicio}-{fim} inclui número(s) que já têm desfecho e não podem ser inutilizados: "
			f"{ocupados[:5]}",
			"faixa",
		)


def _formatar_id(cuf: str, ano: str, cnpj: str, modelo: str, serie: str, nfini: str, nffin: str) -> str:
	"""`"ID" + cUF(2) + ano(2) + CNPJ(14) + mod(2) + serie(3) + nNFIni(9) + nNFFin(9)`,
	cada campo numérico com zero à esquerda até a largura fixa — mesmo quando o campo
	correspondente no corpo do documento não leva zero (ver docstring do módulo)."""
	return f"ID{cuf}{ano}{cnpj}{modelo}{serie.zfill(3)}{nfini.zfill(9)}{nffin.zfill(9)}"


def montar_inutilizacao(
	cuf: str,
	ano: str,
	cnpj: str,
	modelo: str,
	serie: str,
	numero_inicial: str,
	numero_final: str,
	justificativa: str,
	ambiente: str = "2",
) -> dict:
	"""Monta a árvore `inutNFe` (sem `Signature` — ver `assinar_inutilizacao`).

	`serie`/`numero_inicial`/`numero_final` entram sem zero à esquerda (como o corpo do
	documento exige) e só ganham padding dentro do `@Id`, nunca no próprio elemento.
	"""
	cuf_limpo = (cuf or "").strip()

	if cuf_limpo not in CODIGOS_UF_IBGE:
		raise InutilizacaoInvalida(f"cUF {cuf!r} não é um código de UF válido (tabela IBGE)", "cuf")

	ano_limpo = (ano or "").strip()

	if not (len(ano_limpo) == 2 and ano_limpo.isdigit()):
		raise InutilizacaoInvalida(f"ano deve ter 2 dígitos (AA), recebido {ano!r}", "ano")

	try:
		cnpj_valido = validar_cnpj(cnpj)
	except ValueError as e:
		raise InutilizacaoInvalida(f"CNPJ inválido: {e}", "cnpj") from e

	# CNPJ alfanumérico aceito desde 2026-08-29 — ver a seção "CNPJ alfanumérico" na
	# docstring do módulo: `TCnpj` do XSD pós-NT-2026.004 (`leiauteInutNFe_v4.00.xsd`,
	# pacote PL_010_V1.30) confirma `[0-9A-Z]{12}[0-9]{2}`, o mesmo padrão que
	# `validar_cnpj` já produz. `@Id` não muda de tamanho (CNPJ continua 14 caracteres),
	# só passa a aceitar letra nas 12 primeiras posições.

	if modelo not in MODELOS_VALIDOS:
		raise InutilizacaoInvalida(f"mod deve ser '55' ou '65', recebido {modelo!r}", "modelo")

	serie_valida = _numero_ou_erro(serie, "serie") if serie != "0" else "0"
	nfini = _numero_ou_erro(numero_inicial, "numero_inicial")
	nffin = _numero_ou_erro(numero_final, "numero_final")

	if int(nfini) > int(nffin):
		raise InutilizacaoInvalida(
			f"numero_inicial ({nfini}) não pode ser maior que numero_final ({nffin})",
			"numero_final",
		)

	texto_justificativa = (justificativa or "").strip()

	if not (JUSTIFICATIVA_MINIMA <= len(texto_justificativa) <= JUSTIFICATIVA_MAXIMA):
		raise InutilizacaoInvalida(
			f"A justificativa deve ter de {JUSTIFICATIVA_MINIMA} a {JUSTIFICATIVA_MAXIMA} "
			f"caracteres, recebidos {len(texto_justificativa)}",
			"justificativa",
		)

	inf_inut = {
		"@Id": _formatar_id(cuf_limpo, ano_limpo, cnpj_valido, modelo, serie_valida, nfini, nffin),
		"tpAmb": ambiente,
		"xServ": "INUTILIZAR",
		"cUF": cuf_limpo,
		"ano": ano_limpo,
		"CNPJ": cnpj_valido,
		"mod": modelo,
		"serie": serie_valida,
		"nNFIni": nfini,
		"nNFFin": nffin,
		"xJust": texto_justificativa,
	}

	return {"inutNFe": {"@xmlns": NAMESPACE_NFE, "@versao": VERSAO_INUTILIZACAO, "infInut": inf_inut}}


def assinar_inutilizacao(inut_nfe: dict, assinador: Assinador) -> dict:
	"""Assina `infInut` e anexa `Signature` como irmão — mesmo padrão de `assinar_nfe` e
	`evento.assinar_evento`, e mesma obrigatoriedade: `TInutNFe` exige `Signature` com
	cardinalidade 1-1."""
	raiz = inut_nfe["inutNFe"]
	id_elemento = raiz["infInut"]["@Id"]
	xml = para_xml(inut_nfe).encode("utf-8")

	material = assinador.assinar(xml, id_elemento)
	signature = montar_signature(id_elemento, material)

	return {"inutNFe": {**raiz, **signature}}


@dataclass(frozen=True)
class RetornoInutilizacao:
	"""Leitura estruturada de `retInutNFe` — sem par lote/evento: um único `cStat`,
	porque inutilização não passa por lote nem é assíncrona."""

	cstat: str
	motivo: str
	protocolo: str | None = None
	data_registro: str | None = None

	@property
	def homologada(self) -> bool:
		return self.cstat == CODIGO_SUCESSO_INUTILIZACAO


def interpretar_retorno_inutilizacao(xml_resposta: str | bytes) -> RetornoInutilizacao:
	"""Interpreta `retInutNFe` (a resposta de `NFeInutilizacao4`). Mesma disciplina do
	resto do app: `lxml` com `local-name()` via `.xpath()`, nunca `.find()`."""
	from lxml import etree

	bruto = xml_resposta.encode("utf-8") if isinstance(xml_resposta, str) else xml_resposta

	try:
		raiz = etree.fromstring(bruto)
	except etree.XMLSyntaxError as e:
		raise RespostaSefazInvalida(f"Resposta da SEFAZ não é XML válido: {e}") from e

	def filho_direto(no, nome: str) -> str | None:
		encontrados = no.xpath(f".//*[local-name()='{nome}']")

		return encontrados[0].text.strip() if encontrados and encontrados[0].text else None

	cstat = filho_direto(raiz, "cStat")

	if cstat is None:
		raise RespostaSefazInvalida("Resposta sem cStat — não é um retInutNFe reconhecível")

	return RetornoInutilizacao(
		cstat=cstat,
		motivo=filho_direto(raiz, "xMotivo") or "",
		protocolo=filho_direto(raiz, "nProt"),
		data_registro=filho_direto(raiz, "dhRecbto"),
	)
