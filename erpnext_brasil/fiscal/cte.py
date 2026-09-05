# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""CT-e (Conhecimento de Transporte Eletrônico, modelo 57): montagem de grupos do XML.

Por que existe
--------------
Primeira peça de código do CT-e, depois do levantamento em `docs/cte-estado.md`. Escopo
deliberadamente estreito: só o grupo `ICMSUFFim` (partilha do ICMS entre UF de origem e UF de
término da prestação, para tomador consumidor final não contribuinte — Art. 155 §2º VII/VIII
CF, EC 87/2015), porque é o único ponto do levantamento já verificado byte a byte contra o XSD
oficial (`cte_v4.00.xsd`, `nfephp-org/sped-cte`, grupo `imp/ICMSUFFim`, linha 3960).

O que fica de fora, e por quê
------------------------------
A tabela de CFOP para prestação de serviço de transporte (grupo `5.35x`/`6.35x`/`6.36x` do
Convênio SINIEF 6/89) **não** está aqui: não foi verificada contra fonte primária nesta
investigação (o levantamento em `docs/cte-estado.md` confirmou que `ide.CFOP` usa o mesmo tipo
`TCfop` de 4 dígitos já implementado em `fiscal/cfop.py`, mas não os valores específicos de
transporte). Adicionar esses códigos de memória, sem checar a fonte, é exatamente o tipo de erro
silencioso que este projeto existe para evitar (ver `docs/cfop.md` sobre o bug de dígito faltante
pego pelo teste, e `docs/pcp-estado.md` sobre o campo quase reaproveitado errado) — fica para um
incremento futuro, com fonte citada.

Reuso deliberado
----------------
`montar_icms_uf_fim` não recalcula DIFAL — delega inteiramente a
`fiscal.impostos.icms.calcular_difal`, que já implementa a partilha de base dupla/única e o FCP.
A única coisa nova aqui é o **nome dos campos** no grupo `ICMSUFFim` do CT-e, que diverge do
`ICMSUFDest` da NF-e (`vBCUFFim` em vez de `vBCUFDest`, `pICMSUFFim` em vez de `pICMSUFDest`) —
confirmado por leitura direta do XSD, não suposto por analogia.

`montar_infnfe` monta o grupo `infDoc/infNFe` (a ponte com a NF-e transportada — o dado que o
MDF-e vai precisar referenciar depois, ver `docs/cte-estado.md`). Não reimplementa validação de
chave de acesso: reusa `fiscal.documento.chave_acesso.ler_chave`, a mesma função que a NF-e usa
— o layout de 44 posições e o dígito verificador são idênticos entre os documentos da família
(NF-e, CT-e, MDF-e), só o dígito de modelo muda. Confirmado por leitura do XSD (`infNFe.chave`,
tipo `TChDFe` — "T**Ch****D**ocumento **F**iscal **e**letrônico", o mesmo tipo genérico usado
para `chCTe` em outros grupos do próprio CT-e) que o campo é só a chave, sem repetir o valor da
nota (diferente de `infNF`, para NF modelo 01/04 em papel, que carrega o detalhamento fiscal
inteiro — esse grupo não foi implementado, é o caso legado, cada vez mais raro).

`assinar_cte` reusa `fiscal.documento.assinatura.py` inteiro, sem alteração — `referencia_do_id`,
`montar_signed_info` e `montar_signature` já eram genéricos (parametrizados por `id_elemento`,
nunca fixados em `"NFe"`), então não havia nada a mudar para o CT-e. A única coisa a verificar
era se o **perfil** de assinatura do CT-e é mesmo o mesmo da NF-e — não é suposição por analogia:

- O XSD confirma o formato do `Id`: `infCte/@Id`, padrão `CTe[0-9]{44}` (linha 4917 de
  `cteTiposBasico_v4.00.xsd`) — mesma convenção `<prefixo><chave>` da NF-e, só troca `NFe` por
  `CTe`.
