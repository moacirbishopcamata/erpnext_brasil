# Documentação

Referências por assunto. O que cabe numa docstring fica no código; aqui entra o que
precisa de tabela, cronograma ou comparação de alternativas.

| Documento | Assunto |
|---|---|
| [arquitetura.md](arquitetura.md) | Camadas, por que `fiscal/` é puro, como testar sem bench |
| [chave-de-acesso.md](chave-de-acesso.md) | Layout das 44 posições, cálculo do DV, impacto do CNPJ alfanumérico |
| [montagem-da-nfe.md](montagem-da-nfe.md) | Grupos `ide`, `emit`, `dest`; por que a chave é derivada; rejeição 897 |
| [reforma-tributaria.md](reforma-tributaria.md) | IBS, CBS e IS: cronograma, alíquota-teste, obrigatoriedade vigente |
| [transmissao-documento-fiscal.md](transmissao-documento-fiscal.md) | Opções de transporte (ACBrLib × ACBr API) e a fronteira de licença |
| [transporte-nativo-sefaz.md](transporte-nativo-sefaz.md) | Decisão de falar direto com a SEFAZ; tabela de autorizadores por UF (RO confirmado) |
| [inutilizacao-nfe.md](inutilizacao-nfe.md) | Inutilização de faixa de numeração: por que é operação à parte, `@Id`, `cUF` × sigla |
| [ambiente-dev-bench.md](ambiente-dev-bench.md) | Bench Frappe local (Windows 11 + WSL2 + Docker): decisões, obstáculos e como reproduzir |

## Convenções que valem em todo o código

**Idioma.** Tudo em pt-BR — rótulos, mensagens, docstrings, nomes de função. Termos
fiscais brasileiros (CNPJ, NCM, CFOP, CSOSN) são nomes próprios e não se traduzem.

**Alíquota é fração.** `0.18`, nunca `18`. Passar percentual levanta erro. A conversão
para percentual acontece só na fronteira do XML e na leitura de campos do ERPNext, e cada
fronteira tem teste.

**Dinheiro é `Decimal` com `ROUND_HALF_UP`.** O padrão do Python é `ROUND_HALF_EVEN`, que
leva `0.125` para `0.12` quando o documento fiscal espera `0.13`.

**Fonte normativa citada.** Toda constante de origem legal registra onde foi lida. Em
domínio fiscal a regra muda por lei, e sem a fonte ninguém reverifica meses depois.

**Desvio deliberado é documentado como desvio.** Onde a implementação diverge de uma
referência oficial — como a recusa de CNPJ numérico repetido, que o calculador da Receita
aceita —, a divergência é explicada e testada, nunca escondida.
