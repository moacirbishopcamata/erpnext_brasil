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
| Validação de CPF/CNPJ (inclusive **CNPJ alfanumérico**) | pronto |
| Campos fiscais em Company, Customer, Supplier, Address, Item | pronto |
| Validação de NCM e código IBGE de município | pronto |
| Inscrição Estadual — as 27 UFs | pronto, com a ressalva abaixo |
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

### Inscrição Estadual: o que está provado e o que não está

As 27 UFs têm regra implementada, incluindo as irregulares — SP (dígito fora da
posição final e formato próprio de produtor rural), MG (módulo 10 com zero interposto,
somando algarismos do produto), BA (alterna entre módulo 10 e 11 conforme o primeiro
dígito), PE, AP, GO, RO, RR (único caso de módulo 9) e TO.

Os testes constroem uma IE por força bruta sobre as posições de dígito verificador e
exigem que a regra a aceite e que mutações a rejeitem. **Isso prova consistência
aritmética, não aderência à especificação**: um peso trocado em relação ao SINTEGRA
continuaria passando, porque o teste valida a implementação contra ela mesma. Fechar
essa lacuna exige um lote de IEs reais por UF — é o próximo passo dessa frente.

Por isso o viés é deliberadamente a favor do falso positivo: UF que não se consegue
determinar, ou fora das 27, **deixa passar**. Uma IE inválida aceita é pega depois pela
SEFAZ; uma IE válida rejeitada trava o cadastro de um cliente real e não tem contorno
dentro do sistema. O valor `ISENTO` é aceito em qualquer UF, como manda a legislação
para não contribuinte.

A UF vem do endereço padrão da parte, e `state` no ERPNext é texto livre — a resolução
aceita sigla e nome por extenso, com ou sem acento, e devolve "sem regra" quando não dá
para afirmar.

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

São 36 testes cobrindo CPF/CNPJ, as 27 regras de Inscrição Estadual e a resolução de UF.

## Licença

MIT.
