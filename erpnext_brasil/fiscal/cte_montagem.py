# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""CT-e: a árvore `CTe` completa a partir de dados já extraídos — sem `frappe`.

Por que existe
--------------
`integracao/cte_documento.py` lê o cadastro (`Sales Invoice`, `Customer`, `Company`) e **precisa**
importar `frappe`; por isso a suíte pura não o alcança. A regra de montagem — que grupo vem
depois de qual, o que o leiaute exige, como o ICMS é calculado, o que se recusa — não depende de
banco nenhum e mora aqui, onde `tests/test_cte_montagem.py` a trava. A camada Frappe vira só
tradução: cadastro → `DadosCte`. Mesmo precedente de `sortear_codigo_numerico` e das tabelas de
`setup/custom_fields.py`.

O que o leiaute exige (lido, não suposto)
-------------------------------------------
Estrutura conferida no `cteTiposBasico_v4.00.xsd` (`nfephp-org/sped-cte`, `PL_CTe_400`):

- `emit` leva `CRT` depois de `enderEmit` — a NF-e também, mas o primeiro esqueleto do CT-e o
  esqueceu;
- `vPrest` exige `vTPrest` **e** `vRec`; `Comp` é opcional e não é montado aqui;
- `rem` e `dest` são opcionais no XSD, mas o tomador `toma3` aponta para um deles — por isso a
  montagem exige os dois, em vez de emitir um `toma3` sem a parte a que se refere;
- `infCTeNorm` tem `infCarga` (`proPred` e ao menos um `infQ` são obrigatórios) e `infModal`
  (atributo `versaoModal` obrigatório); `infDoc` é opcional e fica de fora, como declarado em
  `design.md`;
- `imp/ICMS` é um `xs:choice` entre sete grupos. Estão montados `ICMS00`, `ICMS20`, `ICMS45`
  (CST 40/41/51), `ICMS90` e `ICMSSN`. `ICMS60` e `ICMSOutraUF` **são recusados** com mensagem
  que nomeia o CST, em vez de emitir um grupo que não se sabe preencher.

Escolhas que não vêm do XSD, e por isso ficam declaradas
------------------------------------------------------------
- `vRec` é igual a `vTPrest`: sem desconto nem componente deduzido, o valor a receber é o da
  prestação. Quando `Comp` existir, é aqui que isso muda.
- A **alíquota e a redução de base** do ICMS vêm do cadastro (`br_aliquota_icms_cte`,
  `br_reducao_base_icms_cte`), não de uma tabela por UF: a alíquota de uma prestação depende da
  rota e do tomador, e escolhê-la por conta própria seria inventar dado fiscal. O cálculo é só a
  aritmética do documento, com arredondamento de meio para cima em centavos.
- O código numérico (`cCT`) é sorteado por `sortear_codigo_numerico` (a regra da NF-e: não repete
  o número nem tem todos os dígitos iguais). A regra do CT-e **não foi conferida** contra o MOC;
  a da NF-e é pelo menos tão estrita, então o sorteio nunca produz o que a do CT-e recusaria.
- `ICMSUFFim` (partilha para consumidor final não contribuinte) não é montado: depende de
  alíquotas interna e interestadual que o cadastro não fornece.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from erpnext_brasil.fiscal.codigos.uf import UfDesconhecida, codigo_da_uf
from erpnext_brasil.fiscal.codigos_de_erro import (
	DOCUMENTO_CTE_DADO_INVALIDO,
	DOCUMENTO_CTE_DADO_OBRIGATORIO_AUSENTE,
)
from erpnext_brasil.fiscal.cte import (
	MODAL_RODOVIARIO,
	TOMADOR_DESTINATARIO,
	TOMADOR_OUTROS,
	TOMADOR_REMETENTE,
	CteInvalido,
	IdentificacaoCte,
	TomadorOutros,
	montar_cte,
	montar_ide,
	montar_toma3,
	montar_toma4,
)
from erpnext_brasil.fiscal.cte_rodoviario import RntrcInvalido, montar_rodo
from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.fiscal.documento.nfe import sortear_codigo_numerico
from erpnext_brasil.fiscal.documento.numeracao import NumeracaoInvalida, validar_numero
from erpnext_brasil.fiscal.natureza_operacao import NaturezaInvalida, validar_natureza
from erpnext_brasil.fiscal.validators import validar_cpf_cnpj

