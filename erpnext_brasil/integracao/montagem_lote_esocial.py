# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Monta e assina um `Lote eSocial` a partir de holerites — a última peça antes da tela.

O que fecha
------------------
A cadeia do eSocial estava assim depois dos incrementos anteriores:

```text
folha_esocial.evento_do_holerite      Salary Slip → árvore do S-1200        ✅
esocial_id.gerar_id_evento            o `Id` de 36 caracteres                ✅
esocial_montagem.montar_evento_assinado   assina cada evento                 ✅
esocial_lote.montar_xml_lote          envelopa os eventos assinados          ✅
transmissao_lote_esocial              transmite o `Lote eSocial`             ✅
```

Cada peça pronta, e **nada que as compusesse**. Este módulo é a composição: recebe
holerites, produz o `Lote eSocial` gravado, com o XML pronto para transmitir.

⚠️ O certificado é aberto **uma vez** para o lote inteiro
-----------------------------------------------------------------
`TransporteEsocial` expõe `assinador` de propósito — e é aqui que isso se paga. Abrir o
PKCS#12 por evento significaria decifrar a chave privada cem vezes numa folha de cem
empregados, e cada abertura é operação cara de criptografia.

Por isso o transporte entra como `with` **em volta do laço**, não dentro dele.

Por que o lote nasce em rascunho, e não transmitido
------------------------------------------------------------
Montar e transmitir são decisões diferentes. Um lote montado pode ser conferido antes de
sair — e, em eSocial, **o que foi transmitido não se desfaz**: retificar exige outro evento,
com o número do recibo do primeiro.

Separar as duas coisas dá ao usuário o momento de olhar, e é o mesmo motivo de
`importar_nfe` não criar o documento sozinho.

⚠️ O limite do lote é do leiaute, não escolha
------------------------------------------------------
`esocial_lote` recusa mais de `LIMITE_MAXIMO_EVENTOS_POR_LOTE` eventos, e este módulo
**não fatia automaticamente** em vários lotes. Fatiar sem pedir produziria vários
`Lote eSocial` de um clique, e quem transmitisse o primeiro acharia que transmitiu tudo.

Estado de verificação: camada Frappe, **não** exercitada contra bench real.
"""

from datetime import datetime

import frappe
from frappe import _

from erpnext_brasil.folha.esocial_id import TIPO_INSCRICAO_CNPJ, gerar_id_evento
from erpnext_brasil.folha.esocial_lote import (
	EventoLote,
	IdeEmpregadorLote,
	IdeTransmissorLote,
	LoteEventos,
	montar_xml_lote,
)
from erpnext_brasil.folha.esocial_montagem import montar_evento_assinado
from erpnext_brasil.integracao.certificado_a1 import carregar_certificado_da_empresa
from erpnext_brasil.integracao.configuracao_fiscal import (
	ambiente_esocial_da_empresa,
	transmissor_esocial_da_empresa,
)
from erpnext_brasil.integracao.folha_esocial import evento_do_holerite
from erpnext_brasil.integracao.transporte_esocial import TransporteEsocial

__all__ = ["GRUPO_PADRAO", "VERSAO_PROCESSO", "montar_lote_de_holerites"]

GRUPO_PADRAO = 1
"""`grupo` do `envioLoteEventos`.

⚠️ O significado exato dos valores **não foi confirmado** em fonte primária — está anotado
assim em `esocial_lote.py` desde o primeiro incremento, e continua. `1` é o valor usado para
eventos periódicos nas implementações de referência; quem souber o contrário passa outro.
"""

VERSAO_PROCESSO = "erpnext_brasil"
"""`verProc` — identifica o software que gerou o evento, para o Fisco.

Nome do app, não a versão: `verProc` admite 20 caracteres, e amarrar a versão aqui faria
cada `bump` mudar o conteúdo de eventos idênticos.
"""

SITUACAO_INICIAL = "Enviado"
"""Situação com que o lote nasce.

