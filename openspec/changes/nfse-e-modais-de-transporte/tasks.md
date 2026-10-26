## 1. Fontes e confirmações

- [ ] 1.1 Baixar o pacote vigente dos XSD da NFS-e nacional e o manual da API em `gov.br/nfse`, para um diretório novo e vazio fora do repositório; conferir a versão contra as Notas Técnicas do CGNFS-e e registrar URL, data, versão e hash em `docs/nfse-fontes.md` — verificar abrindo o documento e recalculando um hash.
- [ ] 1.2 Ler no texto oficial a Resolução CGSN nº 191/2026 (e a 190) e registrar a quem obriga, desde quando, o que exclui (operações só de ICMS) e a data de efeito dos campos IBS/CBS para o Simples — verificar com a citação dos artigos em `docs/nfse-fontes.md`; divergência da fonte secundária vira aviso.
- [ ] 1.3 Confirmar na página oficial da Prefeitura de Porto Velho e da Semec o estado do convênio com o emissor nacional e a existência do manual/Nota Técnica do leiaute municipal, e pedir o documento se não estiver público — verificar com a URL e a data de cada afirmação, ou com a declaração "manual não obtido".
- [ ] 1.4 Baixar os XSD do CT-e 4.00 e do MDF-e 3.00 (modais aéreo, aquaviário e ferroviário) do Portal Nacional, para diretório fora do repositório, e ler cada arquivo inteiro do disco — verificar com `docs/cte-modais.md` listando, por modal, os grupos e os campos obrigatórios com a linha do XSD.
- [ ] 1.5 Ler o manual de orientação da Sefin-RO sobre a obrigatoriedade do MDF-e e o texto do Ajuste SINIEF 21/2010, e registrar o que vale para transporte intramunicipal e para órgão público em Rondônia — verificar com `docs/mdfe-obrigatoriedade.md` citando cláusula e página; nenhuma regra é codificada a partir disso.
- [ ] 1.6 Conferir no texto oficial da LC 116/2003 os itens 4.01 a 4.23 e, na tabela do Anexo B, o desdobro nacional dos serviços de saúde, incluindo a sobreposição entre 4.02 e 4.03 — verificar com a tabela em `docs/nfse-fontes.md` citando a fonte primária.
- [ ] 1.7 Confirmar o ambiente de teste do emissor nacional (Produção Restrita) e os requisitos de certificado e de credenciamento — verificar com a URL e a data em `docs/nfse-fontes.md`.

## 2. Inventário do que existe

- [ ] 2.1 Listar os campos de `Company` e de `Sales Invoice` que já respondem município, regime do Simples, CNAE e item de serviço, e o que falta — verificar com a lista campo a campo e a decisão de reaproveitar ou declarar em `setup/`.
- [ ] 2.2 Ler o app `healthcare` 16.6.1 instalado e registrar como o faturamento acontece (documento, `Item`, pagador) — verificar com arquivo e linha em `docs/nfse-saude.md` (mesma leitura da tarefa 2.2 de `finalizar-ecf`; fazer uma vez só).
- [ ] 2.3 Listar os Custom Fields de CT-e e MDF-e que existem por modal e o que `cte_documento.py`/`mdfe_documento.py` leem — verificar com a lista e a confirmação de que cada campo lido está declarado em `setup/`.

## 3. NFS-e: dados de apoio e caminho

- [ ] 3.1 Incorporar os anexos A, B e C como dado versionado com fonte e hash, e o leitor que recusa código fora da tabela — verificar com testes de código inexistente, de município inexistente e de recálculo do hash dos arquivos de dados.
- [ ] 3.2 Implementar a função pura que decide o caminho (nacional, municipal ou desconhecido) a partir de município, regime e data, com a fonte da regra na docstring — verificar com teste por regime, um para data anterior e outra posterior a 1º/11/2026, e um para caminho desconhecido.
- [ ] 3.3 Declarar em `setup/` o campo de caminho de emissão e o de série da DPS na empresa — verificar com bench: o campo existe após `migrate` e é lido pela integração.

## 4. NFS-e: DPS, assinatura e transporte

