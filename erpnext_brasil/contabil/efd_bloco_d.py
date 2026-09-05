# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Bloco D do EFD-ICMS/IPI — documentos fiscais de serviço de transporte.

`D001` (abertura), `D100` (o documento — CT-e, CT-e OS, BP-e e os modelos em papel),
`D190` (registro analítico) e `D990` (encerramento). É o par do Bloco C para o lado do
transporte, e o consumidor natural do CT-e que este projeto já emite.

Achado 1: `IND_FRT` do `D100` **não é** o `IND_FRT` do `C100`
--------------------------------------------------------------------
Mesmo nome de campo, mesma posição (17), mesmo arquivo — **domínios diferentes**:

| Código | `C100` (desde 01/01/2018) | `D100` (desde 01/07/2012, nunca atualizado) |
|---|---|---|
| `0` | Frete por conta do Remetente (CIF) | Por conta do emitente |
| `1` | Frete por conta do Destinatário (FOB) | Por conta do destinatário/remetente |
| `2` | Frete por conta de Terceiros | Por conta de terceiros |
| `3` | Transporte Próprio por conta do Remetente | — |
| `4` | Transporte Próprio por conta do Destinatário | — |
| `9` | Sem Ocorrência de Transporte | Sem cobrança de frete |

O `C100` ganhou os códigos `3` e `4` na revisão de 2018; o `D100` **ficou parado na
tabela de 2012** e continua com "Valores válidos: [0, 1, 2, 9]" na versão 3.2.1 do guia.

A consequência é concreta: reaproveitar `efd_bloco_c.IND_FRT_VALIDOS` aqui aceitaria um
`3` ou `4` que o PVA recusa. Por isso este módulo declara `IND_FRT_VALIDOS_D100` próprio
em vez de importar o do vizinho — a duplicação é o ponto, não um descuido.

Achado 2: o `D190` tem 9 campos, o `C190` tem 12
-------------------------------------------------------
O analítico do transporte **não tem** `VL_BC_ICMS_ST`, `VL_ICMS_ST` nem `VL_IPI`: serviço
de transporte não sofre substituição tributária nesses campos nem IPI. Copiar a estrutura
do `C190` produziria três campos a mais e um arquivo malformado.

Além disso, o `CST_ICMS` do `D190` tem o **primeiro caractere sempre `0`** — o guia diz
isso duas vezes. É a origem da mercadoria, que não existe para um serviço. No `C190` o
primeiro dígito varia de `0` a `8`.

Achado 3: o CFOP tem de concordar com o sentido da operação
-------------------------------------------------------------------
Regra cruzada entre `D100` e `D190`: se `IND_OPER` é `0` (aquisição), o CFOP começa com
`1`, `2` ou `3`; se é `1` (prestação), começa com `5`, `6` ou `7`. É a diferença entre
entrada e saída, e errá-la inverte o sentido da prestação inteira sem que nada no formato
denuncie.

Tensão de fonte registrada: `VL_BC_ICMS` do `D190` contra o do `D100`
-----------------------------------------------------------------------------
Para o `C190`, o guia manda conferir a **soma**: "a soma dos valores do campo VL_BC_ICMS
dos registros analíticos (C190) deve ser igual ao valor informado neste campo".

Para o `D190`, a redação muda: "o valor informado deve ser **igual ao valor** do campo
VL_BC_ICMS do registro D100, **pai** deste registro D190" — no singular, por registro.
Mas a ocorrência declarada do `D190` é `1:N`. Lida ao pé da letra, com dois analíticos a
regra exigiria que **cada um** valesse o total do documento, o que é aritmeticamente
impossível de satisfazer junto.

Este módulo confere a **soma**, que é a leitura consistente e coincide com a literal no
caso de um único `D190` — que é o caso do CT-e comum. A divergência fica declarada em vez
de resolvida em silêncio.

As demais regras do guia checadas aqui
----------------------------------------------
- **`IND_EMIT = 1` (terceiros) força `IND_OPER = 0`** (entrada). Emissão de terceiro só
  pode ser aquisição — quem presta o serviço emite o próprio documento.
- **`SER` com três posições para CT-e e CT-e OS** (modelos 57 e 67); "se não existir
  série, informar `000`". Deixar vazio não é o mesmo que `000`.
- **`CHV_CTE` obrigatória** para os modelos eletrônicos (57, 63, 67), validada de verdade
  (44 posições e dígito verificador) reaproveitando `fiscal.documento.chave_acesso` — a
  mesma validação da família NF-e/CT-e/MDF-e, não uma segunda implementação.