- O algoritmo de assinatura foi corroborado por **código de produção**, não por manual: a classe
  `Signer` de `nfephp-org/sped-common` — usada por `sped-nfe`, `sped-cte`, `sped-mdfe` e outros
  pacotes da mesma família — tem `OPENSSL_ALGO_SHA1` como algoritmo padrão; `signCTe()` de
  `nfephp-org/sped-cte` chama esse `Signer::sign` sem sobrescrever o algoritmo. É uma
  corroboração mais forte que a maioria das fontes secundárias deste projeto (não é um blog
  resumindo a regra, é a implementação que assina CT-e de verdade em produção), mas ainda não é
  o texto do Ajuste SINIEF — declarado como tal, mesmo padrão de honestidade do módulo
  `cfop_transporte.py`. Sem essa corroboração, reusar `assinatura.py` seria supor que o CT-e
  segue a NF-e por "fazerem parte da mesma família" — o mesmo tipo de suposição que já se provou
  falsa uma vez neste projeto (eSocial usa SHA-256, não SHA-1, apesar de também ser um
  documento fiscal eletrônico brasileiro — ver `docs/rh-esocial-assinatura.md`).

`montar_toma3`/`montar_toma4` fecham o último ponto do levantamento de `docs/cte-estado.md` que
tinha estrutura mapeada mas nenhuma função de montagem: o `xs:choice` de `ide` que identifica o
tomador do serviço. `toma3` é deliberadamente trivial — o layout só pede um código (0-remetente/
1-expedidor/2-recebedor/3-destinatário), reaproveitando dados já informados noutro grupo do
mesmo documento; não há nada para validar além do próprio código. `toma4` ("Outros") é o caso
que precisa de dados completos, e reusa `validar_cpf_cnpj` — a mesma validação que `montar_dest`
já usa para NF-e — porque o XSD modela CNPJ/CPF como escolha exclusiva, igual ao destinatário.

`montar_ide`/`montar_cte` orquestram — o papel que `fiscal.documento.nfe.montar_ide`/
`montar_nfe` cumprem para a NF-e. Todos os 30 campos do `ide` foram lidos e ordenados por leitura
direta do XSD (`cteTiposBasico_v4.00.xsd`, linhas 2700–3145), não por analogia com a NF-e — o
`ide` do CT-e tem campos que a NF-e não tem (`modal`, `tpServ`, `cMunIni`/`cMunFim`, `retira`) e
não tem alguns que a NF-e tem (`cMunFG` vira `cMunEnv`, sem `idDest`/`tpNF`). `montar_ide` recebe
o grupo do tomador (`toma3`/`toma4`) já pronto de `montar_toma3`/`montar_toma4` — composição, não
acoplamento: `IdentificacaoCte` não sabe montar tomador, só onde ele entra na sequência.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from erpnext_brasil.fiscal.documento.assinatura import Assinador, montar_signature
from erpnext_brasil.fiscal.documento.chave_acesso import ChaveInvalida, ler_chave
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.impostos.icms import calcular_difal
from erpnext_brasil.fiscal.validators import limpar, validar_cpf_cnpj

__all__ = [
	"MODAL_AEREO",
	"MODAL_AQUAVIARIO",
	"MODAL_DUTOVIARIO",
	"MODAL_FERROVIARIO",
	"MODAL_MULTIMODAL",
	"MODAL_RODOVIARIO",
	"NAMESPACE_CTE",
	"RETIRA_NAO",
	"RETIRA_SIM",
	"TIPO_CTE_COMPLEMENTO",
	"TIPO_CTE_NORMAL",
	"TIPO_CTE_SUBSTITUICAO",
	"TIPO_SERVICO_NORMAL",
	"TIPO_SERVICO_REDESPACHO",
	"TIPO_SERVICO_REDESPACHO_INTERMEDIARIO",
	"TIPO_SERVICO_SUBCONTRATACAO",
	"TIPO_SERVICO_VINCULADO_MULTIMODAL",
	"TOMADOR_DESTINATARIO",
	"TOMADOR_EXPEDIDOR",
	"TOMADOR_OUTROS",
	"TOMADOR_RECEBEDOR",
	"TOMADOR_REMETENTE",
	"CteInvalido",
	"IdentificacaoCte",
	"TomadorOutros",
	"assinar_cte",
	"montar_cte",
	"montar_icms_uf_fim",
	"montar_ide",
	"montar_infnfe",
	"montar_toma3",
	"montar_toma4",
]

