# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""ECF: Bloco K (Saldos das Contas Contábeis e Referenciais).

Por que existe — a segunda fatia "importada direto da ECD"
------------------------------------------------------------------------------
`docs/ecf-estado.md` já registrava, pela mesma fonte que confirmou o Bloco J: "a ECF
importa dados diretamente da ECD para compor o Bloco J (...) e o Bloco K (Saldos das
Contas Contábeis)". Depois de `J050`/`J051`/`J100` (`ecf_bloco_j.py`), este módulo cobre
o registro principal do Bloco K.

`K155` tem os mesmos valores financeiros de `I155`, mas o indicador D/C tem outro nome
------------------------------------------------------------------------------------------
Confirmado em `documentacao.senior.com.br/.../bloco-k.htm`: `K155` (saldos detalhados,
depois do encerramento de resultado) tem `REG`, `COD_CTA`, `COD_CCUS`, `VL_SLD_INI`,
`IND_VL_SLD_INI`, `VL_DEB`, `VL_CRED`, `VL_SLD_FIN`, `IND_VL_SLD_FIN` — os sete campos
financeiros são idênticos, na mesma ordem, ao `I155` da ECD (`ecd_i150.py`). **Achado
real de divergência de nome, não de valor**: os dois campos indicadores se chamam
`IND_DC_INI`/`IND_DC_FIN` na ECD e `IND_VL_SLD_INI`/`IND_VL_SLD_FIN` na ECF — mesmo
significado (`"D"`/`"C"`, nunca em branco), nome de campo diferente. Padrão consistente
com o resto do registro (`VL_SLD_INI` → `IND_VL_SLD_INI`, `VL_SLD_FIN` →
`IND_VL_SLD_FIN` — o nome do indicador ecoa o nome do valor que qualifica, diferente da
convenção genérica `IND_DC_*` da ECD). Por isso `montar_k155` não delega cegamente
trocando só `REG` (como `montar_j050`/`montar_j051` fazem) — reconstrói o dicionário
renomeando os dois campos indicadores, mantendo os outros sete exatamente como
`montar_i155` os calcula (mesma aritmética de saldo, mesmo `ContaDesconhecida`).

`K156` implementado em seguida — achado real de possível inconsistência de nome, declarado
------------------------------------------------------------------------------------------
`K156` (mapeamento referencial dos saldos finais) tem `REG`, `COD_CTA_REF`, `VL_SLD_INI`,
`IND_VL_SLD_INICIAL`, `VL_DEB`, `VL_CRED`, `VL_SLD_FIN`, `IND_VL_SLD_FIN` — os mesmos
valores financeiros de `K155`, agora indexados por `COD_CTA_REF` (código do plano
referencial da RFB) em vez de `COD_CTA` (código próprio), e sem `COD_CCUS` (o mapeamento
referencial não distingue centro de custo). **Nível de confiança declarado, não
escondido**: duas consultas à mesma fonte devolveram o indicador inicial como
`IND_VL_SLD_INI` (para `K155`) e `IND_VL_SLD_INICIAL` (para `K156`, forma por extenso) —
pode ser uma divergência real entre os dois registros (o leiaute do SPED tem exemplos
conhecidos de inconsistência de nome entre registros próximos, ver `evGTV`/CT-e nesta
mesma frente) ou uma variação de transcrição da fonte secundária. Este módulo grava
`IND_VL_SLD_INICIAL` (a forma que a consulta específica de `K156` devolveu), mas o valor
em si (`"D"`/`"C"`) é idêntico de qualquer forma — o risco fica só no nome do campo, não
no dado, e fica registrado aqui para conferência contra o Manual de Orientação oficial
antes de qualquer geração de arquivo real.

`montar_k156` não agrega várias contas próprias no mesmo código referencial — cada
`MapeamentoReferencial` (o mesmo tipo já usado para `J051`) vira uma linha própria, com o
saldo daquela conta. Agregação de N contas próprias mapeadas para o mesmo
`COD_CTA_REF` não é modelada (a fonte não deixa claro se o PVA agrega ou se cada
mapeamento gera sua própria linha) — declarado como limitação, não escondido.

O que fica de fora deste incremento do Bloco K
------------------------------------------------------------------------------
- **`K030`** (identificação do período e método de apuração de IRPJ/CSLL) — campos
  confirmados na mesma fonte (`REG`, `DT_INI`, `DT_FIN`, `PER_APUR`), mas este projeto não
  modela ainda qual método de apuração a empresa usa (`PER_APUR`); fica para quando o
  núcleo de Lucro Real (Blocos L/M/N) entrar.
- **`K915`/`K935`** (justificativa de divergência de saldo) — a própria fonte diz que
  `K915` "não é gerado pelo ERP" e "o campo de justificativa deve ser preenchido
  manualmente no PVA" — confirma que não é um registro para este projeto calcular, é
  preenchimento manual do usuário final no validador da Receita.
- **`K355`/`K356`** (saldos das contas de resultado **antes** do encerramento) — exige
  distinguir "antes" e "depois" do encerramento de resultado, que `lancamento.py`/
  `ecd_i150.py` não modelam (só produzem o saldo final de cada conta, não os dois
  momentos).
