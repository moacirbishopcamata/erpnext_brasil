## 1. Cadastro brasileiro

- [x] 1.1 Criar `fiscal/codigos/municipio.py` (puro): dígito verificador módulo 10 de pesos 1 e 2, as 9 exceções
      do IBGE com nome e fonte, prefixo de UF e a validação que devolve o motivo — verificar com testes que
      incluem um amostra de municípios reais (as 27 capitais), as 9 exceções aceitas, um dígito trocado recusado
      com o dígito esperado, código de outra UF recusado e código malformado recusado
- [x] 1.2 Ligar a validação em `integracao/party.validar_codigo_municipio` com a chave `brasil_municipios_excecao_dv`
      validada, mantendo o código de erro existente — verificar com teste de costura (a chave existe e tem validação)
      e com teste de bench que grava um `Address` válido, um com dígito trocado, um de outra UF e uma exceção
- [x] 1.3 Instalar o modelo de endereço brasileiro na migração, só quando o site não tiver um para o Brasil, de
      forma idempotente — verificar com teste de bench: cria, não duplica na segunda migração, preserva o existente
      e o texto formatado traz número e bairro

## 2. Valoração de estoque

- [x] 2.1 Criar a regra pura que devolve o aviso para o método de valoração (LIFO avisa; FIFO, média móvel e vazio
      não) — verificar com testes de cada método e de que o texto declara a pendência da fonte legal
- [x] 2.2 Ligar o aviso em `Item` e `Stock Settings` para instalação brasileira, sem bloquear a gravação — verificar com
      teste de bench: grava com LIFO e a mensagem aparece; grava com FIFO e não aparece

## 3. Auditoria da pilha

- [x] 3.1 Criar `scripts/auditar_pilha.py` (biblioteca padrão): leitura de versões instaladas do bench, comparação com
      a série suportada, advisories dos quatro projetos Frappe e vulnerabilidades das bibliotecas, com as fontes
      injetáveis — verificar com testes puros que cobrem faixa só com versão corrigida, `tbd`, CVE duplicado entre
      GHSA e PYSEC, versão igual à corrigida, fonte fora do ar e os códigos de saída
- [x] 3.2 Rodar o script contra o bench real e registrar o resultado em `docs/auditoria-da-pilha.md` — verificar que o
      relatório reproduz os achados desta sessão (antes) e fecha em zero pendência alta (depois da atualização)

## 4. A pilha (execução)

- [x] 4.1 Atualizar Frappe 16.36.1 → 16.51.0, ERPNext 16.37.0 → 16.50.0 e HRMS 16.20.1 → 16.50.0 nas últimas tags,
      com backup dos três sites antes — verificado: pontas do `version-16` iguais às tags; backups em
      `sites/v16.localhost/private/backups` e `G:\erpnext-dados\backups-pg` (dumps do PostgreSQL legíveis)
- [x] 4.2 Refazer os dois patches de PostgreSQL de `contrib/` sobre a 16.51.0 — verificado: os dois defeitos
      continuam no upstream (`json.loads` em `link_filters`; ORDER BY sem tratar consulta só de agregados); o 1º
      conflitou só no arquivo de teste e foi resolvido mantendo as duas partes; o 2º aplicou limpo
- [x] 4.3 Subir `pypdf` 6.15.0 → 6.19.0, `Werkzeug` 3.1.6 → 3.1.9 e `urllib3` 2.7.0 → 2.8.0 — verificado: `pip check`
      sem conflito; versões publicadas há 23, 12 e 24 dias, além da quarentena de 7 dias do Frappe
- [x] 4.4 Compilar o Redis 7.2.16 em espaço de usuário — verificado: sha256 igual ao da lista oficial de hashes; `subir.sh`
      passa a usar `BASE_REDIS`
- [x] 4.5 Baixar o MariaDB 10.11.19 ao lado do 10.11.9 — verificado: sha256 igual ao de `sha256sums.txt` do arquivo oficial
- [x] 4.6 Migrar os três sites e rodar os testes de bench — verificar `bench migrate` sem erro nos três e os módulos de bench
      do app passando
- [ ] 4.7 Trocar o MariaDB 10.11.9 pelo 10.11.19 com `mariadb-upgrade`, **quando nenhuma outra sessão estiver usando o
      servidor** — verificar a versão no ar e os três sites respondendo
- [ ] 4.8 Subir o Python do venv de 3.14.6 para 3.14.8 (recriando o venv, com cópia do atual) — verificar `pip check`, a
      suíte de bench e que o venv antigo foi guardado para voltar
- [x] 4.9 Regenerar `contrib/frappe/` (0001 e 0002 rebaseados) e acrescentar o 0003 (pins de `pypdf`/`Werkzeug`) com texto de
      PR em inglês — verificar `git apply --check` de cada patch contra a ponta atual do `version-16`

## 5. Roteiro: cada item vira uma mudança própria

- [ ] 5.1 Abrir a mudança do **DANFE/DACTE/DAMDFE**, com um protótipo em *Print Format* Jinja e outro com
      `brazilfiscalreport` (versão com mais de 7 dias), comparando licença, dependência e fidelidade ao leiaute —
      verificar que a decisão 8 do `design.md` ficou resolvida com evidência
- [ ] 5.2 Abrir a mudança da **distribuição de NF-e e manifestação do destinatário**, a partir do serviço
      `NFeDistribuicaoDFe` já conhecido para o CT-e — verificar que o endpoint por UF está levantado em fonte
- [ ] 5.3 Abrir a mudança da **consulta de CNPJ e CEP**, decidindo fonte, privacidade e funcionamento sem rede —
      verificar que o preenchimento nunca sobrescreve dado já confirmado
- [ ] 5.4 Levantar os **eventos do eSocial** que faltam (S-1210, S-2206, S-2230, S-2210, S-2220, S-2240) no leiaute S-1.3
      oficial e as **regras de cálculo** (férias, 13º, rescisão, DSR, adicionais) com o dispositivo legal de cada uma —
      verificar que nenhuma regra entra sem fonte citada
- [ ] 5.5 Levantar o **ponto eletrônico** no texto oficial da Portaria MTP 671/2021 (AFD, AEJ, CAdES e prazos) e mapear
      `Employee Checkin` e `Attendance` do HRMS — verificar que as datas deixam de ser de fonte secundária
- [ ] 5.6 Instalar o **Frappe Health v16** num site de teste e levantar os DocTypes de pedido, resultado e laudo; abrir a
      mudança do app de saúde (TISS 4.03.00, TUSS, CNES, RNDS/FHIR) e a da integração com equipamentos (PACS/DICOM,
      HL7 v2/ASTM, ECG) — verificar que cada item cita padrão e fonte
- [ ] 5.7 Abrir as mudanças de **retenção sofrida**, **projetos → serviço** (depende da NFS-e) e **importação** —
      verificar que cada uma lista o que depende de fonte ou de terceiro

## 6. Documentação e fechamento

- [ ] 6.1 Atualizar `docs/avaliacao-tropicalizacao.md` (números de 2026-09-16, hoje desatualizados) e
      `docs/tropicalizacao-por-area.md` com o resultado desta verificação — verificar que cada lacuna aponta para a tarefa
      ou mudança que a resolve
- [ ] 6.2 Registrar em `docs/ambiente-dev-bench.md` o processo de atualização (backup, ordem, o que depende de servidor
      livre) — verificar que um segundo desenvolvedor consegue repetir
- [ ] 6.3 Rodar a suíte pura, a de bench e o `ruff`, e subir a versão em `erpnext_brasil/__init__.py` — verificar tudo verde
      antes do commit
