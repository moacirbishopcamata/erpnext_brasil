# DocTypes próprios: onde o resultado passa a existir

Pedido do usuário: "faltam também os DocType Frappe". Estava certo — e a razão de
faltarem até aqui vale registrar, porque não era esquecimento.

## Por que o app viveu 160 commits sem nenhum DocType

Até agora, todo dado brasileiro cabia como **atributo de um documento que já existe**:
`br_chave_acesso` numa Sales Invoice, `br_efd_perfil` numa Company, `ncm` num Item. Campo
customizado é a ferramenta certa para isso, e criar DocType para o que é atributo
inventaria estrutura sem uso — o mesmo critério que manteve `0005`/`0100` fora do Bloco 0
da EFD.

O que mudou: com a transmissão implementada (NF-e, CT-e, MDF-e, eSocial), passou a existir
dado que **não é atributo de nada** — tem vida própria.

## O que campo não guarda: histórico

Um documento fiscal tem **várias** interações com a SEFAZ ao longo do tempo:

1. autorização (protocolo A, data A, XML de ida e volta);
2. semanas depois, uma carta de correção (protocolo B, data B, outro par de XML);
3. talvez um cancelamento (protocolo C, data C).

`br_protocolo_autorizacao` guarda **um** protocolo. A segunda interação sobrescreveria a
primeira, e o histórico — que é justamente o que o Fisco pode pedir — desapareceria.

## `Transmissao Fiscal`

Primeiro DocType do app. Cada linha é **uma conversa com a SEFAZ**: o que se mandou, o
que voltou, quando, em que ambiente.

| Campo | Papel |
|---|---|
| `documento_tipo` + `documento` | Link dinâmico: serve a Sales Invoice, Delivery Note, Purchase Invoice, o que for |
| `chave_acesso` | 44 dígitos, validada de verdade |
| `tipo` | Autorização, Cancelamento, Carta de Correção, Inutilização, Consulta, Encerramento |
| `ambiente` | Homologação ou Produção — em homologação o documento não tem valor fiscal |
| `situacao`, `codigo_status`, `mensagem` | O que a SEFAZ respondeu |
| `protocolo`, `recebido_em` | A prova da autorização |
| `xml_enviado`, `xml_retorno` | O que foi assinado e o que voltou, sem interpretação |

### As invariantes, e por que cada uma existe

Estão em `fiscal/documento/transmissao_registro.py` — **puras**, testadas sem bench. Cada
uma impede um registro que mentiria sobre o que aconteceu:

- **Autorizado exige protocolo.** É a prova da autorização; sem ele, o registro afirma
  algo que não comprova. Mesma regra que `fiscal/documento/estado.Protocolo` já impunha.
- **Rejeitado e denegado exigem a mensagem.** Um registro que diz "rejeitado" sem dizer
  por quê não ajuda ninguém a corrigir — e o `xMotivo` sempre vem na resposta.
- **Inutilização não tem chave de acesso.** Inutilizar é declarar que uma faixa de
  numeração **não foi usada**: não existe documento, logo não existe chave. Exigir uma ali
  levaria alguém a inventar um valor.
- **Chave, quando houver, é chave de verdade** — layout e dígito verificador, reusando
  `chave_acesso.validar_chave`.

## A decisão de arquitetura: por que um módulo novo

O Frappe exige que todo DocType pertença a um módulo declarado em `modules.txt`, e o
controller de um DocType importa `frappe` **por definição do framework**.

O app já tinha o módulo `Fiscal`, mapeado para a pasta `fiscal/` — que é a **camada pura**,
onde `tests/test_arquitetura.py` verifica que ninguém importa `frappe`. Colocar o DocType
ali quebraria a regra que o projeto verifica por teste.

Mas o framework exige *um* módulo — não exige que seja aquele. Daí o módulo **`Registros
Fiscais`** (pasta `registros_fiscais/`), que existe para guardar o que precisa de banco,
deixando `fiscal/` intacta.

É o caso exato de "ser rígido com o padrão, cedendo só onde o framework impede": não dá
para ter DocType sem controller que importe `frappe`; dá para escolher onde ele mora.

O controller tem **uma linha de lógica** — chama a regra pura e traduz a exceção em
`frappe.throw`.

## A costura que o teste protege

`test_transmissao_registro.py::TestSchemaBateComARegra` confere que os `Select` do JSON
oferecem exatamente as opções que a regra aceita. Sem isso, o usuário escolheria na tela
uma situação que o código recusa — e pareceria bug do sistema, não configuração
inconsistente. Verifica também que o DocType **não** migrou para o módulo `Fiscal`.

## Próximos DocTypes, quando houver consumidor

Mesma disciplina: só quando o dado tiver vida própria e alguém for lê-lo.

- **Lote eSocial** — protocolo de envio, estado do polling (`cdResposta=203`), retorno por
  evento. `transmissao_esocial.py` já produz esse dado e hoje ele se perde.
- **Arquivo SPED gerado** — período, tipo (EFD/ECD/ECF), hash, quem gerou. Hoje o arquivo
  é montado e devolvido, sem registro de que foi entregue.
