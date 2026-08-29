# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Montagem do documento NF-e: os grupos `ide`, `emit`, `dest` e `infNFe`.

O que este módulo devolve
-------------------------
Uma árvore de dicionários com os nomes oficiais das tags — não XML pronto. Mesmo motivo
de `ibs_cbs_xml.py`: o ACBrLib consome INI, a ACBr API consome JSON, e emitir XML aqui
obrigaria todo adaptador a desmontá-lo de volta. Dicionário ainda se testa por igualdade.

A consistência que o módulo garante
-----------------------------------
A chave de acesso **repete** dados que também vivem em `ide` — UF, ano/mês, CNPJ do
emitente, modelo, série, número, tipo de emissão e código numérico. Duas fontes para o
mesmo dado é onde divergência silenciosa nasce: um sistema que gere a chave de um lado e
preencha o `ide` de outro acaba emitindo documento cuja chave não corresponde ao próprio
conteúdo.

Aqui a chave é **derivada** do `ide`, nunca informada em paralelo, e o `cDV` do `ide` sai
do mesmo cálculo. Não há como divergirem.

Regras de validação implementadas
---------------------------------
- **Rejeição 897 (regra B03-10)**: o `cNF` não pode ser igual ao `nNF`, nem ter todos os
  dígitos iguais. Vigora em produção desde 02/09/2019, e existe para dificultar código de
  segurança fraco.
- **Emitente é sempre pessoa jurídica com CNPJ**; destinatário aceita CNPJ, CPF ou
  identificação de estrangeiro — o XSD modela isso como escolha exclusiva.

Funções puras: nenhuma dependência do Frappe.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime

from erpnext_brasil.fiscal.documento.assinatura import Assinador, montar_signature
from erpnext_brasil.fiscal.documento.chave_acesso import calcular_dv, montar_chave
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.validators import limpar, validar_cnpj, validar_cpf_cnpj

__all__ = [
	"MODELO_NFCE",
	"MODELO_NFE",
	"NAMESPACE_NFE",
	"Destinatario",
	"Emitente",
	"Identificacao",
	"NFeInvalida",
	"assinar_nfe",
	"montar_dest",
	"montar_emit",
	"montar_ide",
	"montar_infnfe",
	"montar_nfe",
]

NAMESPACE_NFE = "http://www.portalfiscal.inf.br/nfe"

MODELO_NFE = "55"
MODELO_NFCE = "65"

# Identificador de local de destino da operação (campo `idDest`).
DESTINO_INTERNA = "1"
DESTINO_INTERESTADUAL = "2"
DESTINO_EXTERIOR = "3"

_SEQUENCIA_TRIVIAL = re.compile(r"^(\d)\1*$")


class NFeInvalida(ValueError):
	"""Dado que impediria a autorização do documento."""

	def __init__(self, mensagem: str, campo: str = ""):
		super().__init__(mensagem)
		self.campo = campo


def _obrigatorio(valor, campo: str) -> str:
	texto = str(valor or "").strip()

	if not texto:
		raise NFeInvalida(f"O campo {campo} é obrigatório na NF-e", campo)

	return texto


@dataclass(frozen=True)
class Identificacao:
	"""Dados que identificam o documento — origem do grupo `ide` e da chave."""

	uf: str
	municipio_fato_gerador: str
	natureza_operacao: str
	serie: str
	numero: str
	codigo_numerico: str
	emissao: datetime
	tipo_operacao: str = "1"
	"""0 = entrada, 1 = saída."""
	destino: str = DESTINO_INTERNA
	modelo: str = MODELO_NFE
	tipo_emissao: str = "1"
	ambiente: str = "2"
	"""1 = produção, 2 = homologação. O padrão é homologação de propósito: emitir em
	produção precisa ser escolha consciente, não o que acontece se o campo for esquecido."""
	finalidade: str = "1"
	consumidor_final: str = "0"
	presenca: str = "1"

	def validar(self) -> None:
		"""Pré-condições do grupo `ide`, incluindo a regra da rejeição 897."""
		numero = limpar(self.numero).lstrip("0") or "0"
		codigo = limpar(self.codigo_numerico).lstrip("0") or "0"

		if numero == codigo:
			raise NFeInvalida(
				"O código numérico (cNF) não pode ser igual ao número da nota (nNF) — "
				"rejeição 897, regra B03-10",
				"codigo_numerico",
			)

		if _SEQUENCIA_TRIVIAL.match(limpar(self.codigo_numerico)):
			raise NFeInvalida(
				"O código numérico (cNF) não pode ter todos os dígitos iguais — "
				"rejeição 897, regra B03-10",
				"codigo_numerico",
			)

		if self.modelo not in (MODELO_NFE, MODELO_NFCE):
			raise NFeInvalida(
				f"Modelo deve ser {MODELO_NFE} (NF-e) ou {MODELO_NFCE} (NFC-e), "
				f"recebido {self.modelo!r}",
				"modelo",
			)


