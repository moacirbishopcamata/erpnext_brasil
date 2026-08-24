# Transmissão de documento fiscal: opções e fronteiras

Nota de arquitetura para a frente ainda não implementada (NF-e, NFC-e, NFS-e, CT-e,
MDF-e). Registra o que foi apurado para que a decisão não seja retomada do zero.

## O erro a não repetir

Os dois projetos brasileiros de localização do ERPNext que chegaram a existir morreram,
e um deles morreu de forma instrutiva: o histórico de commits mostra trinta commits em
quatro dias, terminando em `feat: adiciona API debug_xml para investigar canonicalização`
— ou seja, congelou **dentro** da depuração da canonicalização C14N da assinatura, que é
a parte mais difícil e a que decide se a SEFAZ aceita a nota.

A conclusão não é "assinar localmente é impossível". É que **o transporte não pode ser o
acoplamento do sistema**. Quem amarra o documento fiscal a um transporte específico
aposta o projeto inteiro naquele transporte funcionar.

## A porta

O DocType de Documento Fiscal conversa com uma **interface**, nunca com um fornecedor.
Operações mínimas: transmitir, consultar situação, cancelar, emitir carta de correção,
inutilizar faixa, e obter a representação impressa.

O agregado é dono do **estado** (rascunho → autorizado → cancelado → denegado) e do
mapeamento ERPNext → leiaute. O adaptador é dono apenas do protocolo. A costura crítica
— e é onde bug silencioso mora — é o retorno do protocolo de autorização: se ele não
persistir, existe nota autorizada no fisco e rascunho no sistema.

## Opção A — ACBrLib (local)

Biblioteca nativa (`.dll` / `.so`), LGPL. Faz tudo na sua infraestrutura: assinatura com
certificado A1, webservices da SEFAZ, DANFE.

Contrato apurado em `Projeto-ACBr-Oficial/ACBrLib-Nodejs` (que é FFI via koffi, sem
lógica fiscal própria — a mesma ABI C vale para qualquer linguagem):

- ciclo de vida `inicializar(configPath, chaveCrypt)` / `finalizar()`;
- configuração por sessão/chave: `configLer`, `configGravar`, `configLerValor(sessao, chave)`;
- retorno por **buffer dimensionado pelo chamador** (daí `ACBrBuffer` e `TAMANHO_PADRAO`):
  função devolve status inteiro e escreve em `char*` com tamanho de entrada/saída;
- classes concretas com sufixo **MT** (multi-thread) — são os binários exigidos;
- pacotes por documento: NFe, NFSe, CTe, MDFe, REINF, CEP, PIX.

Em Python o equivalente ao koffi é `ctypes`, da biblioteca padrão — nenhuma dependência
nova.

### Fronteira de licença (importa, e é precisa)

- **Pode**: carregar dinamicamente a `.so`/`.dll` a partir deste app MIT. É exatamente o
  uso que a LGPL permite, e não contamina nada.
- **Pode**: ler o wrapper Node para saber *quais* operações existem e como o ciclo de
  vida e o protocolo de buffer funcionam. Isso é informação de interoperabilidade —
  fato, não expressão.
- **Não pode**: transliterar o TypeScript dele para Python e distribuir como MIT. Aí é
  obra derivada, e o resultado herda LGPL-2.1.

Base legítima para escrever o binding: os **demos oficiais em Python** do próprio ACBr
(SVN do projeto, `Projetos/ACBrLib/Demos/`) e o manual em `acbr.sourceforge.io/ACBrLib`.
Existe ainda `base4sistemas/acbrlib-python` (Apache-2.0, portanto reutilizável sem
contaminação), útil como referência de desenho — mas **parado desde novembro de 2021**,
então não serve como dependência.

## Opção B — ACBr API (HTTP)

Serviço em nuvem com OAuth2, SDK Python oficial (`acbrapi-sdk-python`). Cobre NFe, NFCe,
NFSe, CTe, MDFe, DCe e NFCom. Dissolve de uma vez a questão de licença, o certificado no
servidor e a compilação nativa.

Ressalva apurada: o SDK foi criado em julho de 2026 e **não declara LICENSE**. Ausência
de licença é risco real de adoção — vale abrir issue pedindo antes de depender dele.

## Como escolher

Não é "melhor" e "pior", é onde se quer o custo:

| | ACBrLib local | ACBr API |
|---|---|---|
| Custo por documento | nenhum | por uso |
| Certificado A1 | no seu servidor | delegado |
| Binário nativo por plataforma | sim (e Alpine é problemático) | não |
| Contingência e indisponibilidade da SEFAZ | sua | do provedor |
| Licença | LGPL, com a fronteira acima | indefinida no SDK |

A porta existe justamente para que essa escolha seja adiável e reversível — e para que
uma empresa possa usar uma e outra empresa a outra, na mesma instalação.