NAMESPACE_CTE = "http://www.portalfiscal.inf.br/cte"

# `modal` — confirmado em `ide/modal` (linha 2885).
MODAL_RODOVIARIO = "01"
MODAL_AEREO = "02"
MODAL_AQUAVIARIO = "03"
MODAL_FERROVIARIO = "04"
MODAL_DUTOVIARIO = "05"
MODAL_MULTIMODAL = "06"

# `tpServ` — confirmado em `ide/tpServ` (linha 2892).
TIPO_SERVICO_NORMAL = "0"
TIPO_SERVICO_SUBCONTRATACAO = "1"
TIPO_SERVICO_REDESPACHO = "2"
TIPO_SERVICO_REDESPACHO_INTERMEDIARIO = "3"
TIPO_SERVICO_VINCULADO_MULTIMODAL = "4"

# `tpCTe` — confirmado em `ide/tpCTe` (linha 2821). Não existe "2" nesta tabela — CT-e de
# Anulação de Valores é modelado de outro jeito, fora do escopo verificado aqui.
TIPO_CTE_NORMAL = "0"
TIPO_CTE_COMPLEMENTO = "1"
TIPO_CTE_SUBSTITUICAO = "3"

# `retira` — confirmado em `ide/retira` (linha 2961).
RETIRA_SIM = "0"
RETIRA_NAO = "1"

_MODAIS_VALIDOS = {
	MODAL_RODOVIARIO,
	MODAL_AEREO,
	MODAL_AQUAVIARIO,
	MODAL_FERROVIARIO,
	MODAL_DUTOVIARIO,
	MODAL_MULTIMODAL,
}
_TIPOS_SERVICO_VALIDOS = {
	TIPO_SERVICO_NORMAL,
	TIPO_SERVICO_SUBCONTRATACAO,
	TIPO_SERVICO_REDESPACHO,
	TIPO_SERVICO_REDESPACHO_INTERMEDIARIO,
	TIPO_SERVICO_VINCULADO_MULTIMODAL,
}
_TIPOS_CTE_VALIDOS = {TIPO_CTE_NORMAL, TIPO_CTE_COMPLEMENTO, TIPO_CTE_SUBSTITUICAO}
_RETIRA_VALIDOS = {RETIRA_SIM, RETIRA_NAO}
# `indIEToma` — confirmado em `ide/indIEToma` (linha 2985): 1-contribuinte, 2-isento, 9-não
# contribuinte. Mesma enumeração usada em `nfe.Destinatario.indicador_ie`.
_INDICADORES_IE_TOMADOR_VALIDOS = {"1", "2", "9"}

# `toma` dentro de `toma3` — o tomador é uma das partes já identificadas no CT-e.
TOMADOR_REMETENTE = "0"
TOMADOR_EXPEDIDOR = "1"
TOMADOR_RECEBEDOR = "2"
TOMADOR_DESTINATARIO = "3"
# `toma` dentro de `toma4` — sempre "4", mas nomeado para não espalhar o literal.
TOMADOR_OUTROS = "4"

_PAPEIS_TOMA3 = {TOMADOR_REMETENTE, TOMADOR_EXPEDIDOR, TOMADOR_RECEBEDOR, TOMADOR_DESTINATARIO}


