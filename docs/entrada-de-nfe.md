# Entrada de NF-e: ler o XML do fornecedor em vez de digitar

Como dar entrada numa nota recebida a partir do XML, e a fronteira que este módulo se
impôs de propósito.

## O gap que isto fecha

Toda entrada de mercadoria no Brasil vem acompanhada do XML da NF-e do fornecedor. Sem
leitura, a alternativa é **digitar** — e digitar uma chave de 44 dígitos, o NCM e o CFOP de
cada item é onde nasce erro de escrituração, que só aparece meses depois, na validação da
EFD.

O app sabia **montar** NF-e desde sempre (`fiscal/documento/nfe.py`) e não sabia **ler** uma.
Interpretar retorno da SEFAZ já havia (`resposta_sefaz.py`, `evento.py`), mas retorno é
outra coisa: são dezenas de elementos, não uma nota inteira com itens.

### ⚠️ Correção de uma afirmação anterior

A primeira versão de [tropicalizacao-por-area.md](tropicalizacao-por-area.md) dizia que "o
caminho já existe para o CT-e (`integracao/cte_extracao.py`)". **Não existe.** Aquele módulo
percorre `Shipment` → `Delivery Note` → `br_chave_acesso`, isto é, lê **DocTypes do site**,
não XML. Não havia precedente de parser de documento fiscal recebido —
`fiscal/documento/leitura_nfe.py` é o primeiro.

Registro isso porque a afirmação errada estava prestes a orientar a implementação: eu ia
"reaproveitar" um módulo que faz outra coisa.

## Como se usa

`integracao.entrada_nfe.importar_nfe(doctype, name, xml)` — sobre um `Purchase Invoice` já
criado. Preenche a chave de acesso, o número e a natureza da operação, e devolve as
divergências entre a nota e o documento.

```python
{
    "chave_acesso": "35260712345678000199550010000000011000000017",
    "numero": "1",
    "emitente": "Fornecedor Ltda",
    "itens": 3,
    "valor_nota": "318.00",
    "divergencias": ["Total da nota é 318.00 e o do documento é 300.00."],
}
```

## ⚠️ O que ele deliberadamente **não** faz

### Não cria o documento nem os itens

Esta é a decisão central, e é uma recusa consciente.

O código do produto na nota é o **do fornecedor** (`cProd`), não o do comprador. Casá-lo
com o `Item` do site exige uma tabela de correspondência que este app não tem — e adivinhar
por descrição ou por EAN produziria entrada de estoque **no item errado**, que é dos erros
mais caros de desfazer: contamina custo médio, saldo e a própria escrituração.

Então o módulo preenche o que a nota afirma **sobre si mesma** e **confere** o resto,
devolvendo divergências para quem decide. Preencher o que não se sabe seria pior que não
preencher.

Um teste trava essa fronteira (`test_nao_cria_nem_altera_itens`): o dia em que alguém
acrescentar um `doc.append` ali, a suíte recusa.

### Não grava valor nem imposto

O valor do documento vem do que foi **negociado**, não do que o fornecedor declarou.
Divergência entre os dois é para ser vista, não absorvida — absorvê-la esconderia
exatamente o caso que interessa: a nota que veio diferente do pedido.

### Não valida a assinatura do XML

Ler não é confiar. Conferir a assinatura exige a cadeia de certificados da ICP-Brasil e é
operação à parte. E presença de `protNFe` diz que houve autorização **no arquivo recebido**
— se a nota foi cancelada depois, só a consulta à SEFAZ responde.

### Não lê impostos por item

ICMS, IPI, PIS e Cofins de cada item vivem em grupos com nome variável por CST (`ICMS00`,
`ICMS20`, `ICMSSN101`…), e tratá-los exige o mapa de tributação inteiro — frente própria,
não um parâmetro a mais. **Os totais são lidos.**

## As decisões do leitor

### A conferência de destinatário falha alto

Se o CNPJ do destinatário na nota não é o da `Company` do documento, a importação **para**.

Não é excesso de zelo: escriturar a nota de outra empresa gera **crédito indevido de
ICMS**, e o erro só apareceria numa fiscalização. Um aviso amarelo seria clicado sem ler.

A comparação é entre dígitos, não entre strings — `12.345.678/0001-99` e `12345678000199`
são o mesmo CNPJ, e o `tax_id` da `Company` costuma vir formatado.

### A chave é conferida, não só extraída

Lida do `@Id` do `infNFe` e passada por `validar_chave`, **inclusive o dígito verificador**.
Um XML truncado ou adulterado no caminho falha ali, e não depois, quando a chave errada já
tiver sido gravada.

### Quantidade comercial **e** tributável

`qCom`/`uCom`/`vUnCom` (comercial) e `qTrib`/`uTrib`/`vUnTrib` (tributável) **podem
diferir**, e diferem sempre que a unidade de venda não é a de tributação — caixa com 12
unidades, saca de 60 kg.

O leitor devolve **as duas**, porque escolher uma seria decidir por quem chama: a entrada de
estoque quer a comercial, a escrituração fiscal quer a tributável. Um leitor que devolvesse
só `qCom` faria o estoque bater e o SPED não — e ninguém perceberia até o PVA.

É a asserção-âncora de `test_leitura_nfe.py`.

### Valores em `Decimal`, direto da string

Nunca passando por `float`. `Decimal(float("0.1"))` traz o erro de representação binária
junto, e três somas dessas já deslocam um centavo — que em nota fiscal é divergência de
escrituração.

### Valor numérico ilegível falha alto

Devolver zero seria pior: **zero é um número plausível**, e passaria despercebido.

### Os nomes dos elementos não foram escritos de memória

Todos os 43 usados foram conferidos contra `elementos_nfe.json`, o inventário de elementos
do leiaute que o projeto já mantinha. Escrever `qCom` como `qtdCom` produziria uma leitura
que devolve zero em silêncio.

### Aceita `nfeProc` e `NFe` solta

Os dois circulam: o fornecedor manda o `nfeProc` (nota mais protocolo), mas sistemas
intermediários às vezes repassam só a `NFe`. Recusar a segunda forçaria o usuário a editar
XML à mão.

## Estado de verificação

Domínio puro **testado** (19 casos, sem bench). Camada Frappe **não** exercitada contra
bench real — os testes são de costura estática: campo gravado × campo declarado, atributo
lido × atributo existente, e a ordem entre conferir e gravar.

## O que vem depois

- **Tabela de correspondência `cProd` do fornecedor → `Item` do site.** É o que falta para
  criar itens com segurança, e é cadastro, não adivinhação.
- **Criar o `Purchase Invoice` do zero** a partir do XML, uma vez que haja a tabela acima.
- **Manifestação do destinatário** (evento 210200/210210/210220/210240) — confirmar ou
  recusar a operação perante a SEFAZ. Domínio próprio, ainda não modelado.
