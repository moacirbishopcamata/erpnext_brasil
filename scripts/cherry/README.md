# Cherry

Interface desktop (Python + tkinter, sem dependência nova) para as configurações que se fazem à
mão num bench do Frappe/ERPNext: banco de dados (MariaDB ou PostgreSQL), portas e Redis,
sites (`allow_tests`, `default_site`) e `apps.txt`. Documentação completa, decisões de UX e
fontes em [`docs/cherry.md`](../../docs/cherry.md).

```sh
python scripts/cherry/cherry.py            # ou: python -m scripts.cherry (na raiz do repositório)
python -m unittest scripts.cherry.test_config scripts.cherry.test_app -v
```

Licença **MIT** — ver [`LICENSE`](LICENSE) nesta pasta. Versão em `__init__.py`
(`__version__`), incrementada a cada mudança visível.

Revisão de segurança, escrita de arquivo, testes e UX: [`docs/revisao-do-cherry.md`](../../docs/revisao-do-cherry.md).