- **BP-e (modelo 63) não informa `COD_PART`, `SUB` nem `IND_FRT`** (Exceção 6) e **não é
  escriturado nas entradas**.
- **Modelos em papel (07, 09, 10, 11, 26, 27) só até 31/12/2018.** O guia exige `DT_DOC`
  anterior a 01/01/2019 para eles — são leiautes encerrados, e um documento desses com
  data recente é erro de digitação, não caso raro.
- **`VL_RED_BC` só com CST terminado em 20 ou 70** (redução de base de cálculo).

Fora de escopo, declarado
--------------------------------
- **`D101`** (EC 87/15, operação interestadual a consumidor final não contribuinte),
  **`D110`-`D180`** (complementos por modal: rodoviário, aquaviário, aéreo, multimodal),
  **`D195`/`D197`** (observações e ajustes) e todo o **`D300`-`D420`** (bilhetes de
  passagem, ECF, resumo de movimento diário) e **`D500`+** (comunicação e
  telecomunicação). Cada um pede seu próprio incremento verificado.
- Para **CT-e e CT-e OS de emissão própria**, que é o caso deste projeto, a Exceção 4 do
  guia diz que "devem ser apresentados **somente os registros D100 e D190**" — mais
  `D195`/`D197` se houver. O recorte deste módulo é, portanto, o arquivo completo para o
  caso mais comum, não um começo arbitrário.

Fonte: Guia Prático EFD-ICMS/IPI versão 3.2.1 (28/10/2025), páginas 170-186 e 221,
baixado de `sped.rfb.gov.br` e lido localmente.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido

__all__ = [
	"CFOP_INICIAIS_POR_OPERACAO",
	"IND_FRT_VALIDOS_D100",
	"MODELOS_ELETRONICOS_D100",
	"MODELOS_ENCERRADOS_EM_2018",
	"MODELOS_VALIDOS_D100",
	"AnaliticoTransporte",
	"DocumentoTransporte",
	"montar_bloco_d",
	"montar_d001",
	"montar_d100",
	"montar_d190",
	"montar_d990",
]

ZERO = Decimal("0.00")

OPERACAO_AQUISICAO = "0"
OPERACAO_PRESTACAO = "1"

EMISSAO_PROPRIA = "0"
EMISSAO_DE_TERCEIROS = "1"

MODELO_CTE = "57"
MODELO_BPE = "63"
MODELO_CTE_OS = "67"

MODELOS_VALIDOS_D100 = frozenset(
	{"07", "08", "8B", "09", "10", "11", "26", "27", MODELO_CTE, MODELO_BPE, MODELO_CTE_OS}
)

MODELOS_ELETRONICOS_D100 = frozenset({MODELO_CTE, MODELO_BPE, MODELO_CTE_OS})
"""Exigem `CHV_CTE`."""

MODELOS_COM_SERIE_DE_TRES_POSICOES = frozenset({MODELO_CTE, MODELO_CTE_OS})

MODELOS_ENCERRADOS_EM_2018 = frozenset({"07", "09", "10", "11", "26", "27"})
"""Modelos em papel: `DT_DOC` tem de ser anterior a 01/01/2019."""

PRIMEIRO_DIA_SEM_MODELO_EM_PAPEL = date(2019, 1, 1)

SITUACAO_NUMERACAO_INUTILIZADA = "05"

SITUACOES_VALIDAS_D100 = frozenset({"00", "01", "02", "03", "04", "05", "06", "07", "08"})

IND_FRT_VALIDOS_D100 = frozenset({"0", "1", "2", "9"})
"""Tabela de 01/07/2012, **sem** os códigos 3 e 4 que o `C100` ganhou em 2018.

Declarado aqui em vez de importado de `efd_bloco_c` de propósito — ver achado 1 na
docstring do módulo.
"""

CFOP_INICIAIS_POR_OPERACAO = {
	OPERACAO_AQUISICAO: frozenset({"1", "2", "3"}),
	OPERACAO_PRESTACAO: frozenset({"5", "6", "7"}),
}

CST_COM_REDUCAO_DE_BASE = frozenset({"20", "70"})

_PROIBIDOS_NO_BPE = ("codigo_participante", "subserie", "indicador_frete")


