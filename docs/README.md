# Documentação

Referências por assunto. O que cabe numa docstring fica no código; aqui entra o que
precisa de tabela, cronograma ou comparação de alternativas.

| Documento | Assunto |
|---|---|
| [transmissoes-sincronas-e-assincronas.md](transmissoes-sincronas-e-assincronas.md) | Quais transmissões são assíncronas e onde a espera acontece: NF-e resolve o recibo dentro da chamada (~25 s), eventos são síncronos, o eSocial **não tem escapatória** (o envio só devolve protocolo), NFS-e nacional é síncrona — e o gap declarado de **nada rodar em job de segundo plano** |
| [gaps.md](gaps.md) | **Inventário vivo de gaps**: os de costura (código escrito e inalcançável), os módulos sem teste de bench, os itens declarados em `docs/` e as fontes a reconferir — com a ordem de pagamento e o método para refazer a varredura |
| [depreciacao.md](depreciacao.md) | Depreciação fiscal (RIR/2018, arts. 317-323): as cinco regras que um método linear genérico erra — base sempre no **custo de aquisição** e nunca no saldo residual, mês inteiro sem rateio por dias, bem usado pelo **maior** dos dois prazos, teto no custo "em qualquer hipótese", e início quando o bem entra em serviço; mais os coeficientes de turno 1,0/1,5/2,0 só para bens móveis |
| [nfse-estado.md](nfse-estado.md) | Levantamento da NFS-e: **não existe "emitir NFS-e" no singular** — Sefin Nacional (REST/DPS) e emissor municipal (SOAP/ABRASF) são caminhos incompatíveis, e Porto Velho **mantém o próprio**; identificadores de 45 e 53 posições lidos dos XSD oficiais, o `pattern` do XSD com `^`/`$` que em XML Schema são literais, e a decisão de não emitir ainda |
| [entrada-de-nfe.md](entrada-de-nfe.md) | Leitura do XML da NF-e do fornecedor: as duas quantidades (comercial × tributável, e por que devolver só uma faria o estoque bater e o SPED não), `Decimal` direto da string, conferência do destinatário que **falha alto** (nota de outra empresa gera crédito indevido) — e a recusa deliberada de criar itens, já que `cProd` é o código do fornecedor |
| [tropicalizacao-por-area.md](tropicalizacao-por-area.md) | Varredura das quatro áreas do site do ERPNext (contabilidade, aquisições, vendas, bancos) contra o que o app tem: o que é neutro, o que já está pronto, e os quatro gaps reais — **NFS-e** é o maior, o boleto estava pronto e sem dados bancários, faltam depreciação fiscal e leitura do XML de entrada |
| [arquitetura.md](arquitetura.md) | Camadas, por que `fiscal/` é puro, como testar sem bench |
| [desk-transicoes.md](desk-transicoes.md) | Transições/animações do Desk (identidade visual): evento `page-change` real do Frappe, só `opacity`/`transform`, `prefers-reduced-motion` |
| [chave-de-acesso.md](chave-de-acesso.md) | Layout das 44 posições, cálculo do DV, impacto do CNPJ alfanumérico |
| [cfop.md](cfop.md) | CFOP: determinação (não só validação de formato) para um núcleo de 16 códigos — compra/venda/devolução, mesmo/outro estado, importação/exportação, industrialização por encomenda |
| [pcp-estado.md](pcp-estado.md) | Levantamento do PCP/manufatura: módulo já existe no core, gap real em Subcontratação, e um campo quase reaproveitado errado para CFOP |
| [cfop-sugestao.md](cfop-sugestao.md) | Sugestão de CFOP em Pedidos/Subcontratação: dois campos novos no Item, `mesmo_estado` via UF, por que a sugestão nunca sobrescreve nada |
| [montagem-da-nfe.md](montagem-da-nfe.md) | Grupos `ide`, `emit`, `dest`; por que a chave é derivada; rejeição 897 |
| [reforma-tributaria.md](reforma-tributaria.md) | IBS, CBS e IS: cronograma, alíquota-teste, obrigatoriedade vigente |
| [transmissao-documento-fiscal.md](transmissao-documento-fiscal.md) | Opções de transporte (ACBrLib × ACBr API) e a fronteira de licença |
| [transporte-nativo-sefaz.md](transporte-nativo-sefaz.md) | Decisão de falar direto com a SEFAZ; tabela de autorizadores por UF (RO confirmado) |
| [cancelamento-e-carta-de-correcao.md](cancelamento-e-carta-de-correcao.md) | Cancelamento (110111) e CC-e (110110) acionáveis de uma tela: por que UF e CNPJ saem da chave de acesso e não da `Company`, por que o protocolo vem do `Transmissao Fiscal` da autorização, o teste que virou falso-positivo assim que um segundo botão citou o mesmo campo, e o painel de situação fiscal — por que "o registro mais recente" é a implementação errada (uma CC-e ressuscitaria uma nota cancelada) |
| [inutilizacao-nfe.md](inutilizacao-nfe.md) | Inutilização de faixa de numeração: por que é operação à parte, `@Id`, `cUF` × sigla |
| [multi-tenant.md](multi-tenant.md) | Multi-site (um banco por cliente) × multiempresa (uma `Company` por CNPJ), a distinção que decide tudo; como o Frappe resolve o site pelo `Host`; por que a configuração fiscal por `Company` faz multiempresa funcionar sem alterar o app; e o alerta do certificado A1 compartilhar a chave de criptografia do site |
| [hospedagem-demonstracao.md](hospedagem-demonstracao.md) | Opções gratuitas para **demonstrar** o app: Codespaces (recomendado), Gitpod, Oracle Always Free (cota cortada pela metade em jun/2026); por que Frappe Cloud e AWS free tier não servem; e por que demo não é produção fiscal |
| [como-rodar.md](como-rodar.md) | `scripts/subir.sh`: sobe MariaDB, Redis e o servidor sem sudo nem Docker (testado, HTTP 200); por que o datadir não pode ficar no `G:`, por que `currentsite.txt` não serve mais, e as dependências que se instalam sem privilégio |
| [logs-e-auditoria.md](logs-e-auditoria.md) | Log (diagnóstico) × auditoria (prestação de contas): `Version`/`track_changes` como trilha real, `Audit Trail` como relatório, `frappe.logger` × `frappe.log_error`, `Access Log` de exportações; e o alerta de que `Log Settings` pode expurgar o próprio `Version` sem aviso |
| [super-admin-e-multi-site.md](super-admin-e-multi-site.md) | Não existe super admin entre sites: `Administrator` é caso especial no código (pula toda verificação) e vale só para um site; `System Manager` para pessoas reais; administração de vários sites só pelo `bench --site all`, sem painel nem login unificado |
| [lowcode.md](lowcode.md) | O lowcode do Frappe (Customize Form, Client/Server Script, Workflow, Notification, Web Form) e a fronteira com este app: os 223 campos que o `after_migrate` reaplica desfazem edição feita pela tela, o prefixo `br_` **não** é critério suficiente (30 campos têm nome genérico), Server Script só liga pelo `common_site_config.json`; com exemplo completo de conferência fiscal em três passos |
| [relatorios.md](relatorios.md) | Os quatro tipos de `Report`: Builder (sem código), Query (SQL), Script (Python) e Custom; a checagem de SQL que recusa CTE por olhar só a primeira palavra, o fato de Query Report **ignorar permissão por registro**, o auto-`prepared_report` aos 15 s e os arquivos que `developer_mode` grava no app |
| [ambiente-dev-bench.md](ambiente-dev-bench.md) | Bench Frappe local (Windows 11 + WSL2 + Docker): decisões, obstáculos e como reproduzir; Memurai/MariaDB nativos como alternativa ainda não testada |
| [integracao-party-bench.md](integracao-party-bench.md) | Testes reais (bench) de `integracao/party.py`: achado de que a Company padrão do site pode mascarar `_pais_e_brasil()`, e um CNPJ com dígitos repetidos que passou na validação |
| [nfce-qrcode.md](nfce-qrcode.md) | QR Code da NFC-e: algoritmo do hash, `infNFeSupl`, CDATA, o que falta (contingência, tabela de UF) |
| [plano-de-contas.md](plano-de-contas.md) | Bloco contábil: grupos do balanço/DRE (Lei 6.404/76), amarração aos tributos, obstáculo de integração com o seletor de plano de contas do ERPNext |
| [lancamentos-contabeis.md](lancamentos-contabeis.md) | Partidas dobradas de uma venda: por que IPI não passa pela receita (DL 1.598/77), tratamento provisório de IBS/CBS e sua fase de teste sem recolhimento real |
| [apuracao-periodica.md](apuracao-periodica.md) | Fechamento periódico de ICMS/IPI: não cumulatividade (Art. 155/153 CF), saldo a recolher × saldo credor a transportar |
| [sped-fiscal.md](sped-fiscal.md) | EFD-ICMS/IPI: por que o livro em papel foi dispensado (Ajuste SINIEF 02/09), layout dos registros E110 (ICMS) e E520 (IPI), escopo sem ajuste de apuração |
| [sped-fiscal.md#e200e210e220](sped-fiscal.md) | ICMS-ST (E200/E210/E220), DIFAL/FCP (E300/E310/E311), Blocos 0/C/9 e o arquivo EFD completo montado de ponta a ponta; achados do `COD_AJ_APUR` de 8 caracteres, dos três tratamentos de estorno, do `IND_MOV` invertido, do `IND_FRT` que trocou de significado em 2012, e da contagem auto-referente do 9900 |
| [efd-contribuicoes.md](efd-contribuicoes.md) | EFD-Contribuições: registros M200/M210 (PIS) e M600/M610 (Cofins) — mesmo layout confirmado entre os dois, fórmulas citadas literalmente |
| [reinf-r2099.md](reinf-r2099.md) | R-2099 (Fechamento do EFD-Reinf): segundo gatilho da DCTFWeb, achado real de que não tem `transDCTFWeb` (diferente do S-1299), `ideEvento` genuinamente diferente do R-4020 |
| [reinf-r4020.md](reinf-r4020.md) | EFD-Reinf R-4020: retenções de IRRF/CSLL/Cofins/PIS-Pasep sobre pagamento a PJ, irmão do eSocial mas com `procEmi` de domínio diferente |
| [ecf-estado.md](ecf-estado.md) | Levantamento da ECF: dimensão confirmada (Leiaute 12, blocos 0/C/E/J/K/L/M/N/P/T/U/X/Y/S), a fatia mais barata (Bloco J, importado direto da ECD) |
| [ecf-bloco-j.md](ecf-bloco-j.md) | Bloco J da ECF: `J050`/`J051` reaproveitam `I050`/`I051` da ECD com o `REG` trocado, `J100` é tipo novo mínimo, `J053` fora de escopo |
| [ecf-bloco-k.md](ecf-bloco-k.md) | Bloco K da ECF: `K155`/`K156` reaproveitam a aritmética de `I155` da ECD, achado de indicadores D/C com nomes diferentes (`IND_DC_*`/`IND_VL_SLD_*`/`IND_VL_SLD_INICIAL`), nível de confiança declarado |
| [ecf-bloco-0.md](ecf-bloco-0.md) | Bloco 0 da ECF: `0000`/`0001`/`0030`/`0990` implementados, `0010`/`0020`/`0021` (40+ indicadores regulatórios) deliberadamente fora, wiring com `Company`/`Address` (achados dos campos `bairro`/número faltando no ERPNext nativo) |
| [ecf-bloco-p.md](ecf-bloco-p.md) | Bloco P da ECF (Lucro Presumido): dimensionado, núcleo mínimo (`P001`/`P990`); achado de que seis registros compartilham formato "código+valor" sem catálogo oficial verificado |
| [ecf-blocos-l-m-n.md](ecf-blocos-l-m-n.md) | Núcleo do Lucro Real da ECF, dimensionado: maioria dos registros depende de catálogo de códigos não verificado; Bloco M exige um domínio de controle fiscal (LALUR Parte B) inexistente no projeto |
| [precificacao-custos-rastreabilidade.md](precificacao-custos-rastreabilidade.md) | O erro de somar imposto ao custo em vez de dividir; margem × markup; rastreabilidade ligada ao `Batch`; e o gap real de custos (quais tributos integram o custo) |
| [compras-vendas-financeiro.md](compras-vendas-financeiro.md) | Auditoria de Compras/Vendas, contas a pagar/receber e livro caixa: o grupo `cobr` (duplicatas) era o elo faltante entre venda parcelada, NF-e e boleto; por que livro caixa não é gap |
| [estado-da-tropicalizacao.md](estado-da-tropicalizacao.md) | **Panorama geral**: o que está pronto, o que falta para uso real (DocTypes, tradução, interface, transmissão exercitada) e as pendências pontuais |
| [doctypes.md](doctypes.md) | DocTypes do app (`Transmissao Fiscal`, `Lote eSocial`): por que campo não guarda histórico, as invariantes puras, e por que o DocType exigiu um módulo novo em vez de entrar em `fiscal/` |
| [traducao.md](traducao.md) | O app já nasce em português; o que faltava era **corrigir** a tradução pt-BR do ERPNext (Cpf/cnpj, Ativo Fixo, preposição em maiúscula), e o mecanismo que permite sobrescrevê-la |
| [auditoria-padroes.md](auditoria-padroes.md) | Auditoria dos padrões declarados contra o código real: 135 violações de lint e 134 arquivos fora do formatador que nunca tinham sido executados; violações de responsabilidade única e de teste que passava pelo motivo errado, corrigidas |
| [frappe-algoritmo-de-busca.md](frappe-algoritmo-de-busca.md) | O Frappe **não** usa Jaro-Winkler: busca global é trigramas + Jaccard + Ratcliff-Obershelp; busca de link é `LIKE` sem aproximação nenhuma — lido no código-fonte |
| [leitor-codigo-e-alertas.md](leitor-codigo-e-alertas.md) | Leitor 1D lê a chave do DANFE, leitor 2D lê uma URL (não a chave); alerta de vencimento do certificado A1; aviso de documento aprovado em homologação; verificação de prontidão da EFD; e por que os prazos das obrigações **não** viraram alerta (fontes divergem) |
| [efd-configuracoes.md](efd-configuracoes.md) | Campos de configuração da EFD no ERPNext (perfil, atividade, versão do leiaute, SUFRAMA da Company; tipo do item, gênero e EX da TIPI no Item) e por que `TIPO_ITEM` não podia reaproveitar campo existente |
| [certificado-a1-configuracao.md](certificado-a1-configuracao.md) | Certificado A1 e ambiente SEFAZ configuráveis em `Company`; o que deliberadamente não virou configurável (tabelas de autorizador por UF) |
| [docker-compose.md](docker-compose.md) | `Dockerfile`/`docker-compose.yml` no padrão `frappe_docker` — caminho alternativo ao bench WSL2, não build-testado nesta sessão |
| [versoes-frappe-erpnext.md](versoes-frappe-erpnext.md) | `version-16` é a versão estável mais recente (Docker/compose apontam para ela); o bench de teste real continua em `version-15`, divergência declarada |
| [instalacao.md](instalacao.md) | Guia técnico de instalação — bench nativo (recomendado) e Docker/compose (alternativo) |
| [ecd.md](ecd.md) | ECD (SPED Contábil): registros I050/I051/I200/I250/I150/I155, numeração-padrão de contas, a pegadinha do `COD_NAT` do Patrimônio Líquido |
| [sped-texto.md](sped-texto.md) | Serialização de linha pipe-delimited do SPED, comum a EFD e ECD; a correção do formato de data (`DDMMAAAA`, sem separador) |
| [rh-estado-hrms.md](rh-estado-hrms.md) | Bloco RH: estado do `frappe/hrms`, confirmação de que o Brasil não existe nem lá nem no ERPNext, e o hook `regional_overrides` que permite tropicalizar sem fork |
| [rh-inss.md](rh-inss.md) | Contribuição previdenciária do empregado (tabela 2026), verificada faixa a faixa contra o método da parcela a deduzir |
| [rh-irrf.md](rh-irrf.md) | Imposto de Renda Retido na Fonte na folha: tabela 2026, o redutor da Lei 15.270/2025, os 5 exemplos oficiais da Receita Federal reproduzidos como teste |
| [rh-fgts.md](rh-fgts.md) | FGTS: depósito mensal (não é desconto do empregado), multa rescisória por motivo de desligamento, o que fica de fora (prazo, saque) |
| [rh-integracao-salary-slip.md](rh-integracao-salary-slip.md) | Primeira integração real com o `hrms`: hook `regional_overrides`, INSS/IRRF no `Salary Slip`, por que FGTS fica de fora, estado de verificação sem bench |
| [rh-estado-esocial.md](rh-estado-esocial.md) | Levantamento de estado do eSocial: leiaute S-1.3, grupos de evento, arquitetura de transmissão, por que é maior que a NF-e e a decisão de escopo pendente |
| [rh-esocial-s1200.md](rh-esocial-s1200.md) | S-1200 (remuneração): árvore completa do evento verificada contra XSD de terceiro, ponte com INSS/IRRF, grupos raros fora de escopo |
| [rh-esocial-lote.md](rh-esocial-lote.md) | Camada de transporte do eSocial: envelope de lote, endpoints por serviço/ambiente, limite de 50 eventos (regra de negócio, não do XSD), o que falta (assinatura, envio) |
| [rh-esocial-retorno.md](rh-esocial-retorno.md) | Leitura da resposta de envio/processamento de lote: códigos de cdResposta confirmados, tem_erro vs. sucesso, eventos_com_erro |
| [rh-esocial-assinatura.md](rh-esocial-assinatura.md) | Assinatura XMLDSig do eSocial: mesma canonicalização da NF-e, hash SHA-256 (não SHA-1) provado com verificação criptográfica real |
| [rh-esocial-serializacao.md](rh-esocial-serializacao.md) | Árvore do S-1200 serializada em XML de verdade (provado com lxml), reaproveitando `para_xml`; a descoberta do gap `indApuracao` no processo |
| [rh-esocial-montagem.md](rh-esocial-montagem.md) | Orquestração serializar→assinar→mesclar→serializar; assinador injetado (continua puro); prova ponta a ponta com assinatura real verificada |
| [rh-esocial-soap.md](rh-esocial-soap.md) | Envelope SOAP do eSocial: SOAP 1.1 (não 1.2 como a NF-e), wrapper por serviço, o que falta para o envio HTTP de verdade |
| [rh-esocial-consulta.md](rh-esocial-consulta.md) | Conteúdo de `<consulta>`: formato exato do `protocoloEnvio` (agente/ambiente/sequencial), três domínios de "ambiente" que não são o mesmo conceito |
| [rh-esocial-id.md](rh-esocial-id.md) | Geração do `Id` de 36 caracteres do evento: composição confirmada, zeros à direita (não à esquerda) e por quê |
| [rh-esocial-s1010.md](rh-esocial-s1010.md) | S-1010 (Tabela de Rubricas): a peça que falta para o S-1200 funcionar, quatro tabelas de incidência confirmadas no XSD |
| [rh-esocial-s2200.md](rh-esocial-s2200.md) | S-2200 (Admissão): pré-requisito do S-1200, três níveis de confiança por campo (enumeração literal, citada, só formato) declarados explicitamente |
| [rh-esocial-s1299.md](rh-esocial-s1299.md) | S-1299 (Fechamento dos Eventos Periódicos): achado de que a DCTFWeb não é um arquivo que o contribuinte constrói — é o `transDCTFWeb` deste evento que a dispara; `ideEvento` genuinamente diferente do S-1200 |
| [rh-esocial-s2299.md](rh-esocial-s2299.md) | S-2299 (Desligamento): reaproveita de verdade o `DmDev` do S-1200, três variações de `procEmi` confirmadas, `mtvDeslig`/Tabela 19 genuinamente não localizada |
| [rh-esocial-s1000.md](rh-esocial-s1000.md) | S-1000 (Informações do Empregador): `ideEvento` mais simples de todos (sem indRetif/nrRecibo), operação inclusão/alteração/exclusão como `xs:choice` real do XSD |
| [rh-esocial-transmissao.md](rh-esocial-transmissao.md) | Envio HTTP de verdade do eSocial: `montar_xml_lote`, leitura de retorno, `transmissao_esocial.py` espelhando a NF-e; resolve a ressalva antiga sobre o wrapper `<consulta>` |
| [boleto.md](boleto.md) | Código de barras/linha digitável FEBRABAN (validado contra exemplo real) e leitura do CNAB 400 de retorno para conciliação |
| [cnab240-retorno.md](cnab240-retorno.md) | Sucessor do CNAB 400: Segmentos T/U do retorno, posições confirmadas contra dois bancos independentes, `codigo_movimento` como hipótese de trabalho |
| [gia-nao-e-gap.md](gia-nao-e-gap.md) | GIA investigada e descartada: extinção nacional em curso (SP, MG, RJ já dispensaram, migraram para EFD-ICMS/IPI que este projeto já implementa) |
| [destda.md](destda.md) | DeSTDA: retomada de frente bloqueada com fonte nova (documentação de ERP comercial), nível de confiança declarado, registros `0000`/`G605`/`G615`/`G625`/encerramento |
| [pix.md](pix.md) | Payload Pix (BR Code/"Copia e Cola"): TLV + CRC16 verificado contra vetor padrão universal, gap real no app `payments`, PDV ainda sem fio puxado |
| [cte-estado.md](cte-estado.md) | Levantamento do CT-e: estrutura de `TCTe` verificada por grep local (não resumo de ferramenta, que alucinou 3x), `imp` como `xs:choice` de 7 CSTs, `ICMSUFFim` como equivalente do DIFAL da NF-e |
| [cte-icms-uf-fim.md](cte-icms-uf-fim.md) | Primeiro código de CT-e: grupo `ICMSUFFim`, reuso direto de `calcular_difal`, por que o CFOP de transporte ficou de fora |
| [cfop-transporte.md](cfop-transporte.md) | CFOP de prestação de serviço de transporte (`ide.CFOP` do CT-e): oito perfis de tomador, nível de confiança declarado (só fonte secundária cruzada, sem o Ajuste SINIEF localizado) |
| [cte-infnfe.md](cte-infnfe.md) | Grupo `infDoc/infNFe` do CT-e: ponte com a NF-e transportada (dado que o MDF-e vai precisar depois), reuso de `ler_chave` da NF-e, recusa de chave que não seja modelo 55 |
| [cte-modal-rodoviario.md](cte-modal-rodoviario.md) | Modal rodoviário do CT-e: só RNTRC (com a pegadinha do valor `ISENTO`) e ordens de coleta — veículo/motorista é responsabilidade do MDF-e, não do CT-e |
| [cte-assinatura.md](cte-assinatura.md) | Assinatura digital do CT-e: reuso total de `assinatura.py` da NF-e, confirmado (não suposto) por código de produção do `sped-common`/`sped-cte`, não pelo texto do Ajuste SINIEF (não localizado) |
| [cte-toma.md](cte-toma.md) | Tomador do serviço do CT-e: `toma3` (reaproveita parte já citada) vs `toma4` (cadastro completo, ordem de campos estrita do `xs:sequence`) |
| [cte-evento-comprovante-entrega.md](cte-evento-comprovante-entrega.md) | Comprovante de entrega do CT-e: código próprio sem equivalente na NF-e, `hashEntrega` é um SHA-1+Base64 real calculado a partir da chave |
| [cte-evento-correcao.md](cte-evento-correcao.md) | Carta de correção do CT-e: achado real de que não é texto livre (é lista estruturada campo a campo), base legal diferente da NF-e |
| [cte-evento-cancelamento.md](cte-evento-cancelamento.md) | Evento de cancelamento do CT-e: achados de que a justificativa vai até 255 (não 256) e o `@Id` tem 53 dígitos (não 52) |
| [cte-evento-epec.md](cte-evento-epec.md) | EPEC do CT-e: achado real de que o `toma4` não é o `toma4` real da `ide` (aceita qualquer papel, sem `xNome`/`enderToma`), e `tpCTe` fixo em `"0"` |
| [cte-evento-cancelamento-comprovante-entrega.md](cte-evento-cancelamento-comprovante-entrega.md) | Cancelamento do comprovante de entrega do CT-e: achado real de que "CE" no nome do arquivo é Comprovante de Entrega, não Carta de Correção |
| [cte-evento-insucesso-entrega.md](cte-evento-insucesso-entrega.md) | Insucesso na entrega do CT-e: achados de que `xJustMotivo` usa limite 256 (não 255 como o resto do CT-e) e o hash é opcional (não obrigatório como no comprovante de entrega) |
| [cte-evento-cancelamento-insucesso-entrega.md](cte-evento-cancelamento-insucesso-entrega.md) | Cancelamento do insucesso na entrega do CT-e: estruturalmente idêntico ao cancelamento do comprovante de entrega, reaproveitado via função privada comum |
| [cte-evento-gtv.md](cte-evento-gtv.md) | Informações da GTV do CT-e: achado real de que `descEvento` aceita duas grafias (`"Informações"`/`"Informacoes"`), reuso de `validar_rntrc` |
| [cte-evento-prestacao-desacordo.md](cte-evento-prestacao-desacordo.md) | Prestação em desacordo do CT-e e seu cancelamento: achado real do primeiro `tpEvento` fora do padrão `110xxx` (`610110`/`610111`), e do cancelamento sem `nProt` do CT-e |
| [cte-evento-registro-multimodal.md](cte-evento-registro-multimodal.md) | Registro multimodal do CT-e (último dos onze eventos): achado real de que `nDoc` não é validado como chave de acesso apesar do comprimento coincidir |
| [cte-orquestracao.md](cte-orquestracao.md) | `montar_ide`/`montar_cte`: os 30 campos de `ide` verificados e ordenados contra o XSD, composição com tomador/CFOP/assinatura já prontos, prova de ponta a ponta |
| [mdfe-estado.md](mdfe-estado.md) | Levantamento do MDF-e: `ide` bem mais simples que o do CT-e, achado de que `modal`/`procEmi` divergem entre os dois documentos, veículo/motorista mora no MDF-e (não no CT-e) |
| [mdfe-infdoc.md](mdfe-infdoc.md) | `infDoc` do MDF-e: referências a CT-e/NF-e agrupadas por município de descarga (não lista plana como no CT-e), `chave_acesso.MODELOS` ganha `"57"`/`"58"` |
| [mdfe-modal-rodoviario.md](mdfe-modal-rodoviario.md) | Modal rodoviário do MDF-e: veículo/motorista (espelho invertido do CT-e), `RNTRC` reaproveitado, `tara` sem zero à esquerda |
| [mdfe-assinatura.md](mdfe-assinatura.md) | Assinatura digital do MDF-e: reuso total de `assinatura.py`, confirmado por código de produção (`signMDFe`/`sped-mdfe`), verificado de novo apesar do CT-e já ter sido verificado — família diverge às vezes |
| [mdfe-orquestracao.md](mdfe-orquestracao.md) | `montar_ide`/`montar_mdfe`: os 21 campos verificados, lição do `cDV` do CT-e aplicada desde o início (não corrigida depois), confirmação de que não há `CFOP`/`natOp` |
| [mdfe-tot-lacres.md](mdfe-tot-lacres.md) | `tot` (totalizadores da carga) e `lacres` (lista simples de números de lacre) do MDF-e |
| [mdfe-emit-seg-prodpred.md](mdfe-emit-seg-prodpred.md) | `emit` (aceita CNPJ ou CPF, diferente da NF-e), `seg` (seguro da carga) e `prodPred` (12 categorias da Resolução ANTT 5.849/2019) do MDF-e |
| [integracao-cte-extracao.md](integracao-cte-extracao.md) | Extração real `Shipment` → referências fiscais: município vem da viagem, não de cada nota; falha alta quando falta o código IBGE |
| [integracao-cte-frete.md](integracao-cte-frete.md) | Chave de CT-e do lado de quem contrata o transporte: achado real de que `Shipment` não tem link para `Purchase Invoice`, extração opera sobre a fatura já identificada |
| [cte-mdfe-autorizadores.md](cte-mdfe-autorizadores.md) | Autorizador/webservice por UF de CT-e (4 grupos, diverge da NF-e mesmo para UFs com webservice próprio) e MDF-e (um único autorizador nacional) |
| [integracao-chave-acesso.md](integracao-chave-acesso.md) | Campo `br_chave_acesso`/`br_protocolo_autorizacao`: fecha o gap identificado no mapeamento CT-e/MDF-e, validado mas sem transmissão real ligada ainda |
| [integracao-cte-mapeamento.md](integracao-cte-mapeamento.md) | Primeiro passo de integração do CT-e/MDF-e: agrupamento de referências por município, achado de que falta um campo básico (chave de acesso persistida) antes de ir além |
| [mdfe-infmdfe.md](mdfe-infmdfe.md) | Orquestrador de nível mais alto do MDF-e: `infModal` é um ponto de extensão `xs:any`, `montar_infmdfe` compõe todos os grupos na ordem do XSD, prova de ponta a ponta completa |
| [mdfe-evento-cancelamento.md](mdfe-evento-cancelamento.md) | Evento de cancelamento do MDF-e: converge com a forma do CT-e (não da NF-e), mesmo `tpEvento` 110111 dos três documentos, achado do `@Id` com duas larguras toleradas |
| [mdfe-evento-encerramento.md](mdfe-evento-encerramento.md) | Evento de encerramento do MDF-e: achado real de que `cUF` aceita `"99"` para Exterior (`TCodUfIBGE_EX`, não a tabela normal de 27 UFs) |
| [mdfe-evento-inclusao-condutor.md](mdfe-evento-inclusao-condutor.md) | Evento de inclusão de condutor do MDF-e: reuso direto de `fiscal.mdfe_rodoviario.Condutor`, achado de grafia sem acento única |
| [mdfe-evento-inclusao-dfe.md](mdfe-evento-inclusao-dfe.md) | Evento de inclusão de DF-e do MDF-e: nome do arquivo diverge do elemento raiz, e o evento só aceita NF-e (nunca CT-e) — diferente do `infDoc` da orquestração principal |
| [mdfe-evento-confirmacao-servico.md](mdfe-evento-confirmacao-servico.md) | Evento de confirmação do serviço do MDF-e: o mais simples da frente, achado de numeração não contígua/não alfabética |
| [mdfe-evento-pagamento-operacao.md](mdfe-evento-pagamento-operacao.md) | Evento de pagamento da operação do MDF-e: o mais complexo da frente, três formas de identificar o responsável (CPF/CNPJ/estrangeiro), achado de inconsistência no XSD do `idEstrangeiro` |
| [mdfe-evento-alteracao-pagamento.md](mdfe-evento-alteracao-pagamento.md) | Evento de alteração do pagamento do MDF-e: reuso direto e confirmado do `infPag` do pagamento da operação, sem `infViagens` |

## Convenções que valem em todo o código

**Idioma.** Tudo em pt-BR — rótulos, mensagens, docstrings, nomes de função. Termos
fiscais brasileiros (CNPJ, NCM, CFOP, CSOSN) são nomes próprios e não se traduzem.

**Alíquota é fração.** `0.18`, nunca `18`. Passar percentual levanta erro. A conversão
para percentual acontece só na fronteira do XML e na leitura de campos do ERPNext, e cada
fronteira tem teste.

**Dinheiro é `Decimal` com `ROUND_HALF_UP`.** O padrão do Python é `ROUND_HALF_EVEN`, que
leva `0.125` para `0.12` quando o documento fiscal espera `0.13`.

**Fonte normativa citada.** Toda constante de origem legal registra onde foi lida. Em
domínio fiscal a regra muda por lei, e sem a fonte ninguém reverifica meses depois.

**Desvio deliberado é documentado como desvio.** Onde a implementação diverge de uma
referência oficial — como a recusa de CNPJ numérico repetido, que o calculador da Receita
aceita —, a divergência é explicada e testada, nunca escondida.
