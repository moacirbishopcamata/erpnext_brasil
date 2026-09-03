# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Bloco C do EFD-ICMS/IPI — documentos fiscais de mercadoria (NF-e/NFC-e e afins).

O maior bloco do arquivo: é onde cada nota fiscal entra. Este módulo cobre o núcleo que
basta para a NF-e/NFC-e de emissão própria — `C001` (abertura), `C100` (o documento,
29 campos), `C190` (registro analítico, 12 campos) e `C990` (encerramento).

Por que C100 + C190 é um recorte defensável, não arbitrário
------------------------------------------------------------------
Não é "o que deu tempo": é a regra do próprio Guia Prático. Para **NF-e de emissão
própria** (Exceção 2 do C100) e para **NFC-e** (Exceção 9), o guia diz que "regra geral,
devem ser apresentados **somente os registros C100 e C190**". O `C170` (itens, ~38
campos) só é admitido em hipóteses específicas — ressarcimento de ICMS-ST com `C176`,
ou documentos de terceiros — e por isso fica para um incremento próprio, com sua própria
verificação, em vez de entrar meio pronto aqui.

Achado real: `IND_FRT` mudou de significado duas vezes, e os códigos se contradizem
------------------------------------------------------------------------------------------------
O campo mais perigoso deste registro. Três domínios diferentes ao longo do tempo, com
**os mesmos números significando coisas diferentes**:

| Código | Até 31/12/2011 | 2012-2017 | Vigente (desde 01/01/2018) |
|---|---|---|---|
| `0` | por conta de terceiros | por conta do emitente | frete por conta do remetente (CIF) |
| `1` | por conta do emitente | por conta do destinatário/remetente | frete por conta do destinatário (FOB) |
| `2` | por conta do destinatário | por conta de terceiros | frete por conta de terceiros |
| `3` | — | — | transporte próprio por conta do remetente |
| `4` | — | — | transporte próprio por conta do destinatário |
| `9` | sem cobrança de frete | sem cobrança de frete | sem ocorrência de transporte |

Repare que `0` e `1` **trocaram de sentido** entre a primeira e a segunda versão: um
arquivo montado com a tabela antiga atribui o frete à parte errada, e passa no
validador — erro silencioso, do tipo que só aparece numa fiscalização. Este módulo
implementa a tabela **vigente** (`0`-`4` e `9`), e a tabela histórica fica aqui
documentada para que ninguém "corrija" o código de volta ao que uma fonte antiga diz.

Regras cruzadas do guia, checadas aqui
---------------------------------------------
- **`CHV_NFE` é obrigatória** desde abril/2012 em todas as situações, **exceto** para
  NF-e com numeração inutilizada (`COD_SIT = "05"`). Checada para os modelos eletrônicos
  (55/65), e validada de verdade (44 posições e dígito verificador) reaproveitando
  `fiscal.documento.chave_acesso.validar_chave` — a mesma validação da família
  NF-e/CT-e/MDF-e, não uma segunda implementação.
- **NFC-e (modelo 65)** não informa `COD_PART` nem os campos de ICMS-ST/IPI/PIS/COFINS
  (Exceção 9 do guia). Preencher esses campos numa NFC-e é erro de montagem, e falhar
  aqui é melhor que ser rejeitado depois sem contexto.

Conflito de fonte registrado: `IND_PGTO`
-----------------------------------------------
O Guia Prático 2.0.13 anota que, "a partir de 01/07/2012", o domínio passaria a ser
`0`/`1`/`2` — sem o `9` (sem pagamento). A fonte secundária atual, porém, lista
`0`/`1`/`2`/`9`. Como as duas se contradizem e nenhuma é a versão mais recente do guia
oficial (o site da RFB continua recusando conexão), este módulo aceita o **superconjunto**
(`0`/`1`/`2`/`9`): recusar um valor possivelmente válido quebraria um usuário legítimo,
enquanto aceitar um possivelmente inválido é pego pelo validador do Fisco. A dúvida fica
declarada em vez de resolvida por chute.