__all__ = [
	"CargaCte",
	"DadosCte",
	"EmitenteCte",
	"IcmsCte",
	"ParteCte",
	"QuantidadeCarga",
	"montar_cte_alocando_numero",
	"montar_cte_de_dados",
]

VERSAO_MODAL = "4.00"
"""`versaoModal` do `infModal` do CT-e 4.00."""

UNIDADES_DE_CARGA = {"00", "01", "02", "03", "04", "05"}
"""`cUnid`: 00-M3, 01-KG, 02-TON, 03-UNIDADE, 04-LITROS, 05-MMBTU (anotação do XSD)."""

CST_COM_IMPOSTO = {"00", "20", "90"}
CST_ISENCAO = {"40", "41", "51"}
CST_SIMPLES = "SN"

_CAMPOS_DO_ENDERECO = ("xLgr", "nro", "xBairro", "cMun", "xMun", "CEP", "UF")
_CENTAVOS = Decimal("0.01")
_QUATRO_CASAS = Decimal("0.0001")


@dataclass(frozen=True)
class EmitenteCte:
	"""A transportadora que emite o CT-e (a `Company`)."""

	cnpj: str
	nome: str
	inscricao_estadual: str
	regime_tributario: str
	"""`CRT`: 1 = Simples, 2 = Simples com excesso de sublimite, 3 = Regime Normal."""
	endereco: dict


@dataclass(frozen=True)
class ParteCte:
	"""Remetente ou destinatário da carga."""

	documento: str
	nome: str
	endereco: dict
	inscricao_estadual: str = ""


@dataclass(frozen=True)
class QuantidadeCarga:
	"""Uma linha de `infQ`: unidade, tipo de medida e quantidade."""

	unidade: str
	tipo_medida: str
	quantidade: Decimal


@dataclass(frozen=True)
class CargaCte:
	"""`infCarga`: o que está sendo transportado."""

	produto_predominante: str
	quantidades: tuple[QuantidadeCarga, ...]
	valor: Decimal | None = None


@dataclass(frozen=True)
class IcmsCte:
	"""A situação tributária do ICMS e o que a calcula. `cst="SN"` é o Simples Nacional."""

	cst: str
	aliquota: Decimal = Decimal(0)
	reducao_base: Decimal = Decimal(0)


@dataclass(frozen=True)
class DadosCte:
	"""Tudo o que a montagem precisa, já extraído do cadastro."""

	emitente: EmitenteCte
	remetente: ParteCte | None
	destinatario: ParteCte | None
	tomador_papel: str
	"""`0` remetente, `3` destinatário ou `4` outros (este exige `tomador_outros`)."""
	tomador_outros: TomadorOutros | None
	indicador_ie_tomador: str
	cfop: str
	natureza_operacao: str
	serie: str
	emissao: datetime
	ambiente: str
	"""`1` produção, `2` homologação — o código do leiaute, não o nome."""
	modal: str
	tipo_servico: str
	municipio_inicio: tuple[str, str, str]
	"""(código IBGE, nome, UF)."""
	municipio_fim: tuple[str, str, str]
	valor_prestacao: Decimal
	icms: IcmsCte
	carga: CargaCte
	rntrc: str


def _dinheiro(valor: Decimal) -> str:
	return str(valor.quantize(_CENTAVOS, rounding=ROUND_HALF_UP))


def _decimal(valor, campo: str) -> Decimal:
	try:
		numero = Decimal(str(valor))
	except (InvalidOperation, ValueError) as e:
		raise CteInvalido(f"valor numérico inválido em {campo}: {valor!r}", campo) from e

	if not numero.is_finite():
		raise CteInvalido(f"valor numérico inválido em {campo}: {valor!r}", campo)

	return numero


def _ausente_se_vazio(valor) -> int:
	"""`1206` quando o dado não foi informado, `1207` quando foi e o leiaute o recusa."""
	return DOCUMENTO_CTE_DADO_INVALIDO if str(valor or "").strip() else DOCUMENTO_CTE_DADO_OBRIGATORIO_AUSENTE


def _texto(valor, campo: str, rotulo: str, minimo: int = 1, maximo: int = 60) -> str:
	texto = str(valor or "").strip()

	if not minimo <= len(texto) <= maximo:
		raise CteInvalido(
			f"{rotulo} deve ter de {minimo} a {maximo} caracteres, recebido {texto!r}",
			campo,
			_ausente_se_vazio(texto),
		)

	return texto