@dataclass(frozen=True)
class DocumentoTransporte:
	"""Os dados do registro `D100` — 25 campos.

	`indicador_frete` é `""` por padrão, e não `"9"`: "sem cobrança de frete" é uma
	afirmação sobre a operação, e afirmá-la por omissão de quem chama seria inventar
	informação fiscal.
	"""

	operacao: str
	emissao: str
	codigo_modelo: str
	codigo_situacao: str
	numero: str
	data_emissao: date
	valor_documento: Decimal
	valor_servico: Decimal
	serie: str = ""
	subserie: str = ""
	codigo_participante: str = ""
	chave_acesso: str = ""
	data_aquisicao_prestacao: date | None = None
	tipo_cte: str = ""
	chave_documento_substituido: str = ""
	valor_desconto: Decimal = ZERO
	indicador_frete: str = ""
	valor_bc_icms: Decimal = ZERO
	valor_icms: Decimal = ZERO
	valor_nao_tributado: Decimal = ZERO
	codigo_informacao_complementar: str = ""
	codigo_conta: str = ""
	codigo_municipio_origem: str = ""
	codigo_municipio_destino: str = ""

	def __post_init__(self) -> None:
		if self.operacao not in (OPERACAO_AQUISICAO, OPERACAO_PRESTACAO):
			raise EfdInvalido(f"IND_OPER deve ser '0' ou '1', recebido {self.operacao!r}")

		if self.emissao not in (EMISSAO_PROPRIA, EMISSAO_DE_TERCEIROS):
			raise EfdInvalido(f"IND_EMIT deve ser '0' ou '1', recebido {self.emissao!r}")

		if self.emissao == EMISSAO_DE_TERCEIROS and self.operacao != OPERACAO_AQUISICAO:
			raise EfdInvalido(
				"documento de emissão de terceiros só pode ser aquisição (IND_OPER '0'): "
				"quem presta o serviço emite o próprio documento"
			)

		if self.codigo_modelo not in MODELOS_VALIDOS_D100:
			raise EfdInvalido(
				f"COD_MOD deve ser um de {sorted(MODELOS_VALIDOS_D100)}, recebido {self.codigo_modelo!r}"
			)

		if self.codigo_situacao not in SITUACOES_VALIDAS_D100:
			raise EfdInvalido(
				f"COD_SIT deve ser um de {sorted(SITUACOES_VALIDAS_D100)}, recebido {self.codigo_situacao!r}"
			)

		if not self.numero or not self.numero.isdigit() or int(self.numero) <= 0:
			raise EfdInvalido(f"NUM_DOC deve ser um número maior que zero, recebido {self.numero!r}")

		if not isinstance(self.data_emissao, date):
			raise EfdInvalido(f"DT_DOC deve ser date, recebido {type(self.data_emissao).__name__}")

		if self.indicador_frete and self.indicador_frete not in IND_FRT_VALIDOS_D100:
			raise EfdInvalido(
				f"IND_FRT do D100 deve ser um de {sorted(IND_FRT_VALIDOS_D100)} (tabela de "
				f"01/07/2012 — o D100 não tem os códigos '3' e '4' do C100), recebido "
				f"{self.indicador_frete!r}"
			)

		self._validar_modelo_em_papel()
		self._validar_serie()
		self._validar_chave()
		self._validar_bpe()

	def _validar_modelo_em_papel(self) -> None:
		"""Modelos 07, 09, 10, 11, 26 e 27 foram encerrados: `DT_DOC` < 01/01/2019."""
		if self.codigo_modelo not in MODELOS_ENCERRADOS_EM_2018:
			return

		if self.data_emissao >= PRIMEIRO_DIA_SEM_MODELO_EM_PAPEL:
			raise EfdInvalido(
				f"o modelo {self.codigo_modelo!r} exige DT_DOC anterior a "
				f"{PRIMEIRO_DIA_SEM_MODELO_EM_PAPEL}, recebido {self.data_emissao} — "
				"é leiaute encerrado, e data recente aqui é erro de digitação"
			)

	def _validar_serie(self) -> None:
		"""CT-e e CT-e OS exigem série de três posições; sem série, `000` — não vazio."""
		if self.codigo_modelo not in MODELOS_COM_SERIE_DE_TRES_POSICOES:
			return

		if len(self.serie) != 3 or not self.serie.isdigit():
			raise EfdInvalido(
				f"SER do modelo {self.codigo_modelo!r} tem três posições numéricas; se não "
				f"existir série, informar '000' — recebido {self.serie!r}"
			)

	def _validar_chave(self) -> None:
		eletronico = self.codigo_modelo in MODELOS_ELETRONICOS_D100
		inutilizada = self.codigo_situacao == SITUACAO_NUMERACAO_INUTILIZADA

		if eletronico and not inutilizada and not self.chave_acesso:
			raise EfdInvalido(
				f"CHV_CTE é obrigatória para o modelo {self.codigo_modelo} desde abril/2012, "
				f"exceto com COD_SIT {SITUACAO_NUMERACAO_INUTILIZADA!r} (numeração inutilizada)"
			)

		from erpnext_brasil.fiscal.documento.chave_acesso import ChaveInvalida, validar_chave

		for nome, valor in (
			("CHV_CTE", self.chave_acesso),
			("CHV_CTE_REF", self.chave_documento_substituido),
		):
			if not valor:
				continue

			try:
				validar_chave(valor)
			except ChaveInvalida as e:
				raise EfdInvalido(f"{nome} inválida: {e}") from e

	def _validar_bpe(self) -> None:
		"""Exceção 6: o BP-e não informa `COD_PART`, `SUB` nem `IND_FRT`, e não entra nas
		entradas."""
		if self.codigo_modelo != MODELO_BPE:
			return

		informados = [nome for nome in _PROIBIDOS_NO_BPE if getattr(self, nome)]

		if informados:
			raise EfdInvalido(f"BP-e (modelo 63) não informa {informados} (Exceção 6 do Guia Prático)")

		if self.operacao == OPERACAO_AQUISICAO:
			raise EfdInvalido("BP-e (modelo 63) não deve ser escriturado nas entradas")