Fontes
----------
Guia Prático oficial EFD-ICMS/IPI versão 2.0.13 (cópia publicada pela SEFAZ-SP, PDF
baixado e lido localmente com `pdftotext`) para o layout e as regras de exceção;
fonte secundária atual (`vriconsulting.com.br`, guia 22) para os domínios vigentes de
`IND_FRT`/`COD_SIT`, que mudaram depois daquele guia. O site oficial da RFB recusou
conexão nesta rodada.

Funções puras: nenhuma dependência do Frappe.
"""

from dataclasses import dataclass
from decimal import Decimal

from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido

__all__ = [
	"COD_SIT_VALIDOS",
	"EMISSAO_PROPRIA",
	"EMISSAO_TERCEIROS",
	"IND_FRT_VALIDOS",
	"IND_PGTO_VALIDOS",
	"MODELOS_ELETRONICOS",
	"MODELO_NFCE",
	"MODELO_NFE",
	"OPERACAO_ENTRADA",
	"OPERACAO_SAIDA",
	"SITUACAO_NUMERACAO_INUTILIZADA",
	"DocumentoFiscal",
	"RegistroAnalitico",
	"montar_c001",
	"montar_c100",
	"montar_c190",
	"montar_c990",
]

OPERACAO_ENTRADA = "0"
OPERACAO_SAIDA = "1"

EMISSAO_PROPRIA = "0"
EMISSAO_TERCEIROS = "1"

MODELO_NFE = "55"
MODELO_NFCE = "65"

MODELOS_ELETRONICOS = frozenset({MODELO_NFE, MODELO_NFCE})

SITUACAO_NUMERACAO_INUTILIZADA = "05"

# Tabela 4.1.2 — código da situação do documento fiscal.
COD_SIT_VALIDOS = {
	"00": "Documento regular",
	"01": "Documento cancelado (parcialmente)",
	"02": "Documento cancelado",
	"03": "Documento cancelado extemporâneo",
	"04": "NF-e/NFC-e denegada",
	"05": "NF-e/NFC-e numeração inutilizada",
	"06": "Nota fiscal complementar",
	"07": "Nota fiscal complementar extemporânea",
	"08": "Emitido sob regime especial ou norma específica",
}

# Superconjunto declarado — ver o conflito de fonte na docstring do módulo.
IND_PGTO_VALIDOS = frozenset({"0", "1", "2", "9"})

# Domínio VIGENTE desde 01/01/2018 — ver a tabela histórica na docstring do módulo.
IND_FRT_VALIDOS = {
	"0": "Contratação do frete por conta do remetente (CIF)",
	"1": "Contratação do frete por conta do destinatário (FOB)",
	"2": "Contratação do frete por conta de terceiros",
	"3": "Transporte próprio por conta do remetente",
	"4": "Transporte próprio por conta do destinatário",
	"9": "Sem ocorrência de transporte",
}

# Campos que a Exceção 9 do guia proíbe numa NFC-e (modelo 65).
_PROIBIDOS_NA_NFCE = (
	"valor_bc_icms_st",
	"valor_icms_st",
	"valor_ipi",
	"valor_pis",
	"valor_cofins",
	"valor_pis_st",
	"valor_cofins_st",
)


@dataclass(frozen=True)
class DocumentoFiscal:
	"""Os dados do registro `C100` — um documento fiscal de mercadoria.

	`codigo_participante` referencia `COD_PART` do registro `0150` (ver
	`efd_bloco_0.Participante`) — é a amarração entre o documento e o cadastro.
	"""

	operacao: str
	emissao: str
	codigo_modelo: str
	codigo_situacao: str
	numero: str
	data_emissao: str
	valor_documento: Decimal
	indicador_pagamento: str
	indicador_frete: str
	codigo_participante: str = ""
	serie: str = ""
	chave_acesso: str = ""
	data_entrada_saida: str = ""
	valor_desconto: Decimal | None = None
	valor_abatimento_nao_tributado: Decimal | None = None
	valor_mercadorias: Decimal | None = None
	valor_frete: Decimal | None = None
	valor_seguro: Decimal | None = None
	valor_outras_despesas: Decimal | None = None
	valor_bc_icms: Decimal | None = None
	valor_icms: Decimal | None = None
	valor_bc_icms_st: Decimal | None = None
	valor_icms_st: Decimal | None = None
	valor_ipi: Decimal | None = None
	valor_pis: Decimal | None = None
	valor_cofins: Decimal | None = None
	valor_pis_st: Decimal | None = None
	valor_cofins_st: Decimal | None = None

	def __post_init__(self) -> None:
		if self.operacao not in (OPERACAO_ENTRADA, OPERACAO_SAIDA):
			raise EfdInvalido(
				f"IND_OPER deve ser {OPERACAO_ENTRADA!r} (entrada) ou {OPERACAO_SAIDA!r} "
				f"(saída), recebido {self.operacao!r}"
			)

		if self.emissao not in (EMISSAO_PROPRIA, EMISSAO_TERCEIROS):
			raise EfdInvalido(
				f"IND_EMIT deve ser {EMISSAO_PROPRIA!r} (própria) ou {EMISSAO_TERCEIROS!r} "
				f"(terceiros), recebido {self.emissao!r}"
			)

		if self.codigo_situacao not in COD_SIT_VALIDOS:
			raise EfdInvalido(
				f"COD_SIT deve ser um de {sorted(COD_SIT_VALIDOS)}, recebido {self.codigo_situacao!r}"
			)

		if self.indicador_pagamento not in IND_PGTO_VALIDOS:
			raise EfdInvalido(
				f"IND_PGTO deve ser um de {sorted(IND_PGTO_VALIDOS)}, recebido {self.indicador_pagamento!r}"
			)

		if self.indicador_frete not in IND_FRT_VALIDOS:
			raise EfdInvalido(
				f"IND_FRT deve ser um de {sorted(IND_FRT_VALIDOS)} (tabela vigente desde "
				f"01/01/2018), recebido {self.indicador_frete!r}"
			)

		if not self.numero:
			raise EfdInvalido("NUM_DOC não pode ser vazio")

		self._validar_chave()
		self._validar_nfce()

	def _validar_chave(self) -> None:
		"""`CHV_NFE` é obrigatória para documento eletrônico desde abril/2012, exceto
		com numeração inutilizada — regra do guia, não invenção deste módulo."""
		eletronico = self.codigo_modelo in MODELOS_ELETRONICOS
		inutilizada = self.codigo_situacao == SITUACAO_NUMERACAO_INUTILIZADA

		if eletronico and not inutilizada and not self.chave_acesso:
			raise EfdInvalido(
				f"CHV_NFE é obrigatória para o modelo {self.codigo_modelo} desde abril/2012, "
				f"exceto com COD_SIT {SITUACAO_NUMERACAO_INUTILIZADA!r} (numeração inutilizada)"
			)

		if not self.chave_acesso:
			return

		from erpnext_brasil.fiscal.documento.chave_acesso import ChaveInvalida, validar_chave

		try:
			validar_chave(self.chave_acesso)
		except ChaveInvalida as e:
			raise EfdInvalido(f"CHV_NFE inválida: {e}") from e

	def _validar_nfce(self) -> None:
		"""Exceção 9 do guia: a NFC-e não informa `COD_PART` nem os campos de
		ICMS-ST/IPI/PIS/COFINS."""
		if self.codigo_modelo != MODELO_NFCE:
			return

		if self.codigo_participante:
			raise EfdInvalido("NFC-e (modelo 65) não informa COD_PART (Exceção 9 do Guia Prático)")

		informados = [nome for nome in _PROIBIDOS_NA_NFCE if getattr(self, nome) is not None]

		if informados:
			raise EfdInvalido(f"NFC-e (modelo 65) não informa {informados} (Exceção 9 do Guia Prático)")


@dataclass(frozen=True)
class RegistroAnalitico:
	"""Os dados do registro `C190` — os totais do documento agrupados pela combinação
	`CST_ICMS` + `CFOP` + `ALIQ_ICMS`.

	Havendo mais de uma combinação na mesma nota, há mais de um `C190` para o mesmo
	`C100` (ocorrência `1:N` no layout).
	"""

	cst_icms: str
	cfop: str
	valor_operacao: Decimal
	valor_bc_icms: Decimal = Decimal("0.00")
	valor_icms: Decimal = Decimal("0.00")
	valor_bc_icms_st: Decimal = Decimal("0.00")
	valor_icms_st: Decimal = Decimal("0.00")
	valor_reducao_bc: Decimal = Decimal("0.00")
	valor_ipi: Decimal = Decimal("0.00")
	aliquota_icms: Decimal | None = None
	codigo_observacao: str = ""

	def __post_init__(self) -> None:
		if len(self.cst_icms) != 3 or not self.cst_icms.isdigit():
			raise EfdInvalido(f"CST_ICMS deve ter 3 dígitos, recebido {self.cst_icms!r}")

		if len(self.cfop) != 4 or not self.cfop.isdigit():
			raise EfdInvalido(f"CFOP deve ter 4 dígitos, recebido {self.cfop!r}")


def montar_c001(tem_dados: bool) -> dict:
	"""Abertura do Bloco C. `IND_MOV` segue a convenção invertida dos registros de
	abertura de bloco (`0` = com dados), a mesma de `efd_bloco_0.montar_0001` — e
	oposta à do `IND_MOV_ST` do E210."""
	return {"REG": "C001", "IND_MOV": "0" if tem_dados else "1"}


def montar_c100(documento: DocumentoFiscal) -> dict:
	"""Campos do registro `C100`, na ordem oficial — 29 campos."""
	return {
		"REG": "C100",
		"IND_OPER": documento.operacao,
		"IND_EMIT": documento.emissao,
		"COD_PART": documento.codigo_participante,
		"COD_MOD": documento.codigo_modelo,
		"COD_SIT": documento.codigo_situacao,
		"SER": documento.serie,
		"NUM_DOC": documento.numero,
		"CHV_NFE": documento.chave_acesso,
		"DT_DOC": documento.data_emissao,
		"DT_E_S": documento.data_entrada_saida,
		"VL_DOC": documento.valor_documento,
		"IND_PGTO": documento.indicador_pagamento,
		"VL_DESC": documento.valor_desconto,
		"VL_ABAT_NT": documento.valor_abatimento_nao_tributado,
		"VL_MERC": documento.valor_mercadorias,
		"IND_FRT": documento.indicador_frete,
		"VL_FRT": documento.valor_frete,
		"VL_SEG": documento.valor_seguro,
		"VL_OUT_DA": documento.valor_outras_despesas,
		"VL_BC_ICMS": documento.valor_bc_icms,
		"VL_ICMS": documento.valor_icms,
		"VL_BC_ICMS_ST": documento.valor_bc_icms_st,
		"VL_ICMS_ST": documento.valor_icms_st,
		"VL_IPI": documento.valor_ipi,
		"VL_PIS": documento.valor_pis,
		"VL_COFINS": documento.valor_cofins,
		"VL_PIS_ST": documento.valor_pis_st,
		"VL_COFINS_ST": documento.valor_cofins_st,
	}


def montar_c190(analitico: RegistroAnalitico) -> dict:
	"""Campos do registro `C190`, na ordem oficial — 12 campos."""
	return {
		"REG": "C190",
		"CST_ICMS": analitico.cst_icms,
		"CFOP": analitico.cfop,
		"ALIQ_ICMS": analitico.aliquota_icms,
		"VL_OPR": analitico.valor_operacao,
		"VL_BC_ICMS": analitico.valor_bc_icms,
		"VL_ICMS": analitico.valor_icms,
		"VL_BC_ICMS_ST": analitico.valor_bc_icms_st,
		"VL_ICMS_ST": analitico.valor_icms_st,
		"VL_RED_BC": analitico.valor_reducao_bc,
		"VL_IPI": analitico.valor_ipi,
		"COD_OBS": analitico.codigo_observacao,
	}


def montar_c990(quantidade_linhas: int) -> dict:
	"""Encerramento do Bloco C, com a contagem de linhas do próprio bloco — mesma
	convenção de `efd_bloco_0.montar_0990`. A contagem inclui o próprio `C990`."""
	if quantidade_linhas < 2:
		raise EfdInvalido(
			f"o Bloco C tem no mínimo duas linhas (C001 e o próprio C990), recebido {quantidade_linhas}"
		)

	return {"REG": "C990", "QTD_LIN_C": str(quantidade_linhas)}
