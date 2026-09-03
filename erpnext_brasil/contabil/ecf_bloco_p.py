# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""ECF: Bloco P (Lucro Presumido) — abertura/encerramento apenas.

Por que só isso, desta vez — achado real que limitou o escopo
------------------------------------------------------------------------------
Confirmado em `documentacao.senior.com.br/.../bloco-p.htm`: o Bloco P tem dez
registros — `P001`/`P990` (abertura/encerramento, mesma convenção dos outros blocos),
`P030` (período/método de apuração — mesma pendência já registrada para `K030`: este
projeto não modela qual método de apuração a empresa usa), `P100` (Balanço
Patrimonial), `P150` (Demonstração do Resultado), e **seis registros**
(`P130`/`P200`/`P230`/`P300`/`P400`/`P500`) com o **mesmo formato genérico**: `REG`,
`CODIGO`, `DESCRICAO`, `VALOR` (mais `IND_VALOR`/similar em alguns) — cada um é uma
tabela de memória de cálculo (base do IRPJ, isenção/redução, cálculo do IRPJ, base da
CSLL, cálculo da CSLL) referenciando um **catálogo de códigos** publicado pela Receita
que este incremento não tem verificado.

**Por que não implementar os seis registros de código+valor com uma função genérica
"aceita qualquer código"**: uma função que só embrulha `(codigo, descricao, valor)` num
dicionário não encodifica nenhum conhecimento de domínio — é indistinguível de um
`dict` literal, e daria a falsa impressão de que os códigos foram verificados quando
não foram. Sem o catálogo oficial (qual `CODIGO` é "Receita Bruta", qual é "Lucro
Presumido", em que ordem aparecem), implementar aqui seria abrir espaço para alguém
preencher um `CODIGO` inventado sem perceber que nunca foi conferido contra a tabela
real da Receita.

`P100`/`P150` — candidatos reais de reuso, não implementados por falta de confirmação
------------------------------------------------------------------------------------------
`P100` (Balanço Patrimonial) combina exatamente os campos de plano de contas já
produzidos por `ecd_i050.montar_i050` (`DESCRICAO`≈`CTA`, `NIVEL`, `COD_NAT`,
`COD_CTA_SUP`) com os de saldo já produzidos por `ecd_i150.montar_i155`/
`ecf_bloco_k.montar_k155` (`VAL_CTA_REF_INI`/`IND_VAL_CTA_REF_INI`/`VAL_CTA_REF_FIN`/
`IND_VAL_CTA_REF_FIN` ≈ `VL_SLD_INI`/`IND_DC_INI`/`VL_SLD_FIN`/`IND_DC_FIN`) — um
padrão de reuso genuíno, mesmo espírito do que já funcionou para `J050`/`K155`. **Não
implementado ainda** porque a fonte secundária usada não confirma se `P100` recebe o
plano de contas **próprio** ou o **referencial** da RFB (o nome `CODIGO`, não
`COD_CTA`, sugere referencial — mas isso mudaria de onde vêm os dados, e essa dúvida
não está resolvida com confiança suficiente para implementar). `P150` (DRE) tem forma
parecida, mesma dúvida.

Funções puras: nenhuma dependência do Frappe.

Fonte: `documentacao.senior.com.br/goup/5.10.3/menu_controladoria/sped/contabil-fiscal-ecf/
bloco-p.htm`, consultada em 2026-09-03 — mesmo padrão de confiança já aceito para os
Blocos 0/J/K.
"""

__all__ = ["montar_p001", "montar_p990"]


def montar_p001(tem_dados: bool) -> dict:
	"""Monta o registro `P001` — abertura do Bloco P, mesma convenção de
	`montar_j001`/`montar_k001`/`ecf_bloco_0.montar_0001`."""
	return {"REG": "P001", "IND_DAD": "0" if tem_dados else "1"}


def montar_p990(quantidade_linhas: int) -> dict:
	"""Monta `P990` — encerramento do Bloco P, mesma convenção dos demais blocos."""
	return {"REG": "P990", "QTD_LIN": str(quantidade_linhas)}
