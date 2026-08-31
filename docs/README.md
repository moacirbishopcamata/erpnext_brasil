# Documentação

Referências por assunto. O que cabe numa docstring fica no código; aqui entra o que
precisa de tabela, cronograma ou comparação de alternativas.

| Documento | Assunto |
|---|---|
| [arquitetura.md](arquitetura.md) | Camadas, por que `fiscal/` é puro, como testar sem bench |
| [chave-de-acesso.md](chave-de-acesso.md) | Layout das 44 posições, cálculo do DV, impacto do CNPJ alfanumérico |
| [montagem-da-nfe.md](montagem-da-nfe.md) | Grupos `ide`, `emit`, `dest`; por que a chave é derivada; rejeição 897 |
| [reforma-tributaria.md](reforma-tributaria.md) | IBS, CBS e IS: cronograma, alíquota-teste, obrigatoriedade vigente |
| [transmissao-documento-fiscal.md](transmissao-documento-fiscal.md) | Opções de transporte (ACBrLib × ACBr API) e a fronteira de licença |
| [transporte-nativo-sefaz.md](transporte-nativo-sefaz.md) | Decisão de falar direto com a SEFAZ; tabela de autorizadores por UF (RO confirmado) |
| [inutilizacao-nfe.md](inutilizacao-nfe.md) | Inutilização de faixa de numeração: por que é operação à parte, `@Id`, `cUF` × sigla |
| [ambiente-dev-bench.md](ambiente-dev-bench.md) | Bench Frappe local (Windows 11 + WSL2 + Docker): decisões, obstáculos e como reproduzir; Memurai/MariaDB nativos como alternativa ainda não testada |
| [nfce-qrcode.md](nfce-qrcode.md) | QR Code da NFC-e: algoritmo do hash, `infNFeSupl`, CDATA, o que falta (contingência, tabela de UF) |
| [plano-de-contas.md](plano-de-contas.md) | Bloco contábil: grupos do balanço/DRE (Lei 6.404/76), amarração aos tributos, obstáculo de integração com o seletor de plano de contas do ERPNext |
| [lancamentos-contabeis.md](lancamentos-contabeis.md) | Partidas dobradas de uma venda: por que IPI não passa pela receita (DL 1.598/77), tratamento provisório de IBS/CBS e sua fase de teste sem recolhimento real |
| [apuracao-periodica.md](apuracao-periodica.md) | Fechamento periódico de ICMS/IPI: não cumulatividade (Art. 155/153 CF), saldo a recolher × saldo credor a transportar |
| [sped-fiscal.md](sped-fiscal.md) | EFD-ICMS/IPI: por que o livro em papel foi dispensado (Ajuste SINIEF 02/09), layout dos registros E110 (ICMS) e E520 (IPI), escopo sem ajuste de apuração |
| [efd-contribuicoes.md](efd-contribuicoes.md) | EFD-Contribuições: registros M200/M210 (PIS) e M600/M610 (Cofins) — mesmo layout confirmado entre os dois, fórmulas citadas literalmente |
| [reinf-r4020.md](reinf-r4020.md) | EFD-Reinf R-4020: retenções de IRRF/CSLL/Cofins/PIS-Pasep sobre pagamento a PJ, irmão do eSocial mas com `procEmi` de domínio diferente |
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
| [rh-esocial-s2299.md](rh-esocial-s2299.md) | S-2299 (Desligamento): reaproveita de verdade o `DmDev` do S-1200, três variações de `procEmi` confirmadas, `mtvDeslig`/Tabela 19 genuinamente não localizada |
| [boleto.md](boleto.md) | Código de barras/linha digitável FEBRABAN (validado contra exemplo real) e leitura do CNAB 400 de retorno para conciliação |
| [cnab240-retorno.md](cnab240-retorno.md) | Sucessor do CNAB 400: Segmentos T/U do retorno, posições confirmadas contra dois bancos independentes, `codigo_movimento` como hipótese de trabalho |

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
