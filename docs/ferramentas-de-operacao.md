# Ferramentas de operação: Cherry, Soda e Chantilly

Visão geral das três ferramentas de quem desenvolve e opera o ERPNext Brasil num bench de desenvolvimento. **Estado em 2026-10-11:** o Cherry existe (`0.2.1`); a **persistência selecionável** e o **núcleo puro do Soda** (identidade, portas, registro, conciliação, diário, planos, leitor) estão implementados e mesclados; o ciclo de vida e a interface do Soda e o Chantilly inteiro são **propostas** (OpenSpec), sem código. Cada ferramenta tem o seu documento; este mostra como se encaixam.

| Ferramenta | Para que serve | Estado | Documento | Mudança OpenSpec |
|---|---|---|---|---|
| **Cherry** | Configurar o bench: banco, portas, Redis, sites, `apps.txt` | existe, `0.2.1` | [`cherry.md`](cherry.md) | `cherry-instancias-por-uuid` (proposta) |
| **Soda** | Criar e operar **várias instâncias** do ERPNext Brasil, cada uma em portas diferentes, com UUID único | núcleo implementado; ciclo de vida e interface em proposta | [`soda.md`](soda.md) | `soda-instancias-do-erp` |
| **Chantilly** | Monitorar o **consumo** de RAM, CPU e armazenamento e estimar o custo; iniciar e parar o ERP com gentileza | proposta | [`chantilly.md`](chantilly.md) | `chantilly-monitor-de-recursos` |

A persistência selecionável (JSON ou SQLite) das três é a mudança `persistencia-sqlite-opcional`.

## Windows e Linux

**O ERP e os três utilitários devem funcionar em Windows e em Linux** (mudança `ferramentas-multiplataforma`). Um limite precisa ficar claro: o **Frappe/ERPNext não roda nativo no Windows** (o `bench` não funciona nativo; o projeto roda o bench no WSL2). Então:

| | Windows com WSL2 | Windows sem WSL | Linux |
|---|---|---|---|
| **ERP (ERPNext Brasil)** | funciona (o bench roda dentro do WSL2) | **não suportado** (o upstream não suporta Frappe nativo no Windows) | funciona nativo |
| **Cherry** | janela no Windows, bench no WSL2 por `\\wsl.localhost\...` | indisponível sem bench; orienta a instalar o WSL2 | janela e bench no mesmo Linux; sem display, comandos de terminal |
| **Soda** | idem | idem | idem |
| **Chantilly** | mede o computador Windows (por `ctypes`) **e** o ambiente do bench no WSL2, separados | mede só o computador Windows | mede o Linux por `/proc` |

Mesmo código nos dois sistemas; a diferença fica em adaptadores de plataforma (`WindowsComWsl` e `LinuxNativo`), e a regra pura nunca consulta o sistema operacional. Caminho do computador e caminho do bench são tipos distintos (o do bench é sempre Linux). O CI roda em Ubuntu e em Windows. **Pendente de confirmação:** se "o ERP funcionar em Windows" significa WSL2 (o único modo suportado) ou Windows nativo (projeto à parte e de risco alto).

## Docker, para portabilidade

Além do caminho de desenvolvimento sem Docker (`scripts/subir.sh`), o ERPNext Brasil tem **configuração Docker** em `docker/` ([`docker.md`](docker.md)): uma imagem com `erpnext` e `erpnext_brasil` na versão 16 e um Compose com MariaDB ou PostgreSQL por override, igual em Windows (Docker Desktop) e em Linux. Segredos por arquivo, porta web só em `127.0.0.1`. **A escolha do banco continua sendo do Cherry** (o Compose só combina o override). Cada projeto do Compose aceita `SODA_INSTANCE_ID` e `SODA_DESCRITIVO` como rótulos e um nome de projeto derivado do UUID, o que deixa o terreno pronto para o Soda orquestrar instâncias em contêineres e para o Chantilly medir por contêiner (`docker stats`); esses dois usos são **evolução**, não fazem parte desta entrega.

