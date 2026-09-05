# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Gera o arquivo EFD-ICMS/IPI de um período e o registra no `Arquivo SPED`.

Fecha o último trecho da cadeia do SPED, que existia inteira em pedaços incomunicáveis:

```text
efd_dados_cadastrais   Bloco 0 a partir da Company e do Address
efd_escrituracao       Bloco C a partir dos documentos do período
efd_apuracao           Bloco E: débitos e créditos de ICMS do período
efd_inventario         Bloco H: saldo de estoque na data de encerramento
efd_producao           Bloco K: saldos escriturados e produção do período
efd_arquivo            junta os blocos, calcula o Bloco 9, serializa
Arquivo SPED           guarda o texto, o hash e o período
```

Cada peça estava testada e **nenhuma chamava a outra** — três módulos órfãos em
`docs/gaps.md`. Este é o adaptador que os liga, exposto por `@frappe.whitelist()` para que
exista um caminho de uso, não só de biblioteca.

O endereço é escolhido por quem chama, não deduzido
------------------------------------------------------------
`montar_identificacao_0000` já registra o porquê: a `Company` pode ter vários `Address`
vinculados e o ERPNext não tem "endereço fiscal" único sem ambiguidade. Aqui a decisão é
repassada — este módulo não sabe mais do que aquele, e escolher o primeiro da lista seria
inventar critério.

O que ainda **não** entra no arquivo
--------------------------------------------
O bloco **D** (serviço de transporte) tem o leiaute
implementado em `contabil/` e **ainda não têm quem os leia do site** — o equivalente de
`efd_escrituracao` para cada um. O arquivo gerado aqui é, portanto, **incompleto para
entrega**: serve para conferir a montagem contra o PVA, não para transmitir.

O **Bloco E** deixou de estar nessa lista em 2026-09-05 (`integracao/efd_apuracao.py`) —
e era o mais urgente dos quatro, porque é o único que não admite ser declarado vazio.

Isso está dito também na mensagem de retorno, e não só aqui: quem clica precisa saber o
que recebeu. Prometer arquivo entregável e devolver parcial seria o tipo de silêncio que
este projeto trata como pior que erro.

Estado de verificação: camada Frappe, **não** exercitada contra bench real.
"""

import frappe
from frappe import _

from erpnext_brasil.contabil.arquivo_sped_registro import FINALIDADE_ORIGINAL, TIPO_EFD_ICMS_IPI
from erpnext_brasil.contabil.efd_arquivo import montar_arquivo_efd, serializar_arquivo_efd
from erpnext_brasil.contabil.efd_bloco_0 import (
	montar_0001,
	montar_0990,
)
from erpnext_brasil.integracao.efd_apuracao import bloco_e_do_periodo
from erpnext_brasil.integracao.efd_dados_cadastrais import montar_identificacao_0000
from erpnext_brasil.integracao.efd_escrituracao import bloco_c_do_periodo
from erpnext_brasil.integracao.efd_inventario import bloco_h_do_periodo
from erpnext_brasil.integracao.efd_producao import bloco_k_do_periodo

__all__ = ["BLOCOS_SEM_LEITURA_DO_SITE", "gerar_efd"]

BLOCOS_SEM_LEITURA_DO_SITE = ("D",)
"""Blocos com leiaute pronto e sem quem os leia do site — ver docstring do módulo."""


def _bloco_zero(company: str, address: str, data_inicial: str, data_final: str) -> list[dict]:
	"""Abertura, identificação e encerramento do Bloco 0.

	Os cadastros (`0150` participantes, `0190` unidades, `0200` itens) ainda não entram:
	dependem de varrer os documentos do período para saber **quais** participantes e itens
	foram usados, que é trabalho da mesma camada que falta para os demais blocos. Um Bloco
	0 sem eles é recusado pelo PVA, e é exatamente por isso que o retorno avisa que o
	arquivo é parcial.
	"""
	from erpnext_brasil.contabil.efd_bloco_0 import montar_0000

	identificacao = montar_identificacao_0000(
		company=company,
		address=address,
		data_inicial=data_inicial,
		data_final=data_final,
	)

	linhas = [montar_0000(identificacao), montar_0001(tem_dados=True)]

	return [*linhas, montar_0990(len(linhas) + 1)]


@frappe.whitelist()
def gerar_efd(company: str, address: str, data_inicial: str, data_final: str) -> dict:
	"""Gera o arquivo do período e cria o `Arquivo SPED` correspondente.

	Devolve `{"registro", "linhas", "blocos_ausentes", "aviso"}`. O aviso não é decoração:
	o arquivo ainda não tem os blocos D/H/K nem os cadastros do Bloco 0, e quem clica
	precisa saber disso antes de tentar transmitir.
	"""
	blocos = {
		"0": _bloco_zero(company, address, data_inicial, data_final),
		"C": bloco_c_do_periodo(company, data_inicial, data_final),
		# O Bloco E entra sempre: é o único que não admite ser declarado vazio, e sem ele
		# nenhum EFD é aceito.
		"E": bloco_e_do_periodo(company, data_inicial, data_final),
		"H": bloco_h_do_periodo(company, data_final),
		"K": bloco_k_do_periodo(company, data_inicial, data_final),
	}

	linhas = montar_arquivo_efd(blocos)
	texto = serializar_arquivo_efd(linhas)

	registro = frappe.get_doc(
		{
			"doctype": "Arquivo SPED",
			"company": company,
			"tipo": TIPO_EFD_ICMS_IPI,
			"finalidade": FINALIDADE_ORIGINAL,
			"data_inicial": data_inicial,
			"data_final": data_final,
			"situacao": "Gerado",
			"gerado_em": frappe.utils.now(),
		}
	)
	registro.registrar_conteudo(texto)
	registro.insert(ignore_permissions=True)

	return {
		"registro": registro.name,
		"linhas": len(linhas),
		"blocos_ausentes": list(BLOCOS_SEM_LEITURA_DO_SITE),
		"aviso": _(
			"Arquivo parcial: os blocos {0} ainda não são lidos do site, e o Bloco 0 sai sem "
			"os cadastros de participantes, unidades e itens. Serve para conferir a montagem "
			"no PVA, não para transmitir."
		).format(", ".join(BLOCOS_SEM_LEITURA_DO_SITE)),
	}
