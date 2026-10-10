# Consulta de CNPJ

Preenche o nome do cliente, do fornecedor e da empresa a partir do CNPJ, avisa a **situação cadastral** na Receita e, por clique,
cria o endereço do estabelecimento. É a metade "CNPJ" da tarefa 5.3 de `tropicalizar-demais-modulos` (a metade "CEP" está em
`consulta-cep.md`).

## Por que existe

O CNPJ (`tax_id`) é digitado à mão e validado só no formato e no dígito verificador. Um CNPJ **válido** pode ser de empresa baixada,
suspensa ou inapta, e a nota emitida contra ele é rejeitada ou, pior, aceita e contestada depois. A consulta avisa isso antes de
salvar e poupa digitar razão social e endereço.

## De onde vem o dado (conferido ao vivo em 2026-10-10)

**Não existe API oficial gratuita da Receita para consulta por CNPJ.** O serviço oficial é pago (Serpro, com OAuth2 e certificado
e-CNPJ; teste grátis de 30 dias e 3.000 consultas). Os dois provedores gratuitos usados falam o **mesmo esquema** e repartem a mesma
origem, os dados abertos da Receita, publicados **uma vez por mês**:

| Provedor | Modelo de URL | Observação |
|---|---|---|
| BrasilAPI (primeiro) | `https://brasilapi.com.br/api/cnpj/v1/{cnpj}` | usado na chamada real de teste |
| Minha Receita (segundo) | `https://minhareceita.org/{cnpj}` | licença MIT; **dá para hospedar** |

Consequência que a tela diz em voz alta: **a situação cadastral pode estar defasada em até um mês.** Por isso é aviso, nunca bloqueio.

Respostas de erro vêm em JSON: `400` para dígito verificador inválido e `404` para CNPJ que não consta. O CNPJ **alfanumérico**
(IN RFB 2.229/2024, em produção desde julho de 2026) é aceito como formato; a chamada real com `12ABC34501DE35` (dígito válido) devolveu
"não encontrado", como esperado para um CNPJ de teste.

## Como o app usa

1. O usuário digita o CNPJ (14 caracteres) no cliente, fornecedor ou empresa — este último só se o país for o Brasil. Também há os botões
   **Brasil → Consultar CNPJ**, **Ver dados da Receita** e **Criar endereço pelo CNPJ**.
2. O navegador manda ao servidor o CNPJ e o nome que o formulário já tem; o servidor consulta (ou usa o cache) e responde o que cabe
   preencher, a situação e um resumo.
3. O formulário recebe **só a lacuna** — na prática, a razão social quando o nome está vazio. Uma faixa amarela diz o que foi
   pré-preenchido ("confira e salve") e some ao salvar; um alerta no topo mostra a situação (verde se ATIVA, vermelho nas demais).

Regras que não se negociam:

- **Sugestão preenche lacuna, nunca corrige.** O nome que o usuário digitou (por exemplo, o nome fantasia) nunca é trocado.
- **Situação não ATIVA é aviso**: códigos 1 nula, 3 suspensa, 4 inapta, 8 baixada.
- **A razão social com CPF não é sugerida como nome.** MEI e empresário individual antigos têm a razão social terminando no CPF do
  titular (11 dígitos) ou com um CPF formatado; isso é dado de pessoa física e não vira nome de cadastro. O formato atual do MEI
  (desde 12/12/2022), `12.345.678 NOME`, é mantido como está.
- **Não confundir os dois códigos de município.** `codigo_municipio` é o da Receita (por exemplo `9701`); o do IBGE, de 7 dígitos
  (`5300108`), é `codigo_municipio_ibge`. Só o segundo vai para `br_codigo_municipio_ibge`.
- **Endereço**: o número pode ser `SN`; o tipo de logradouro vem separado (`QUADRA`) e não se repete quando o logradouro já o traz
  (`SAUN QUADRA 5…`). O `Address` só nasce por **clique explícito** e **só se a parte ainda não tem endereço** — cria um endereço de
  cobrança principal, vinculado à parte.

## Sem rede, o cadastro continua

Provedor fora do ar, limite de uso, 5xx ou resposta estranha viram "Consulta de CNPJ indisponível agora. Preencha o cadastro
manualmente." — nenhuma exceção sobe, e **falha não é guardada em cache**.

- **Cache**: 1 dia para CNPJ achado (a base é mensal), 1 hora para inexistente.
- **Fallback**: passa ao próximo provedor **só quando o anterior não respondeu**. O `404` é a resposta, não uma falha, e não é repetido.
- **Prazo**: 5 segundos por chamada, sem seguir redirecionamento.
- **Limite de uso**: 60 consultas por minuto por IP e 20 criações de endereço.
- **Permissão**: quem pode criar ou gravar o cadastro; só Cliente, Fornecedor e Empresa são aceitos.

## Configuração (`site_config.json`)

| Chave | Efeito |
|---|---|
| `brasil_consulta_cnpj: false` | desliga a consulta (rede restrita, ou política de não enviar o CNPJ a terceiros) |
| `brasil_consulta_cnpj_provedores: ["https://…/{cnpj}"]` | lista própria de modelos de URL, com `{cnpj}` uma vez, `http` ou `https`, sem credencial na URL |

Uma lista configurada e **inválida não volta aos provedores padrão**: reintroduziria justamente os terceiros que o administrador quis
evitar. A consulta fica indisponível e o motivo vai para o Error Log.

## Privacidade

**Só o CNPJ sai do servidor.** Em empresário individual e MEI o CNPJ identifica uma pessoa física; por isso o envio é desligável e a
consulta pode ser hospedada em casa (Minha Receita). Do que volta, **nunca são lidos nem guardados** o quadro de sócios (QSA), o
e-mail e o telefone — a camada pura nem tem campo para eles, e há teste que garante isso.

## O que não faz

- Não traz inscrição estadual nem regime de ICMS: isso é da SEFAZ, não da Receita (lacuna aberta).
- Não consulta a Receita em tempo real; não substitui a consulta oficial quando a decisão fiscal depende da situação de hoje.
- Não foi exercitada a tela em navegador (como a do CEP): a lógica do servidor está provada em bench, o JS tem teste de costura
  (nomes de método, campos, registro no `hooks.py`), mas o clique real ainda precisa de verificação manual.
- Não preenche telefone, e-mail nem contatos (decisão de privacidade, acima).

## Onde está

| Peça | Arquivo |
|---|---|
| Regra pura (URL, leitura, lacuna, aviso, endereço) | `fiscal/cadastro_cnpj.py` — 47 testes em `tests/test_cadastro_cnpj.py` |
| Chamada, provedores, cache, limite, permissão, `Address` | `integracao/consulta_cnpj.py` — costura em `tests/test_consulta_cnpj.py` (22), comportamento em `tests_bench/test_consulta_cnpj.py` (20, verdes em MariaDB e PostgreSQL) |
| Tela | `public/js/consulta_cnpj.js`, ligado a Customer, Supplier e Company em `hooks.py` |