## Quem decide o quê

| Decisão | Dono | Como as outras ferramentas sabem |
|---|---|---|
| **Qual banco usar** (MariaDB e/ou PostgreSQL, servidor, porta, usuário) | **Cherry**, que faz toda a configuração | perfis de banco publicados somente para leitura (`cherry-perfis-de-banco`) |
| **Quais instâncias existem**, UUID, descritivo, portas | **Soda** | contrato de identidade (registro e `site_config`) |
| **O quanto cada coisa consome** | **Chantilly** (coleta e guarda) | só observa; a única ação é iniciar e parar o ERP, sempre explícita; publica um resumo de desempenho por instância, somente leitura |
| **Mostrar o desempenho de cada instância e do seu banco** | **Soda** (lê) | lê o resumo do Chantilly por UUID; não coleta por conta própria |

O Soda não pergunta qual banco usar: ele oferece os perfis que o Cherry configurou (sem perfil, recusa e aponta o Cherry). O Chantilly só lê o tipo de banco para saber como consultar o tamanho das tabelas.

## Complementos desktop em Python puro

**O Cherry, o Chantilly e o Soda são complementos desktop, em Python puro, para gerenciar melhor o ERP.** Isso quer dizer, para as três:

- **Só a biblioteca padrão:** `tkinter`, `sqlite3`, `json`, `uuid`, `socket`, `subprocess`. Nenhum pacote de terceiros, nenhum `pip install`.
- **Desktop:** uma janela no computador de quem opera, sem servidor web e sem página no desk do Frappe. Rodam no Windows e operam o bench do WSL2/Linux pelo caminho `\\wsl.localhost\...` e por comandos `wsl`.
- **Complementos, não parte do site:** funcionam ao lado do ERP, sem depender de instalar nada no site. Onde precisam de algo de dentro do bench (por exemplo, o tamanho das tabelas no banco, que a biblioteca padrão não consegue consultar porque não há driver de MariaDB nela), chamam o próprio bench (`bench execute`) pelo executor e leem o resultado.
- **Sondas dentro do ERPNext são opcionais.** O Chantilly mede host, processos, armazenamento e jobs sem nenhuma sonda; as sondas de requisição (`before_request`/`after_request`), que dão a CPU por endpoint, são um acréscimo opcional do app `erpnext_brasil`, que o complemento reconhece quando presente e dispensa quando ausente.

## O que é o "ERPNext Brasil"

**O ERPNext Brasil é o ERPNext inteiro, com a adição da tropicalização própria das leis brasileiras.** Não é um subconjunto fiscal do ERPNext: é todo o ERPNext (vendas, compras, estoque, contabilidade, produção, projetos, RH quando instalado...) mais a camada brasileira (`erpnext_brasil`: documentos fiscais, SPED, eSocial, impostos, folha). As três ferramentas operam esse conjunto completo:

- o **Soda** instala em cada instância o `erpnext` completo e o `erpnext_brasil` (sempre os dois); `hrms` e `healthcare` são opcionais;
- o **Chantilly** atribui consumo a **todos** os módulos e DocTypes do ERPNext, e não apenas aos fiscais; a camada brasileira aparece como mais um recorte, não como o todo;
- o **Cherry** configura o bench inteiro.

## Como se encaixam

```
                 ┌──────────────────────────────────────────────┐
                 │  Bench (WSL2/Linux)                          │
                 │   site A  site B  site C   ← instâncias      │
                 │   (UUID + descritivo + host + porta)         │
                 └──────────────────────────────────────────────┘
                      ▲ cria, inicia, para        ▲ lê consumo
        ┌─────────────┴───────┐        ┌──────────┴─────────┐
        │  Soda               │        │  Chantilly         │
        │  (dono da           │        │  (coletor + UI;    │
        │   identidade)       │        │   lê a identidade) │
        └─────────┬───────────┘        └──────────┬─────────┘
                  │ contrato de identidade (somente leitura)
                  ▼
        ┌─────────────────────┐
        │  Cherry             │  edita a configuração comum do bench
        │  (lê a identidade)  │  e avisa o alcance sobre as instâncias
        └─────────────────────┘
```

