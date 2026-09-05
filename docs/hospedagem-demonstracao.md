# Hospedagem para demonstração

Levantamento das opções gratuitas para subir o `erpnext_brasil` e **mostrar funcionando**
— demonstração, não operação real. Consultado em 2026-09-04.

O recorte importa: para demo, o que vale é **subir rápido e descartar**. Endereço fixo,
disponibilidade e backup só entram quando alguém depender daquilo, e aí a conversa deixa
de ser sobre plano gratuito.

## ⚠️ Antes de tudo: demo não é produção fiscal

Nenhuma das opções abaixo serve para **emitir NF-e de verdade**. Não por limitação técnica
— tecnicamente funcionaria — mas porque emitir documento fiscal exige:

- **guardar o certificado A1 com responsabilidade** (ele é a identidade da empresa perante
  o Fisco; num ambiente descartável ou compartilhado, isso não se sustenta);
- **disponibilidade**, já que nota não emitida trava faturamento;
- **retenção do que foi transmitido**, porque o XML autorizado precisa ser guardado por
  cinco anos.

Para demonstrar, use **ambiente de homologação da SEFAZ** e certificado de teste. Ver o
aviso de responsabilidade no [README](../README.md).

## Comparativo

| Opção | Custo | Some sozinho? | Esforço | Serve para |
|---|---|---|---|---|
| **GitHub Codespaces** | 60 core-h/mês grátis (120 no Pro) | sim, ao parar | baixo | demo pontual ✅ |
| **Gitpod** | horas grátis mensais | sim | baixo | demo pontual |
| **Oracle Always Free** | grátis para sempre | não | alto | ambiente que persiste |
| **Google Cloud** | US$ 300 / 90 dias | não | médio | avaliação longa |
| **Frappe Cloud** | — | — | — | ❌ não serve, ver abaixo |
| **AWS free tier** | 750 h/mês, 12 meses | não | médio | ❌ RAM insuficiente |

## 🥇 GitHub Codespaces — a recomendação para demonstração

**Por que é a melhor aqui:** o `frappe_docker` mantém um **devcontainer** pronto. Você abre
o repositório no navegador, o ambiente sobe com Frappe, MariaDB e Redis já configurados, e
você instala o `erpnext_brasil` por cima. Não há nada a provisionar, e como o código já vai
para o GitHub, é o caminho de menor atrito.

- **Grátis:** 60 core-hours por mês na conta gratuita, 120 na Pro. Um codespace de 2 núcleos
  consome 2 core-hours por hora ligada — ou seja, ~30 h/mês de uso real.
- **Para de contar quando você para o codespace.** Só o armazenamento continua (15 GB-mês
  grátis).
- **Descartável de propósito:** apagou, acabou. Perfeito para demo, péssimo para guardar
  dado.

⚠️ **Cuidado:** o codespace **hiberna sozinho** depois de 30 minutos ociosos (configurável).
No meio de uma apresentação isso é constrangedor — deixe rodando antes de começar.

## 🥈 Gitpod

Mesma ideia do Codespaces, com horas gratuitas mensais e integração com GitHub/GitLab.
Vale como alternativa se você já usa. Sem vantagem clara sobre o Codespaces quando o
repositório já está no GitHub.

## 🥉 Oracle Cloud Always Free — quando a instância precisa persistir

É a única opção **gratuita para sempre** com máquina de verdade. Faz sentido se você quiser
um endereço fixo que fique de pé entre demonstrações, em vez de subir e descartar.

⚠️ **Mudança importante, confirmada:** em **15 de junho de 2026** a Oracle **cortou pela
metade** a cota Always Free de ARM (Ampere A1), de **4 OCPU / 24 GB** para **2 OCPU /
12 GB** — sem anúncio público, sem post de blog, sem aviso a clientes. Ainda é folgado para
o ERPNext, mas quem planejou em cima dos 24 GB precisa refazer a conta.

Outras pegadinhas reais:

- **Capacidade ARM vive esgotada.** "Out of capacity" é resposta comum em várias regiões, e
  não há fila — é tentar de novo.
- **A região é escolhida uma vez** (Home Region) e **não muda depois**. Escolher uma sem
  disponibilidade de Ampere A1 inutiliza a cota.
- As instâncias AMD micro (2 × 1/8 OCPU, 1 GB) continuam, mas **1 GB não roda ERPNext**.

## ❌ Frappe Cloud — não serve para este caso

Seria o caminho natural, e não é: o **trial de 14 dias não permite app customizado**.
Aplicativo próprio exige **private bench**, que só existe depois de cadastrar forma de
pagamento — planos a partir de **US$ 25/mês** (o de US$ 5 é hospedagem compartilhada, sem
app customizado).

Ou seja: para demonstrar o ERPNext puro, o trial serve; para demonstrar **o
`erpnext_brasil`**, não.

Isso não é crítica ao serviço — é o modelo de negócio deles, e para produção o Frappe Cloud
é provavelmente a opção mais sensata do mercado, justamente por cuidar de atualização,
backup e restauração.

## ❌ AWS free tier — RAM insuficiente

750 h/mês de `t2.micro`/`t3.micro` por 12 meses parece resolver, mas são **1 GB de RAM**.
ERPNext com MariaDB e Redis não roda de forma utilizável nisso, nem com swap. Descartado.

## Fontes

- Corte da cota Always Free da Oracle (4 OCPU/24 GB → 2 OCPU/12 GB em 15/06/2026),
  reportado por [InfoQ](https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/)
  e [TerminalBytes](https://terminalbytes.com/oracle-cloud-free-tier-changes-2026/) —
  a Oracle não publicou anúncio próprio, o que é em si um dado sobre confiabilidade de
  planejamento em cima dessa cota.
- Trial e private benches do Frappe Cloud:
  [docs.frappe.io/cloud/benches](https://docs.frappe.io/cloud/benches) e
  [frappe.io/cloud](https://frappe.io/cloud).

⚠️ Termos de plano gratuito mudam sem aviso — a própria Oracle é o exemplo. **Confira antes
de decidir**; este documento registra o que era verdade em 2026-09-04.