- [ ] 4.1 Modelar os tipos do leiaute nacional que a DPS usa (prestador, tomador, serviço, valores, tributação, IBS/CBS) e a montagem do XML da DPS — verificar com teste que monta a DPS de um exemplo e a compara à estrutura do XSD (teste de conformidade pula sem o diretório dos XSD e roda com ele).
- [ ] 4.2 Reaproveitar a assinatura A1 para a DPS e conferir o resultado — verificar com teste de ida e volta (assinar, verificar a assinatura) e com o XSD, se disponível.
- [ ] 4.3 Implementar o `Protocol` de transporte de NFS-e e a implementação REST com TLS mútuo em `integracao/transporte_nfse.py` — verificar com teste usando transporte falso (autorizada, rejeitada, indisponível) e com teste de que o erro não contém o conteúdo do certificado.
- [ ] 4.4 Implementar o estado persistido da NFS-e (DocType ou campos), gravado em todos os desfechos, e a regra de não reenviar nota autorizada — verificar com bench: gravar, reler por outro caminho e comparar; segundo pedido de emissão não transmite.
- [ ] 4.5 Implementar `emitir_nfse` a partir da `Sales Invoice` de serviços (numeração, montagem, assinatura, transmissão, estado), com `has_permission` antes de qualquer leitura — verificar com `tests/test_whitelist_com_permissao.py` verde e teste de bench em que usuário sem papel recebe `PermissionError`.
- [ ] 4.6 Implementar o cancelamento como evento (`pedRegEvento`), só de nota autorizada — verificar com testes de cancelamento autorizado, de nota rejeitada e de nota já cancelada.
- [ ] 4.7 Expor emissão e cancelamento na fatura de serviços, com o estado decidindo os botões — verificar manualmente no bench e registrar o resultado em `docs/nfse-estado.md`.

## 5. NFS-e: saúde

- [ ] 5.1 Implementar o mapeamento configurável de item de serviço para o código da lista nacional, sem heurística, com recusa de item sem código — verificar com teste de item mapeado e de item sem mapeamento.
- [ ] 5.2 Implementar a discriminação por modelo fixo (item + competência) e o teste que passa um atendimento com diagnóstico e resultado e confere a ausência deles na NFS-e — verificar com o teste verde.
- [ ] 5.3 Implementar a distinção paciente × operadora a partir do pagador da fatura e a recusa de tomador não identificável — verificar com os dois cenários e o de tomador ausente.
- [ ] 5.4 Implementar a recusa de emissão para atendimento sem cobrança (SUS, dispensação gratuita) — verificar com teste em que nenhum registro de NFS-e é criado.

## 6. NFS-e: caminho municipal de Porto Velho (condicionado à tarefa 1.3)

- [ ] 6.1 Se o manual do município foi obtido: ler o leiaute municipal e registrar divergências em relação ao ABRASF padrão, e implementar montagem e transporte SOAP municipal sobre as mesmas portas — verificar com testes de montagem contra o exemplo do manual e transporte falso. Se não foi obtido: registrar "bloqueado: manual não obtido" em `docs/nfse-estado.md` e `docs/gaps.md` e manter a recusa do município — verificar pelo registro nos dois documentos.

## 7. CT-e e MDF-e: aquaviário

- [ ] 7.1 Implementar o módulo puro do modal aquaviário do CT-e conforme o XSD lido na tarefa 1.4 — verificar com testes de campo obrigatório ausente, de formato inválido e de montagem do grupo.
- [ ] 7.2 Implementar o módulo puro do modal aquaviário do MDF-e (embarcação e viagem) — verificar com os mesmos três tipos de teste.
- [ ] 7.3 Declarar em `setup/` os Custom Fields do modal aquaviário (com `depends_on` pelo modal) em `Sales Invoice`/documento de transporte e em `Shipment` — verificar com bench: os campos existem após `migrate` e as integrações os leem.
- [ ] 7.4 Ligar o modal à montagem do CT-e e do MDF-e, substituindo a recusa de "só rodoviário" por recusa do modal não implementado — verificar com teste que o rodoviário não mudou e outro que dutoviário e multimodal ainda recusam com mensagem.
- [ ] 7.5 Teste de ponta a ponta do aquaviário (CT-e e MDF-e) assinado e, com XSD disponível, validado contra o leiaute — verificar com o teste verde e com a execução da conformidade registrada, ou "pulado, sem XSD" declarado.

## 8. CT-e e MDF-e: aéreo e ferroviário

- [ ] 8.1 Repetir 7.1 a 7.5 para o modal aéreo (CT-e e MDF-e) — verificar com a mesma bateria de testes e o registro de conformidade.
- [ ] 8.2 Repetir 7.1 a 7.5 para o modal ferroviário (CT-e e MDF-e) — verificar com a mesma bateria de testes e o registro de conformidade.

## 9. Fechamento

- [ ] 9.1 Garantir por teste que despacho de armazém não emite MDF-e (a emissão só por ação do usuário) — verificar com teste que despacha uma carga por rota fluvial e confere que nenhum MDF-e foi criado.
- [ ] 9.2 Atualizar `docs/nfse-estado.md` (premissa de 2026-09 superada pela Resolução CGSN nº 191), `docs/mdfe-estado.md`, `docs/cte-estado.md`, `docs/gaps.md`, `docs/README.md` e `CLAUDE.md` — verificar com `ruff` limpo, suíte pura verde e links conferidos por script.
- [ ] 9.3 Rodar `python scripts/cobertura_de_bench.py` e os testes de bench dos módulos novos, e registrar que nenhuma autorização real foi feita sem certificado A1 e ambiente de teste — verificar pela saída anexada ao documento de estado.