O **Soda é o único escritor da identidade**. O Cherry e o Chantilly só leem.

## Identidade: UUID com descritivo único

Toda instância tem:

- **UUID versão 4**, gerado uma vez, **imutável** e **nunca reutilizado**, nem depois de a instância ser removida. É a chave de identidade: tudo que uma ferramenta guarda por instância (histórico de consumo, por exemplo) fica preso ao UUID.
- **Descritivo único**: texto de 3 a 60 caracteres que descreve a instância para quem lê ("NF-e em homologação"). Único sem diferença de caixa nem de acento, **renomeável**. Renomear não muda o UUID, o host nem a porta.
- **Nome de host** `descritivo-xxxxxxxx.localhost`, derivado do descritivo e do trecho do UUID. Por que host próprio e não só porta própria: o navegador **compartilha cookies entre portas do mesmo host**, então duas instâncias em `localhost:8101` e `localhost:8102` derrubariam a sessão uma da outra. (Premissa a confirmar na prática; é a tarefa 1.1 do Soda.)

### O contrato de identidade

Publicado pelo Soda, lido pelas outras duas, em três faces:

1. O **registro** do bench (`sites/soda/registro.json`, ou SQLite se escolhido) com a **versão de esquema**.
2. As chaves `soda_instance_id` e `soda_descritivo` no **`site_config`** de cada instância, para identificar a instância mesmo com o Soda fechado e de dentro do processo do Frappe.
3. Um **leitor puro e somente leitura** (`erpnext_brasil/soda/leitura.py`), que lê JSON ou SQLite com o mesmo resultado.

Compatibilidade: campo novo não quebra leitor antigo; remover ou renomear campo exige nova versão de esquema. Sem o Soda, Cherry e Chantilly funcionam como antes, tratando cada site como instância **sem UUID**.

## Persistência: JSON ou SQLite, à escolha

| Ferramenta | Estado persistido | Padrão | Opção |
|---|---|---|---|
| Cherry | preferências (bench, distro, geometria); **nunca senha** | JSON | SQLite |
| Soda | registro das instâncias, portas, UUIDs aposentados | JSON | SQLite |
| Chantilly | **série histórica** | SQLite (único) | — (JSON não comporta o volume) |
| Chantilly | limiares, preços, registro de ações de controle | JSON | SQLite |

Cada ferramenta define uma **porta de persistência** (repositório) e dois adaptadores. Uma **suíte de contrato** roda a mesma bateria de testes contra os dois, para provar que se comportam igual. A troca de formato **migra sem perda**, mantém cópia do formato anterior até a confirmação, e o esquema do SQLite é versionado (`PRAGMA user_version`) com migrações testadas. Nenhum formato guarda segredo, e arquivo ilegível vai para quarentena em vez de ser sobrescrito.

## Resiliência, robustez e segurança (obrigatórias nas três)

Por decisão do dono do projeto (2026-10-11), as três devem ser **bem escritas e ter o máximo de resiliência, robustez e segurança**. Como alteram o ambiente (gravam configuração, criam e removem bancos, iniciam e param o ERP), a qualidade é requisito, e não estética. Os critérios, conferidos por testes e por um **gate** ao fim de cada mudança (mudança `resiliencia-e-seguranca-das-ferramentas`):

