# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Onde o registro mora e em que formato: `sites/soda/registro.json|sqlite` e o marcador `formato`.

O formato (JSON ou SQLite) é **configuração**, não código (mudança `persistencia-sqlite-opcional`). Um arquivo
pequeno, `formato`, guarda a escolha; o leitor do contrato o consulta para saber o que abrir. Sem o marcador, o
formato é deduzido do arquivo que existe; se existirem **os dois** sem marcador, a ferramenta **recusa** em vez de
adivinhar (fail-closed): ler o errado apresentaria instâncias desatualizadas como verdade.

A troca de formato migra tudo, confere por releitura, grava o marcador **depois** de conferir e deixa o arquivo
anterior ao lado até o usuário confirmar o descarte.
"""

from pathlib import Path

from erpnext_brasil.persistencia import fabrica
from erpnext_brasil.persistencia.arquivos import escrever_atomico
from erpnext_brasil.persistencia.documentos import PersistenciaInvalida, RepositorioDeDocumentos
from erpnext_brasil.soda.registro import Registro

__all__ = [
	"FORMATO_PADRAO",
	"ConfiguracaoAmbigua",
	"abrir_registro",
	"abrir_repositorio",
	"caminho_do_registro",
	"gravar_formato",
	"ler_formato",
	"pasta_do_soda",
	"trocar_formato_do_registro",
]

FORMATO_PADRAO = "json"
NOME_DO_REGISTRO = "registro"
NOME_DO_MARCADOR = "formato"


class ConfiguracaoAmbigua(RuntimeError):
	"""Existem os dois arquivos de registro e nenhum marcador diz qual vale."""


def pasta_do_soda(sites: Path) -> Path:
	return Path(sites) / "soda"


def caminho_do_registro(pasta: Path, formato: str) -> Path:
	return Path(pasta) / f"{NOME_DO_REGISTRO}{fabrica.extensao_do_formato(formato)}"


def ler_formato(pasta: Path) -> str:
	"""O formato em uso: o marcador, ou o arquivo que existe, ou o padrão."""
	pasta = Path(pasta)
	marcador = pasta / NOME_DO_MARCADOR

	if marcador.is_file():
		escolhido = marcador.read_text(encoding="utf-8").strip()
		fabrica.extensao_do_formato(escolhido)  # recusa formato desconhecido

		return escolhido

	existentes = [f for f in fabrica.FORMATOS if caminho_do_registro(pasta, f).exists()]

	if len(existentes) > 1:
		raise ConfiguracaoAmbigua(
			f"há {' e '.join(caminho_do_registro(pasta, f).name for f in existentes)} em {pasta} e nenhum marcador "
			f"`{NOME_DO_MARCADOR}` diz qual vale; escolha um e grave o marcador"
		)

	return existentes[0] if existentes else FORMATO_PADRAO


def gravar_formato(pasta: Path, formato: str) -> None:
	fabrica.extensao_do_formato(formato)
	escrever_atomico(Path(pasta) / NOME_DO_MARCADOR, formato + "\n")


def abrir_repositorio(pasta: Path, *, somente_leitura: bool = False) -> RepositorioDeDocumentos:
	"""O repositório do registro no formato em uso. `somente_leitura` só tem efeito no SQLite (o JSON é lido sem trava)."""
	formato = ler_formato(pasta)
	opcoes = {"somente_leitura": True} if somente_leitura and formato == "sqlite" else {}

	return fabrica.abrir(caminho_do_registro(pasta, formato), formato, **opcoes)


def abrir_registro(pasta: Path, **opcoes) -> Registro:
	return Registro(abrir_repositorio(pasta), **opcoes)


def trocar_formato_do_registro(pasta: Path, novo: str) -> fabrica.ResultadoDaTroca:
	"""Migra o registro para outro formato. O marcador só muda depois de a releitura conferir."""
	pasta = Path(pasta)
	atual = ler_formato(pasta)
	fabrica.extensao_do_formato(novo)

	if atual == novo:
		raise PersistenciaInvalida(f"o registro já está em {novo}")

	resultado = fabrica.trocar_formato(
		caminho_do_registro(pasta, atual), atual, caminho_do_registro(pasta, novo), novo
	)
	gravar_formato(pasta, novo)

	return resultado
