# Revisão do Cherry — requisitos para executar `bench` de dentro dele

Cobre a tarefa 5.2 do change `revisao-do-cherry`. O roteiro combinado é o Cherry passar a executar `bench new-site`, `install-app` e `migrate` e subir o Redis. Hoje ele só gera e copia o comando. **Este documento só levanta requisitos; nada foi implementado.** Cada um responde a um achado (CH-nn) ou a uma decisão do `design.md` do change.

## Pré-requisitos (corrigir antes de executar qualquer coisa)

1. **Segredo nunca em argumento** (CH-01): a senha de root e a de administrador chegam ao processo por variável de ambiente do filho ou por `stdin`. Vale para a sonda de conexão e, depois, para o `bench`.
2. **Escrita atômica** (CH-02): arquivo temporário e `os.replace`. Quem executa comandos escreve ainda mais arquivos; um truncamento no meio de um `new-site` seria pior que hoje.
3. **Valores escapados ou recusados** (CH-03): host, usuário, site e nomes de app não podem chegar a um shell sem aspas. Ao **executar**, usar lista de argumentos (sem `shell=True`), o que elimina a classe inteira.
4. **Operação longa fora da thread da interface** (CH-05): `new-site` e `migrate` levam minutos; a janela precisa continuar viva.

## Requisitos da execução

| Requisito | Motivo |
|---|---|
| Mostrar o comando exato antes de rodar e pedir confirmação sim/não, com o efeito dito ("cria o site X e o banco Y") | Confirmação só com consequência real, como o doc já pratica; `new-site` e `migrate` alteram banco |
| Saída do processo em tempo real numa área de texto, com o código de saída e o traceback completo no fim | O doc recusou executar justamente por "onde o erro aparece"; a resposta é mostrar a saída inteira, não resumir |
| Botão **Parar** enquanto roda (e **Cancelar** só se não houver efeito colateral) | Guia da Microsoft: rotular "Stop" quando a operação está em andamento e deixa estado alterado |
| Barra de progresso indeterminada só quando não houver como medir; sem combinar com cursor de espera | Guia da Microsoft sobre barras de progresso |
| Nunca gravar senha no log de saída; mascarar o que o `bench` ecoar | Mesma regra de `site_config.json` hoje |
| Rodar sempre no bench escolhido, no WSL, pelo mesmo `wsl -d <distro>` da sonda; recusar bench que não exista | Já existe `Bench.no_wsl` |
| Executor injetável, como `testar_conexao(..., executar=...)` | Permite testar sem `wsl` nem bench; o teste de costura relê o que o comando escreveria |
| Antes de `migrate`, lembrar de backup e dizer em que arquivo | Regra do projeto: backup antes de mexer na pilha |

## Decisões em aberto (do `design.md`)

- Versão após as correções: segurança que muda como a senha trafega é visível ao usuário, então pede `minor` (`0.2.0`); a decisão é do dono do projeto.
- Display no CI para a interface (CH-06): `xvfb` ou piso só no núcleo.