def _endereco(endereco: dict, campo: str, rotulo: str) -> dict:
	faltando = [c for c in _CAMPOS_DO_ENDERECO if not str((endereco or {}).get(c) or "").strip()]

	if faltando:
		raise CteInvalido(
			f"endereço de {rotulo} sem {', '.join(faltando)}", campo, DOCUMENTO_CTE_DADO_OBRIGATORIO_AUSENTE
		)

	return {c: str(endereco[c]).strip() for c in _CAMPOS_DO_ENDERECO}


def _documento(valor: str, campo: str, rotulo: str) -> str:
	try:
		return validar_cpf_cnpj(valor)
	except ValueError as e:
		raise CteInvalido(f"CPF/CNPJ de {rotulo} inválido: {e}", campo, _ausente_se_vazio(valor)) from e


def _emit(emitente: EmitenteCte) -> dict:
	documento = _documento(emitente.cnpj, "emitente", "emitente")

	if len(documento) != 14:
		raise CteInvalido("o emitente do CT-e é a transportadora e precisa de CNPJ", "emitente")

	if not str(emitente.inscricao_estadual or "").strip():
		raise CteInvalido(
			"inscrição estadual do emitente é obrigatória no CT-e",
			"emitente",
			DOCUMENTO_CTE_DADO_OBRIGATORIO_AUSENTE,
		)

	if emitente.regime_tributario not in {"1", "2", "3"}:
		raise CteInvalido(
			f"regime tributário (CRT) do emitente deve ser 1, 2 ou 3, recebido {emitente.regime_tributario!r}",
			"emitente",
			_ausente_se_vazio(emitente.regime_tributario),
		)

	return {
		"CNPJ": documento,
		"IE": str(emitente.inscricao_estadual).strip(),
		"xNome": _texto(emitente.nome, "emitente", "razão social do emitente", 2),
		"enderEmit": _endereco(emitente.endereco, "emitente", "emitente"),
		"CRT": emitente.regime_tributario,
	}


def _parte(parte: ParteCte | None, campo: str, tag_endereco: str) -> dict:
	if parte is None:
		raise CteInvalido(
			f"o CT-e exige {campo} da carga e ele não foi informado",
			campo,
			DOCUMENTO_CTE_DADO_OBRIGATORIO_AUSENTE,
		)

	documento = _documento(parte.documento, campo, campo)
	grupo: dict = {"CNPJ" if len(documento) == 14 else "CPF": documento}

	if str(parte.inscricao_estadual or "").strip():
		grupo["IE"] = str(parte.inscricao_estadual).strip()

	grupo["xNome"] = _texto(parte.nome, campo, f"nome do {campo}", 2)
	grupo[tag_endereco] = _endereco(parte.endereco, campo, campo)

	return grupo


def _tomador(dados: DadosCte) -> dict:
	if dados.tomador_papel in (TOMADOR_REMETENTE, TOMADOR_DESTINATARIO):
		return montar_toma3(dados.tomador_papel)

	if dados.tomador_papel == TOMADOR_OUTROS:
		if dados.tomador_outros is None:
			raise CteInvalido(
				'tomador "Outros" exige o cadastro completo do tomador',
				"tomador",
				DOCUMENTO_CTE_DADO_OBRIGATORIO_AUSENTE,
			)

		try:
			return montar_toma4(dados.tomador_outros)
		except CteInvalido as e:
			raise CteInvalido(str(e), "tomador", e.codigo) from e

	raise CteInvalido(
		f"papel do tomador deve ser 0 (remetente), 3 (destinatário) ou 4 (outros), "
		f"recebido {dados.tomador_papel!r}",
		"tomador",
	)


def _vprest(valor: Decimal) -> dict:
	if valor <= 0:
		raise CteInvalido(f"valor da prestação deve ser maior que zero, recebido {valor}", "valor_prestacao")

	return {"vTPrest": _dinheiro(valor), "vRec": _dinheiro(valor)}


