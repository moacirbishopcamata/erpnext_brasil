## Why

Duas lacunas de emissão fiscal seguem abertas e o app só entrega a metade de cada uma:

- **NFS-e**: existe apenas `fiscal/documento/identificador_nfse.py` (identificadores da DPS e da NFS-e). Não há DPS, assinatura, transmissão, estado nem tela. A decisão registrada em `docs/nfse-estado.md` (2026-09-06) foi não emitir ainda, porque o caminho nacional "serviria só ao MEI" e o municipal de Porto Velho dependia de manual não obtido. **Essa premissa mudou**: a Resolução CGSN nº 191/2026 torna a NFS-e de padrão nacional obrigatória para ME e EPP optantes do Simples Nacional a partir de **1º/11/2026**, inclusive em município com sistema próprio (fonte secundária, confirmada por mais de um veículo e por um PDF da resolução no site do governo do DF; o texto no Planalto/CGSN ainda não foi lido). O caminho nacional passa a servir justamente o público que usa ERP.
- **Modais de transporte**: CT-e (modelo 57) e MDF-e (modelo 58) só montam o **rodoviário**. `fiscal/cte_montagem.py` e `fiscal/mdfe_montagem.py` recusam qualquer outro modal com "só o modal rodoviário está implementado", embora o Custom Field `br_modal_cte` já ofereça aéreo, aquaviário, ferroviário, dutoviário e multimodal ao usuário. O MDF-e só existe com `rodo` (`docs/mdfe-estado.md`, linha 124).

## What Changes

- **NFS-e pelo caminho nacional primeiro** (as fontes primárias estão em mãos: XSD v1.01 e manual da API v1.2): DPS a partir de fatura de serviços, assinatura A1 reaproveitada, transmissão REST síncrona (novo; todo o transporte atual é SOAP), NFS-e e rejeição gravadas em estado persistido, sem reenvio de nota autorizada, e cancelamento como evento.
- **Caminho por município e regime**: a emissão escolhe nacional ou municipal conforme o prestador e **recusa com motivo** o caminho ainda não implementado, em vez de enviar pelo errado.
- **Caminho municipal de Porto Velho (ABRASF)** só depois de obter o manual/Nota Técnica do município; se não vier, a change registra o bloqueio e o município segue recusado. Quem não é Simples ME/EPP (Lucro Presumido ou Real) emite por ele.
- **Tabelas oficiais** dos anexos A (municípios), B (NBS e lista nacional de serviços) e C (INDOP IBS/CBS) como dado versionado com fonte e hash, e os campos de IBS/CBS que o leiaute exige.
- **Modais aquaviário, aéreo e ferroviário no CT-e e no MDF-e**, nessa ordem de prioridade, cada um entregável sozinho: módulo puro do modal, Custom Fields por modal declarados em `setup/`, montagem, validação contra o XSD oficial e a recusa de "só rodoviário" removida para o modal pronto. Dutoviário e multimodal do CT-e ficam fora, declarados.
- **Aplicação ao módulo de saúde**:
  - **NFS-e de serviços de saúde** (clínica, laboratório e hospital privados): o enquadramento na lista nacional vem de tabela oficial, não de palavra-chave (a fonte consultada aponta os itens 4.02 e 4.03 da LC 116/2003, mas é de um único site comercial, a confirmar no texto oficial); a **discriminação do serviço não carrega dado clínico** (diagnóstico, CID, resultado de exame), por ser dado de saúde sob a LGPD; o tomador é o paciente (pessoa física) ou a operadora de saúde (pessoa jurídica), e a emissão distingue os dois; **atendimento sem cobrança (SUS, dispensação gratuita) não gera NFS-e**.
  - **Modal aquaviário** atende o transporte fluvial de amostras, insumos e medicamentos aos distritos e ao Baixo Madeira, que o módulo de armazém do laboratório SUS já trata como "despacho por rota (inclusive fluvial)". Se o MDF-e é **obrigatório** nesse transporte (intramunicipal, órgão público) depende da legislação de Rondônia: a change registra o que o manual da Sefin-RO diz, não cria regra própria, e o MDF-e continua sendo uma emissão **acionada pelo usuário**, nunca automática.
  - **Modais aéreo e ferroviário** servem sobretudo a transportadoras; para o hospital ou laboratório, o CT-e desses modais costuma ser **recebido** do transportador, e a referência a ele pela chave (`cte_extracao`) já independe do modal (verificado no código).
- **Sem prova de autorização**: nada é enviado à SEFAZ nem à Sefin de verdade nesta change sem certificado A1 e ambiente de homologação/produção restrita; o que não rodar fica declarado como não executado.

## Capabilities

### New Capabilities

- `fiscal/nfse-operacional`: emissão, consulta de desfecho e cancelamento da NFS-e a partir de fatura de serviços, com escolha de caminho por município e regime, tratamento dos serviços de saúde e estado persistido.

### Modified Capabilities

- `fiscal/cte-operacional`: acrescenta a emissão do CT-e nos modais aquaviário, aéreo e ferroviário.
- `fiscal/mdfe-operacional`: acrescenta a emissão do MDF-e nos modais aquaviário, aéreo e ferroviário.

## Impact

- Código novo: `fiscal/documento/` (DPS, tipos do leiaute nacional, evento), `fiscal/` (módulos de modal para CT-e e MDF-e); `integracao/` (transporte REST, emissão a partir da fatura, modais), cada módulo abaixo de 320 linhas.
- Custom Fields em `setup/` para os dados de cada modal e para o caminho da NFS-e na empresa; DocType ou campos de estado da NFS-e; testes de bench com `MODULOS_COBERTOS`.
- Dados versionados: anexos A, B e C da NFS-e nacional; XSD dos modais fora do repositório, testes que dependem deles pulam sem a variável de ambiente (padrão já usado para a lista do IBGE).
- Dependência externa nova: cliente HTTP/REST com TLS mútuo, reaproveitando o certificado A1 existente.
- Risco regulatório: leiaute da NFS-e nacional, Notas Técnicas do CGNFS-e e a reforma tributária mudam durante a implementação; cada documento gerado fixa versão e data da fonte.
