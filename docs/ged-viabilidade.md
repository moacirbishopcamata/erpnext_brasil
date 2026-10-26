# GED (Gestão Eletrônica de Documentos) dentro do ERPNext Brasil: estudo de viabilidade

Pedido do usuário em 2026-10-11: *"verifique a possibilidade de adicionar um GED dentro do ERPNext BR"*, e depois *"pesquise na net"*. Pesquisa feita no mesmo dia, em fontes primárias quando possível. **Nada foi implementado**; este documento só diz o que existe, o que a lei exige e o que recomendo.

> **Resposta curta:** **é viável**, e o caminho de menor risco é um **núcleo próprio e pequeno dentro do `erpnext_brasil`** (metadados, integridade, guarda e custódia sobre o `File` do Frappe), **com assinatura eletrônica em dois níveis** (avançada, feita por nós com dossiê de evidências; qualificada, com ICP-Brasil), e OCR e busca de texto como acréscimo opcional. **Não recomendo** depender hoje do Frappe Drive nem do Suite: o Drive foi **arquivado** em 2026-10-01 e o Suite é **trabalho em andamento**. Há **uma dúvida jurídica que muda custo** (por quanto tempo o contribuinte guarda o XML: 5 ou 11 anos) e que precisa de confirmação com o contador antes de qualquer regra automática de descarte.

## Convenção de confiança

| Marca | Significa |
|---|---|
| **Verificado** | li a fonte primária (código, repositório, texto da norma) nesta pesquisa |
| **Fonte secundária** | só blogs, escritórios ou portais; precisa de conferência na norma |
| **Divergente** | as fontes discordam |
| **Não verificado** | conhecimento meu, sem fonte nesta pesquisa |

## 1. O que o ERPNext/Frappe 16 já tem

**Verificado** no Frappe 16.51.0 instalado (`frappe/core/doctype/file/file.json`): o DocType `File` tem `file_name`, `file_url`, `file_size`, `file_type`, `is_private`, `folder`, `is_folder`, `is_home_folder`, `is_attachments_folder`, `attached_to_doctype`, `attached_to_name`, `attached_to_field`, `thumbnail_url`, `preview`, **`content_hash`** e `uploaded_to_dropbox` / `uploaded_to_google_drive`. `track_changes` está ligado (registra mudança dos **metadados**).

| Capacidade de GED | Situação no Frappe 16 |
|---|---|
| Anexar arquivo a um documento, público ou privado | **tem** |
| Pastas (Home, Attachments) | **tem** (desde 2015, **fonte secundária**: artigo da Frappe) |
| Permissão herdada do documento ao qual o arquivo está anexado | **tem** (`has_permission` do `File` usa o documento de origem) |
| Compartilhar com usuários | **tem** (compartilhamento padrão do Frappe) |
| Hash do conteúdo (base para integridade) | **tem o campo** `content_hash`; **não verifiquei** se é conferido depois de gravado |
| **Versionamento do conteúdo** de um arquivo | **não encontrei**. O artigo da Frappe não o descreve e comentários de leitores pedem "Versioning" e documentos somente leitura como pendência (**fonte secundária**) |
| Tabela de temporalidade, prazo de guarda, descarte controlado | **não tem** |
| Trava contra exclusão por obrigação legal | **não tem** |
| Metadados de classificação (tipo de documento, responsável, data de produção) | **não tem** (só os do `File`) |
| Assinatura digital do arquivo (ICP-Brasil) e carimbo do tempo | **não tem** |
| OCR e busca no conteúdo do arquivo | **não tem** |
| Trilha de custódia (quem viu, baixou, alterou) | **parcial**: `track_changes` do `File`; **não verifiquei** registro de acesso e download |

Ou seja: o Frappe tem um **gerenciador de anexos**, não um GED.

## 2. O que existe pronto

### 2.1 Frappe Drive e Suite (o caminho da própria Frappe)