class CteInvalido(ValueError):
	"""Dado que impediria a autorização do CT-e."""

	def __init__(self, mensagem: str, campo: str = ""):
		super().__init__(mensagem)
		self.campo = campo


def _natureza(valor) -> str:
	"""`natOp` do CT-e — mesmo limite da NF-e, **verificado**, não assumido por analogia.

	O `cteTiposBasico_v4.00.xsd` foi baixado e lido: as quatro ocorrências de `natOp` no
	schema (CT-e, CT-e OS, GTV-e e o grupo de substituição) declaram todas `minLength 1`
	e `maxLength 60`, iguais às do `leiauteNFe_v4.00.xsd`.

	A verificação não era dispensável: este projeto já foi mordido várias vezes por supor
	que documentos irmãos compartilham domínio (`procEmi` do CT-e × MDF-e, `IND_FRT` do
	C100 × D100, `IND_MOV` do E001 × H001). Coincidirem é conclusão, não ponto de partida.
	"""
	from erpnext_brasil.fiscal.natureza_operacao import NaturezaInvalida, validar_natureza

	try:
		return validar_natureza(str(valor or ""))
	except NaturezaInvalida as e:
		raise CteInvalido(str(e), "natureza_operacao") from e


@dataclass(frozen=True)
class IdentificacaoCte:
	"""Dados que identificam o documento — origem do grupo `ide`.

	Campos confirmados por leitura direta do XSD (`cteTiposBasico_v4.00.xsd`, linhas
	2700–3145), na ordem exata do `xs:sequence`. Alguns campos genéricos (`cUF`,
	`codigo_numerico`, `serie`, `numero`, `emissao`) espelham `fiscal.documento.nfe.
	Identificacao` de propósito — são o mesmo conceito com o mesmo nome no domínio, e o
	XSD confirma que carregam o mesmo formato; os campos específicos de transporte
	(`modal`, `tipo_servico`, município de início/fim) não têm equivalente na NF-e.
	"""

	uf: str
	"""`cUF` — código IBGE, não a sigla."""
	cfop: str
	natureza_operacao: str
	serie: str
	numero: str
	codigo_numerico: str
	emissao: datetime
	modal: str
	tipo_servico: str
	municipio_inicio: str
	"""`cMunIni` — código IBGE. `9999999` para operações com o exterior."""
	municipio_inicio_nome: str
	uf_inicio: str
	municipio_fim: str
	municipio_fim_nome: str
	uf_fim: str
	municipio_envio: str
	"""`cMunEnv` — município do emitente, não da prestação."""
	municipio_envio_nome: str
	uf_envio: str
	indicador_ie_tomador: str
	"""`indIEToma` — 1 = contribuinte ICMS, 2 = isento de inscrição, 9 = não contribuinte.
	Aplica-se ao tomador indicado em `toma3`/`toma4`, por isso não tem valor-padrão: quem
	monta `ide` precisa saber o papel do tomador antes de montar este campo."""
	retira: str = RETIRA_NAO
	detalhes_retira: str = ""
	tipo_cte: str = TIPO_CTE_NORMAL
	processo_emissao: str = "0"
	versao_processo: str = "1.0.0"
	tipo_impressao: str = "1"
	tipo_emissao: str = "1"
	ambiente: str = "2"
	"""1 = produção, 2 = homologação — mesmo padrão-seguro de `nfe.Identificacao`."""
	globalizado: bool = False

	def validar(self) -> None:
		if self.modal not in _MODAIS_VALIDOS:
			raise CteInvalido(
				f"modal deve ser um de {sorted(_MODAIS_VALIDOS)}, recebido {self.modal!r}", "modal"
			)

		if self.tipo_servico not in _TIPOS_SERVICO_VALIDOS:
			raise CteInvalido(
				f"tipo_servico deve ser um de {sorted(_TIPOS_SERVICO_VALIDOS)}, "
				f"recebido {self.tipo_servico!r}",
				"tipo_servico",
			)

		if self.tipo_cte not in _TIPOS_CTE_VALIDOS:
			raise CteInvalido(
				f"tipo_cte deve ser um de {sorted(_TIPOS_CTE_VALIDOS)}, recebido {self.tipo_cte!r}",
				"tipo_cte",
			)

		if self.retira not in _RETIRA_VALIDOS:
			raise CteInvalido(
				f"retira deve ser um de {sorted(_RETIRA_VALIDOS)}, recebido {self.retira!r}", "retira"
			)

		if self.indicador_ie_tomador not in _INDICADORES_IE_TOMADOR_VALIDOS:
			raise CteInvalido(
				f"indicador_ie_tomador deve ser um de {sorted(_INDICADORES_IE_TOMADOR_VALIDOS)}, "
				f"recebido {self.indicador_ie_tomador!r}",
				"indicador_ie_tomador",
			)


