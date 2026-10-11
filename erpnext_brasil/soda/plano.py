# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Executor de planos: passos com desfazer, tudo ou nada.

Uma operação do Soda (criar instância, remover, trocar de formato) é uma lista de **passos**; cada passo sabe
executar e, quando faz sentido, desfazer. O executor roda os passos em ordem e, se um falhar, **desfaz só o que
os passos já executados fizeram**, em ordem inversa (spec `resiliencia-e-seguranca`: falha no terceiro de cinco
passos deixa o estado final igual ao inicial).

Contratos
---------
- O `desfazer` de um passo deve ser **idempotente e tolerar efeito parcial ou ausente**: ele também roda para o
  passo que falhou, porque este pode ter feito parte do trabalho antes de levantar a exceção.
- Falha ao desfazer **não interrompe** o desfazer dos demais: é coletada e devolvida (nada se perde em silêncio).
- A mensagem de erro devolvida é a da exceção, **sem pilha**; quem a exibe passa pelo redator de segredos.
- `KeyboardInterrupt` e saída do programa também desfazem e **propagam**: cancelar não deixa lixo.
- Com um `Diario`, a intenção é registrada antes do primeiro passo e o desfecho depois do último.

Esta camada é pura: executar de verdade (chamar o `bench`, apagar um site) é dos passos que a camada fina fornece.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from erpnext_brasil.soda.diario import Diario, EstadoDaOperacao

__all__ = ["Passo", "ResultadoDoPlano", "executar_plano"]


@dataclass(frozen=True)
class Passo:
	nome: str
	executar: Callable[[], None]
	desfazer: Callable[[], None] | None = None


@dataclass(frozen=True)
class ResultadoDoPlano:
	concluidos: tuple[str, ...]
	falhou_em: str | None = None
	erro: str | None = None
	desfeitos: tuple[str, ...] = ()
	falhas_ao_desfazer: tuple[tuple[str, str], ...] = ()

	@property
	def ok(self) -> bool:
		return self.falhou_em is None


def _desfazer(executados: Sequence[Passo]) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
	desfeitos: list[str] = []
	falhas: list[tuple[str, str]] = []

	for passo in reversed(executados):
		if passo.desfazer is None:
			continue

		try:
			passo.desfazer()
		except Exception as erro:  # a falha de um desfazer não impede os outros: é coletada
			falhas.append((passo.nome, f"{type(erro).__name__}: {erro}"))
		else:
			desfeitos.append(passo.nome)

	return tuple(desfeitos), tuple(falhas)


def executar_plano(
	passos: Sequence[Passo],
	*,
	diario: Diario | None = None,
	tipo: str = "operacao",
	instancia: str = "",
) -> ResultadoDoPlano:
	"""Executa os passos em ordem; na falha, desfaz o feito em ordem inversa."""
	operacao = diario.abrir(tipo, instancia, tuple(p.nome for p in passos)) if diario else None
	concluidos: list[Passo] = []
	em_execucao: Passo | None = None

	try:
		for passo in passos:
			em_execucao = passo

			try:
				passo.executar()
			except Exception as erro:
				a_desfazer = [*concluidos, passo]
				desfeitos, falhas = _desfazer(a_desfazer)
				resultado = ResultadoDoPlano(
					concluidos=tuple(p.nome for p in concluidos),
					falhou_em=passo.nome,
					erro=f"{type(erro).__name__}: {erro}",
					desfeitos=desfeitos,
					falhas_ao_desfazer=falhas,
				)

				if diario and operacao:
					diario.encerrar(operacao.id, EstadoDaOperacao.FALHOU, f"falhou em {passo.nome}")

				return resultado

			concluidos.append(passo)
			em_execucao = None

			if diario and operacao:
				diario.passo_concluido(operacao.id, passo.nome)
	except BaseException:
		# Cancelamento (Ctrl+C, saída): desfaz o feito, inclusive o passo que estava rodando, e deixa a exceção subir.
		_desfazer([*concluidos, em_execucao] if em_execucao else concluidos)

		if diario and operacao:
			diario.encerrar(operacao.id, EstadoDaOperacao.FALHOU, "cancelada")

		raise

	if diario and operacao:
		diario.encerrar(operacao.id, EstadoDaOperacao.CONCLUIDA)

	return ResultadoDoPlano(concluidos=tuple(p.nome for p in concluidos))