@dataclass(frozen=True)
class Emitente:
	"""Quem emite. Sempre pessoa jurídica com CNPJ e Inscrição Estadual."""

	cnpj: str
	nome: str
	inscricao_estadual: str
	regime_tributario: str
	"""CRT: 1 = Simples Nacional, 2 = Simples com excesso de sublimite, 3 = Regime Normal."""
	endereco: dict = field(default_factory=dict)
	nome_fantasia: str = ""
	inscricao_municipal: str = ""
	cnae: str = ""


@dataclass(frozen=True)
class Destinatario:
	"""Para quem se emite. CNPJ, CPF ou identificação de estrangeiro — nunca dois."""

	nome: str
	indicador_ie: str
	"""1 = contribuinte, 2 = isento, 9 = não contribuinte."""
	cnpj_cpf: str = ""
	identificacao_estrangeiro: str = ""
	inscricao_estadual: str = ""
	endereco: dict = field(default_factory=dict)
	suframa: str = ""


def montar_ide(identificacao: Identificacao, chave: str) -> dict:
	"""Monta o grupo `ide`.

	Recebe a chave já pronta para extrair dela o `cDV`, garantindo que os dois nunca
	divirjam — o dígito publicado no `ide` é sempre o da chave que acompanha o documento.
	"""
	identificacao.validar()

	return {
		"cUF": identificacao.uf,
		"cNF": str(identificacao.codigo_numerico).rjust(8, "0"),
		"natOp": _obrigatorio(identificacao.natureza_operacao, "natureza da operação"),
		"mod": identificacao.modelo,
		"serie": str(identificacao.serie).lstrip("0") or "0",
		"nNF": str(identificacao.numero).lstrip("0") or "0",
		# O layout exige data com fuso; sem ele a SEFAZ rejeita.
		"dhEmi": identificacao.emissao.isoformat(),
		"tpNF": identificacao.tipo_operacao,
		"idDest": identificacao.destino,
		"cMunFG": _obrigatorio(identificacao.municipio_fato_gerador, "município do fato gerador"),
		"tpImp": "1",
		"tpEmis": identificacao.tipo_emissao,
		"cDV": chave[-1],
		"tpAmb": identificacao.ambiente,
		"finNFe": identificacao.finalidade,
		"indFinal": identificacao.consumidor_final,
		"indPres": identificacao.presenca,
		"procEmi": "0",
		"verProc": "erpnext_brasil",
	}


def montar_emit(emitente: Emitente) -> dict:
	"""Monta o grupo `emit`. O CNPJ é validado aqui — inclusive alfanumérico."""
	try:
		cnpj = validar_cnpj(emitente.cnpj)
	except ValueError as e:
		raise NFeInvalida(f"CNPJ do emitente inválido: {e}", "cnpj") from e

	grupo = {
		"CNPJ": cnpj,
		"xNome": _obrigatorio(emitente.nome, "razão social do emitente"),
		"enderEmit": dict(emitente.endereco),
		"IE": _obrigatorio(emitente.inscricao_estadual, "Inscrição Estadual do emitente"),
		"CRT": _obrigatorio(emitente.regime_tributario, "regime tributário (CRT)"),
	}

	# Campos opcionais entram só quando preenchidos: tag vazia é rejeição, não omissão.
	if emitente.nome_fantasia:
		grupo["xFant"] = emitente.nome_fantasia

	if emitente.inscricao_municipal:
		grupo["IM"] = emitente.inscricao_municipal

	if emitente.cnae:
		grupo["CNAE"] = emitente.cnae

	return grupo


def montar_dest(destinatario: Destinatario) -> dict:
	"""Monta o grupo `dest`.

	CNPJ, CPF e identificação de estrangeiro são mutuamente exclusivos no XSD — informar
	mais de um é rejeição. A escolha é feita pelo que veio preenchido, e informar os dois
	é erro explícito em vez de escolha silenciosa.
	"""
	tem_documento = bool(limpar(destinatario.cnpj_cpf))
	tem_estrangeiro = bool(destinatario.identificacao_estrangeiro.strip())

	if tem_documento and tem_estrangeiro:
		raise NFeInvalida(
			"Destinatário não pode ter CNPJ/CPF e identificação de estrangeiro ao mesmo "
			"tempo: o layout admite apenas um",
			"cnpj_cpf",
		)

	if not tem_documento and not tem_estrangeiro:
		raise NFeInvalida(
			"Destinatário precisa de CNPJ, CPF ou identificação de estrangeiro", "cnpj_cpf"
		)

	grupo: dict = {}

	if tem_documento:
		try:
			documento = validar_cpf_cnpj(destinatario.cnpj_cpf)
		except ValueError as e:
			raise NFeInvalida(f"CPF/CNPJ do destinatário inválido: {e}", "cnpj_cpf") from e

		grupo["CNPJ" if len(documento) == 14 else "CPF"] = documento
	else:
		grupo["idEstrangeiro"] = destinatario.identificacao_estrangeiro.strip()

	grupo["xNome"] = _obrigatorio(destinatario.nome, "nome do destinatário")

	if destinatario.endereco:
		grupo["enderDest"] = dict(destinatario.endereco)

	grupo["indIEDest"] = _obrigatorio(destinatario.indicador_ie, "indicador de IE do destinatário")

	# A IE só é informada quando o destinatário é contribuinte; informá-la para isento
	# ou não contribuinte é rejeição.
	if destinatario.indicador_ie == "1":
		grupo["IE"] = _obrigatorio(
			destinatario.inscricao_estadual, "Inscrição Estadual do destinatário"
		)

	if destinatario.suframa:
		grupo["ISUF"] = destinatario.suframa

	return grupo


