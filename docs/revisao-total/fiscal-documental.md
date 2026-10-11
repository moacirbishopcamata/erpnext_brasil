# Revisão total — fiscal documental (NF-e, NFC-e, CT-e, MDF-e, eventos)

Versão `0.227.0`, 2026-10-11. Cobre a tarefa 3.1 do change `revisao-total-erpnext-brasil`.

## Cobertura

- **Lido:** as chamadas de hora em `fiscal/` e `integracao/`, o encadeamento da guarda de consumo indevido (via testes `test_transporte_cte`, `test_transporte_mdfe`, `test_consumo_indevido`), o trecho de `dhEmi` em `fiscal/documento/nfe.py:179-183`.
- **Rodado:** a suíte pura inteira (3.490 testes, verde).
- **Não lido:** montagem de XML, assinatura, leiaute e tabelas de `cStat`. Nada foi conferido contra o MOC ou os XSD nesta revisão. Nada foi enviado a uma SEFAZ.

## Verificado

- `dhEmi` exige fuso: `fiscal/documento/nfe.py:179-183` recusa data sem deslocamento, e a emissão usa `agora_da_emissao()`, que lê o fuso do site (`configuracao_fiscal.py:179-187`).
- A guarda de consumo indevido recusa antes da SEFAZ com zero chamadas ao transporte, para CT-e e MDF-e (tarefas 3.3 e 5.3 de `fechar-laco-cte-mdfe`); reexecutei os três módulos de teste: 43 testes, verde.
- Os montadores de evento do MDF-e tinham a forma da NF-e e foram corrigidos no PR #13 para cancelamento e encerramento; os outros cinco continuam em `docs/gaps.md`.

## Achados

### RT-06 — fuso do servidor nos eventos de CT-e e MDF-e — **Médio**

Detalhe e evidência em [`integracao.md`](integracao.md) (RT-06): `eventos_cte.py:80` e `eventos_mdfe.py:74` ignoram o fuso do site que a emissão usa.

### RT-12 — emissão por lote do MDF-e e CT-e sem prova em homologação — **Médio (declarado)**

As tarefas 3.1 (CT-e) e 5.1 (MDF-e) de `fechar-laco-cte-mdfe` seguem abertas porque falta autorizar um documento em homologação com certificado A1 real. Envelope SOAP, `cUF` do cabeçalho e códigos 103/105/100 vêm de fonte **secundária** (pacote de esquemas `PL_MDFe_300b` e `sped-mdfe`), não do MOC. Não é falha de código; é risco de ambiente que só a homologação fecha.

### RT-13 — cinco montadores de evento do MDF-e ainda com a forma da NF-e — **Médio (declarado)**

Registrado em `docs/gaps.md:817-819` pelo PR #13 (raiz `evento` e campos soltos em `detEvento`, no lugar de `eventoMDFe`): condutor, inclusão de documento e os demais montadores que não são cancelamento nem encerramento. Não têm gatilho de tela hoje (tarefa 5.6), então são inalcançáveis; viram bug no dia em que ganharem botão.