| Qualidade | O que exigimos | Como se confere |
|---|---|---|
| **Resiliência** | operação de vários passos registra a intenção, desfaz só o que fez e pode ser retomada depois de interrupção; repetir é seguro; todo comando externo tem prazo e saída limitada | falha injetada em cada passo; processo morto no meio; comando que não termina |
| **Robustez** | toda entrada validada na fronteira; limites de tamanho, quantidade e tempo; nenhuma exceção sem tratamento chega à janela; leitores de `/proc`, de saída de comando e de JSON de terceiros resistem a entrada malformada | testes de entrada truncada, vazia, com bytes inválidos e mil entradas aleatórias de semente fixa |
| **Segurança** | segredo nunca em argumento, log, persistência, mensagem nem clipboard indefinido; comando é lista de argumentos, nunca shell; caminhos confinados ao bench e sem seguir link simbólico; arquivos de estado só do dono; ação destrutiva falha fechada; processos por PID e diretório, nunca por nome | varredura por `ast` de padrões proibidos (`shell=True`, `os.system`, `eval`, `exec`, `pickle`, `except:` sem tipo); busca do segredo em todos os arquivos; link simbólico real |
| **Escrita** | regra pura separada de I/O, contratos, nomes do domínio, nenhuma exceção engolida, módulos pequenos | `ruff`, `tests/test_arquitetura.py`, revisão |

Já aprendido no código: a revisão do Cherry mediu senha legível na linha de comando (CH-01), arquivo truncado por falha de escrita (CH-02) e comando sem escape (CH-03); e a suíte de concorrência da nova persistência encontrou, no Windows, gravações perdidas por `os.replace` contra um leitor, conversão para WAL concorrente e migração repetida, todas corrigidas por teste.

## Padrões de projeto, testes e cobertura (iguais para as três)

Os mesmos do app e do Cherry:

- **Design by Contract:** pré-condição recusada antes de tocar em estado, pós-condição gravada como teste, invariante no construtor.
- **Dados imutáveis** nas fronteiras (`dataclass(frozen=True)`) e **inversão de dependência** por portas pequenas: relógio, executor de comandos, repositório, leitor de `/proc`, teste de porta livre.
- **Regra pura** (sem I/O, sem `frappe`, sem tkinter) e camada fina que só traduz; `tests/test_arquitetura.py` vigia a fronteira.
- **Falha alto** onde o silêncio daria dado errado; **senha nunca em argumento de processo**; **escrita atômica**.
- **TDD com teste na costura:** grava-se por um caminho e relê-se por outro.
- **Cobertura:** núcleo a 100% (piso de 95% no CI), interface com piso próprio dois pontos abaixo do medido, `ruff check` e `ruff format` limpos, job de CI com `xvfb`.
- Versão própria, licença MIT própria, documento próprio com as fontes de UX.

Cada mudança termina com uma tarefa de **gate de padrões** que confere isso com a saída dos comandos.

## UX: idêntica à do Cherry

Interface desktop em tkinter, só com a biblioteca padrão: abas com nome específico e uma instrução principal por aba; sucesso na barra de estado e numa marca "✓" que some sozinha, com caixa de diálogo só para problema; vocabulário que não culpa ("não foi possível"); teclado completo (foco inicial, Enter, teclas de acesso); nitidez em HiDPI; geometria lembrada e **validada contra a tela**; operações longas numa thread de trabalho com "Parar de esperar". Estado sempre por texto e ícone, nunca só por cor.

## Ordem sugerida de implementação

1. **Persistência selecionável nas preferências do Cherry** *(adaptadores e suíte de contrato feitos; falta ligar nas preferências do Cherry)*: pequena, independente, e define a porta e a suíte de contrato que as outras reaproveitam.
2. **Soda, núcleo e contrato** *(feito, PR #22; falta o `site_config`)*: UUID, descritivo, portas, registro e leitor. O leitor destrava as duas integrações.
3. **Cherry por instância** (`cherry-instancias-por-uuid`).
4. **Soda, ciclo de vida e interface.**
5. **Chantilly:** pode começar antes (sites sem UUID) e ganha a identificação por instância quando o contrato existir.

## Decisões em aberto para o dono do projeto

As do Soda (isolamento por site ou por bench, aplicativos por instância, faixa de portas, remoção com backup), as do Chantilly (o que "custo" significa, retenção, Prometheus, controle em produção) e as transversais: o padrão de persistência de cada ferramenta e se o Cherry importa o leitor do Soda ou tem um leitor próprio. Estão listadas no `design.md` de cada mudança.
