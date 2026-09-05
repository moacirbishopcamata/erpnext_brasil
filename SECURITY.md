# Política de Segurança

## Como relatar uma vulnerabilidade

**Não abra uma issue pública** para falha de segurança. Issues são visíveis a todos, e uma
falha exposta antes da correção deixa quem usa o projeto vulnerável no intervalo.

Use o canal privado do GitHub: **Security → Report a vulnerability** (GitHub Security
Advisories) neste repositório.

Inclua, se possível: o que acontece, como reproduzir, a versão do `erpnext_brasil` e do
Frappe/ERPNext, e o impacto que você enxerga. Não é preciso ter a correção pronta — o
relato já ajuda.

## O que é vulnerabilidade neste projeto

Este é um app fiscal, então a superfície de risco tem duas partes.

**Segurança de software**, no sentido usual:

- exposição do **certificado digital A1** ou da sua senha (o PFX é anexado à `Company` e a
  senha vive em campo `Password`, criptografado pelo Frappe — qualquer caminho que os
  revele em log, erro, API ou arquivo é falha);
- exposição do **CSC da NFC-e**, pelo mesmo motivo;
- método `@frappe.whitelist()` sem checagem de permissão adequada;
- injeção de SQL, XSS ou desserialização insegura;
- escrita de arquivo fora do diretório esperado.

**Correção fiscal com consequência de segurança**, que é específica daqui:

- documento assinado com dado diferente do que foi exibido ao usuário;
- chave de acesso que não corresponde ao conteúdo do documento;
- qualquer caminho que permita emitir em **produção** quando o usuário escolheu
  homologação, ou o contrário.

## O que **não** é vulnerabilidade

Erro de cálculo de tributo, leiaute desatualizado, campo faltando ou regra fiscal
implementada de forma incompleta são **bugs** — abra issue normal. São importantes, e
`docs/gaps.md` registra o que já se sabe estar incompleto; mas não são falha de segurança e
não precisam de canal privado.

## Sem garantia

Ver o **Aviso de responsabilidade** no [README](README.md). Este projeto é software livre
sob licença MIT, fornecido como está, sem garantia de espécie alguma — inclusive quanto a
segurança. Não há SLA de resposta nem compromisso de correção em prazo determinado.
