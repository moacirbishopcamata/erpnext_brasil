# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes que exigem um bench real (banco/Redis/Frappe) — deliberadamente **fora**
de `erpnext_brasil/tests/`.

Por que uma pasta separada, não `tests/` mesmo
------------------------------------------------------------------------------
`test_arquitetura.py::TestSuiteRodaSemBench.test_nenhum_teste_importa_frappe` varre
só `erpnext_brasil/tests/` (`RAIZ / "tests"`, hardcoded) — um teste que importa
`frappe` ali quebraria essa invariante e pararia de rodar em qualquer máquina sem
bench. A suíte pura (`python -m unittest discover -s erpnext_brasil/tests -t .`,
usada em CI e por qualquer contribuidor sem ambiente Frappe) também só varre esse
diretório — um teste aqui em `tests_bench/` nunca é descoberto por ela, por
construção, não por convenção que alguém possa violar sem perceber.

Como rodar
------------------------------------------------------------------------------
Só dentro de um bench com `erpnext_brasil` instalado (ver `docs/ambiente-dev-bench.md`):

    bench --site <site> run-tests --module erpnext_brasil.tests_bench.test_certificado_a1

Cada teste usa `frappe.tests.utils.FrappeTestCase` — rollback automático por teste,
mesma disciplina de não deixar resíduo entre testes já exigida para o resto do SPED
(`ERPNextTestSuite` no core do `erpnext`).

Por que existe agora, não antes
------------------------------------------------------------------------------
Todo módulo de `integracao/` até 2026-09-03 estava documentado como "sem teste
dedicado — depende do Frappe, não testável sem bench" (`party.py`, `cte_extracao.py`,
`certificado_a1.py`, etc.). Isso deixou de ser verdade quando o bench WSL2 foi
reconfirmado funcionando de ponta a ponta (ver `docs/ambiente-dev-bench.md`) —
`tests_bench/` é onde a cobertura real desses módulos passa a viver, incrementada aos
poucos, não de uma vez.
"""
