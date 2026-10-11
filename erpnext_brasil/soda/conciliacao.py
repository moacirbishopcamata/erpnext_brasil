# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Conciliação: o estado que o Soda mostra é o da realidade, e não o que o registro afirma.

O registro diz "no ar"; o processo pode ter morrido. Mostrar o registro como verdade esconderia a queda. A
conciliação compara o que o registro afirma com **fatos** observados (processo existe? porta em escuta? operação em
andamento?) e devolve o estado verdadeiro. Os fatos entram por parâmetro: esta função é pura e testável sem
processo nenhum (mudança `soda-instancias-do-erp`, spec `ciclo-de-vida`).

Fail-closed
-----------
Fato **desconhecido** (`None`) nunca vira conclusão: a conciliação mantém o estado do registro e marca o
resultado como **incerto**. Não se declara "caiu" nem "no ar" sem prova.

Processo órfão
--------------
Um processo escutando uma porta da faixa do Soda sem instância no registro é **listado e nunca encerrado** sem
pedido do usuário (`encontrar_orfaos`).
"""

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass

from erpnext_brasil.soda.modelo import Estado, Instancia
from erpnext_brasil.soda.portas import FaixaDePortas

__all__ = [
	"PRAZO_DE_SUBIDA_PADRAO",
	"Conciliacao",
	"FatosDaInstancia",
	"Orfao",
	"conciliar",
	"encontrar_orfaos",
]

PRAZO_DE_SUBIDA_PADRAO = 120.0
"""Segundos que uma instância "subindo" pode levar antes de ser dada como "falhou ao subir"."""


@dataclass(frozen=True)
class FatosDaInstancia:
	"""O que se observou. `None` significa "não se conseguiu observar", que é diferente de "não".

	`operacao_em_andamento` diz se há um processo do Soda vivo executando um plano (criação, remoção) para esta
	instância; é o que separa "criando" de "criação interrompida".
	"""

	processo_existe: bool | None = None
	porta_em_escuta: bool | None = None
	site_presente: bool | None = None
	operacao_em_andamento: bool | None = None
	segundos_desde_o_inicio: float | None = None


@dataclass(frozen=True)
class Conciliacao:
	estado: Estado
	motivo: str
	incerto: bool = False
	"""`True` quando faltou fato para concluir e o estado do registro foi mantido."""
	anomalias: tuple[str, ...] = ()
	"""Coisas estranhas que não mudam o estado (por exemplo, site ausente do bench)."""


def conciliar(
	instancia: Instancia,
	fatos: FatosDaInstancia,
	*,
	prazo_de_subida: float = PRAZO_DE_SUBIDA_PADRAO,
) -> Conciliacao:
	"""O estado verdadeiro de uma instância, dado o que se observou."""
	estado = instancia.estado
	anomalias: list[str] = []

	if fatos.site_presente is False and estado != Estado.CRIANDO:
		anomalias.append("o site da instância não está no bench")

	def incerta(motivo: str) -> Conciliacao:
		return Conciliacao(estado, motivo, incerto=True, anomalias=tuple(anomalias))

	def conclui(novo: Estado, motivo: str) -> Conciliacao:
		return Conciliacao(novo, motivo, anomalias=tuple(anomalias))

	if estado == Estado.CRIANDO:
		if fatos.operacao_em_andamento is None:
			return incerta("não foi possível saber se a criação ainda está em andamento")

		if fatos.operacao_em_andamento:
			return conclui(Estado.CRIANDO, "a criação está em andamento")

		return conclui(Estado.CRIACAO_INTERROMPIDA, "a criação não está mais em andamento e não terminou")

	if estado == Estado.CRIACAO_INTERROMPIDA:
		return conclui(estado, "a criação foi interrompida; só se desfaz")

	if fatos.processo_existe is None:
		return incerta("não foi possível observar o processo da instância")

	if estado == Estado.PARADA:
		if fatos.processo_existe and fatos.porta_em_escuta:
			return conclui(
				Estado.NO_AR, "há um processo respondendo na porta da instância, iniciado fora do Soda"
			)

		return conclui(Estado.PARADA, "nenhum processo da instância")

	if estado in (Estado.NO_AR, Estado.CAIU):
		if fatos.processo_existe:
			if fatos.porta_em_escuta is False:
				return conclui(Estado.CAIU, "o processo existe, mas a porta não está em escuta")

			if fatos.porta_em_escuta is None:
				return incerta("o processo existe, mas não foi possível observar a porta")

			return conclui(Estado.NO_AR, "o processo existe e a porta está em escuta")

		return conclui(Estado.CAIU, "o processo da instância não existe mais")

	if estado == Estado.SUBINDO:
		if not fatos.processo_existe:
			return conclui(Estado.FALHOU_AO_SUBIR, "o processo morreu antes de a instância ficar no ar")

		if fatos.porta_em_escuta:
			return conclui(Estado.NO_AR, "o servidor passou a responder")

		if fatos.segundos_desde_o_inicio is None:
			return incerta("não foi possível saber há quanto tempo a instância está subindo")

		if fatos.segundos_desde_o_inicio > prazo_de_subida:
			return conclui(Estado.FALHOU_AO_SUBIR, f"o servidor não respondeu em {prazo_de_subida:g} s")

		return conclui(Estado.SUBINDO, "ainda dentro do prazo de subida")

	# Estado.FALHOU_AO_SUBIR
	if fatos.processo_existe and fatos.porta_em_escuta:
		return conclui(Estado.NO_AR, "o servidor passou a responder depois da falha")

	return conclui(Estado.FALHOU_AO_SUBIR, "continua sem responder")


@dataclass(frozen=True)
class Orfao:
	porta: int
	pid: int | None
	descricao: str


def encontrar_orfaos(
	faixa: FaixaDePortas,
	portas_em_escuta: Mapping[int, tuple[int | None, str]],
	portas_do_registro: Collection[int],
) -> list[Orfao]:
	"""Processos escutando uma porta da faixa do Soda que nenhuma instância do registro tem.

	`portas_em_escuta` mapeia a porta a `(pid, descrição curta)`. Nada aqui encerra processo algum.
	"""
	registradas = set(portas_do_registro)
	encontrados: Iterable[tuple[int, tuple[int | None, str]]] = sorted(portas_em_escuta.items())

	return [
		Orfao(porta, pid, descricao)
		for porta, (pid, descricao) in encontrados
		if porta in faixa and porta not in registradas
	]
