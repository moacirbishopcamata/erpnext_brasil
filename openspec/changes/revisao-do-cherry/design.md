## Context

Ver `proposal.md` (Why). O que a leitura inicial estabeleceu sobre o Cherry:

- Mora em `scripts/cherry/`, fora do pacote `erpnext_brasil/`, com licença MIT própria e versão própria (`__version__ = "0.1.0"`).
- `config.py` é o núcleo, sem tkinter, sem Frappe e sem rede, testável com `unittest` puro; `app.py` só coleta o que foi digitado e chama o núcleo (mesma fronteira `fiscal/` × `integracao/` do app).
- Escreve em `sites/common_site_config.json`, `sites/<site>/site_config.json` e `sites/apps.txt`, e em `~/.cherry.json` (só caminho, distro e geometria, nunca senha).
- O teste de conexão tem três níveis (venv do bench no WSL, driver local, TCP) e injeta o executor (`executar=subprocess.run`), o que permite testar sem `wsl` nem rede.
- No CI, o job `cherry` roda só o núcleo, com piso de cobertura de 95% sobre `config.py`; `test_app.py` precisa de display e pula no Ubuntu sem X.
- Regras do roteiro: mesmos padrões do app (SOLID, DbC, teste na costura), núcleo com 100% de cobertura, versionamento incremental, UX conforme boas práticas pesquisadas na web.

## Goals / Non-Goals

**Goals:**
- Dizer se o Cherry está pronto para ganhar o poder de **executar** comandos do bench, e o que precisa mudar antes.
- Achar o que ninguém declarou: segredo exposto, escrita que pode corromper arquivo, interface sem teste no CI, doc que descreve uma versão que já passou.
- Sair com uma fila de correções pequenas e um desenho de requisitos de segurança para a próxima etapa do roteiro.

**Non-Goals:**
- Implementar correção ou a execução de `bench` (cada uma vira change próprio, depois desta revisão).
- Revisar o ERPNext Brasil (`erpnext_brasil/`); isso foi feito na revisão total.
- Trocar tkinter por outra tecnologia de interface.
- Testar o Cherry contra um bench real que o usuário use no dia a dia: qualquer execução que escreva num bench usa uma cópia temporária.

## Decisions

1. **Seis frentes, mesma escala de severidade da revisão total.** Núcleo; interface; segurança de segredo e de escrita; testes e cobertura; UX e acessibilidade; documentação e roteiro. Crítico: segredo exposto ou arquivo de configuração corrompido sem aviso. Alto: caminho inalcançável ou teste que não prova a costura. Médio: doc defasada, cobertura menor que a prometida. Baixo: estilo.
2. **Segredo é a frente prioritária.** Verificar, com evidência de execução e não só de leitura: (a) a senha de root aparece na lista de processos durante o teste de conexão (`wsl -d ... -- python -c ... <senha>`); (b) o comando copiado para o clipboard contém as senhas; (c) `~/.cherry.json` nunca recebe senha; (d) a senha não vai para log, repr nem mensagem de erro. Para (a), preferir a medição (listar processos durante a chamada) a afirmar pela leitura.
3. **Escrita de arquivo: provar a pós-condição, não só o formato.** Conferir se a gravação é atômica (arquivo temporário e troca), o que acontece com o arquivo se o processo cair no meio, com permissão negada e com caminho `\\wsl.localhost\...` indisponível. Teste na costura: reler os bytes por caminho independente, como o projeto já faz.
4. **Interface testada onde roda.** Medir a cobertura real do `app.py` (a promessa foi 83%), rodar `test_app.py` com display, e decidir se o CI ganha um passo com `xvfb` ou se o piso de cobertura continua só no núcleo. A decisão fica registrada com o custo.
5. **UX: reconferir contra as fontes, não só contra o `docs/cherry.md`.** As diretrizes citadas (Microsoft, NN/g) são releitas na web; cada linha da tabela de UX do doc é verificada na tela (teclado, foco, HiDPI, redimensionamento, leitor de tela quando o tkinter permitir). Como o Cherry é desktop, "responsivo" aqui significa janela redimensionável e legível em tamanhos e escalas diferentes, não celular.
6. **Roteiro: requisitos antes de código.** A próxima etapa (executar `bench new-site`, `install-app`, `migrate`) pede decisões que a revisão deve levantar: onde o erro aparece, como o segredo chega ao processo (variável de ambiente ou arquivo temporário protegido, nunca argumento), confirmação antes de comando destrutivo, e o que o botão "cancelar" faz com um processo em andamento.
7. **Revisão em linha, sem subagentes**, para a severidade ficar consistente.

## Risks / Trade-offs

- **Medir a lista de processos exige executar `wsl`:** pode não estar disponível. Mitigação: se não der, a síntese diz "inferido da leitura" e deixa a medição como tarefa.
- **Tocar num bench real:** qualquer teste que grave usa um diretório temporário; nenhum bench do usuário é lido para escrita. Leitura de bench real só com autorização explícita.
- **Display ausente:** parte da interface só se verifica com janela; sem display, essa parte fica como não executada e é dito.
- **Escopo que cresce:** a tentação é já implementar o `bench new-site`. A revisão só propõe.

## Open Questions

- O Cherry deve passar a usar versão `0.2.0` ao receber correções? Pela regra do doc, correção sem mudança de comportamento é `patch`; correção de segurança que muda a forma como a senha trafega é visível ao usuário e seria `minor`. A decidir na aplicação.