@dataclass(frozen=True)
class AnaliticoTransporte:
	"""Os dados do registro `D190` — 9 campos, três a menos que o `C190`.

	Não há `VL_BC_ICMS_ST`, `VL_ICMS_ST` nem `VL_IPI`: serviço de transporte não os tem.
	"""

	cst_icms: str
	cfop: str
	valor_operacao: Decimal
	valor_bc_icms: Decimal = ZERO
	valor_icms: Decimal = ZERO
	valor_reducao_bc: Decimal = ZERO
	aliquota_icms: Decimal | None = None
	codigo_observacao: str = ""

	def __post_init__(self) -> None:
		if len(self.cst_icms) != 3 or not self.cst_icms.isdigit():
			raise EfdInvalido(f"CST_ICMS deve ter 3 dígitos, recebido {self.cst_icms!r}")

		if self.cst_icms[0] != "0":
			raise EfdInvalido(
				f"o primeiro caractere do CST_ICMS do D190 é sempre '0' (não há origem de "
				f"mercadoria em serviço de transporte), recebido {self.cst_icms!r}"
			)

		if len(self.cfop) != 4 or not self.cfop.isdigit():
			raise EfdInvalido(f"CFOP deve ter 4 dígitos, recebido {self.cfop!r}")

		if self.cfop.endswith(("00", "50")):
			raise EfdInvalido(
				f"o CFOP {self.cfop!r} é título de agrupamento, não código de prestação — "
				"códigos terminados em 00 ou 50 não podem ser usados"
			)

		if self.valor_reducao_bc != ZERO and self.cst_icms[1:] not in CST_COM_REDUCAO_DE_BASE:
			raise EfdInvalido(
				f"VL_RED_BC só pode ser preenchido com CST terminado em "
				f"{sorted(CST_COM_REDUCAO_DE_BASE)}, recebido {self.cst_icms!r}"
			)


def montar_d001(tem_dados: bool) -> dict:
	"""Abertura do Bloco D. `IND_MOV` aceita `[0,1]` — pode ser vazio, ao contrário do
	`E001` (ver `efd_icms_ipi.montar_e001`)."""
	return {"REG": "D001", "IND_MOV": "0" if tem_dados else "1"}


def montar_d100(documento: DocumentoTransporte) -> dict:
	"""Campos do registro `D100`, na ordem oficial — 25 campos."""
	return {
		"REG": "D100",
		"IND_OPER": documento.operacao,
		"IND_EMIT": documento.emissao,
		"COD_PART": documento.codigo_participante,
		"COD_MOD": documento.codigo_modelo,
		"COD_SIT": documento.codigo_situacao,
		"SER": documento.serie,
		"SUB": documento.subserie,
		"NUM_DOC": documento.numero,
		"CHV_CTE": documento.chave_acesso,
		"DT_DOC": documento.data_emissao,
		"DT_A_P": documento.data_aquisicao_prestacao,
		"TP_CT-e": documento.tipo_cte,
		"CHV_CTE_REF": documento.chave_documento_substituido,
		"VL_DOC": documento.valor_documento,
		"VL_DESC": documento.valor_desconto,
		"IND_FRT": documento.indicador_frete,
		"VL_SERV": documento.valor_servico,
		"VL_BC_ICMS": documento.valor_bc_icms,
		"VL_ICMS": documento.valor_icms,
		"VL_NT": documento.valor_nao_tributado,
		"COD_INF": documento.codigo_informacao_complementar,
		"COD_CTA": documento.codigo_conta,
		"COD_MUN_ORIG": documento.codigo_municipio_origem,
		"COD_MUN_DEST": documento.codigo_municipio_destino,
	}