def montar_infnfe(
	identificacao: Identificacao,
	emitente: Emitente,
	destinatario: Destinatario,
	itens: list[dict],
	totais: dict,
	transp: dict | None = None,
	pag: dict | None = None,
	infadic: dict | None = None,
	versao: str = "4.00",
) -> dict:
	"""Monta `infNFe` completo, com a chave derivada da identificação.

	A chave **não** é parâmetro: é calculada a partir do `ide` e do CNPJ do emitente. Duas
	fontes para o mesmo dado produziriam documento cuja chave não corresponde ao conteúdo,
	e o erro só apareceria na validação da SEFAZ.

	O atributo `Id` é a chave prefixada por "NFe", como o layout exige.
	"""
	if not itens:
		raise NFeInvalida("A NF-e precisa de ao menos um item", "itens")

	# transp e pag são obrigatórios no XSD (sem minOccurs="0") — mesmo quando não há
	# transporte real (modFrete="9") ou pagamento a destacar (tPag="90"), o grupo precisa
	# existir. Inventar um valor aqui seria decidir por conta própria dado de negócio que
	# não é nosso; falhar alto e pedir ao chamador é a alternativa correta.
	if not transp:
		raise NFeInvalida(
			"O grupo transp é obrigatório — use montar_transp('9', ...) quando não há "
			"transporte a relatar",
			"transp",
		)

	if not pag:
		raise NFeInvalida(
			"O grupo pag é obrigatório — use montar_pag([{'forma': '90', 'valor': None}]) "
			"quando não há pagamento a destacar",
			"pag",
		)

	identificacao.validar()

	chave = montar_chave(
		uf=identificacao.uf,
		ano_mes=identificacao.emissao.strftime("%y%m"),
		cnpj=emitente.cnpj,
		modelo=identificacao.modelo,
		serie=identificacao.serie,
		numero=identificacao.numero,
		tipo_emissao=identificacao.tipo_emissao,
		codigo_numerico=identificacao.codigo_numerico,
	)

	# Pós-condição: o dígito publicado no `ide` tem de ser o da chave montada.
	if chave[-1] != calcular_dv(chave[:-1]):
		raise NFeInvalida("Inconsistência interna: o dígito da chave não confere", "chave")

	detalhes = [
		{"@nItem": str(indice), **item} for indice, item in enumerate(itens, start=1)
	]

	corpo = {
		"@versao": versao,
		"@Id": f"NFe{chave}",
		"ide": montar_ide(identificacao, chave),
		"emit": montar_emit(emitente),
		"dest": montar_dest(destinatario),
		"det": detalhes,
		"total": dict(totais),
		# A ordem destas três linhas é a ordem do XSD (`xs:sequence`), não escolha
		# estética: `infNFe` é serializado depois, e trocar a ordem produziria XML válido
		# para outras ferramentas mas rejeitado pelo validador da SEFAZ.
		"transp": dict(transp),
		"pag": dict(pag),
	}

	if infadic:
		corpo["infAdic"] = dict(infadic)

	return {"infNFe": corpo}


def montar_nfe(infnfe: dict) -> dict:
	"""Envolve `infNFe` na raiz `NFe`, com o namespace do leiaute.

	É neste nível — não dentro de `infNFe` — que a assinatura entra como elemento
	**irmão**: a NF-e usa assinatura *enveloped* (o `Signature` fica dentro do
	elemento que contém o que foi assinado, mas fora do próprio conteúdo assinado).
	`assinar_nfe` é quem acrescenta esse irmão depois.
	"""
	return {"NFe": {"@xmlns": NAMESPACE_NFE, **infnfe}}


def assinar_nfe(nfe: dict, assinador: Assinador) -> dict:
	"""Assina o documento e devolve a árvore completa, com `Signature` anexado.

	A costura entre três módulos que, até aqui, não se conheciam: `serializacao.py`
	(dict → XML, para o assinador poder canonicalizar), `assinatura.py` (estrutura do
	envelope) e a porta `Assinador` (a criptografia em si, local ou remota). O documento
	final tem exatamente a forma que a SEFAZ espera: `NFe > (infNFe, Signature)`.

	Recebe `nfe`, não `infnfe`: o `Id` a assinar é o de `infNFe`, mas o que se
	serializa para calcular o digest é a árvore com o namespace já aplicado — assinar
	antes de aplicar o namespace produziria um digest que não bate com o XML final.
	"""
	id_elemento = nfe["NFe"]["infNFe"]["@Id"]
	xml = para_xml(nfe).encode("utf-8")

	material = assinador.assinar(xml, id_elemento)
	signature = montar_signature(id_elemento, material)

	return {"NFe": {**nfe["NFe"], **signature}}
