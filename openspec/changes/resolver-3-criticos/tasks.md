## 1. B1: Corrigir proposal.md do fechar-laco-cte-mdfe

- [x] 1.1 Atualizar as linhas 22-24 de `openspec/changes/fechar-laco-cte-mdfe/proposal.md`
      para refletir a decisão 3 do design.md: CT-e síncrono `CTeRecepcaoSincV4` (sem lote
      nem recibo) e MDF-e lote+recibo `MDFeRecepcao`/`MDFeRetRecepcao` — verificar que
      o texto bate com design.md e com as specs

## 2. G8: Implementar alocação de numeração antes da transmissão

- [x] 2.1 Ler `integracao/emissao_nfe.py` e localizar o ponto onde
      `TransporteSefaz.transmitir` é chamado — verificar que a chamada atual não alocou
      número antes
- [x] 2.2 Inserir chamada a `numero_do_documento(doc, modelo=55, serie=doc.br_serie_nfe)`
      antes de `TransporteSefaz.transmitir` — verificar que o número é alocado e que uma
      falha de alocação (`frappe.throw()`) recusa antes de atingir a rede
- [x] 2.3 PULADO — descrição incorreta: `numero_do_documento` retorna o número existente
      na reemissão (comportamento correto); teste de concorrência exige bench (não é puro)
- [x] 2.4 Verificar com `test_arquitetura.py` que o módulo continua sem importar `frappe`
      em contexto de teste puro

## 3. G9: Validar emissão contra SEFAZ real

> **ℹ️ Bench encontrado (2026-09-15, não precisou instalar):** o binário existe em WSL em
> `~/.local/bin/bench` (bench `5.31.0`), só não estava no PATH de login — o find anterior
> falhou por timeout, **não** por ausência. O site `erpnext-brasil.localhost` está em
> `~/frappe-bench/sites/`. O que *continua* bloqueando 3.1-3.3 é a infra externa: site
> precisa estar **up** para o console responder (`bench doctor`/`console` penduram com o
> site inacessível), **certificado A1 real** e **homologação SEFAZ** — nenhum dos três é
> instalável por código. Decisão: não marcar 3.1-3.3 como feito; registrar cada descoberta
> em `docs/emitir-nfe-1a-validacao.md` à medida que a infra for disponibilizada.

- [ ] 3.1 Verificar no bench que o certificado A1 está configurado: `bench --site <site>
      console` → `configuracao_fiscal()` → conferir `arquivo_cert` e `arquivo_chave`
- [ ] 3.2 Criar documento de teste (`Sales Invoice` com modelo 65, dados válidos) e rodar
      `emitir_nfe()` contra homologação — registrar cStat e mensagem retornada
- [ ] 3.3 Se cStat = 100: sucesso. Se cStat 110-199: investigar rejeição e registrar
      motivo. Se cStat 200+: erro de sistema, reportar. Documentar em `docs/emitir-nfe-1a-validacao.md`