- **Verificado** (API do GitHub, 2026-10-11): `frappe/drive` é **AGPL-3.0**, tem a **versão mais recente v0.3.0 (2025-10-08)**, e está **arquivado**. O último commit, de 2026-10-01, é *"docs: add archival notice"*. O README diz: *"Frappe Drive is archived and is now part of Suite"*.
- **Verificado:** `frappe/suite` (**AGPL-3.0**) foi criado em 2026-05-27, descreve-se como **"[WIP]"**, reúne sete produtos (Drive, Writer, Sheets, Slides, Meet, Mail, Calendar) e **não tem release estável** (só uma etiqueta `assets-develop`).
- **Verificado:** o README do Drive já o declarava **beta** e recomendava backup porque ele "não deve ser o único meio de armazenamento". O versionamento que ele tem é do editor **Writer**, não de arquivos em geral (**fonte secundária**: artigo da Frappe de 2025-10-10). A integração com o ERPNext existia mas o próprio autor a chamou de incompleta.
- **Verificado, e é o achado mais importante:** o framework ganhou dois ganchos para o Drive, **mesclados só na `develop`**: `after_file_upload` (PR #38167, 2026-06-23) e um gancho para o Drive sobrescrever permissões do `File` (PR #40752, 2026-07-10). **Eles não estavam no Frappe 16.51.0 então instalado** (o bench está hoje na 16.53.0 e a busca **não foi refeita** nela) (procurei no `handler.py` e no `file.py`) e **não achei backport** para a `version-16`. Ou seja, usar o Drive/Suite como gerenciador de arquivos pede o Frappe da `develop`, e não o 16 que o projeto adota.

**Conclusão:** não existe hoje, para a versão 16, um GED mantido pela Frappe em que se possa confiar.

### 2.2 GEDs externos (integração por API)

- **Paperless-ngx:** **GPL-3.0**, projeto muito ativo (v3.3.0 em 2026-10-06, 46 mil estrelas, **verificado**). Tem API REST (documentos, tipos de documento, tags, correspondentes; autenticação por token), guarda uma versão PDF/A arquivada e o original, e faz OCR (**fonte**: documentação oficial). A API **não aceita upload por `POST /api/documents/`**: o envio é por um endpoint de consumo à parte. **Não achei integração pronta com ERPNext/Frappe.**
- **Mayan EDMS:** código aberto, em Django, desde 2015, 14.672 commits (**verificado**), com OCR, workflow e indexação indicados por etiquetas do projeto. **Não consegui confirmar** licença, estado atual, versionamento, assinatura digital nem API pelas páginas lidas.
- **OpenKM, Alfresco, LogicalDOC, Nuxeo:** **não pesquisados.**
- **Licença:** integrar um serviço GPL ou AGPL **por API, como processo separado**, não contamina o `erpnext_brasil` (MIT). **Incorporar o código dele no app, não.**

## 3. O que a lei brasileira exige

### 3.1 Digitalização com validade (Lei 12.682/2012 e Decreto 10.278/2020)

**Verificado** (texto do decreto na Câmara dos Deputados, arts. 3º a 7º) e **fonte secundária** (anexos):

- O documento digitalizado produz os efeitos do original (art. 2º-A da Lei 12.682/2012, regulamentado pelo Decreto 10.278/2020). Os procedimentos devem assegurar **integridade, rastreabilidade, auditabilidade, qualidade da imagem, confidencialidade quando aplicável e interoperabilidade** (art. 4º).
- **Perante pessoas jurídicas de direito público** (art. 5º), são três requisitos cumulativos: **assinatura digital com certificado ICP-Brasil**, **padrões técnicos do Anexo I** e **metadados mínimos do Anexo II**.
- **Entre particulares** (art. 6º), vale qualquer meio de comprovar autoria, integridade e, se preciso, confidencialidade, **desde que as partes concordem** ou que a pessoa contra quem o documento é oposto o aceite. Sem acordo prévio, aplica-se o art. 5º.
- **Fonte secundária, a conferir nos anexos:** Anexo I, texto impresso em preto e branco ou colorido, **300 dpi**, formato **PDF/A**; plantas e mapas, 600 dpi. Anexo II, metadados: **identificador único** do documento, **data e hora e local da digitalização**, **responsável pela digitalização**, e **hash** da imagem; **as fontes divergem** no número de metadados (oito a nove) e sobre exigir ou não SHA-256. **Não obtive o texto dos anexos** (o servidor do Planalto recusou a conexão e a página da Câmara não os trazia).
- Observação crítica (nota técnica do TSE, **fonte secundária**): a assinatura só garante autenticidade ao longo do tempo dentro de um ambiente de preservação confiável.

### 3.2 Guarda dos documentos fiscais eletrônicos

**Divergente.** O **Ajuste SINIEF 2/2025** (publicado em 2025-04-16, vigência 2025-05-01) fixa **132 meses (11 anos)** para a guarda dos XML de NF-e, CT-e, CT-e OS, MDF-e, NFC-e, BP-e, NF3e, GTV-e, DC-e e NFCom, contados da autorização. **Quem é obrigado, as fontes discordam:**

- parte delas diz que é obrigação dos **contribuintes**;
- outra parte, incluindo escritório de advocacia que cita a redação ("critérios e procedimentos para a temporalidade e a destinação de documentos fiscais eletrônicos tutelados pela [...] Receita Federal [...], Estados e o Distrito Federal"), diz que o prazo vale para a **administração tributária** e que o contribuinte continua obrigado a **5 anos** (art. 173 do CTN, salvo processo em andamento).

**Não obtive o texto oficial** (publicado no DOU e no CONFAZ). **Recomendação:** tratar como **11 anos até o contador confirmar**, porque guardar de mais custa disco e guardar de menos custa multa. O prazo precisa ser **configurável**, nunca fixo no código.

### 3.3 Guarda de documentos trabalhistas

**Divergente e fraco.** As fontes são materiais de contabilidade, não normas: prazos de 5 anos (tributários), 10 anos (folha), 20 anos (PPP/PPRA), "indeterminado" (contrato e ficha de registro) e **30 anos para o FGTS**. A fonte que dá os 30 anos o apoia na Súmula 362 do TST, **que pode estar desatualizada**: tenho a lembrança, **não verificada**, de que o STF reduziu a prescrição do FGTS para 5 anos em 2014. Há também a observação de que, com o eSocial, parte desses documentos deixa de ser exigida, mas holerites e recibos seguem úteis como prova. **Conclusão:** não codificar prazo trabalhista; o usuário (RH, contador, advogado trabalhista) o define numa tabela.

### 3.4 Assinatura eletrônica de documentos (Lei 14.063/2020)

Pedido adicional do usuário (2026-10-11): o GED deve ter **assinatura eletrônica de documentos**. A lei distingue **três níveis** (**fonte secundária**: portais jurídicos e uma decisão do STJ; **não consegui o texto da lei no Planalto**, o servidor recusou a conexão):

| Nível | O que é | Força |
|---|---|---|
| **Simples** | identifica o signatário ou associa dados eletrônicos (marcar uma caixa, assinar um e-mail), sem garantia de legitimidade | a menor |
| **Avançada** | associada ao signatário de forma **unívoca** (token, biometria, senha única e temporária) e aos dados do documento de modo que **qualquer alteração posterior seja detectável**; pode usar certificado **não** ICP-Brasil ou outros meios de comprovar autoria e integridade | válida, com presunção menor |
| **Qualificada** | certificado digital **ICP-Brasil** | a maior, com presunção legal de veracidade em relação aos signatários |

- **Todas as modalidades têm validade jurídica**; a diferença é a **força probatória** (STJ, REsp 2159442-PR, **fonte secundária**: o legislador quis níveis diferentes conforme o método). Para contratos **entre empresas**, a avançada costuma bastar; **atos que a lei exige forma específica** (escritura pública, tabelião, assinatura qualificada) **não se resolvem** com nenhuma assinatura eletrônica comum.
- **Entre particulares**, o art. 10 da MP 2.200-2/2001 admite outros meios de comprovar autoria e integridade **se as partes aceitarem** (o próprio Decreto 10.278, art. 6º, segue a mesma lógica). **Não verificado** nesta pesquisa: a redação exata dos arts. 4º a 7º da Lei 14.063/2020 sobre em que interações com entes públicos cada nível é exigido.
- **Evidências que sustentam uma assinatura avançada** (conhecimento geral, **não verificado em fonte**): quem enviou, quem visualizou, quando assinou, endereço IP, dispositivo, hash do documento, confirmação por e-mail ou SMS. **Carimbo do tempo** emitido por autoridade ICP-Brasil tem fé pública técnica; o registro de data feito pela própria plataforma é mais contestável (também sem fonte).
- **O que o Frappe tem:** o tipo de campo `Signature` (**verificado**: `frappe/public/js/frappe/form/controls/signature.js`) é uma **assinatura desenhada à mão**, guardada como imagem. É no máximo assinatura **simples**: não amarra a imagem ao conteúdo do documento nem guarda evidência de autoria. **Não encontrei** módulo de assinatura eletrônica no Frappe, no ERPNext nem no HRMS (busca não exaustiva).
- **O que existe pronto, de código aberto** (**verificado** pela API do GitHub, 2026-10-11): **Documenso** (AGPL-3.0, v2.20.0 de 2026-10-08, 15 mil estrelas), **DocuSeal** (AGPL-3.0, v3.3.1 de 2026-10-05, 18 mil estrelas) e **OpenSign** (licença não identificada pelo GitHub, v2.41.3 de 2026-08-21). Todos são aplicações web que se hospedam à parte e têm API; **não verifiquei** suporte a ICP-Brasil, a português nem a políticas de assinatura. Plataformas brasileiras de assinatura (SaaS) existem, **não foram pesquisadas**.

**Consequência para o desenho:** a assinatura **avançada** é viável dentro do app (autenticar o signatário, registrar o dossiê de evidências, calcular o hash do documento, e **selar** o PDF com o certificado institucional A1 que o app já gerencia, com carimbo do tempo); a **qualificada** de uma pessoa exige o **certificado dela** (A3 em token, ou A1), que **não está no servidor**, então precisa de assinatura no computador do signatário ou de um serviço de assinatura remota (**não pesquisado**).

### 3.5 Assinatura digital ICP-Brasil

- A ICP-Brasil regula a assinatura em PDF no padrão **PAdES** (DOC-ICP-15.02, perfil de uso geral) e as **políticas de assinatura e o carimbo do tempo** (DOC-ICP-15.03, versões 7.1 e 7.2 encontradas; **a versão vigente precisa ser conferida no site do ITI**).
- **pyHanko** (MIT, mantido: último push em 2026-10-11, **verificado**) assina PDF nos perfis PAdES B-B, B-T, B-LT e B-LTA e usa servidor de carimbo do tempo RFC 3161. **Ele não interpreta políticas de assinatura**: o identificador da política é incorporado como informado, e **cumprir a política ICP-Brasil é responsabilidade de quem usa a API**. Não achei exemplo pronto com certificado A1 (PKCS#12) nem A3 (PKCS#11) para ICP-Brasil.
- O `erpnext_brasil` **já trata certificado A1** para assinar XML fiscal; reaproveitar essa gestão de certificado é um ponto a favor.

### 3.6 LGPD e eliminação de dados

**Não pesquisado nesta rodada.** Um GED guarda dados pessoais (RH, cadastros), então retenção, finalidade e eliminação precisam ser tratadas; fica como tarefa.

## 4. Opções de arquitetura

| | A. Núcleo próprio sobre o `File` | B. Frappe Drive / Suite | C. GED externo (Paperless-ngx) por API | D. Híbrido (A + C opcional) |
|---|---|---|---|---|
| Funciona no Frappe 16 | **sim** | **não, hoje** (ganchos só na `develop`; Drive arquivado; Suite WIP) | **sim** (processo separado) | **sim** |
| Atende "dentro do ERPNext BR" | **sim** | parcial | parcial (é outro sistema) | **sim** no essencial |
| Metadados do Anexo II, guarda e custódia sob nosso controle | **sim** | não | parcial | **sim** |
| OCR e busca de texto | não (a construir) | não | **sim** | **sim**, opcional |
| Assinatura eletrônica | a construir (avançada) e integrar (qualificada) | não tem | não tem (Paperless-ngx não assina) | avançada nativa; qualificada por ICP-Brasil; ou serviço de assinatura aberto (Documenso, DocuSeal) à parte |
| Dependência e risco de manutenção | só nosso código | **alto** (projeto em transição) | médio (projeto ativo, GPL) | médio |
| Esforço | médio | baixo, mas sobre base instável | médio (integração e operação de um serviço a mais) | médio a alto |
| Encaixe nos padrões do projeto (regra pura, teste, fonte citada) | **alto** | baixo | médio | alto |

## 5. Recomendação

**Opção D, começando pela A.** Um núcleo pequeno e próprio que dá ao ERP o que a lei mais cobra (identidade, integridade, guarda, rastreabilidade), com OCR e busca como acréscimo opcional via Paperless-ngx, sem depender do Drive.

Fases propostas, cada uma útil sozinha:

1. **Custódia do que o app já produz.** XML de NF-e, CT-e e MDF-e (`Transmissao Fiscal`), arquivos SPED (`Arquivo SPED`) e XML do eSocial passam a ter **hash (SHA-256) conferível**, **prazo de guarda configurável** e **trava de exclusão** durante o prazo. É a fase de maior valor e menor custo, porque os arquivos já existem.
2. **`Documento GED` com metadados.** Tipo de documento, responsável, data de produção, identificador único, hash, vínculo ao documento do ERP, e **versões imutáveis** (um arquivo novo não substitui o anterior, gera outra versão). Permissão herdada do documento de origem.
3. **Política de guarda e descarte controlado.** Tabela de temporalidade editável, bloqueio de descarte por obrigação ou processo em andamento, descarte com aprovação e registro.
4. **Assinatura eletrônica de documentos**, em dois degraus:
   - **4a. Assinatura avançada nativa.** Fluxo de assinatura sobre o `Documento GED`: um ou mais signatários, em ordem; autenticação do signatário (senha única por e-mail ou SMS); **dossiê de evidências** (quem, quando, IP, dispositivo, hash antes e depois); o PDF **selado** com o certificado institucional A1 e carimbo do tempo; e uma **página de verificação** do documento. Precisa de uma decisão: o que vale como autenticação do signatário.
   - **4b. Assinatura qualificada ICP-Brasil (PAdES)** com pyHanko, carimbo do tempo RFC 3161 e a política de assinatura da ICP-Brasil; **depende de conferir a política vigente (DOC-ICP-15.03) e de decidir como o signatário usa o certificado dele** (computador dele ou assinatura remota).
5. **Digitalização com validade (Decreto 10.278)**: captura com os metadados do Anexo II e assinatura do responsável. **Depende de obter o texto dos anexos.**
6. **OCR e busca de texto** por Paperless-ngx, opcional.

**Estrutura, igual ao resto do projeto:** regra pura em `erpnext_brasil/ged/` (cálculo de prazo, validação de metadados, hash, classificação; sem `frappe`) e camada fina em `integracao/` ligada ao `File` por `doc_events`; Custom Fields e DocTypes declarados em `setup/`; teste de bench por módulo ligado; fonte normativa citada no docstring com o grau de confiança.

## 6. Riscos e pontos em aberto

1. **Jurídico, muda custo:** prazo de guarda do XML (5 ou 11 anos), prazos trabalhistas e conteúdo dos anexos do Decreto 10.278. **Confirmar com o contador e com o texto oficial** antes de regra automática.
2. **Armazenamento:** onze anos de XML e PDF crescem. O **Chantilly** (previsão de esgotamento do disco, armazenamento por DocType) e o **Docker** (volume `sites`, opção de armazenamento externo) entram aqui.
3. **Imutabilidade real:** o app consegue impedir exclusão e detectar alteração (hash), mas não impõe armazenamento tipo WORM; isso depende da infraestrutura e do backup.
4. **Licença:** AGPL/GPL só por processo separado.
5. **Dependência do Frappe:** o `after_file_upload` e o gancho de permissão só existem na `develop`; qualquer plano que dependa deles espera uma versão futura.
6. **LGPD:** não pesquisada.
7. **Assinatura eletrônica:** a força probatória depende do nível e das **evidências guardadas**; assinatura avançada mal evidenciada vale pouco numa disputa. Atos que exigem forma especial não se resolvem com ela. Certificado do signatário não está no servidor.
8. **Escopo:** "GED" pode ir de guardar XML com prazo até digitalização com validade e fluxo de aprovação e assinatura. A recomendação começa no menor e mais valioso pedaço.

## 7. Fontes

- Frappe Drive: [repositório](https://github.com/frappe/drive) (arquivado; aviso de 2026-10-01), [Frappe Suite](https://github.com/frappe/suite), [artigo "Reimagining Frappe Drive"](https://frappe.io/blog/product-stories/reimagining-frappe-drive).
- Framework: PRs [frappe/frappe#38167](https://github.com/frappe/frappe/pull/38167) e [#40752](https://github.com/frappe/frappe/pull/40752); [artigo sobre o DMS do ERPNext (2015)](https://frappe.io/blog/erpnext-features/a-document-management-system-within-erpnext).
- Decreto 10.278/2020: [texto na Câmara](https://www2.camara.leg.br/legin/fed/decret/2020/decreto-10278-18-marco-2020-789857-publicacaooriginal-160146-pe.html), [nota técnica do TSE](https://www.tse.jus.br/institucional/gestao-documental/arquivos/nota-tecnica-n-1-2020), [Anexo II (fonte secundária)](https://modeloinicial.com.br/lei/DEC-10278-2020/anexo-ii-metadados-minimos-exigidos-@AII), [Arquivar](https://arquivar.com.br/blog/decreto-10-278-digitalizacao-documentos/).
- Ajuste SINIEF 2/2025: [Lacerda Diniz](https://lacerdadiniz.com.br/ajuste-sinief-02-2025/), [Contábeis](https://www.contabeis.com.br/artigos/70492/novo-ajuste-sinief-exige-guarda-de-documentos-fiscais-por-11-anos/), [Klaus Fiscal](https://klausfiscal.com.br/blog/novo-prazo-de-guarda-de-xml-entenda-o-que-muda-e-o-que-nao-muda-com-o-ajuste-sinief-no-2-2025).
- Documentos de RH: [Fenacon](https://fenacon.org.br/noticias/por-quanto-tempo-e-necessario-guardar-documentos-do-rh/).
- ICP-Brasil: [DOC-ICP-15.02](https://mailman.iti.gov.br/images/repositorio/legislacao/documentos-principais/15.2/DOC-ICP-15.02_-_Versao_3.0.pdf), [DOC-ICP-15.03](https://mailman.iti.gov.br/images/repositorio/legislacao/documentos-principais/15.3/DOC-ICP-15.03_-_Versao_7.2.pdf), [pyHanko](https://github.com/MatthiasValvekens/pyHanko).
- Assinatura eletrônica: [Canaltech sobre os níveis](https://canaltech.com.br/mercado/qual-e-a-diferenca-entre-assinatura-digital-avancada-e-qualificada/), [CNB-SP sobre o REsp do STJ](https://cnbsp.org.br/2025/02/13/artigo-stj-valida-uso-de-assinatura-eletronica-nao-certificada-pela-icp-brasil-por-jose-higidio/), [Barbieri Advogados](https://barbieriadvogados.com/assinatura-eletronica-validade-juridica/); código aberto: [Documenso](https://github.com/documenso/documenso), [DocuSeal](https://github.com/docusealco/docuseal), [OpenSign](https://github.com/opensignlabs/opensign).
- GEDs: [Paperless-ngx (API)](https://docs.paperless-ngx.com/api), [Mayan EDMS](https://gitlab.com/mayan-edms/mayan-edms).

## 8. Próximo passo sugerido

Se a direção for aprovada: abrir a mudança OpenSpec `ged-custodia-de-documentos` com a **fase 1** (a assinatura eletrônica entra na fase 4, depois que a custódia e os metadados existirem, porque a assinatura se apoia neles) (custódia do que o app já produz), que depende só de uma decisão: o prazo de guarda padrão do XML (sugestão: 11 anos até confirmação). As demais fases viram mudanças próprias, cada uma com a sua pendência jurídica nomeada.