def montar_ide(identificacao: IdentificacaoCte, tomador: dict, chave: str) -> dict:
	"""Monta o grupo `ide`, na ordem exata do XSD.

	Recebe `tomador` já pronto de `montar_toma3`/`montar_toma4` — este módulo só sabe
	onde ele entra na sequência (depois de `indIEToma`, antes de `dhCont`/`xJust`), não
	como montá-lo.

	Recebe também `chave` — não para repeti-la, só para extrair `cDV` (dígito
	verificador), campo obrigatório do `ide` (confirmado no XSD, `ide/cDV`, sem
	`minOccurs="0"` — corrigido aqui depois de um primeiro incremento tê-lo esquecido).
	Mesma disciplina de `fiscal.documento.nfe.montar_ide`: o `cDV` publicado no `ide` é
	sempre o da chave que acompanha o documento, nunca informado em paralelo — não há
	como divergirem. `montar_cte` recebe a mesma `chave` para montar o `Id`.

	Pré-condição (Design by Contract), não só formato: `chave` é decomposta com
	`ler_chave` — que já valida layout e dígito verificador — e o `modelo` decomposto
	precisa ser `"57"`. Sem essa checagem, uma chave de NF-e ou de MDF-e passada por
	engano aqui produziria um `ide` de CT-e com `cDV` tecnicamente correto mas de outro
	documento — um erro silencioso que só apareceria na rejeição da SEFAZ. É a mesma
	categoria de defesa em profundidade já aplicada em `montar_infnfe` (recusa de chave
	de modelo errado).
	"""
	identificacao.validar()

	chave_decomposta = ler_chave(chave)

	if chave_decomposta.modelo != "57":
		raise CteInvalido(
			f"ide/cDV precisa de uma chave de CT-e (modelo 57), recebida chave de modelo "
			f"{chave_decomposta.modelo} ({chave_decomposta.documento})",
			"chave",
		)

	grupo = {
		"cUF": identificacao.uf,
		"cCT": str(identificacao.codigo_numerico).rjust(8, "0"),
		"CFOP": identificacao.cfop,
		"natOp": identificacao.natureza_operacao,
		"mod": "57",
		"serie": str(identificacao.serie).lstrip("0") or "0",
		"nCT": str(identificacao.numero).lstrip("0") or "0",
		"dhEmi": identificacao.emissao.isoformat(),
		"tpImp": identificacao.tipo_impressao,
		"tpEmis": identificacao.tipo_emissao,
		"cDV": chave_decomposta.dv,
		"tpAmb": identificacao.ambiente,
		"tpCTe": identificacao.tipo_cte,
		"procEmi": identificacao.processo_emissao,
		"verProc": identificacao.versao_processo,
	}

	if identificacao.globalizado:
		grupo["indGlobalizado"] = "1"

	grupo.update(
		{
			"cMunEnv": identificacao.municipio_envio,
			"xMunEnv": identificacao.municipio_envio_nome,
			"UFEnv": identificacao.uf_envio,
			"modal": identificacao.modal,
			"tpServ": identificacao.tipo_servico,
			"cMunIni": identificacao.municipio_inicio,
			"xMunIni": identificacao.municipio_inicio_nome,
			"UFIni": identificacao.uf_inicio,
			"cMunFim": identificacao.municipio_fim,
			"xMunFim": identificacao.municipio_fim_nome,
			"UFFim": identificacao.uf_fim,
			"retira": identificacao.retira,
		}
	)

	if identificacao.detalhes_retira.strip():
		grupo["xDetRetira"] = identificacao.detalhes_retira.strip()

	grupo["indIEToma"] = identificacao.indicador_ie_tomador
	grupo.update(tomador)

	return grupo


