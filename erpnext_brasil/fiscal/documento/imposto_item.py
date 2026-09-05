# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Grupo `imposto` do item: ICMS, IPI, PIS, COFINS, ISSQN, e o encaixe do IBS/CBS.

Escopo deste módulo — leia antes de estender
---------------------------------------------
O XSD define **cerca de 20 variantes de ICMS** por CST/CSOSN (`ICMS00`, `ICMS10`,
`ICMS20`, ..., `ICMSSN900`), cada uma com seu próprio conjunto de campos. Modelar as 20
não cabia neste incremento, e fazê-lo pela metade seria pior que ser explícito sobre o
recorte. Estão cobertas as variantes que `fiscal/impostos/icms.py` já sabe calcular:

- **ICMS00** — tributação integral;
- **ICMS20** — redução de base;
- **ICMS40/41/60** — isenta / não tributada / cobrado anteriormente por ST (mesma forma,
  o que muda é só o CST e a eventual desoneração);
- **ICMSSN101/102** — Simples Nacional, com e sem crédito.

**Fora do escopo, e não finja que está coberto**: ICMS-ST nas variantes próprias
(`ICMSPart`, `ICMSST`), `PISST`/`COFINSST`, `II` (imposto de importação). Adicionar
precisa vir acompanhado do cálculo correspondente — este módulo só monta o que a
apuração sabe calcular, nunca o contrário.

DIFAL (`ICMSUFDest`) já está coberto — não é mais gap
------------------------------------------------------------
`fiscal/impostos/icms.calcular_difal` já calculava o diferencial de alíquotas (EC
87/2015) desde antes, mas este módulo não sabia montar o grupo `ICMSUFDest` da
NF-e — o cálculo existia sem ter como entrar no XML. `montar_icms_uf_dest`
(`_grupo_icms_uf_dest`) fecha essa lacuna: monta os nove campos do grupo,
confirmados contra a NT 2015.003 (`vBCUFDest`, `vBCFCPUFDest`, `pFCPUFDest`,
`pICMSUFDest`, `pICMSInter`, `pICMSInterPart`, `vFCPUFDest`, `vICMSUFDest`,
`vICMSUFRemet`, nesta ordem).

`vICMSUFRemet` existe no leiaute, mas é **sempre zero desde 2019**
------------------------------------------------------------------------------
A partilha do DIFAL entre origem e destino foi um regime de transição (EC 87/2015):
a partir de 2019, 100% do diferencial vai para o destino — não há mais parcela para
a UF de origem. O campo continua existindo no XSD (não foi removido), só que seu
valor é estruturalmente zero a partir dessa data. Este módulo não hardcoda esse
"sempre 100%" — `percentual_partilha_destino` é parâmetro obrigatório, calculado
por quem chama a partir da data da operação, mesma disciplina de nunca supor uma
alíquota legalmente faseada (ver `ibs_cbs.py`/`ANO_TESTE`, `boleto.py`/bases de
fator de vencimento).

A escolha de qual variante montar (mercadoria × serviço, qual CST de ICMS) é do
chamador — este módulo não infere natureza de operação a partir de dado incompleto.

IBS/CBS já está pronto
-----------------------
`fiscal/documento/ibs_cbs_xml.py` já monta o grupo `IBSCBS`. Este módulo só o encaixa
como irmão de `ICMS`/`ISSQN` dentro de `imposto` — não duplica a lógica.
"""

from decimal import Decimal

from erpnext_brasil.fiscal.documento.ibs_cbs_xml import grupo_ibscbs_item
from erpnext_brasil.fiscal.impostos.apuracao import ApuracaoItem
from erpnext_brasil.fiscal.impostos.icms import arredondar

__all__ = [
	"CST_COM_ICMS_DESONERADO",
	"CST_ICMS_SUPORTADOS",
	"ImpostoInvalido",
	"montar_icms_uf_dest",
	"montar_imposto_item",
]

CST_ICMS_SUPORTADOS = ("00", "20", "40", "41", "60")
"""Os CSTs que `montar_imposto_item` sabe montar — não a tabela inteira do leiaute.