⚠️ Nome herdado do `Select` do DocType, e ele **mente um pouco**: o lote nasce montado, não
enviado. Trocar o rótulo mudaria dado já gravado em sites existentes, então o que se faz é
declarar aqui — e `transmitir_lote_esocial` é quem de fato envia.
"""


def _digitos(valor: str | None) -> str:
	import re

	return re.sub(r"\D", "", valor or "")


def _conferir_mesma_empresa(holerites: list[str]) -> str:
	"""Todos os holerites do lote pertencem à mesma `Company`.

	O `ideEmpregador` é **um por lote**: misturar empresas produziria um envelope que
	declara uma e contém eventos de outra — aceito pelo montador, recusado pelo eSocial, e
	com uma mensagem que não diria qual holerite é o intruso.
	"""
	empresas = {frappe.db.get_value("Salary Slip", nome, "company") for nome in holerites}

	if len(empresas) > 1:
		frappe.throw(
			_("Um lote do eSocial é de uma empresa só; a seleção tem {0}: {1}.").format(
				len(empresas), ", ".join(sorted(str(e) for e in empresas))
			)
		)

	empresa = empresas.pop() if empresas else None

	if not empresa:
		frappe.throw(_("Não foi possível determinar a empresa dos holerites selecionados."))

	return empresa


def montar_lote_de_holerites(holerites: list[str] | str, momento: datetime | None = None) -> str:
	"""Monta, assina e grava um `Lote eSocial` com o S-1200 de cada holerite.

	`momento` é injetável para que o `Id` do evento seja determinístico em teste — mesma
	razão de `gerar_id_evento` receber o horário em vez de chamar `now()` por dentro.

	Devolve o nome do `Lote eSocial` criado, **em rascunho**: montar e transmitir são
	decisões diferentes.
	"""
	if isinstance(holerites, str):
		holerites = frappe.parse_json(holerites)

	if not holerites:
		frappe.throw(_("Selecione ao menos um holerite."))

	empresa = _conferir_mesma_empresa(holerites)

	cnpj = _digitos(frappe.db.get_value("Company", empresa, "tax_id"))

	if not cnpj:
		frappe.throw(_("A empresa {0} não tem CNPJ preenchido.").format(empresa))

	ambiente = ambiente_esocial_da_empresa(empresa)
	transmissor = _digitos(transmissor_esocial_da_empresa(empresa)) or cnpj
	quando = momento or datetime.now()

	pfx, senha = carregar_certificado_da_empresa(empresa)

	eventos: list[EventoLote] = []

	# Um `with` em volta do laço, não dentro: abrir o PKCS#12 por evento decifraria a
	# chave privada uma vez por empregado — ver docstring do módulo.
	with TransporteEsocial(pfx=pfx, senha=senha, ambiente=ambiente) as transporte:
		for sequencial, holerite in enumerate(holerites, start=1):
			id_evento = gerar_id_evento(
				tp_insc=TIPO_INSCRICAO_CNPJ,
				nr_insc=cnpj,
				momento=quando,
				sequencial=sequencial,
			)

			arvore = evento_do_holerite(
				holerite_nome=holerite,
				id_evento=id_evento,
				ambiente=ambiente,
				ver_proc=VERSAO_PROCESSO,
			)

			eventos.append(
				EventoLote(
					id_evento=id_evento,
					xml_assinado=montar_evento_assinado(arvore, id_evento, transporte.assinador),
				)
			)

	lote = LoteEventos(
		grupo=GRUPO_PADRAO,
		ide_empregador=IdeEmpregadorLote(tp_insc=TIPO_INSCRICAO_CNPJ, nr_insc=cnpj),
		ide_transmissor=IdeTransmissorLote(tp_insc=TIPO_INSCRICAO_CNPJ, nr_insc=transmissor),
		eventos=tuple(eventos),
	)

	registro = frappe.get_doc(
		{
			"doctype": "Lote eSocial",
			"company": empresa,
			"grupo": GRUPO_PADRAO,
			"ambiente": "Produção" if ambiente == 1 else "Produção restrita",
			"situacao": SITUACAO_INICIAL,
			"xml_enviado": montar_xml_lote(lote),
			# As linhas nascem com o `id_evento` e sem retorno: é o retorno que as
			# preenche, e `transmissao_lote_esocial` as substitui inteiras ao gravar.
			"eventos": [{"id_evento": evento.id_evento, "tipo_evento": "S-1200"} for evento in eventos],
		}
	)
	registro.insert()

	return registro.name


@frappe.whitelist()
def montar_lote(holerites: list[str] | str) -> dict:
	"""Ponto de entrada da tela. Devolve `{"lote", "eventos"}`."""
	nome = montar_lote_de_holerites(holerites)

	return {
		"lote": nome,
		"eventos": frappe.db.count("Evento do Lote eSocial", {"parent": nome}),
	}
