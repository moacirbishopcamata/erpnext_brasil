# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""O registro das instâncias: a regra de identidade e de portas sobre a porta de persistência.

O `Registro` não sabe se o armazenamento é JSON, SQLite ou memória (mudança `persistencia-sqlite-opcional`).
Toda operação que lê para decidir e depois grava acontece **dentro de uma transação**, que é a trava entre
processos: dois Sodas criando instâncias ao mesmo tempo não alocam a mesma porta nem o mesmo UUID.

Contratos
---------
- **Pré-condição:** descritivo válido e único, tipo de banco conhecido, aplicativos dentro do permitido, porta
  alocável. Violação levanta exceção própria **antes** de gravar.
- **Pós-condição:** o que `criar` devolve é o que está gravado; releitura por outra instância do registro vê o
  mesmo (teste na costura).
- **Invariante:** UUIDs únicos entre instâncias **e** aposentadas; descritivos únicos sem caixa nem acento; portas
  únicas; host único. Um registro de esquema mais novo que o conhecido **não é gravado** (`RegistroMaisNovo`).
"""

import uuid
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone

from erpnext_brasil.persistencia.documentos import RepositorioDeDocumentos, validar_nome
from erpnext_brasil.sistema.rede import porta_livre
from erpnext_brasil.soda import identidade as ident
from erpnext_brasil.soda import portas as pt
from erpnext_brasil.soda.modelo import (
	APLICATIVOS_OBRIGATORIOS,
	APLICATIVOS_OPCIONAIS,
	ESTADOS_QUE_IMPEDEM_REMOVER,
	TIPOS_DE_BANCO,
	TRANSICOES,
	TRANSICOES_DA_CONCILIACAO,
	Aposentada,
	DocumentoInvalido,
	Estado,
	Instancia,
)

__all__ = [
	"COLECAO_APOSENTADAS",
	"COLECAO_INSTANCIAS",
	"ESQUEMA",
	"DescritivoRepetido",
	"InstanciaInexistente",
	"LimiteDeInstancias",
	"OperacaoNaoPermitida",
	"Registro",
	"RegistroMaisNovo",
	"TransicaoInvalida",
]

ESQUEMA = 1
COLECAO_INSTANCIAS = "instancias"
COLECAO_APOSENTADAS = "aposentadas"
COLECAO_META = "meta"
CHAVE_META = "esquema"


class DescritivoRepetido(ValueError):
	def __init__(self, existente: Instancia):
		super().__init__(
			f'já existe a instância "{existente.descritivo}" ({existente.abreviado}) com esse descritivo '
			"(a comparação ignora maiúsculas e acentos)"
		)
		self.existente = existente


class InstanciaInexistente(LookupError):
	pass


class TransicaoInvalida(ValueError):
	pass


class OperacaoNaoPermitida(ValueError):
	pass


class RegistroMaisNovo(RuntimeError):
	"""O registro foi gravado por uma versão mais nova do Soda; esta não grava nele."""


class LimiteDeInstancias(RuntimeError):
	pass


def _agora_utc() -> datetime:
	return datetime.now(timezone.utc)


class _Indisponiveis:
	"""UUIDs que não podem ser sorteados: os de instâncias, os de aposentadas e os que dariam um host repetido."""

	def __init__(self, uuids: set[str], hosts: set[str], descritivo: str):
		self._uuids = uuids
		self._hosts = hosts
		self._descritivo = descritivo

	def __contains__(self, candidato: object) -> bool:
		return candidato in self._uuids or ident.nome_do_host(self._descritivo, str(candidato)) in self._hosts


class Registro:
	def __init__(
		self,
		repositorio: RepositorioDeDocumentos,
		*,
		faixa: pt.FaixaDePortas = pt.FAIXA_PADRAO,
		livre: Callable[[int], bool] = porta_livre,
		quem_ocupa: Callable[[int], str | None] = lambda porta: None,
		agora: Callable[[], datetime] = _agora_utc,
		gerar_uuid: Callable[[], uuid.UUID] = uuid.uuid4,
	):
		self._repo = repositorio
		self._faixa = faixa
		self._livre = livre
		self._quem_ocupa = quem_ocupa
		self._agora = agora
		self._gerar_uuid = gerar_uuid

	# ------------------------------------------------------------------ leitura (reconstituição fresca)

	def _instancias(self) -> list[Instancia]:
		return [Instancia.de_documento(doc) for _, doc in self._repo.listar(COLECAO_INSTANCIAS)]

	def _aposentadas(self) -> list[Aposentada]:
		return [Aposentada.de_documento(doc) for _, doc in self._repo.listar(COLECAO_APOSENTADAS)]

	def listar(self) -> list[Instancia]:
		return sorted(self._instancias(), key=lambda i: (i.chave, i.uuid))

	def aposentadas(self) -> list[Aposentada]:
		return sorted(self._aposentadas(), key=lambda a: a.uuid)

	def obter(self, identificador: str) -> Instancia | None:
		documento = self._repo.obter(COLECAO_INSTANCIAS, ident.normalizar_uuid(identificador))

		return Instancia.de_documento(documento) if documento is not None else None

	def por_descritivo(self, descritivo: str) -> Instancia | None:
		chave = ident.chave_de_unicidade(descritivo)

		return next((i for i in self._instancias() if i.chave == chave), None)

	def portas_alocadas(self) -> dict[int, str]:
		return {i.porta: i.descritivo for i in self._instancias()}

	def versao_do_esquema(self) -> int:
		meta = self._repo.obter(COLECAO_META, CHAVE_META)

		return meta["versao_esquema"] if meta else ESQUEMA

	def colisoes_de_uuid(self) -> int:
		meta = self._repo.obter(COLECAO_META, CHAVE_META)

		return int(meta.get("colisoes_de_uuid", 0)) if meta else 0

	# ------------------------------------------------------------------ escrita

	def _garantir_esquema(self, *, colisoes: int = 0) -> None:
		"""Recusa gravar num registro mais novo; grava a versão do esquema (e a contagem de colisões) na primeira vez."""
		meta = self._repo.obter(COLECAO_META, CHAVE_META)

		if meta and meta.get("versao_esquema", ESQUEMA) > ESQUEMA:
			raise RegistroMaisNovo(
				f"o registro está na versão de esquema {meta['versao_esquema']}; esta versão do Soda conhece até {ESQUEMA}"
			)

		total = (meta or {}).get("colisoes_de_uuid", 0) + colisoes

		if meta is None or colisoes:
			self._repo.gravar(
				COLECAO_META, CHAVE_META, {"versao_esquema": ESQUEMA, "colisoes_de_uuid": total}
			)

	def _exigir(self, identificador: str) -> Instancia:
		instancia = self.obter(identificador)

		if instancia is None:
			raise InstanciaInexistente(f"não existe instância com o UUID {identificador}")

		return instancia

	def _gravar(self, instancia: Instancia) -> None:
		self._repo.gravar(COLECAO_INSTANCIAS, instancia.uuid, instancia.para_documento())

	def criar(
		self,
		descritivo: str,
		*,
		perfil_de_banco: str,
		tipo_de_banco: str,
		aplicativos_opcionais: tuple[str, ...] = (),
		porta: int | None = None,
		expoe_na_rede: bool = False,
	) -> Instancia:
		"""Registra uma instância nova no estado "criando". O ambiente em si é criado depois (plano de criação)."""
		descritivo = ident.validar_descritivo(descritivo)
		validar_nome(perfil_de_banco, "o perfil de banco")

		if tipo_de_banco not in TIPOS_DE_BANCO:
			raise ValueError(
				f"tipo de banco desconhecido: {tipo_de_banco!r} (use {' ou '.join(TIPOS_DE_BANCO)})"
			)

		desconhecidos = [a for a in aplicativos_opcionais if a not in APLICATIVOS_OPCIONAIS]

		if desconhecidos:
			raise ValueError(
				f"aplicativo opcional desconhecido: {desconhecidos} (use {', '.join(APLICATIVOS_OPCIONAIS)})"
			)

		aplicativos = APLICATIVOS_OBRIGATORIOS + tuple(dict.fromkeys(aplicativos_opcionais))

		with self._repo.transacao():
			self._garantir_esquema()
			existentes = self._instancias()
			chave = ident.chave_de_unicidade(descritivo)

			for outra in existentes:
				if outra.chave == chave:
					raise DescritivoRepetido(outra)

			sorteio = ident.sortear_uuid(
				_Indisponiveis(
					{i.uuid for i in existentes} | {a.uuid for a in self._aposentadas()},
					{i.host for i in existentes},
					descritivo,
				),
				gerar=self._gerar_uuid,
			)
			alocada = pt.alocar(
				self._faixa,
				{i.porta: i.descritivo for i in existentes},
				self._livre,
				escolhida=porta,
				quem_ocupa=self._quem_ocupa,
			)
			instancia = Instancia(
				uuid=sorteio.uuid,
				descritivo=descritivo,
				host=ident.nome_do_host(descritivo, sorteio.uuid),
				porta=alocada,
				estado=Estado.CRIANDO,
				perfil_de_banco=perfil_de_banco,
				tipo_de_banco=tipo_de_banco,
				aplicativos=aplicativos,
				criada_em=self._agora().isoformat(),
				expoe_na_rede=expoe_na_rede,
			)
			self._gravar(instancia)

			if sorteio.colisoes:
				self._garantir_esquema(colisoes=sorteio.colisoes)

		return instancia

	def renomear(self, identificador: str, novo_descritivo: str) -> Instancia:
		"""Altera só o descritivo: UUID, host e porta ficam."""
		novo = ident.validar_descritivo(novo_descritivo)

		with self._repo.transacao():
			self._garantir_esquema()
			atual = self._exigir(identificador)
			chave = ident.chave_de_unicidade(novo)

			for outra in self._instancias():
				if outra.uuid != atual.uuid and outra.chave == chave:
					raise DescritivoRepetido(outra)

			renomeada = replace(atual, descritivo=novo)
			self._gravar(renomeada)

		return renomeada

	def mudar_estado(self, identificador: str, novo: Estado, *, constatado: bool = False) -> Instancia:
		"""Muda o estado conforme as transições. `constatado=True` aplica o que a conciliação viu na realidade.

		Repetir o mesmo estado é um não-fazer (operação idempotente).
		"""
		with self._repo.transacao():
			self._garantir_esquema()
			atual = self._exigir(identificador)

			if novo == atual.estado:
				return atual

			permitidas = TRANSICOES_DA_CONCILIACAO if constatado else TRANSICOES

			if novo not in permitidas[atual.estado]:
				raise TransicaoInvalida(
					f'a instância "{atual.descritivo}" está {atual.estado.value} e não pode ir para {novo.value}'
				)

			mudada = replace(atual, estado=novo)
			self._gravar(mudada)

		return mudada

	def exigir_vaga_para_subir(self, limite: int) -> None:
		"""Recusa iniciar além do limite de instâncias no ar (cada uma consome memória)."""
		no_ar = sum(1 for i in self._instancias() if i.estado in (Estado.SUBINDO, Estado.NO_AR))

		if no_ar >= limite:
			raise LimiteDeInstancias(
				f"já há {no_ar} instância(s) no ar ou subindo; o limite é {limite} porque cada uma consome memória "
				"(o limite pode ser alterado)"
			)

	def aposentar(self, identificador: str) -> Aposentada:
		"""Remove a instância do registro e aposenta o UUID para sempre. Instância no ar não se remove."""
		with self._repo.transacao():
			self._garantir_esquema()
			instancia = self._exigir(identificador)

			if instancia.estado in ESTADOS_QUE_IMPEDEM_REMOVER:
				raise OperacaoNaoPermitida(
					f'a instância "{instancia.descritivo}" está {instancia.estado.value}; pare-a antes de remover'
				)

			rastro = Aposentada(instancia.uuid, instancia.descritivo, self._agora().isoformat())
			self._repo.remover(COLECAO_INSTANCIAS, instancia.uuid)
			self._repo.gravar(COLECAO_APOSENTADAS, rastro.uuid, rastro.para_documento())

		return rastro

	def descartar_criacao(self, identificador: str) -> None:
		"""Desfaz uma criação que falhou ou foi interrompida: libera porta e nome **sem** aposentar o UUID.

		O UUID de uma instância que nunca chegou a existir de fato não vira rastro.
		"""
		with self._repo.transacao():
			self._garantir_esquema()
			instancia = self._exigir(identificador)

			if instancia.estado not in (Estado.CRIANDO, Estado.CRIACAO_INTERROMPIDA):
				raise OperacaoNaoPermitida(
					f'a instância "{instancia.descritivo}" está {instancia.estado.value}; '
					"só uma criação em andamento ou interrompida se descarta"
				)

			self._repo.remover(COLECAO_INSTANCIAS, instancia.uuid)


__all__ += ["DocumentoInvalido"]
