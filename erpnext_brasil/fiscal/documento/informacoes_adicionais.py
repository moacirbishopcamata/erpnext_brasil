# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Grupo `infAdic` — informações complementares e observações.

Diferença entre `infCpl` e `obsCont`/`obsFisco`
------------------------------------------------
`infCpl` é texto livre único, o que aparece no campo "Informações Complementares" do
DANFE — mensagem promocional, condição de pagamento por extenso, referência a contrato.

`obsCont` e `obsFisco` são **estruturados**: cada observação tem um identificador
(`@xCampo`) e um texto (`xTexto`). Existem para sistemas trocarem dado semiestruturado
sem inventar convenção própria dentro de `infCpl` — um contador que precisa localizar
"a observação de desconto" faz isso pelo `xCampo`, não fazendo parsing de texto livre.

Funções puras: nenhuma dependência do Frappe.
"""

__all__ = ["montar_infadic"]


def _observacoes(pares: dict[str, str] | None) -> list[dict] | None:
	if not pares:
		return None

	return [{"@xCampo": campo, "xTexto": texto} for campo, texto in pares.items()]


def montar_infadic(
	informacoes_complementares: str = "",
	informacoes_ao_fisco: str = "",
	observacoes_contribuinte: dict[str, str] | None = None,
	observacoes_fisco: dict[str, str] | None = None,
) -> dict | None:
	"""Monta `infAdic`. Devolve `None` quando não há nada a informar — o grupo inteiro
	é opcional, e um `infAdic` vazio não deveria existir no documento."""
	# .strip() e não checagem direta de truthy: string só com espaço é truthy em Python,
	# e a mesma disciplina de "vazio é vazio" já vale no resto do app (`_obrigatorio` em
	# nfe.py, por exemplo). Sem isso, `informacoes_ao_fisco="  "` produziria uma tag
	# infAdFisco tecnicamente presente mas sem conteúdo útil.
	informacoes_ao_fisco = (informacoes_ao_fisco or "").strip()
	informacoes_complementares = (informacoes_complementares or "").strip()

	grupo: dict = {}

	if informacoes_ao_fisco:
		grupo["infAdFisco"] = informacoes_ao_fisco

	if informacoes_complementares:
		grupo["infCpl"] = informacoes_complementares

	obs_cont = _observacoes(observacoes_contribuinte)

	if obs_cont:
		grupo["obsCont"] = obs_cont

	obs_fisco = _observacoes(observacoes_fisco)

	if obs_fisco:
		grupo["obsFisco"] = obs_fisco

	return {"infAdic": grupo} if grupo else None
