# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Escrita atômica, trava entre processos e quarentena de arquivos.

Lições que viraram código (CH-02 da revisão do Cherry, medido): abrir o destino com `"w"` o trunca na
hora, e uma falha no meio da escrita deixava o `common_site_config.json` com 10 bytes e JSON inválido.
Aqui o texto vai para um arquivo temporário **na mesma pasta** e só então troca o original com
`os.replace`; se qualquer passo falhar, o original fica como estava e o temporário é apagado.

Sempre `\\n`, nunca `\\r\\n`: quem lê o arquivo pode ser um bench Linux.
"""

import os
import shutil
import tempfile
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from erpnext_brasil.persistencia.documentos import TravaOcupada

__all__ = ["Trava", "escrever_atomico", "quarentena"]


def _trocar(origem: Path, destino: Path, dormir: Callable[[float], None], tentativas: int = 60) -> None:
	"""`os.replace` com nova tentativa: no Windows ele falha com `PermissionError` enquanto outro processo
	está lendo o destino (a leitura abre o arquivo sem permitir a troca). Medido pela suíte de concorrência
	(quatro fios gravando e lendo o mesmo arquivo perdiam gravações). Em Linux a primeira tentativa basta."""
	for tentativa in range(tentativas):
		try:
			os.replace(origem, destino)
			return
		except PermissionError:
			if tentativa == tentativas - 1:
				raise

			dormir(0.01)


def escrever_atomico(caminho: Path, texto: str, *, dormir: Callable[[float], None] = time.sleep) -> None:
	caminho.parent.mkdir(parents=True, exist_ok=True)
	descritor, nome_temporario = tempfile.mkstemp(
		dir=caminho.parent, prefix=f".{caminho.name}.", suffix=".tmp"
	)
	temporario = Path(nome_temporario)

	try:
		with os.fdopen(descritor, "w", encoding="utf-8", newline="\n") as arquivo:
			arquivo.write(texto)
			arquivo.flush()
			os.fsync(arquivo.fileno())

		if caminho.exists():
			shutil.copymode(caminho, temporario)

		_trocar(temporario, caminho, dormir)
	except BaseException:
		temporario.unlink(missing_ok=True)
		raise


class Trava:
	"""Trava entre processos por arquivo: criar com `O_EXCL` é atômico no sistema de arquivos.

	Uma trava mais velha que `obsoleta_apos` segundos é de um processo que morreu e é desfeita. O relógio
	e a espera são injetáveis, para o teste não dormir de verdade.
	"""

	def __init__(
		self,
		caminho: Path,
		*,
		espera: float = 5.0,
		obsoleta_apos: float = 30.0,
		agora: Callable[[], float] = time.time,
		dormir: Callable[[float], None] = time.sleep,
	):
		self.caminho = caminho
		self.espera = espera
		self.obsoleta_apos = obsoleta_apos
		self._agora = agora
		self._dormir = dormir

	def __enter__(self):
		self.caminho.parent.mkdir(parents=True, exist_ok=True)
		limite = self._agora() + self.espera

		while True:
			try:
				descritor = os.open(self.caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
			except (FileExistsError, PermissionError):
				# No Windows, criar o arquivo enquanto outro processo o apaga falha com `PermissionError`.
				if self._obsoleta():
					self.caminho.unlink(missing_ok=True)
					continue

				if self._agora() >= limite:
					raise TravaOcupada(
						f"outro processo está gravando ({self.caminho.name}); tente de novo"
					) from None

				self._dormir(0.01)
				continue

			os.write(descritor, f"{os.getpid()}\n".encode("ascii"))
			os.close(descritor)
			return self

	def __exit__(self, *_):
		self.caminho.unlink(missing_ok=True)

	def _obsoleta(self) -> bool:
		try:
			idade = self._agora() - self.caminho.stat().st_mtime
		except FileNotFoundError:
			return False  # sumiu entre o erro e a conferência: tenta criar de novo

		return idade > self.obsoleta_apos


def quarentena(caminho: Path, *, agora: Callable[[], datetime] = datetime.now) -> Path:
	"""Move o arquivo ilegível para uma cópia de quarentena ao lado, para recomeçar sem perder o original."""
	destino = caminho.with_name(f"{caminho.name}.quarentena-{agora().strftime('%Y%m%d%H%M%S')}")
	os.replace(caminho, destino)

	return destino
