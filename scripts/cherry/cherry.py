# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Atalho: `python scripts/cherry/cherry.py` de qualquer diretório.

Põe a raiz do repositório no `sys.path` para que `scripts.cherry` importe como pacote —
o mesmo que `python -m scripts.cherry` faz quando se está na raiz.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

if str(RAIZ) not in sys.path:
	sys.path.insert(0, str(RAIZ))

from scripts.cherry.app import main  # noqa: E402

main()