Exposto porque o Select de `br_cst_icms` precisa oferecer **exatamente** estes: um valor
a mais na tela produziria `ImpostoInvalido` no meio da emissão, depois de o usuário já ter
escolhido; um a menos esconderia caso que o código cobre.

Fora daqui ficam, entre outros, o `10`/`70` (ICMS-ST na própria operação) e o `51`
(diferimento) — cada um exige grupo XML próprio, com campos que este projeto ainda não
modela. Ampliar a lista sem implementar o grupo é o erro que a constante evita.
"""

# CSTs em que `vICMSDeson`/`motDesICMS` fazem sentido — desoneração condicional
# (ex.: isenção de IPVA/ICMS para taxista). Confirmado no leiaute e no guia de uso.
CST_COM_ICMS_DESONERADO = ("20", "30", "40", "41", "70", "90")

# Motivos de desoneração do ICMS (campo `motDesICMS`), tabela do leiaute.
MOTIVO_DESONERACAO = {
	"1": "Táxi",
	"3": "Produtor Agropecuário",
	"9": "Outros",
	"12": "Órgão de fomento e desenvolvimento agropecuário",
}


class ImpostoInvalido(ValueError):
	def __init__(self, mensagem: str, campo: str = ""):
		super().__init__(mensagem)
		self.campo = campo


def _valor(quantia) -> str:
	return str(arredondar(Decimal(str(quantia or 0))))


def _percentual(fracao: Decimal) -> str:
	"""Alíquota do ICMS/IPI/PIS/COFINS no XML é percentual com até 4 casas."""
	return str((fracao * 100).quantize(Decimal("0.0001")))


def _grupo_icms_integral(apuracao: ApuracaoItem, cst: str) -> dict:
	"""ICMS00 — tributação integral. Também serve de base para as demais variantes."""
	return {
		"orig": "0",
		"CST": cst,
		"modBC": "3",  # valor da operação — as demais modalidades não são calculadas aqui
		"vBC": _valor(apuracao.base_icms),
		"pICMS": _percentual(apuracao.icms.aliquota),
		"vICMS": _valor(apuracao.icms.valor),
	}


def _grupo_icms_reduzido(apuracao: ApuracaoItem, cst: str = "20") -> dict:
	"""ICMS20 — redução de base. `pRedBC` é obrigatório nesta variante."""
	if apuracao.item.reducao_icms <= 0:
		raise ImpostoInvalido("ICMS20 exige percentual de redução de base maior que zero", "reducao_icms")

	return {
		"orig": "0",
		"CST": cst,
		"modBC": "3",
		"pRedBC": _percentual(apuracao.item.reducao_icms),
		"vBC": _valor(apuracao.icms.base),
		"pICMS": _percentual(apuracao.icms.aliquota),
		"vICMS": _valor(apuracao.icms.valor),
	}


def _grupo_icms_isento_ou_nao_tributado(cst: str) -> dict:
	"""ICMS40/41/60 — isenta, não tributada, ou ST cobrada anteriormente.

	Sem base nem alíquota: por definição não há ICMS a destacar. `vICMSDeson` e
	`motDesICMS` ficam fora — são para desoneração condicional, que este app não calcula.
	"""
	if cst not in ("40", "41", "60"):
		raise ImpostoInvalido(f"CST {cst} não é isenção/não tributação/ST anterior", "cst")

	return {"orig": "0", "CST": cst}


def _grupo_icms_simples_nacional(apuracao: ApuracaoItem, csosn: str) -> dict:
	"""ICMSSN101 (com crédito) ou ICMSSN102 (sem crédito), conforme o CSOSN."""
	grupo = {"orig": "0", "CSOSN": csosn}

	if csosn == "101":
		grupo["pCredSN"] = _percentual(apuracao.icms.aliquota)
		grupo["vCredICMSSN"] = _valor(apuracao.icms.valor)

	return grupo


def _grupo_ipi(apuracao: ApuracaoItem, tributado: bool) -> dict:
	"""Grupo IPI: `IPITrib` quando há incidência, `IPINT` quando não (fora do campo)."""
	cst = "50" if tributado else "53"

	if not tributado:
		return {"IPINT": {"CST": cst}}

	return {
		"IPITrib": {
			"CST": cst,
			"vBC": _valor(apuracao.ipi.base),
			"pIPI": _percentual(apuracao.item.aliquota_ipi),
			"vIPI": _valor(apuracao.ipi.valor),
		}
	}


def _grupo_pis(apuracao: ApuracaoItem) -> dict:
	"""PIS, variante `PISAliq` — alíquota por percentual, sem substituição."""
	return {
		"PISAliq": {
			"CST": "01",
			"vBC": _valor(apuracao.pis_cofins.base),
			"pPIS": _percentual(apuracao.pis_cofins.aliquota_pis),
			"vPIS": _valor(apuracao.pis_cofins.pis),
		}
	}


def _grupo_cofins(apuracao: ApuracaoItem) -> dict:
	"""COFINS, variante `COFINSAliq` — mesmo padrão do PIS."""
	return {
		"COFINSAliq": {
			"CST": "01",
			"vBC": _valor(apuracao.pis_cofins.base),
			"pCOFINS": _percentual(apuracao.pis_cofins.aliquota_cofins),
			"vCOFINS": _valor(apuracao.pis_cofins.cofins),
		}
	}


def _grupo_issqn(base: Decimal, aliquota: Decimal, municipio: str, item_lista_servico: str) -> dict:
	"""ISSQN — para item de serviço. Mutuamente exclusivo com ICMS no mesmo item."""
	if not municipio:
		raise ImpostoInvalido("Município de incidência do ISSQN é obrigatório", "municipio")

	if not item_lista_servico:
		raise ImpostoInvalido(
			"Item da lista de serviços (LC 116) é obrigatório para ISSQN", "item_lista_servico"
		)

	valor_iss = arredondar(base * aliquota)

	return {
		"vBC": _valor(base),
		"vAliq": _percentual(aliquota),
		"vISSQN": _valor(valor_iss),
		# O nome oficial é cMunFG (mesmo nome do grupo ide), não cMunFGISS — nome que
		# pareceria natural por analogia com cMunFGIBS, mas não existe no leiaute.
		"cMunFG": municipio,
		"cListServ": item_lista_servico,
	}


def montar_icms_uf_dest(
	resultado_difal: dict,
	aliquota_interestadual: Decimal,
	aliquota_interna_destino: Decimal,
	percentual_partilha_destino: Decimal,
	aliquota_fcp: Decimal = Decimal(0),
) -> dict:
	"""Grupo `ICMSUFDest` — partilha do DIFAL (EC 87/2015) entre origem e destino.

	`resultado_difal` é a saída de `fiscal/impostos/icms.calcular_difal` (mesmo
	`aliquota_fcp` usado nos dois, para que `resultado_difal["fcp"]` e os campos de
	FCP aqui montados venham da mesma base). `percentual_partilha_destino` nunca é
	suposto — ver docstring do módulo sobre por que `vICMSUFRemet` não é hardcodado
	como zero, mesmo sendo estruturalmente zero desde 2019.
	"""
	if not (Decimal("0") <= percentual_partilha_destino <= Decimal("1")):
		raise ImpostoInvalido(
			"percentual_partilha_destino deve ser uma fração entre 0 e 1",
			"percentual_partilha_destino",
		)

	difal = resultado_difal["difal"]
	v_icms_uf_dest = arredondar(difal * percentual_partilha_destino)
	v_icms_uf_remet = arredondar(difal - v_icms_uf_dest)

	grupo = {"vBCUFDest": _valor(resultado_difal["base_destino"])}

	if aliquota_fcp:
		grupo["vBCFCPUFDest"] = _valor(resultado_difal["base_destino"])
		grupo["pFCPUFDest"] = _percentual(aliquota_fcp)

	grupo.update(
		{
			"pICMSUFDest": _percentual(aliquota_interna_destino),
			"pICMSInter": _percentual(aliquota_interestadual),
			"pICMSInterPart": _percentual(percentual_partilha_destino),
		}
	)

	if aliquota_fcp:
		grupo["vFCPUFDest"] = _valor(resultado_difal["fcp"])

	grupo["vICMSUFDest"] = _valor(v_icms_uf_dest)
	grupo["vICMSUFRemet"] = _valor(v_icms_uf_remet)

	return grupo


def montar_imposto_item(
	apuracao: ApuracaoItem,
	cst_icms: str | None = None,
	csosn: str | None = None,
	icms_tributado: bool = True,
	ipi_tributado: bool = False,
	issqn: dict | None = None,
	icms_uf_dest: dict | None = None,
) -> dict:
	"""Monta o grupo `imposto` de um item.

	    `cst_icms` e `csosn` são mutuamente exclusivos: regime normal informa CST, Simples
	    Nacional informa CSOSN. Informar ISSQN torna o item de serviço, e é incompatível com
	    ICMS/IPI no mesmo item — mercadoria e serviço não se misturam no mesmo detalhe.

	    `icms_uf_dest` (saída de `montar_icms_uf_dest`) entra como `ICMSUFDest`, **dentro**
	    do grupo `ICMS` — irmão de `ICMS00`/`ICMSSN101`/etc, não fora dele (confirmado
	    contra o caminho oficial `det/imposto/ICMS/ICMSUFDest`, não um grupo separado no
	    nível de `imposto`). Incompatível com ISSQN pela mesma razão que ICMS em si é.

	    O grupo IBS/CBS entra sempre que a apuração o tiver calculado, independente do item
	ser mercadoria ou serviço: a reforma tributária alcança os dois.
	"""
	if icms_uf_dest and issqn:
		raise ImpostoInvalido(
			"Item de serviço (ISSQN) não tem ICMSUFDest: mercadoria e serviço não se misturam no mesmo item",
			"icms_uf_dest",
		)
	if cst_icms and csosn:
		raise ImpostoInvalido("Informe CST ou CSOSN, nunca os dois", "cst_icms")

	if issqn and (cst_icms or csosn):
		raise ImpostoInvalido(
			"Item de serviço (ISSQN) não tem ICMS: mercadoria e serviço não se misturam no mesmo item",
			"issqn",
		)

	grupo: dict = {}

	if issqn:
		grupo["ISSQN"] = _grupo_issqn(**issqn)
	elif csosn:
		grupo["ICMS"] = {f"ICMSSN{csosn}": _grupo_icms_simples_nacional(apuracao, csosn)}
	elif cst_icms == "00":
		grupo["ICMS"] = {"ICMS00": _grupo_icms_integral(apuracao, "00")}
	elif cst_icms == "20":
		grupo["ICMS"] = {"ICMS20": _grupo_icms_reduzido(apuracao)}
	elif cst_icms in ("40", "41", "60"):
		grupo["ICMS"] = {f"ICMS{cst_icms}": _grupo_icms_isento_ou_nao_tributado(cst_icms)}
	else:
		raise ImpostoInvalido(
			f"CST de ICMS {cst_icms!r} não é montado por este módulo — ver docstring para o escopo coberto",
			"cst_icms",
		)

	if icms_uf_dest:
		grupo["ICMS"]["ICMSUFDest"] = icms_uf_dest

	if not issqn:
		grupo["IPI"] = _grupo_ipi(apuracao, ipi_tributado)
		grupo["PIS"] = _grupo_pis(apuracao)
		grupo["COFINS"] = _grupo_cofins(apuracao)

	ibscbs = grupo_ibscbs_item(
		apuracao.ibs_cbs,
		cst=apuracao.item.cst_ibs_cbs,
		classificacao_tributaria=apuracao.item.classificacao_tributaria,
	)
	grupo.update(ibscbs)

	return {"imposto": grupo}
