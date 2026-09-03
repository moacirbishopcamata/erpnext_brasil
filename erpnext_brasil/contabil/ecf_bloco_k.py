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

O que fica de fora deste primeiro incremento do Bloco K
------------------------------------------------------------------------------
- **`K030`** (identificação do período e método de apuração de IRPJ/CSLL — trimestral,
  anual por estimativa) — este projeto não modela ainda qual método de apuração a
  empresa usa; fica para quando o núcleo de Lucro Real (Blocos L/M/N) entrar.
- **`K156`** (mapeamento referencial dos saldos finais) — mesmo papel de `J051`/`I051`
  para o Bloco K, mas não investigado a fundo ainda; candidato a incremento seguinte.
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

from erpnext_brasil.contabil.ecd_i150 import ContaDesconhecida, SaldoInicial, montar_i155
from erpnext_brasil.contabil.lancamento import Lancamento

__all__ = ["ContaDesconhecida", "SaldoInicial", "montar_k001", "montar_k155", "montar_k990"]


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


def montar_k990(quantidade_linhas: int) -> dict:
	"""Monta `K990` — encerramento do Bloco K, mesma convenção de `montar_j990`."""
	return {"REG": "K990", "QTD_LIN": str(quantidade_linhas)}
