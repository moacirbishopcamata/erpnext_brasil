# Cancelamento e carta de correção da NF-e

Como um usuário cancela ou corrige uma nota emitida pelo app — e as decisões que a costura
tomou.

## O gap que isto fecha

O item 4 de [gaps.md](gaps.md). Tudo o que um cancelamento exige já existia, testado e
documentado:

```text
fiscal/documento/evento.py        monta 110111 e 110110, lidos do XSD
integracao/eventos_sefaz.py       assina, envia por NFeRecepcaoEvento4, traduz o retorno
TransporteSefaz.cancelar/corrigir encadeia os dois
Transmissao Fiscal                já tinha os tipos "Cancelamento" e "Carta de Correção"
```

E nada disso era alcançável de um site: nenhum método `@frappe.whitelist()` chamava a
cadeia, e nenhum botão chamava o método. **Uma nota emitida pelo app não podia ser
cancelada pelo app** — que, para o contribuinte, é o mesmo que não haver cancelamento.

Este é o formato de gap que o projeto trata como pior que bug: código completo, com teste
verde, e inerte.

## Como se usa

No `Sales Invoice` efetivado, menu **Brasil**:

| Botão | Aparece quando | Pergunta |
|---|---|---|
| **Emitir NF-e** | ainda **não** há chave de acesso | confirma o ambiente |
| **Cancelar NF-e** | **há** chave de acesso | justificativa (15 a 256), depois confirma |
| **Carta de Correção** | **há** chave de acesso | texto da correção (15 a 1000) |

Os limites aparecem no diálogo, mas quem valida é o domínio puro
(`fiscal/documento/evento.py`) — o aviso na tela é espelho da regra do XSD, nunca a única
barreira.

Cada desfecho vira um `Transmissao Fiscal`, inclusive a recusa.

## As decisões, e por quê

### UF e CNPJ saem da chave de acesso, não da `Company`

A chave carrega o código da UF nas duas primeiras posições e o CNPJ do emitente da 7ª à
20ª. Foi ela que a SEFAZ autorizou, e é dela que o evento tem de falar.

Reler o cadastro abriria a hipótese de a `Company` ter mudado de endereço ou de CNPJ entre
a emissão e o cancelamento: o evento iria para a SEFAZ errada, ou com autor que não
confere, e a rejeição não diria o porquê. Mesma disciplina que `emissao_nfe` aplica ao
tirar a UF da árvore transmitida.

### O protocolo vem do `Transmissao Fiscal` da autorização

Cancelar exige o `nProt`, que não fica no documento do ERPNext — fica no registro que a
emissão gravou. Procurá-lo ali garante que **só se cancela o que este app conseguiu
autorizar**.

Sem esse registro a operação falha alto, em vez de tentar com protocolo vazio: cancelar
algo não autorizado é erro de premissa, não caso de borda.

### O registro é gravado antes do `throw`

Rejeição de evento é resultado, não defeito de programa. Se o `throw` viesse primeiro, a
resposta da SEFAZ não deixaria rastro nenhum e o usuário teria de adivinhar.

É a asserção-âncora de `test_eventos_nfe.py`: ela não olha valor nenhum, olha a **ordem** —
a parte que um teste de retorno jamais pegaria.

### O JS escreve o nome do método por extenso

`test_costura_cliente` varre os `.js` procurando `method: "<literal>"` e confere que o
método existe no Python e está exposto. Um nome montado em template string
(`` `...${metodo}` ``) **passa despercebido pela varredura**, e um erro de digitação só
apareceria no primeiro clique de um usuário real.

Por isso cada evento monta o seu `frappe.call` com o nome escrito inteiro, e só o desfecho
comum ficou fatorado. É decisão de testabilidade, não de estilo.

### ⚠️ Um teste virou falso-positivo ao ganhar o segundo botão

Vale registrar porque é a armadilha mais barata de repetir. Os testes do botão de emissão
faziam `assertIn("br_chave_acesso", fonte_inteira)`. Com um botão só isso bastava. No
instante em que o botão de cancelamento passou a citar o mesmo campo, **a asserção deixou
de provar qualquer coisa**: continuaria verde mesmo se a condição do botão de emissão
sumisse.

Corrigido com `_bloco()`, que fatia a função pelo balanceamento de chaves e mede só a parte
que interessa. É a mesma família de `_sem_comentarios()` — asserção que mede texto demais
passa a valer por acidente.

## O que **não** está aqui, declarado

- **`xml_enviado` fica vazio nos registros de evento.** O XML é montado dentro do
  `TransporteSefaz`, que não o devolve. Trazê-lo até o adaptador exigiria montar o evento
  fora do transporte e duplicar o ciclo de vida do certificado que `contexto_sefaz.py`
  proíbe duplicar — preferiu-se um campo vazio e declarado a uma duplicação que vaza chave
  privada em disco. O `xml_retorno` é gravado normalmente.
- **O documento do ERPNext não é marcado como cancelado.** Não existe campo declarado para
  a situação fiscal, e gravar atributo não declarado num `Document` **some no save, sem
  erro** — foi assim que 31 campos ficaram inertes. A situação vive no `Transmissao
  Fiscal`; criar o campo é decisão à parte, com o campo declarado **antes** do código que
  o usa.
- **Prazo de cancelamento.** A SEFAZ recusa cancelamento fora do prazo, e quem recusa é
  ela. O app não replica a regra: replicá-la sem fonte verificada produziria uma recusa
  local que talvez não corresponda à real.
- **`nSeqEvento` fica em 1.** Retransmitir o mesmo evento é outro fluxo, e um contador sem
  controle de concorrência repetiria o problema que `numeracao_fiscal` resolve com trava de
  linha.
- **Eventos de CT-e e MDF-e** têm domínio próprio já documentado
  ([cte-evento-cancelamento.md](cte-evento-cancelamento.md),
  [mdfe-evento-cancelamento.md](mdfe-evento-cancelamento.md)) e **não** têm esta costura:
  não há DocType no ERPNext que guarde esses documentos.
- **EPEC** continua fora — depende de detectar indisponibilidade da SEFAZ, que é outra
  frente.

## Estado de verificação

Camada Frappe, **não** exercitada contra bench real nem contra a SEFAZ. Os testes são de
costura estática: domínios gravados × `Select` do DocType, campos gravados × campos
declarados, ordem dos efeitos e superfície exposta. Clicar o botão num site segue em
[gaps.md](gaps.md).