def montar_cte(infcte: dict, chave: str) -> dict:
	"""Envolve `infCte` na raiz `CTe`, com o namespace do leiaute e o `Id` derivado.

	Mesma disciplina de `fiscal.documento.nfe.montar_nfe`: o `Id` é `"CTe" + chave`,
	nunca informado em paralelo — não há como divergir do que a chave realmente é.
	"""
	return {
		"CTe": {
			"@xmlns": NAMESPACE_CTE,
			"infCte": {**infcte, "@Id": f"CTe{chave}"},
		}
	}


def montar_icms_uf_fim(
	valor_prestacao: Decimal,
	aliquota_interestadual: Decimal,
	aliquota_interna_destino: Decimal,
	aliquota_fcp: Decimal = Decimal(0),
	base_dupla: bool = True,
) -> dict:
	"""Monta o grupo `ICMSUFFim` (`imp/ICMSUFFim` do XSD do CT-e).

	Só se aplica a prestações interestaduais de transporte para consumidor final não
	contribuinte do ICMS — mesma condição de aplicabilidade do `ICMSUFDest` na NF-e.
	Devolve os nomes de campo exatos do XSD (`vBCUFFim`, `pFCPUFFim`, `pICMSUFFim`,
	`pICMSInter`, `vFCPUFFim`, `vICMSUFFim`, `vICMSUFIni` — este último é o ICMS que fica
	com a UF de início da prestação, equivalente ao `icms_origem` do cálculo).
	"""
	resultado = calcular_difal(
		valor_operacao=valor_prestacao,
		aliquota_interestadual=aliquota_interestadual,
		aliquota_interna_destino=aliquota_interna_destino,
		base_dupla=base_dupla,
		aliquota_fcp=aliquota_fcp,
	)

	grupo = {
		"vBCUFFim": str(resultado["base_destino"]),
		"pFCPUFFim": str(aliquota_fcp),
		"pICMSUFFim": str(aliquota_interna_destino),
		"pICMSInter": str(aliquota_interestadual),
		"vFCPUFFim": str(resultado["fcp"]),
		"vICMSUFFim": str(resultado["difal"]),
		"vICMSUFIni": str(resultado["icms_origem"]),
	}

	return grupo


def montar_infnfe(chaves_nfe: list[str]) -> list[dict]:
	"""Monta a lista de referências `infDoc/infNFe` — uma por NF-e transportada.

	Cada item vira `{"chave": <44 dígitos>}` — o XSD não carrega mais nada obrigatório
	além da chave (ver docstring do módulo). Valida cada chave com a mesma rotina da
	NF-e (`ler_chave`) e recusa uma chave que não seja de NF-e — evitaria colar por
	engano a chave de outro CT-e ou de um MDF-e no lugar errado, erro que só apareceria
	na rejeição da SEFAZ sem essa checagem local.
	"""
	grupo = []

	for chave in chaves_nfe:
		decomposta = ler_chave(chave)

		if decomposta.modelo != "55":
			raise ChaveInvalida(
				f"infDoc/infNFe só aceita chave de NF-e (modelo 55), "
				f"recebida chave de modelo {decomposta.modelo} ({decomposta.documento})",
				chave,
			)

		grupo.append({"chave": decomposta.valor})

	return grupo


