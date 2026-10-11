## Why

O Cherry (`scripts/cherry/`, MIT, tkinter) nasceu em 2026-09-17 como tela de configuração do bench e, pelo roteiro combinado, vai crescer até automatizar a configuração do ERPNext Brasil (`bench new-site`, `install-app`, `migrate`, subir Redis). Hoje ele já **escreve** em `common_site_config.json`, `site_config.json` e `apps.txt`, **recebe a senha de administrador do banco** e a passa a um subprocesso do WSL. Antes de dar a ele o poder de executar comandos, vale uma revisão do que existe: o `docs/cherry.md` descreve a versão `0.1.0`, o `__version__` ainda é `0.1.0`, e nenhuma auditoria olhou o projeto depois do primeiro dia. A revisão total do app (`docs/revisao-total.md`) deixou o Cherry de fora: o app é `erpnext_brasil/`, e o Cherry é ferramenta de quem desenvolve.

Pistas que a leitura inicial já deu, **ainda não verificadas** e por isso são o foco da revisão, não achados:

- `config.py:393` passa `banco.senha_root` como argumento de linha de comando a `wsl -d <distro> -- <python> -c ...`, e `comando_new_site` (`config.py:330-334`) embute `--db-root-password` e `--admin-password` no texto copiado para a área de transferência: a senha fica visível na lista de processos e no clipboard.
- O `app.py` tem 662 linhas e cobertura de 83% na primeira versão; o CI só roda o núcleo (`config.py`), então a interface não tem teste no CI.
- A escrita de arquivo (`gravar_json`, `gravar_apps_txt`) já foi corrigida para `\n` no Windows; não está dito se a gravação é atômica (arquivo temporário e troca) ou direta, nem o que acontece se o processo cair no meio.

## What Changes

- Executar uma **revisão somente leitura** do Cherry em seis frentes: núcleo (`config.py`), interface (`app.py`), segurança de segredo e de escrita, testes e cobertura, UX e acessibilidade, documentação e alinhamento com o roteiro.
- Produzir `docs/revisao-do-cherry.md` (síntese priorizada, mesma escala de severidade da revisão total) e anexos curtos em `docs/revisao-do-cherry/`.
- Reconciliar `docs/cherry.md` e `scripts/cherry/README.md` com o que a revisão encontrar.
- Propor, **sem implementar**, o change de correção de cada achado Crítico ou Alto e um desenho de roteiro para a próxima etapa (executar `bench` de dentro do Cherry) com os requisitos de segurança que a revisão levantar.
- **Não** altera código do Cherry nem do app.

## Capabilities

### New Capabilities

Nenhuma. A revisão não muda comportamento; o change usa `skip_specs: true`.

### Modified Capabilities

Nenhuma.

## Impact

- Escreve apenas em `docs/` e `openspec/changes/`.
- Lê `scripts/cherry/` (1.808 linhas: `config.py` 443, `app.py` 662, testes 520), `docs/cherry.md`, `scripts/cherry/README.md`, `.github/workflows/ci.yml` (job `cherry`) e o roteiro registrado na memória do projeto.
- Roda `python -m unittest scripts.cherry.test_config scripts.cherry.test_app`, `coverage` (como no CI), `ruff check` e `ruff format --check` em `scripts/`.
- Consulta externa para UX e acessibilidade (diretrizes citadas no `docs/cherry.md` e releitura de que ainda valem), conforme a autorização permanente de verificar na fonte.
