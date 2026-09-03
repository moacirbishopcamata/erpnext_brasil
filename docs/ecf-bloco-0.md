# ECF: Bloco 0 (Abertura, Identificação e Referências) — núcleo mínimo

Terceiro bloco da ECF a ganhar código, depois de J e K. Fonte:
`documentacao.senior.com.br/.../bloco-0.htm`, mesmo padrão de confiança já aceito para
J/K.

## Oito registros confirmados, quatro implementados

`0000` (abertura do arquivo), `0001` (abertura do bloco), `0010`/`0020`/`0021`
(parâmetros de tributação), `0030` (dados cadastrais), `0035` (SCP), `0930`
(signatários), `0990` (encerramento).

## Por que `0010`/`0020`/`0021` ficam de fora — não é preguiça, é risco real

Juntos, esses três registros somam **mais de 40 indicadores** regulatórios: é optante do
Refis? tem Sociedade em Conta de Participação? opera com o exterior? participa de
consórcios/coligadas? está habilitada num dos mais de dez programas de incentivo fiscal
(Repes, Recap, Padis, Reidi, Recine, Reporto, Repetro em suas quatro variantes, RET-II,
RET-PMCMV, RET-EEI, EBAS)? Cada um é uma pergunta de sim/não sobre a situação real da
empresa perante a Receita — **nenhum tem valor padrão seguro**. "Não" errado é uma
declaração fiscal tão incorreta quanto "sim" errado, e este projeto não tem, em lugar
nenhum, o cadastro que responderia essas perguntas de verdade. Implementar isso agora
significaria inventar dado — pior que não implementar.

`0035` (identificação de SCP) e `0930` (signatário com registro CRC) também ficam de
fora: nenhum conceito correspondente (sociedade em conta de participação, contador
responsável) existe no projeto ainda.

## O que foi implementado: `0000`, `0001`, `0030`, `0990`

`0000` e `0030` são identificação — CNPJ, nome empresarial, CNAE, endereço — dado que o
projeto já tem em `Company`/`Address`, não pergunta regulatória de sim/não.

**Achado real, declarado**: os campos de `0000` que são indicadores/enumerações
(`IND_SIT_INI_PER`, `SIT_ESPECIAL`, `RETIFICADORA`, `TIP_ECF`, `COD_SCP`) **não têm seus
valores catalogados** neste incremento — a fonte lista os nomes dos campos, não o
significado de cada código, e verificado que nenhum outro módulo `contabil/` deste
projeto tem um campo idêntico para conferir por precedente interno (`RETIFICADORA`/
`TIP_ECF`/`IND_SIT_INI_PER` não aparecem em nenhum outro lugar). Por isso são parâmetros
de texto livre, sem enumeração — `IdentificacaoEcf.retificadora` tem um padrão
razoável (`"0"`) mas não verificado contra o Manual de Orientação; quem gerar um arquivo
real precisa confirmar o valor certo antes.

## Wiring com `Company`/`Address` — pedido direto do usuário ("não esqueça das configurações")

`ecf_bloco_0.py` é puro (não toca Frappe) — correto para testar, mas exigiria de quem
chama digitar CNPJ/nome/CNAE/endereço de novo, mesmo já existindo em `Company`/`Address`.
`integracao/ecf_dados_empresa.py` fecha essa lacuna, mesmo espírito de
`integracao/certificado_a1.py`: `montar_identificacao_0000(company, ...)` e
`montar_dados_cadastrais_0030(company, address)` leem o cadastro e devolvem
`IdentificacaoEcf`/`DadosCadastrais` prontos — só os campos que são decisão da
declaração em si (período, situação, tipo de ECF, retificadora) continuam parâmetro
explícito, não cadastro.

Dois campos novos: `Company.br_natureza_juridica` (não existia; `COD_NAT` do `0030` não
tinha de onde vir) e **`Address.bairro`** — achado real: o `Address` nativo do ERPNext
não tem campo de bairro. Não é lacuna nova desta investigação: `xBairro` já era exigido
pelo endereço da NF-e (`fiscal/documento/elementos_nfe.json`) e nunca tinha campo — o
`0030` da ECF só expôs de novo uma lacuna pré-existente, corrigida aqui.

**Achado real 2, fechado em seguida ao anterior**: o `Address` nativo também não separa
"número" de `address_line1` (embutido no texto do logradouro). Campo novo,
`Address.numero_endereco`, mesmo padrão de `bairro` — `DadosCadastrais.numero` agora lê
dele em vez de ficar sempre vazio.

Sem teste dedicado — `integracao/ecf_dados_empresa.py` depende do Frappe.

## Arquivos

- `erpnext_brasil/contabil/ecf_bloco_0.py` — `IdentificacaoEcf`/`montar_0000`,
  `montar_0001`, `DadosCadastrais`/`montar_0030`, `montar_0990`.
- `erpnext_brasil/integracao/ecf_dados_empresa.py` — `montar_identificacao_0000`,
  `montar_dados_cadastrais_0030`.
- `erpnext_brasil/tests/test_ecf_bloco_0.py` — 6 testes.