@dataclass(frozen=True)
class TomadorOutros:
	"""Dados do tomador para `toma4` — o layout exige cadastro completo, não um código."""

	nome: str
	cnpj_cpf: str
	inscricao_estadual: str = ""
	nome_fantasia: str = ""
	fone: str = ""
	endereco: dict = field(default_factory=dict)
	email: str = ""


def montar_toma3(papel: str) -> dict:
	"""Monta `toma3` — o tomador é uma das partes já identificadas no CT-e.

	`papel` é um dos `TOMADOR_REMETENTE`/`TOMADOR_EXPEDIDOR`/`TOMADOR_RECEBEDOR`/
	`TOMADOR_DESTINATARIO`. Não há mais nada a montar: o XSD reusa os dados do grupo
	correspondente (`rem`/`exped`/`receb`/`dest`), evitando duplicar cadastro.
	"""
	if papel not in _PAPEIS_TOMA3:
		raise CteInvalido(
			f"papel de toma3 deve ser um de {sorted(_PAPEIS_TOMA3)}, recebido {papel!r}", "papel"
		)

	return {"toma3": {"toma": papel}}


def montar_toma4(tomador: TomadorOutros) -> dict:
	"""Monta `toma4` — tomador "Outros", com dados cadastrais completos.

	CNPJ e CPF são escolha exclusiva no XSD, igual ao destinatário da NF-e — reusa
	`validar_cpf_cnpj`, a mesma validação de `fiscal.documento.nfe.montar_dest`.
	"""
	if not limpar(tomador.nome):
		raise CteInvalido("Tomador (toma4) precisa de nome", "nome")

	try:
		documento = validar_cpf_cnpj(tomador.cnpj_cpf)
	except ValueError as e:
		raise CteInvalido(f"CPF/CNPJ do tomador inválido: {e}", "cnpj_cpf") from e

	# Ordem do XSD: toma, CNPJ|CPF, IE, xNome, xFant, fone, enderToma, email — não é livre,
	# é `xs:sequence` (ver `docs/cte-toma.md`).
	grupo: dict = {"toma": TOMADOR_OUTROS}
	grupo["CNPJ" if len(documento) == 14 else "CPF"] = documento

	if tomador.inscricao_estadual.strip():
		grupo["IE"] = tomador.inscricao_estadual.strip()

	grupo["xNome"] = tomador.nome.strip()

	if tomador.nome_fantasia.strip():
		grupo["xFant"] = tomador.nome_fantasia.strip()

	if tomador.fone.strip():
		grupo["fone"] = tomador.fone.strip()

	if not tomador.endereco:
		raise CteInvalido("Tomador (toma4) precisa de endereço (enderToma é obrigatório no XSD)", "endereco")

	grupo["enderToma"] = dict(tomador.endereco)

	if tomador.email.strip():
		grupo["email"] = tomador.email.strip()

	return {"toma4": grupo}


def assinar_cte(cte: dict, assinador: Assinador) -> dict:
	"""Assina o documento e devolve a árvore completa, com `Signature` anexado.

	Mesma costura de `fiscal.documento.nfe.assinar_nfe`: serializa a árvore (com o `Id`
	já aplicado em `infCte`), assina, e monta o envelope `Signature` como irmão de
	`infCte` dentro de `CTe`. Recebe `cte` — não `infcte` — pelo mesmo motivo da NF-e: o
	`Id` a assinar é o de `infCte`, mas o digest tem que ser calculado sobre a árvore com
	o namespace já aplicado.
	"""
	id_elemento = cte["CTe"]["infCte"]["@Id"]
	xml = para_xml(cte).encode("utf-8")

	material = assinador.assinar(xml, id_elemento)
	signature = montar_signature(id_elemento, material)

	return {"CTe": {**cte["CTe"], **signature}}
