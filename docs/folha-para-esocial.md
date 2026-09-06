# Da folha do ERPNext ao S-1200

A ponte que faltava entre o `Salary Slip` e o evento de remuneração do eSocial.

## O vazio que isto preenche

`folha/esocial_s1200.py` monta a árvore do evento. `transmissao_lote_esocial` a transmite.
Entre os dois **nada lia a folha do ERPNext** — e sem isso o eSocial dependia de alguém
montar dataclasses à mão.

## ⚠️ O código da rubrica é o centro de tudo

O S-1200 declara cada verba por `codRubr`, e esse código vem da **tabela de rubricas do
próprio empregador** (evento S-1010). **Não existe tabela nacional a consultar** — é
cadastro de quem declara.

Por isso o `Salary Component` ganhou `br_cod_rubrica`. Sem ele, um componente não tem como
virar linha de `itensRemun`.

### E a falta dele **recusa a montagem**

Pular a linha produziria um evento com remuneração **a menos** — aceito pelo eSocial, e
errado. A diferença viraria divergência entre a folha e o que foi declarado, descoberta
meses depois.

A mensagem diz **qual** componente falta: "não há código de rubrica" mandaria o usuário
procurar entre dezenas.

## Os campos, e os que **não** se criou

| Dado do eSocial | De onde vem | Novo? |
|---|---|---|
| `cpfTrab` | `Employee.br_cpf` | ✅ novo |
| `nisTrab` | `Employee.br_nis` | ✅ novo |
| `codCateg` | `Employee.br_cod_categoria` | ✅ novo |
| `codCBO` | `Employee.br_cod_cbo` | ✅ novo |
| `codLotacao` | `Employee.br_cod_lotacao` | ✅ novo |
| `codRubr` | `Salary Component.br_cod_rubrica` | ✅ novo |
| `nmTrab` | `Employee.employee_name` | ❌ nativo |
| `dtNascto` | `Employee.date_of_birth` | ❌ nativo |
| `matricula` | `Employee.employee_number` | ❌ nativo |

Os três últimos seguem a regra que já evitou um `br_conta` no `Bank Account` e um
`br_taxa_depreciacao` no `Asset`: **não criar segunda verdade sobre o mesmo dado**. Um
`br_data_nascimento` ao lado de `date_of_birth` produziria duas datas, e a divergência
apareceria quando alguém corrigisse uma e não a outra.

### O CBO fica no `Employee`, não na `Designation`

Dois empregados com o mesmo cargo podem ter CBO diferente. Pôr o campo no cargo pareceria
mais organizado e produziria classificação errada para o segundo.

### A categoria é `Data` com sugestões, não `Select`

A Tabela 01 do eSocial tem dezenas de categorias. Um `Select` fechado com as oito comuns
**recusaria contratações legítimas** — quem tem categoria fora da lista digita o código, e
quem valida é o eSocial.

## O que não entra no evento

- **Componente estatístico** (`statistical_component`) — existe só para cálculo interno do
  ERPNext, não representa verba paga.
- **Componente fora do total** (`do_not_include_in_total`) — pela mesma razão.
- **Valor zero entra normalmente**: o eSocial espera o valor apurado do período, e omitir a
  linha esconderia o cálculo em vez de mostrar "apurado como zero".

## Ganhos e descontos, uma lista só

`itensRemun` **não separa** provento de desconto — o código da rubrica é que diz o que cada
linha é. Por isso `earnings` e `deductions` viram uma lista única: separá-las inventaria uma
estrutura que o leiaute não tem.

## Duas decisões pequenas com motivo grande

### `Decimal(str(valor))`, nunca `Decimal(valor)`

O `amount` vem do Frappe como `float`. `Decimal(float)` traz o erro de representação binária
junto; passar por `str` preserva o número que o usuário vê na tela.

### O período vem de `start_date`, não de `end_date`

Um holerite que atravessa o mês pertence à competência em que **começou**. Usar a data final
deslocaria a folha inteira de um mês num período que feche no dia 1º.

## ⚠️ Um teste que media o universo errado

Ao acrescentar os campos de folha, a suíte de costura os **reprovou dizendo que não estavam
declarados** — quando estavam.

A causa: o teste montava a sua própria união de campos, e conhecia só **um** dos três mapas
(`custom_fields`, `campos_documento`, `campos_folha`). A instalação juntava os três; o teste,
um.

> Um teste que constrói o seu próprio universo mede o universo dele, não o do app.

Corrigido extraindo a união para `setup/campos.py` — módulo **sem `frappe`**, porque a suíte
precisa dele sem bench. Agora instalação e teste leem o mesmo dado, e acrescentar um quarto
mapa é uma linha só.

A mesclagem é **por DocType**, não `dict.update`: `Company` aparece em dois mapas e
`Employee` num terceiro, e um `update` faria o segundo apagar a lista do primeiro — campo
sumindo da instalação sem que ninguém o tivesse removido.

## A composição, e o caminho completo

`integracao/montagem_lote_esocial.py` compõe as peças e grava o `Lote eSocial`:

```text
seleção de holerites
  → evento_do_holerite        (este documento)
  → gerar_id_evento           Id de 36 caracteres
  → montar_evento_assinado    assinatura XMLDSig
  → montar_xml_lote           envelope envioLoteEventos
  → Lote eSocial              gravado, em rascunho
```

### ⚠️ O certificado é aberto uma vez para o lote inteiro

`TransporteEsocial` expõe `assinador` justamente para isto, e o `with` fica **em volta do
laço**, não dentro. Dentro, o PKCS#12 seria decifrado uma vez por empregado — numa folha de
cem, cem operações caras de criptografia. O código funcionaria igual e ficaria lento de um
jeito que ninguém relaciona à causa. Um teste confere a posição do `with` por AST.

### Montar não transmite

O lote nasce em **rascunho**. Em eSocial, o que foi transmitido **não se desfaz**: retificar
exige outro evento, com o número do recibo do primeiro. Separar as duas ações dá ao usuário o
momento de conferir — a mesma razão de a importação de XML não criar o documento sozinha.

### Uma empresa por lote

O `ideEmpregador` é **um** por envelope. Misturar empresas produziria um lote que declara uma
e contém eventos de outra — aceito pelo montador, recusado pelo eSocial, com mensagem que não
diria qual holerite é o intruso. A recusa aqui **lista as empresas encontradas**.

### Não se fatia o lote automaticamente

O leiaute tem teto de eventos por lote, e passar dele é recusado. Fatiar sem pedir produziria
vários `Lote eSocial` de um clique, e quem transmitisse o primeiro acharia que transmitiu
tudo.

## As telas

| Onde | O quê |
|---|---|
| lista de `Salary Slip` | **Montar Lote eSocial** a partir da seleção |
| formulário do `Lote eSocial` | **Transmitir ao eSocial** |
| idem, com protocolo | **Consultar processamento** |

Transmitir e consultar são botões **separados**, e um exclui o outro: com protocolo, o lote
já foi recebido, e reenviar duplicaria os eventos.

## O que falta

**Exercitar contra o ambiente de produção restrita**, que exige certificado A1 real. Nenhum
módulo do eSocial foi executado fora de teste — a cadeia está inteira e nunca falou com o
Fisco.

Estado de verificação: camada Frappe, **não** exercitada contra bench real.
