# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Perguntas à rede do computador onde a ferramenta roda, só com a biblioteca padrão.

`porta_livre` é a verificação que o alocador de portas do Soda usa: **abre** a porta em vez de consultar um
registro, porque o registro só sabe das instâncias do Soda e a porta pode estar com qualquer outro programa.
Funciona igual em Windows e em Linux.

Há uma janela de corrida inevitável entre a verificação e o uso (outro programa pode abrir a porta nesse
intervalo). Ela é aceita e tratada por quem usa: o servidor que não conseguir a porta marca a instância como
"falhou ao subir" com o motivo.
"""

import socket

__all__ = ["porta_livre"]


def porta_livre(porta: int, endereco: str = "127.0.0.1") -> bool:
	"""`True` se uma conexão de escuta puder ser aberta agora nessa porta."""
	if not isinstance(porta, int) or isinstance(porta, bool) or not 1 <= porta <= 65535:
		return False

	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as teste:
		try:
			teste.bind((endereco, porta))
		except OSError:
			return False

	return True