def _icms(icms: IcmsCte, valor_prestacao: Decimal) -> dict:
	cst = str(icms.cst or "").strip()

	if cst in CST_ISENCAO:
		return {"ICMS45": {"CST": cst}}

	if cst == CST_SIMPLES:
		return {"ICMSSN": {"CST": "90", "indSN": "1"}}

	if cst not in CST_COM_IMPOSTO:
		raise CteInvalido(
			f"CST {cst!r} do ICMS do CT-e não é suportado — montados: "
			f"{sorted(CST_COM_IMPOSTO | CST_ISENCAO)} e SN (Simples Nacional)",
			"icms",
			_ausente_se_vazio(cst),
		)

	aliquota = _decimal(icms.aliquota, "icms")
	reducao = _decimal(icms.reducao_base, "icms")

	if not Decimal(0) <= aliquota <= Decimal(100):
		raise CteInvalido(f"alíquota do ICMS deve estar entre 0 e 100, recebida {aliquota}", "icms")

	if not Decimal(0) <= reducao <= Decimal(100):
		raise CteInvalido(f"redução da base deve estar entre 0 e 100, recebida {reducao}", "icms")

	if cst == "20" and reducao == 0:
		raise CteInvalido(
			"CST 20 (base reduzida) exige a redução da base de cálculo",
			"icms",
			DOCUMENTO_CTE_DADO_OBRIGATORIO_AUSENTE,
		)

	base = (valor_prestacao * (Decimal(100) - reducao) / Decimal(100)).quantize(
		_CENTAVOS, rounding=ROUND_HALF_UP
	)
	imposto = (base * aliquota / Decimal(100)).quantize(_CENTAVOS, rounding=ROUND_HALF_UP)

	grupo: dict = {"CST": cst}

	if reducao > 0:
		grupo["pRedBC"] = _dinheiro(reducao)

	grupo.update({"vBC": _dinheiro(base), "pICMS": _dinheiro(aliquota), "vICMS": _dinheiro(imposto)})

	return {f"ICMS{cst}": grupo}


def _info_carga(carga: CargaCte) -> dict:
	grupo: dict = {}

	if carga.valor is not None:
		valor = _decimal(carga.valor, "carga")

		if valor < 0:
			raise CteInvalido(f"valor da carga não pode ser negativo, recebido {valor}", "carga")

		grupo["vCarga"] = _dinheiro(valor)

	grupo["proPred"] = _texto(carga.produto_predominante, "carga", "produto predominante")

	if not carga.quantidades:
		raise CteInvalido(
			"a carga precisa de ao menos uma quantidade (infQ)",
			"carga",
			DOCUMENTO_CTE_DADO_OBRIGATORIO_AUSENTE,
		)

	quantidades = []

	for item in carga.quantidades:
		if item.unidade not in UNIDADES_DE_CARGA:
			raise CteInvalido(
				f"unidade de carga deve ser uma de {sorted(UNIDADES_DE_CARGA)}, recebida {item.unidade!r}",
				"carga",
			)

		quantidade = _decimal(item.quantidade, "carga")

		if quantidade <= 0:
			raise CteInvalido(f"quantidade da carga deve ser maior que zero, recebida {quantidade}", "carga")

		quantidades.append(
			{
				"cUnid": item.unidade,
				"tpMed": _texto(item.tipo_medida, "carga", "tipo da medida", 1, 20),
				"qCarga": str(quantidade.quantize(_QUATRO_CASAS, rounding=ROUND_HALF_UP)),
			}
		)

	grupo["infQ"] = quantidades

	return grupo


def _identificacao(dados: DadosCte, numero: str, codigo_numerico: str) -> IdentificacaoCte:
	endereco = dados.emitente.endereco

	try:
		natureza = validar_natureza(dados.natureza_operacao)
		uf = codigo_da_uf(str(endereco.get("UF") or ""))
	except NaturezaInvalida as e:
		raise CteInvalido(str(e), "natureza_operacao") from e
	except UfDesconhecida as e:
		raise CteInvalido(f"UF do endereço do emitente desconhecida: {e}", "emitente") from e

	(cod_ini, nome_ini, uf_ini), (cod_fim, nome_fim, uf_fim) = dados.municipio_inicio, dados.municipio_fim

	return IdentificacaoCte(
		uf=uf,
		cfop=dados.cfop,
		natureza_operacao=natureza,
		serie=dados.serie,
		numero=numero,
		codigo_numerico=codigo_numerico,
		emissao=dados.emissao,
		modal=dados.modal,
		tipo_servico=dados.tipo_servico,
		municipio_inicio=cod_ini,
		municipio_inicio_nome=nome_ini,
		uf_inicio=uf_ini,
		municipio_fim=cod_fim,
		municipio_fim_nome=nome_fim,
		uf_fim=uf_fim,
		municipio_envio=str(endereco.get("cMun") or ""),
		municipio_envio_nome=str(endereco.get("xMun") or ""),
		uf_envio=str(endereco.get("UF") or ""),
		indicador_ie_tomador=dados.indicador_ie_tomador,
		ambiente=dados.ambiente,
	)


