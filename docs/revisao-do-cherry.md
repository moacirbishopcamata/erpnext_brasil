# Revisão do Cherry — síntese

Revisão de **2026-10-11**, commit `861fa11`, Cherry `0.1.0`. Executa o change `revisao-do-cherry`. Somente leitura: nenhum código do Cherry foi alterado. Mesma escala de severidade da [revisão total do app](revisao-total.md).

Anexos: [linha de base](revisao-do-cherry/linha-de-base.md) · [segredo e escrita](revisao-do-cherry/seguranca-e-escrita.md) · [núcleo, interface, testes e UX](revisao-do-cherry/interface-testes-ux.md) · [requisitos para executar `bench`](revisao-do-cherry/proximo-passo-bench.md).

## O que esta revisão é, e o que não é

Leitura dirigida por risco mais medições em diretório temporário. Não rodei o Cherry contra um bench real do usuário e não mexi em nenhum. Medi na prática três coisas (senha na linha de comando do processo, falha de escrita no meio do arquivo, comando copiado sem escape); o resto é leitura. Não li o corpo das abas Sites e `apps.txt` de `app.py` nem os 41 testes de `test_config.py`.

## Veredito

O núcleo está bem desenhado e coberto (`config.py`, 100%, contratos e executor injetável). **O Cherry ainda não está pronto para executar comandos do `bench`**: dois achados Altos de segurança e escrita precisam ser corrigidos antes, porque uma ferramenta que executa comandos amplia o dano de ambos.

## O que está bem

- `config.py` com 100% de cobertura de linhas e contratos que recusam antes de tocar em arquivo.
- JSON corrompido, objeto que é lista e arquivo somente leitura **não** levam a gravar por cima (medido).
- `~/.cherry.json` nunca recebe senha; `Banco` esconde a senha do `repr`; o `site_config.json` exibido mascara três chaves.
- Doc fiel à `0.1.0`: 55 testes, 100% / 83% / 88%, abas, teclas de acesso e foco conferem.
- `ruff` limpo; 55 testes passam, inclusive os da interface (a máquina tem display).

## Achados

| ID | Sev. | Achado | Onde |
|---|---|---|---|
| CH-01 | **Alto** | Senha de root como argumento de linha de comando do processo (medido no Windows: legível) | `config.py:393-402` |
| CH-02 | **Alto** | Gravação não atômica: falha no meio deixa o arquivo truncado e inválido (medido) | `config.py:176-187` |
| CH-03 | Médio | `bench new-site` copiado escapa só as senhas; host, usuário, site e apps entram crus (medido) | `config.py:310-338` |
| CH-04 | Médio | Senha de administrador `admin` pré-preenchida e senhas no clipboard sem limpar | `app.py:210`, `388-389` |
| CH-05 | Médio | Teste de conexão na thread da interface: até ~63 s de janela travada (inferido) | `app.py:321-337`, `config.py:421` |
| CH-06 | Médio | Interface sem teste no CI; 17% de `app.py` sem cobertura, inclusive `_testar_conexao` inteiro | `ci.yml` job `cherry`, `app.py:322-337` |
| CH-07 | Baixo | Mensagens "inválido" contrariam a regra de vocabulário do próprio Cherry | `config.py:157`, `318` |
| CH-08 | Baixo | Geometria salva restaurada sem checar se cabe na tela | `app.py:613-614` |
| CH-09 | Baixo | Campo vazio remove a chave de Portas e Redis sem dizer qual | `app.py:436-461` |

Contagem: 2 Altos, 4 Médios, 3 Baixos (9). Nenhum Crítico. Todos são achados desta revisão; nenhum estava declarado antes.

## O que depende do ambiente

- Cronometrar CH-05 e medir CH-01 dentro do WSL (`ps`).
- Verificar visualmente HiDPI, escala de 150% e tela menor que 1366×768.
- Decidir `xvfb` no CI para a interface.

## Fila de correções

1. **`endurecer-segredo-e-escrita-do-cherry`** — CH-01, CH-02, CH-03 e CH-04. Criado.
2. Sem change criado, a decidir: CH-05 (sonda em thread) e CH-06 (interface no CI), que andam juntos; CH-07, CH-08 e CH-09 são ajustes pequenos.
3. Só depois: executar `bench` de dentro do Cherry, com os requisitos de [`proximo-passo-bench.md`](revisao-do-cherry/proximo-passo-bench.md).

## Correções aplicadas (Cherry `0.2.0`)

CH-01, CH-02, CH-03 e CH-04 corrigidos no código, com teste que **falha no código antigo** (13 falhas e 5 erros em `test_config`) e passa no novo. CH-01 foi medido de ponta a ponta no WSL: a senha chega ao Linux pelo ambiente, não aparece na linha de comando do `wsl.exe` e tem zero ocorrências no `ps`. CH-05 e CH-06 foram corrigidos na `0.2.1` (sonda em thread de trabalho com "Parar de esperar"; interface no CI com `xvfb` e piso de 87%). Ficam abertos os Baixos CH-07, CH-08 e CH-09. Detalhes em `docs/cherry.md`, seção "Versão 0.2.0".

## Reconciliação feita

`docs/cherry.md` ganhou uma seção "Revisão de 2026-10-11" e `scripts/cherry/README.md` aponta para esta síntese; `docs/README.md` indexa a revisão. Os números do corpo do `docs/cherry.md` **não** mudaram: conferem com o código.
