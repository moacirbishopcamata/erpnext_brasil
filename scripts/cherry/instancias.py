# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Cherry — as instâncias do Soda vistas pelo Cherry: identidade, alcance da configuração comum e portas.

O Cherry **só lê** o registro do Soda, pelo leitor do contrato de identidade (`erpnext_brasil.soda.leitura`): sem
método de escrita, sem trava, tolerante a campo novo e a registro ilegível. Sem registro (o Soda nunca foi usado
neste bench), tudo aqui degrada para "nenhuma instância identificada" e o Cherry funciona como antes.

Garantias deste módulo (mudança `cherry-instancias-por-uuid`):

- **A identidade é do Soda.** `gravar_no_site` recusa as chaves `soda_instance_id` e `soda_descritivo` e, depois de
  gravar, confere que elas continuam exatamente iguais (pós-condição), em vez de confiar que ninguém as tocou.
- **A configuração comum vale para todas as instâncias.** `instancias_no_ar` diz quais são, para o aviso.
- **As portas das instâncias não são do Cherry.** `conflito_de_porta` recusa a porta de uma instância e qualquer
  porta da faixa que o Soda aloca, dizendo quem a usa.

Sem tkinter e sem Frappe: testável com `unittest` puro.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from erpnext_brasil.bancos.repositorio import Uso
from erpnext_brasil.persistencia.documentos import ArquivoIlegivel, EsquemaMaisNovo
from erpnext_brasil.soda import configuracao as soda_configuracao
from erpnext_brasil.soda.leitura import CHAVES_PROTEGIDAS, InstanciaLida, LeitorDeInstancias
from erpnext_brasil.soda.portas import FAIXA_PADRAO
from scripts.cherry import config as cfg

__all__ = [
	"ESTADOS_NO_AR",
	"InstanciaDoSite",
	"conflito_de_porta",
	"gravar_no_site",
	"instancias_do_bench",
	"instancias_no_ar",
	"leitor_do_soda",
	"porta_do_valor",
	"rotulo_da_instancia",
	"rotulo_do_estado",
	"tem_registro_do_soda",
]

ESTADOS_NO_AR = ("no_ar", "subindo")
ROTULO_DO_ESTADO = {
	"criando": "criando",
	"parada": "parada",
	"subindo": "subindo",
	"no_ar": "no ar",
	"caiu": "caiu",
	"falhou_ao_subir": "falhou ao subir",
	"criacao_interrompida": "criação interrompida",
}


def rotulo_do_estado(estado: str) -> str:
	"""O estado em português para a tela; um estado de versão futura aparece como veio, sem quebrar."""
	return ROTULO_DO_ESTADO.get(estado, estado)


def leitor_do_soda(bench: cfg.Bench) -> LeitorDeInstancias | None:
	"""O leitor do registro do Soda, ou `None` quando o Soda nunca foi usado neste bench (estado normal)."""
	pasta = soda_configuracao.pasta_do_soda(bench.sites)

	try:
		formato = soda_configuracao.ler_formato(pasta)

		if not soda_configuracao.caminho_do_registro(pasta, formato).exists():
			return None

		return LeitorDeInstancias.abrir(pasta)
	except (soda_configuracao.ConfiguracaoAmbigua, ArquivoIlegivel, EsquemaMaisNovo, ValueError):
		return None


def tem_registro_do_soda(bench: cfg.Bench) -> bool:
	return leitor_do_soda(bench) is not None


def _instancias_lidas(bench: cfg.Bench) -> list[InstanciaLida]:
	leitor = leitor_do_soda(bench)

	return list(leitor.ler().instancias) if leitor else []


@dataclass(frozen=True)
class InstanciaDoSite:
	"""Um site do bench com a identidade que o Soda deu a ele, quando deu."""

	site: str
	instancia: InstanciaLida | None = None

	@property
	def identificada(self) -> bool:
		return self.instancia is not None


def instancias_do_bench(bench: cfg.Bench) -> list[InstanciaDoSite]:
	"""Cada site do bench, com a instância do Soda que o tem como host (se houver)."""
	por_host = {i.host: i for i in _instancias_lidas(bench)}

	return [InstanciaDoSite(site, por_host.get(site)) for site in bench.nomes_de_sites()]


def rotulo_da_instancia(item: InstanciaDoSite) -> str:
	"""O que a lista mostra: descritivo, UUID abreviado, porta e estado, com o nome do site em segundo plano."""
	if item.instancia is None:
		return f"{item.site}  (sem UUID)"

	i = item.instancia

	return f"{i.descritivo} · {i.abreviado} · porta {i.porta} · {rotulo_do_estado(i.estado)}   [{item.site}]"


def instancias_no_ar(bench: cfg.Bench) -> list[Uso]:
	"""As instâncias no ar ou subindo: quem vê o aviso ao gravar a configuração comum do bench."""
	return [Uso(i.descritivo, i.abreviado) for i in _instancias_lidas(bench) if i.estado in ESTADOS_NO_AR]


def porta_do_valor(valor: object) -> int | None:
	"""A porta de um valor de configuração: um número, ou a porta de uma URL (`redis://host:porta`)."""
	if isinstance(valor, int) and not isinstance(valor, bool):
		return valor

	if not isinstance(valor, str) or not valor.strip():
		return None

	texto = valor.strip()

	if texto.isdigit():
		return int(texto)

	try:
		return urlparse(texto).port
	except ValueError:
		return None


def conflito_de_porta(bench: cfg.Bench, valor: object) -> str | None:
	"""Por que a porta não pode ser usada pela configuração comum, ou `None` se pode.

	Recusa a porta **alocada a uma instância** (dizendo qual) e qualquer porta da **faixa do Soda**, que o Soda
	reserva para as instâncias que ainda vai criar.
	"""
	porta = porta_do_valor(valor)

	if porta is None:
		return None

	for instancia in _instancias_lidas(bench):
		if instancia.porta == porta:
			return f"a porta {porta} é da instância {instancia.descritivo} ({instancia.abreviado})"

	if porta in FAIXA_PADRAO and tem_registro_do_soda(bench):
		return (
			f"a porta {porta} está na faixa {FAIXA_PADRAO.inicio} a {FAIXA_PADRAO.fim}, reservada às instâncias "
			"do Soda; use uma porta fora dela"
		)

	return None


def gravar_no_site(bench: cfg.Bench, site: str, alteracoes: dict) -> dict:
	"""Grava no `site_config.json` do site **sem poder tocar na identidade** da instância.

	- Pré-condição: nenhuma chave de `alteracoes` é `soda_instance_id` ou `soda_descritivo`.
	- Pós-condição: essas duas chaves, depois da gravação, valem exatamente o que valiam antes (inclusive ausentes).
	"""
	caminho = bench.site_config(site)
	protegidas = sorted(set(alteracoes) & set(CHAVES_PROTEGIDAS))

	if protegidas:
		raise cfg.CherryInvalido(
			f"{', '.join(protegidas)} {'é' if len(protegidas) == 1 else 'são'} da identidade da instância e só o "
			"Soda as altera"
		)

	antes = {chave: cfg.ler_json(caminho).get(chave) for chave in CHAVES_PROTEGIDAS}
	dados = cfg.atualizar_json(caminho, alteracoes)
	depois = {chave: cfg.ler_json(caminho).get(chave) for chave in CHAVES_PROTEGIDAS}

	if antes != depois:  # nunca deve acontecer: falha alto em vez de seguir com a identidade alterada
		raise cfg.CherryInvalido(f"a identidade da instância mudou durante a gravação em {site}")

	return dados
