# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""O leitor dos perfis de banco: o que o Soda, o Chantilly e qualquer outra ferramenta podem ler do Cherry.

O **Cherry é o único escritor** dos perfis. Este leitor não tem operação de escrita (nem `gravar`, nem
`transacao`) e não toma a trava de escrita: ler durante uma gravação devolve o último estado consistente. Tolera
campo novo e esquema mais novo (`mais_nova`), pula perfil malformado com aviso e devolve leitura vazia marcada como
ilegível quando o arquivo não abre. Quem consome recebe só nome, tipo, host, porta, usuário administrador,
indicação de padrão e o resultado do último teste (sem senha, que não existe no registro).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from erpnext_brasil.bancos.modelo import PerfilDeBanco, PerfilInvalido
from erpnext_brasil.bancos.repositorio import CHAVE_META, COLECAO_META, COLECAO_PERFIS, ESQUEMA
from erpnext_brasil.persistencia import fabrica
from erpnext_brasil.persistencia.documentos import ArquivoIlegivel, EsquemaMaisNovo, RepositorioDeDocumentos

__all__ = ["LeitorDePerfis", "LeituraDePerfis", "PerfilLido", "abrir_leitor"]


@dataclass(frozen=True)
class PerfilLido:
	nome: str
	tipo: str
	host: str
	porta: int
	usuario_root: str
	padrao: bool
	ultimo_teste_em: str | None = None
	ultimo_teste_nivel: str | None = None
	ultimo_teste_ok: bool | None = None


@dataclass(frozen=True)
class LeituraDePerfis:
	perfis: tuple[PerfilLido, ...] = ()
	versao_do_esquema: int = ESQUEMA
	mais_nova: bool = False
	ilegivel: bool = False
	avisos: tuple[str, ...] = ()

	@property
	def padrao(self) -> PerfilLido | None:
		return next((p for p in self.perfis if p.padrao), None)


def _perfil_lido(perfil: PerfilDeBanco) -> PerfilLido:
	teste = perfil.ultimo_teste

	return PerfilLido(
		nome=perfil.nome,
		tipo=perfil.tipo,
		host=perfil.host,
		porta=perfil.porta,
		usuario_root=perfil.usuario_root,
		padrao=perfil.padrao,
		ultimo_teste_em=teste.quando if teste else None,
		ultimo_teste_nivel=teste.nivel if teste else None,
		ultimo_teste_ok=teste.ok if teste else None,
	)


class LeitorDePerfis:
	"""Somente leitura: não existe aqui nenhum método de escrita."""

	def __init__(self, repositorio: RepositorioDeDocumentos):
		self._repo = repositorio

	def ler(self) -> LeituraDePerfis:
		avisos: list[str] = []

		try:
			meta = self._repo.obter(COLECAO_META, CHAVE_META)
			documentos = self._repo.listar(COLECAO_PERFIS)
		except (ArquivoIlegivel, EsquemaMaisNovo) as erro:
			return LeituraDePerfis(ilegivel=True, avisos=(str(erro),))

		versao = meta.get("versao_esquema", ESQUEMA) if isinstance(meta, dict) else ESQUEMA

		if not isinstance(versao, int) or isinstance(versao, bool):
			avisos.append("a versão do esquema dos perfis é ilegível; tratada como a conhecida")
			versao = ESQUEMA

		mais_nova = versao > ESQUEMA

		if mais_nova:
			avisos.append(
				f"os perfis estão na versão de esquema {versao} e este leitor conhece até {ESQUEMA}; "
				"mostrando o que é identificável, sem gravar nada"
			)

		perfis: list[PerfilLido] = []

		for chave, documento in documentos:
			try:
				perfis.append(_perfil_lido(PerfilDeBanco.de_documento(documento)))
			except PerfilInvalido as erro:
				avisos.append(f"o perfil {chave} está malformado ({erro}); ignorado")

		return LeituraDePerfis(
			perfis=tuple(sorted(perfis, key=lambda p: p.nome.casefold())),
			versao_do_esquema=versao,
			mais_nova=mais_nova,
			avisos=tuple(avisos),
		)

	def por_nome(self, nome: Any) -> PerfilLido | None:
		if not isinstance(nome, str):
			return None

		return next((p for p in self.ler().perfis if p.nome.casefold() == nome.casefold()), None)

	def padrao(self) -> PerfilLido | None:
		return self.ler().padrao


NOME_DO_ARQUIVO = "perfis-de-banco"


def abrir_leitor(pasta: Path, formato: str) -> LeitorDePerfis:
	"""O leitor dos perfis guardados na pasta, no formato dado, aberto somente para leitura."""
	opcoes = {"somente_leitura": True} if formato == "sqlite" else {}

	return LeitorDePerfis(
		fabrica.abrir(
			Path(pasta) / f"{NOME_DO_ARQUIVO}{fabrica.extensao_do_formato(formato)}", formato, **opcoes
		)
	)