def montar_d190(analitico: AnaliticoTransporte) -> dict:
	"""Campos do registro `D190`, na ordem oficial — 9 campos."""
	return {
		"REG": "D190",
		"CST_ICMS": analitico.cst_icms,
		"CFOP": analitico.cfop,
		"ALIQ_ICMS": analitico.aliquota_icms,
		"VL_OPR": analitico.valor_operacao,
		"VL_BC_ICMS": analitico.valor_bc_icms,
		"VL_ICMS": analitico.valor_icms,
		"VL_RED_BC": analitico.valor_reducao_bc,
		"COD_OBS": analitico.codigo_observacao,
	}


def montar_d990(quantidade_linhas: int) -> dict:
	"""Encerramento do Bloco D, contando também a abertura e ele próprio."""
	if quantidade_linhas < 2:
		raise EfdInvalido(
			f"o Bloco D tem no mínimo duas linhas (D001 e o próprio D990), recebido {quantidade_linhas}"
		)

	return {"REG": "D990", "QTD_LIN_D": str(quantidade_linhas)}


_SITUACOES_SEM_FILHOS = frozenset({"02", "03", "04", SITUACAO_NUMERACAO_INUTILIZADA})


def _conferir_analiticos(documento: DocumentoTransporte, analiticos: list[AnaliticoTransporte]) -> None:
	if documento.codigo_situacao in _SITUACOES_SEM_FILHOS:
		if analiticos:
			raise EfdInvalido(
				f"documento com COD_SIT {documento.codigo_situacao!r} (cancelado, denegado ou "
				"inutilizado) não tem registros filhos"
			)

		return

	if not analiticos:
		raise EfdInvalido(
			f"o documento {documento.numero} exige ao menos um D190 — todo D100 regular tem "
			"registro analítico"
		)

	iniciais = CFOP_INICIAIS_POR_OPERACAO[documento.operacao]
	divergentes = [a.cfop for a in analiticos if a.cfop[0] not in iniciais]

	if divergentes:
		raise EfdInvalido(
			f"com IND_OPER {documento.operacao!r} o CFOP começa com {sorted(iniciais)}; "
			f"divergentes: {divergentes}"
		)

	for nome, do_documento, soma in (
		("VL_BC_ICMS", documento.valor_bc_icms, sum((a.valor_bc_icms for a in analiticos), ZERO)),
		("VL_ICMS", documento.valor_icms, sum((a.valor_icms for a in analiticos), ZERO)),
	):
		if do_documento != soma:
			raise EfdInvalido(
				f"{nome} do D100 ({do_documento}) não bate com a soma dos D190 ({soma}) — "
				f"documento {documento.numero}"
			)


def montar_bloco_d(
	documentos: list[tuple[DocumentoTransporte, list[AnaliticoTransporte]]],
) -> list[dict]:
	"""O bloco D inteiro, com as regras que cruzam `D100` e `D190`.

	Recebe pares documento/analíticos porque o vínculo é hierárquico (nível 2 e 3) e as
	validações que importam são justamente entre os dois níveis:

	- **todo `D100` exige ao menos um `D190`** (com as exceções de documento cancelado ou
	  inutilizado, que não têm registro filho);
	- **o CFOP concorda com o `IND_OPER`** do pai;
	- **base e imposto do documento batem com o analítico** — a soma, pela leitura
	  consistente da tensão documentada na docstring do módulo.
	"""
	if not documentos:
		return [montar_d001(tem_dados=False), montar_d990(2)]

	linhas: list[dict] = [montar_d001(tem_dados=True)]

	for documento, analiticos in documentos:
		_conferir_analiticos(documento, analiticos)

		linhas.append(montar_d100(documento))
		linhas.extend(montar_d190(analitico) for analitico in analiticos)

	return [*linhas, montar_d990(len(linhas) + 1)]
