# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Cherry — os perfis de banco de um bench: a costura entre a regra pura e os arquivos do bench.

A regra (nome único, exatamente um padrão, perfil em uso protegido, nenhuma senha) mora em
`erpnext_brasil/bancos/`, pura e testada sem bench. Este módulo só liga essa regra ao que o Cherry conhece:

- onde os perfis ficam (`sites/cherry/perfis-de-banco.json`, no formato escolhido) — o Cherry é o **único
  escritor**; o Soda e o Chantilly leem por `erpnext_brasil.bancos.perfis.abrir_leitor`;
- como o **padrão** chega ao `common_site_config.json` (`db_type`, `db_host`, `db_port`, `root_login`), que é onde o
  `bench new-site` o espera. **Nunca `root_password`**: a senha não vem de perfil;
- como um perfil vira o `Banco` do teste de conexão e do `bench new-site` (a senha entra só na hora, por parâmetro);
- como saber quais instâncias do Soda usam um perfil e quais estão no ar (para o aviso de alcance).

Sem tkinter e sem Frappe: testável com `unittest` puro.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from erpnext_brasil.bancos.modelo import PerfilDeBanco
from erpnext_brasil.bancos.perfis import NOME_DO_ARQUIVO
from erpnext_brasil.bancos.repositorio import PerfisDeBanco, Uso, adotar_configuracao_existente
from erpnext_brasil.bancos.uso import usos_pelas_instancias
from erpnext_brasil.persistencia import fabrica
from scripts.cherry import config as cfg
from scripts.cherry.instancias import instancias_no_ar, leitor_do_soda

__all__ = [
	"FORMATO_PADRAO",
	"abrir_perfis",
	"banco_do_perfil",
	"comando_new_site_do_perfil",
	"instancias_no_ar",
	"pasta_dos_perfis",
	"testar_perfil",
]

FORMATO_PADRAO = "json"


def pasta_dos_perfis(bench: cfg.Bench) -> Path:
	return bench.sites / "cherry"


def _usos(bench: cfg.Bench) -> Callable[[str], Sequence[Uso]]:
	def usos(nome: str) -> Sequence[Uso]:
		leitor = leitor_do_soda(bench)

		return usos_pelas_instancias(leitor)(nome) if leitor else ()

	return usos


def abrir_perfis(bench: cfg.Bench, formato: str = FORMATO_PADRAO) -> PerfisDeBanco:
	"""Os perfis do bench. Na primeira abertura de um bench que já tem banco configurado, cria o perfil padrão a
	partir do `common_site_config.json`, sem alterá-lo."""
	repositorio = fabrica.abrir(
		pasta_dos_perfis(bench) / f"{NOME_DO_ARQUIVO}{fabrica.extensao_do_formato(formato)}", formato
	)

	def publicar(perfil: PerfilDeBanco) -> None:
		cfg.atualizar_json(bench.common_config, perfil.chaves_common_config())

	perfis = PerfisDeBanco(repositorio, usos=_usos(bench), publicar_padrao=publicar)
	adotar_configuracao_existente(perfis, cfg.ler_json(bench.common_config))

	return perfis


def banco_do_perfil(perfil: PerfilDeBanco, senha: str = "") -> cfg.Banco:
	"""O `Banco` do Cherry para este perfil. A senha entra aqui, por parâmetro, e não é guardada em lugar nenhum."""
	return cfg.Banco(perfil.tipo, perfil.host, perfil.porta, perfil.usuario_root, senha)


def comando_new_site_do_perfil(
	perfil: PerfilDeBanco, site: str, senha_root: str = "", senha_admin: str = "", apps: tuple[str, ...] = ()
) -> str:
	"""O `bench new-site` com o tipo, o host, a porta e o usuário do perfil. As senhas, se vierem, vão só no comando."""
	return cfg.comando_new_site(banco_do_perfil(perfil, senha_root), site, senha_admin, apps)


def testar_perfil(
	perfis: PerfisDeBanco,
	nome: str,
	senha: str,
	bench: cfg.Bench | None = None,
	executar=subprocess.run,
) -> cfg.ResultadoConexao:
	"""Testa a conexão do perfil com a senha informada agora e guarda no perfil só data, nível e resultado."""
	perfil = perfis.obter(nome)

	if perfil is None:
		raise cfg.CherryInvalido(f"não existe o perfil {nome!r}")

	resultado = cfg.testar_conexao(banco_do_perfil(perfil, senha), bench, executar)
	perfis.registrar_teste(perfil.nome, ok=resultado.ok, nivel=resultado.nivel)

	return resultado
