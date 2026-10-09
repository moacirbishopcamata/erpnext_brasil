# Instalação do ERPNext Brasil — guia técnico

Este documento cobre os dois caminhos de instalação: **bench nativo** (produção ou
desenvolvimento real, o único confirmado funcionando de ponta a ponta neste projeto) e
**Docker/compose** (alternativo, ver ressalva). Para o que cada versão suportada
significa, ver [`versoes-frappe-erpnext.md`](versoes-frappe-erpnext.md).

## Pré-requisitos

- **Python** — a versão exigida acompanha a do Frappe/ERPNext instalados (`>=3.10`,
  `pyproject.toml` deste app). O repositório `erpnext` (core) já pede `>=3.14` para o
  branch `develop`; um bench em `version-15`/`version-16` (estável) usa a versão que
  aquele branch específico exigir — conferir com `bench` no momento da instalação.
- **Node.js** e **Yarn** — exigidos pelo próprio `bench` para os assets do Frappe.
- **MariaDB 10.6+** (mínimo recomendado pelo Frappe) ou o que a versão do bench exigir.
  **PostgreSQL** também funciona (provado com 18.6 — ver [`postgresql.md`](postgresql.md)),
  mas o Frappe o declara experimental e o ERPNext não o suporta oficialmente; exige o
  cliente `psql` na máquina do bench e as correções listadas naquela página.
- **Redis** — dois processos, cache e fila (o próprio `bench init` gera a configuração
  com as portas certas).
- **`bench`, o CLI do Frappe** (`pipx install frappe-bench` ou `pip install --user
  frappe-bench`) — **só roda em ambiente Unix** (Linux, macOS, ou WSL2 no Windows).
  **Achado real, confirmado nesta investigação**: `bench` não roda nativo no Windows —
  o próprio pacote `frappe-bench` faz `import pwd` (módulo exclusivamente POSIX) no
  topo do arquivo de entrada da CLI, e a importação falha antes de qualquer comando.
  Ver [`ambiente-dev-bench.md`](ambiente-dev-bench.md) para o achado completo. No
  Windows, use **WSL2** — nunca tente rodar `bench` nativo.

## Caminho 1 — bench nativo (recomendado, confirmado funcionando)

Este é o caminho testado de ponta a ponta neste projeto (ver
[`ambiente-dev-bench.md`](ambiente-dev-bench.md) para o histórico completo, obstáculos
reais encontrados e como reproduzir em Windows+WSL2 especificamente).

```sh
# 1. Criar o bench (ajuste --frappe-branch para version-15 ou version-16 — ver
#    versoes-frappe-erpnext.md sobre qual está de fato testada com este app)
bench init --frappe-branch version-15 frappe-bench
cd frappe-bench

# 2. Instalar o ERPNext (dependência deste app)
bench get-app erpnext --branch version-15

# 3. Instalar o erpnext_brasil — de um clone local (enquanto não há remote público)...
bench get-app erpnext_brasil /caminho/para/o/repositorio/local
# ...ou, quando publicado no GitHub:
# bench get-app erpnext_brasil https://github.com/<org>/erpnext_brasil

# 4. Criar o site e instalar os apps, nesta ordem (erpnext_brasil depende de erpnext)
bench new-site meusite.localhost
bench --site meusite.localhost install-app erpnext
bench --site meusite.localhost install-app erpnext_brasil

# 5. Subir
bench start
```

Os campos fiscais (`Company`, `Customer`, `Supplier`, `Address`, `Item` — ver
`setup/custom_fields.py`) são criados na instalação e **recriados a cada `bench
migrate`** (hook `after_migrate`), de forma idempotente — não há passo manual adicional.

### Habilitar testes (opcional, para desenvolvimento)

```sh
bench --site meusite.localhost set-config allow_tests true
bench --site meusite.localhost run-tests --app erpnext_brasil
```

## Caminho 2 — Docker/compose (alternativo, não build-testado nesta sessão)

```sh
docker compose up -d
docker compose logs -f create-site   # acompanha a criação do site na 1ª subida
```

Acesso: `http://localhost:8080` (usuário `Administrator`, senha `admin` — só para
desenvolvimento local). Ver [`docker-compose.md`](docker-compose.md) para a estrutura
completa dos serviços e a ressalva sobre não ter sido build-testado de ponta a ponta
nesta sessão — o caminho 1 (bench nativo/WSL2) é o único confirmado.

## Depois de instalado — configuração mínima

1. **Certificado A1** (para transmissão real ao SEFAZ, quando disponível): em
   `Company`, seção "Certificado Digital (transmissão SEFAZ)" — anexar o `.pfx`/`.p12`
   em `br_certificado_a1`, informar a senha em `br_senha_certificado_a1`, e escolher o
   ambiente em `br_ambiente_sefaz` (**"Homologação" é o padrão** — nunca produção sem
   trocar conscientemente). Ver [`certificado-a1-configuracao.md`](certificado-a1-configuracao.md).
2. **Dados fiscais da empresa**: `Company` ganha campos de Regime Tributário,
   Inscrição Estadual/Municipal, CNAE, Natureza Jurídica, Chave Pix. `Address` ganha
   Código do Município (IBGE), Bairro e Número — nenhum desses é derivável
   automaticamente, preencha ao cadastrar.
3. **Contas fiscais**: `Company` também ganha uma seção de contas contábeis (ICMS,
   IPI, PIS, COFINS, IBS, CBS) — tributo sem conta configurada não é lançado na
   apuração automática.

## Desinstalação

```sh
bench --site meusite.localhost uninstall-app erpnext_brasil
bench remove-app erpnext_brasil
```

Os campos customizados (`Custom Field`) criados por este app são removidos junto pelo
mecanismo padrão de `uninstall_app` do Frappe — não é preciso limpeza manual.

## Ver também

- [`ambiente-dev-bench.md`](ambiente-dev-bench.md) — histórico completo de como o bench
  de desenvolvimento deste projeto foi montado (Windows 11 + WSL2 + Docker), obstáculos
  reais e por que o bench nativo no Windows não funciona.
- [`docker-compose.md`](docker-compose.md) — estrutura do `Dockerfile`/`docker-compose.yml`.
- [`versoes-frappe-erpnext.md`](versoes-frappe-erpnext.md) — qual versão de Frappe/ERPNext
  é a estável mais recente vs. a efetivamente testada.
- [`README.md`](README.md) (raiz do repositório) — visão geral do que este app cobre.
