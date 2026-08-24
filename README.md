# ERPNext Brasil

Localização fiscal brasileira para o ERPNext, distribuída como **app Frappe separado** —
o ERPNext nunca é forkado nem editado.

## Por que app separado

O `erpnext/regional/` mantém hoje apenas seis países; a localização indiana, que era a
mais pesada do projeto, saiu do core e virou app próprio. Essa é a direção do projeto.
Além disso, o mecanismo de sobrescrita por região do ERPNext dá **prioridade ao último
app instalado**, de modo que um app instalado depois do erpnext vence por construção,
sem precisar tocar em nenhum arquivo do core.

Os dois projetos brasileiros anteriores que tentaram o caminho do fork morreram em
poucos meses. Isto aqui é uma tentativa de não repetir isso.

## Estado atual

Primeiro incremento entregue: **cadastros e campos fiscais**, com validação.

| Área | Situação |
|---|---|
| Validação de CPF/CNPJ (inclusive **CNPJ alfanumérico**) | pronto, 17 testes |
| Campos fiscais em Company, Customer, Supplier, Address, Item | pronto |
| Validação de NCM e código IBGE de município | pronto |
| Inscrição Estadual (dígito verificador por UF) | **pendente** — 27 algoritmos distintos |
| Motor de impostos (ICMS/IPI/PIS/COFINS, ST, DIFAL) | não iniciado |
| Tabelas de código (NCM, CFOP, CST/CSOSN, LC 116) | não iniciado |
| Documento fiscal / NF-e | não iniciado |
| Obrigações acessórias (SPED, EFD-Reinf) | não iniciado |

### CNPJ alfanumérico

Desde julho de 2026 (IN RFB 2.229/2024) o CNPJ admite letras nas 12 posições da
raiz/ordem, mantendo os 2 dígitos verificadores numéricos. O cálculo do DV continua
sendo o módulo 11; muda apenas a conversão do caractere em valor (`ord(c) - 48`).
CNPJs numéricos antigos permanecem válidos e passam pelo mesmo caminho de código.

Validadores que só aceitam dígitos já nascem quebrados — por isso este é o ponto de
partida do app, e não um detalhe deixado para depois.

## Decisões de projeto

**Não duplicar o que o ERPNext já tem.** Company, Customer e Supplier já possuem
`tax_id`; é ali que o CPF/CNPJ mora. Criar um campo `cnpj` paralelo produziria dois
lugares para o mesmo dado, divergindo em silêncio. Só se acrescenta o que o núcleo não
modela (Inscrição Estadual, indicador de IE, SUFRAMA, NCM, CEST, origem da mercadoria,
código IBGE do município).

**Regra fiscal separada do framework.** `fiscal/validators.py` não importa `frappe`:
são funções puras, testáveis sem bench, sem site e sem banco. `fiscal/party.py` é a
camada fina que traduz o resultado em `frappe.throw`.

**Validação só em contexto brasileiro.** As validações consultam o país da Company; uma
instalação multiempresa com filial no exterior não passa a exigir CNPJ de fornecedor
estrangeiro.

## Instalação

```sh
bench get-app <url-deste-repositorio>
bench --site <site> install-app erpnext_brasil
```

Os campos fiscais são recriados a cada `bench migrate` (`after_migrate`), de forma
idempotente — campos customizados podem se perder quando o ERPNext altera o DocType base.

## Testes

As funções puras rodam sem infraestrutura nenhuma:

```sh
python -m unittest discover -s erpnext_brasil/tests -t .
```

## Licença

MIT.
