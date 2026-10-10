# Consulta de CEP e logradouro (ViaCEP)

Preenche o endereço do cliente, do fornecedor e da empresa a partir do CEP, ou acha o CEP a partir do logradouro. É a metade
"CEP" da lacuna 4 de `tropicalizar-demais-modulos` (a consulta de CNPJ segue aberta).

## Por que existe: onde o app exige endereço

O endereço é exigido **por inteiro** e **falha alto** quando falta (`integracao/nfe_documento._grupo_endereco`, reaproveitada pelo
CT-e): logradouro (`address_line1`), número (`br_numero_endereco`), bairro (`br_bairro`), código IBGE do município
(`br_codigo_municipio_ibge`), município (`city`), UF (`state`) e CEP (`pincode`). Quem lê as mesmas colunas:

| Quem | Para quê |
|---|---|
| NF-e e NFC-e (`nfe_documento.py`) | `enderEmit` e `enderDest` |
| CT-e (`cte_documento.py`) | emitente, remetente, destinatário e tomador |
| MDF-e (`mdfe_documento.py`) | município de descarga (IBGE) |
| SPED (`efd_dados_cadastrais.py`) e ECF (`ecf_dados_empresa.py`) | participantes e dados da empresa |
| Prontidão e alerta fiscal | conferem UF e IBGE antes de emitir |

Hoje tudo isso é digitado à mão, e o código IBGE de 7 dígitos é o dado mais fácil de errar. O ViaCEP devolve o IBGE junto.

## O que o serviço faz (conferido ao vivo em 2026-10-10)

| Consulta | Endereço | Resposta |
|---|---|---|
| Por CEP | `/ws/01001000/json/` | objeto com `cep`, `logradouro`, `complemento`, `bairro`, `localidade`, `uf`, `estado`, `ibge`, `ddd`… |
| Por logradouro | `/ws/RS/Porto%20Alegre/Domingos+José/json/` | lista de **até 50**; cidade e logradouro com **ao menos 3 caracteres** |
| CEP inexistente | `/ws/99999999/json/` | **HTTP 200** com `{"erro": "true"}` — o valor é o *texto* `"true"`, não booleano |
| CEP malformado | `/ws/123/json/` | **HTTP 400 com página HTML**, não JSON |

**`+` e `%20` não são iguais** (achado ao vivo): no logradouro, `Domingos+José` buscou por palavras e achou 3 ruas, e `Domingos%20José` exigiu a
frase e achou 2; na cidade, `+` devolve uma página de erro em vez de JSON. O app usa `%20` na cidade e `+` no logradouro — a forma do exemplo da
própria documentação — e um `+` digitado pelo usuário vira `%2B` (é dado, não separador).

O serviço é gratuito, **não publica SLA nem limite de requisições** e avisa que "uso massivo para validação de bases de dados
locais" pode levar a bloqueio por tempo indeterminado. A base informava 1.608.385 CEPs; fontes IBGE, GIA/ICMS (SP), Anatel e SIAFI.

## Como o app usa

1. O usuário digita o CEP (8 dígitos) num endereço do **Brasil**, ou usa o botão **Brasil → Buscar CEP pelo logradouro**.
2. O navegador manda ao servidor o CEP e os valores que o formulário já tem; o servidor consulta (ou usa o cache) e responde o que
   cabe preencher e o que diverge.
3. O formulário recebe **só as lacunas**. Uma faixa amarela diz o que foi pré-preenchido ("confira e salve") e some depois de salvar.

Regras que não se negociam:

- **Sugestão preenche lacuna, nunca corrige.** O valor que o usuário digitou ou salvou manda sobre o cadastro externo, que pode estar
  defasado ou ser mais genérico que o endereço real.
- **O que o ViaCEP contradiz é avisado, não trocado** (UF, município e código IBGE). "São Paulo" e "SP" são o mesmo estado; acento e
  caixa do município não contam. Logradouro e bairro não são comparados ("Rua X" e "R. X" dariam alarme falso).
- **O `complemento` do ViaCEP nunca é usado.** Para `01001-000` ele vale `"lado ímpar"`, uma nota sobre a faixa do CEP; gravá-lo em
  `address_line2` mandaria "lado ímpar" para o `xCpl` da nota. O **número** e o complemento são sempre do usuário.
- **A UF vai como sigla** (`SP`), que é o que a nota e a validação do município usam.
- **O código IBGE continua passando pela validação existente** ao salvar (formato, UF e dígito verificador, com as exceções do IBGE).

## Sem rede, o cadastro continua

A consulta ajuda e nunca trava. Serviço fora do ar, erro 5xx, página de erro ou resposta estranha viram a mensagem "Consulta de CEP
indisponível agora. Preencha o endereço manualmente." — nenhuma exceção sobe. **Falha não é guardada em cache** (senão um CEP bom ficaria
"indisponível" por dias); CEP inexistente é.

- **Cache**: 7 dias para CEP achado, 1 dia para inexistente e para busca sem resultado. Cada resultado de uma busca alimenta o cache por
  CEP, então escolher uma linha da lista não faz uma segunda chamada.
- **Prazo**: 5 segundos por chamada.
- **Limite de uso**: 120 consultas por minuto por IP no CEP e 60 na busca (com vários usuários atrás do mesmo NAT, o limite é do grupo).
- **Desligar**: `brasil_consulta_cep: false` em `site_config.json` (rede restrita, ou política de não enviar texto a terceiros).

## Privacidade

Só o CEP ou o texto de busca (UF, cidade, logradouro) sai do servidor. **Nenhum dado de pessoa** (nome, CPF, CNPJ, telefone, e-mail) vai
ao ViaCEP; um CEP isolado não identifica ninguém. O texto da busca vai a um serviço de terceiro: quem não admite isso desliga a consulta.

## O que não faz

- Não preenche número nem complemento, e não confirma que o endereço completo existe (o CEP de cidade pequena vem sem logradouro e sem bairro;
  o app deixa em branco o que a resposta não traz).
- Não consulta CNPJ (lacuna aberta).
- Não foram avaliadas alternativas ao ViaCEP (agregadores de CEP, base dos Correios sob contrato); a camada pura (`fiscal/endereco_cep.py`)
  não depende de fornecedor além do formato da resposta.

## Onde está

| Peça | Arquivo |
|---|---|
| Regra pura (URL, leitura, lacuna, divergência) | `fiscal/endereco_cep.py` — 40 testes em `tests/test_endereco_cep.py` |
| Chamada, cache, limite, permissão | `integracao/consulta_cep.py` — costura em `tests/test_consulta_cep.py`, comportamento em `tests_bench/test_consulta_cep.py` |
| Tela | `public/js/endereco_cep.js`, ligado ao `Address` em `hooks.py` |