def montar_cte_de_dados(
	dados: DadosCte, numero: str, sortear: Callable[[str], str] = sortear_codigo_numerico
) -> tuple[dict, str]:
	"""A árvore `CTe` **não assinada** e a chave de acesso de 44 posições.

	O `numero` chega pronto — alocá-lo é da camada que conhece o banco, e esta função não consome
	nada: recusa antes de devolver qualquer árvore, então uma recusa nunca deixa um CT-e pela
	metade. Para alocar **depois** de validar, use `montar_cte_alocando_numero`. A chave é montada aqui, com o `cCT` sorteado, porque `ide/cDV` e o
	`Id` dependem dela e não podem ser informados em paralelo.
	"""
	try:
		numero = validar_numero(numero)
	except NumeracaoInvalida as e:
		raise CteInvalido(str(e), "numero") from e

	if dados.emissao.tzinfo is None:
		raise CteInvalido(
			"a data de emissão (dhEmi) precisa trazer o fuso horário — o XSD recusa a data sem deslocamento",
			"emissao",
		)

	if dados.modal != MODAL_RODOVIARIO:
		raise CteInvalido(
			f"só o modal rodoviário ({MODAL_RODOVIARIO}) está implementado, recebido {dados.modal!r}", "modal"
		)

	emit = _emit(dados.emitente)
	rem = _parte(dados.remetente, "remetente", "enderReme")
	dest = _parte(dados.destinatario, "destinatario", "enderDest")
	tomador = _tomador(dados)
	v_prest = _vprest(dados.valor_prestacao)
	imp = {"ICMS": _icms(dados.icms, dados.valor_prestacao)}
	info_carga = _info_carga(dados.carga)

	try:
		modal = montar_rodo(dados.rntrc)
	except RntrcInvalido as e:
		raise CteInvalido(str(e), "rntrc", _ausente_se_vazio(dados.rntrc)) from e

	codigo = sortear(numero)
	identificacao = _identificacao(dados, numero, codigo)

	chave = montar_chave(
		uf=identificacao.uf,
		ano_mes=dados.emissao.strftime("%y%m"),
		cnpj=emit["CNPJ"],
		modelo="57",
		serie=str(dados.serie),
		numero=numero,
		tipo_emissao=identificacao.tipo_emissao,
		codigo_numerico=codigo,
	)

	infcte = {
		"ide": montar_ide(identificacao, tomador, chave),
		"emit": emit,
		"rem": rem,
		"dest": dest,
		"vPrest": v_prest,
		"imp": imp,
		"infCTeNorm": {
			"infCarga": info_carga,
			"infModal": {"@versaoModal": VERSAO_MODAL, "rodo": modal},
		},
	}

	return montar_cte(infcte, chave), chave


NUMERO_DE_PROVA = "1"
"""Número descartável da montagem de prova — só prova que os dados valem, nunca vai a documento."""


def montar_cte_alocando_numero(
	dados: DadosCte, alocar: Callable[[], str], sortear: Callable[[str], str] = sortear_codigo_numerico
) -> tuple[dict, str]:
	"""Como `montar_cte_de_dados`, mas o número só é consumido **depois** de tudo validar.

	A numeração fiscal é sequencial, e lacuna só se justifica por inutilização de faixa. Um número
	gasto com um CT-e que nem chegou a ser montado é um número perdido — e quem aloca (`alocar`,
	do banco) trava a linha da série até o fim da transação. Por isso há duas montagens: a
	primeira, com `NUMERO_DE_PROVA`, existe só para recusar antes de tocar na série; a segunda usa
	o número de verdade. Se `alocar` falhar (sem série, sem número livre), a exceção sobe daqui e
	nenhuma árvore é devolvida — falha alto antes de qualquer transmissão.
	"""
	montar_cte_de_dados(dados, NUMERO_DE_PROVA, sortear)

	return montar_cte_de_dados(dados, alocar(), sortear)
