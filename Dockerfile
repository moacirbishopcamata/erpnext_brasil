# syntax=docker/dockerfile:1

# Imagem de desenvolvimento do erpnext_brasil, no padrão do frappe_docker
# (https://github.com/frappe/frappe_docker) — parte da imagem oficial `frappe/erpnext`,
# que já traz Frappe + ERPNext instalados e configurados, e só acrescenta este app.
#
# Por que não `bench init` do zero aqui dentro
# ------------------------------------------------------------------------------
# A imagem oficial já resolveu a parte cara (Python/Node/wkhtmltopdf/dependências de
# sistema, versões compatíveis de Frappe/ERPNext) — refazer isso num Dockerfile próprio
# duplicaria manutenção sem ganho: qualquer atualização de versão do Frappe/ERPNext já
# vem pronta na imagem oficial, só é preciso instalar o app por cima.
#
# ARG FRAPPE_VERSION escolhe a tag/branch da imagem oficial — mantido sempre na versão
# **estável** mais recente de Frappe/ERPNext (`version-16`, confirmado via
# github.com/frappe/frappe e github.com/frappe/erpnext em 2026-09-03: Frappe v16.33.0,
# ERPNext v16.34.1). Ver `docs/versoes-frappe-erpnext.md` — o bench WSL2 usado para
# testar de verdade este app ainda está em `version-15`; a compatibilidade com
# `version-16` não foi exercitada além do build da imagem em si.
ARG FRAPPE_VERSION=version-16
FROM frappe/erpnext:${FRAPPE_VERSION}

# O usuário `frappe` já existe na imagem oficial e é quem o bench espera rodar como.
USER frappe

# Copia o código deste repositório para dentro da imagem e instala como app local —
# não via git (este repositório não tem remote público ainda; ver
# docs/ambiente-dev-bench.md). Quando o repositório for publicado no GitHub, trocar
# este COPY por `bench get-app <url>` é a migração natural, sem mudar mais nada.
COPY --chown=frappe:frappe . /home/frappe/erpnext_brasil_src

WORKDIR /home/frappe/frappe-bench

RUN bench get-app erpnext_brasil /home/frappe/erpnext_brasil_src

# Instalação no site é feita depois, com o site já criado (não há site no build da
# imagem) — ver `docker-compose.yml` (`create-site` no serviço `configurator`) e
# `docs/ambiente-dev-bench.md` para o fluxo completo `bench new-site`/`install-app`.