- **`K915`/`K935`** (justificativa de divergência de saldo) — só se aplicam quando há
  divergência a justificar; sem dado real para gerar isso ainda.

Funções puras: nenhuma dependência do Frappe.

Fonte: `documentacao.senior.com.br/goup/5.10.3/menu_controladoria/sped/contabil-fiscal-ecf/
bloco-k.htm`, consultada em 2026-09-03 — mesmo padrão de confiança já aceito para o Bloco J
(fonte técnica de ERP, não o Manual de Orientação da Receita lido diretamente).
"""

from erpnext_brasil.contabil.ecd_i050 import MapeamentoReferencial
from erpnext_brasil.contabil.ecd_i150 import ContaDesconhecida, SaldoInicial, montar_i155
from erpnext_brasil.contabil.lancamento import Lancamento
from erpnext_brasil.contabil.plano_de_contas import ARVORE, montar_codigos

__all__ = [
	"ContaDesconhecida",
	"SaldoInicial",
	"montar_k001",
	"montar_k155",
	"montar_k156",
	"montar_k990",
]


def montar_k001(tem_dados: bool) -> dict:
	"""Monta o registro `K001` — abertura do Bloco K, mesma convenção de `montar_j001`."""
	return {"REG": "K001", "IND_DAD": "0" if tem_dados else "1"}


def montar_k155(
	lancamentos: list[Lancamento], saldos_iniciais: dict[str, SaldoInicial] | None = None
) -> list[dict]:
	"""Monta o registro `K155` a partir de `ecd_i150.montar_i155` — mesma aritmética de
	saldo, só os dois campos indicadores mudam de nome (ver docstring do módulo:
	`IND_DC_INI`/`IND_DC_FIN` da ECD viram `IND_VL_SLD_INI`/`IND_VL_SLD_FIN` na ECF)."""
	linhas_k155 = []

	for linha in montar_i155(lancamentos, saldos_iniciais):
		linhas_k155.append(
			{
				"REG": "K155",
				"COD_CTA": linha["COD_CTA"],
				"COD_CCUS": linha["COD_CCUS"],
				"VL_SLD_INI": linha["VL_SLD_INI"],
				"IND_VL_SLD_INI": linha["IND_DC_INI"],
				"VL_DEB": linha["VL_DEB"],
				"VL_CRED": linha["VL_CRED"],
				"VL_SLD_FIN": linha["VL_SLD_FIN"],
				"IND_VL_SLD_FIN": linha["IND_DC_FIN"],
			}
		)

	return linhas_k155


def montar_k156(
	lancamentos: list[Lancamento],
	mapeamentos: list[MapeamentoReferencial],
	saldos_iniciais: dict[str, SaldoInicial] | None = None,
) -> list[dict]:
	"""Monta o registro `K156` — uma linha por `MapeamentoReferencial`, com o saldo da
	conta própria mapeada, indexado por `COD_CTA_REF` em vez de `COD_CTA` (ver
	docstring do módulo sobre o achado de possível divergência de nome do indicador
	inicial, e sobre agregação de várias contas no mesmo código referencial não ser
	modelada).

	Não recebe `arvore` como parâmetro — `montar_i155` (que este módulo reaproveita
	por dentro) também não recebe, sempre usa `plano_de_contas.ARVORE`; aceitar um
	valor diferente aqui criaria uma inconsistência silenciosa entre os dois lados do
	cruzamento (código próprio resolvido por uma árvore, saldo calculado por outra).
	"""
	codigos = montar_codigos(ARVORE)
	linhas_por_codigo = {linha["COD_CTA"]: linha for linha in montar_i155(lancamentos, saldos_iniciais)}

	linhas_k156 = []

	for mapeamento in mapeamentos:
		codigo_proprio = codigos.get(mapeamento.conta)

		if codigo_proprio is None:
			raise ContaDesconhecida(f"Conta {mapeamento.conta!r} não existe em plano_de_contas.ARVORE")

		linha_saldo = linhas_por_codigo.get(codigo_proprio)

		if linha_saldo is None:
			# Conta mapeada, mas sem movimento no período — mesma disciplina de
			# `montar_i155`: nenhuma linha é gerada, não é erro.
			continue

		linhas_k156.append(
			{
				"REG": "K156",
				"COD_CTA_REF": mapeamento.codigo_referencial,
				"VL_SLD_INI": linha_saldo["VL_SLD_INI"],
				"IND_VL_SLD_INICIAL": linha_saldo["IND_DC_INI"],
				"VL_DEB": linha_saldo["VL_DEB"],
				"VL_CRED": linha_saldo["VL_CRED"],
				"VL_SLD_FIN": linha_saldo["VL_SLD_FIN"],
				"IND_VL_SLD_FIN": linha_saldo["IND_DC_FIN"],
			}
		)

	return linhas_k156


def montar_k990(quantidade_linhas: int) -> dict:
	"""Monta `K990` — encerramento do Bloco K, mesma convenção de `montar_j990`."""
	return {"REG": "K990", "QTD_LIN": str(quantidade_linhas)}
